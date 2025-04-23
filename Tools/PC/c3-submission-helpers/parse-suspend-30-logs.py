#! /usr/bin/env python3

import argparse
import io
import os
import re
import sys
import tarfile
import textwrap
from collections import defaultdict
from typing import Literal, TypedDict, cast
from rich.console import Console

SPACE = "    "
BRANCH = "│   "
TEE = "├── "
LAST = "└── "


type FailType = Literal["Critical", "High", "Medium", "Low", "Other"]


SUMMARY_FILE_PATTERN = (
    r"test_output/com.canonical.certification__stress-tests"
    r"_suspend-[0-9]+-cycles-with-reboot-[0-9]+-log-check"
)


class Input:
    filename: str
    write_individual_files: bool
    write_directory: str
    verbose: bool
    num_suspends: int
    num_boots: int
    inverse_find: bool
    no_summary: bool
    no_meta: bool


class C:  # color
    high = "\033[94m"
    low = "\033[95m"
    medium = "\033[93m"
    critical = "\033[91m"
    other = "\033[96m"
    ok = "\033[92m"
    end = "\033[0m"
    gray = "\033[90m"
    bold = "\033[1m"


class Meta(TypedDict):
    """
    Metadata of a single run. We only collect time and kernel info for now
    """

    date: str
    time: str
    kernel: str


def parse_args() -> Input:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--no-summary",
        action="store_true",
        help="Don't print the summary file at the top",
    )
    p.add_argument(
        "--no-meta",
        action="store_true",
        help=(
            "Don't write the metadata section when -w is specified. ("
            f"The {'/'.join(Meta.__annotations__.keys())} section)"
        ),
    )
    p.add_argument(
        "filename",
        help="The path to the suspend logs or the stress test submission .tar",
    )
    p.add_argument(
        "-w",
        "--write-individual-files",
        action="store_true",
        help=(
            "If specified, the logs will be split up into individual files "
            "in a directory specified with -d"
        ),
    )
    p.add_argument(
        "-d",
        "--directory",
        dest="write_directory",
        default="",
        required=False,
        help=(
            "Where to write the individual logs. "
            "If not specified and the -w flag is true, "
            "it will create a new local directory called "
            "{your original file name}-split"
        ),
    )
    p.add_argument(
        "-v",
        "--verbose",
        help="Show line numbers of where the errors are in th input file",
        dest="verbose",
        action="store_true",
    )
    p.add_argument(
        "-nb",
        "--num-boots",
        help="Set the expected number of boots in the input file. Default=3.",
        dest="num_boots",
        default=3,
        required=False,
        type=int,
    )
    p.add_argument(
        "-ns",
        "--num-suspends-per-boot",
        help="Set the expected number of runs in the input file. Default=30.",
        dest="num_suspends",
        default=30,
        required=False,
        type=int,
    )
    p.add_argument(
        "-i",
        "--inverse",
        dest="inverse_find",
        action="store_true",
        default=False,
        help=(
            "Find runs that do NOT have a failure instead of the opposite. "
            "Useful if you encounter machines that fails almost every run."
        ),
    )

    out = p.parse_args()
    out.write_directory = out.write_directory or f"{out.filename}-split"
    return cast(Input, out)


def line_is_summary_table(l: str) -> bool:
    return l.replace(" ", "") == "Test|Pass|Fail|Abort|Warn|Skip|Info|"


def open_log_file(
    args: Input,
) -> tuple[
    dict[int, dict[int, io.TextIOWrapper]],  # {boot_i: {suspend_i: file_obj}}
    io.TextIOWrapper | None,
    dict[int, list[int]],
]:
    if not args.filename.endswith(".tar.xz"):
        raise TypeError("File must be a tar file")

    try:
        tarball = tarfile.open(args.filename)
    except FileNotFoundError:
        print(f"{C.critical}{args.filename} not found!{C.end}")
        exit(1)

    summary_file_name = None
    possible_summary_files = [
        m.name
        for m in tarball.getmembers()
        if re.match(SUMMARY_FILE_PATTERN, m.name) is not None
    ]
    if len(possible_summary_files) == 0:
        print(
            "No attachment files matching",
            f"{C.medium}`{SUMMARY_FILE_PATTERN}`{C.end}",
            f"was found in {args.filename}. Ignoring",
        )
    summary_file_name = (
        possible_summary_files[0] if len(possible_summary_files) > 0 else None
    )

    summary_file = None
    if summary_file_name:
        print("Found this summary attachment:", f'"{summary_file_name}"')
        summary_file = tarball.extractfile(summary_file_name)
        if summary_file is None:
            print(
                f"Found {summary_file_name} in {args.filename},"
                "but it can't be extracted, Ignoring",
                file=sys.stderr,
            )

    # 1 based indices
    log_files = defaultdict(
        defaultdict
    )  # type: dict[int, dict[int,io.TextIOWrapper]]
    missing_runs = defaultdict(list)  # type: dict[int, list[int]]
    for boot_i in range(1, args.num_boots + 1):
        for suspend_i in range(1, args.num_suspends + 1):
            individual_file_name = (
                "test_output/com.canonical.certification__stress-tests_"
                + f"suspend_cycles_{suspend_i}_reboot{boot_i}"
            )
            try:
                extracted = tarball.extractfile(individual_file_name)
                assert extracted, f"Failed to extract {individual_file_name}"
                log_files[boot_i][suspend_i] = io.TextIOWrapper(extracted)
            except KeyError:  # from extract
                missing_runs[boot_i].append(suspend_i)

    return (
        log_files,
        summary_file and io.TextIOWrapper(summary_file),
        missing_runs,
    )


def transform_err_msg(msg: str) -> str:
    # some known error message transforms to help group them together
    # this is disabled with --no-transform flag
    msg = msg.strip()
    s3_total_hw_sleep = (
        "s3: Expected /sys/power/suspend_stats/total_hw_sleep to increase"
    )
    if msg.startswith(s3_total_hw_sleep):
        return s3_total_hw_sleep
    s3_last_hw_sleep = r"s3: Expected /sys/power/suspend_stats/last_hw_sleep to be at least 70% of the last sleep cycle"
    if msg.startswith(s3_last_hw_sleep):
        return s3_last_hw_sleep

    return msg


def group_by_err(
    failed_runs_by_type: dict[FailType, dict[int, dict[int, set[str]]]],
):
    # [fail_type][boot_i][suspend_i][msg_i] = msg
    # convert to => [fail_type][msg][boot_i] = list of suspend indices
    out: dict[FailType, dict[str, dict[int, list[int]]]] = {}
    for fail_type, runs in failed_runs_by_type.items():
        if len(runs) == 0:
            continue

        for boot_i, suspends in runs.items():
            for suspend_i, messages in suspends.items():
                for msg in messages:
                    if fail_type not in out:
                        out[fail_type] = {}
                    if msg not in out[fail_type]:
                        out[fail_type][msg] = {}
                    if boot_i not in out[fail_type][msg]:
                        out[fail_type][msg][boot_i] = []

                    out[fail_type][msg][boot_i].append(suspend_i)

    return out


def print_by_err(
    grouped: dict[FailType, dict[str, dict[int, list[int]]]],
    num_boots: int,
    num_suspends: int,
):
    for fail_type, msg_group in grouped.items():
        print(f"{getattr(C, fail_type.lower())}{fail_type} failures{C.end}")
        for msg in msg_group:
            print(SPACE, f"{C.bold}{msg}{C.end}")
            for boot_i, suspends in msg_group[msg].items():
                branch_text = LAST if boot_i == num_boots  else BRANCH
                wrapped_indices = textwrap.wrap(
                    str(suspends),
                    width=50,
                )
                line1 = f"{SPACE} {SPACE} {TEE} Reboot {boot_i}: {wrapped_indices[0]}"
                print(line1)
                for line in wrapped_indices[1:]:
                    print(
                        f"{SPACE} {SPACE} {BRANCH}{' ' * len(f' Reboot {boot_i}: ')}",
                        line,
                    )
                print(
                    SPACE,
                    SPACE,
                    branch_text,
                    f"Fail rate: {len(suspends)}/{num_suspends}",
                )


def main():
    args = parse_args()

    print(
        f"{C.medium}[ WARN ] The summary file might not match",
        "the number of failures found by this script.",
        "Please double check since the original test case did some filtering",
        "and may consider some failures to be not worth reporting",
        C.end,
    )

    expected_num_results = args.num_boots * args.num_suspends  # noqa: N806

    print(
        f"Expecting ({args.num_boots} boots * "
        f"{args.num_suspends} suspends per boot) = "
        f"{expected_num_results} results"
    )

    if args.write_individual_files:
        print(f'Individual results will be in "{args.write_directory}"')

    log_files, summary_file, missing_runs = open_log_file(args)

    if not args.no_summary:
        if summary_file:
            print(f"\n{C.gray}{' Begin Summary Attachment ':-^80}{C.end}\n")

            for line in summary_file.readlines():
                clean_line = line.strip()
                if clean_line != "":
                    print(clean_line)
            summary_file.close()

            print(f"\n{C.gray}{' End of Summary ':-^80}{C.end}\n")
        else:
            print(
                "No suspend-30-cycles-with-reboot-3-log-check attachment",
                "was found in the tarball",
            )

    # [fail_type][boot_i][suspend_i][msg_i] = msg
    failed_runs_by_type: dict[FailType, dict[int, dict[int, set[str]]]] = {
        "Critical": {},
        "High": {},
        "Medium": {},
        "Low": {},
        "Other": {},
    }
    for boot_i in log_files:
        for suspend_i in log_files[boot_i]:
            log_file = log_files[boot_i][suspend_i]
            curr_meta = None  # type: Meta | None

            log_file_lines = log_file.readlines()
            for i, line in enumerate(log_file_lines):
                if line.startswith("This test run on"):
                    # Example:
                    # This test run on 13/08/24 at
                    # 01:10:22 on host Linux ubuntu 6.5.0-1027-oem
                    regex = r"This test run on (.*) at (.*) on host (.*)"
                    match_output = re.match(regex, line)
                    if match_output:
                        curr_meta = Meta(
                            date=match_output.group(1),
                            time=match_output.group(2),
                            kernel=match_output.group(3),
                        )
                    continue

                for fi, fail_type in enumerate(
                    ("Critical", "High", "Medium", "Low", "Other")
                ):
                    if line.startswith(f"{fail_type} failures: "):
                        fail_count = line.split(":")[1].strip()
                        if fail_count == "NONE":
                            continue

                        if boot_i not in failed_runs_by_type[fail_type]:
                            failed_runs_by_type[fail_type][boot_i] = {}
                        if (
                            suspend_i
                            not in failed_runs_by_type[fail_type][boot_i]
                        ):
                            failed_runs_by_type[fail_type][boot_i][
                                suspend_i
                            ] = set()

                        if fail_type == "Other":
                            error_msg_i = i + 1
                            msg = transform_err_msg(
                                log_file_lines[error_msg_i]
                            )
                            while error_msg_i < len(
                                log_file_lines
                            ) and not line_is_summary_table(msg):
                                failed_runs_by_type[fail_type][boot_i][
                                    suspend_i
                                ].add(msg)
                                error_msg_i += 1
                        else:
                            error_msg_i = i + 1
                            msg = transform_err_msg(
                                log_file_lines[error_msg_i]
                            )
                            while error_msg_i < len(
                                log_file_lines
                            ) and not msg.startswith(fail_type[fi + 1]):
                                failed_runs_by_type[fail_type][boot_i][
                                    suspend_i
                                ].add(msg)
                                error_msg_i += 1

            if args.write_individual_files:
                print(
                    f"Writing boot_{boot_i}_suspend_{suspend_i}.txt...",
                    end="\r",
                )
                if not os.path.exists(args.write_directory):
                    os.mkdir(args.write_directory)

                with open(
                    f"{args.write_directory}/boot_{boot_i}_suspend_{suspend_i}.txt",
                    "w",
                ) as f:
                    if curr_meta:
                        f.write(f"{' BEGIN METADATA  ':*^80}\n\n")
                        f.write(
                            "\n".join(
                                f"{k}: {v}" for k, v in curr_meta.items()
                            )
                        )
                        f.write(
                            "\n\n"
                            f"{' END OF METADATA, BEGIN ORIGINAL OUTPUT  ':*^80}"
                            "\n\n"
                        )
                    else:
                        print(
                            f"{C.high}[ WARN ]{C.end} No meta data was found",
                            f"for boot {boot_i} suspend {suspend_i}",
                        )
                    log_file.seek(0)
                    f.write(log_file.read())

            log_file.close()

    # done collecting, pretty print results
    n_missing_runs = sum(map(len, missing_runs.values()))
    n_failed_runs = sum(map(len, failed_runs_by_type.values()))

    if n_missing_runs == 0:
        print(
            f"{C.ok}[ OK ]{C.end} Found all {expected_num_results}",
            "expected log files!",
        )
        if n_failed_runs == 0:
            print(
                f"{C.ok}No failures across {args.num_boots} boots "
                f"and {args.num_suspends} suspends!{C.end}"
            )
            return
    else:
        print(
            f"{C.critical}These log files are missing;",
            f"DUT might have crashed during these jobs!{C.end}",
        )
        for boot_i, suspend_indicies in missing_runs.items():
            print(f"- Reboot {boot_i}, suspend {str(suspend_indicies)}")

    print()
    print(C.gray + "=" * 80 + C.end)

    grouped = group_by_err(failed_runs_by_type)
    print_by_err(grouped, args.num_boots, args.num_suspends)

    return

    for fail_type, runs in failed_runs_by_type.items():
        fail_type = fail_type.lower()
        if len(runs) == 0:
            continue

        total_fails_of_this_type = sum(map(len, runs.values()))

        if args.inverse_find:
            print(
                f"\nRuns without {getattr(C, fail_type)}{fail_type}{C.end} failures:"
            )
        else:
            print(
                f"\nFound {total_fails_of_this_type} run(s) with",
                f"{getattr(C, fail_type)}{fail_type}{C.end} failures:",
            )

        for boot_i in range(1, args.num_boots + 1):
            branch_text = LAST if boot_i == args.num_boots else TEE
            if boot_i not in runs:
                print(f"{SPACE} {branch_text} Reboot {boot_i}: No failures!")
                continue

            branch_text = LAST if boot_i == args.num_boots else BRANCH
            if args.inverse_find:
                indices_to_print = list(
                    set(range(1, args.num_suspends + 1))
                    - set(missing_runs[boot_i])
                    - set(runs[boot_i])
                )
            else:
                indices_to_print = runs[boot_i]

            wrapped_suspend_indices = textwrap.wrap(
                str(indices_to_print),
                width=50,
            )
            line1 = (
                f"{SPACE} {TEE} Reboot {boot_i}: {wrapped_suspend_indices[0]}"
            )
            print(line1)
            for line in wrapped_suspend_indices[1:]:
                print(
                    f"{SPACE} {BRANCH}{' ' * len(f' Reboot {boot_i}: ')}", line
                )

            if args.inverse_find:
                print(
                    SPACE,
                    branch_text,
                    f"Success rate: {len(indices_to_print)}/{args.num_suspends}",
                )
            else:
                print(
                    SPACE,
                    branch_text,
                    f"Fail rate: {len(indices_to_print)}/{args.num_suspends}",
                )


if __name__ == "__main__":
    main()

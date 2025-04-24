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

SPACE = "    "
BRANCH = "│   "
TEE = "├── "
LAST = "└── "


FailType = Literal["Critical", "High", "Medium", "Low", "Other"]


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
    # inverse_find: bool
    no_summary: bool
    no_meta: bool
    no_transform: bool


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
        "-s",
        "--no-summary",
        action="store_true",
        help="Don't print the summary file at the top",
    )
    p.add_argument(
        "-m",
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
        "-t",
        "--no-transform",
        action="store_true",
        help="Disables any form of error message tranformation "
        "except trimming whitespaces. "
        "By default, this script will attempt to remove timestamps and "
        "certain numbers to better group the error messages. "
        "This option disables this behavior.",
    )

    out = p.parse_args()
    out.write_directory = out.write_directory or f"{out.filename}-split"
    return cast(Input, out)


def line_is_summary_table(line: str) -> bool:
    return line.replace(" ", "") == "Test|Pass|Fail|Abort|Warn|Skip|Info|"


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
        print(
            f"{C.low}[ INFO ]{C.end} Found this summary attachment:",
            f'"{summary_file_name}"',
        )
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


def default_err_msg_transform(msg: str) -> str:
    # some known error message transforms to help group them together
    # this is disabled with --no-transform flag
    kernel_msg_prefix_pattern = (
        r"(CRITICAL|HIGH|MEDIUM|LOW|OTHER) Kernel message:"
    )
    timestamp_pattern = r"\[ *[0-9]+.[0-9]+\]"

    msg = re.sub(timestamp_pattern, "", msg)
    msg = re.sub(kernel_msg_prefix_pattern, "", msg)
    msg = re.sub(" +", " ", msg)  # remove double spaces
    msg = msg.strip()

    known_prefixes = [
        "s3: Expected /sys/power/suspend_stats/total_hw_sleep to increase",
        (
            "s3: Expected /sys/kernel/debug/pmc_core/slp_s0_residency_usec "
            + "to increase"
        ),
        (
            r"s3: Expected /sys/power/suspend_stats/last_hw_sleep "
            + r"to be at least 70% of the last sleep cycle"
        ),
    ]
    for prefix in known_prefixes:
        if msg.startswith(prefix):
            return prefix

    known_patterns = {r"slept for (.*) seconds,": "slept"}
    for pattern, replacement in known_patterns.items():
        msg = re.sub(pattern, replacement, msg)

    return msg


def group_by_err(
    failed_runs_by_type: dict[FailType, dict[int, dict[int, set[str]]]],
):
    # [fail_type][boot_i][suspend_i][msg_i] = msg
    # convert to => [fail_type][msg][boot_i] = list of suspend indices
    out: dict[FailType, dict[str, dict[int, list[int]]]] = {}

    for fail_type, runs in failed_runs_by_type.items():
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
    actual_suspend_counts: dict[int, int],
    expected_n_suspends: int,
):
    for fail_type, msg_group in grouped.items():
        print(f"{getattr(C, fail_type.lower())}{fail_type} failures{C.end}")
        for msg in msg_group:
            print(SPACE, f"{C.bold}{msg}{C.end}")
            for pos, (boot_i, suspends) in enumerate(msg_group[msg].items()):
                suspend_count = actual_suspend_counts[boot_i]
                if suspend_count != expected_n_suspends:
                    fail_rate_text = (
                        f"{C.critical}{len(suspends)}/{suspend_count}{C.end}"
                    )
                else:
                    fail_rate_text = f"{len(suspends)}/{str(suspend_count)}"

                branch_text = (
                    LAST if pos == len(msg_group[msg]) - 1 else BRANCH
                )

                wrapped_indices = textwrap.wrap(
                    str(suspends),
                    width=50,
                )
                line1 = (
                    f"{SPACE} {SPACE} {TEE} "
                    + f"Reboot {boot_i}: {wrapped_indices[0]}"
                )
                print(line1)
                for line in wrapped_indices[1:]:
                    print(
                        f"{SPACE} {SPACE} {BRANCH}"
                        + f"{' ' * len(f' Reboot {boot_i}: ')}",
                        line,
                    )

                print(
                    SPACE,
                    SPACE,
                    branch_text,
                    f"Fail rate: {fail_rate_text}",
                )
        print()  # new line between critical, high ...


transform_err_msg = default_err_msg_transform


def main():
    args = parse_args()

    if args.no_transform:
        global transform_err_msg
        # idk why tox doesn't like this, this is super common
        transform_err_msg = lambda s: s.strip()  # noqa: E731

    print(
        f"{C.medium}[ WARN ]{C.end} The summary file might not match",
        "the number of failures found by this script.",
    )
    print(
        f"{C.medium}[ WARN ]{C.end} Please double check since",
        "the original test case did some filtering",
        "and may consider some failures to be not worth reporting",
    )

    expected_num_results = args.num_boots * args.num_suspends  # noqa: N806

    print(
        f"{C.low}[ INFO ]{C.end} Expecting ({args.num_boots} boots * "
        f"{args.num_suspends} suspends per boot) = "
        f"{expected_num_results} results"
    )

    if args.write_individual_files:
        print(
            f"{C.low}[ INFO ]{C.end} Individual results will be in",
            f'"{args.write_directory}"',
        )

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
    actual_suspend_counts: dict[int, int] = {}

    for boot_i in log_files:
        actual_suspend_counts[boot_i] = len(log_files[boot_i])
        for suspend_i in log_files[boot_i]:
            log_file = log_files[boot_i][suspend_i]
            log_file_lines = log_file.readlines()
            log_file.close()

            curr_meta = None  # type: Meta | None

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

                for fail_type in "Critical", "High", "Medium", "Low", "Other":
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

                        error_msg_i = i + 1
                        while error_msg_i < len(log_file_lines):
                            raw_line = log_file_lines[error_msg_i].strip()
                            if raw_line == "" or line_is_summary_table(
                                raw_line
                            ):
                                break

                            msg = transform_err_msg(
                                log_file_lines[error_msg_i]
                            )
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
                    f"{args.write_directory}/boot_{boot_i}_suspend_{suspend_i}.txt",  # noqa: E501
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
                            f"{' END OF METADATA, BEGIN ORIGINAL FILE ':*^80}"
                            "\n\n"
                        )
                    else:
                        print(
                            f"{C.high}[ WARN ]{C.end} No meta data was found",
                            f"for boot {boot_i} suspend {suspend_i}",
                        )

                    for line in log_file_lines:
                        f.write(line)

    # done collecting, pretty print results
    n_missing_runs = sum(map(len, missing_runs.values()))
    n_failed_runs = sum(map(len, failed_runs_by_type.values()))

    if n_missing_runs == 0:
        print(
            f"{C.ok}[  OK  ]{C.end} Found all {expected_num_results}",
            "expected log files!",
        )
        if n_failed_runs == 0:
            print(
                f"{C.ok}[  OK  ]{C.end}",
                f"No failures across {args.num_boots} boots",
                f"and {args.num_suspends} suspends!",
            )
            return
    else:
        print(
            f"{C.critical}These log files are missing,",
            f"DUT might have crashed during these jobs!{C.end}",
        )
        for boot_i, suspend_indicies in missing_runs.items():
            print(f"- Reboot {boot_i}, suspend {str(suspend_indicies)}")

    print()
    print(C.gray + "=" * 80 + C.end)
    print()

    grouped = group_by_err(failed_runs_by_type)
    print_by_err(grouped, actual_suspend_counts, args.num_suspends)


if __name__ == "__main__":
    main()

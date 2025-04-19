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
        tar = tarfile.open(args.filename)
    except FileNotFoundError:
        print(f"{C.critical}{args.filename} not found!{C.end}")
        exit(1)

    summary_file_name = None
    possible_summary_files = [
        m.name
        for m in tar.getmembers()
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
        summary_file = tar.extractfile(summary_file_name)
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
                extracted = tar.extractfile(individual_file_name)
                assert extracted, f"Failed to extract {individual_file_name}"
                log_files[boot_i][suspend_i] = io.TextIOWrapper(extracted)
            except KeyError:  # from extract
                missing_runs[boot_i].append(suspend_i)

    return (
        log_files,
        summary_file and io.TextIOWrapper(summary_file),
        missing_runs,
    )


def main():
    args = parse_args()
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

    failed_runs_by_type: dict[FailType, dict[int, list[int]]] = {
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

            for line in log_file:
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

                        if boot_i in failed_runs_by_type[fail_type]:
                            failed_runs_by_type[fail_type][boot_i].append(
                                suspend_i
                            )
                        else:
                            failed_runs_by_type[fail_type][boot_i] = [
                                suspend_i
                            ]

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
    if sum(map(len, missing_runs.values())) == 0:
        print(
            f"{C.ok}[ OK ]{C.end} Found all {expected_num_results}",
            "expected log files!",
        )
    else:
        print(
            f"{C.critical}These log files are missing;",
            f"DUT might have crashed during these jobs!{C.end}",
        )
        for boot_i, suspend_indicies in missing_runs.items():
            print(f"- Reboot {boot_i}, suspend {str(suspend_indicies)}")
    if sum(map(len, failed_runs_by_type.values())) == 0:
        print(
            f"{C.ok}No failures across {args.num_boots} boots "
            f"and {args.num_suspends} suspends!{C.end}"
        )
        return

    print()
    print(C.gray + "=" * 80 + C.end)

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
    print(
        f"{C.medium}The summary file might not match",
        "the number of failures found by this script.",
        "Please double check as the original test case did some filtering.",
        C.end,
    )
    main()

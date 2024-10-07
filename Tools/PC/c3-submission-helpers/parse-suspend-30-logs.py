#! /usr/bin/python3

import os
from typing import Literal, TypedDict
import re
import argparse
import tarfile
import io
import sys
import textwrap

space = "    "
branch = "│   "
tee = "├── "
last = "└── "


class Input:
    filename: str
    write_individual_files: bool
    write_directory: str
    verbose: bool
    num_runs: int | None
    inverse_find: bool


class C:  # color
    high = "\033[94m"
    low = "\033[95m"
    medium = "\033[93m"
    critical = "\033[91m"
    other = "\033[96m"
    ok = "\033[92m"
    end = "\033[0m"


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
        "-f", "--filename", required=True, help="The path to the suspend logs"
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
        "-n",
        "--num-runs",
        help="Set the expected number of runs in the input file. Default=90.",
        dest="num_runs",
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
            "Find runs that do NOT have a failure instead of the opposite."
            "Useful if you encounter machines that fails almost every run."
        ),
    )

    out = p.parse_args()
    out.write_directory = out.write_directory or f"{out.filename}-split"
    return out  # type:ignore


FailType = Literal["Critical", "High", "Medium", "Low", "Other"]

log_file_pattern = (
    r"attachment_files/com.canonical.certification__"
    r"stress-tests_suspend-[0-9]+-cycles-with-reboot-[0-9]+-log-attach"
)


def open_log_file(filename: str) -> io.TextIOWrapper:
    if not filename.endswith(".tar.xz"):
        return open(filename)

    summary_file_name = 'test_output/com.canonical.certification__stress-tests_suspend-30-cycles-with-reboot-3-log-check'
    log_file_name = None
    try:
        possible_log_files = [
            m.name
            for m in tarfile.open(filename).getmembers()
            if re.match(log_file_pattern, m.name) is not None
        ]

        if len(possible_log_files) == 0:
            print(
                f"No log files matching {C.critical}`{log_file_pattern}`{C.end} was found in {filename}, exiting"
            )
            exit(1)

        if len(possible_log_files) > 1:
            print(
                f"Multiple log files found in {filename}, assuming {possible_log_files[0]}"
            )

        log_file_name = possible_log_files[0]
        print("Parsing this file:", log_file_name)

        extracted = tarfile.open(filename).extractfile(log_file_name)

        if extracted is None:
            print(
                f"Found {log_file_name} in {filename}, but it's not a file.",
                file=sys.stderr,
            )
            exit(1)

        file = io.TextIOWrapper(extracted)
    except KeyError:
        print(
            f'{C.critical}"{log_file_name}" doesn\'t exist in the tarball "{filename}"{C.end}',
            file=sys.stderr,
        )
        print(
            f"If the log file is under a different name, try manually extracting {filename} and pass in path/to/the/log/file with the -f flag."
        )
        exit(1)

    return file


def main():
    SECTION_BEGIN = "= Test Results ="  # noqa: N806

    args = parse_args()
    EXPECTED_NUM_RESULTS = args.num_runs or 90  # noqa: N806
    print(f"{C.ok}Expecting {EXPECTED_NUM_RESULTS} results{C.end}")

    if args.write_individual_files:
        print(f'Individual results will be in "{args.write_directory}"')

    with open_log_file(args.filename) as file:
        lines = file.readlines()
        test_results: list[list[str]] = []
        meta: list[Meta] = []
        failed_runs_by_type: dict[FailType, list[int]] = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": [],
            "Other": [],
        }

        i = 0
        while i < len(lines) and SECTION_BEGIN not in lines[i]:
            i += 1  # scroll to the first section

        while i < len(lines):
            line = lines[i]

            if SECTION_BEGIN not in line:
                continue

            i += 1
            curr_result_lines: list[str] = []
            curr_meta: Meta = {"date": "", "time": "", "kernel": ""}

            while i < len(lines) and SECTION_BEGIN not in lines[i]:
                curr_line = lines[i].strip().strip("\n")

                if curr_line != "":
                    curr_result_lines.append(curr_line)

                if curr_line.startswith("This test run on"):
                    # Example:
                    # This test run on 13/08/24 at
                    # 01:10:22 on host Linux ubuntu 6.5.0-1027-oem
                    regex = r"This test run on (.*) at (.*) on host (.*)"
                    match_output = re.match(regex, curr_line)
                    if match_output:
                        curr_meta["date"] = match_output.group(1)
                        curr_meta["time"] = match_output.group(2)
                        curr_meta["kernel"] = match_output.group(3)

                for fail_type in "Critical", "High", "Medium", "Low", "Other":
                    if curr_line.startswith(f"{fail_type} failures: "):
                        fail_count = curr_line.split(": ")[1]
                        if fail_count == "NONE":
                            continue
                        if args.verbose:
                            t = fail_type.lower()
                            print(
                                f"Line {i}, run {len(test_results) + 1} has "
                                f"{getattr(C, t)}{t}{C.end} "
                                f"failures: {fail_count}"
                            )

                        failed_runs_by_type[fail_type].append(
                            len(test_results) + 1
                        )
                i += 1

            if args.write_individual_files:
                if not os.path.exists(args.write_directory):
                    os.mkdir(args.write_directory)
                with open(
                    f"{args.write_directory}/{len(test_results) + 1}.txt", "w"
                ) as f:
                    f.write(f"{' BEGIN METADATA  ':*^80}\n\n")
                    f.write(
                        "\n".join(f"{k}: {v}" for k, v in curr_meta.items())
                    )
                    f.write(
                        "\n\n"
                        f"{' END OF METADATA, BEGIN ORIGINAL OUTPUT  ':*^80}"
                        "\n\n"
                    )
                    f.write("\n".join(curr_result_lines))

            test_results.append(curr_result_lines)
            meta.append(curr_meta)

        n_results = len(test_results)
        print(
            f"\nTotal results = {n_results}"
            + (
                f" {C.ok}COUNT OK!{C.end}"
                if n_results == EXPECTED_NUM_RESULTS
                else (
                    f", {C.critical}but {EXPECTED_NUM_RESULTS} "
                    f"was expected{C.end}"
                )
            )
        )

        for fail_type, runs in failed_runs_by_type.items():
            if len(runs) != 0:
                if args.inverse_find:
                    runs_without_failures = list(
                        set(range(1, n_results + 1)).difference(runs)
                    )
                    print(
                        f"Runs without {getattr(C, fail_type.lower())}"
                        f"{fail_type}{C.end} failures: {runs_without_failures}"
                    )
                    print(
                        "  - Success rate:",
                        f"{len(runs_without_failures)}/{n_results}",
                    )
                else:
                    print(
                        f"Runs with {getattr(C, fail_type.lower())}"
                        f"{fail_type}{C.end} failures:"
                    )
                    print(space + (f"\n{space}").join(textwrap.wrap(str(runs))))
                    print(f"{space}- Fail rate: {len(runs)}/{n_results}")

if __name__ == "__main__":
    main()

#! /usr/bin/env python3

import argparse
import io
import os
import re
import sys
import tarfile
import textwrap
from collections import defaultdict
from typing import Callable, Iterable, Literal, MutableMapping, TypedDict, cast

SPACE = "    "
BRANCH = "│   "
TEE = "├── "
LAST = "└── "


FailType = Literal["Critical", "High", "Medium", "Low", "Other"]
RunsGroupedByIndex = MutableMapping[
    FailType, MutableMapping[int, MutableMapping[int, set[str]]]
]
RunsGroupedByError = MutableMapping[
    FailType, MutableMapping[str, MutableMapping[int, list[int]]]
]
LogFilesByIndex = MutableMapping[int, MutableMapping[int, io.TextIOWrapper]]


class Input:
    filename: str
    write_individual_files: bool
    write_dir: str
    verbose: bool
    num_suspends: int
    num_boots: int
    # inverse_find: bool
    no_summary: bool
    no_meta: bool
    no_transform: bool
    no_color: bool


class Color:
    def __init__(self, no_color=False) -> None:
        self.no_color = no_color

    def critical(self, s: str):
        if self.no_color:
            return s
        return f"\033[91m{s}\033[0m"

    def high(self, s: str):
        if self.no_color:
            return s
        return f"\033[94m{s}\033[0m"

    def medium(self, s: str):
        if self.no_color:
            return s
        return f"\033[93m{s}\033[0m"

    def low(self, s: str):
        if self.no_color:
            return s
        return f"\033[95m{s}\033[0m"

    def other(self, s: str):
        if self.no_color:
            return s
        return f"\033[96m{s}\033[0m"

    def ok(self, s: str):
        if self.no_color:
            return s
        return f"\033[92m{s}\033[0m"

    def gray(self, s: str):
        if self.no_color:
            return s
        return f"\033[90m{s}\033[0m"

    def bold(self, s: str):
        if self.no_color:
            return s
        return f"\033[1m{s}\033[0m"


class Meta(TypedDict):
    """
    Metadata of a single run. We only collect time and kernel info for now
    """

    date: str
    time: str
    kernel: str


C = Color()
SUMMARY_FILE_PATTERN = (
    r"test_output/com.canonical.certification__stress-tests"
    r"_suspend-[0-9]+-cycles-with-reboot-[0-9]+-log-check"
)
FAIL_TYPES = ("Critical", "High", "Medium", "Low", "Other")


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
        dest="write_dir",
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
    p.add_argument(
        "-c",
        "--no-color",
        action="store_true",
        help="Disables all colors and styles",
    )

    out = p.parse_args()
    # have to wait until out.filename is populated
    out.write_dir = out.write_dir or f"{out.filename}-split"
    return cast(Input, out)


def line_is_summary_table(line: str) -> bool:
    return line.replace(" ", "") == "Test|Pass|Fail|Abort|Warn|Skip|Info|"


def open_log_file(filename: str, num_boots: int, num_suspends: int) -> tuple[
    LogFilesByIndex,
    io.TextIOWrapper | None,
    dict[int, list[int]],
]:
    """Collects all the file handles for each log file

    :param args: input
    :raises TypeError: if the input file is not a tar file
    :return: 3-tuple (
            [boot_i][suspend_i] = file,
            file object for the summary attachment,
            [boot_i]=list of missing suspends
        )
    """
    try:
        tarball = tarfile.open(filename)
    except FileNotFoundError:
        print(C.critical(f"{filename} not found!"))
        exit(1)
    except tarfile.ReadError as e:
        print(C.critical(f"{filename} cannot be opened as a tar file!"))
        print("Original error:", str(e))
        exit(1)

    possible_summary_files = [
        m.name
        for m in tarball.getmembers()
        if re.match(SUMMARY_FILE_PATTERN, m.name) is not None
    ]
    if len(possible_summary_files) == 0:
        print(
            "No attachment files matching",
            C.medium(SUMMARY_FILE_PATTERN),
            f"was found in {filename}. Ignoring",
        )
    summary_file_name = (
        possible_summary_files[0] if len(possible_summary_files) > 0 else None
    )

    summary_file = None
    if summary_file_name:
        try:
            summary_file = tarball.extractfile(summary_file_name)
        except KeyError as e:
            summary_file = None
            print(
                f"Found {summary_file_name} in {filename},"
                "but it can't be extracted, Ignoring.",
                file=sys.stderr,
            )
            print("The original error is", e, file=sys.stderr)

    # 1 based indices
    # [boot_i][suspend_i] = file object
    log_files: LogFilesByIndex = defaultdict(defaultdict)
    missing_runs: dict[int, list[int]] = defaultdict(list)

    for boot_i in range(1, num_boots + 1):
        for suspend_i in range(1, num_suspends + 1):
            individual_file_name = (
                "test_output/com.canonical.certification__stress-tests_"
                + f"suspend_cycles_{suspend_i}_reboot{boot_i}"
            )
            try:
                extracted = tarball.extractfile(individual_file_name)
                assert extracted, f"Failed to extract {individual_file_name}"
                log_files[boot_i][suspend_i] = io.TextIOWrapper(extracted)
            except KeyError:  # raised from extract when the file is missing
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
    failed_runs: RunsGroupedByIndex,
) -> RunsGroupedByError:
    """Converts RunsGroupedByIndex to RunsGroupedByError

    :param failed_runs: [fail_type][boot_i][suspend_i][msg_i] = msg
    :return: [fail_type][msg][boot_i] = suspend index array
    """
    out: RunsGroupedByError = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for fail_type, runs in failed_runs.items():
        for boot_i, suspends in runs.items():
            for suspend_i, messages in suspends.items():
                for msg in messages:
                    out[fail_type][msg][boot_i].append(suspend_i)

    return out


def print_by_err(
    failed_runs: RunsGroupedByError,
    actual_suspend_counts: dict[int, int],
    expected_n_suspends: int,
) -> None:
    """Pretty prints a RunsGroupedByError dict

    :param failed_runs: the dict to print
    :param actual_suspend_counts: [boot_i] = num suspends in this boot
    :param expected_n_suspends: expected num suspends for all boots
    """
    for fail_type, msg_group in failed_runs.items():
        print(getattr(C, fail_type.lower())(f"{fail_type} Failures"))
        for msg in msg_group:
            print(SPACE, C.bold(msg))
            for pos, (boot_i, suspends) in enumerate(msg_group[msg].items()):
                suspend_count = actual_suspend_counts[boot_i]
                if suspend_count != expected_n_suspends:
                    fail_rate_text = C.critical(
                        f"{len(suspends)}/{suspend_count}"
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


def write_suspend_output(
    write_dir: str,
    boot_i: int,
    suspend_i: int,
    meta: Meta | None,
    lines: Iterable[str],
):
    """Write a singel fwts output to a file along with extracted metadata

    :param write_dir: directory to write to
    :param boot_i: index of boot, 1-based
    :param suspend_i: index of suspend, 1-based
    :param meta: metadata extracted from fwts output
    :param lines: original lines found in the tar ball
    """
    with open(
        f"{write_dir}/boot_{boot_i}_suspend_{suspend_i}.txt",
        "w",
    ) as f:
        if meta:
            f.write(f"{' BEGIN METADATA  ':*^80}\n\n")
            f.writelines(f"{k}: {v}\n" for k, v in meta.items())
            f.write(f"\n{' END OF META, BEGIN ORIGINAL FILE ':*^80}\n\n")
        else:
            print(
                C.medium("[ WARN ]"),
                "No meta data was found",
                f"for boot {boot_i} suspend {suspend_i}",
            )

        f.writelines(lines)


def main():
    args = parse_args()
    C.no_color = args.no_color

    if args.no_transform:
        # idk why tox doesn't like this, this is super common
        transform_err_msg: Callable[[str], str] = lambda msg: msg.strip()
    else:
        transform_err_msg = default_err_msg_transform

    print(
        C.medium("[ WARN ]"),
        "The summary file might not match",
        "the number of failures found by this script.",
    )
    print(
        C.medium("[ WARN ]"),
        "Please double check since the original test case",
        "may consider some failures to be not worth reporting",
    )

    expected_num_results = args.num_boots * args.num_suspends  # noqa: N806

    print(
        C.low("[ INFO ]"),
        f"Expecting ({args.num_boots} boots * {args.num_suspends} suspends) = "
        f"{expected_num_results} results",
    )

    if args.write_individual_files:
        print(
            C.low("[ INFO ]"),
            f"Individual results will be in",
            f'"{args.write_dir}"',
        )
        if not os.path.exists(args.write_dir):
            os.mkdir(args.write_dir)

    log_files, summary_file, missing_runs = open_log_file(
        args.filename, args.num_boots, args.num_suspends
    )

    if not args.no_summary:
        if summary_file:
            print(f"\n{C.gray(' Begin Summary File '.center(80, '-'))}\n")

            for line in summary_file.readlines():
                clean_line = line.strip()
                if clean_line != "":
                    print(clean_line)
            summary_file.close()

            print(f"\n{C.gray(' End of Summary '.center(80, '-'))}\n")
        else:
            print(
                "No suspend-30-cycles-with-reboot-3-log-check attachment",
                "was found in the tarball",
            )

    # failed_runs[fail_type][boot_i][suspend_i] = set of messages
    failed_runs: RunsGroupedByIndex = {
        k: defaultdict(lambda: defaultdict(set)) for k in FAIL_TYPES
    }
    # actual_suspend_counts[boot_i] = num files actually found
    actual_suspend_counts: dict[int, int] = {}

    for boot_i in log_files:
        actual_suspend_counts[boot_i] = len(log_files[boot_i])
        for suspend_i in log_files[boot_i]:
            log_file_lines = log_files[boot_i][suspend_i].readlines()
            log_files[boot_i][suspend_i].close()

            curr_meta: Meta | None = None
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

                for fail_type in FAIL_TYPES:
                    if line.startswith(f"{fail_type} failures: "):
                        fail_count_str = line.split(":")[1].strip()
                        if fail_count_str == "NONE":
                            continue

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
                            failed_runs[fail_type][boot_i][suspend_i].add(msg)
                            error_msg_i += 1

            if args.write_individual_files:
                print(
                    f"Writing boot_{boot_i}_suspend_{suspend_i}.txt...",
                    end="\r",
                )
                write_suspend_output(
                    args.write_dir,
                    boot_i,
                    suspend_i,
                    curr_meta,
                    log_file_lines,
                )

    # done collecting, pretty print results
    n_missing_runs = sum(map(len, missing_runs.values()))
    n_failed_runs = sum(map(len, failed_runs.values()))

    if n_missing_runs == 0:
        print(
            C.ok("[ OK ]"),
            f"Found all {expected_num_results}",
            "expected log files!",
        )
        if n_failed_runs == 0:
            print(
                C.ok("[ OK ]"),
                f"No failures across {args.num_boots} boots",
                f"and {args.num_suspends} suspends!",
            )
            return
    else:
        print(
            C.critical(
                "These log files are missing, "
                + "DUT might have crashed during these jobs"
            )
        )
        for boot_i, suspend_indicies in missing_runs.items():
            print(f"- Reboot {boot_i}, suspend {str(suspend_indicies)}")

    print(f"\n{C.gray(' Begin Parsed Output '.center(80, '-'))}\n")

    print_by_err(
        group_by_err(failed_runs), actual_suspend_counts, args.num_suspends
    )


if __name__ == "__main__":
    main()

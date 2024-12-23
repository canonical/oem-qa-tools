#! /usr/bin/python3

import abc
import argparse
from collections import defaultdict
from typing import Literal
import io
import itertools
import tarfile
import re
import textwrap


space = "    "
branch = "│   "
tee = "├── "
last = "└── "

D = dict[str, dict[int, list[str]]]


class Input:
    filename: str
    group_by_err: bool
    expected_n_runs: int | None  # if specified show a warning
    verbose: bool


class C:  # color
    high = "\033[94m"
    low = "\033[95m"
    medium = "\033[93m"
    critical = "\033[91m"
    other = "\033[96m"
    ok = "\033[92m"
    end = "\033[0m"


class Log:
    @staticmethod
    def ok(*args: str):
        print(f"{C.ok}[ OK ]{C.end}", *args)

    @staticmethod
    def warn(*args: str):
        print(f"{C.medium}[ WARN ]{C.end}", *args)

    @staticmethod
    def err(*args: str):
        print(f"{C.critical}[ WARN ]{C.end}", *args)


RunIndexToMessageMap = dict[int, list[str]]
GroupedResultByIndex = dict[
    str, RunIndexToMessageMap
]  # key is fail type (for fwts it's critical, high, medium, low
# for device cmp it's lsusb, lspci, iw)
# key is index to actual message map
BootType = Literal["warm", "cold"]
TestType = Literal["fwts", "device_cmp", "renderer", "service_check"]


class SubmissionTarReader:
    def __init__(self, filepath: str) -> None:
        self.raw_tar = tarfile.open(filepath)

        slash_dot = r"\."
        warm_prefix = (
            "test_output/com.canonical.certification__warm-boot-loop-test"
        )
        cold_prefix = (
            "test_output/com.canonical.certification__cold-boot-loop-test"
        )
        # it's always the prefix followed by a multi-digit number
        # NOTE: stderr outputs are in files that end with ".err"
        warm_boot_stdout_pattern = f"{warm_prefix}[0-9]+$"
        warm_boot_stderr_pattern = f"{warm_prefix}[0-9]+{slash_dot}stderr$"

        cold_boot_stdout_pattern = f"{cold_prefix}[0-9]+$"
        cold_boot_stderr_pattern = f"{cold_prefix}[0-9]+{slash_dot}stderr$"

        members = self.raw_tar.getmembers()

        self.warm_stdout_files = [
            m.name
            for m in members
            if re.match(warm_boot_stdout_pattern, m.name) is not None
        ]
        self.warm_stderr_files = [
            m.name
            for m in members
            if re.match(warm_boot_stderr_pattern, m.name) is not None
        ]

        self.cold_stdout_files = [
            m.name
            for m in members
            if re.match(cold_boot_stdout_pattern, m.name) is not None
        ]
        self.cold_stderr_files = [
            m.name
            for m in members
            if re.match(cold_boot_stderr_pattern, m.name) is not None
        ]

    def get_files(
        self,
        boot_type: BootType,
        ch: Literal["stdout", "stderr"],
    ) -> list[str]:
        return getattr(self, f"{boot_type}_{ch}_files")

    @property
    def boot_count(self) -> int:
        if len(self.warm_stdout_files) != len(self.cold_stdout_files):
            Log.warn(
                "[ WARN ] num warm boots != num cold boots.",
                "Is the submission broken?",
            )
        return len(self.warm_stdout_files)

def parse_args() -> Input:
    p = argparse.ArgumentParser(
        description="Parses the outputs of reboot_check_test.py "
        "from a C3 submission tar file"
    )
    p.add_argument(
        "filename",
        help="path to the stress test tarball",
    )
    p.add_argument(
        "-g",
        "--group-by-err",
        dest="group_by_err",
        help=(
            "Group run-indices by error messages. "
            "Similar messages might be shown twice"
        ),
        action="store_true",
    )
    p.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        help="Whether to print detailed messages",
        action="store_true",
    )
    p.add_argument(
        "-n",
        "--num-runs",
        dest="expected_n_runs",
        help=(
            "Specify a value to show a warning when the number of boot files "
            "!= the number of runs you expect. Default=30. "
            "Note that this number applies to both cold and warm boot "
            "since checkbox doesn't use a different number for CB/WB either."
        ),
        type=int,
        default=30,
    )
    return p.parse_args()  # type: ignore


def group_fwts_output(file: io.TextIOWrapper) -> dict[str, list[str]]:
    """
    Picks out the fwts output lines from a
    single file and groups them by severity/fail_type
    """

    grouped_output = [
        (a, list(s.strip() for s in iter(b)))
        for a, b in itertools.groupby(
            file, key=lambda line: line.strip().endswith("failures:")
        )
    ]
    fail_type_to_lines: dict[str, list[str]] = {}

    for i, (is_fail_type, lines) in enumerate(grouped_output):
        # print(i, (is_fail_type, lines))
        if not is_fail_type:
            continue
        assert len(lines) > 0, "Broken fwts output"
        # if not broken, this list should look like ['High failures:'],
        # exactly 1 element
        # take the first word and use it as the key
        fail_type = lines[0].split()[0]
        # the [0] of each element should alternate between True, False
        # If False, then we have the actual lines of the
        #  immediate predecessor fail_type
        actual_messages = grouped_output[i + 1][1]
        # get rid of everything before the divider
        divider = "========================================"

        exclude_prefixes = [
            "[ OK ]",
            "Comparing devices",
            "These nodes",
            "Checking $",
            "klog",
            "oops",
            "Listing all DRM",
        ]
        exclude_suffixes = ["is connected to display!", "connected", "seconds"]
        fail_type_to_lines[fail_type] = [
            s
            for s in actual_messages
            if s != ""
            and s != divider
            and sum(1 for _ in filter(s.startswith, exclude_prefixes)) == 0
            and sum(1 for _ in filter(s.endswith, exclude_suffixes)) == 0
        ]  # also filter out empty strings

    return fail_type_to_lines


def group_renderer_check_output(file: io.TextIOWrapper):
    prefix = "[ ERR ] unity support test"
    out: dict[str, list[str]] = {}

    for line in file:
        if not line.startswith(prefix):
            continue
        out["hardware_renderer_test"] = [line]

    return out


def group_device_cmp_output(file: io.TextIOWrapper):
    regex = re.compile(r"\[ ERR \] The output of (.*) differs!")
    out: dict[str, list[str]] = {}
    for line in file:
        m = regex.match(line)
        if not m:
            continue
        device_name = m.group(1)
        out[device_name] = [line]

    return out


def group_failed_service_errors(file: io.TextIOWrapper):
    prefix = "These services failed: "
    out: dict[str, list[str]] = {}
    for line in file:
        if not line.startswith(prefix):
            continue
        out["service_check"] = [line]

    return out


def group_by_fwts_error(raw: RunIndexToMessageMap):
    timestamp_pattern = r"\[ +[0-9]+.[0-9]+\]"  # example [    3.415050]
    prefix_pattern = r"(CRITICAL|HIGH|MEDIUM|LOW|OTHER) Kernel message:"
    message_to_run_index_map = defaultdict[str, list[int]](list)
    for run_index, messages in raw.items():
        for message in messages:
            message = re.sub(
                prefix_pattern, "", re.sub(timestamp_pattern, "", message)
            ).strip()
            message_to_run_index_map[message].append(run_index)

    for v in message_to_run_index_map.values():
        v.sort()

    return message_to_run_index_map


def pretty_print(
    boot_results: dict[str, dict[int, list[str]]],
    expected_n_runs: int = 30,
    prefix: str = "",
):
    if len(boot_results) == 0:
        Log.ok("No failures!")
    for fail_type, results in boot_results.items():
        print(f"{prefix} {fail_type.replace('_', ' ')} failures".title())
        result_items = list(results.items())
        result_items.sort(key=lambda i: i[0])

        for list_idx, (run_index, messages) in enumerate(result_items):
            is_last = list_idx == len(result_items) - 1
            print(space, last if is_last else tee, "Run", run_index)

            for m_i, message in enumerate(messages):
                if m_i == len(messages) - 1:
                    print(space, space if is_last else branch, last, message)
                else:
                    print(space, space if is_last else branch, tee, message)
        if expected_n_runs != 0:
            print(
                space,
                f"Fail rate: {len(results)} / {expected_n_runs}",
            )


def short_print(
    boot_results: dict[str, dict[int, list[str]]],
    expected_n_runs: int = 30,
    prefix="",
):
    if len(boot_results) == 0:
        print(prefix, end="")
        Log.ok("No failures!")

    for fail_type, results in boot_results.items():

        failed_runs = sorted(list(results.keys()))
        print(
            f"{prefix}{getattr(C, fail_type.lower(), C.medium)}"
            f"{fail_type.replace('_', ' ').title()} failures:{C.end}"  # noqa: E501
        )
        wrapped = textwrap.wrap(str(failed_runs))
        print(f"{prefix}{space}- Failed runs: {wrapped[0]}")
        prefix_len = len(f"{prefix}{space}- Failed runs: ")
        for line in wrapped[1:]:
            print(" " * prefix_len, line)
        if expected_n_runs != 0:
            print(
                f"{prefix}{space}- Fail rate: "
                f"{len(failed_runs)}/{expected_n_runs}"
            )


def group_by_index(reader: SubmissionTarReader):
    out: dict[
        BootType,
        dict[TestType, GroupedResultByIndex],
    ] = {"warm": {}, "cold": {}}

    for boot_type in "warm", "cold":
        prefix = (
            "test_output/com.canonical.certification__"
            f"{boot_type}-boot-loop-test"
        )

        # it's always the prefix followed by a multi-digit number
        # NOTE: This assumes everything useful is on stdout.
        # NOTE: stderr outputs are in files that end with ".err"
        fwts_results: D = defaultdict(
            lambda: defaultdict(list)
        )  # {fail_type: {run_index: list[actual_message]}}
        renderer_test_results: D = defaultdict(lambda: defaultdict(list))
        device_cmp_results: D = defaultdict(lambda: defaultdict(list))
        failed_service_results: D = defaultdict(lambda: defaultdict(list))

        for stdout_filename in reader.get_files(boot_type, "stdout"):
            run_index = int(stdout_filename[len(prefix) :])  # noqa: E203
            file = reader.raw_tar.extractfile(stdout_filename)
            assert file

            # looks weird but allows f to close itself
            with io.TextIOWrapper(file) as f:
                # key is fail type, value is list of actual err messages
                grouped_fwts_output = group_fwts_output(f)
                for fail_type, messages in grouped_fwts_output.items():
                    for msg in messages:
                        fwts_results[fail_type][run_index].append(msg.strip())

        for stderr_filename in reader.get_files(boot_type, "stderr"):
            run_index = int(
                stderr_filename[len(prefix) : -7]  # noqa: E203,
            )  # cut off .stderr
            file = reader.raw_tar.extractfile(stderr_filename)
            if not file:
                continue

            with io.TextIOWrapper(file) as f:
                grouped_device_out = group_device_cmp_output(f)
                for device, messages in grouped_device_out.items():
                    for msg in messages:
                        device_cmp_results[device][run_index].append(
                            msg.strip()
                        )
                f.seek(0)
                for key, messages in group_renderer_check_output(f).items():
                    for msg in messages:
                        renderer_test_results[key][run_index].append(
                            msg.strip()
                        )
                f.seek(0)
                for key, messages in group_failed_service_errors(f).items():
                    for msg in messages:
                        failed_service_results[key][run_index].append(
                            msg.strip()
                        )

        # sort by boot number
        out[boot_type]["fwts"] = fwts_results
        out[boot_type]["device_cmp"] = device_cmp_results
        out[boot_type]["renderer"] = renderer_test_results
        out[boot_type]["service_check"] = failed_service_results

    return out


def main():
    args = parse_args()
    reader = SubmissionTarReader(args.filename)
    out = group_by_index(reader)

    for test in "fwts", "device_cmp", "renderer", "service_check":
        cold_result = out["cold"][test]
        warm_result = out["warm"][test]

        if (len(cold_result) + len(warm_result)) == 0:
            print()
            Log.ok(f"No {test} failures")
            continue

        if test == "fwts":
            print(f"\n{f' FWTS failures ':=^80}\n")

            if args.verbose:
                print(f"\n{f' Verbose cold boot FWTS results ':-^80}\n")
                pretty_print(cold_result)
                print(f"\n{f' Verbose warm boot FWTS results ':-^80}\n")
                pretty_print(warm_result)
                continue

            if not args.group_by_err:
                print(f"\n{f' Cold boot fwts failures ':-^80}\n")
                short_print(cold_result)
                print(f"\n{f' Warm boot fwts failures ':-^80}\n")
                short_print(warm_result)
                continue

            # key is message, value is {cold: [index], warm: index}
            for fail_type in cold_result:
                print(
                    f"{getattr(C, fail_type.lower())}"
                    f"FWTS {fail_type} errors:{C.end}"
                )
                regrouped_cold = group_by_fwts_error(cold_result[fail_type])
                regrouped_warm = group_by_fwts_error(warm_result[fail_type])

                for err_msg in regrouped_cold:
                    print(space, err_msg)
                    buffer = {
                        err_msg: {
                            "cold": regrouped_cold[err_msg],
                            "warm": regrouped_warm[err_msg],
                        }
                    }
                    for b in "cold", "warm":
                        wrapped = textwrap.wrap(
                            str(buffer[err_msg][b]), width=50
                        )
                        shared_prefix = " ".join((space, space))
                        line1 = f"{b.capitalize()} Failures: "
                        print(shared_prefix, tee, line1, wrapped[0])

                        for line in wrapped[1:]:
                            print(
                                shared_prefix, branch, len(line1) * " ", line
                            )

                        print(
                            space,
                            space,
                            last if b == "warm" else tee,
                            f"{b.capitalize()} failure rate:",
                            f"{len(buffer[err_msg][b])} / {reader.boot_count}",
                        )
                    print("")  # new line
        elif test == "device_cmp":
            if args.verbose:
                print(f"\n{f' Verbose cold boot device comparison ':-^80}\n")
                pretty_print(cold_result)
                print(f"\n{f' Verbose warm boot device comparison ':-^80}\n")
                pretty_print(warm_result)
                continue
            print(f"\n{f' Device comparison failures ':=^80}\n")
            if len(cold_result) > 0:
                print("Cold boot:")
                short_print(cold_result, prefix=space)
            if len(warm_result) > 0:
                print("Warm boot:")
                short_print(out["warm"]["device_cmp"], prefix=space)

        elif test == "renderer":
            if args.verbose:
                print(f"\n{f' Verbose cold boot renderer test ':-^80}\n")
                pretty_print(cold_result)
                print(f"\n{f' Verbose warm boot renderer test ':-^80}\n")
                pretty_print(warm_result)
                continue
            print(f"\n{f' Renderer test failures ':=^80}\n")
            if len(cold_result) > 0:
                print("Cold boot:")
                short_print(cold_result, prefix=space)
            if len(warm_result) > 0:
                print("Warm boot:")
                short_print(out["warm"]["renderer"], prefix=space)

        elif test == "service_check":
            if args.verbose:
                print(
                    f"\n{f' Verbose cold boot failed services test ':-^80}\n"
                )
                pretty_print(cold_result)
                print(
                    f"\n{f' Verbose warm boot failed services test ':-^80}\n"
                )
                pretty_print(warm_result)
                continue
            print(f"\n{f' Found failed services ':=^80}\n")
            if len(cold_result) > 0:
                print("Cold boot:")
                short_print(cold_result, prefix=space)
            if len(warm_result) > 0:
                print("Warm boot:")
                short_print(out["warm"]["service_check"], prefix=space)


if __name__ == "__main__":
    main()

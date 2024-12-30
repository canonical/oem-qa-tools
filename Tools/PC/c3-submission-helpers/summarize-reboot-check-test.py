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
            f"{prefix}{getattr(Color, fail_type.lower(), Color.medium)}"
            f"{fail_type.replace('_', ' ').title()} failures:{Color.end}"
        )
        wrapped = textwrap.wrap(str(failed_runs))
        print(f"{prefix}{space}- Failed runs: {wrapped[0]}")
        prefix_len = len(f"{prefix}{space}- Failed runs: ")
        for line in wrapped[1:]:
            print(" " * prefix_len, line)
        if expected_n_runs != 0:
            print(
                f"{prefix}{space}- Fail rate:",
                f"{len(failed_runs)}/{expected_n_runs}",
            )


class Input:
    filename: str
    group_by_err: bool
    expected_n_runs: int | None  # if specified show a warning
    verbose: bool


class Color:
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
        print(f"{Color.ok}[ OK ]{Color.end}", *args)

    @staticmethod
    def warn(*args: str):
        print(f"{Color.medium}[ WARN ]{Color.end}", *args)

    @staticmethod
    def err(*args: str):
        print(f"{Color.critical}[ WARN ]{Color.end}", *args)


RunIndexToMessageMap = dict[int, list[str]]
GroupedResultByIndex = dict[
    str, RunIndexToMessageMap
]  # key is fail type (for fwts it's critical, high, medium, low
# for device cmp it's lsusb, lspci, iw)
# key is index to actual message map
BootType = Literal["warm", "cold"]
TestType = Literal["fwts", "device comparison", "renderer", "service check"]


class SubmissionTarReader:
    def __init__(self, filepath: str) -> None:
        self.raw_tar = tarfile.open(filepath)

        slash_dot = r"\."
        warm_prefix = "test_output/com.canonical.certification__warm-boot-loop-test"  # noqa: E501
        cold_prefix = "test_output/com.canonical.certification__cold-boot-loop-test"  # noqa: E501
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


class TestResultPrinter(abc.ABC):

    name: TestType

    def __init__(
        self,
        warm_results: GroupedResultByIndex,
        cold_results: GroupedResultByIndex,
        reader: SubmissionTarReader,
    ) -> None:
        self.warm_results = warm_results
        self.cold_results = cold_results
        self.reader = reader

    def print_verbose(self):
        print(f"\n{f' Verbose cold boot {self.name} results ':-^80}\n")
        pretty_print(self.cold_results)
        print(f"\n{f' Verbose warm boot device comparison ':-^80}\n")
        pretty_print(self.warm_results)

    def print_by_err(self):
        # if not implemented, just do this
        self.print_by_index()

    def print_by_index(self):
        print("Cold boot:")
        if len(self.cold_results) > 0:
            short_print(self.cold_results, prefix=space)
        else:
            print(space + "No failures!")

        print("Warm boot:")
        if len(self.warm_results) > 0:
            short_print(self.warm_results, prefix=space)
        else:
            print(space + "No failures!")


class FwtsPrinter(TestResultPrinter):

    name = "fwts"

    def __init__(
        self,
        warm_results: GroupedResultByIndex,
        cold_results: GroupedResultByIndex,
        reader: SubmissionTarReader,
    ) -> None:
        super().__init__(warm_results, cold_results, reader)

    def print_by_err(self):
        # key is message, value is {cold: [index], warm: [index]}
        for fail_type in self.cold_results:
            print(
                f"{getattr(Color, fail_type.lower())}"
                f"FWTS {fail_type} errors:{Color.end}"
            )
            regrouped_cold = self._group_by_fwts_error(
                self.cold_results[fail_type]
            )
            regrouped_warm = self._group_by_fwts_error(
                self.warm_results[fail_type]
            )

            all_err_msg = set(regrouped_cold.keys()).union(
                set(regrouped_warm.keys())
            )

            for err_msg in all_err_msg:
                print(space, f"\033[1m{err_msg}\033[0m")
                buffer = {
                    err_msg: {
                        "cold": regrouped_cold.get(err_msg, []),
                        "warm": regrouped_warm.get(err_msg, []),
                    }
                }
                for b in "cold", "warm":
                    wrapped = textwrap.wrap(
                        str(buffer[err_msg][b]),
                        width=50,
                    )
                    num_fails = len(buffer[err_msg][b])
                    shared_prefix = " ".join((space, space))
                    if num_fails > 0:
                        line1 = f"{b.capitalize()} failures: "
                        print(shared_prefix, tee, line1, wrapped[0])
                    else:
                        line1 = f"No {b} boot failures"
                        print(shared_prefix, tee, line1)
                        continue

                    for line in wrapped[1:]:
                        print(
                            shared_prefix,
                            branch,
                            len(line1) * " ",
                            line,
                        )
                    print(
                        space,
                        space,
                        last if b == "warm" else tee,
                        f"{b.capitalize()} failure rate:",
                        f"{num_fails} / {self.reader.boot_count}",
                    )

    def print_by_index(self):
        print(f"\n{f' Cold boot fwts failures ':-^80}\n")
        short_print(self.cold_results)
        print(f"\n{f' Warm boot fwts failures ':-^80}\n")
        short_print(self.warm_results)

    def print_verbose(self):
        print(f"\n{f' Verbose cold boot FWTS results ':-^80}\n")
        pretty_print(self.cold_results)
        print(f"\n{f' Verbose warm boot FWTS results ':-^80}\n")
        pretty_print(self.warm_results)

    def _group_by_fwts_error(self, raw: RunIndexToMessageMap):
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


class DeviceComparisonPrinter(TestResultPrinter):
    name = "device comparison"

    def __init__(
        self,
        warm_results: GroupedResultByIndex,
        cold_results: GroupedResultByIndex,
        reader: SubmissionTarReader,
    ) -> None:
        super().__init__(warm_results, cold_results, reader)

    def print_by_err(self):
        super().print_by_index()

    def print_verbose(self):
        super().print_verbose()


class ServiceCheckPrinter(TestResultPrinter):
    name = "service check"

    def __init__(
        self,
        warm_results: GroupedResultByIndex,
        cold_results: GroupedResultByIndex,
        reader: SubmissionTarReader,
    ) -> None:
        super().__init__(warm_results, cold_results, reader)

    def print_by_index(self):
        super().print_by_index()

    def print_verbose(self):
        super().print_verbose()


class RendererCheckPrinter(TestResultPrinter):
    name = "renderer"

    def __init__(
        self,
        warm_results: GroupedResultByIndex,
        cold_results: GroupedResultByIndex,
        reader: SubmissionTarReader,
    ) -> None:
        super().__init__(warm_results, cold_results, reader)

    def print_by_index(self):
        super().print_by_index()

    def print_verbose(self):
        super().print_verbose()


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


def group_device_comparison_output(file: io.TextIOWrapper):
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
    searching_services = False
    for line in file:
        if line.startswith(prefix):
            first_service = line.removeprefix(prefix)
            out["service_check"] = [first_service]
            searching_services = True
            continue
        if searching_services:
            if ".service" in line:
                out["service_check"].append(line)

    return out


def group_by_index(reader: SubmissionTarReader):
    out: dict[
        BootType,
        dict[TestType, GroupedResultByIndex],
    ] = {"warm": {}, "cold": {}}

    for boot_type in "warm", "cold":
        prefix = (
            "test_output/com.canonical.certification__"
            + f"{boot_type}-boot-loop-test"
        )

        fwts_results: GroupedResultByIndex = defaultdict(
            lambda: defaultdict(list)
        )  # {fail_type: {run_index: list[actual_message]}}
        renderer_test_results: GroupedResultByIndex = defaultdict(
            lambda: defaultdict(list)
        )
        device_comparison_results: GroupedResultByIndex = defaultdict(
            lambda: defaultdict(list)
        )
        failed_service_results: GroupedResultByIndex = defaultdict(
            lambda: defaultdict(list)
        )

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
                grouped_device_out = group_device_comparison_output(f)
                for device, messages in grouped_device_out.items():
                    for msg in messages:
                        device_comparison_results[device][run_index].append(
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

        out[boot_type]["fwts"] = fwts_results
        out[boot_type]["device comparison"] = device_comparison_results
        out[boot_type]["renderer"] = renderer_test_results
        out[boot_type]["service check"] = failed_service_results

    return out


def main():
    args = parse_args()
    reader = SubmissionTarReader(args.filename)
    out = group_by_index(reader)

    printer_classes: dict[TestType, type[TestResultPrinter]] = {
        klass.name: klass
        for klass in (
            FwtsPrinter,
            DeviceComparisonPrinter,
            RendererCheckPrinter,
            ServiceCheckPrinter,
        )
    }

    for test in printer_classes:
        cold_results = out["cold"][test]
        warm_results = out["warm"][test]

        printer = printer_classes[test](warm_results, cold_results, reader)
        print(f"\n{f' {printer.name.capitalize()} failures ':=^80}\n")
        if (len(cold_results) + len(warm_results)) == 0:
            Log.ok(f"No {printer.name} failures")
            continue

        if args.verbose:
            printer.print_verbose()
        elif args.group_by_err:
            printer.print_by_err()
        else:
            printer.print_by_index()


if __name__ == "__main__":
    main()

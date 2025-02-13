#! /usr/bin/env python3

import abc
import argparse
from collections import defaultdict, Counter
from typing import Callable, Literal
import io
import itertools
import tarfile
import re
import textwrap


SPACE = "    "
BRANCH = "│   "
TEE = "├── "
LAST = "└── "


class Input:
    filename: str
    group_by_err: bool
    expected_n_runs: int  # if specified show a warning
    verbose: bool
    no_color: bool


class Color:
    high = "\033[94m"
    low = "\033[95m"
    medium = "\033[93m"
    critical = "\033[91m"
    other = "\033[96m"
    ok = "\033[92m"
    end = "\033[0m"
    bold = "\033[1m"


class Log:
    @staticmethod
    def ok(*args: str):
        print(f"{Color.ok}[ OK ]{Color.end}", *args)

    @staticmethod
    def warn(*args: str):
        print(f"{Color.medium}[ WARN ]{Color.end}", *args)

    @staticmethod
    def err(*args: str):
        print(f"{Color.critical}[ ERR ]{Color.end}", *args)


RunIndexToMessageMap = dict[int, list[str]]
GroupedResultByIndex = dict[
    str, RunIndexToMessageMap
]  # key is fail type (for fwts it's critical, high, medium, low
# for device cmp it's lsusb, lspci, iw)
# value is index to actual message map
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

    def get_file(
        self,
        run_index: int,
        ch: Literal["stdout", "stderr"],
        boot_type: BootType,
    ) -> io.TextIOWrapper | None:
        prefix = (
            "test_output/com.canonical.certification__"
            + f"{boot_type}-boot-loop-test"
        )
        if ch == "stderr":
            suffix = ".stderr"
        else:
            suffix = ""

        try:
            raw_file = self.raw_tar.extractfile(f"{prefix}{run_index}{suffix}")
        except KeyError:
            return None
        if not raw_file:
            return None

        return io.TextIOWrapper(raw_file)

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
        reader: SubmissionTarReader,
        expected_n_runs: int = 30,
    ) -> None:
        self.warm_results: GroupedResultByIndex = defaultdict(
            lambda: defaultdict(list)
        )
        self.cold_results: GroupedResultByIndex = defaultdict(
            lambda: defaultdict(list)
        )
        self.reader = reader
        self.expected_n_runs = expected_n_runs
        self._group_by_index()

    def print_verbose(self):
        print(f"\n{f' Verbose cold boot {self.name} results ':-^80}\n")
        self._pretty_print(self.cold_results, self.expected_n_runs)
        print(f"\n{f' Verbose warm boot {self.name} results ':-^80}\n")
        self._pretty_print(self.warm_results, self.expected_n_runs)

    def print_by_err(self):
        self._default_print_by_err()

    def print_by_index(self):
        print("Cold boot:")
        if len(self.cold_results) > 0:
            self._short_print(self.cold_results, prefix=SPACE)
        else:
            print(SPACE + "No failures!")

        print("Warm boot:")
        if len(self.warm_results) > 0:
            self._short_print(self.warm_results, prefix=SPACE)
        else:
            print(SPACE + "No failures!")

    def _default_title_transform(self, fail_type: str):
        color = getattr(Color, fail_type.lower(), Color.medium)
        return (
            f"{color}{fail_type.lower().replace("_", " ").capitalize()}"
            f" errors:{Color.end}"
        )

    def _default_err_msg_transform(self, msg: str):
        return msg

    def _default_print_by_err(
        self,
        title_transform: None | Callable[[str], str] = None,
        err_msg_transform: None | Callable[[str], str] = None,
    ):
        fail_types = (
            self.cold_results
            if len(self.cold_results) > len(self.warm_results)
            else self.warm_results
        ).keys()

        for fail_type in fail_types:
            print(
                title_transform(fail_type)
                if title_transform
                else self._default_title_transform(fail_type)
            )
            regrouped_cold = self._group_by_err(
                self.cold_results.get(fail_type, {}), err_msg_transform
            )
            regrouped_warm = self._group_by_err(
                self.warm_results.get(fail_type, {}), err_msg_transform
            )

            all_err_msg = set(regrouped_cold.keys()).union(
                set(regrouped_warm.keys())
            )

            for err_msg in all_err_msg:
                print(SPACE, f"{Color.bold}{err_msg}{Color.end}")

                buffer = {
                    err_msg: {
                        "cold": regrouped_cold.get(err_msg, []),
                        "warm": regrouped_warm.get(err_msg, []),
                    }
                }

                for boot_type in "cold", "warm":
                    wrapped = textwrap.wrap(
                        str(sorted(buffer[err_msg][boot_type])),
                        width=50,
                    )
                    n_fails = len(buffer[err_msg][boot_type])
                    shared_prefix = " ".join((SPACE, SPACE))

                    if n_fails > 0:
                        line_1 = f"{boot_type.capitalize()} failures: "
                        print(shared_prefix, TEE, line_1, wrapped[0])
                    else:
                        line_1 = f"No {boot_type} boot failures!"
                        print(
                            shared_prefix,
                            TEE if boot_type == "cold" else LAST,
                            line_1,
                        )
                        continue

                    for line in wrapped[1:]:
                        print(
                            shared_prefix,
                            BRANCH,
                            len(line_1) * " ",
                            line,
                        )
                    print(
                        SPACE,
                        SPACE,
                        LAST if boot_type == "warm" else TEE,
                        f"{boot_type.capitalize()} failure rate:",
                        f"{n_fails} / {self.reader.boot_count}",
                    )

    @abc.abstractmethod
    def _group_by_index(self): ...

    def _group_by_err(
        self,
        index_results: RunIndexToMessageMap,
        msg_transform: None | Callable[[str], str] = None,
    ):
        out: dict[str, list[int]] = {}

        for idx, messages in index_results.items():
            for msg in messages:
                if msg_transform:
                    msg_transformed = msg_transform(msg)
                else:
                    msg_transformed = msg.strip()

                if msg_transformed in out:
                    out[msg_transformed].append(idx)
                else:
                    out[msg_transformed] = [idx]

        return out

    def _pretty_print(
        self,
        boot_results: dict[str, dict[int, list[str]]],
        expected_n_runs: int,
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
                print(SPACE, LAST if is_last else TEE, "Run", run_index)

                for m_i, message in enumerate(messages):
                    if m_i == len(messages) - 1:
                        print(
                            SPACE, SPACE if is_last else BRANCH, LAST, message
                        )
                    else:
                        print(
                            SPACE, SPACE if is_last else BRANCH, TEE, message
                        )
            if expected_n_runs != 0:
                print(
                    SPACE,
                    f"Fail rate: {len(results)} / {expected_n_runs}",
                )

    def _short_print(
        self,
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
            wrapped = textwrap.wrap(str(failed_runs), width=50)
            print(f"{prefix}{SPACE}- Failed runs: {wrapped[0]}")
            prefix_len = len(f"{prefix}{SPACE}- Failed runs: ")
            for line in wrapped[1:]:
                print(" " * prefix_len, line)
            if expected_n_runs != 0:
                print(
                    f"{prefix}{SPACE}- Fail rate:",
                    f"{len(failed_runs)}/{expected_n_runs}",
                )


class FwtsPrinter(TestResultPrinter):
    name = "fwts"

    def print_by_err(self):
        def title_transform(fail_type: str):
            return (
                f"{getattr(Color, fail_type.lower())}"
                f"FWTS {fail_type} errors:{Color.end}"
            )

        def err_msg_transform(msg: str):
            prefix_pattern = (
                r"(CRITICAL|HIGH|MEDIUM|LOW|OTHER) Kernel message:"
            )
            timestamp_pattern = (
                r"\[ +[0-9]+.[0-9]+\]"  # example [    3.415050]
            )
            return re.sub(
                prefix_pattern, "", re.sub(timestamp_pattern, "", msg)
            ).strip()

        self._default_print_by_err(title_transform, err_msg_transform)

    def _group_by_index(self):
        for boot_type in ("cold", "warm"):
            res = (
                self.cold_results if boot_type == "cold" else self.warm_results
            )
            for run_index in range(1, self.reader.boot_count + 1):
                f = self.reader.get_file(run_index, "stdout", boot_type)
                if not f:
                    continue
                with f:
                    grouped_output = [
                        (a, list(s.strip() for s in iter(b)))
                        for a, b in itertools.groupby(
                            f,
                            key=lambda line: line.strip().endswith(
                                "failures:"
                            ),
                        )
                    ]

                    for i, (is_fail_type, lines) in enumerate(grouped_output):
                        if not is_fail_type:
                            continue
                        assert len(lines) > 0, "Broken fwts output"
                        # this list should look like ['High failures:'],
                        # with exactly 1 element
                        # take the first word and use it as the key
                        fail_type = lines[0].split()[0]
                        # the [0] of each element should alternate between T,F
                        # If False, then we have the actual lines of the
                        # immediate predecessor fail_type
                        actual_messages = grouped_output[i + 1][1]
                        # get rid of everything before the divider
                        divider = "========================================"

                        # this is kinda dumb but fwts output is mixed with
                        # output from other tests
                        exclude_prefixes = [
                            "[ OK ]",
                            "Comparing devices",
                            "These nodes",
                            "Checking $",
                            "klog",
                            "oops",
                            "Listing all DRM",
                            "$DISPLAY is not set",
                            "- ",  # the drm list bullet
                            "Checking if DUT has reached",
                            "Graphical target reached!",
                        ]
                        exclude_suffixes = [
                            "is connected to display!",
                            "connected",
                            "seconds",
                            "graphical.target was not reached",
                        ]
                        res[fail_type][run_index] = [
                            s
                            for s in actual_messages
                            if s != ""
                            and s != divider
                            and all(
                                not s.startswith(prefix)
                                for prefix in exclude_prefixes
                            )
                            and all(
                                not s.endswith(suffix)
                                for suffix in exclude_suffixes
                            )
                        ]  # also filter out empty strings


class DeviceComparisonPrinter(TestResultPrinter):
    name = "device comparison"

    def _group_by_index(self):
        for boot_type in ("cold", "warm"):
            res = (
                self.cold_results if boot_type == "cold" else self.warm_results
            )
            for run_index in range(1, self.reader.boot_count + 1):
                f = self.reader.get_file(run_index, "stderr", boot_type)
                if not f:
                    continue
                with f:
                    regex = re.compile(
                        r"\[ ERR \] The output of (.*) differs!"
                    )

                    lines = f.readlines()
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        m = regex.match(line)

                        if not m:
                            i += 1
                            continue

                        device_name = m.group(1)
                        expected: list[str] = []
                        actual: list[str] = []

                        i += 2
                        while i < len(lines):
                            if lines[i].startswith("Actual"):
                                break

                            expected.append(lines[i].strip())
                            i += 1

                        i += 1
                        while i < len(lines):
                            if lines[i].startswith("End of"):
                                break

                            actual.append(lines[i].strip())
                            i += 1

                        diff = list(Counter(expected) - Counter(actual))
                        diff.sort()

                        res[device_name][run_index] = [
                            line.strip()
                            + f" Diff: {Color.critical}"
                            + f"{re.sub(r'\s\s+', " ", str(diff))}"
                            + Color.end
                        ]
                        i += 1


class ServiceCheckPrinter(TestResultPrinter):
    name = "service check"

    def _group_by_index(self):
        for boot_type in ("cold", "warm"):
            res = (
                self.cold_results if boot_type == "cold" else self.warm_results
            )
            for run_index in range(1, self.reader.boot_count + 1):
                f = self.reader.get_file(run_index, "stderr", boot_type)
                if not f:
                    continue
                with f:
                    msg_prefix = "These services failed: "
                    searching_services = False

                    for line in f:
                        if line.startswith(msg_prefix):
                            first_service = line.removeprefix(msg_prefix)
                            res["service check"][run_index] = [first_service]
                            searching_services = True
                            continue
                        if searching_services:
                            if ".service" in line:
                                res["service check"][run_index].append(line)


class RendererCheckPrinter(TestResultPrinter):
    name = "renderer"

    def _group_by_index(self):
        unity_fail_prefix = "[ ERR ] unity support test"
        graphical_target_fail_prefix = (
            "[ ERR ] systemd's graphical.target was not reached"
        )

        for boot_type in ("cold", "warm"):
            res = (
                self.cold_results if boot_type == "cold" else self.warm_results
            )
            for run_index in range(1, self.reader.boot_count + 1):
                f = self.reader.get_file(run_index, "stderr", boot_type)
                if not f:
                    continue
                with f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(unity_fail_prefix):
                            res["Unity support"][run_index] = [line]
                        elif line.startswith(graphical_target_fail_prefix):
                            res["Graphical target not reached"][run_index] = [
                                line
                            ]


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
    p.add_argument(
        "--no-color",
        help="Removes all colors and styles",
        action="store_true",
    )
    return p.parse_args()  # type: ignore


def main():
    args = parse_args()
    reader = SubmissionTarReader(args.filename)

    if args.no_color:
        for prop in dir(Color):
            if prop.startswith("__") and type(getattr(Color, prop)) is not str:
                continue
            setattr(Color, prop, "")

    print(
        "Checking if the tar file has the expected number of runs...", end=" "
    )
    if reader.boot_count != args.expected_n_runs:
        Log.err(
            f"Expected {args.expected_n_runs} runs,",
            f"but got {reader.boot_count}",
        )
    else:
        Log.ok(f"Found the expected {args.expected_n_runs} runs.")

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
        printer = printer_classes[test](reader, args.expected_n_runs)
        print(f"\n{f' {printer.name.capitalize()} failures ':=^80}\n")

        if (len(printer.cold_results) + len(printer.warm_results)) == 0:
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

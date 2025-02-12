#! /usr/bin/python3

import abc
import argparse
from collections import defaultdict
from typing import Callable, Literal
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
        wrapped = textwrap.wrap(str(failed_runs), width=50)
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


def group_by_err(
    index_results: RunIndexToMessageMap,
    msg_transform: None | Callable[[str], str] = None,
):
    out: dict[str, list[int]] = {}

    for idx, messages in index_results.items():
        for msg in messages:
            msg_transformed = msg_transform(msg) if msg_transform else msg
            if msg_transformed in out:
                out[msg_transformed].append(idx)
            else:
                out[msg_transformed] = [idx]

    return out


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
        expected_n_runs: int,
    ) -> None:
        self.warm_results = warm_results
        self.cold_results = cold_results
        self.reader = reader
        self.expected_n_runs = expected_n_runs

    def print_verbose(self):
        print(f"\n{f' Verbose cold boot {self.name} results ':-^80}\n")
        pretty_print(self.cold_results, self.expected_n_runs)
        print(f"\n{f' Verbose warm boot {self.name} results ':-^80}\n")
        pretty_print(self.warm_results, self.expected_n_runs)

    def print_by_err(self):
        self._default_print_by_err()

    def _default_title_transform(self, fail_type: str):
        return (
            f"{getattr(Color, fail_type.lower(), Color.medium)}"
            f"{fail_type} errors:{Color.end}"
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
            regrouped_cold = group_by_err(
                self.cold_results.get(fail_type, {}), err_msg_transform
            )
            regrouped_warm = group_by_err(
                self.warm_results.get(fail_type, {}), err_msg_transform
            )

            all_err_msg = set(regrouped_cold.keys()).union(
                set(regrouped_warm.keys())
            )

            for err_msg in all_err_msg:
                print(space, f"{Color.bold}{err_msg}{Color.end}")

                buffer = {
                    err_msg: {
                        "cold": regrouped_cold.get(err_msg, []),
                        "warm": regrouped_warm.get(err_msg, []),
                    }
                }

                for b in "cold", "warm":
                    wrapped = textwrap.wrap(
                        str(sorted(buffer[err_msg][b])),
                        width=50,
                    )
                    n_fails = len(buffer[err_msg][b])
                    shared_prefix = " ".join((space, space))

                    if n_fails > 0:
                        line1 = f"{b.capitalize()} failures: "
                        print(shared_prefix, tee, line1, wrapped[0])
                    else:
                        line1 = f"No {b} boot failures!"
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
                        f"{n_fails} / {self.reader.boot_count}",
                    )

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
        expected_n_runs=30,
    ) -> None:
        super().__init__(warm_results, cold_results, reader, expected_n_runs)

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


class DeviceComparisonPrinter(TestResultPrinter):
    name = "device comparison"


class ServiceCheckPrinter(TestResultPrinter):
    name = "service check"


class RendererCheckPrinter(TestResultPrinter):
    name = "renderer"


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
    unity_fail_prefix = "[ ERR ] unity support test"
    graphical_target_fail_prefix = (
        "[ ERR ] systemd's graphical.target was not reached"
    )
    out: dict[str, list[str]] = {}

    for line in file:
        if line.startswith(unity_fail_prefix):
            out["Unity support"] = [line]
        elif line.startswith(graphical_target_fail_prefix):
            out["Graphical target not reached"] = [line]

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

    if args.no_color:
        for prop in dir(Color):
            if prop.startswith("__") and type(getattr(Color, prop)) is not str:
                continue
            setattr(Color, prop, "")

    if reader.boot_count != args.expected_n_runs:
        Log.err(
            f"Expected {args.expected_n_runs} runs,",
            f"but got {reader.boot_count}",
        )
    else:
        Log.ok(f"COUNT OK! Found the expected {args.expected_n_runs} runs.")

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

        printer = printer_classes[test](
            warm_results, cold_results, reader, args.expected_n_runs
        )
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

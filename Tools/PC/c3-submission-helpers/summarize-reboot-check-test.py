#! /usr/bin/python3

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


RunIndexToMessageMap = dict[int, list[str]]
GroupedResultByIndex = dict[
    str, RunIndexToMessageMap
]  # key is fail type (for fwts it's critical, high, medium, low
# for device cmp it's lsusb, lspci, iw)
# key is index to actual message map


def parse_args() -> Input:
    p = argparse.ArgumentParser()
    p.add_argument(
        "filename",
        help="path to the stress test tarball",
    )
    p.add_argument(
        "-g",
        "--group-by-err",
        dest="group_by_err",
        help="Group run-indicies by error messages. Similar messages might be shown twice",
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
            "Note that this number applies to both CB and WB since checkbox doesn't use a different number for CB/WB either."
        ),
        type=int,
        default=30,
    )
    return p.parse_args()  # type: ignore


def get_fwts_lines(file: io.TextIOWrapper) -> list[str]:
    fwts_output_lines: list[str] = []
    should_include = False
    for line in file:
        if line.startswith("## Checking FWTS log failures..."):
            should_include = True
            continue
        if line.startswith("## Comparing the devices..."):
            break
        if should_include:
            fwts_output_lines.append(line.strip())
    return fwts_output_lines


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
        # eactly 1 element
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
        ]
        exclude_suffixes = ["is connected to display!"]
        fail_type_to_lines[fail_type] = [
            s
            for s in actual_messages
            if s != ""
            and s != divider
            and sum(1 for _ in filter(s.startswith, exclude_prefixes)) == 0
            and sum(1 for _ in filter(s.endswith, exclude_suffixes)) == 0
        ]  # also filter out empty strings

    return fail_type_to_lines


def group_device_cmp_output(file: io.TextIOWrapper) -> dict[str, list[str]]:
    regex = re.compile(r"\[ ERR \] The output of (.*) differs!")
    out = {}
    for line in file:
        m = regex.match(line)
        if not m:
            continue
        device_name = m.group(1)
        out[device_name] = ["line"]

    return out


def group_by_error(raw: RunIndexToMessageMap):
    timestamp_pattern = r"\[ +[0-9]+.[0-9]+\]"  # example [    3.415050]
    message_to_run_index_map = defaultdict[str, list[int]](list)
    for run_index, messages in raw.items():
        for message in messages:
            message = re.sub(timestamp_pattern, "", message)
            message_to_run_index_map[message].append(run_index)

    for v in message_to_run_index_map.values():
        v.sort()

    return message_to_run_index_map


def pretty_print(
    boot_results: dict[str, dict[int, list[str]]],
    expected_n_runs=30,
    prefix="",
):
    for fail_type, results in boot_results.items():
        print(f"{prefix} {fail_type} failures".title())
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
    expected_n_runs=30,
):
    for fail_type, results in boot_results.items():
        failed_runs = sorted(list(results.keys()))
        print(
            f"{getattr(C, fail_type.lower(), C.medium)}{fail_type} failures:{C.end}"
        )
        print(space + f"\n{space}".join(textwrap.wrap(str(failed_runs))))
        if expected_n_runs != 0:
            print(f"{space}- Fail rate: {len(failed_runs)}/{expected_n_runs}")


def main():
    args = parse_args()
    submission = tarfile.open(args.filename)

    out: dict[
        Literal["warm", "cold"],
        dict[Literal["fwts", "device_cmp"], GroupedResultByIndex],
    ] = {"warm": {}, "cold": {}}

    warm_boot_count = 0
    cold_boot_count = 0
    for boot_type in "warm", "cold":
        prefix = f"test_output/com.canonical.certification__{boot_type}-boot-loop-test"
        # it's always the prefix followed by a multi-digit number
        # NOTE: This assumes everything useful is on stdout.
        # NOTE: stderr outputs are in files that end with ".err"
        boot_stdout_pattern = f"{prefix}[0-9]+$"
        slash_dot = r"\."
        boot_stderr_pattern = f"{prefix}[0-9]+{slash_dot}stderr$"
        fwts_results: dict[str, dict[int, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )  # {fail_type: {run_index: list[actual_message]}}
        device_cmp_results: dict[str, dict[int, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for stdout_filename in [
            m.name
            for m in submission.getmembers()
            if re.match(boot_stdout_pattern, m.name) is not None
        ]:
            if boot_type == "warm":
                warm_boot_count += 1
            else:
                cold_boot_count += 1

            run_index = int(stdout_filename[len(prefix) :])
            file = submission.extractfile(stdout_filename)
            if not file:
                continue

            # looks weird but allows f to close itself
            with io.TextIOWrapper(file) as f:
                # key is fail type, value is list of actual err messages
                grouped_fwts_output = group_fwts_output(f)
                for fail_type, messages in grouped_fwts_output.items():
                    for message in messages:
                        fwts_results[fail_type][run_index].append(message)

                f.seek(0)  # rewind file pointer

        for stderr_filename in [
            m.name
            for m in submission.getmembers()
            if re.match(boot_stderr_pattern, m.name) is not None
        ]:
            run_index = int(stderr_filename[len(prefix) : -7])
            file = submission.extractfile(stderr_filename)
            if not file:
                continue

            with io.TextIOWrapper(file) as f:
                grouped_device_out = group_device_cmp_output(f)
                for device, messages in grouped_device_out:
                    for msg in messages:
                        device_cmp_results[device][run_index].append(msg)

        # sort by boot number
        out[boot_type]["fwts"] = fwts_results
        out[boot_type]["device_cmp"] = device_cmp_results

    for boot_type in "warm", "cold":
        boot_count = warm_boot_count if boot_type == "warm" else cold_boot_count

        for test in "fwts", "device_cmp":
            print(f"\n{f' Start of {boot_type} boot {test} failures ':-^80}\n")

            if len(out[boot_type][test]) == 0:
                print(f"No {boot_type} boot {test} failures!")
            else:
                if args.verbose:
                    pretty_print(
                        out[boot_type][test],
                        boot_count,
                        test,
                    )
                else:
                    short_print(out[boot_type][test], boot_count)

                if test == "fwts" and args.group_by_err:
                    for fail_type in out[boot_type][test]:
                        group_res = group_by_error(
                            out[boot_type][test][fail_type],
                        )
                        for k in group_res:
                            print(k)
                            print(space, last, "Failed Runs:", group_res[k])
                            print(
                                space,
                                space,
                                "Fail Rate:",
                                f"{len(group_res[k])}/{boot_count}",
                            )

        if boot_count != args.expected_n_runs:
            print(
                f"{C.high}Expected {args.expected_n_runs} {boot_type} boots, but got {boot_count}{C.end}"
            )


if __name__ == "__main__":
    main()

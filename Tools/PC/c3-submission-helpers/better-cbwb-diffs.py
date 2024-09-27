#! /usr/bin/python3

import argparse
from collections import defaultdict
from typing import Literal
import io
import itertools
import tarfile
import re

space = "    "
branch = "│   "
tee = "├── "
last = "└── "


class Input:
    filename: str
    use_inference: bool
    num_runs: int | None  # override
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
]  # key is fail type (for fwts it's critical, high, medium, low)
# key is index to actual message map


def dice_coefficient(a: str, b: str) -> float:
    """dice coefficient 2nt/(na + nb)."""
    if not len(a) or not len(b):
        return 0.0
    if len(a) == 1:
        a = a + "."
    if len(b) == 1:
        b = b + "."

    a_bigram_list = []
    for i in range(len(a) - 1):
        a_bigram_list.append(a[i : i + 2])
    b_bigram_list = []
    for i in range(len(b) - 1):
        b_bigram_list.append(b[i : i + 2])

    a_bigrams = set(a_bigram_list)
    b_bigrams = set(b_bigram_list)
    overlap = len(a_bigrams & b_bigrams)
    dice_coeff = overlap * 2.0 / (len(a_bigrams) + len(b_bigrams))
    return dice_coeff


def parse_args() -> Input:
    p = argparse.ArgumentParser()
    p.add_argument(
        "-f",
        "--filename",
        required=True,
        help="path to the stress test tarball",
    )
    p.add_argument(
        "-i",
        "--use-inference",
        dest="use_inference",
        help="Use string similarity inference on fwts error messages",
        action="store_true",
    )
    p.add_argument(
        "--num-runs",
        dest="num_runs",
        help="Override the default number of boot loops (default=30 for both warm and cold)",
        type=int,
        required=False,
    )
    p.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        help="Whether to print detailed messages",
        action="store_true",
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


def get_device_cmp_lines(file: io.TextIOWrapper) -> list[str]:
    cmp_lines: list[str] = []
    should_include = False
    for line in file:
        if line.startswith("## Comparing the devices..."):
            should_include = True
            continue
        if line.startswith("## Checking system services..."):
            break
        if should_include:
            cmp_lines.append(line.strip())
    return cmp_lines


def group_fwts_output(file: io.TextIOWrapper) -> dict[str, list[str]]:
    """
    Picks out the fwts output lines from a single file and groups them by severity/fail_type
    """

    fwts_lines = get_fwts_lines(file)
    grouped_output = [
        (a, list(b))
        for a, b in itertools.groupby(
            fwts_lines, key=lambda line: line.endswith("failures:")
        )
    ]
    fail_type_to_lines: dict[str, list[str]] = {}

    for i, (is_fail_type, lines) in enumerate(grouped_output):
        if not is_fail_type:
            continue
        assert len(lines) > 0, "Broken fwts output"
        # if not broken, this list should look like ['High failures:'], eactly 1 element
        # take the first word and use it as the key
        fail_type = lines[0].split()[0]
        # the [0] of each element of grouped_output should alternate between True, False
        # If False, then we have the actual lines of the immediate predecessor fail_type
        actual_messages = grouped_output[i + 1][1]
        divider = "========================================"  # get rid of everything before the divider

        fail_type_to_lines[fail_type] = [
            s
            for s in actual_messages
            if s != ""
            and s != divider
            and not (s.startswith("oops:") or s.startswith("klog:"))
        ]  # also filter out empty strings

    return fail_type_to_lines


def group_device_cmp_output(file: io.TextIOWrapper) -> dict[str, list[str]]:
    device_type_to_lines: dict[str, list[str]] = {}

    grouped_output = [
        (a, list(b))
        for a, b in itertools.groupby(
            reversed(get_device_cmp_lines(file)),
            key=lambda line: line.endswith(
                "is different from the original list gathered at the beginning of the session!"
            ),
        )
    ]

    for i, (is_divider, lines) in enumerate(grouped_output):
        if is_divider:
            assert len(lines) > 0, "Broken device cmp output"
            for device_type in "lspci", "iw", "lsusb":
                if device_type in lines[0]:
                    actual_messages = grouped_output[i + 1][1]
                    device_type_to_lines[device_type] = [
                        s for s in actual_messages if s != ""
                    ]

    return device_type_to_lines


def infer_similar_errors(raw: RunIndexToMessageMap, similarity_threshold=0.9):
    message_to_run_index_map = defaultdict[str, list[int]](list)
    for run_index, messages in raw.items():
        for message in messages:
            message_to_run_index_map[message].append(run_index)

    # now we likely have 1 message mapped to exactly 1 index, run a reducer
    # print(message_to_run_index_map)

    items = list(message_to_run_index_map.items())
    out = []
    seen = set()
    i = 0
    # for i in range(len(items) - 1):
    while i < len(items) - 1:
        if i in seen:
            i += 1
            continue
        l = items[i]
        j = i + 1
        while j < len(items):
            if j in seen:
                j += 1
                continue
            r = items[j]
            if dice_coefficient(l[0], r[0]) > similarity_threshold:
                for e in r[1]:
                    l[1].append(e)
                seen.add(j)
            j += 1
        i += 1
        l[1].sort()
        out.append(l)
    return dict(out)


def pretty_print(
    boot_results: dict[str, dict[int, list[str]]], expected_n_runs=30, prefix=""
):
    for fail_type, results in boot_results.items():
        print(f"{prefix} {fail_type} failures".title())
        result_items = list(results.items())

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
        failed_runs = list(results.keys())
        print(
            f"{getattr(C, fail_type.lower())}{fail_type} failures:{C.end} {failed_runs}"
        )
        if expected_n_runs != 0:
            print(
                space,
                f"Fail rate: {len(failed_runs)} / {expected_n_runs}",
            )


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
        boot_stdout_pattern = f"{prefix}[0-9]+$"
        fwts_results: dict[str, dict[int, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )  # {fail_type: {run_index: list[actual_message]}}
        device_cmp_results: dict[str, dict[int, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for boot_filename in [
            m.name
            for m in submission.getmembers()
            if re.match(boot_stdout_pattern, m.name) is not None
        ]:
            if boot_type == "warm":
                warm_boot_count += 1
            else:
                cold_boot_count += 1

            run_index = int(boot_filename[len(prefix) :])
            file = submission.extractfile(boot_filename)
            if not file:
                continue

            # looks weird but allows f to close itself
            with io.TextIOWrapper(file) as f:
                # key is fail type, value is list of actual err messages
                grouped_fwts_output = group_fwts_output(f)
                for fail_type, messages in grouped_fwts_output.items():
                    for message in messages:
                        fwts_results[fail_type][run_index].append(message)

                grouped_device_cmp_output = group_device_cmp_output(f)
                for fail_type, messages in grouped_device_cmp_output.items():
                    for message in messages:
                        device_cmp_results[fail_type][run_index].append(message)

        # sort by boot number
        out[boot_type]["fwts"] = fwts_results
        out[boot_type]["device_cmp"] = device_cmp_results
        for fail_type in out[boot_type]:
            out[boot_type][fail_type] = dict(
                sorted(out[boot_type][fail_type].items())
            )

    # print(f"{getattr(C, fail_type.lower())}{fail_type} failures:{C.end}")
    for boot_type, test in itertools.product(
        ("warm", "cold"), ("fwts", "device_cmp")
    ):
        print(
            f"{'='*5}{C.other} Start of {boot_type} boot {test} failures{C.end} {'='*5}\n"
        )

        if len(out[boot_type][test]) == 0:
            print(f"No {boot_type} boot {test} failures!")
        else:
            if args.verbose:
                pretty_print(
                    out[boot_type][test],
                    warm_boot_count if boot_type == "warm" else cold_boot_count,
                    test,
                )
            else:
                short_print(
                    out[boot_type][test],
                    warm_boot_count if boot_type == "warm" else cold_boot_count,
                )

            if test == "fwts" and args.use_inference:
                print(
                    f"{C.ok}Begin inference results. These are just guesses and may not be accurate{C.end}\n"
                )
                for fail_type in out[boot_type][test]:
                    infer_res = infer_similar_errors(
                        out[boot_type][test][fail_type]
                    )
                    for k in infer_res:
                        print(k)
                        print(space, last, "Failed Runs:", infer_res[k])

        print(
            f"\n{'='*5}{C.other} End of {boot_type} boot {test} failures{C.end} {'='*5}"
        )


if __name__ == "__main__":
    main()

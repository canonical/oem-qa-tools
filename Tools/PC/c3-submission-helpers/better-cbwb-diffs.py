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


def parse_args() -> Input:
    p = argparse.ArgumentParser()
    p.add_argument(
        "-f",
        "--filename",
        required=True,
        help="path to the stress test tarball",
    )
    p.add_argument(
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
        help="Whether to print detailed messaged",
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


def group_fwts_output(file: io.TextIOWrapper) -> dict[str, list[str]]:
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


def pretty_print(boot_results: dict[str, dict[int, list[str]]]):
    for fail_type, results in boot_results.items():
        print(f"{getattr(C, fail_type.lower())}{fail_type} failures:{C.end}")
        result_items = list(results.items())

        for list_idx, (run_index, messages) in enumerate(result_items):
            is_last = list_idx == len(result_items) - 1
            print(space, last if is_last else tee, "Run", run_index)

            for m_i, message in enumerate(messages):
                if m_i == len(messages) - 1:
                    print(space, space if is_last else branch, last, message)
                else:
                    print(space, space if is_last else branch, tee, message)


def short_print(
    boot_results: dict[str, dict[int, list[str]]],
    expected_n_runs=30,
):
    for fail_type, results in boot_results.items():
        failed_runs = list(results.keys())
        print(
            f"{getattr(C, fail_type.lower())}{fail_type} failures:{C.end} {failed_runs}"
        )
        print(
            space,
            f"Fail rate: {len(failed_runs)} / {expected_n_runs}",
        )


def main():
    args = parse_args()
    submission = tarfile.open(args.filename)

    out: dict[Literal["warm", "cold"], dict[str, dict[int, list[str]]]] = {}
    for boot_type in "warm", "cold":
        prefix = f"test_output/com.canonical.certification__{boot_type}-boot-loop-test"
        # it's always the prefix followed by a multi-digit number
        boot_stdout_pattern = f"{prefix}[0-9]+$"
        boot_results: dict[str, dict[int, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )  # {fail_type: {run_index: list[actual_message]}}
        for boot_filename in [
            m.name
            for m in submission.getmembers()
            if re.match(boot_stdout_pattern, m.name) is not None
        ]:
            run_index = int(boot_filename[len(prefix) :])
            file = submission.extractfile(boot_filename)
            if not file:
                continue

            # looks weird but allows f to close itself
            with io.TextIOWrapper(file) as f:
                # key is fail type, value is list of actual err messages
                grouped_output = group_fwts_output(f)
                for fail_type, messages in grouped_output.items():
                    for message in messages:
                        boot_results[fail_type][run_index].append(message)

        out[boot_type] = boot_results
        for k in out[boot_type]:
            out[boot_type][k] = dict(sorted(out[boot_type][k].items()))

        if len(out[boot_type]) == 0:
            print(f"No {boot_type} boot fwts failures!")
        else:
            print(f"{boot_type.capitalize()} boot failures")
            if args.verbose:
                pretty_print(out[boot_type])
            else:
                short_print(out[boot_type], args.num_runs or 30)


if __name__ == "__main__":
    main()

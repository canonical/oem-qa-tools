#! /usr/bin/python3

from filecmp import cmp
import itertools
import os
from collections import defaultdict
import argparse
from typing import Literal  # noqa: F401


def inclusive_range(a: int, b: int):
    return range(a, b + 1)


def blue(s: str):
    return f"\033[96m{s}\033[0m"


def orange(s: str):
    return f"\033[94m{s}\033[0m"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "-p", "--path", required=True, help="The path to session-share"
    )
    p.add_argument(
        "-g",
        "--group-by",
        dest="group_by",
        required=False,
        default="index",
        help=(
            "Whether to group by index or group by fail types."
            "Accepts '-g index' or '-g log-name' "
        ),
        choices=["index", "log-name"],
    )
    p.add_argument(
        "--ignore", help="ignore differences of these files", type=list
    )
    return p.parse_args()


def main():
    args = parse_args()
    print("Checking session share path", args.path)
    # Add names of log files here to suppress comparing them
    args.ignored_log_names = []

    if args.group_by == "index":
        main_by_index(args)
    if args.group_by == "log-name":
        main_by_log_name(args)


def main_by_index(args):
    warm_fail_count = defaultdict(list)
    cold_fail_count = defaultdict(list)
    log_names = os.listdir(f"{args.path}/session-share/before_reboot/")
    for ignored in args.ignored_log_names:
        log_names.remove(ignored)

    for i, log_name, cold_or_warm in itertools.product(
        inclusive_range(1, 30),
        log_names,
        ("warm", "cold"),
    ):
        if not (
            cmp(
                f"{args.path}/session-share/before_reboot/{log_name}",
                (
                    f"{args.path}/session-share/"
                    f"{cold_or_warm}_reboot_cycle{i}/"
                    f"{log_name}"
                ),
            )
        ):
            if cold_or_warm == "cold":
                cold_fail_count[i].append(log_name)
            else:
                warm_fail_count[i].append(log_name)

    if len(cold_fail_count) > 0:
        print("\nCold boot fails:")
        for i, logs in cold_fail_count.items():
            print(f'\tRun {i}: {",".join(logs)}')

    if len(warm_fail_count) > 0:
        print("\nWarm boot fails:")
        for i, logs in warm_fail_count.items():
            print(f'\tRun {i}: {",".join(logs)}')


def main_by_log_name(args):
    log_names = os.listdir(f"{args.path}/session-share/before_reboot/")
    out = {}  # type: dict[str, dict[Literal['cold', 'warm'], list[int]]]
    for ignored in args.ignored_log_names:
        log_names.remove(ignored)

    for log_name in log_names:
        out[log_name] = {
            "cold": [],
            "warm": [],
        }

    for i, log_name, cold_or_warm in itertools.product(
        inclusive_range(1, 30),
        log_names,
        ("warm", "cold"),
    ):
        if not (
            cmp(
                f"{args.path}/session-share/before_reboot/{log_name}",
                (
                    f"{args.path}/session-share/"
                    f"{cold_or_warm}_reboot_cycle{i}/{log_name}"
                ),
            )
        ):
            out[log_name][cold_or_warm].append(i)

    for log_name in log_names:
        if len(out[log_name]["cold"]) > 0:
            print(
                f"{log_name} failed in these cold boot runs: "
                f'{out[log_name]["cold"]}'
            )

        if len(out[log_name]["warm"]) > 0:
            print(
                f"{log_name} failed in these warm boot runs: "
                f'{out[log_name]["warm"]}'
            )


if __name__ == "__main__":
    main()

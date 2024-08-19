#! /usr/bin/python3

from filecmp import cmp
import itertools
import os
from collections import defaultdict
import argparse


def inclusive_range(a: int, b: int):
    return range(a, b + 1)


def blue(s: str):
    return f"\033[96m{s}\033[0m"


def orange(s: str):
    return f"\033[94m{s}\033[0m"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("-p", "--path", required=True, help="The path to session-share")
    p.add_argument(
        "-g",
        "--group-by",
        dest="group_by",
        required=False,
        default="index",
        help="Whether to group by index or group by fail types. Accepts '-g index' or '-g log-name' ",
        choices=["index", "log-name"],
    )
    return p.parse_args()


def main():
    args = parse_args()
    print("Checking session share path", args.path)
    args.suppress = ["fwts_klog_oops.log"]

    if args.group_by == "index":
        main_by_index(args)
    if args.group_by == "log-name":
        main_by_log_name(args)


def main_by_index(args):
    warm_fail_count = defaultdict(list)
    cold_fail_count = defaultdict(list)
    log_names = os.listdir(f"{args.path}/session-share/before_reboot/")
    for suppressd in args.suppress:
        log_names.remove(suppressd)

    for i, log_name, cold_or_warm in itertools.product(
        inclusive_range(1, 30),
        log_names,
        ("warm", "cold"),
    ):
        if (
            cmp(
                f"{args.path}/session-share/before_reboot/{log_name}",
                f"{args.path}/session-share/{cold_or_warm}_reboot_cycle{i}/{log_name}",
            )
            == False
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
    out = {}
    for suppressd in args.suppress:
        log_names.remove(suppressd)

    for log_name in log_names:
        out[log_name] = {
            "cold": [],
            "warm": [],
        }  # dict[Literal['cold', 'warm'], list[int]]

    for i, log_name, cold_or_warm in itertools.product(
        inclusive_range(1, 30),
        log_names,
        ("warm", "cold"),
    ):
        if (
            cmp(
                f"{args.path}/session-share/before_reboot/{log_name}",
                f"{args.path}/session-share/{cold_or_warm}_reboot_cycle{i}/{log_name}",
            )
            == False
        ):
            out[log_name][cold_or_warm].append(i)

    for log_name in log_names:
        if len(out[log_name]["cold"]) > 0:
            print(f'{log_name} failed in these cold boot runs: {out[log_name]["cold"]}')

        if len(out[log_name]["warm"]) > 0:
            print(f'{log_name} failed in these warm boot runs: {out[log_name]["warm"]}')


if __name__ == "__main__":
    main()

#! /usr/bin/env python3

import os
import subprocess as sp
import configparser


def info(s: str):
    print(f"[ INFO ] \033[92m{s}\033[0m")


if __name__ == "__main__":
    if os.getuid() != 0:
        print("This script needs sudo")
        exit(1)

    info("Setting journalctl to keep as many logs as possible")
    sp.run(
        [
            "sudo",
            "cp",
            "/etc/systemd/journald.conf",
            "/etc/systemd/journald.conf.bak",
        ]
    )

    journal_config = configparser.ConfigParser()
    journal_config.optionxform = lambda optionstr: optionstr
    journal_config.read("/etc/systemd/journald.conf")
    journal_config["Journal"]["Storage"] = "persistent"
    # journal_config["Journal"]["MaxFileSec"] = "180day"
    journal_config["Journal"]["SystemMaxFiles"] = "200"
    journal_config["Journal"]["SystemMaxUse"] = "10G"

    ok = input(
        "After this change, journalctl will save at most "
        + journal_config["Journal"]["SystemMaxFiles"]
        + " entries and use at most "
        + journal_config["Journal"]["SystemMaxUse"]
        + " of space. "
        + "Continue? [y/n] "
    )

    if ok != "y":
        print("Exiting.")
        exit(1)

    with open("/etc/systemd/journald.conf", "w") as f:
        journal_config.write(f)

    sp.run(["sudo", "systemctl", "restart", "systemd-journald"])
    info("Journal service has been restarted with the new config!")
    info("The backup config is at /etc/systemd/journald.conf.bak")

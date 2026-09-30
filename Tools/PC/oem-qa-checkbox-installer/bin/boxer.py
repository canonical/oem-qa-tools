#!/usr/bin/env python3

import argparse
import configparser
import os
import subprocess as sp
import time
from pathlib import Path

VERSION = "2.2"
PROVIDERS = (
    "somerville",
    "sutton",
    "stella",
    "kittyhawk",
    "otaru",
    "wenshan",
)
CHECKBOX_REPOS = {
    "stable": "ppa:checkbox-dev/stable",
    "testing": "ppa:checkbox-dev/beta",
    "daily": "ppa:checkbox-dev/edge",
}
FWTS_REPO = "ppa:firmware-testing-team/ppa-fwts-stable"
PC_ENABLE_REPO = "ppa:oem-solutions-engineers/pc-enablement-tools"
OEM_REPO = (
    "https://{username}:{password}@private-ppa.launchpad.net/"
    "oem-services-qa/ppa/ubuntu"
)
OEM_SOURCE_LIST = (
    "deb https://private-ppa.launchpad.net/"
    "oem-services-qa/ppa/ubuntu {codename} main"
)

# Public key for OEM Services PPA (PUBKEY 17B878BE09D5DC1F)
OEM_PPA_GPG = """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Comment: Hostname:
Version: Hockeypuck ~unreleased

xo0ESkJgvQEEANvHkVH7riYJ1+mIjtCg15XI/QpVKDAuDVF8B6unTVottuEQ1WZw
6ESWE8q+k004iroTof8XB8zYGDcqUIKZ5rfsPtgQklq2QltQdhRm4bnpr8SlCBJZ
l83PcUmOZ77bihdxyzHqTR3qRl3Yz+aRVunG9decBWN+D24JrJQgP1nPABEBAAHN
IUxhdW5jaHBhZCBQUEEgZm9yIE9FTSBTZXJ2aWNlcyBRQcK2BBMBAgAgBQJKQmC9
AhsDBgsJCAcDAgQVAggDBBYCAwECHgECF4AACgkQF7h4vgnV3B+jdAQAg+Wkf4pF
q1UIe1r6KVYHDGjaS2J6oLPN781/ccMqEthFUfns5s+nqbvNZfvSjZbTt9wc2EQz
5vJDV7uyj1MQWJDaWgTHTRxAOMiaSNKPQ50qjhGcprhjZnHxJa71PTRB+8pqiTBw
OqboGUSfWwcOY7fN98NQj1aJGCiDr2Jy9tE=
=ER36
-----END PGP PUBLIC KEY BLOCK-----
"""


# Colors for messages output
class TColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def main():
    print(f"== Boxer v{VERSION} ==")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        help="Command to run (default: install)",
        nargs="?",
        default="install",
    )
    parser.add_argument(
        "-p",
        "--provider",
        help="Provider name ({})".format(", ".join(PROVIDERS)),
    )
    parser.add_argument(
        "-r",
        "--repository",
        help="Checkbox repository to use ({})".format(
            ", ".join(CHECKBOX_REPOS)
        ),
    )
    args = parser.parse_args()

    config = configparser.ConfigParser()
    while not config.read("./conf/setting.conf"):
        create_config()
    boxercfg = config["boxer"]
    username = boxercfg["username"]
    ppa_password = boxercfg["ppa_password"]
    provider = args.provider or boxercfg["provider"]
    repository = args.repository or boxercfg["repository"] or "testing"

    pre_install()
    # We remove any existing PPA before adding the new ones
    setup_public_ppa(repository, remove=True)
    setup_public_ppa(repository)
    setup_stress_ng_ppa("ppa:colin-king/stress-ng")
    setup_oem_ppa(username, ppa_password)
    install(provider)


def create_config():
    """If boxer config file not found, this will ask the user a few questions
    and create one next to the boxer script."""

    print(
        "Hi! It looks like there is no boxer.conf file yet.",
        "Let's create one!",
    )
    username = input("What's your Launchpad username? ")
    print()
    print(
        "Let's find the password",
        "you need to access the OEM providers repository.",
    )
    # The link to personal private ppa subscription management
    # <https://launchpad.net/~oem-services-qa/+archive/ubuntu/ppa>
    print(
        "Go to",
        f"<https://launchpad.net/~{username}/+archivesubscriptions/10011>",
    )
    print("You should see something like")
    print()
    print(f"\tdeb https://{username}:<password>@private-ppa...")
    print()
    ppa_password = input("Copy the password and paste it here: ")
    print()
    print("Boxer currently supports the following providers: ", end="")
    print(", ".join(PROVIDERS))
    provider = input("What provider do you want to use by default? ")
    print()
    print(
        "Checkbox can be installed from the following repositories: ", end=""
    )
    print(", ".join(CHECKBOX_REPOS))
    repository = input("Which repository do you want to use by default? ")

    config = configparser.ConfigParser()
    config.add_section("boxer")
    boxercfg = config["boxer"]
    boxercfg["username"] = username
    boxercfg["ppa_password"] = ppa_password
    boxercfg["provider"] = provider
    boxercfg["repository"] = repository

    with open("./conf/setting.conf", "w") as configfile:
        config.write(configfile)
    print()
    print("All set!")
    print(
        "Next time you run boxer, "
        "make sure your boxer.conf is located in the same directory!"
    )
    print()
    time.sleep(3)


def setup_stress_ng_ppa(ppa: str):
    """
    Setup required stress-ng PPAs to install Checkbox OEM stack.
    By default, it adds the PPAs. If `remove` is set, the PPAs are removed.
    """
    print("Setting up the stress-ng PPAs...")
    print("Removing installed stress-ng ...")
    # run_command("sudo apt remove stress-ng -y")
    sp.run(["sudo", "apt", "remove", "stress-ng", "-y"], check=True)
    print(f"Adding PPA {ppa}...")
    sp.run(["sudo", "add-apt-repository", "-y", ppa], check=True)

    # disable the stress-ng in the checkbox-dev PPA
    # need to use a tmp file here because we need to call sudo later
    tmp_file_path = Path("/tmp/no-stress-ng-from-checkbox-dev")
    with tmp_file_path.open("w") as f:
        f.writelines(
            [
                "Package: stress-ng\n",
                "Pin: release o=LP-PPA-colin-king-stress-ng\n",
                "Pin-Priority: 1001\n",
                "\n",
                "Package: stress-ng\n",
                "Pin: release o=LP-PPA-checkbox-dev-beta\n",
                "Pin-Priority: -1\n",
            ]
        )

    pin_file = Path("/etc/apt/preferences.d/no-stress-ng-from-checkbox-dev")
    sp.run(["sudo", "cp", tmp_file_path, pin_file], check=True)
    sp.run(["sudo", "apt", "update"], check=True)


def setup_public_ppa(repo: str, remove: bool = False):
    """
    Setup required public PPAs to install Checkbox OEM stack.
    By default, it adds the PPAs. If `remove` is set, the PPAs are removed.
    """
    print("Setting up the public PPAs...")
    # If we remove the PPAs, we want to make sure we remove any Checkbox PPA,
    # not only the PPA we are trying to install, otherwise if the previously
    # chosen PPA was 'daily', and we want to install 'stable', in the end we'll
    # still have the version from daily installed...
    if remove:
        checkbox_repo = list(CHECKBOX_REPOS.values())
    else:
        checkbox_repo = [CHECKBOX_REPOS[repo]]
    repos = checkbox_repo + [FWTS_REPO, PC_ENABLE_REPO]
    for ppa in repos:
        if remove:
            print(f"Removing PPA {ppa}...")
            command = ["sudo", "add-apt-repository", "-y", "-r", ppa]
        else:
            print(f"Adding PPA {ppa}...")
            command = ["sudo", "add-apt-repository", "-y", ppa]

        sp.run(command, check=True)


def add_oem_source_list():
    """
    Add OEM Services PPA to sources.list.d and update the apt database
    """
    print("Adding the OEM Providers PPA...")
    cmd = "lsb_release -sc"
    output = sp.run(["lsb_release", "-sc"], capture_output=True, check=True)
    ubuntu_codename = output.stdout.decode().strip()
    source_list = OEM_SOURCE_LIST.format(codename=ubuntu_codename)
    cmd = (
        f'sudo sh -c \'echo "{source_list}" > '
        f"/etc/apt/sources.list.d/oem-services-qa-ubuntu-ppa.list'"
    )
    sp.run(cmd, shell=True, check=True)
    sp.run(["sudo", "apt", "update"], check=True)


def add_auth_conf(username: str, password: str):
    """
    Add authentication data for the OEM Services PPA to auth.conf.d
    """
    print("Add authentication data for the OEM Services PPA to auth.conf.d...")
    auth_conf = (
        "machine "
        "private-ppa.launchpad.net/oem-services-qa/ppa/ubuntu "
        f"login {username} password {password}"
    )
    cmd = (
        f'sudo sh -c \'echo "{auth_conf}" > '
        "/etc/apt/auth.conf.d/oem-services-qa-ubuntu-ppa.conf'"
    )
    sp.run(cmd, shell=True, check=True)


def add_oem_ppa_gpg():
    """
    Add OEM Services PPA public GPG key to the trusted.gpg.d directory
    For more info, see:
    <https://www.linuxuprising.com/2021/01/apt-key-is-deprecated-how-to-add.html>
    """
    print(
        "Add OEM Services PPA public GPG key to "
        "the trusted.gpg.d directory..."
    )
    cmd = (
        f'sudo sh -c \'echo "{OEM_PPA_GPG}" | '
        "gpg --dearmor > "
        "/etc/apt/trusted.gpg.d/oem-services-qa-ubuntu-ppa.gpg'"
    )
    sp.run(cmd, shell=True, check=True)


def setup_oem_ppa(username: str, password: str):
    """
    Setup the OEM providers PPA.
    """
    add_auth_conf(username, password)
    add_oem_ppa_gpg()
    add_oem_source_list()


def pre_install():
    # Add sudoer setting file to allow Checkbox to run sudo commands without
    # having to enter the sudo password.
    user = os.getenv("USER")
    sp.run(
        f"echo '{user} ALL=(ALL:ALL) NOPASSWD: ALL' | "
        "sudo tee /etc/sudoers.d/checkbox",
        shell=True,
        check=True,
    )

    sp.run(
        [
            "sudo",
            "gpg",
            "--keyserver",
            "keyserver.ubuntu.com",
            "--recv-keys",
            "2BBDF2BD",  # checkbox
            "09D5DC1F",  # oem services qa
            "6BE75981",  # sutton
        ],
        check=True,
    )


def install(provider: str):
    assert provider in PROVIDERS, f"Unknown provider {provider}"
    print(
        "Purging Checkbox-related packages "
        "that might already be installed..."
    )
    sp.run(
        ["sudo", "apt-get", "purge", "--yes", ".*plainbox.*", ".*checkbox.*"],
        check=True,
    )

    print("Installing Checkbox base packages...")
    sp.run(
        [
            "sudo",
            "env",
            "DEBIAN_FRONTEND=noninteractive",
            "apt",
            "install",
            "--yes",
            "--allow-downgrades",
            "--allow-remove-essential",
            "--allow-change-held-packages",
            "checkbox-ng",
            "checkbox-provider-resource",
            "checkbox-provider-certification-client",
            "checkbox-provider-base",
            "canonical-certification-client",
        ],
        check=True,
    )

    print(f"Installing provider {provider}...")
    # Add DEBIAN_FRONTEND=noninteractive
    # to avoid interruption, example: postfix
    sp.run(
        [
            "sudo",
            "env",
            "DEBIAN_FRONTEND=noninteractive",
            "apt",
            "install",
            "-y",
            "--allow-downgrades",
            "--allow-remove-essential",
            "--allow-change-held-packages",
            f"plainbox-provider-oem-{provider}",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()

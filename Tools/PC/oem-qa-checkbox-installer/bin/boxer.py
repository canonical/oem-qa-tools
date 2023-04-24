#!/usr/bin/env python3

import argparse
import configparser
import os
import subprocess
import time

VERSION = "2.2"
PROVIDERS = ("somerville",
             "sutton",
             "stella",
             "kittyhawk",
             "otaru",
             "wenshan",
             )
CHECKBOX_REPOS = {"stable": "ppa:hardware-certification/public",
                  "testing": "ppa:checkbox-dev/testing",
                  "daily": "ppa:checkbox-dev/ppa"}
FWTS_REPO = "ppa:firmware-testing-team/ppa-fwts-stable"
PC_ENABLE_REPO = "ppa:oem-solutions-engineers/pc-enablement-tools"
OEM_REPO = "https://{username}:{password}@private-ppa.launchpad.net/" \
           "oem-services-qa/ppa/ubuntu"
OEM_SOURCE_LIST = "deb https://private-ppa.launchpad.net/" \
                  "oem-services-qa/ppa/ubuntu {codename} main"

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
class tcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def main():
    print("== Boxer v{} ==".format(VERSION))
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="Command to run (default: install)",
                        nargs="?", default="install")
    parser.add_argument("-p", "--provider",
                        help="Provider name ({})".format(", ".join(PROVIDERS)))
    parser.add_argument("-r", "--repository",
                        help="Checkbox repository to use ({})"
                             .format(", ".join(CHECKBOX_REPOS)))
    args = parser.parse_args()

    config = configparser.ConfigParser()
    while not config.read("./conf/setting.conf"):
        create_config()
    boxercfg = config["boxer"]
    username = boxercfg["username"]
    ppa_password = boxercfg["ppa_password"]
    provider = args.provider or boxercfg["provider"]
    repository = args.repository or boxercfg["repository"] or "stable"

    pre_install()
    # We remove any existing PPA before adding the new ones
    setup_public_ppa(repository, username, ppa_password, remove=True)
    setup_public_ppa(repository, username, ppa_password)
    setup_oem_ppa(username, ppa_password)
    install(provider)


def create_config():
    """ If boxer config file not found, this will ask the user a few questions
    and create one next to the boxer script."""

    print("Hi! It looks like there is no boxer.conf file yet."
          " Let's create one!")
    username = input("What's your Launchpad username? ")
    print()
    print("Let's find the password "
          "you need to access the OEM providers repository.")
    # The link to personal private ppa subscription management
    # <https://launchpad.net/~oem-services-qa/+archive/ubuntu/ppa>
    print("Go to "
          f"<https://launchpad.net/~{username}/+archivesubscriptions/10011>")
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
    print("Checkbox can be installed from the following repositories: ",
          end="")
    print(", ".join(CHECKBOX_REPOS))
    repository = input("Which repository do you want to use by default? ")

    config = configparser.ConfigParser()
    config.add_section("boxer")
    boxercfg = config["boxer"]
    boxercfg["username"] = username
    boxercfg["ppa_password"] = ppa_password
    boxercfg["provider"] = provider
    boxercfg["repository"] = repository

    with open('./conf/setting.conf', 'w') as configfile:
        config.write(configfile)
    print()
    print("All set!")
    print("Next time you run boxer, "
          "make sure your boxer.conf is located in the same directory!")
    print()
    time.sleep(3)


def setup_public_ppa(repo, username, password, remove=False):
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
            print("Removing PPA {}...".format(ppa))
            command = f"sudo add-apt-repository -y -r {ppa}"
        else:
            print("Adding PPA {}...".format(ppa))
            command = f"sudo add-apt-repository -y {ppa}"
        run_command(command)


def add_oem_source_list():
    """
    Add OEM Services PPA to sources.list.d and update the apt database
    """
    print("Adding the OEM Providers PPA...")
    cmd = "lsb_release -sc"
    output = subprocess.run(cmd.split(), capture_output=True)
    ubuntu_codename = output.stdout.decode().strip()
    source_list = OEM_SOURCE_LIST.format(codename=ubuntu_codename)
    cmd = f"sudo sh -c 'echo \"{source_list}\" > " \
          f"/etc/apt/sources.list.d/oem-services-qa-ubuntu-ppa.list'"
    run_command(cmd, shell=True)
    cmd = "sudo apt update"
    run_command(cmd)


def add_auth_conf(username, password):
    """
    Add authentication data for the OEM Services PPA to auth.conf.d
    """
    print("Add authentication data for the OEM Services PPA to auth.conf.d...")
    auth_conf = "machine " \
                "private-ppa.launchpad.net/oem-services-qa/ppa/ubuntu " \
                f"login {username} password {password}"
    cmd = f"sudo sh -c 'echo \"{auth_conf}\" > " \
          "/etc/apt/auth.conf.d/oem-services-qa-ubuntu-ppa.conf'"
    run_command(cmd, shell=True)


def add_oem_ppa_gpg():
    """
    Add OEM Services PPA public GPG key to the trusted.gpg.d directory
    For more info, see:
    <https://www.linuxuprising.com/2021/01/apt-key-is-deprecated-how-to-add.html>
    """
    print("Add OEM Services PPA public GPG key to "
          "the trusted.gpg.d directory...")
    cmd = f"sudo sh -c 'echo \"{OEM_PPA_GPG}\" | " \
          "gpg --dearmor > " \
          "/etc/apt/trusted.gpg.d/oem-services-qa-ubuntu-ppa.gpg'"
    run_command(cmd, shell=True)


def setup_oem_ppa(username, password):
    """
    Setup the OEM providers PPA.
    """
    add_auth_conf(username, password)
    add_oem_ppa_gpg()
    add_oem_source_list()


def run_command(command, shell=False, check=True):
    if not shell:
        command = command.split()
    try:
        subprocess.run(command, shell=shell, check=check)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"{tcolors.FAIL}Error:{tcolors.ENDC} {e}")


def pre_install():
    # Add sudoer setting file to allow Checkbox to run sudo commands without
    # having to enter the sudo password.
    user = os.getenv("USER")
    cmd = f"echo '{user} ALL=(ALL:ALL) NOPASSWD: ALL' | " \
          "sudo tee /etc/sudoers.d/checkbox"
    run_command(cmd, shell=True)

    # Add GPG keys from the different repositories.
    commands = ("sudo apt-key adv --keyserver keyserver.ubuntu.com "
                "--recv-keys 2BBDF2BD 09D5DC1F 6BE75981",)
    print("Running pre-install commands...")
    for cmd in commands:
        run_command(cmd)


def install(provider):
    print("Purging Checkbox-related packages "
          "that might already be installed...")
    cmd = "sudo apt-get purge -y .*plainbox.* .*checkbox.*"
    run_command(cmd)

    print("Installing Checkbox base packages...")
    cmd = ("sudo DEBIAN_FRONTEND=noninteractive apt install -y "
           "--allow-downgrades --allow-remove-essential "
           "--allow-change-held-packages "
           "checkbox-ng "
           "checkbox-provider-resource "
           "checkbox-provider-certification-client "
           "checkbox-provider-base "
           "canonical-certification-client")
    run_command(cmd)

    print("Installing provider {}...".format(provider))
    # Add DEBIAN_FRONTEND=noninteractive
    # to avoid interruption, example: postfix
    cmd = ("sudo DEBIAN_FRONTEND=noninteractive apt install -y "
           "--allow-downgrades --allow-remove-essential "
           "--allow-change-held-packages plainbox-provider-oem-"+provider)
    run_command(cmd)


if __name__ == "__main__":
    main()

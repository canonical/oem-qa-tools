#!/usr/bin/env python3

"""Charm the application."""

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v0.apt import DebianRepository
from charms.operator_libs_linux.v2 import snap
import subprocess
from subprocess import CalledProcessError
import logging
import ops
from ops.model import (
    BlockedStatus,
)
import os

logger = logging.getLogger(__name__)


class OemQaVmCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self._checkbox_ppa_channel = "beta"
        self._checkbox_release = "jammy"
        self._checkbox_branch = "main"
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.install, self._on_install)
        
    @property
    def checkbox_ppa(self):
        """Construct the full PPA URL dynamically."""
        return f"https://ppa.launchpadcontent.net/checkbox-dev/{self._checkbox_ppa_channel}/ubuntu/"

    @property
    def checkbox_ppa_channel(self):
        return self._checkbox_ppa_channel

    @checkbox_ppa_channel.setter
    def checkbox_ppa_channel(self, value):
        self._checkbox_ppa_channel = value

    @property
    def checkbox_release(self):
        return self._checkbox_release

    @checkbox_release.setter
    def checkbox_release(self, value):
        self._checkbox_release = value

    @property
    def checkbox_branch(self):
        return self._checkbox_branch

    @checkbox_branch.setter
    def checkbox_branch(self, value):
        self._checkbox_branch = value

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.ActiveStatus()

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        self.unit.status = ops.MaintenanceStatus("Installing needed packages")
        self.add_checkbox_beta_ppa()
        self.install_apt_packages(
            [
                "tmux",
                "checkbox-ng",
            ]
        )
        self.install_snap_packages(
            [
                "testflinger-cli",
            ]
        )
        self.import_ssh_key()
        self.set_static_ip()
        self.set_tmux_config()
        self.unit.status = ops.ActiveStatus("Ready")

    def add_checkbox_beta_ppa(self):
        """Add checkbox beta PPA"""
        apt.import_key("968504F7952C9377")  # For checkbox
        repositories = apt.RepositoryMapping()
        line = f"deb {self.checkbox_ppa} {self.checkbox_release} {self.checkbox_branch}"
        repo = DebianRepository.from_repo_line(line)
        repositories.add(repo)

    def import_ssh_key(self):
        """Import ssh key by launchpad id"""
        lp_id = self.config.get("launchpad-id")
        if not lp_id:
            logger.error("launchpad-id must be set")
            raise ValueError("launchpad-id must be set")
        try:
            # juju will use root to execute all commands. Let's change it
            subprocess.check_output(
                ["sudo", "-u", "ubuntu", "ssh-import-id", lp_id]
            )
        except CalledProcessError as e:
            logger.error(
                f"Failed to import ssh key from [{lp_id}] with {repr(e)}"
            )
            raise ValueError("launchpad-id may be incorrect")

    def set_static_ip(self):
        """Add 60-oemqa.yaml to set static IP"""
        config = """
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: false
      dhcp-identifier: mac
      addresses:
      - {}/22
"""
        ip = self.config.get("static-ip")
        if not ip or ip == "127.0.0.1":
            logger.error("static-ip is not provided, using dhcp mode")
        else:
            file = "/etc/netplan/60-oemqa.yaml"
            with open(file, "w") as f:
                f.write(config.format(ip))
            subprocess.check_output(["netplan", "apply"])

    def set_tmux_config(self):
        """Make tumx could use mouse"""
        file = "/home/ubuntu/.tmux.conf"
        with open(file, "w") as f:
            f.write("set -g mouse on")
        os.chown(file, 1000, 1000)

    def install_apt_packages(self, packages: list):
        """Simple wrapper around 'apt-get install -y"""
        try:
            apt.update()
            apt.add_package(packages)
        except apt.PackageNotFoundError:
            logger.error(
                "a specified package not found in package cache or on system"
            )
            self.unit.status = BlockedStatus("Failed to install packages")
        except apt.PackageError:
            logger.error("could not install package")
            self.unit.status = BlockedStatus("Failed to install packages")

    def install_snap_packages(self, packages: list):
        """Simple wrapper around 'snap install"""
        try:
            snap.add(packages)
        except snap.SnapError as e:
            logger.error(
                "An exception occurred when installing snaps. Reason: %s"
                % e.message
            )


if __name__ == "__main__":  # pragma: nocover
    ops.main(OemQaVmCharm)

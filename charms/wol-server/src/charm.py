#!/usr/bin/env python3

"""Charm the application."""

from charmlibs import apt
import subprocess
from subprocess import CalledProcessError
import urllib.request
import logging
import ops
from ops.model import (
    BlockedStatus,
)

logger = logging.getLogger(__name__)

wol_install_destination = "/usr/bin/"


class WolCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.install, self._on_install)

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.ActiveStatus()

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        self.unit.status = ops.MaintenanceStatus("Installing needed packages")
        self.install_apt_packages(
            [
                "wakeonlan",
                "python3-fastapi",
                "uvicorn",
            ]
        )
        self.download_default_wol_server_code()
        self.start_wol_server(self.config.get("port"))
        self.unit.status = ops.ActiveStatus("Ready")

    def _on_update(self, event: ops.UpgradeCharmEvent):
        """Handle install event."""
        self.unit.status = ops.MaintenanceStatus("Updating the wol server")
        self.download_default_wol_server_code()
        self.start_wol_server(self.config.get("port"))
        self.unit.status = ops.ActiveStatus("Ready")

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

    def download_default_wol_server_code(self):
        """Download default WoL server script"""
        try:
            urllib.request.urlretrieve(
                self.config.get("wol_server_script"),
                f"{wol_install_destination}wol_server.py",
            )
            logger.info(f"Downloaded file to {wol_install_destination}")
        except Exception as e:
            logger.error(f"Failed to download file: {repr(e)}")
            self.unit.status = BlockedStatus("Failed to install packages")

    def start_wol_server(self, port: int):
        """Start default WoL server"""
        cmd = "uvicorn --app-dir {} wol_server:app --host {} --port {}".format(
            wol_install_destination, "0.0.0.0", port
        )
        service_content = f"""
        [Unit]
        Description=Wake-on-Lan server
        After=network.target

        [Service]
        ExecStart={cmd}
        Restart=on-failure

        [Install]
        WantedBy=multi-user.target
        """
        service_file = "/etc/systemd/system/wol.service"
        with open(service_file, "w") as f:
            f.write(service_content)

        try:
            subprocess.check_call(["systemctl", "daemon-reload"])
            subprocess.check_call(["systemctl", "enable", "wol"])
            subprocess.check_call(["systemctl", "start", "wol"])
        except CalledProcessError as e:
            logger.error(f"Failed to start wol server: {repr(e)}")
            self.unit.status = BlockedStatus("Failed to setup service")


if __name__ == "__main__":  # pragma: nocover
    ops.main(WolCharm)

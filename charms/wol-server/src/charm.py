#!/usr/bin/env python3

"""Charm the application."""

import logging
import subprocess
import urllib.request
from subprocess import CalledProcessError

import ops
from charmlibs import apt
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

logger = logging.getLogger(__name__)

wol_install_destination = "/usr/bin/"


class WolCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.config_changed, self._on_config_or_upgrade)
        framework.observe(self.on.upgrade_charm, self._on_config_or_upgrade)

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        if not isinstance(
            self.unit.status, (BlockedStatus, MaintenanceStatus)
        ):
            self.unit.status = ActiveStatus()

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        self.unit.status = MaintenanceStatus("Installing needed packages")
        if not self.install_apt_packages(
            [
                "wakeonlan",
                "python3-fastapi",
                "uvicorn",
            ]
        ):
            return
        self.setup_wol_server()

    def _on_config_or_upgrade(
        self, event: ops.ConfigChangedEvent | ops.UpgradeCharmEvent
    ):
        """Handle config-changed or upgrade-charm event."""
        self.setup_wol_server()

    def setup_wol_server(self):
        """Set up WoL server with config validation."""
        port = self.config.get("port")
        wol_script_url = self.config.get("wol_server_script")

        if not port:
            self.unit.status = BlockedStatus("Missing required config: port")
            return

        if not wol_script_url:
            self.unit.status = BlockedStatus(
                "Missing required config: wol_server_script"
            )
            return

        self.unit.status = MaintenanceStatus("Setting up WoL server")

        if not self.download_default_wol_server_code():
            return

        if not self.start_wol_server(port):
            return

        self.unit.status = ActiveStatus("Ready")

    def install_apt_packages(self, packages: list) -> bool:
        """Install apt packages using apt-get."""
        try:
            apt.update()
            apt.add_package(packages)
            return True
        except apt.PackageNotFoundError:
            logger.error(
                "a specified package not found in package cache or on system"
            )
            self.unit.status = BlockedStatus("Failed to install packages")
            return False
        except apt.PackageError:
            logger.error("could not install package")
            self.unit.status = BlockedStatus("Failed to install packages")
            return False

    def download_default_wol_server_code(self) -> bool:
        """Download default WoL server script."""
        try:
            urllib.request.urlretrieve(
                self.config.get("wol_server_script"),
                f"{wol_install_destination}wol_server.py",
            )
            logger.info(f"Downloaded file to {wol_install_destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {repr(e)}")
            self.unit.status = BlockedStatus(
                "Failed to download WoL server script"
            )
            return False

    def start_wol_server(self, port: int) -> bool:
        """Start default WoL server."""
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
            subprocess.check_call(["systemctl", "restart", "wol"])
            return True
        except CalledProcessError as e:
            logger.error(f"Failed to start wol server: {repr(e)}")
            self.unit.status = BlockedStatus("Failed to setup service")
            return False


if __name__ == "__main__":  # pragma: nocover
    ops.main(WolCharm)

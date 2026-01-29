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

REPO_URL = "https://github.com/KhronosGroup/WebGL.git"
REPO_NAME = "WebGL"

WEBGL_TESTS_PATH = "/var/www/webgl_tests"
CLONE_PATH = os.path.join(WEBGL_TESTS_PATH, "sdk", "tests")

NGINX_CONFIG_FILE = "webgl_tests.conf"
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available/"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled/"


class WebGLCharm(ops.CharmBase):
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
                "nginx",
            ]
        ):
            return
        self.setup_webgl_server()

    def _on_config_or_upgrade(
        self, event: ops.ConfigChangedEvent | ops.UpgradeCharmEvent
    ):
        """Handle config-changed or upgrade-charm event."""
        self.setup_webgl_server()

    def run_command(command, message):
        """
        Executes a shell command and provides feedback.
        """
        logger.info(f"\n[INFO] {message}")
        try:
            subprocess.run(command, check=True, shell=True)
            logger.info("[SUCCESS] Command executed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed with exit code {e.returncode}.")
            logger.error(f"       Command: {command}")
            if e.output:
                logger.error(f"       Output: {e.output}")
    
    def configure_firewall():
        """
        Checks and configures the UFW firewall to allow Nginx.
        """
        logger.info("\nChecking firewall status...")
        try:
            ufw_status = subprocess.run(
                "ufw status | grep 'Status: active'",
                shell=True,
                check=False,
                capture_output=True,
                text=True,
            )
            if ufw_status.returncode == 0:
                logger.info(
                    "UFW is active. Configuring firewall"
                    " to allow Nginx Full profile."
                )
                self.run_command(
                    "ufw allow 'Nginx Full'",
                    "Allowing Nginx traffic through the firewall...",
                )
            else:
                logger.info(
                    "UFW is not active or is not installed."
                    "Skipping firewall configuration."
                )
        except Exception as e:
            logger.error(f"An error occurred while checking firewall status: {e}")

    def setup_webgl_server(self):
        """Set up WebGL conformance test server with config validation."""
        port = self.config.get("port")

        if not port:
            self.unit.status = BlockedStatus("Missing required config: port")
            return

        self.unit.status = MaintenanceStatus("Setting up WebGL conformance test server")

        logger.info("Starting WebGL Nginx Server Setup...")

        # Step 1: Clone the WebGL repository
        if not os.path.exists(WEBGL_TESTS_PATH):
            # Create the directory if it doesn't exist
            self.run_command(
                f"mkdir -p {WEBGL_TESTS_PATH}",
                "Creating web server root directory...",
            )
            self.run_command(
                f"git clone {REPO_URL} {WEBGL_TESTS_PATH}",
                "Cloning WebGL repository to fixed location...",
            )
            # copy and patch for local testing
            self.run_command(
                "cp {}{}webgl-conformance-tests.html {}{}local-tests.html".format(
                    WEBGL_TESTS_PATH,
                    "/sdk/tests/",
                    WEBGL_TESTS_PATH,
                    "/sdk/tests/",
                ),
                "Copy webgl-conformance-tests.html to local-tests.html...",
            )
            self.run_command(
                f"patch {WEBGL_TESTS_PATH}/sdk/tests/local-tests.html local.patch",
                "Patch local-tests.html to download result automatically...",
            )
            # Ensure the user has ownership of the directory for future permissions
            self.un_command(
                f"chown -R $USER:$USER {WEBGL_TESTS_PATH}",
                "Setting correct file permissions...",
            )
        else:
            logger.info(
                "\nDirectory '{}' already exists. Skipping clone.".format(
                    WEBGL_TESTS_PATH
                )
            )

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

    def download_default_webgl_server_code(self) -> bool:
        """Download default WoL server script."""
        try:
            urllib.request.urlretrieve(
                self.config.get("webgl_server_script"),
                f"{webgl_install_destination}webgl_server.py",
            )
            logger.info(f"Downloaded file to {webgl_install_destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {repr(e)}")
            self.unit.status = BlockedStatus(
                "Failed to download WoL server script"
            )
            return False

    def start_webgl_server(self, port: int) -> bool:
        """Start default WoL server."""
        cmd = "uvicorn --app-dir {} webgl_server:app --host {} --port {}".format(
            webgl_install_destination, "0.0.0.0", port
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
        service_file = "/etc/systemd/system/webgl.service"
        with open(service_file, "w") as f:
            f.write(service_content)

        try:
            subprocess.check_call(["systemctl", "daemon-reload"])
            subprocess.check_call(["systemctl", "enable", "webgl"])
            subprocess.check_call(["systemctl", "restart", "webgl"])
            return True
        except CalledProcessError as e:
            logger.error(f"Failed to start webgl server: {repr(e)}")
            self.unit.status = BlockedStatus("Failed to setup service")
            return False


if __name__ == "__main__":  # pragma: nocover
    ops.main(WebGLCharm)

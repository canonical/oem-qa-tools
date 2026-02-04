#!/usr/bin/env python3

"""Charm the application."""

import os
import shutil
import logging
import subprocess
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
        charm_dir = self.framework.charm_dir
        src_file = os.path.join(charm_dir, "patches", "local.patch")
        dst_file = os.path.join("/tmp", "webgl", "local.patch")
        if os.path.exists(src_file):
            os.makedirs("/tmp/webgl", exist_ok=True)
            shutil.copy2(src_file, dst_file)
            self.unit.status = ops.MaintenanceStatus("Copied patch file")
        else:
            self.unit.status = ops.BlockedStatus("patch file missing")
        self.setup_webgl_server()

    def _on_config_or_upgrade(
        self, event: ops.ConfigChangedEvent | ops.UpgradeCharmEvent
    ):
        """Handle config-changed or upgrade-charm event."""
        self.setup_webgl_server()

    def run_command(self, command, message):
        """
        Executes a shell command and provides feedback.
        """
        logger.info("%s", message)
        try:
            subprocess.run(command, check=True, shell=True)
            logger.info("[SUCCESS] Command executed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error("Command failed with exit code %s.", e.returncode)
            logger.error("       Command: %s", command)
            if e.output:
                logger.error("       Output: %s", e.output)

    def configure_firewall(self):
        """
        Checks and configures the UFW firewall to allow Nginx.
        """
        logger.info("Checking firewall status...")
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
            logger.error(
                "An error occurred while checking firewall status: %s", e
            )

    def configue_nginx(self):
        """
        Checks and configures the Nginx.
        """
        # Create Nginx configuration file for WebGL tests
        nginx_conf_content = f"""
server {{
    listen 80;
    server_name localhost;

    root {CLONE_PATH};
    index index.html;

    location / {{
        # First attempt to serve request as file, then as directory
        try_files $uri $uri/ =404;
    }}
}}
"""
        local_conf_path = NGINX_CONFIG_FILE
        with open(local_conf_path, "w") as f:
            f.write(nginx_conf_content)

        logger.info("Created Nginx configuration file: %s", local_conf_path)

        # Move configuration to sites-available and link to sites-enabled
        self.run_command(
            f"mv {local_conf_path} {NGINX_SITES_AVAILABLE}",
            "Moving configuration to Nginx's sites-available directory...",
        )

        # Remove default site configuration
        self.run_command(
            f"rm -f {NGINX_SITES_ENABLED}default",
            "Removing default Nginx configuration link...",
        )

        # Create symbolic link to enable the new site
        self.run_command(
            "ln -s -f {}{} {}".format(
                NGINX_SITES_AVAILABLE, NGINX_CONFIG_FILE, NGINX_SITES_ENABLED
            ),
            "Creating symbolic link to enable the new site...",
        )

    def setup_webgl_server(self):
        """Set up WebGL conformance test server with config validation."""

        self.unit.status = MaintenanceStatus(
            "Setting up WebGL conformance test server"
        )

        logger.info("Starting WebGL Nginx Server Setup...")

        # Clone the WebGL repository
        if not os.path.exists(WEBGL_TESTS_PATH):
            # Create the directory if it doesn't exist
            logger.info("Creating web server root directory...")
            os.makedirs(WEBGL_TESTS_PATH, exist_ok=True)
            self.run_command(
                f"git clone {REPO_URL} {WEBGL_TESTS_PATH}",
                "Cloning WebGL repository to fixed location...",
            )
            # copy and patch for local testing
            src_file = os.path.join(CLONE_PATH, "webgl-conformance-tests.html")
            dst_file = os.path.join(CLONE_PATH, "local-tests.html")
            logger.info(
                "Copy webgl-conformance-tests.html to local-tests.html..."
            )
            shutil.copy2(src_file, dst_file)
            # the patch file is installed by hook
            self.run_command(
                f"patch {CLONE_PATH}/local-tests.html /tmp/webgl/local.patch",
                "Patch local-tests.html to download result automatically...",
            )
            # Ensure the user has ownership of the directory
            self.run_command(
                f"chown -R $USER:$USER {WEBGL_TESTS_PATH}",
                "Setting correct file permissions...",
            )
        else:
            logger.info(
                "Directory '%s' already exists. Skipping clone.",
                WEBGL_TESTS_PATH,
            )
            self.run_command(
                f"git -C {WEBGL_TESTS_PATH} pull",
                f"Updating {REPO_URL}...",
            )

        # Configure Nginx
        self.configue_nginx()
        # Configure firewall
        self.configure_firewall()
        self.start_webgl_server()
        logger.info("[SUCCESS] WebGL server setup complete!")

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

    def start_webgl_server(self) -> bool:
        """Start default WebGL Conformance Test Server."""

        try:
            subprocess.check_call(["systemctl", "daemon-reload"])
            subprocess.check_call(["systemctl", "restart", "nginx"])
            return True
        except CalledProcessError as e:
            logger.error("Failed to start webgl server: %s", e)
            self.unit.status = BlockedStatus("Failed to setup service")
            return False


if __name__ == "__main__":  # pragma: nocover
    ops.main(WebGLCharm)

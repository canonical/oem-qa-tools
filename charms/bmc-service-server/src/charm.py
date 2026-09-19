#!/usr/bin/env python3

"""Charm the application."""

import logging
import os
import shutil
import subprocess
from subprocess import CalledProcessError

import ops
from charmlibs import apt
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

logger = logging.getLogger(__name__)

BMC_SERVICE_ROOT = "/opt/bmc-service"
REPO_DIR = os.path.join(BMC_SERVICE_ROOT, "repo")
VENV_DIR = os.path.join(BMC_SERVICE_ROOT, ".venv")
STATE_FILE = os.path.join(BMC_SERVICE_ROOT, ".charm_repo_state")
SERVICE_NAME = "bmc-service"
SYSTEMD_UNIT = f"/etc/systemd/system/{SERVICE_NAME}.service"


class BMCServiceCharm(ops.CharmBase):
    """Charm for the BMC Manager FastAPI service."""

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
        if not self._install_apt_packages(
            ["git", "python3-pip", "python3-venv"]
        ):
            return
        if not self._setup_bmc_service():
            return
        self.unit.status = ActiveStatus("Ready")

    def _on_config_or_upgrade(
        self, event: ops.ConfigChangedEvent | ops.UpgradeCharmEvent
    ):
        """Handle config-changed or upgrade-charm event."""
        if not self._setup_bmc_service():
            return
        if not isinstance(
            self.unit.status, (BlockedStatus, MaintenanceStatus)
        ):
            self.unit.status = ActiveStatus("Ready")

    def _install_apt_packages(self, packages: list) -> bool:
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

    def _get_install_root(self) -> str:
        """
        Return the directory containing the bmc_manager package to pip install.
        """
        source_path = (self.config.get("source-path") or "").strip()
        if source_path:
            return os.path.join(REPO_DIR, source_path)
        return REPO_DIR

    def _clone_repo(self) -> bool:
        """Clone the configured repo and branch into REPO_DIR."""
        repo_url = self.config.get("repo-url") or ""
        branch = self.config.get("branch") or "main"
        if not repo_url:
            self.unit.status = BlockedStatus("Missing config: repo-url")
            return False

        self.unit.status = MaintenanceStatus("Cloning repository")
        os.makedirs(BMC_SERVICE_ROOT, exist_ok=True)
        if os.path.exists(REPO_DIR):
            shutil.rmtree(REPO_DIR)

        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--branch",
                    branch,
                    "--depth",
                    "1",
                    repo_url,
                    REPO_DIR,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(
                "Cloned %s (branch %s) to %s", repo_url, branch, REPO_DIR
            )
            return True
        except CalledProcessError as e:
            logger.error(
                "Git clone failed: %s %s", e.stderr or e.stdout or e.returncode
            )
            self.unit.status = BlockedStatus("Failed to clone repository")
            return False

    def _install_python_deps(self) -> bool:
        """Create venv and pip install bmc_manager from install root."""
        install_root = self._get_install_root()
        if not os.path.isdir(install_root):
            self.unit.status = BlockedStatus(
                f"Source path not found: {install_root}"
            )
            return False

        self.unit.status = MaintenanceStatus("Installing Python dependencies")
        os.makedirs(BMC_SERVICE_ROOT, exist_ok=True)

        # Create venv if missing
        if not os.path.isdir(VENV_DIR):
            try:
                subprocess.run(
                    [
                        os.environ.get("python3", "python3"),
                        "-m",
                        "venv",
                        VENV_DIR,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except CalledProcessError as e:
                logger.error("Failed to create venv: %s", e.stderr or e)
                self.unit.status = BlockedStatus("Failed to create venv")
                return False

        pip = os.path.join(VENV_DIR, "bin", "pip")
        try:
            subprocess.run(
                [pip, "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                text=True,
                cwd=BMC_SERVICE_ROOT,
            )
            subprocess.run(
                [pip, "install", "."],
                check=True,
                capture_output=True,
                text=True,
                cwd=install_root,
            )
            logger.info("Installed bmc_manager from %s", install_root)
            return True
        except CalledProcessError as e:
            logger.error(
                "pip install failed: %s", e.stderr or e.stdout or e.returncode
            )
            self.unit.status = BlockedStatus(
                "Failed to install Python package"
            )
            return False

    def _repo_config_changed(self) -> bool:
        """
        Return True if repo-url, branch, or source-path changed since last run.
        """
        repo_url = (self.config.get("repo-url") or "").strip()
        branch = (self.config.get("branch") or "main").strip()
        source_path = (self.config.get("source-path") or "").strip()
        current = f"{repo_url}\n{branch}\n{source_path}"
        if not os.path.isfile(STATE_FILE):
            return True
        try:
            with open(STATE_FILE) as f:
                return f.read() != current
        except OSError:
            return True

    def _write_repo_state(self) -> None:
        """Record current repo config so we can detect changes."""
        repo_url = (self.config.get("repo-url") or "").strip()
        branch = (self.config.get("branch") or "main").strip()
        source_path = (self.config.get("source-path") or "").strip()
        os.makedirs(BMC_SERVICE_ROOT, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(f"{repo_url}\n{branch}\n{source_path}")

    def _setup_bmc_service(self) -> bool:
        """Clone repo (if needed), install deps, and start systemd unit."""
        need_clone = not os.path.isdir(REPO_DIR) or self._repo_config_changed()

        if need_clone and not self._clone_repo():
            return False
        if need_clone:
            self._write_repo_state()
        if not self._install_python_deps():
            return False

        port = self.config.get("port") or 8000
        log_level = (self.config.get("log-level") or "info").strip().upper()

        self.unit.status = MaintenanceStatus("Configuring BMC service")
        uvicorn_bin = os.path.join(VENV_DIR, "bin", "uvicorn")
        exec_start = (
            f"{uvicorn_bin} bmc_manager.bmc_service:app --host 0.0.0.0 "
            f"--port {port}"
        )

        service_content = f"""[Unit]
Description=BMC Manager API service
After=network.target

[Service]
ExecStart={exec_start}
Restart=on-failure
Environment=BMC_LOG_LEVEL={log_level}

[Install]
WantedBy=multi-user.target
"""
        try:
            with open(SYSTEMD_UNIT, "w") as f:
                f.write(service_content)
            subprocess.check_call(["systemctl", "daemon-reload"])
            subprocess.check_call(["systemctl", "enable", SERVICE_NAME])
            subprocess.check_call(["systemctl", "restart", SERVICE_NAME])
            return True
        except CalledProcessError as e:
            logger.error("Failed to start BMC service: %s", e)
            self.unit.status = BlockedStatus("Failed to setup service")
            return False


if __name__ == "__main__":  # pragma: nocover
    ops.main(BMCServiceCharm)

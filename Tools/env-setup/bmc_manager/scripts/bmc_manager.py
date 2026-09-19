import argparse
import json
import logging
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import urllib3

try:
    from bmc_manager.utils.config import config as _bmc_config

    _REDFISH_REQUEST_TIMEOUT: int = _bmc_config.redfish_request_timeout
except ImportError:
    _REDFISH_REQUEST_TIMEOUT = 5

# Disable SSL warnings for Redfish (Self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


class BMCManager(ABC):
    """
    Abstract Base Class that defines the interface for BMC management.
    """

    def __init__(self, ip: str, username: str, password: str) -> None:
        self.ip: str = ip
        self.username: str = username
        self.password: str = password

    @abstractmethod
    def validate_connection(self) -> bool:
        """Checks if credentials work without using Ping."""
        pass

    @abstractmethod
    def list_users(self) -> Dict[str, Any]:
        """Lists users from the BMC. Returns dict with 'success' and data."""
        pass

    @abstractmethod
    def list_actions(self) -> Dict[str, Any]:
        """Lists supported power/reset actions. Returns dict with data."""
        pass

    @abstractmethod
    def run_action(self, action_name: str) -> Dict[str, Any]:
        """Execute a power action. Returns dict with status/result."""
        pass

    @abstractmethod
    def get_power_state(self) -> Dict[str, Any]:
        """Return chassis power state. Returns dict with power_state."""
        pass


class IpmiManager(BMCManager):
    """
    Implementation using the 'ipmitool' CLI command.
    """

    def __init__(
        self, ip: str, username: str, password: str, cipher_suite: int = 17
    ) -> None:
        super().__init__(ip, username, password)
        self.cipher_suite: int = cipher_suite

    def _run_cmd(
        self, args: List[str], verbose: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Helper to run ipmitool subprocess."""
        # Base command with Cipher Suite 17 (standard for modern servers)
        cmd: List[str] = [
            "ipmitool",
            "-I",
            "lanplus",
            "-H",
            self.ip,
            "-U",
            self.username,
            "-P",
            self.password,
            "-C",
            str(self.cipher_suite),
        ]

        if verbose:
            cmd.insert(1, "-vv")  # Add verbose if requested

        cmd.extend(args)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        except FileNotFoundError:
            logger.error("Error: 'ipmitool' is not installed on this system.")
            sys.exit(1)

    def validate_connection(self) -> bool:
        logger.info(f"[IPMI] Validating connection to {self.ip}...")
        # We use 'mc info' as a lightweight handshake check
        result = self._run_cmd(["mc", "info"])

        if result.returncode != 0:
            err = result.stderr.lower()
            if "unauthorized name" in err or "password" in err:
                logger.error(
                    "[-] Authentication Failed: "
                    "Invalid Username or Password."
                )
            elif "cipher" in err or "authentication type" in err:
                logger.error(
                    "[-] Protocol Error: Cipher Suite mismatch. "
                    "Try changing Cipher ID."
                )
            elif "timeout" in err:
                logger.error(
                    "[-] Connection Timeout: "
                    "BMC unreachable (UDP Port 623)."
                )
            else:
                logger.error(f"[-] Unknown Error: {result.stderr.strip()}")
            return False

        logger.info("[+] Connection Verified (IPMI v2.0)")
        return True

    def list_users(self) -> Dict[str, Any]:
        logger.info("\n--- IPMI User List (Channel 1) ---")
        result = self._run_cmd(["user", "list", "1"])
        if result.returncode != 0:
            logger.error(f"Error fetching users: {result.stderr}")
            return {"success": False, "error": result.stderr.strip()}
        logger.info(result.stdout)
        return {"success": True, "output": result.stdout}

    def list_actions(self) -> Dict[str, Any]:
        actions = ["status", "on", "off", "cycle", "reset", "soft"]
        logger.info("\n--- IPMI Supported Actions (Standard) ---")
        logger.info(
            "IPMI actions are standardized. "
            "Available commands via this script:"
        )
        for a in actions:
            logger.info(f" - {a}")
        return {"success": True, "actions": actions}

    def run_action(self, action_name: str) -> Dict[str, Any]:
        logger.info(f"\n[IPMI] Executing Action: {action_name}")
        cmd_map: Dict[str, List[str]] = {
            "status": ["chassis", "status"],
            "on": ["chassis", "power", "on"],
            "off": ["chassis", "power", "off"],
            "cycle": ["chassis", "power", "cycle"],
            "reset": ["chassis", "power", "reset"],
            "soft": ["chassis", "power", "soft"],
        }

        if action_name not in cmd_map:
            msg = f"Action '{action_name}' not supported by IPMI handler."
            logger.error(f"Error: {msg}")
            return {"success": False, "error": msg}

        result = self._run_cmd(cmd_map[action_name])
        if result.returncode == 0:
            out = result.stdout.strip()
            logger.info(f"[+] Success: {out}")
            return {"success": True, "message": "Success", "output": out}
        err = result.stderr.strip()
        logger.error(f"[-] Failed: {err}")
        return {"success": False, "error": err, "output": err}

    def get_power_state(self) -> Dict[str, Any]:
        """
        Chassis power status via ipmitool; only "on" or "off" (binary).
        See: https://codeberg.org/IPMITool/ipmitool/src/branch/master/
        lib/ipmi_chassis.c (ipmi_chassis_print_power_status)
        """
        logger.info("\n[IPMI] Chassis power status")
        result = self._run_cmd(["chassis", "power", "status"])
        if result.returncode != 0:
            err = result.stderr.strip()
            logger.error(f"[-] Failed: {err}")
            return {"success": False, "error": err}
        out = result.stdout.strip()
        logger.info(out)
        if "is on" in out.lower():
            state = "on"
        elif "is off" in out.lower():
            state = "off"
        else:
            state = out
        return {"success": True, "power_state": state}


class RedfishManager(BMCManager):
    """
    Implementation using Redfish (HTTPS/REST).

    PowerState and reset semantics follow DMTF Redfish; schema reference:
    https://redfish.dmtf.org/schemas/v1/Resource.json

    PowerState enum (Resource.PowerState): On, Off, PoweringOn,
    PoweringOff, Paused. ResetType (ComputerSystem.Reset) is discovered
    at runtime from Actions/#ComputerSystem.Reset AllowableValues.
    """

    # Request timeout in seconds for GET/POST (from config when available)
    _REQUEST_TIMEOUT: int = _REDFISH_REQUEST_TIMEOUT

    def __init__(self, ip: str, username: str, password: str) -> None:
        super().__init__(ip, username, password)
        self.base_url: str = f"https://{self.ip}/redfish/v1"
        self.auth: Tuple[str, str] = (self.username, self.password)
        self.system_id_path: Optional[str] = None
        # Cache for discovered actions
        self.available_actions: Dict[str, Dict[str, str]] = {}
        # Reuse connections to this BMC
        self._session: requests.Session = requests.Session()
        self._session.verify = False
        self._session.auth = self.auth

    def _get_request(self, endpoint: str) -> Optional[requests.Response]:
        """
        Smart GET request that handles absolute, relative,
        and redfish-rooted paths.
        """
        try:
            url: str = ""
            # 1. Handle Absolute URL (http://...)
            if endpoint.startswith("http"):
                url = endpoint
            # 2. Handle Path that already contains /redfish/v1
            elif endpoint.startswith("/redfish/v1"):
                url = f"https://{self.ip}{endpoint}"
            # 3. Handle Relative Path (append to base_url)
            else:
                # Ensure we don't double-slash
                clean_end = endpoint.lstrip("/")
                url = f"{self.base_url}/{clean_end}"

            response = self._session.get(url, timeout=self._REQUEST_TIMEOUT)
            return response
        except requests.exceptions.ConnectTimeout:
            logger.error("[-] Connection Timeout (TCP Port 443)")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("[-] Connection Error (Check IP or Firewall)")
            return None

    def validate_connection(self) -> bool:
        logger.info(f"[Redfish] Validating connection to {self.ip}...")
        # Check root Redfish service
        response = self._get_request("/redfish/v1")

        if response is None:
            return False

        if response.status_code == 200:
            logger.info("[+] Connection Verified (Redfish)")
            discover_err = self._discover_system_id()
            if discover_err == "Authentication failed":
                logger.error("[-] Authentication Failed: HTTP 401/403.")
                return False
            return True
        elif response.status_code in [401, 403]:
            logger.error(
                "[-] Authentication Failed: " "HTTP 401/403 Unauthorized."
            )
            return False
        else:
            logger.error(f"[-] Unexpected Status: {response.status_code}")
            return False

    def _discover_system_id(self) -> Optional[str]:
        """
        Find the unique System URL (e.g. /Systems/IGX_BMC_System_0).

        Returns:
            None on success; "Authentication failed" on 401/403;
            "No Systems found" when 200 but no Members.
        """
        resp = self._get_request("/Systems")
        if not resp:
            return "No Systems found"
        if resp.status_code in [401, 403]:
            return "Authentication failed"
        if resp.status_code != 200:
            return "No Systems found"
        data = resp.json()
        if not data.get("Members"):
            logger.error("[-] No Systems found in Redfish collection.")
            return "No Systems found"
        raw_id = data["Members"][0]["@odata.id"]
        if raw_id.startswith("http"):
            self.system_id_path = urlparse(raw_id).path
        else:
            self.system_id_path = raw_id
        return None

    def _check_response(
        self,
        resp: Optional[requests.Response],
        context: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return error dict if response is missing, 401/403, or non-200.

        Otherwise return None (caller proceeds).
        """
        if not resp:
            return {"success": False, "error": "No response"}
        if resp.status_code in [401, 403]:
            return {"success": False, "error": "Authentication failed"}
        if resp.status_code != 200:
            return {
                "success": False,
                "error": "{}: {}".format(context, resp.status_code),
            }
        return None

    def list_users(self) -> Dict[str, Any]:
        logger.info("\n--- Redfish User List ---")
        resp = self._get_request("/AccountService/Accounts")
        err = self._check_response(resp, "Failed to fetch accounts")
        if err:
            return err
        members = resp.json().get("Members", [])
        users: List[Dict[str, Any]] = []
        logger.info(f"{'ID':<10} {'Name':<20} " f"{'Role':<15} {'Enabled'}")
        logger.info("-" * 60)
        for m in members:
            u_resp = self._get_request(m["@odata.id"])
            if u_resp and u_resp.status_code == 200:
                u = u_resp.json()
                uid = u.get("Id", "N/A")
                name = u.get("UserName", "N/A")
                role = u.get("RoleId", "N/A")
                enabled = u.get("Enabled", False)
                users.append(
                    {"id": uid, "name": name, "role": role, "enabled": enabled}
                )
                logger.info(f"{uid:<10} {name:<20} " f"{role:<15} {enabled}")
        return {"success": True, "users": users}

    def list_actions(self) -> Dict[str, Any]:
        if not self.system_id_path:
            discover_err = self._discover_system_id()
            if discover_err is not None:
                return {"success": False, "error": discover_err}

        logger.info(f"\n--- Redfish Actions for {self.system_id_path} ---")
        resp = self._get_request(self.system_id_path)
        err = self._check_response(resp, "Failed to get system")
        if err:
            return err

        data = resp.json()
        actions_data = data.get("Actions", {})
        self.available_actions = {}
        action_names: List[str] = []

        for key, val in actions_data.items():
            if "Reset" in key:
                target = val["target"]
                logger.info(f"Action Endpoint: {key}")
                logger.info(f"Target: {target}")
                allowable: List[str] = []
                for k, v in val.items():
                    if "AllowableValues" in k:
                        allowable = v
                if not allowable and "@Redfish.ActionInfo" in val:
                    ai_path = val["@Redfish.ActionInfo"]
                    ai_resp = self._get_request(ai_path)
                    if ai_resp and ai_resp.status_code == 200:
                        ai_data = ai_resp.json()
                        for param in ai_data.get("Parameters", []):
                            if param.get("Name") == "ResetType":
                                allowable = param.get("AllowableValues", [])
                logger.info("Supported Commands:")
                for cmd in allowable:
                    logger.info(f"  - {cmd}")
                    action_names.append(cmd)
                    self.available_actions[cmd.lower()] = {
                        "name": cmd,
                        "target": target,
                    }
        return {"success": True, "actions": action_names}

    def run_action(self, action_name: str) -> Dict[str, Any]:
        if not self.available_actions:
            logger.info("Discovering capabilities...")
            list_result = self.list_actions()
            if not list_result.get("success"):
                return list_result

        if not self.available_actions:
            err = "No power actions discovered on this system."
            logger.error(f"[-] Error: {err}")
            return {"success": False, "error": err}

        user_input = action_name.lower()
        selected_cmd: Optional[str] = None
        target_url: Optional[str] = None

        # 1. Check for Direct Match
        # (e.g., user typed "forceoff")
        if user_input in self.available_actions:
            cmd_data = self.available_actions[user_input]
            selected_cmd = cmd_data["name"]
            target_url = cmd_data["target"]

        # 2. Smart Alias Resolution
        # (Map generic words to available capabilities)
        else:
            # Preference list: Generic Alias ->
            # [List of Redfish Commands to try]
            alias_map: Dict[str, List[str]] = {
                "on": ["on", "forceon"],
                "off": ["forceoff", "gracefulshutdown", "poweroff"],
                "reset": ["forcerestart", "gracefulrestart", "powercycle"],
                "soft": ["gracefulshutdown"],
                "cycle": ["powercycle"],
            }
            if user_input in alias_map:
                for p in alias_map[user_input]:
                    if p in self.available_actions:
                        cmd_data = self.available_actions[p]
                        selected_cmd = cmd_data["name"]
                        target_url = cmd_data["target"]
                        logger.info(
                            f"[Info] Mapping alias '{action_name}' "
                            f"-> '{selected_cmd}'"
                        )
                        break

        if not selected_cmd or not target_url:
            supported = ", ".join(
                [v["name"] for v in self.available_actions.values()]
            )
            err = (
                f"Action '{action_name}' is not supported. "
                f"Supported: {supported}"
            )
            logger.error(f"[-] Error: {err}")
            return {"success": False, "error": err}

        logger.info(f"\n[Redfish] Sending '{selected_cmd}' to {target_url}...")
        payload: Dict[str, str] = {"ResetType": selected_cmd}
        headers: Dict[str, str] = {"Content-Type": "application/json"}

        try:
            full_url: str = ""
            if target_url.startswith("http"):
                full_url = target_url
            elif target_url.startswith("/redfish/v1"):
                full_url = f"https://{self.ip}{target_url}"
            else:
                full_url = (
                    f"https://{self.ip}/redfish/v1/"
                    f"{target_url.lstrip('/')}"
                )
            post_resp = self._session.post(
                full_url,
                json=payload,
                headers=headers,
                timeout=self._REQUEST_TIMEOUT,
            )
            if post_resp.status_code in [200, 202, 204]:
                msg = f"Command Accepted ({post_resp.status_code})"
                logger.info(f"[+] Success: {msg}")
                return {"success": True, "message": msg}
            err = f"HTTP {post_resp.status_code}: {post_resp.text}"
            logger.error(f"[-] Failed: {err}")
            return {"success": False, "error": err}
        except Exception as e:
            logger.error(f"[-] Exception: {e}")
            return {"success": False, "error": str(e)}

    def get_power_state(self) -> Dict[str, Any]:
        """
        Read PowerState from system resource (DMTF PowerState enum:
        On, Off, PoweringOn, PoweringOff, Paused).
        """
        if not self.system_id_path:
            discover_err = self._discover_system_id()
            if discover_err is not None:
                return {"success": False, "error": discover_err}
        resp = self._get_request(self.system_id_path)
        err = self._check_response(resp, "Failed to get system")
        if err:
            return err
        data = resp.json()
        power_state = data.get("PowerState")
        if power_state is None:
            return {"success": False, "error": "PowerState not in response"}
        logger.info(f"\n[Redfish] PowerState: {power_state}")
        return {"success": True, "power_state": power_state}

    def close(self) -> None:
        """Close the HTTP session and release connections."""
        self._session.close()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Build argument parser and return parsed namespace."""
    parser = argparse.ArgumentParser(
        description="BMC Manager (Redfish & IPMI)"
    )
    parser.add_argument("ip", help="BMC IP Address")
    parser.add_argument("user", help="BMC Username")
    parser.add_argument("password", help="BMC Password")
    parser.add_argument(
        "protocol",
        choices=["redfish", "ipmitool"],
        help="Control protocol to use",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list-users", action="store_true", help="List all users"
    )
    group.add_argument(
        "--list-actions",
        action="store_true",
        help="List supported power actions",
    )
    group.add_argument(
        "--action",
        help=("Perform power action " "(on, off, reset, soft, cycle, status)"),
    )
    group.add_argument(
        "--power-state",
        action="store_true",
        help="Get current chassis power state",
    )
    out = parser.add_mutually_exclusive_group()
    out.add_argument(
        "--txt",
        action="store_true",
        help="Output result as plain text only (e.g. Supported Commands)",
    )
    out.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON only (default)",
    )
    return parser.parse_args(argv)


def _run_mode(manager: BMCManager, args: argparse.Namespace) -> Dict[str, Any]:
    """Run selected mode (list-users, list-actions, action, power-state)."""
    if args.list_users:
        return manager.list_users()
    if args.list_actions:
        return manager.list_actions()
    if args.action:
        return manager.run_action(args.action)
    if getattr(args, "power_state", False):
        return manager.get_power_state()
    return {"success": False, "error": "No mode selected"}


def main() -> None:
    args = parse_args()

    manager: BMCManager
    if args.protocol == "ipmitool":
        manager = IpmiManager(args.ip, args.user, args.password)
    else:
        manager = RedfishManager(args.ip, args.user, args.password)

    output_txt = getattr(args, "txt", False)
    if not output_txt:
        root = logging.getLogger()
        old_level = root.level
        root.setLevel(logging.WARNING)

    if not manager.validate_connection():
        sys.exit(1)

    result = _run_mode(manager, args)

    if not output_txt:
        root = logging.getLogger()
        root.setLevel(old_level)
        print(json.dumps(result, indent=2))
    elif isinstance(result.get("success"), bool) and not result["success"]:
        err = result.get("error", "Unknown error")
        print(err, file=sys.stderr)

    if isinstance(result.get("success"), bool) and not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Execution utilities for BMC service."""

import inspect
import ipaddress
import logging
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FuturesTimeoutError,
)
from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Optional, Tuple, TypeVar

import requests

from bmc_manager.scripts.bmc_manager import (
    BMCManager,
    IpmiManager,
    RedfishManager,
)
from bmc_manager.utils.config import Config, config
from bmc_manager.utils.errors import ERRORS, ErrorDef, ServiceError

_T = TypeVar("_T")
logger = logging.getLogger(__name__)


# Input validation
def validate_ip(ip: str) -> None:
    """Validate IP address format."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise ServiceError(ERRORS["INVALID_IP"])


def validate_username(username: str) -> None:
    """Validate username."""
    if not username or len(username) < 1:
        raise ServiceError(
            ERRORS["INVALID_USERNAME"],
            "Username cannot be empty",
        )
    if len(username) > 64:
        raise ServiceError(
            ERRORS["INVALID_USERNAME"],
            "Username too long (max 64 characters)",
        )


def validate_password(password: str) -> None:
    """Validate password."""
    if not password:
        raise ServiceError(
            ERRORS["INVALID_PASSWORD"],
            "Password cannot be empty",
        )


def validate_protocol(protocol: str) -> None:
    """Validate protocol."""
    if protocol not in ["redfish", "ipmitool"]:
        raise ServiceError(ERRORS["INVALID_PROTOCOL"])


def validate_cipher_suite(cipher_suite: Optional[int]) -> None:
    """Validate cipher suite."""
    if cipher_suite is not None and (cipher_suite < 0 or cipher_suite > 17):
        raise ServiceError(ERRORS["INVALID_CIPHER_SUITE"])


@dataclass(kw_only=True)
class BMCRequest:
    """Base request dataclass with common BMC connection fields."""

    ip: str
    username: str
    password: str
    protocol: Literal["redfish", "ipmitool"]
    cipher_suite: Optional[int] = 17

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        validate_ip(self.ip)
        validate_username(self.username)
        validate_password(self.password)
        validate_protocol(self.protocol)
        validate_cipher_suite(self.cipher_suite)


@dataclass(kw_only=True)
class BMCExecuteRequest(BMCRequest):
    """Generic extensible request for calling any BMC_Manager method."""

    method: str
    params: Optional[Dict[str, Any]] = None
    delay: Optional[float] = None
    retry_times: Optional[int] = 1

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        super().__post_init__()
        if self.params is None:
            self.params = {}


@dataclass(kw_only=True)
class BMCValidateRequest(BMCRequest):
    """Request for validating BMC connection."""


@dataclass(kw_only=True)
class BMCListUsersRequest(BMCRequest):
    """Request for listing BMC users."""


@dataclass(kw_only=True)
class BMCListActionsRequest(BMCRequest):
    """Request for listing available BMC actions."""


@dataclass(kw_only=True)
class BMCPowerStateRequest(BMCRequest):
    """Request for getting current chassis power state."""


# Stable power states (polling stops when reached)
_STABLE_POWER_STATES = frozenset({"On", "Off", "on", "off"})


@dataclass(kw_only=True)
class BMCActionRequest(BMCRequest):
    """Request for executing a power action."""

    action: str
    delay: Optional[float] = None
    retry_times: Optional[int] = 1
    wait_for_state_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        super().__post_init__()
        if self.wait_for_state_seconds is not None:
            w = float(self.wait_for_state_seconds)
            if w < 0:
                raise ServiceError(
                    ERRORS["INVALID_PARAMETERS"],
                    "wait_for_state_seconds must be >= 0",
                )
            max_wait = config.max_wait_for_state_seconds
            if w > max_wait:
                raise ServiceError(
                    ERRORS["INVALID_PARAMETERS"],
                    "wait_for_state_seconds must be <= {}".format(max_wait),
                )


def create_bmc_manager(
    ip: str,
    username: str,
    password: str,
    protocol: Literal["redfish", "ipmitool"],
    cipher_suite: Optional[int] = 17,
) -> BMCManager:
    """
    Factory function to create appropriate BMC manager instance.

    Args:
        ip: BMC IP address
        username: BMC username
        password: BMC password
        protocol: Protocol to use (redfish or ipmitool)
        cipher_suite: Cipher suite for IPMI (default: 17)

    Returns:
        BMCManager instance (IpmiManager or RedfishManager)
    """
    if protocol == "ipmitool":
        return IpmiManager(ip, username, password, cipher_suite)
    else:
        return RedfishManager(ip, username, password)


def to_execute_request(
    request: BMCRequest,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    delay: Optional[float] = None,
    retry_times: Optional[int] = None,
) -> BMCExecuteRequest:
    """
    Convert a request carrying BMC connection fields into BMCExecuteRequest.
    Helper for convenience endpoints.
    """
    return BMCExecuteRequest(
        ip=request.ip,
        username=request.username,
        password=request.password,
        protocol=request.protocol,
        cipher_suite=request.cipher_suite,
        method=method,
        params=params or {},
        delay=delay,
        retry_times=retry_times,
    )


def action_to_execute_request(
    request: BMCActionRequest,
) -> BMCExecuteRequest:
    """
    Convert BMCActionRequest to BMCExecuteRequest for run_action.
    Helper for /action and /action/async endpoints.
    """
    return to_execute_request(
        request=request,
        method="run_action",
        params={"action_name": request.action},
        delay=request.delay,
        retry_times=request.retry_times,
    )


def simple_convenience_endpoint(
    request: BMCRequest, method: str
) -> BMCExecuteRequest:
    """
    Convert a simple BMCRequest to BMCExecuteRequest.
    Helper for /validate, /list-users, /list-actions endpoints.
    """
    return to_execute_request(request=request, method=method)


def validate_and_get_error_code(
    manager: BMCManager, protocol: str
) -> Optional[Tuple[ErrorDef, str]]:
    """
    Validate connection and return an ErrorDef + details if validation fails.

    Args:
        manager: BMCManager instance
        protocol: Protocol type (redfish or ipmitool)

    Returns:
        None if validation succeeds, else (ErrorDef, details)
    """
    try:
        if manager.validate_connection():
            return None

        # Redfish: probe status for better classification
        if protocol == "redfish" and isinstance(manager, RedfishManager):
            test_resp = manager._get_request("/redfish/v1")
            if test_resp is None:
                return (
                    ERRORS["CONNECTION_TIMEOUT"],
                    "BMC unreachable (TCP Port 443)",
                )
            if test_resp.status_code in [401, 403]:
                return (
                    ERRORS["HTTP_UNAUTHORIZED"],
                    "HTTP {} Unauthorized".format(test_resp.status_code),
                )
            return (
                ERRORS["UNEXPECTED_ERROR"],
                "HTTP Status: {}".format(test_resp.status_code),
            )

        # IPMI: without stderr capture, best-effort classification
        return (
            ERRORS["AUTH_FAILED"],
            "Invalid username or password, or connection error",
        )
    except requests.exceptions.ConnectTimeout:
        err = ERRORS["CONNECTION_TIMEOUT"]
        return (err, err.default_details)
    except requests.exceptions.ConnectionError:
        return (
            ERRORS["CONNECTION_TIMEOUT"],
            "BMC unreachable (Check IP or Firewall)",
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            err = ERRORS["CONNECTION_TIMEOUT"]
            return (err, err.default_details)
        if "cipher" in error_msg or "protocol" in error_msg:
            err = ERRORS["PROTOCOL_ERROR"]
            return (err, err.default_details)
        return (ERRORS["UNEXPECTED_ERROR"], str(e))


# Executor for run_with_timeout; avoids signal.SIGALRM (main-thread only).
# Must have at least as many workers as the service executor so it never
# becomes the bottleneck when BMC_MAX_WORKERS is raised.
_timeout_executor = ThreadPoolExecutor(
    max_workers=config.max_workers,
    thread_name_prefix="bmc_timeout",
)


def run_with_timeout(
    seconds: int, func: Callable[..., _T], *args: Any, **kwargs: Any
) -> _T:
    """
    Run func(*args, **kwargs) with a timeout. Thread-safe (no signals).

    Raises TimeoutError if the call does not complete within `seconds`.
    """
    if seconds <= 0:
        return func(*args, **kwargs)
    future = _timeout_executor.submit(lambda: func(*args, **kwargs))
    try:
        return future.result(timeout=seconds)
    except FuturesTimeoutError:
        raise TimeoutError("Operation timed out")


def execute_bmc_method(
    manager: BMCManager,
    method_name: str,
    params: Optional[Dict[str, Any]] = None,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Generic method executor using introspection.

    Args:
        manager: BMCManager instance
        method_name: Name of method to call
        params: Dictionary of method parameters
        config: Service configuration (for timeout)

    Returns:
        Dictionary with result and method name

    Raises:
        ServiceError: If method doesn't exist or execution fails
    """
    params = params or {}
    if config is None:
        config = Config()

    # Validate method exists
    if not hasattr(manager, method_name):
        raise ServiceError(
            ERRORS["METHOD_NOT_FOUND"],
            "Method '{}' not found on BMC_Manager".format(method_name),
        )

    method = getattr(manager, method_name)

    # Validate method is callable and public
    if not callable(method):
        raise ServiceError(
            ERRORS["METHOD_NOT_CALLABLE"],
            "'{}' is not a callable method".format(method_name),
        )

    if method_name.startswith("_"):
        raise ServiceError(
            ERRORS["PRIVATE_METHOD"],
            "'{}' is a private method and cannot be called".format(
                method_name
            ),
        )

    # Get method signature
    try:
        sig = inspect.signature(method)
    except ValueError as e:
        raise ServiceError(
            ERRORS["METHOD_NOT_FOUND"],
            "Could not get signature for method '{}': {}".format(
                method_name, e
            ),
        )

    # Bind parameters to method signature
    try:
        bound_args = sig.bind(**params)
        bound_args.apply_defaults()
    except TypeError as e:
        raise ServiceError(
            ERRORS["INVALID_PARAMETERS"],
            "Parameter mismatch for method '{}': {}".format(method_name, e),
        )

    # Execute method with timeout (thread-safe; no signals)
    try:
        result = run_with_timeout(
            config.timeout,
            method,
            *bound_args.args,
            **bound_args.kwargs,
        )
    except TimeoutError:
        raise ServiceError(
            ERRORS["TIMEOUT"],
            "Method execution timed out after {} seconds".format(
                config.timeout
            ),
        )

    # Return result
    return {"result": result, "method": method_name}


def _poll_power_state_until_stable(
    manager: BMCManager,
    wait_sec: float,
    config: Config,
) -> Tuple[Optional[str], bool]:
    """
    Poll get_power_state until On/Off (or on/off) or timeout.

    Returns (last_power_state, power_state_stable).
    """
    poll_interval = config.power_state_poll_interval_seconds
    deadline = time.time() + wait_sec
    power_state_stable = False
    last_power_state: Optional[str] = None

    while time.time() < deadline:
        time.sleep(poll_interval)
        state_result = run_with_timeout(
            config.timeout, manager.get_power_state
        )
        if not state_result.get("success"):
            return last_power_state, False
        last_power_state = state_result.get("power_state")
        if last_power_state in _STABLE_POWER_STATES:
            return last_power_state, True

    return last_power_state, power_state_stable


def run_action_with_optional_wait(
    request: BMCActionRequest,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Run power action via run_job_with_retry (retries + delay); optionally
    poll get_power_state until stable or timeout.

    Reuses run_job_with_retry so delay and retry_times apply to the action.
    Returns a single dict with success, message, error, output (from action),
    and if wait was requested: power_state, power_state_stable.
    """
    if config is None:
        config = Config()

    execute_request = action_to_execute_request(request)
    raw = run_job_with_retry(execute_request, config)
    action_result = raw["result"]

    if not action_result.get("success"):
        return action_result

    wait_sec = request.wait_for_state_seconds or 0
    if wait_sec <= 0:
        return action_result

    manager = create_bmc_manager(
        request.ip,
        request.username,
        request.password,
        request.protocol,
        request.cipher_suite,
    )
    try:
        validation = validate_and_get_error_code(manager, request.protocol)
        if validation is not None:
            err, details = validation
            raise ServiceError(err, details)

        power_state, power_state_stable = _poll_power_state_until_stable(
            manager, wait_sec, config
        )
        action_result["power_state"] = power_state
        action_result["power_state_stable"] = power_state_stable
        return action_result
    finally:
        if hasattr(manager, "close"):
            manager.close()


def run_job_with_retry(
    request: BMCExecuteRequest,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Shared execution logic for both sync and async paths.

    Applies:
    - optional validation (skip validate_connection itself)
    - retry_times
    - delay between retries (for attempt > 0). Uses min_retry_delay_seconds
      as default if not provided, and enforces minimum delay to avoid tight
      retry loops.

    Args:
        request: BMC execute request
        config: Service configuration (for timeout)

    Returns:
        Dictionary with result and method name

    Raises:
        ServiceError: If all retry attempts fail
    """
    if config is None:
        config = Config()

    retry_times = request.retry_times or 1
    # Use min_retry_delay_seconds as default if delay not provided
    if request.delay is not None:
        delay = max(
            float(request.delay), float(config.min_retry_delay_seconds)
        )
    else:
        delay = float(config.min_retry_delay_seconds)

    last_exc: Optional[Exception] = None

    for attempt in range(retry_times):
        if attempt > 0:
            logger.debug(
                "Waiting {} seconds before retry {}".format(delay, attempt)
            )
            time.sleep(delay)

        manager = None
        try:
            manager = create_bmc_manager(
                request.ip,
                request.username,
                request.password,
                request.protocol,
                request.cipher_suite,
            )

            if request.method != "validate_connection":
                validation = validate_and_get_error_code(
                    manager,
                    request.protocol,
                )
                if validation is not None:
                    err, details = validation
                    raise ServiceError(err, details)

            return execute_bmc_method(
                manager, request.method, request.params, config
            )
        except ServiceError as e:
            last_exc = e
        except Exception as e:
            last_exc = e
        finally:
            if manager is not None and hasattr(manager, "close"):
                manager.close()

    # Retries exhausted
    if isinstance(last_exc, ServiceError):
        details = "{}: {}".format(last_exc.err.message, last_exc.details)
    elif last_exc is not None:
        details = str(last_exc)
    else:
        details = "Unknown error"

    raise ServiceError(ERRORS["RETRY_EXHAUSTED"], details)

"""Configuration management for BMC service."""

import os
from dataclasses import dataclass


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    """Service configuration from environment variables."""

    max_workers: int = int(os.getenv("BMC_MAX_WORKERS", "10"))
    timeout: int = int(os.getenv("BMC_TIMEOUT", "30"))
    log_level: str = os.getenv("BMC_LOG_LEVEL", "INFO")
    enable_cors: bool = os.getenv("BMC_ENABLE_CORS", "false").lower() == "true"
    min_retry_delay_seconds: float = _get_float_env(
        "BMC_MIN_RETRY_DELAY_SECONDS", 0.2
    )
    # Max number of tasks to retain; 0 means no cap (only time-based retention)
    max_tasks: int = int(os.getenv("BMC_MAX_TASKS", "0"))
    # Task retention: tasks older than this many days are removed
    # (GET /tasks returns "expired")
    task_retention_days: int = int(os.getenv("BMC_TASK_RETENTION_DAYS", "7"))
    # Redfish HTTP request timeout in seconds (GET/POST to BMC)
    redfish_request_timeout: int = int(
        os.getenv("BMC_REDFISH_REQUEST_TIMEOUT", "5")
    )
    # Polling interval in seconds when waiting for power state to become stable
    power_state_poll_interval_seconds: float = _get_float_env(
        "BMC_POWER_STATE_POLL_INTERVAL", 1.5
    )
    # Maximum allowed wait_for_state_seconds in action requests
    # (validation cap)
    max_wait_for_state_seconds: int = int(
        os.getenv("BMC_MAX_WAIT_FOR_STATE_SECONDS", "300")
    )


config = Config()

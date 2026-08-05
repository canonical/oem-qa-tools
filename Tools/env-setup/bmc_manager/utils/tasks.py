"""Task tracking utilities for BMC service."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from bmc_manager.utils.config import config
from bmc_manager.utils.errors import ERRORS, ServiceError

# From config; tasks older than this are removed (user gets "expired" message)
TASK_RETENTION_DAYS = config.task_retention_days
TASK_RETENTION_SECONDS = TASK_RETENTION_DAYS * 24 * 3600


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskInfo:
    """Structured information about a tracked task."""

    status: TaskStatus
    method: str
    ip: str
    started_at: float
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "status": self.status.value,
            "method": self.method,
            "ip": self.ip,
            "started_at": self.started_at,
        }
        if self.completed_at is not None:
            data["completed_at"] = self.completed_at
        if self.result is not None:
            data["result"] = self.result
        if self.error_code is not None:
            data["error_code"] = self.error_code
        if self.error_message is not None:
            data["error_message"] = self.error_message
        if self.details is not None:
            data["details"] = self.details
        return data


tasks: Dict[str, TaskInfo] = {}


def _create_task_info(
    task_id: str,
    status: TaskStatus,
    method: str,
    ip: str,
    started_at: float,
) -> TaskInfo:
    info = TaskInfo(
        status=status,
        method=method,
        ip=ip,
        started_at=started_at,
    )
    tasks[task_id] = info
    # Enforce max_tasks cap: drop oldest by started_at when over limit
    if config.max_tasks > 0 and len(tasks) > config.max_tasks:
        by_started = sorted((tid, tasks[tid].started_at) for tid in tasks)
        for tid, _ in by_started:
            if len(tasks) <= config.max_tasks:
                break
            del tasks[tid]
    return info


def update_task_status(
    task_id: str,
    status: TaskStatus,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[ServiceError] = None,
    generic_error: Optional[Exception] = None,
    method: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """
    Update task status in tracking dictionary.
    Helper for task status updates.
    """
    now = time.time()

    if status == TaskStatus.RUNNING:
        # Initial task creation
        if method is None or ip is None:
            raise ValueError("method and ip are required for RUNNING status")
        _create_task_info(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            method=method,
            ip=ip,
            started_at=now,
        )
        return

    info = tasks.get(task_id)
    if info is None:
        # Fallback: create a minimal record if it does not exist
        if method is None:
            method = "unknown"
        if ip is None:
            ip = "unknown"
        info = _create_task_info(
            task_id=task_id,
            status=status,
            method=method,
            ip=ip,
            started_at=now,
        )

    info.status = status
    info.completed_at = now

    if status == TaskStatus.SUCCESS and result is not None:
        info.result = result
    elif status == TaskStatus.FAILED:
        if error is not None:
            info.error_code = error.err.code
            info.error_message = error.err.message
            info.details = error.details
        elif generic_error is not None:
            info.error_code = ERRORS["EXECUTION_FAILED"].code
            info.error_message = ERRORS["EXECUTION_FAILED"].message
            info.details = str(generic_error)


def get_task_if_valid(
    task_id: str,
) -> Tuple[Optional[TaskInfo], Optional[str]]:
    """
    Return task if it exists and is not older than TASK_RETENTION_DAYS.

    Returns (TaskInfo, None) if valid; (None, reason) if not found or expired.
    reason is "not_found" or "expired". Expired tasks are removed.
    """
    if task_id not in tasks:
        return None, "not_found"
    info = tasks[task_id]
    if time.time() - info.started_at > TASK_RETENTION_SECONDS:
        del tasks[task_id]
        return None, "expired"
    return info, None

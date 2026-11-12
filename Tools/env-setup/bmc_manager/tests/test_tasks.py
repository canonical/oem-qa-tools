"""Unit tests for bmc_manager.utils.tasks."""

import time

import pytest

from bmc_manager.utils.errors import ERRORS, ServiceError
from bmc_manager.utils.tasks import (
    TASK_RETENTION_SECONDS,
    TaskInfo,
    TaskStatus,
    get_task_if_valid,
    tasks,
    update_task_status,
)


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear tasks before each test; restore after to avoid leakage."""
    before = dict(tasks)
    tasks.clear()
    yield
    tasks.clear()
    for k, v in before.items():
        tasks[k] = v


def test_task_info_to_dict():
    """TaskInfo.to_dict: status, method, ip, started_at; optional when set."""
    info = TaskInfo(
        status=TaskStatus.SUCCESS,
        method="validate_connection",
        ip="192.168.1.1",
        started_at=1000.0,
        completed_at=1005.0,
        result={"result": True, "method": "validate_connection"},
    )
    d = info.to_dict()
    assert d["status"] == "success"
    assert d["method"] == "validate_connection"
    assert d["ip"] == "192.168.1.1"
    assert d["started_at"] == 1000.0
    assert d["completed_at"] == 1005.0
    assert "result" in d


def test_update_task_status_running_creates_task():
    """update_task_status RUNNING creates new task with method and ip."""
    update_task_status(
        "task-1", TaskStatus.RUNNING, method="list_users", ip="10.0.0.1"
    )
    assert "task-1" in tasks
    info = tasks["task-1"]
    assert info.status == TaskStatus.RUNNING
    assert info.method == "list_users"
    assert info.ip == "10.0.0.1"


def test_update_task_status_success_sets_result():
    """update_task_status SUCCESS sets completed_at and result."""
    update_task_status(
        "task-2", TaskStatus.RUNNING, method="execute", ip="10.0.0.2"
    )
    update_task_status("task-2", TaskStatus.SUCCESS, result={"result": True})
    info = tasks["task-2"]
    assert info.status == TaskStatus.SUCCESS
    assert info.completed_at is not None
    assert info.result == {"result": True}


def test_update_task_status_failed_sets_error():
    """update_task_status FAILED with ServiceError sets error_code, details."""
    update_task_status(
        "task-3", TaskStatus.RUNNING, method="validate", ip="10.0.0.3"
    )
    err = ServiceError(ERRORS["AUTH_FAILED"], "Bad credentials")
    update_task_status("task-3", TaskStatus.FAILED, error=err)
    info = tasks["task-3"]
    assert info.status == TaskStatus.FAILED
    assert info.error_code == 1001
    assert "credentials" in (info.details or "")


def test_get_task_if_valid_not_found():
    """get_task_if_valid returns (None, 'not_found') for unknown task_id."""
    task_obj, reason = get_task_if_valid("nonexistent-uuid")
    assert task_obj is None
    assert reason == "not_found"


def test_get_task_if_valid_expired_removes_task():
    """get_task_if_valid returns (None, 'expired'), deletes task if too old."""
    update_task_status(
        "old-task", TaskStatus.RUNNING, method="x", ip="1.2.3.4"
    )
    info = tasks["old-task"]
    info.started_at = time.time() - TASK_RETENTION_SECONDS - 1
    task_obj, reason = get_task_if_valid("old-task")
    assert task_obj is None
    assert reason == "expired"
    assert "old-task" not in tasks


def test_get_task_if_valid_returns_task_when_fresh():
    """get_task_if_valid returns (TaskInfo, None) for valid task."""
    update_task_status(
        "fresh-task", TaskStatus.RUNNING, method="health", ip="1.2.3.4"
    )
    task_obj, reason = get_task_if_valid("fresh-task")
    assert task_obj is not None
    assert reason is None
    assert task_obj.method == "health"

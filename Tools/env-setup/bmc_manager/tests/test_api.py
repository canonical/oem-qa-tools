"""Integration/API tests for BMC service endpoints."""

import uuid

from fastapi.testclient import TestClient

from bmc_manager.bmc_service import app

client = TestClient(app)


def test_health_returns_200_and_healthy():
    """GET /health returns 200, data.status healthy, thread_pool, config."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert "data" in data
    health = data["data"]
    assert health.get("status") == "healthy"
    assert "thread_pool" in health
    assert health["thread_pool"].get("max_workers") is not None
    assert "config" in health
    assert "timeout" in health["config"]


def test_validate_invalid_ip_returns_400():
    """POST /validate with invalid IP returns 400 and error code 4xxx."""
    response = client.post(
        "/validate",
        json={
            "ip": "not-an-ip",
            "username": "admin",
            "password": "secret",
            "protocol": "redfish",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("success") is False
    assert data.get("error_code") == 4001
    assert "method" in data


def test_validate_empty_password_returns_400():
    """POST /validate with empty password returns 400 and error code 4xxx."""
    response = client.post(
        "/validate",
        json={
            "ip": "192.168.1.1",
            "username": "admin",
            "password": "",
            "protocol": "redfish",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("success") is False
    assert data.get("error_code") == 4003


def test_execute_invalid_method_returns_error():
    """POST /execute with invalid method returns 400/500 and error shape."""
    response = client.post(
        "/execute",
        json={
            "ip": "192.168.1.1",
            "username": "admin",
            "password": "pwd",
            "protocol": "redfish",
            "method": "nonexistent_method",
            "params": {},
        },
    )
    assert response.status_code in (400, 500)
    data = response.json()
    assert data.get("success") is False
    assert "error_code" in data
    assert "method" in data


def test_tasks_not_found_returns_404():
    """GET /tasks/{task_id} with unknown UUID returns 404, task not found."""
    task_id = str(uuid.uuid4())
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404
    data = response.json()
    assert data.get("success") is False
    assert data.get("error_code") == 3005
    assert "Task not found" in (data.get("details") or "")


def test_list_users_invalid_credentials_returns_error():
    """POST /list-users with invalid payload returns 400 (validation error)."""
    response = client.post(
        "/list-users",
        json={
            "ip": "192.168.1.1",
            "username": "",
            "password": "pwd",
            "protocol": "redfish",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data.get("success") is False
    assert data.get("error_code") in (4002, 4003)

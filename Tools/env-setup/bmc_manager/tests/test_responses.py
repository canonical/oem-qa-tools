"""Unit tests for bmc_manager.utils.responses."""

from bmc_manager.utils.responses import (
    ApiResponse,
    error_response,
    normalize_bmc_result,
    ok_response,
)


class TestNormalizeBmcResult:
    """Tests for normalize_bmc_result."""

    def test_dict_with_success_true(self):
        """Dict with success=True: success, message, data (no success key)."""
        bmc_return = {"success": True, "power_state": "On"}
        success, message, data = normalize_bmc_result(
            bmc_return, "get_power_state"
        )
        assert success is True
        assert message == "Method executed successfully"
        assert data == {"power_state": "On"}

    def test_dict_with_success_false(self):
        """Dict with success=False uses error or message."""
        bmc_return = {"success": False, "error": "Auth failed"}
        success, message, data = normalize_bmc_result(bmc_return, "validate")
        assert success is False
        assert message == "Auth failed"
        assert "success" not in data

    def test_dict_success_false_fallback_message(self):
        """When success=False and no 'error', uses 'message' or default."""
        bmc_return = {"success": False, "message": "Custom fail"}
        success, message, _ = normalize_bmc_result(bmc_return, "x")
        assert success is False
        assert message == "Custom fail"

    def test_true_returns_ok_and_data_ok_true(self):
        """Plain True return yields success=True, data.ok=True."""
        success, message, data = normalize_bmc_result(
            True, "validate_connection"
        )
        assert success is True
        assert message == "Method executed successfully"
        assert data == {"ok": True}

    def test_non_dict_non_bool_puts_in_data_result(self):
        """Non-dict (e.g. string) is wrapped in data.result."""
        success, message, data = normalize_bmc_result(
            "some output", "run_action"
        )
        assert success is True
        assert data == {"result": "some output"}


class TestApiResponse:
    """Tests for ApiResponse.to_dict."""

    def test_to_dict_includes_required_fields(self):
        """to_dict has success, message, method."""
        r = ApiResponse(success=True, message="OK", method="health_check")
        d = r.to_dict()
        assert d["success"] is True
        assert d["message"] == "OK"
        assert d["method"] == "health_check"

    def test_to_dict_optional_fields_excluded_when_none(self):
        """data, error_code, details, task_id omitted when None."""
        r = ApiResponse(success=False, message="Fail", method="x")
        d = r.to_dict()
        assert "data" not in d
        assert "error_code" not in d
        assert "details" not in d
        assert "task_id" not in d

    def test_to_dict_includes_optional_when_set(self):
        """data, error_code, details, task_id included when set."""
        r = ApiResponse(
            success=True,
            message="OK",
            method="run_action",
            data={"power_state": "On"},
            task_id="abc-123",
        )
        d = r.to_dict()
        assert d["data"] == {"power_state": "On"}
        assert d["task_id"] == "abc-123"


class TestErrorResponse:
    """Tests for error_response."""

    def test_error_response_shape_and_status(self):
        """error_response returns JSONResponse with correct status and keys."""
        from bmc_manager.utils.errors import ERRORS

        resp = error_response("validate", ERRORS["INVALID_IP"], "Bad format")
        assert resp.status_code == 400
        body = resp.body.decode()
        assert "success" in body
        assert "error_code" in body
        assert "4001" in body or "Invalid IP" in body


class TestOkResponse:
    """Tests for ok_response."""

    def test_ok_response_default_status_200(self):
        """ok_response defaults to 200."""
        resp = ok_response("health_check", "OK", data={"status": "healthy"})
        assert resp.status_code == 200

    def test_ok_response_custom_status(self):
        """ok_response accepts custom status_code (e.g. 202)."""
        resp = ok_response(
            "execute_async", "Task started", status_code=202, task_id="t1"
        )
        assert resp.status_code == 202
        body = resp.body.decode()
        assert "t1" in body or "task_id" in body

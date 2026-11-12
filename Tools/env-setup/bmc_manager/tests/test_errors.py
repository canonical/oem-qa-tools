"""Unit tests for bmc_manager.utils.errors."""

from bmc_manager.utils.errors import (
    ERRORS,
    ERRORS_BY_CODE,
    ServiceError,
)


def test_error_def_fields():
    """ErrorDef has code, message, http_status, default_details."""
    err = ERRORS["INVALID_IP"]
    assert err.code == 4001
    assert err.message == "Invalid IP"
    assert err.http_status == 400
    assert "IP" in err.default_details


def test_service_error_carries_err_and_details():
    """ServiceError stores ErrorDef and optional details."""
    err_def = ERRORS["AUTH_FAILED"]
    e = ServiceError(err_def, "custom details")
    assert e.err is err_def
    assert e.err.code == 1001
    assert e.details == "custom details"
    assert str(e) == "Authentication failed"


def test_service_error_uses_default_details_when_empty():
    """ServiceError uses err.default_details when details is empty."""
    err_def = ERRORS["INVALID_PASSWORD"]
    e = ServiceError(err_def, "")
    assert e.details == err_def.default_details


def test_errors_by_code_maps_code_to_error_def():
    """ERRORS_BY_CODE allows lookup by integer code."""
    assert ERRORS_BY_CODE[4001].message == "Invalid IP"
    assert ERRORS_BY_CODE[3005].message == "Task not found"

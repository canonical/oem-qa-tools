"""API response utilities for BMC service."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from bmc_manager.utils.errors import ErrorDef


def normalize_bmc_result(
    bmc_return: Any, method: str
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Build a single success flag and data payload from BMC method return.

    Root success reflects BMC operation outcome; data has method-specific
    payload (no nested result.success).
    """
    if isinstance(bmc_return, dict) and "success" in bmc_return:
        success = bool(bmc_return["success"])
        data = {k: v for k, v in bmc_return.items() if k != "success"}
        message = (
            "Method executed successfully"
            if success
            else bmc_return.get(
                "error",
                bmc_return.get("message", "Operation failed"),
            )
        )
        return success, message, data
    success = True
    data = {"ok": True} if bmc_return is True else {"result": bmc_return}
    return success, "Method executed successfully", data


@dataclass(frozen=True)
class ApiResponse:
    """
    Canonical API response envelope.
    All JSON responses follow one shape.
    """

    success: bool
    message: str
    method: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[int] = None
    details: Optional[str] = None
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": self.success,
            "message": self.message,
            "method": self.method,
        }
        if self.data is not None:
            payload["data"] = self.data
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.details is not None:
            payload["details"] = self.details
        if self.task_id is not None:
            payload["task_id"] = self.task_id
        return payload


def json_response(payload: ApiResponse, status_code: int) -> JSONResponse:
    return JSONResponse(
        content=jsonable_encoder(payload.to_dict()),
        status_code=status_code,
    )


def error_response(
    method: str,
    err: ErrorDef,
    details: str = "",
    task_id: Optional[str] = None,
) -> JSONResponse:
    """Create a consistent JSON error response."""
    return json_response(
        ApiResponse(
            success=False,
            message=err.message,
            method=method,
            error_code=err.code,
            details=details or err.default_details,
            task_id=task_id,
        ),
        status_code=err.http_status,
    )


def ok_response(
    method: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    task_id: Optional[str] = None,
    success: bool = True,
) -> JSONResponse:
    """Success or BMC-operation result (success=True/False, always 200)."""
    return json_response(
        ApiResponse(
            success=success,
            message=message,
            method=method,
            data=data,
            task_id=task_id,
        ),
        status_code=status_code,
    )

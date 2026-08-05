"""Error definitions and registry for BMC service."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ErrorDef:
    """
    Error definition for consistent error responses.
    Central registry for code/message/http_status defaults.
    """

    code: int
    message: str
    http_status: int
    default_details: str = ""


# Error registry
ERRORS: Dict[str, ErrorDef] = {
    # Validation errors (1xxx)
    "AUTH_FAILED": ErrorDef(
        code=1001,
        message="Authentication failed",
        http_status=401,
        default_details="Invalid username or password",
    ),
    "CONNECTION_TIMEOUT": ErrorDef(
        code=1002,
        message="Connection timeout",
        http_status=504,
        default_details="BMC unreachable or timeout",
    ),
    "PROTOCOL_ERROR": ErrorDef(
        code=1003,
        message="Protocol error",
        http_status=400,
        default_details="Cipher suite mismatch or protocol error",
    ),
    "HTTP_UNAUTHORIZED": ErrorDef(
        code=1004,
        message="HTTP Unauthorized",
        http_status=401,
        default_details="HTTP 401/403 Unauthorized",
    ),
    "UNEXPECTED_ERROR": ErrorDef(
        code=1005,
        message="Unexpected error",
        http_status=500,
        default_details="Unexpected validation error",
    ),
    # Method errors (2xxx)
    "METHOD_NOT_FOUND": ErrorDef(
        code=2001,
        message="Method not found",
        http_status=400,
        default_details="Method does not exist on BMC_Manager",
    ),
    "INVALID_PARAMETERS": ErrorDef(
        code=2002,
        message="Invalid parameters",
        http_status=400,
        default_details="Parameter mismatch or invalid parameters",
    ),
    "METHOD_NOT_CALLABLE": ErrorDef(
        code=2003,
        message="Method not callable",
        http_status=400,
        default_details="Method exists but is not callable",
    ),
    "PRIVATE_METHOD": ErrorDef(
        code=2004,
        message="Private method not allowed",
        http_status=400,
        default_details="Attempted to call private method",
    ),
    # Execution errors (3xxx)
    "EXECUTION_FAILED": ErrorDef(
        code=3001,
        message="Execution failed",
        http_status=500,
        default_details="Method execution failed",
    ),
    "TIMEOUT": ErrorDef(
        code=3002,
        message="Timeout",
        http_status=408,
        default_details="Method execution timed out",
    ),
    "RETRY_EXHAUSTED": ErrorDef(
        code=3003,
        message="Retry exhausted",
        http_status=500,
        default_details="All retry attempts failed",
    ),
    "SERVICE_SHUTTING_DOWN": ErrorDef(
        code=3004,
        message="Service is shutting down",
        http_status=503,
        default_details=(
            "The service is shutting down and cannot accept new requests."
        ),
    ),
    "TASK_NOT_FOUND": ErrorDef(
        code=3005,
        message="Task not found",
        http_status=404,
        default_details="Unknown task_id",
    ),
    # Input validation errors (4xxx)
    "INVALID_IP": ErrorDef(
        code=4001,
        message="Invalid IP",
        http_status=400,
        default_details="Invalid IP address format",
    ),
    "INVALID_USERNAME": ErrorDef(
        code=4002,
        message="Invalid username",
        http_status=400,
        default_details="Invalid username",
    ),
    "INVALID_PASSWORD": ErrorDef(
        code=4003,
        message="Invalid password",
        http_status=400,
        default_details="Invalid password",
    ),
    "INVALID_PROTOCOL": ErrorDef(
        code=4004,
        message="Invalid protocol",
        http_status=400,
        default_details="Protocol must be 'redfish' or 'ipmitool'",
    ),
    "INVALID_CIPHER_SUITE": ErrorDef(
        code=4005,
        message="Invalid cipher suite",
        http_status=400,
        default_details="Cipher suite must be between 0 and 17",
    ),
}


ERRORS_BY_CODE: Dict[int, ErrorDef] = {e.code: e for e in ERRORS.values()}


class ServiceError(Exception):
    """Internal exception carrying an ErrorDef and optional details."""

    def __init__(self, err: ErrorDef, details: str = "") -> None:
        super().__init__(err.message)
        self.err = err
        self.details = details or err.default_details

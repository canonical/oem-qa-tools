"""Middleware utilities for BMC service."""

import logging
import uuid
from typing import Callable

from fastapi import Request

from bmc_manager.utils.errors import ERRORS
from bmc_manager.utils.responses import error_response
from bmc_manager.utils.shutdown import SHUTTING_DOWN

logger = logging.getLogger(__name__)


async def add_request_id_middleware(request: Request, call_next: Callable):
    """Add request ID to each request and handle shutdown flag."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(
        "Request {}: {} {}".format(request_id, request.method, request.url)
    )

    if SHUTTING_DOWN:
        return error_response(
            method="service_shutdown",
            err=ERRORS["SERVICE_SHUTTING_DOWN"],
        )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

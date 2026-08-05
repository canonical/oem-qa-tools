#!/usr/bin/python3

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Callable, Dict, Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bmc_manager.utils.config import config
from bmc_manager.utils.errors import ERRORS, ServiceError
from bmc_manager.utils.execution import (
    BMCActionRequest,
    BMCExecuteRequest,
    BMCListActionsRequest,
    BMCListUsersRequest,
    BMCPowerStateRequest,
    BMCValidateRequest,
    action_to_execute_request,
    run_action_with_optional_wait,
    run_job_with_retry,
    simple_convenience_endpoint,
)
from bmc_manager.utils.middleware import add_request_id_middleware
from bmc_manager.utils.responses import (
    error_response,
    normalize_bmc_result,
    ok_response,
)
from bmc_manager.utils.shutdown import register_shutdown_handlers
from bmc_manager.utils.tasks import (
    TaskStatus,
    get_task_if_valid,
    tasks,
    update_task_status,
)

# Setup logging
logging.basicConfig(level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="BMC Manager API",
    description=(
        "REST API for managing Baseboard Management Controllers (BMCs) "
        "via Redfish and IPMI. Sync/async execution and task tracking."
    ),
    version="1.0.0",
)

# CORS configuration
if config.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Thread pool executor
executor = ThreadPoolExecutor(max_workers=config.max_workers)

# Register shutdown handlers
register_shutdown_handlers(executor)

# Request ID middleware
app.middleware("http")(add_request_id_middleware)


@app.exception_handler(ServiceError)
def service_error_exception_handler(request, exc: ServiceError):
    """Convert ServiceError (e.g. validation) to JSON error response."""
    method = (
        request.url.path.strip("/").replace("/", "_") or "request_validation"
    )
    return error_response(method, exc.err, exc.details)


def _run_sync_with_task_tracking(
    task_id: str,
    method_name: str,
    ip: str,
    run_fn: Callable[[], Dict[str, Any]],
) -> JSONResponse:
    """
    Run a sync job with task tracking; return ok_response or error_response.

    run_fn() must return {"result": ..., "method": ...}. See USER_GUIDE_SERVICE
    for task retention.
    """
    update_task_status(
        task_id,
        TaskStatus.RUNNING,
        method=method_name,
        ip=ip,
    )
    try:
        raw = run_fn()
        success, message, data = normalize_bmc_result(
            raw["result"], raw["method"]
        )
        update_task_status(task_id, TaskStatus.SUCCESS, result=raw)
        return ok_response(
            method=raw["method"],
            message=message,
            data=data,
            task_id=task_id,
            success=success,
        )
    except ServiceError as e:
        logger.error("ServiceError: {} ({})".format(e.err.code, e.details))
        update_task_status(task_id, TaskStatus.FAILED, error=e)
        return error_response(method_name, e.err, e.details, task_id=task_id)
    except Exception as e:
        logger.exception("Error executing method: {}".format(e))
        update_task_status(
            task_id,
            TaskStatus.FAILED,
            generic_error=e,
        )
        return error_response(
            method_name,
            ERRORS["EXECUTION_FAILED"],
            "Internal error: {}".format(str(e)),
            task_id=task_id,
        )


def run_async_task_with_tracking(
    task_id: str,
    request: BMCExecuteRequest,
    delay: Optional[float],
    retry_times: int,
) -> None:
    """
    Execute BMC method in background thread with retry logic and tracking.

    Args:
        task_id: Unique task identifier
        request: BMC execute request
        delay: Delay before execution
        retry_times: Number of retry attempts
    """
    # Get method and IP from request for initial status
    method = request.method
    ip = request.ip

    # Keep compatibility: async endpoint passes delay/retry_times separately
    request.delay = delay
    request.retry_times = retry_times

    # Initialize task status
    update_task_status(
        task_id=task_id,
        status=TaskStatus.RUNNING,
        method=method,
        ip=ip,
    )

    try:
        result = run_job_with_retry(request, config)
        update_task_status(task_id, TaskStatus.SUCCESS, result=result)
    except ServiceError as e:
        update_task_status(task_id, TaskStatus.FAILED, error=e)
    except Exception as e:
        update_task_status(task_id, TaskStatus.FAILED, generic_error=e)


@app.post("/execute")
async def execute(request: BMCExecuteRequest) -> JSONResponse:
    """
    Generic endpoint: call any BMC_Manager method synchronously.

    Work runs in the thread pool so the event loop stays free and
    multiple requests can run concurrently. See USER_GUIDE_SERVICE.md
    for task_id and task retention.
    """
    task_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        _run_sync_with_task_tracking,
        task_id,
        request.method,
        request.ip,
        lambda: run_job_with_retry(request, config),
    )


@app.post("/execute/async")
async def execute_async(request: BMCExecuteRequest) -> JSONResponse:
    """
    Generic async endpoint: call any BMC_Manager method in background.

    Returns immediately with task acceptance, executes method in
    separate thread.
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Submit task to thread pool
        executor.submit(
            run_async_task_with_tracking,
            task_id,
            request,
            request.delay,
            request.retry_times,
        )

        logger.info(
            "Started async execution of method '{}' for BMC {} "
            "(task_id: {})".format(request.method, request.ip, task_id)
        )
        return ok_response(
            method=request.method,
            message="Task started in background",
            status_code=202,
            task_id=task_id,
        )

    except Exception as e:
        logger.exception("Error starting async task: {}".format(e))
        return error_response(
            request.method,
            ERRORS["EXECUTION_FAILED"],
            "Error starting task: {}".format(str(e)),
        )


def _task_retention_msg(prefix: str) -> str:
    return "{} Tasks are kept for {} days.".format(
        prefix, config.task_retention_days
    )


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> JSONResponse:
    """
    Get status and result of any task (sync or async).

    See USER_GUIDE_SERVICE.md for task retention and re-fetch.
    """
    task_obj, reason = get_task_if_valid(task_id)
    if task_obj is None:
        prefix = "Task expired." if reason == "expired" else "Task not found."
        details = _task_retention_msg(prefix)
        return error_response(
            method="get_task_status",
            err=ERRORS["TASK_NOT_FOUND"],
            details=details,
        )

    task_info = task_obj.to_dict()
    completed = task_obj.completed_at or time.time()
    task_info["duration"] = completed - task_obj.started_at

    raw_result = task_info.get("result")
    if (
        isinstance(raw_result, dict)
        and "result" in raw_result
        and "method" in raw_result
    ):
        success, msg, data = normalize_bmc_result(
            raw_result["result"], raw_result["method"]
        )
        task_info["result"] = {
            "success": success,
            "message": msg,
            "data": data,
        }

    return ok_response(
        method="get_task_status",
        message="Task status retrieved",
        data=task_info,
        status_code=200,
    )


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for service monitoring.

    Returns:
        Service health status
    """
    config_dict = asdict(config)
    health_status = {
        "status": "healthy",
        "service": "bmc_service",
        "version": "1.0.0",
        "thread_pool": {
            "max_workers": config_dict["max_workers"],
            "active_tasks": len(
                [t for t in tasks.values() if t.status == TaskStatus.RUNNING]
            ),
        },
        "config": config_dict,
    }
    return ok_response(
        method="health_check",
        message="Service healthy",
        data=health_status,
        status_code=200,
    )


@app.post("/validate")
async def validate(request: BMCValidateRequest) -> JSONResponse:
    """
    Convenience endpoint: validate BMC connection.

    Internally calls /execute with method="validate_connection".
    """
    return await execute(
        simple_convenience_endpoint(request, "validate_connection")
    )


@app.post("/list-users")
async def list_users(request: BMCListUsersRequest) -> JSONResponse:
    """
    Convenience endpoint: list BMC users.

    Internally calls /execute with method="list_users".
    """
    return await execute(simple_convenience_endpoint(request, "list_users"))


@app.post("/list-actions")
async def list_actions(request: BMCListActionsRequest) -> JSONResponse:
    """
    Convenience endpoint: list available BMC actions.

    Internally calls /execute with method="list_actions".
    """
    return await execute(simple_convenience_endpoint(request, "list_actions"))


@app.post("/power-state")
async def power_state(request: BMCPowerStateRequest) -> JSONResponse:
    """
    Convenience endpoint: get current chassis power state.

    Internally calls /execute with method="get_power_state".
    """
    return await execute(
        simple_convenience_endpoint(request, "get_power_state")
    )


@app.post("/action")
async def action(request: BMCActionRequest) -> JSONResponse:
    """
    Convenience endpoint: execute power action synchronously.

    If wait_for_state_seconds > 0, polls get_power_state until stable or
    timeout and includes power_state (and power_state_stable) in response.
    See USER_GUIDE_SERVICE.md for task_id and task retention.
    """
    wait_sec = getattr(request, "wait_for_state_seconds", None) or 0
    if wait_sec > 0:
        task_id = str(uuid.uuid4())

        def run_action_raw() -> Dict[str, Any]:
            bmc_return = run_action_with_optional_wait(request, config)
            return {"result": bmc_return, "method": "run_action"}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            _run_sync_with_task_tracking,
            task_id,
            "run_action",
            request.ip,
            run_action_raw,
        )
    return await execute(action_to_execute_request(request))


@app.post("/action/async")
async def action_async(request: BMCActionRequest) -> JSONResponse:
    """
    Convenience endpoint: execute power action asynchronously.

    Internally calls /execute/async with method="run_action".
    """
    return await execute_async(action_to_execute_request(request))

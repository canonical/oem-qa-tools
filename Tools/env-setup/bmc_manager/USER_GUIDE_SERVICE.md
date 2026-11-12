# BMC Manager Webservice User Guide

## Overview

BMC Manager Webservice is a FastAPI-based REST API that provides a unified
interface for managing Baseboard Management Controllers (BMC) using two protocols:

- **IPMI** (via ipmitool)
- **Redfish** (via REST API)

This webservice allows you to programmatically manage BMCs through HTTP requests,
supporting both synchronous and asynchronous operations. The service automatically
validates connections before executing actions and returns specific error codes
for easy error handling.

**Key Features**:

- REST API interface for BMC management
- Automatic connection validation before actions
- Specific error codes for different failure types
- Support for both synchronous and asynchronous operations
- Task tracking for async operations
- Health check endpoint for monitoring
- Thread pool management for resource control
- Request timeouts to prevent hanging operations
- Input validation for all request fields
- Extensible design: automatically supports new BMC_Manager methods
- Multi-threaded execution for concurrent requests
- Configurable via environment variables

## Requirements

### System Requirements

- Python 3.10 or higher
- Linux/Unix system (for IPMI support)
- `uv` package manager (recommended) or `pip`

### Dependencies

Python Packages:

Install required Python packages using `uv`:

```bash
cd bmc_manager
uv sync
```

Or using `pip`:

```bash
pip install fastapi uvicorn requests urllib3
```

External Tools (for IPMI):

For IPMI protocol support, you need `ipmitool` installed:

```bash
# Ubuntu/Debian
sudo apt-get install ipmitool

# RHEL/CentOS
sudo yum install ipmitool

# macOS
brew install ipmitool
```

## Installation

1. Ensure Python 3.10+ is installed:

   ```bash
   python3 --version
   ```

2. Install Python dependencies using `uv`:

   ```bash
   cd bmc_manager
   uv sync
   ```

   Or using `pip`:

   ```bash
   pip install fastapi uvicorn requests urllib3
   ```

3. Install ipmitool (if using IPMI protocol):

   ```bash
   # See dependencies section above for your OS
   ```

4. Start the webservice:

   ```bash
   cd bmc_manager
   uv run uvicorn bmc_manager.bmc_service:app --host 0.0.0.0 --port 8000
   ```

   Or with reload for development:

   ```bash
   cd bmc_manager
   uv run uvicorn bmc_manager.bmc_service:app --host 0.0.0.0 --port 8000 --reload
   ```

### Configuration

The service can be configured using environment variables:

- `BMC_MAX_WORKERS` (default: 10): Maximum number of concurrent threads used
  for sync endpoints (POST /execute, POST /action with wait). Blocking BMC work
  runs in this pool so multiple requests can be handled in parallel.
- `BMC_TIMEOUT` (default: 30): Timeout in seconds for BMC operations
- `BMC_LOG_LEVEL` (default: INFO): Logging level (DEBUG, INFO, WARNING, ERROR)
- `BMC_ENABLE_CORS` (default: false): Enable CORS middleware for browser-based
  clients. If you run a frontend on a different origin (different host/port)
  than this API, the browser may block requests unless CORS is enabled. When
  enabled, the service adds FastAPI's `CORSMiddleware` (currently configured to
  allow all origins/headers/methods); for production, restrict origins to the
  specific domains you trust.
- `BMC_MIN_RETRY_DELAY_SECONDS` (default: 0.2): Minimum delay (in seconds)
  between retry attempts when you set `delay` in requests. This prevents tight
  retry loops when a very small (or zero) delay is provided.
- `BMC_MAX_TASKS` (default: 0): Maximum number of tasks to retain in memory.
  When exceeded, oldest tasks (by `started_at`) are removed. Use 0 for no cap
  (only time-based retention applies; see `BMC_TASK_RETENTION_DAYS`). Tuning
  under load: increase `BMC_MAX_WORKERS` for more concurrent BMC operations
  and `BMC_TIMEOUT` for longer-running BMC calls.
- `BMC_TASK_RETENTION_DAYS` (default: 7): Tasks older than this many days are
  removed; GET /tasks/{task_id} returns "Task expired" for such task IDs.
- `BMC_REDFISH_REQUEST_TIMEOUT` (default: 5): Timeout in seconds for Redfish
  HTTP GET/POST requests to the BMC.
- `BMC_POWER_STATE_POLL_INTERVAL` (default: 1.5): Interval in seconds between
  polls when waiting for power state to become stable (action with
  wait_for_state_seconds).
- `BMC_MAX_WAIT_FOR_STATE_SECONDS` (default: 300): Maximum allowed value for
  `wait_for_state_seconds` in action requests (validation cap).

Reference: [FastAPI - CORS (Cross-Origin Resource Sharing)](https://fastapi.tiangolo.com/tutorial/cors/)

Example:

```bash
export BMC_MAX_WORKERS=20
export BMC_TIMEOUT=60
export BMC_LOG_LEVEL=DEBUG
export BMC_ENABLE_CORS=true
cd bmc_manager
uv run uvicorn bmc_manager.bmc_service:app --host 0.0.0.0 --port 8000
```

## Usage

### Base URL

By default, the service runs on:

```text
http://localhost:8000
```

### Interactive API docs

Swagger UI and ReDoc provide interactive request/response schemas:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

Request and response shapes in the OpenAPI schema match the examples in this
guide.

### API Endpoints

The service provides the following endpoints:

- `POST /execute` - Execute any BMC_Manager method synchronously
- `POST /execute/async` - Execute any BMC_Manager method asynchronously
- `GET /tasks/{task_id}` - Get status of an async task
- `GET /health` - Health check endpoint for monitoring
- `POST /validate` - Validate BMC connection (convenience endpoint)
- `POST /list-users` - List BMC users (convenience endpoint)
- `POST /list-actions` - List available actions (convenience endpoint)
- `POST /power-state` - Get current chassis power state (convenience endpoint)
- `POST /action` - Execute power action synchronously (convenience endpoint)
- `POST /action/async` - Execute power action asynchronously (convenience endpoint)

### Request Format

All endpoints accept JSON requests with the following base fields:

```json
{
  "ip": "192.168.1.100",
  "username": "admin",
  "password": "password",
  "protocol": "redfish",
  "cipher_suite": 17
}
```

**Fields**:

- `ip` (required): BMC IP address
- `username` (required): BMC username
- `password` (required): BMC password
- `protocol` (required): Either `"redfish"` or `"ipmitool"`
- `cipher_suite` (optional): Cipher suite for IPMI (default: 17)

### Response Format

All endpoints return JSON with a single root `success` that reflects the BMC
operation outcome (or service-level failure). There is no nested `data.result`
with a second `success`; method-specific payload is in `data` directly.

**Success (BMC operation succeeded)**:

- `success`: `true`
- `message`: e.g. "Method executed successfully"
- `method`: method name
- `data`: method-specific payload (e.g. `data.users`, `data.actions`,
  `data.power_state`, `data.message`, `data.ok`)

**BMC operation failed** (e.g. invalid action, wrong credentials on BMC):

- `success`: `false`
- `message`: error message from BMC (e.g. "Action 'X' is not supported")
- `method`: method name
- `data`: may include `error`, `actions` (supported list), etc.

**Service-level error** (validation, timeout, method not found):

- `success`: `false`
- `error_code`: 1xxx–4xxx
- `message`, `details`, `method`
- `task_id`: present when the request had created a task before failing

### Task retention and re-fetch

All sync and async operations return a `task_id` in the response. Clients can
re-fetch the result at any time with `GET /tasks/{task_id}`. Tasks are
retained for 7 days and then removed; after that, `GET /tasks/{task_id}`
returns either "Task not found" or "Task expired" (see GET /tasks in API
Reference).

### Automatic Validation

**Important**: The service automatically validates the BMC connection before
executing any action (except when calling `validate_connection` itself). If
validation fails, the request returns immediately with a specific error code
without attempting to execute the action.

**Input Validation**: All request fields are automatically validated:

- IP address format
- Username (non-empty, max 64 characters)
- Password (non-empty)
- Protocol (must be "redfish" or "ipmitool")
- Cipher suite (must be between 0 and 17)

Invalid input returns error code 4xxx with appropriate message.

## Examples

### Validate Connection

Using curl:

```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish"
  }'
```

Using Python:

```python
import requests

url = "http://localhost:8000/validate"
payload = {
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish"
}

response = requests.post(url, json=payload)
print(response.json())
```

**Success Response** (includes `task_id` for re-fetch; see Task retention):

```json
{
  "success": true,
  "message": "Method executed successfully",
  "data": { "ok": true },
  "method": "validate_connection",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### List Users

Using curl:

```bash
curl -X POST "http://localhost:8000/list-users" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish"
  }'
```

Using Python:

```python
import requests

url = "http://localhost:8000/list-users"
payload = {
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish"
}

response = requests.post(url, json=payload)
print(response.json())
```

### List Available Actions

Using curl:

```bash
curl -X POST "http://localhost:8000/list-actions" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish"
  }'
```

### Get Power State

Get the current chassis power state. Redfish returns values such as `On`,
`Off`, `PoweringOn`, `PoweringOff`, or `Paused`. IPMI returns `on` or `off`.

Using curl:

```bash
curl -X POST "http://localhost:8000/power-state" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish"
  }'
```

Using Python:

```python
import requests

url = "http://localhost:8000/power-state"
payload = {
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
}
response = requests.post(url, json=payload)
print(response.json())
```

Example success response (Redfish):

```json
{
  "success": true,
  "message": "Method executed successfully",
  "data": { "power_state": "On" },
  "method": "get_power_state"
}
```

Example success response (IPMI):

```json
{
  "success": true,
  "message": "Method executed successfully",
  "data": { "power_state": "on" },
  "method": "get_power_state"
}
```

### Execute Power Action (Synchronous)

Power On:

```bash
curl -X POST "http://localhost:8000/action" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "action": "on",
    "delay": 5.0,
    "retry_times": 3
  }'
```

Power Off:

```bash
curl -X POST "http://localhost:8000/action" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "action": "off"
  }'
```

Power Cycle:

```bash
curl -X POST "http://localhost:8000/action" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "action": "cycle"
  }'
```

Power On and wait for stable power state (up to 10 seconds):

```bash
curl -X POST "http://localhost:8000/action" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "action": "on",
    "wait_for_state_seconds": 10
  }'
```

Response includes `data.power_state` and `data.power_state_stable` (true if
On/Off was reached before timeout).

### Execute Power Action (Asynchronous)

Power On with Retry:

```bash
curl -X POST "http://localhost:8000/action/async" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "action": "on",
    "delay": 5.0,
    "retry_times": 3
  }'
```

**Response** (returns immediately):

```json
{
  "success": true,
  "message": "Task started in background",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "run_action"
}
```

### Check Task Status

After starting an async task, you can check its status using the task_id:

Using curl:

```bash
curl -X GET "http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000"
```

Using Python:

```python
import requests

task_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.get(f"http://localhost:8000/tasks/{task_id}")
print(response.json())
```

**Response Examples**:

Running task:

```json
{
  "status": "running",
  "method": "run_action",
  "ip": "192.168.1.100",
  "started_at": 1234567890.123
}
```

Completed task (result is normalized: success, message, data):

```json
{
  "status": "success",
  "result": {
    "success": true,
    "message": "Method executed successfully",
    "data": { "message": "Command Accepted (200)" }
  },
  "started_at": 1234567890.123,
  "completed_at": 1234567895.456,
  "duration": 5.333
}
```

Failed task:

```json
{
  "status": "failed",
  "error_code": 1001,
  "error_message": "Authentication failed",
  "details": "Invalid username or password",
  "started_at": 1234567890.123,
  "completed_at": 1234567891.456,
  "duration": 1.333
}
```

### Health Check

Check service health and status:

Using curl:

```bash
curl -X GET "http://localhost:8000/health"
```

Using Python:

```python
import requests

response = requests.get("http://localhost:8000/health")
print(response.json())
```

**Response**:

```json
{
  "status": "healthy",
  "service": "bmc_service",
  "version": "1.0.0",
  "thread_pool": {
    "max_workers": 10,
    "active_tasks": 2
  },
  "config": {
    "max_workers": 10,
    "timeout": 30,
    "log_level": "INFO",
    "enable_cors": false,
    "min_retry_delay_seconds": 0.2,
    "max_tasks": 0,
    "task_retention_days": 7,
    "redfish_request_timeout": 5,
    "power_state_poll_interval_seconds": 1.5,
    "max_wait_for_state_seconds": 300
  }
}
```

### Generic Method Execution

The `/execute` endpoint allows you to call any method on BMC_Manager dynamically.
This makes the service automatically extensible when new methods are added to
bmc_manager.py.

Example: Call validate_connection

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "method": "validate_connection",
    "params": {}
  }'
```

Example: Call run_action

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "protocol": "redfish",
    "method": "run_action",
    "params": {
      "action_name": "on"
    }
  }'
```

**Note**: When new methods are added to bmc_manager.py (e.g., `get_power_state()`,
`get_fw_version()`), they are automatically available via the `/execute`
endpoint without any changes to the webservice code.

## API Reference

### POST /execute

Generic endpoint to execute any BMC_Manager method synchronously.

**Request Body**:

```json
{
  "ip": "string (required)",
  "username": "string (required)",
  "password": "string (required)",
  "protocol": "redfish|ipmitool (required)",
  "cipher_suite": "integer (optional, default: 17)",
  "method": "string (required)",
  "params": "object (optional, default: {})"
}
```

**Response**: 200 OK (success) or 400/500 (error)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "validate_connection",
  "data": { "ok": true },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /execute/async

Generic endpoint to execute any BMC_Manager method asynchronously.

**Request Body**:

```json
{
  "ip": "string (required)",
  "username": "string (required)",
  "password": "string (required)",
  "protocol": "redfish|ipmitool (required)",
  "cipher_suite": "integer (optional, default: 17)",
  "method": "string (required)",
  "params": "object (optional, default: {})",
  "delay": "float (optional)",
  "retry_times": "integer (optional, default: 1)"
}
```

**Response**: 202 Accepted (task started) or 500 (error)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Task started in background",
  "method": "run_action",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /validate

Convenience endpoint to validate BMC connection.

**Request Body**:

```json
{
  "ip": "string (required)",
  "username": "string (required)",
  "password": "string (required)",
  "protocol": "redfish|ipmitool (required)",
  "cipher_suite": "integer (optional, default: 17)"
}
```

**Response**: 200 OK (success) or 400/401/500 (error)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "validate_connection",
  "data": { "ok": true },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /list-users

Convenience endpoint to list BMC users.

**Request Body**: Same as `/validate`

**Response**: 200 OK (success) or 400/401/500 (error)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "list_users",
  "data": { "users": [] },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /list-actions

Convenience endpoint to list available BMC actions.

**Request Body**: Same as `/validate`

**Response**: 200 OK (success) or 400/401/500 (error)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "list_actions",
  "data": { "actions": ["on", "off", "cycle"] },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /power-state

Convenience endpoint to get the current chassis power state.

**Request Body**: Same as `/validate`

**Response**: 200 OK with `data.power_state` (e.g. `On`, `Off`,
`PoweringOn`, `PoweringOff`, `Paused` for Redfish; `on` or `off` for IPMI).

**Success response (example)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "get_power_state",
  "data": { "power_state": "On" },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

When Redfish returns 401/403 (e.g. wrong username), the service returns
`success: false` with message "Authentication failed" instead of
"No Systems found".

### POST /action

Convenience endpoint to execute a power action synchronously.

**Request Body**:

```json
{
  "ip": "string (required)",
  "username": "string (required)",
  "password": "string (required)",
  "protocol": "redfish|ipmitool (required)",
  "cipher_suite": "integer (optional, default: 17)",
  "action": "string (required)",
  "delay": "float (optional)",
  "retry_times": "integer (optional, default: 1)",
  "wait_for_state_seconds": "float (optional, 0–300)"
}
```

- **wait_for_state_seconds**: If &gt; 0, after the action the service polls
  `get_power_state` until the state is stable (On/Off or on/off) or the
  timeout. Response then includes:
  - **data.power_state**: The last power state seen (e.g. `On`, `Off`,
    `PoweringOn`, `PoweringOff`, `on`, `off`). Redfish uses `On`/`Off`;
    IPMI uses `on`/`off`.
  - **data.power_state_stable**: Boolean. `true` if the chassis reached a
    final state (`On`, `Off`, `on`, or `off`) before the wait timeout;
    `false` if the timeout was reached while still transitioning (e.g.
    `PoweringOn`) or if a poll failed. Use this to know whether the
    action can be treated as “done” or if you should poll `/power-state`
    yourself or retry later.

**Response**: 200 OK (success) or 400/401/500 (error)

**Success (no wait)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "run_action",
  "data": {
    "message": "Command Accepted (200)"
  },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Success (with `wait_for_state_seconds` &gt; 0)**:

```json
{
  "success": true,
  "message": "Method executed successfully",
  "method": "run_action",
  "data": {
    "message": "Command Accepted (200)",
    "power_state": "On",
    "power_state_stable": true
  },
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /action/async

Convenience endpoint to execute a power action asynchronously.

**Request Body**:

```json
{
  "ip": "string (required)",
  "username": "string (required)",
  "password": "string (required)",
  "protocol": "redfish|ipmitool (required)",
  "cipher_suite": "integer (optional, default: 17)",
  "action": "string (required)",
  "delay": "float (optional)",
  "retry_times": "integer (optional, default: 1)"
}
```

**Response**: 202 Accepted (task started) or 500 (error)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Task started in background",
  "method": "run_action",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /tasks/{task_id}

Get the status of an async task.

**Path Parameters**:

- `task_id` (required): Task identifier returned from async endpoints

**Response**: 200 OK (task found) or 404 (task not found)

**Success response (example)**:

```json
{
  "success": true,
  "message": "Task status retrieved",
  "method": "get_task_status",
  "data": {
    "status": "success",
    "method": "run_action",
    "ip": "192.168.1.100",
    "started_at": 1234567890.123,
    "completed_at": 1234567895.456,
    "duration": 5.333,
    "result": {
      "success": true,
      "message": "Method executed successfully",
      "data": { "message": "Command Accepted (200)" }
    }
  }
}
```

**404 (task not found or expired)**:

```json
{
  "success": false,
  "message": "Task not found",
  "method": "get_task_status",
  "error_code": 3005,
  "details": "Task not found. Tasks are kept for 7 days."
}
```

### GET /health

Health check endpoint for service monitoring. Response includes full
service configuration so users can see current values (from environment).

**Response**: 200 OK

**Success response (example)**:

```json
{
  "success": true,
  "message": "Service healthy",
  "method": "health_check",
  "data": {
    "status": "healthy",
    "service": "bmc_service",
    "version": "1.0.0",
    "thread_pool": {
      "max_workers": 10,
      "active_tasks": 2
    },
    "config": {
      "max_workers": 10,
      "timeout": 30,
      "log_level": "INFO",
      "enable_cors": false,
      "min_retry_delay_seconds": 0.2,
      "max_tasks": 0,
      "task_retention_days": 7,
      "redfish_request_timeout": 5,
      "power_state_poll_interval_seconds": 1.5,
      "max_wait_for_state_seconds": 300
    }
  }
}
```

**config** (all from environment; keys match Config): `max_workers`, `timeout`,
`log_level`, `enable_cors`, `min_retry_delay_seconds`, `max_tasks`,
`task_retention_days`,
`redfish_request_timeout`, `power_state_poll_interval_seconds`,
`max_wait_for_state_seconds`. See Configuration for env var names.

## Error Codes

The service returns specific error codes for different failure types:

### Validation Errors (1xxx)

- **1001 - AUTH_FAILED**: Invalid username or password
- **1002 - CONNECTION_TIMEOUT**: BMC unreachable or connection timeout
- **1003 - PROTOCOL_ERROR**: Cipher suite mismatch (IPMI) or protocol error
- **1004 - HTTP_UNAUTHORIZED**: HTTP 401/403 Unauthorized (Redfish)
- **1005 - UNEXPECTED_ERROR**: Other connection/validation errors

### Method Errors (2xxx)

- **2001 - METHOD_NOT_FOUND**: Method doesn't exist on BMC_Manager
- **2002 - INVALID_PARAMETERS**: Parameter mismatch or invalid parameters
- **2003 - METHOD_NOT_CALLABLE**: Method exists but is not callable
- **2004 - PRIVATE_METHOD**: Attempted to call private method

### Execution Errors (3xxx)

- **3001 - EXECUTION_FAILED**: Method execution failed
- **3002 - TIMEOUT**: Method execution timed out
- **3003 - RETRY_EXHAUSTED**: All retry attempts failed

### Input Validation Errors (4xxx)

- **4001 - INVALID_IP**: Invalid IP address format
- **4002 - INVALID_USERNAME**: Invalid username format
- **4003 - INVALID_PASSWORD**: Invalid password format
- **4004 - INVALID_PROTOCOL**: Invalid protocol value
- **4005 - INVALID_CIPHER_SUITE**: Invalid cipher suite value

## Protocol Differences

### IPMI (ipmitool)

**Advantages**:

- Standardized commands across all BMCs
- Works on older hardware
- Lightweight protocol (UDP)

**Limitations**:

- Requires ipmitool to be installed
- Limited to standard IPMI commands
- Uses UDP port 623

**Supported Actions**:

- `status`: Check power status
- `on`: Power on
- `off`: Power off (hard)
- `cycle`: Power cycle
- `reset`: Reset
- `soft`: Graceful shutdown

### Redfish

**Advantages**:

- Modern REST API
- More detailed information
- Vendor-specific actions supported
- Uses HTTPS (port 443)

**Limitations**:

- Requires HTTPS support
- May have vendor-specific implementations
- Some older BMCs may not support it

**Supported Actions**:

- Actions are discovered dynamically from the BMC
- Common actions include: `On`, `ForceOff`, `GracefulShutdown`,
  `GracefulRestart`, `PowerCycle`, etc.
- The service maps generic aliases (`on`, `off`, `reset`, `soft`, `cycle`)
  to vendor-specific commands automatically

## Troubleshooting

### Connection Issues

Error Code 1002: "Connection Timeout" (IPMI)

- Verify the BMC IP address is correct
- Check if UDP port 623 is accessible:

  ```bash
  nc -u -v <BMC_IP> 623
  ```

- Ensure firewall allows UDP port 623
- Try changing the cipher suite (set `cipher_suite` in request)

Error Code 1002: "Connection Timeout" (Redfish)

- Verify the BMC IP address is correct
- Check if HTTPS port 443 is accessible:

  ```bash
  curl -k https://<BMC_IP>/redfish/v1
  ```

- Ensure firewall allows TCP port 443

Error Code 1005: "Connection Error"

- Verify network connectivity to BMC
- Check if BMC is powered on and accessible
- Verify IP address is correct

### Authentication Issues

Error Code 1001: "Authentication Failed"

- Double-check username and password in request
- Ensure credentials are correct for the BMC
- Some BMCs are case-sensitive
- Verify user account is enabled on the BMC

Error Code 1004: "HTTP Unauthorized" (Redfish)

- Verify credentials are correct
- Check if user account is enabled
- Ensure user has appropriate permissions
- Verify the user has not been locked out

### Protocol-Specific Issues

Error Code 1003: "Protocol Error: Cipher Suite mismatch" (IPMI)

- The default cipher suite is 17
- Some older BMCs may require a different cipher suite
- Try setting `cipher_suite` to a different value (0-17) in the request

IPMI: "ipmitool is not installed"

- Install ipmitool (see Requirements section)
- Ensure ipmitool is in your PATH
- Restart the webservice after installation

Redfish: "No Systems found in Redfish collection"

- The BMC may not expose systems via Redfish
- Try using IPMI protocol instead
- Verify Redfish service is enabled on the BMC

Redfish: "No power actions discovered"

- The BMC may not support power actions via Redfish
- Try using IPMI protocol instead
- Check BMC firmware version (may need update)

### Action Execution Issues

Error Code 2001: "Method not found"

- Verify the method name is correct
- Check available methods using `/list-actions`
- Ensure you're using the correct method name (case-sensitive)

Error Code 2002: "Invalid Parameters"

- Verify parameter names match method signature
- Check required parameters are provided
- Ensure parameter types are correct

"Action not supported by this system"

- Use `/list-actions` to see available actions
- Try using the exact action name from the list
- Some actions may require specific permissions

"Command Accepted" but nothing happens

- Some actions take time to execute
- Check BMC logs for errors
- Verify user has sufficient permissions
- For async operations, check service logs

### Service Issues

"Connection refused" when calling API

- Verify the webservice is running:

  ```bash
  ps aux | grep uvicorn
  ```

- Check if the service is listening on the correct port
- Verify firewall allows connections to the service port
- Check service health:

  ```bash
  curl http://localhost:8000/health
  ```

"Task not found" (404) when checking task status

- Verify the task_id is correct
- Tasks are stored in memory and may be lost on service restart
- Check if the task completed and was cleaned up
- Verify the service hasn't been restarted since task creation

Response example (404):

```json
{
  "success": false,
  "message": "Task not found",
  "method": "get_task_status",
  "details": "Unknown task_id"
}
```

"Internal Server Error" (500)

- Check service logs for detailed error messages
- Verify all dependencies are installed
- Ensure bmc_manager.py is accessible
- Check system resources (memory, file descriptors)

## Service Configuration

### Environment Variables

The service supports configuration via environment variables:

```bash
# Thread pool configuration
export BMC_MAX_WORKERS=20  # Max concurrent threads (default: 10)

# Timeout configuration
export BMC_TIMEOUT=60  # BMC operation timeout in seconds (default: 30)

# Logging configuration
export BMC_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR (default: INFO)

# CORS configuration
export BMC_ENABLE_CORS=true  # Enable CORS middleware (default: false)
```

### Request Headers

The service adds a `X-Request-ID` header to all responses for request
tracking and debugging.

## Advanced Usage

### Using with Python Scripts

You can integrate the webservice into Python applications:

```python
import requests
import time

BMC_SERVICE_URL = "http://localhost:8000"
BMC_IP = "192.168.1.100"
BMC_USER = "admin"
BMC_PASS = "password"

def validate_bmc():
    """Validate BMC connection."""
    response = requests.post(
        f"{BMC_SERVICE_URL}/validate",
        json={
            "ip": BMC_IP,
            "username": BMC_USER,
            "password": BMC_PASS,
            "protocol": "redfish"
        }
    )
    return response.json()

def power_on_bmc():
    """Power on the server via BMC."""
    response = requests.post(
        f"{BMC_SERVICE_URL}/action",
        json={
            "ip": BMC_IP,
            "username": BMC_USER,
            "password": BMC_PASS,
            "protocol": "redfish",
            "action": "on"
        }
    )
    return response.json()

# Check connection
result = validate_bmc()
if result.get("success"):
    print("BMC connection validated")
    # Power on
    result = power_on_bmc()
    if result.get("success"):
        print("Power on command sent")
    else:
        print(f"Error: {result.get('message')}")
else:
    print(f"Validation failed: {result.get('message')}")
```

### Using with Shell Scripts

You can call the webservice from shell scripts:

```bash
#!/bin/bash

BMC_SERVICE="http://localhost:8000"
BMC_IP="192.168.1.100"
BMC_USER="admin"
BMC_PASS="password"

# Validate connection
RESPONSE=$(curl -s -X POST "${BMC_SERVICE}/validate" \
  -H "Content-Type: application/json" \
  -d "{
    \"ip\": \"${BMC_IP}\",
    \"username\": \"${BMC_USER}\",
    \"password\": \"${BMC_PASS}\",
    \"protocol\": \"redfish\"
  }")

SUCCESS=$(echo $RESPONSE | jq -r '.success')

if [ "$SUCCESS" = "true" ]; then
  echo "BMC connection validated"
  
  # Power on
  curl -X POST "${BMC_SERVICE}/action" \
    -H "Content-Type: application/json" \
    -d "{
      \"ip\": \"${BMC_IP}\",
      \"username\": \"${BMC_USER}\",
      \"password\": \"${BMC_PASS}\",
      \"protocol\": \"redfish\",
      \"action\": \"on\"
    }"
else
  echo "Validation failed"
  echo $RESPONSE | jq -r '.message'
fi
```

### Task Status Monitoring

Monitor async task status:

```python
import requests
import time

def wait_for_task_completion(task_id, timeout=300):
    """Wait for async task to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(
            f"http://localhost:8000/tasks/{task_id}"
        )
        task = response.json()
        
        if task.get("status") == "success":
            return True, task.get("result")
        elif task.get("status") == "failed":
            return False, task.get("error_message")
        
        time.sleep(1)  # Poll every second
    
    return False, "Task timeout"

# Start async task
response = requests.post(
    "http://localhost:8000/action/async",
    json={
        "ip": "192.168.1.100",
        "username": "admin",
        "password": "password",
        "protocol": "redfish",
        "action": "on"
    }
)

task_id = response.json().get("task_id")
success, result = wait_for_task_completion(task_id)
if success:
    print("Task completed successfully")
else:
    print(f"Task failed: {result}")
```

### Error Handling

Handle errors programmatically using error codes:

```python
import requests

def execute_action_with_error_handling(ip, username, password, action):
    """Execute action with proper error handling."""
    response = requests.post(
        "http://localhost:8000/action",
        json={
            "ip": ip,
            "username": username,
            "password": password,
            "protocol": "redfish",
            "action": action
        }
    )
    
    result = response.json()
    
    if result.get("success"):
        return True, result.get("message")
    
    error_code = result.get("error_code")
    error_message = result.get("message")
    
    # Handle specific error codes
    if error_code == 1001:
        return False, "Authentication failed - check credentials"
    elif error_code == 1002:
        return False, "Connection timeout - check network"
    elif error_code == 1003:
        return False, "Protocol error - try different cipher suite"
    else:
        return False, f"Error {error_code}: {error_message}"

success, message = execute_action_with_error_handling(
    "192.168.1.100", "admin", "password", "on"
)
print(f"Result: {message}")
```

### Using Environment Variables

For better security, use environment variables:

```python
import os
import requests

BMC_IP = os.getenv("BMC_IP")
BMC_USER = os.getenv("BMC_USER")
BMC_PASS = os.getenv("BMC_PASS")

response = requests.post(
    "http://localhost:8000/validate",
    json={
        "ip": BMC_IP,
        "username": BMC_USER,
        "password": BMC_PASS,
        "protocol": "redfish"
    }
)
```

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review error codes and messages in responses
3. Check service logs for detailed error information
4. Verify your BMC firmware version supports the protocol
5. Test with both IPMI and Redfish to isolate protocol-specific issues
6. Review service logs for detailed error information

## Code Formatting

This project uses Black formatting with a line length of 79 characters:

```bash
cd bmc_manager
uv run black --line-length 79 bmc_service.py
```

## Version Compatibility

- **Python**: 3.10+
- **FastAPI**: 0.104.0+
- **Uvicorn**: Latest stable version
- **IPMI**: IPMI 2.0 compatible BMCs
- **Redfish**: Redfish 1.0+ compatible BMCs

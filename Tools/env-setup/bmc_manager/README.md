# BMC Manager

BMC Manager provides tools for managing Baseboard Management Controllers
(BMCs) using IPMI and Redfish protocols.

## Package Structure

```text
bmc_manager/
├── README.md              # This file
├── bmc_service.py         # FastAPI webservice
├── USER_GUIDE_SERVICE.md  # Service usage guide
├── pyproject.toml         # Service dependencies
├── scripts/
│   ├── bmc_manager.py     # Standalone BMC management script
│   ├── USER_GUIDE.md      # Script usage guide
│   └── pyproject.toml     # Script dependencies
└── utils/                 # Shared utilities
    ├── config.py          # Configuration management
    ├── errors.py          # Error definitions
    ├── execution.py       # Execution logic and request models
    ├── middleware.py      # Request middleware
    ├── responses.py       # API response utilities
    ├── shutdown.py        # Graceful shutdown handlers
    └── tasks.py           # Task tracking
```

## Quick Start

### Running the FastAPI Service

**Install dependencies:**

```bash
cd bmc_manager
uv sync
```

**Run the service:**

```bash
uv run uvicorn bmc_manager.bmc_service:app --host 0.0.0.0 --port 8000
```

**Access the API documentation:**

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

The service reuses HTTP connections per BMC (Redfish) for better performance
when multiple operations hit the same host.

### Running the Standalone Script

**Install dependencies:**

```bash
cd bmc_manager/scripts
uv sync
```

**Run the script:**

```bash
uv run python bmc_manager.py --help
```

## Detailed Documentation

- **Service Guide**: See [`USER_GUIDE_SERVICE.md`](USER_GUIDE_SERVICE.md) for
  detailed information about the FastAPI webservice, including API endpoints,
  request/response formats, task_id and 7-day task retention, error codes,
  and configuration options.

- **Script Guide**: See [`scripts/USER_GUIDE.md`](scripts/USER_GUIDE.md) for
  detailed information about the standalone `bmc_manager.py` script, including
  command-line usage, list users/actions, check power state, execute actions,
  and protocol differences.

## Testing

Run the test suite (unit and API tests) from the `bmc_manager` directory:

```bash
cd bmc_manager
uv sync --extra dev
uv run pytest tests/ -v
```

With coverage:

```bash
uv run pytest tests/ -v --cov=bmc_manager --cov-report=term-missing
```

## Environment Variables

The service supports the following environment variables (see
`USER_GUIDE_SERVICE.md` for details):

- `BMC_MAX_WORKERS`: Thread pool size (default: 10)
- `BMC_TIMEOUT`: Operation timeout in seconds (default: 30)
- `BMC_LOG_LEVEL`: Logging level (default: INFO)
- `BMC_ENABLE_CORS`: Enable CORS (default: false)
- `BMC_MIN_RETRY_DELAY_SECONDS`: Minimum retry delay in seconds (default: 0.2)
- `BMC_MAX_TASKS`: Max tasks to retain (0 = no cap; default: 0)
- `BMC_TASK_RETENTION_DAYS`: Task retention in days (default: 7)
- `BMC_REDFISH_REQUEST_TIMEOUT`: Redfish HTTP timeout in seconds (default: 5)
- `BMC_POWER_STATE_POLL_INTERVAL`: Power-state poll interval in seconds (default: 1.5)
- `BMC_MAX_WAIT_FOR_STATE_SECONDS`: Max wait_for_state_seconds (default: 300)

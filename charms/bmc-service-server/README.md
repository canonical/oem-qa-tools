# BMC Service Server charm

Deploys and runs the BMC Manager FastAPI service (`bmc_service.py`). The charm
fetches the `bmc_manager` package at deploy time via git clone (default:
[oem-qa-tools](https://github.com/canonical/oem-qa-tools)) and runs uvicorn with
a systemd unit.

## Prerequisites

A Juju model with a machine (e.g. LXD) to deploy the charm.

## Build

From this directory:

```bash
charmcraft pack
```

## Deploy

```bash
juju deploy ./bmc-service-server_ubuntu-24.04-amd64.charm bmc-service-server \
  --debug --verbose
```

## Configuration

- **port** (int, default 8000): Port for the BMC API service.
- **log-level** (string, default "info"): Log level (info, debug, warning,
  error, critical).
- **repo-url** (string): Git repository URL (default:
  [oem-qa-tools](https://github.com/canonical/oem-qa-tools)).
- **branch** (string): Branch or tag to check out (default: main).
- **source-path** (string): Subfolder inside the repo that contains the
  bmc_manager package (default: Tools/env-setup/bmc_manager for oem-qa-tools).
  Leave empty if the repo root is the bmc_manager tree.

Example with custom repo and branch:

```bash
juju config bmc-service-server \
  repo-url=https://github.com/canonical/oem-qa-tools branch=main \
  source-path=Tools/env-setup/bmc_manager
```

## Usage

Once active, the BMC API is available at `http://<unit-ip>:8000`. Docs:

- Swagger UI: `http://<unit-ip>:8000/docs`
- ReDoc: `http://<unit-ip>:8000/redoc`

The workload is fetched at deploy time from the configured repo and branch; no
bundling of `bmc_manager` in the charm directory is required.

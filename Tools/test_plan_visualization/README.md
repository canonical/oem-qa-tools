# Checkbox Job Database

A web application to inspect, filter, and explore Checkbox jobs and test plans.

## Overview

This application parses the
[Checkbox](https://github.com/canonical/checkbox) repository and provides
a local search engine for job units and test plans. It supports two views:

- **Jobs View** — browse and filter individual job units
- **Test Plans View** — search test plans and explore their nested structure
  down to included jobs

## Features

- **Two-View UI**: Toggle between Jobs and Test Plans views from the header.
- **Automated Parsing**: Scans `.pxu` files and extracts both job units
  (including legacy `plugin:`-style entries) and test plan units.
- **Job Filters**: Filter by Provider, Category, Environ, Manifest Keys,
  and Template ID presence.
- **Search**: Search by job ID, test plan ID, or plan name — searches across
  both jobs and the test plans they belong to.
- **Test Plan Tree**: In the Test Plans view, expand plans to see nested
  sub-plans and directly included jobs.
- **Exclude Support**: Jobs excluded by a test plan's `exclude:` field are
  shown with a strikethrough and an EXCLUDED badge — they remain visible
  but clearly marked.
- **Job Details Modal**: Click Details on any job to see its full attributes
  and the complete test plan hierarchy it belongs to.
- **Plan Details Modal**: Click Details on any test plan card to see all raw
  plan attributes, include/exclude patterns, and nested parts.
- **Dynamic Filters**: Dropdown options update dynamically based on
  current selections.
- **Provider Resolution**: Automatically resolves provider namespaces
  from `manage.py`.
- **Compare Plans**: Switch to the Compare view, enter two plan IDs, and see
  a three-column diff — jobs only in Plan 1, jobs in both, and jobs only in
  Plan 2 (excludes are applied before comparing).

## Getting Started

### Option A: Run Locally

**Prerequisites:** Python 3.10+, `git`

1. **Run the startup script** — it automatically creates a virtual
    environment, installs dependencies, clones/updates the checkbox repo,
    builds the database, and starts the server:

    ```bash
    ./run.sh
    ```

    > To restart (e.g. after a code change):
    >
    > ```bash
    > pkill -f "uvicorn app.main:app"; ./run.sh
    > ```

2. **Access the Web Interface**:
    Open your browser to [http://localhost:8888](http://localhost:8888).

---

### Option B: Run with Docker

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/)

1. **Build the Docker image**:

    ```bash
    sudo docker build -t checkbox-job-db .
    ```

2. **Run the container** (the startup script runs automatically
    inside the container):

    ```bash
    sudo docker run -p 8888:8888 checkbox-job-db
    ```

    > If you get a "port already allocated" error, stop any existing
    > container first:
    >
    > ```bash
    > sudo docker stop $(sudo docker ps -q --filter publish=8888)
    > ```
    >
    > If the port still appears stuck with no process using it, restart
    > the Docker daemon:
    >
    > ```bash
    > sudo systemctl restart docker
    > ```

3. **Access the Web Interface**:
    Open your browser to [http://localhost:8888](http://localhost:8888).

## Project Structure

- `app/`: Source code
  - `main.py`: FastAPI server and API endpoints
  - `parser.py`: PXU file parsing logic (jobs + test plans)
  - `database.py`: SQLite schema (jobs and test_plans tables)
  - `templates/`: HTML/CSS/JS frontend
- `providers/`: *(optional)* Local provider folders — place any custom or
  OEM provider trees here. Jobs and test plans in this folder take
  **priority** over the upstream checkbox repo; duplicates from the repo
  are silently skipped. See [Local Providers](#local-providers) below.
- `Dockerfile`: Container definition
- `run.sh`: Startup script (venv → install → clone/pull → parse → serve)

## API Endpoints

<!-- markdownlint-disable MD013 -->
| Endpoint | Description |
| --- | --- |
| `GET /api/jobs` | List jobs with optional filters: `provider`, `category`, `environ`, `manifest`, `has_template_id`, `search` |
| `GET /api/options` | Get available filter values for the current filter selection |
| `GET /api/testplans?job_id=` | Get the full test plan ancestry for a given job ID |
| `GET /api/plan-tree?search=` | Search test plans and return their full nested tree with included jobs (excluded jobs marked) |
| `GET /api/plan-details?plan_id=` | Get all attributes, include/exclude patterns, and nested parts for a single test plan |
| `GET /api/compare-plans?plan1=&plan2=` | Compare effective job sets of two test plans (excludes applied), returning only-in-1, in-both, only-in-2 |
<!-- markdownlint-enable MD013 -->

## Troubleshooting: Port 8888

**Check what is using port 8888:**

```bash
ss -tlnp sport = :8888          # shows process if owned by current user
sudo ss -tlnp sport = :8888     # shows process for all users
                                # (including Docker/root)
```

**Kill local uvicorn process:**

```bash
pkill -f "uvicorn app.main:app"
```

**Kill via port (requires root for Docker-owned processes):**

```bash
sudo fuser -k 8888/tcp
```

**Stop Docker container holding the port:**

```bash
sudo docker stop $(sudo docker ps -q --filter publish=8888)
```

**List running containers and their ports:**

```bash
sudo docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

**If port appears stuck with no process using it (stale Docker state):**

```bash
sudo systemctl restart docker
```

## Local Providers

Place any custom provider trees inside the `providers/` directory next to
`run.sh`. The directory structure mirrors a normal Checkbox provider:

```text
providers/
    my-provider/
        manage.py          ← namespace is read from here
        units/
            foo/
                jobs.pxu
                test-plan.pxu
```

When the database is built:

1. All `.pxu` files under `providers/` are parsed **first** and their job
   and test-plan IDs are recorded.
2. The upstream checkbox git repo is then scanned; any unit whose ID was
   already loaded from `providers/` is skipped.

This means local providers can **override** upstream job definitions
(e.g. to add missing jobs or corrected summaries) without modifying the
checked-out checkbox repo.

> **Rebuild trigger**: if `providers/` contains any `.pxu` files, the
> database is always rebuilt on startup so local changes are picked up
> automatically.

## Notes

- The database is rebuilt every time the server starts
  (both locally and in Docker).
- `unit: job`, legacy `plugin:`-style, and modern `flags: simple`
  job blocks are all parsed correctly.
- Test plan nested hierarchy is traversed recursively;
  cycle detection is built in.
- The `exclude:` field in test plans is parsed and stored. Excluded jobs
  are shown with a strikethrough in the plan tree and are removed from
  the effective job set when comparing plans.
- Environment variables referenced in a job's `command:` field
  (e.g. `$SERIAL_PORTS_STATIC`) are automatically added to the Environ
  filter even if no explicit `environ:` field is declared.

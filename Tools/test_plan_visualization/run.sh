#!/bin/bash
set -e

REPO_URL="https://github.com/canonical/checkbox.git"
REPO_DIR="checkbox_repo"
VENV_DIR=".venv"

# Set up virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install -q -r requirements.txt

NEEDS_DB_UPDATE=false

if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning checkbox repository..."
    git clone "$REPO_URL" "$REPO_DIR"
    NEEDS_DB_UPDATE=true
else
    echo "Updating repository..."
    cd "$REPO_DIR"
    PULL_OUTPUT=$(git pull)
    cd ..
    if echo "$PULL_OUTPUT" | grep -q "Already up to date."; then
        echo "Repository unchanged, skipping DB rebuild."
    else
        echo "Repository updated, rebuilding database..."
        NEEDS_DB_UPDATE=true
    fi
fi

if [ ! -f "checkbox_jobs.db" ]; then
    echo "Database missing, building..."
    NEEDS_DB_UPDATE=true
fi

# If the local providers/ folder has any .pxu files, always rebuild so
# changes to local providers are picked up on every run.
if find providers -name "*.pxu" -print -quit 2>/dev/null | grep -q .; then
    echo "Local providers/ folder has .pxu files, rebuilding database..."
    NEEDS_DB_UPDATE=true
fi

if [ "$NEEDS_DB_UPDATE" = true ]; then
    echo "Updating database..."
    python3 -c "from app.parser import update_db; update_db('checkbox_repo', 'providers')"
fi

echo "Starting Web Server..."
uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload

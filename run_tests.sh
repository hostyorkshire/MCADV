#!/bin/bash
# Wrapper script to run tests in virtual environment
# This ensures tests always run with the correct dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run './setup_venv.sh' first to create it"
    exit 1
fi

# Run tests with unittest
cd "$SCRIPT_DIR" || exit 1
exec "$VENV_PYTHON" -m unittest discover tests "$@"

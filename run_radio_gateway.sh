#!/bin/bash
# Wrapper script to run radio_gateway.py in virtual environment
# This ensures the gateway always runs with the correct dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run './setup_venv.sh' first to create it"
    exit 1
fi

# Run radio_gateway.py with all arguments passed through
exec "$VENV_PYTHON" "$SCRIPT_DIR/radio_gateway.py" "$@"

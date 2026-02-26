#!/bin/bash
# Wrapper script to run adventure_bot.py in virtual environment
# This ensures the bot always runs with the correct dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run './setup_venv.sh' first to create it"
    exit 1
fi

# Run adventure_bot.py with all arguments passed through
exec "$VENV_PYTHON" "$SCRIPT_DIR/adventure_bot.py" "$@"

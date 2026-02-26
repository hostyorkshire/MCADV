#!/bin/bash
# Quick activation script for MCADV virtual environment
# Usage: source activate_venv.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR"
    echo "Run './setup_venv.sh' first to create it"
    return 1 2>/dev/null || exit 1
fi

source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo "Python: $(which python3)"
echo "To deactivate: deactivate"

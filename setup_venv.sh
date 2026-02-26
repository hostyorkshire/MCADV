#!/bin/bash
# Setup Virtual Environment for MCADV
# This script creates and activates a Python virtual environment
# and installs all required dependencies.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo "================================================"
echo "  MCADV Virtual Environment Setup"
echo "================================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "Python version: $PYTHON_VERSION"
echo ""

# Create virtual environment if it doesn't exist
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_DIR${NC}"
    echo "To recreate it, delete the venv directory first: rm -rf venv"
else
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r "$SCRIPT_DIR/requirements.txt"
echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"
echo -e "${GREEN}✓ logs/ directory created${NC}"
echo ""

echo "================================================"
echo -e "${GREEN}✓ Setup complete!${NC}"
echo "================================================"
echo ""
echo "To activate the virtual environment in the future, run:"
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "Or use the convenience script:"
echo -e "  ${YELLOW}source activate_venv.sh${NC}"
echo ""
echo "To run the bot:"
echo "  python3 adventure_bot.py --help"
echo ""
echo "To run tests:"
echo "  python3 -m unittest discover tests"
echo ""

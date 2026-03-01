#!/bin/bash
# Build standalone executable for MCADV Terminal Client

set -e

echo "Building MCADV Terminal Client executable..."

# Install PyInstaller if not present
pip install pyinstaller

# Build for current platform
pyinstaller \
  --onefile \
  --name mcadv-cli \
  terminal_client.py

echo "Build complete! Executable located at: dist/mcadv-cli"

@echo off
REM Build standalone executable for MCADV Terminal Client

echo Building MCADV Terminal Client executable...

pip install pyinstaller

pyinstaller ^
  --onefile ^
  --name mcadv-cli ^
  terminal_client.py

echo Build complete! Executable located at: dist\mcadv-cli.exe

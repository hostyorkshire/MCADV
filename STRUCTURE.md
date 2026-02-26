# Repository Structure

This document describes the organization of the MCADV repository.

## Root Directory - Main Bot Code

The main bot code stays in the root directory for easy access and deployment:

- `adventure_bot.py` - Main bot application (run this to start the bot)
- `meshcore.py` - MeshCore LoRa serial I/O handler
- `logging_config.py` - Logging configuration
- `requirements.txt` - Python dependencies

## Folders

### `/tests`
Unit tests for the bot
- `test_adventure_bot.py` - Main test suite (62 tests)

### `/logs`
Runtime logs and session data
- `adventure_bot.log` - Application logs
- `sessions.json` - Player sessions (survives reboots)

### `/scripts`
Setup and deployment scripts
- `setup_mcadv.sh` - Installation script for Raspberry Pi
- `adventure_bot.service` - Systemd service configuration

### `/config`
Configuration files for development tools
- `.flake8` - Flake8 linting configuration
- `.pylintrc` - Pylint configuration

### `/guides`
Comprehensive setup guides and documentation
- `README.md` - Index of all setup guides
- `OLLAMA_SETUP.md` - Complete Ollama setup guide (local and LAN)

## Quick Start

```bash
# Run from repository root
bash scripts/setup_mcadv.sh

# Or run manually
python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1
```

## Documentation Files

- `README.md` - Main documentation and deployment guide
- `HARDWARE.md` - Hardware recommendations for distributed architecture
- `PERFORMANCE.md` - Performance optimizations for Pi
- `LICENSE` - Apache 2.0 license
- `STRUCTURE.md` - This file

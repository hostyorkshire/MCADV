# Repository Structure

This document describes the organization of the MCADV repository.

## Root Directory - Main Bot Code

The main bot code stays in the root directory for easy access and deployment:

- `adventure_bot.py` - Main bot application (run this to start the bot)
- `radio_gateway.py` - Radio gateway for distributed mode
- `meshcore.py` - MeshCore LoRa serial I/O handler
- `logging_config.py` - Logging configuration
- `requirements.txt` - Python dependencies

## Virtual Environment Scripts

Scripts for managing the Python virtual environment (VENV):

- `setup_venv.sh` - Create virtual environment and install dependencies
- `activate_venv.sh` - Quick activation helper (use with `source`)
- `run_adventure_bot.sh` - Run adventure bot with venv activated
- `run_radio_gateway.sh` - Run radio gateway with venv activated
- `run_tests.sh` - Run test suite with venv activated

**See [SETUP.md](SETUP.md) for detailed usage instructions.**

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

**Recommended:** Use the virtual environment setup for isolated dependencies.

```bash
# Setup virtual environment (first time)
./setup_venv.sh

# Run the bot using wrapper script
./run_adventure_bot.sh --port /dev/ttyUSB0 --channel adventure

# Or use existing setup scripts (also creates venv)
bash scripts/setup_mcadv.sh
```

See [SETUP.md](SETUP.md) for detailed virtual environment instructions.

## Documentation Files

- `README.md` - Main documentation and deployment guide
- `SETUP.md` - Virtual environment setup guide (NEW)
- `HARDWARE.md` - Hardware recommendations for distributed architecture
- `PERFORMANCE.md` - Performance optimizations for Pi
- `LICENSE` - Apache 2.0 license
- `STRUCTURE.md` - This file

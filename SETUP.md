# MCADV Virtual Environment Setup Guide

This guide explains how to set up and use the MCADV bot in a virtual environment (VENV). Using a virtual environment ensures isolated, self-contained environments for the project, preventing dependency conflicts with other Python projects on your system.

## Why Virtual Environment?

A virtual environment (VENV) provides:
- **Dependency Isolation**: Each project has its own dependencies, preventing conflicts
- **Clean Installation**: Easy to recreate from scratch if something goes wrong
- **Portability**: Ensures consistent behavior across different systems
- **No System-Wide Changes**: Doesn't require sudo/root to install Python packages

## Quick Start

### 1. Initial Setup (First Time Only)

#### Option A: Interactive Setup (Recommended for New Users)

Run the interactive menu-driven setup script that will guide you through the entire configuration:

```bash
./full_setup.sh
```

This interactive script will:
- Create a Python virtual environment in `venv/`
- Install all dependencies from `requirements.txt`
- Detect and configure serial port settings
- Set up channel restrictions
- Configure LLM backend (Offline or Ollama)
- Configure bot behavior (announcements, debug logging)
- Optionally install as a systemd service
- Test your configuration

#### Option B: Manual Setup

For advanced users who prefer manual configuration:

```bash
./setup_venv.sh
```

This script will:
- Create a Python virtual environment in `venv/`
- Install all dependencies from `requirements.txt`
- Create the `logs/` directory
- Display instructions for next steps

### 2. Running the Bot

After setup, you have two options:

#### Option A: Use the wrapper scripts (Recommended)

The wrapper scripts automatically activate the virtual environment:

```bash
# Run the adventure bot
./run_adventure_bot.sh --help
./run_adventure_bot.sh --port /dev/ttyUSB0

# Run the radio gateway (distributed mode)
./run_radio_gateway.sh --bot-server-url http://192.168.1.50:5000

# Run tests
./run_tests.sh
```

#### Option B: Activate manually and run Python directly

```bash
# Activate the virtual environment
source activate_venv.sh

# Now run Python commands normally
python3 adventure_bot.py --help
python3 adventure_bot.py --port /dev/ttyUSB0
python3 -m unittest discover tests

# Deactivate when done
deactivate
```

## Detailed Setup Instructions

### Prerequisites

- Python 3.7 or higher
- `python3-venv` package (usually included with Python)

On Raspberry Pi/Debian/Ubuntu, if needed:
```bash
sudo apt update
sudo apt install python3-venv
```

### Manual Virtual Environment Setup

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create logs directory
mkdir -p logs
```

### Verifying Installation

Check that all dependencies are installed correctly:

```bash
# Using wrapper (no activation needed)
./run_tests.sh

# Or activate and test manually
source activate_venv.sh
python3 -c "import requests; import serial; import flask; print('✓ All imports OK')"
python3 -m unittest discover tests
deactivate
```

## Dependencies

The project requires the following Python packages (see `requirements.txt`):

- **requests** (>=2.31.0): HTTP client for LLM API calls (Ollama, Groq, OpenAI)
- **pyserial** (>=3.5): Serial communication with MeshCore radio hardware
- **flask** (>=2.3.0): Web server for distributed mode (bot server component)

All standard library modules (argparse, json, logging, etc.) are included with Python.

## Using with Existing Setup Scripts

The existing setup scripts (`setup_mcadv.sh`, `setup_bot_server.sh`, `setup_radio_gateway.sh`) already create virtual environments. They will:

1. Create `venv/` directory
2. Install dependencies via `venv/bin/pip`
3. Configure systemd services to use `venv/bin/python3`

So if you've already run one of these scripts, you're already using a virtual environment!

## Troubleshooting

### "Virtual environment not found"

If you see this error when using wrapper scripts:
```bash
Error: Virtual environment not found
Please run './setup_venv.sh' first to create it
```

Solution: Run `./setup_venv.sh` to create the virtual environment.

### "python3: command not found"

Solution: Install Python 3:
```bash
# Raspberry Pi / Debian / Ubuntu
sudo apt install python3 python3-venv

# Other systems: see https://www.python.org/downloads/
```

### "Permission denied" when running scripts

Solution: Make scripts executable:
```bash
chmod +x setup_venv.sh activate_venv.sh run_*.sh
```

### Reinstalling from Scratch

To completely reset the virtual environment:

```bash
# Remove existing venv
rm -rf venv/

# Recreate it
./setup_venv.sh
```

## Updating Dependencies

To update dependencies to newer versions:

```bash
# Activate virtual environment
source activate_venv.sh

# Update packages
pip install --upgrade requests pyserial flask

# Or update all packages
pip list --outdated
pip install --upgrade <package-name>

# Deactivate
deactivate
```

## Systemd Service Configuration

The systemd service files already use the virtual environment Python. When installed via setup scripts, services run as:

```ini
ExecStart=/path/to/MCADV/venv/bin/python3 /path/to/MCADV/adventure_bot.py ...
```

No additional configuration is needed.

## Development Workflow

For active development:

```bash
# 1. Activate virtual environment
source activate_venv.sh

# 2. Make code changes with your editor

# 3. Test changes
python3 -m unittest discover tests

# 4. Run the bot in terminal mode for testing
python3 adventure_bot.py --terminal

# 5. When done, deactivate
deactivate
```

## CI/CD Integration

For automated testing and deployment:

```bash
# Setup (CI environment)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python3 -m unittest discover tests

# Or use wrapper
./run_tests.sh
```

## Summary of Available Scripts

| Script | Purpose |
|--------|---------|
| `full_setup.sh` | **Interactive menu-driven setup** - guides you through complete configuration (recommended for new users) |
| `setup_venv.sh` | Create virtual environment and install dependencies |
| `activate_venv.sh` | Activate virtual environment (use with `source`) |
| `run_adventure_bot.sh` | Run adventure bot with venv activated |
| `run_radio_gateway.sh` | Run radio gateway with venv activated |
| `run_tests.sh` | Run test suite with venv activated |

## Additional Resources

- [Python Virtual Environments Documentation](https://docs.python.org/3/library/venv.html)
- [pip Documentation](https://pip.pypa.io/)
- Project README: `README.md`
- Hardware Setup: `HARDWARE.md`
- Ollama Setup: `guides/OLLAMA_SETUP.md`

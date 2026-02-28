# MCADV - MeshCore Adventure Bot

AI-powered Choose Your Own Adventure bot for MeshCore LoRa mesh networks.

**Offline-First Architecture:** MCADV runs entirely offline using locally-hosted AI models via Ollama—requiring no internet access whatsoever. The network depends solely on the meshcore LoRa mesh network, making it truly independent from external connectivity.

## 🎭 Collaborative Storytelling

**MCADV features collaborative storytelling** where all users on the **#adventures** channel participate in the same shared story. This isn't a solo adventure—it's a community effort where:

- **Everyone shares the same story**: When one user makes a choice, the story progresses for everyone
- **Work together to reach the end**: Collaborate to find the best path without being killed
- **Stories continue until reset**: The adventure runs until someone uses `!reset`, then a new story begins
- **One channel, one story**: All interaction happens on the #adventures channel for the collaborative experience

This creates a unique, dynamic storytelling experience where the mesh community works together to navigate challenges and reach conclusions.

## Hardware Setup

MCADV uses a distributed architecture with two hardware components:

### 🧠 Bot Server (Raspberry Pi 5 or Ubuntu Desktop)

Runs the main bot logic and AI models.

- **For Testing/Development:** Ubuntu Desktop
- **For Production:** Raspberry Pi 5 (8 GB recommended)
- [Setup Guide](docs/hardware_setup/BOT_SERVER_SETUP.md)

### 📻 Radio Gateway (Raspberry Pi Zero 2W)

Handles LoRa mesh communication and forwards messages to the Bot Server.

- **Required:** Raspberry Pi Zero 2W + MeshCore-compatible LoRa radio
- [Setup Guide](docs/hardware_setup/RADIO_GATEWAY_SETUP.md)

### 🔄 Migration Path

1. Develop and test on Ubuntu Desktop
2. Test integration with Pi Zero 2W radio gateway
3. Migrate bot server to Pi 5 for production

- [Migration Guide](docs/hardware_setup/MIGRATION_DESKTOP_TO_PI5.md)

## Quick Start by Hardware Role

### On Bot Server (Ubuntu Desktop or Pi 5)

```bash
./full_setup.sh
# Select: 1) Bot Server

./scripts/testing/test_bot_server.sh
./scripts/pre_deployment_check.sh
```

### On Radio Gateway (Pi Zero 2W)

```bash
./full_setup.sh
# Select: 2) Radio Gateway

./scripts/testing/test_radio_gateway.sh
./scripts/pre_deployment_check.sh
```

### Test Distributed Integration

```bash
# From either device
./scripts/testing/test_distributed_integration.sh --bot-server <hostname>

# Test network connectivity
./scripts/testing/test_network_connectivity.sh --bot-server <hostname>
```

## Quick Setup

For detailed setup instructions with virtual environment (recommended):

**📖 See [SETUP.md](SETUP.md) for complete installation guide**

### Option 1: Interactive Setup (Recommended for New Users)
```bash
# Run the interactive menu-driven setup script
./full_setup.sh
```

This will guide you through:
- **Hardware role selection** (Bot Server / Radio Gateway / Standalone)
- Python environment setup
- Serial port detection and configuration
- Channel and LLM backend configuration
- Systemd service installation
- Testing your configuration

### Option 2: Manual Setup
```bash
# Create virtual environment and install dependencies
./setup_venv.sh

# Run the bot using wrapper script
./run_adventure_bot.sh --help
```

## Testing & Deployment

### Quick Setup Check

Verify your entire setup in one command:

```bash
./scripts/setup_check.sh
```

### Testing Scripts

| Script | Purpose |
|--------|---------|
| `scripts/testing/test_hardware.sh` | Detect and test LoRa radios |
| `scripts/testing/test_ollama.sh` | Test Ollama connectivity and models |
| `scripts/testing/test_bot_integration.sh` | End-to-end bot integration test |
| `scripts/testing/field_test_monitor.sh` | Live tmux monitoring dashboard |

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `scripts/deployment/install_service.sh` | Install as systemd service |
| `scripts/deployment/manage_service.sh` | Interactive service management |
| `scripts/deployment/setup_logrotate.sh` | Configure log rotation |

### Monitoring Scripts

| Script | Purpose |
|--------|---------|
| `scripts/monitoring/monitor_bot.sh` | Real-time status dashboard |
| `scripts/monitoring/tune_performance.sh` | Hardware-tuned recommendations |
| `scripts/monitoring/check_resources.sh` | Cron-friendly health check |

### Quick Commands

```bash
# Check setup
./scripts/setup_check.sh

# Test hardware
./scripts/testing/test_hardware.sh

# Monitor the running bot
./scripts/monitoring/monitor_bot.sh

# Install as systemd service
sudo ./scripts/deployment/install_service.sh

# Manage the service
./scripts/deployment/manage_service.sh
```

See [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) and [docs/FIELD_TESTING.md](docs/FIELD_TESTING.md) for comprehensive testing procedures.

## Documentation

- **[SETUP.md](SETUP.md)** - Virtual environment setup and usage guide
- **[HARDWARE.md](HARDWARE.md)** - Hardware recommendations
- **[PERFORMANCE.md](PERFORMANCE.md)** - Performance optimizations
- **[STRUCTURE.md](STRUCTURE.md)** - Repository structure
- **[docs/LINTING.md](docs/LINTING.md)** - Code linting guide and standards
- **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing scripts and procedures
- **[docs/FIELD_TESTING.md](docs/FIELD_TESTING.md)** - Field testing procedures and checklists
- **[guides/](guides/)** - Detailed setup guides (Ollama, Raspberry Pi, Production Deployment, etc.)

### Hardware Setup Guides

- **[docs/hardware_setup/BOT_SERVER_SETUP.md](docs/hardware_setup/BOT_SERVER_SETUP.md)** - Bot Server (Pi 5 / Ubuntu Desktop) setup
- **[docs/hardware_setup/RADIO_GATEWAY_SETUP.md](docs/hardware_setup/RADIO_GATEWAY_SETUP.md)** - Radio Gateway (Pi Zero 2W) setup
- **[docs/hardware_setup/POWER_MANAGEMENT.md](docs/hardware_setup/POWER_MANAGEMENT.md)** - Power consumption and battery sizing
- **[docs/hardware_setup/PHYSICAL_SETUP.md](docs/hardware_setup/PHYSICAL_SETUP.md)** - Enclosures, antennas, and cable management
- **[docs/hardware_setup/MIGRATION_DESKTOP_TO_PI5.md](docs/hardware_setup/MIGRATION_DESKTOP_TO_PI5.md)** - Migrating from Ubuntu Desktop to Pi 5

## Quick Model Selection Guide

**Best models for CYOA bot:**

| Hardware | Recommended Model | Size | Speed | Quality | Notes |
|----------|------------------|------|-------|---------|-------|
| **Pi 4/5 (4GB or 8GB)** | `llama3.2:1b` | 1.3 GB | Fast (2-3s/scene) | Good | Lightweight, great for Pi |
| **Pi 5 (8GB)** | `llama3.2:3b` | 3.2 GB | Medium (4-6s/scene) | Very Good | Good balance on Pi 5 |
| **Jetson/PC (8GB+)** | `llama3.1:8b` ⭐ | 4.9 GB | Medium (3-5s/scene) | Excellent | **Best storytelling model** – recommended for CYOA |
| **Jetson/PC (8GB+)** | `llama3.2:3b` or `llama3:8b` | 3.2-4.7 GB | Medium-Slow | Excellent | Alternative for 8GB+ hardware |
| **High-end PC / Server (48GB+ VRAM)** | `llama3.3:70b` | 43 GB | Slow (10-30s/scene) | Outstanding | Best quality storytelling, needs serious hardware |

> ⭐ **Recommended for CYOA:** `llama3.1:8b` (~4.9 GB) hits the sweet spot of storytelling quality, narrative coherence, and speed. It handles branching story logic well and keeps long-term context across choices. Pull it with:
> ```bash
> ollama pull llama3.1:8b
> ```
> If you have 48GB+ VRAM available, `llama3.3:70b` (~43 GB) produces outstanding prose and story depth, but is overkill for most deployments.

**Storage requirements:**
- Small model: ~1-2 GB per model
- Medium model: ~3-5 GB per model
- Large model: ~43+ GB per model
- **239 GB SSD:** Plenty of space for all models + OS + data

*Note: Speed is per scene generation (each story prompt/continuation)*

See [Storage Capacity Planning](guides/OLLAMA_SETUP.md#storage-capacity-planning) for detailed recommendations based on your available storage.

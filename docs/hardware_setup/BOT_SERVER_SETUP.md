# Bot Server Setup Guide

The **Bot Server** is the "brains" of MCADV. It runs the adventure bot logic, hosts the Ollama LLM, and exposes an HTTP API that the Radio Gateway connects to.

## Hardware Options

| Hardware | Use Case | RAM | Notes |
|----------|----------|-----|-------|
| **Ubuntu Desktop** | Development / testing | 8 GB+ | Easiest to set up; fastest iteration |
| **Raspberry Pi 5** | Production deployment | 8 GB | Recommended for field events |
| **Raspberry Pi 4** | Budget production | 4–8 GB | Slower LLM inference |

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| Storage | 16 GB | 32 GB+ (for OS + models) |
| Python | 3.7+ | 3.11 |
| Network | WiFi or Ethernet | Ethernet (for reliability) |
| Power | 5V 5A USB-C (Pi 5) | AC adapter (desktop) |

## Power Specifications

| Hardware | Idle | Load | Peak |
|----------|------|------|------|
| Pi 5 8 GB | ~5 W | ~15 W | ~25 W |
| Pi 4 8 GB | ~3 W | ~10 W | ~15 W |
| Ubuntu Desktop | ~20 W | ~50 W+ | ~100 W+ |

## Setup Steps

### 1. Install Operating System

**Ubuntu Desktop (testing/development):**
- Download Ubuntu 22.04+ from [ubuntu.com](https://ubuntu.com)
- Install normally; ensure Python 3.7+ is available

**Raspberry Pi 5 (production):**
- Flash Raspberry Pi OS (64-bit) using Raspberry Pi Imager
- Enable SSH: add empty `ssh` file to boot partition
- Connect via SSH or keyboard/monitor

### 2. Clone Repository

```bash
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV
```

### 3. Run Interactive Setup

```bash
./full_setup.sh
# Select: Bot Server (option 1)
```

This will:
- Create Python virtual environment
- Install dependencies
- Configure serial port (if radio connected directly)
- Configure Ollama backend

### 4. Install Ollama (for AI-generated stories)

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &

# Pull recommended model
ollama pull llama3.2:1b    # Fast, good for Pi 4/5
# or
ollama pull llama3.1:8b    # Best quality, needs 8 GB RAM
```

### 5. Verify Setup

```bash
./scripts/pre_deployment_check.sh
./scripts/testing/test_bot_server.sh
```

### 6. Start the Bot

```bash
# Manual start
./run_adventure_bot.sh

# Or install as systemd service
sudo ./scripts/deployment/install_service.sh
sudo systemctl start mcadv-bot
```

## Configuration

Edit `config.yaml` to customise:

```yaml
server:
  host: "0.0.0.0"
  port: 5000

llm:
  backend: "ollama"
  url: "http://localhost:11434"
  model: "llama3.2:1b"
```

## Monitoring

```bash
# Real-time status dashboard
./scripts/monitoring/monitor_bot.sh

# Temperature and power monitoring
./scripts/monitoring/monitor_power_temp.sh --once

# Resource check (for cron)
./scripts/monitoring/check_resources.sh
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama not responding | `ollama serve` or `sudo systemctl start ollama` |
| Port 5000 in use | Check `ss -tlnp \| grep 5000`; kill conflicting process |
| High CPU temperature | Improve cooling; reduce Ollama model size |
| Out of memory | Use smaller model (`llama3.2:1b`); close other apps |

See [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for more.

# MCADV - MeshCore Adventure Bot

AI-powered Choose Your Own Adventure bot for MeshCore LoRa mesh networks.

## Quick Setup

For detailed setup instructions with virtual environment (recommended):

**📖 See [SETUP.md](SETUP.md) for complete installation guide**

### Option 1: Interactive Setup (Recommended for New Users)
```bash
# Run the interactive menu-driven setup script
./full_setup.sh
```

This will guide you through:
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

## Documentation

- **[SETUP.md](SETUP.md)** - Virtual environment setup and usage guide
- **[HARDWARE.md](HARDWARE.md)** - Hardware recommendations
- **[PERFORMANCE.md](PERFORMANCE.md)** - Performance optimizations
- **[STRUCTURE.md](STRUCTURE.md)** - Repository structure
- **[guides/](guides/)** - Detailed setup guides (Ollama, Raspberry Pi, etc.)

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

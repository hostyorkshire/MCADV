# MCADV – MeshCore Adventure Bot

An AI-powered **Choose Your Own Adventure** bot for the
[MeshCore](https://github.com/meshcore-dev/MeshCore) LoRa mesh radio network.

---

## What is Choose Your Own Adventure?

**Choose Your Own Adventure** (CYOA) is an interactive storytelling format that
puts you in control of the narrative. Unlike traditional stories where you're a
passive reader, CYOA books let you make decisions that change the plot.

The format was popularized by the **Choose Your Own Adventure** book series
created by Edward Packard in the 1970s and published by Bantam Books starting
in 1979. These books became a cultural phenomenon, selling over 250 million
copies worldwide and introducing millions of readers to interactive fiction.

### How CYOA works:

1. **You read a scene** – The story sets up a situation or dilemma
2. **You make a choice** – Usually 2-3 options like "Turn left" or "Investigate the noise"
3. **The story branches** – Your choice leads to a new scene with new consequences
4. **Multiple endings** – Different paths lead to different outcomes (some triumphant, some tragic)

This format transformed reading from a linear experience into an adventure where
**your decisions matter**. MCADV brings this classic interactive storytelling
format to LoRa mesh networks, letting you and your friends experience branching
adventures over the radio.

---

## How it works

### Standalone Mode (Single Pi)
```
Player → LoRa radio → Pi 4/5 (adventure_bot.py) → LLM or offline tree → LoRa radio → Player
                         |
                   Bot runs here
                   All game logic
                   Radio + LLM
```

**Hardware:** Pi 4/5 (4GB+ RAM) with LoRa radio connected via USB  
**Storage:** SSD via USB recommended for LLM models  
**Alternative:** Desktop PC running Ubuntu (for development/testing)

### Distributed Mode (Recommended for Pi Zero 2W)
```
Player → LoRa → Pi Zero 2W → HTTP → Pi 4/5 (adventure_bot.py) → HTTP → Pi Zero 2W → LoRa → Player
                   |                              |
              Radio Only                    Bot runs here
              MeshCore I/O                  All game logic
              ~15MB RAM                     LLM Processing
                                           Story Generation
                                           ~4GB RAM
                                           SSD storage via USB
```

**Pi Zero 2W:** Handles only LoRa radio communication (future: radio_gateway.py)  
**Pi 4/5:** Runs the bot with all game logic and LLM (adventure_bot.py)  
**Storage:** SSD connected via USB to Pi 4/5 for LLM model storage  
**Alternative:** Desktop PC running Ubuntu instead of Pi 4/5 (for development/testing)

> **Note:** Currently only standalone mode is implemented. Distributed mode components 
> (radio_gateway.py and llm_server.py) are planned for future development.

1. A player types `!adv` on the MeshCore channel.
2. The bot generates (or retrieves) the opening scene and three choices.
3. The player replies `1`, `2`, or `3`.
4. The story continues until it reaches a conclusion (`THE END`).

---

## Quick start

### Terminal Mode (Testing & Playing without Hardware)

Try MCADV from your terminal without any radio hardware:

```bash
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python3 adventure_bot.py --terminal
```

This opens an interactive terminal session where you can test all commands and play through adventures. Perfect for:
- Testing the bot before deploying to hardware
- Playing adventures offline
- Development and debugging
- Learning how the bot works

### Radio Mode (Deployment)

For production deployment on LoRa mesh network:

```bash
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
bash scripts/setup_mcadv.sh  # creates venv, installs deps, creates service
sudo systemctl start adventure_bot
sudo journalctl -u adventure_bot -f
```

---

## Commands (send on the channel)

| Command | Description |
|---------|-------------|
| `!adv` | Start a fantasy adventure |
| `!adv scifi` | Start a sci-fi adventure |
| `!adv horror` | Start a horror adventure |
| `!start [theme]` | Alias for `!adv` |
| `1` / `2` / `3` | Make a choice |
| `!status` | Show your current adventure state |
| `!quit` | End your adventure early |
| `!help` | Show available commands |

---

## Hardware Requirements

### Where Does the Bot Run? 🤖

**The bot (adventure_bot.py) always runs on the more powerful device:**
- ✅ **Pi 4/5 (4GB+ RAM)** - Runs bot + LLM, connects to LoRa radio via USB
- ✅ **Desktop PC (Ubuntu)** - For development/testing, acts like Pi 4/5
- ❌ **Pi Zero 2W** - Only for radio gateway (future implementation)

### For Pi Zero 2W Deployments ⚠️

**The Pi Zero 2W (512MB RAM) cannot run the bot or LLMs.** It's perfect for handling 
LoRa radio communication but needs a partner for the bot and AI processing.

**Recommended distributed setup:**
- **Pi Zero 2W** ($15) - Radio gateway ONLY (future: radio_gateway.py)
- **Pi 5 8GB** ($80) - **Runs the bot (adventure_bot.py)** with Ollama
- **SSD via USB** ($40) - Storage for LLM models on Pi 4/5
- **Total cost:** ~$210 (with accessories)

> **Current Status:** Distributed mode is planned but not yet implemented.  
> Currently, run adventure_bot.py in standalone mode on Pi 4/5 with radio attached.

See **[HARDWARE.md](HARDWARE.md)** for complete hardware recommendations including:
- Raspberry Pi 5 (budget option)
- NVIDIA Jetson Orin Nano (best performance)
- Mini PC / NUC (maximum power)
- Desktop PC running Ubuntu (for development)
- Network setup, power budgets, and shopping lists

### For Standalone Deployments

**Minimum:** Raspberry Pi 4 (4GB+ RAM) with offline story trees  
**Recommended:** Raspberry Pi 4/5 (8GB RAM) with local Ollama + SSD storage  
**Development:** Desktop PC running Ubuntu with LoRa radio via USB

---

## Design options

### Option 1 – LLM backend

The bot tries Ollama first, then falls back to offline story trees if unavailable.

| Priority | Backend | How to enable | Cost | Needs internet? |
|----------|---------|--------------|------|----------------|
| 1 | **Ollama (local/LAN)** | `--ollama-url http://<host>:11434 --model llama3.2:1b` | Free | No (LAN only) |
| 2 | **Offline story trees** | *(automatic fallback, always available)* | Free | No |

#### Choosing an LLM backend

**For distributed architecture (future):**
- **Pi Zero 2W:** Handles radio only (future: radio_gateway.py)
- **Pi 4/5:** Runs the bot (adventure_bot.py) with Ollama
- **Storage:** SSD via USB on Pi 4/5 for LLM models
- **Network:** WiFi or Ethernet between devices
- **Development:** Use Ubuntu desktop PC instead of Pi 4/5

**For Pi 4/5 standalone (current implementation):**
- **Ollama on same device** – Pi 4/5 with 4GB+ RAM can run small models
- **Ollama on your LAN** – run `ollama serve` on a laptop, desktop, or another Pi
- **No LLM / offline** – three fully self-contained story trees (fantasy, sci-fi, horror)
- **Storage:** SSD via USB recommended for model storage (2-8GB per model)

**For development/testing:**
- Use Ubuntu desktop PC with LoRa radio connected via USB
- Run adventure_bot.py directly on your desktop
- Acts exactly like Pi 4/5 deployment

📖 **See [guides/OLLAMA_SETUP.md](guides/OLLAMA_SETUP.md) for a comprehensive guide on setting up Ollama (local and LAN).**

---

### Option 2 – Story themes

Three built-in offline story trees are included.  The LLM can generate
stories for any theme you type (`!adv pirate`, `!adv western`, etc.).

| Theme | Keyword | Setting |
|-------|---------|---------|
| Fantasy *(default)* | `fantasy` | Medieval crossroads, forests, dragons |
| Sci-fi | `scifi` | Colony ship disaster, AI, escape pods |
| Horror | `horror` | Locked manor, fog, cryptic choices |

---

## Installation

### Terminal Mode (No Hardware Required)

Test and play adventures directly from your terminal without any radio hardware:

```bash
# 1. Clone the repository
git clone https://github.com/hostyorkshire/MCADV
cd MCADV

# 2. Set up Python environment
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Run in terminal mode
venv/bin/python3 adventure_bot.py --terminal

# Or with debug output
venv/bin/python3 adventure_bot.py --terminal --debug
```

**Terminal mode features:**
- ✅ No radio hardware needed
- ✅ Works on any Python 3.7+ system (Linux, macOS, Windows)
- ✅ All story themes available (fantasy, scifi, horror)
- ✅ Full LLM support (Ollama, offline)
- ✅ Perfect for development, testing, and just playing

**Example session:**
```
$ python3 adventure_bot.py --terminal

======================================================================
  MCADV - Choose Your Own Adventure (Terminal Mode)
======================================================================
Type '!adv' to begin your adventure!

You> !adv
📖 You wake at a crossroads at dusk. Strange sounds fill the air.
1:Take the road 2:Enter forest 3:Make camp

You> 1
📖 A bridge ahead. A troll demands: 'Pay or fight!'
1:Pay the toll 2:Fight him 3:Sneak past
```

### On Raspberry Pi 4/5 (Recommended)

The bot runs on Pi 4/5 with the LoRa radio connected via USB. Optional SSD for LLM storage.

```bash
# 1. Install OS dependencies
sudo apt-get update && sudo apt-get install -y python3-pip python3-serial python3-venv

# 2. Clone and set up
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Run manually to test (Ctrl+C to stop)
venv/bin/python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1 --debug

# 4. Install as a service that starts on boot
bash scripts/setup_mcadv.sh
sudo systemctl start adventure_bot
```

**Optional SSD Setup:**
```bash
# Mount SSD for LLM model storage
sudo mkdir -p /mnt/ssd
sudo mount /dev/sda1 /mnt/ssd
# Add to /etc/fstab for automatic mounting

# Install Ollama and store models on SSD
export OLLAMA_MODELS=/mnt/ssd/ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```

### On Ubuntu Desktop PC (Development/Testing)

Use your desktop PC as a substitute for Pi 4/5 during development.

```bash
# 1. Install dependencies
sudo apt-get update && sudo apt-get install -y python3-pip python3-serial python3-venv

# 2. Clone and set up
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Connect LoRa radio via USB and run
venv/bin/python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1 --debug
```

### Pi Zero 2W (Future - Radio Gateway Only)

> **Note:** Distributed mode not yet implemented. Pi Zero 2W will only run the radio 
> gateway component (radio_gateway.py) in future releases. The bot itself runs on Pi 4/5.

For now, use Pi 4/5 in standalone mode for all deployments.

---

## Configuration reference

```
usage: adventure_bot.py [-h] [-p PORT] [-b BAUD] [-d] [-a] [-t] [-c CHANNEL_IDX]
                        [--ollama-url OLLAMA_URL] [--model MODEL]

options:
  -h, --help         Show this help message and exit
  -p, --port         Serial port (e.g. /dev/ttyUSB0). Auto-detects if omitted.
  -b, --baud         Baud rate (default: 115200)
  -d, --debug        Enable verbose debug output
  -a, --announce     Send a periodic announcement every 3 hours
  -t, --terminal     Run in terminal mode (no radio hardware needed)
  -c, --channel-idx  Only respond on this MeshCore channel index (e.g. 1)
  --ollama-url       Ollama base URL (default: http://localhost:11434)
  --model            Ollama model name (default: llama3.2:1b)
```

Environment variables: `OLLAMA_URL`, `OLLAMA_MODEL`

**Examples:**
```bash
# Terminal mode (no hardware)
python adventure_bot.py --terminal

# Radio mode with auto-detected port
python adventure_bot.py --channel-idx 1

# Radio mode with specific port
python adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1 --debug

# With Ollama LLM on local network
python adventure_bot.py --terminal --ollama-url http://192.168.1.50:11434

# With specific Ollama model
python adventure_bot.py --terminal --model llama3.2:3b
```

---

## Architecture

```
adventure_bot.py          ← main bot, all game logic
  └── uses MeshCore API   ← meshcore.py handles all LoRa serial I/O
        └── logging_config.py
logs/
  ├── adventure_bot.log
  ├── sessions.json       ← player sessions survive reboots
  └── …
tests/
  └── test_adventure_bot.py
scripts/
  ├── setup_mcadv.sh      ← installation script
  └── adventure_bot.service
config/
  ├── .flake8             ← linting configuration
  └── .pylintrc
```

See [STRUCTURE.md](STRUCTURE.md) for detailed repository organization.

### Message flow

```
MeshCore radio (USB serial)
  │  binary frame (LoRa)
  ▼
meshcore.py  ─── _dispatch_channel_message() ──▶ handle_message()
                                                      │
                                          ┌───────────┼───────────┐
                                          │           │           │
                                        !adv       1/2/3       !quit
                                          │           │           │
                                   _generate_story()  │     _clear_session()
                                   ┌──────┴──────┐    │
                                 Ollama         Offline
                                   └──────┬──────┘
                                          ▼
                                   mesh.send_message()  ──▶ LoRa radio
```

---

## Performance & Architecture

### Single Pi Mode
MCADV is **optimized for Raspberry Pi** hardware with:
- ⚡ Fast startup (instant in offline mode)
- 💾 Low memory usage (~20MB for 50 concurrent players)
- 💿 Reduced SD card wear (batched I/O)
- 🔌 HTTP connection pooling for faster LLM calls

See [PERFORMANCE.md](PERFORMANCE.md) for details on optimizations and benchmarks.

### Distributed Mode (Pi Zero 2W + Partner)

**Why distributed architecture?**
- Pi Zero 2W is perfect for radio I/O but lacks power for LLM processing
- Separates concerns: radio gateway vs. compute server
- Scalable: Multiple Pi Zeros can share one LLM server
- Lower latency: Pi Zero handles radio immediately, offloads thinking

**Architecture benefits:**
- 🔥 **Fast radio response** - Pi Zero 2W handles LoRa with <10ms latency
- 🧠 **Powerful thinking** - Pi 5/Jetson runs LLM with GPU acceleration
- 🔋 **Low power** - Pi Zero 2W uses <1W, can run on small battery
- 📡 **Multi-node** - One LLM server can serve 3-5 radio gateways
- 💰 **Cost effective** - Total setup ~$170 vs. $80+ per standalone unit

**Performance:**
| Setup | Radio Latency | LLM Time | Total Response | Power |
|-------|---------------|----------|----------------|-------|
| Pi Zero standalone | <10ms | N/A (offline only) | <100ms | <1W |
| Pi Zero + Pi 5 | <10ms | 2-5s | 2-5s | ~12W |
| Pi Zero + Jetson | <10ms | 500ms-2s | 500ms-2s | ~25W |
| Pi 4 standalone | <50ms | 3-8s | 3-8s | ~8W |

See [HARDWARE.md](HARDWARE.md) for complete hardware guide and setup instructions.

---

## Running the tests

```bash
python -m unittest tests/test_adventure_bot.py -v
```

64 tests, no radio hardware required.

**Interactive testing:**

You can also test interactively using terminal mode:

```bash
python adventure_bot.py --terminal
```

This lets you play through adventures and verify all commands work correctly without needing any hardware.

---

## Acknowledgements

Built on the same MeshCore companion radio binary protocol as
[MCWB](https://github.com/hostyorkshire/MCWB).  Story model inspired by
[Choose Your Own Adventure](https://en.wikipedia.org/wiki/Choose_Your_Own_Adventure).

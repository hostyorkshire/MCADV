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
Player → LoRa radio → Pi (adventure_bot.py) → LLM or offline tree → LoRa radio → Player
```

### Distributed Mode (Recommended for Pi Zero 2W)
```
Player → LoRa → Pi Zero 2W (radio_gateway) → HTTP → Pi 5 (llm_server) → HTTP → Pi Zero 2W → LoRa → Player
                   |                                        |
              Radio I/O                              LLM Processing
              Sessions                               Story Generation
              ~15MB RAM                              ~4GB RAM
```

1. A player types `!adv` on the MeshCore channel.
2. The bot generates (or retrieves) the opening scene and three choices.
3. The player replies `1`, `2`, or `3`.
4. The story continues until it reaches a conclusion (`THE END`).

---

## Quick start

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

### For Pi Zero 2W Deployments ⚠️

**The Pi Zero 2W (512MB RAM) cannot run LLMs locally.** It's perfect for handling 
LoRa radio communication but needs a partner for AI processing.

**Recommended distributed setup:**
- **Pi Zero 2W** ($15) - Radio gateway, message handling
- **Pi 5 8GB** ($80) - LLM server with Ollama
- **Total cost:** ~$170 (with accessories)

See **[HARDWARE.md](HARDWARE.md)** for complete hardware recommendations including:
- Raspberry Pi 5 (budget option)
- NVIDIA Jetson Orin Nano (best performance)
- Mini PC / NUC (maximum power)
- Network setup, power budgets, and shopping lists

### For Standalone Deployments

**Minimum:** Raspberry Pi 3B+ or 4 (1GB+ RAM) with cloud LLM (OpenAI/Groq)  
**Recommended:** Raspberry Pi 4/5 (4GB+ RAM) with local Ollama

---

## Design options

### Option 1 – LLM backend

The bot tries each backend in order and falls back to the next if unavailable.

| Priority | Backend | How to enable | Cost | Needs internet? |
|----------|---------|--------------|------|----------------|
| 1 | **Remote LLM Server** | `--llm-server-url http://pi5.local:5000` | Free | No (LAN only) |
| 2 | **Ollama (local/LAN)** | `--ollama-url http://<host>:11434 --model llama3.2:1b` | Free | No (LAN only) |
| 3 | **OpenAI** | `--openai-key sk_…` or `$OPENAI_API_KEY` | ~$0.0002/turn | Yes |
| 4 | **Groq** | `--groq-key gsk_…` or `$GROQ_API_KEY` | Free tier | Yes |
| 5 | **Offline story trees** | *(automatic fallback, always available)* | Free | No |

#### Choosing an LLM backend

**For Pi Zero 2W:** Use the distributed architecture (see HARDWARE.md)
- Run `llm_server.py` on a Pi 5 or more powerful device
- Run `radio_gateway.py` on the Pi Zero 2W
- Connect via local network (WiFi or Ethernet)

**For Pi 3B+/4/5 standalone:**
- **Ollama on same device** – Pi 4/5 with 4GB+ RAM can run small models
- **Ollama on your LAN** – run `ollama serve` on a laptop, desktop, or another Pi
- **Groq free tier** – very fast cloud inference, generous free quota
- **OpenAI** – reliable, small cost per adventure
- **No LLM / offline** – three fully self-contained story trees (fantasy, sci-fi, horror)

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

## Installation on Raspberry Pi Zero

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

---

## Configuration reference

```
usage: adventure_bot.py [-h] [-p PORT] [-b BAUD] [-d] [-a] [-c CHANNEL_IDX]
                        [--ollama-url OLLAMA_URL] [--model MODEL]
                        [--openai-key OPENAI_KEY] [--groq-key GROQ_KEY]

options:
  -p, --port         Serial port (e.g. /dev/ttyUSB0). Auto-detects if omitted.
  -b, --baud         Baud rate (default: 115200)
  -d, --debug        Enable verbose debug output
  -a, --announce     Send a periodic announcement every 3 hours
  -c, --channel-idx  Only respond on this MeshCore channel index (e.g. 1)
  --ollama-url       Ollama base URL (default: http://localhost:11434)
  --model            Ollama model name (default: llama3.2:1b)
  --openai-key       OpenAI API key
  --groq-key         Groq API key
```

Environment variables: `OLLAMA_URL`, `OLLAMA_MODEL`, `OPENAI_API_KEY`, `GROQ_API_KEY`

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
                                 Ollama/OpenAI  Offline
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

62 tests, no radio hardware required.

---

## Acknowledgements

Built on the same MeshCore companion radio binary protocol as
[MCWB](https://github.com/hostyorkshire/MCWB).  Story model inspired by
[Choose Your Own Adventure](https://en.wikipedia.org/wiki/Choose_Your_Own_Adventure).

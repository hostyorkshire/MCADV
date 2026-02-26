# MCADV – MeshCore Adventure Bot

An AI-powered **Choose Your Own Adventure** bot for the
[MeshCore](https://github.com/meshcore-dev/MeshCore) LoRa mesh radio network.
Designed to run on a **Raspberry Pi Zero** connected to a MeshCore companion
radio via USB serial.

Players interact on a dedicated MeshCore channel.  Every message fits within
**200 characters** to respect LoRa's small payload budget.

---

## How it works

```
Player → LoRa radio → Pi Zero (adventure_bot.py) → LLM or offline tree → LoRa radio → Player
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
bash scripts/setup_mcadv.sh  # installs deps, creates service
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

## Design options

### Option 1 – LLM backend

The bot tries each backend in order and falls back to the next if unavailable.

| Priority | Backend | How to enable | Cost | Needs internet? |
|----------|---------|--------------|------|----------------|
| 1 | **Ollama (local/LAN)** | `--ollama-url http://<host>:11434 --model llama3.2:1b` | Free | No (LAN only) |
| 2 | **OpenAI** | `--openai-key sk_…` or `$OPENAI_API_KEY` | ~$0.0002/turn | Yes |
| 3 | **Groq** | `--groq-key gsk_…` or `$GROQ_API_KEY` | Free tier | Yes |
| 4 | **Offline story trees** | *(automatic fallback, always available)* | Free | No |

#### Choosing an LLM backend

**Pi Zero 2W cannot run a local LLM** (512 MB RAM is not enough even for the
smallest quantised models).  Realistic options are:

- **Ollama on your LAN** – run `ollama serve` on a laptop, desktop, or a
  more powerful Pi.  Point the bot at `http://<that-machine's-ip>:11434`.
  Recommended models for speed: `llama3.2:1b`, `tinyllama`, `phi3:mini`.
- **Groq free tier** – very fast cloud inference, generous free quota.
  Sign up at <https://console.groq.com>.
- **OpenAI** – reliable, small cost per adventure.
- **No LLM / offline** – the bot uses three fully self-contained story
  trees (fantasy, sci-fi, horror).  Zero dependencies, works anywhere.

---

### Option 2 – Gameplay mode

#### Per-user mode *(default)*

Each player runs their **own independent adventure** in parallel.  When Alice
types `!adv` and Bob types `!adv`, both get separate stories broadcast to the
channel.  Good for: personal play, small groups.

```
Alice: !adv fantasy
Bot:   You wake at a crossroads…  1:Take road 2:Forest 3:Camp
Alice: 2
Bot:   Ancient trees tower above…

Bob: !adv scifi
Bot:   Your colony ship drifts off course…
```

#### Shared mode (`--shared`)

**One adventure per channel** – anyone can advance the story.  The first
person to reply with `1`, `2`, or `3` sets the next chapter.  The bot
announces who made each choice.  Good for: community play, radio drama feel.

```
Alice: !adv horror
Bot:   🎲 Alice started a horror adventure!
       You wake alone in an old manor…
       1:Upstairs 2:Window 3:Cellar

Bob:   2
Bot:   Bob chose 2:
       Outside: thick fog and silent figures…
```

---

### Option 3 – Story themes

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
sudo apt-get update && sudo apt-get install -y python3-pip python3-serial

# 2. Clone and set up
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
pip3 install --user -r requirements.txt

# 3. Run manually to test (Ctrl+C to stop)
python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1 --debug

# 4. Install as a service that starts on boot
bash scripts/setup_mcadv.sh
sudo systemctl start adventure_bot
```

---

## Configuration reference

```
usage: adventure_bot.py [-h] [-p PORT] [-b BAUD] [-d] [-a] [-c CHANNEL_IDX]
                        [--shared]
                        [--ollama-url OLLAMA_URL] [--model MODEL]
                        [--openai-key OPENAI_KEY] [--groq-key GROQ_KEY]

options:
  -p, --port         Serial port (e.g. /dev/ttyUSB0). Auto-detects if omitted.
  -b, --baud         Baud rate (default: 115200)
  -d, --debug        Enable verbose debug output
  -a, --announce     Send a periodic announcement every 3 hours
  -c, --channel-idx  Only respond on this MeshCore channel index (e.g. 1)
  --shared           Shared mode: one adventure per channel
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

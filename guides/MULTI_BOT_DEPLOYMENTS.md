# Multi-Bot Deployments Guide

**Quick reference guide for running multiple bots on one mesh network.**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Why Run Multiple Bots](#why-run-multiple-bots)
4. [Architecture Options](#architecture-options)
5. [Channel Separation Strategy](#channel-separation-strategy)
6. [Standalone Multi-Bot Setup](#standalone-multi-bot-setup)
7. [Shared Bot Server with Multiple Gateways](#shared-bot-server-with-multiple-gateways)
8. [Node ID Configuration](#node-id-configuration)
9. [Session Management](#session-management)
10. [Systemd Service Naming](#systemd-service-naming)
11. [Configuration File Management](#configuration-file-management)
12. [Monitoring Multiple Instances](#monitoring-multiple-instances)
13. [Testing Multi-Bot Setups](#testing-multi-bot-setups)
14. [Troubleshooting](#troubleshooting)
15. [Next Steps](#next-steps)

---

## Overview

MCADV supports running **multiple bot instances** on a single MeshCore mesh network. Each bot instance handles a separate LoRa channel, enabling:

- **Coverage redundancy** — multiple bots covering the same channel for failover
- **Channel separation** — different themes or games on different channels
- **Load distribution** — split player traffic across multiple instances

Collaborative storytelling in MCADV is **channel-based**: all players on the same channel share one story. Running a bot per channel gives each group their own independent adventure.

---

## Prerequisites

- MCADV installed on one or more devices
- Multiple MeshCore LoRa radios (one per standalone bot, or shared in distributed mode)
- Basic familiarity with systemd services
- For distributed mode: see [DISTRIBUTED_ARCHITECTURE.md](DISTRIBUTED_ARCHITECTURE.md)

---

## Why Run Multiple Bots

### Coverage and Redundancy

A single LoRa radio covers one geographic area. Running bots at multiple locations with overlapping range ensures players always have access:

```
Location A bot (channel 1) ──► covers west side of festival
Location B bot (channel 1) ──► covers east side of festival
```

Both bots can serve the **same channel** — the mesh routes messages to whichever bot is reachable.

### Different Themes per Channel

Each channel can run a completely different adventure theme:

```
Channel 1 ── Fantasy adventure bot
Channel 2 ── Sci-fi adventure bot
Channel 3 ── Horror bot (adults only)
```

Players choose their channel to pick their preferred genre.

### Event-Specific Bots

For large events, dedicate channels to specific groups:

```
Channel 1 ── Public (open to all)
Channel 2 ── VIP participants
Channel 3 ── Staff / volunteers
```

---

## Architecture Options

### Option A: Multiple Standalone Bots

Each bot has its own radio, runs the full `adventure_bot.py`, and connects to an LLM directly.

```
┌──────────────────────┐    ┌──────────────────────┐
│  Pi Zero 2W  (bot 1) │    │  Pi Zero 2W  (bot 2) │
│  adventure_bot.py    │    │  adventure_bot.py    │
│  channel_idx=1       │    │  channel_idx=2       │
│  theme=fantasy       │    │  theme=scifi         │
│  offline / Ollama LAN│    │  offline / Ollama LAN│
└──────────────────────┘    └──────────────────────┘
```

**Pros:** Simple, independent, no single point of failure
**Cons:** Duplicates resources; each needs its own radio and LLM access

### Option B: Shared Bot Server with Multiple Gateways

One bot server handles all logic; multiple radio gateways (on different channels) feed into it.

```
┌────────────────────┐    ┌────────────────────┐
│  Pi Zero 2W #1     │    │  Pi Zero 2W #2     │
│  radio_gateway.py  │    │  radio_gateway.py  │
│  channel_idx=1     │    │  channel_idx=2     │
└────────┬───────────┘    └────────┬───────────┘
         │ HTTP                    │ HTTP
         └──────────┬──────────────┘
                    ▼
         ┌──────────────────────────┐
         │  Pi 4/5 Bot Server       │
         │  adventure_bot.py        │
         │  --distributed-mode      │
         │  + Ollama                │
         └──────────────────────────┘
```

**Pros:** Single LLM backend shared across all channels; efficient use of resources
**Cons:** Bot server is a single point of failure; requires distributed mode setup

---

## Channel Separation Strategy

### One Bot per Channel (Recommended)

The simplest approach: each bot instance listens on exactly one channel. Players on channel 1 interact with bot 1; players on channel 2 interact with bot 2.

```bash
# Bot 1: Channel 1, fantasy theme
python3 adventure_bot.py --channel-idx 1 --theme fantasy

# Bot 2: Channel 2, sci-fi theme
python3 adventure_bot.py --channel-idx 2 --theme scifi
```

### Session Isolation

MCADV's session management is already channel-aware. The `channel_idx` field on each incoming message determines which story session is active:

- Sessions are keyed by `(channel_idx, sender)` internally
- Players on channel 1 never interfere with players on channel 2
- Each channel has its own collaborative story state

### Channel Planning

```
Channel 0 ── Reserve for general mesh chat (not MCADV)
Channel 1 ── Primary MCADV bot
Channel 2 ── Secondary MCADV bot (different theme or redundant)
Channel 3 ── Optional third bot
...
Channel 7 ── Maximum channel index
```

> **Note:** MeshCore supports channel indices 0–7 (`_MAX_VALID_CHANNEL_IDX = 7`). Plan your channel assignments before deployment.

---

## Standalone Multi-Bot Setup

### Running Two Bots Locally (Different Channels)

You can run two bot instances on **one machine** with one radio, using different channel indices. MCADV filters messages by `channel_idx`, so the two instances won't conflict as long as they listen on different channels.

**Terminal 1:**

```bash
python3 adventure_bot.py --channel-idx 1 --theme fantasy --port /dev/ttyUSB0
```

**Terminal 2:**

```bash
python3 adventure_bot.py --channel-idx 2 --theme scifi --port /dev/ttyUSB0
```

> **Caution:** Running two Python processes on the same serial port can cause read conflicts. For production, use the distributed architecture (one gateway, one bot server) instead.

### Running Bots on Separate Hardware

The cleanest setup: each bot has its own Pi and radio.

**Pi #1 (channel 1):**

```bash
python3 adventure_bot.py \
  --channel-idx 1 \
  --theme fantasy \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b \
  --announce
```

**Pi #2 (channel 2):**

```bash
python3 adventure_bot.py \
  --channel-idx 2 \
  --theme scifi \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b \
  --announce
```

Both bots can share the same Ollama server on the LAN.

---

## Shared Bot Server with Multiple Gateways

Use the distributed architecture when you want one bot server to handle multiple channels via separate radio gateways.

### Step 1: Start the Bot Server

The bot server in `--distributed-mode` handles messages from multiple gateways concurrently:

```bash
python3 adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --ollama-url http://localhost:11434 \
  --model llama3.2:1b
```

Note: do **not** specify `--channel-idx` on the bot server in this configuration — each gateway specifies its own channel, and the bot server handles sessions for all channels.

### Step 2: Start Gateway #1 (Channel 1)

On Pi Zero 2W #1:

```bash
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --port /dev/ttyUSB0 \
  --channel-idx 1
```

### Step 3: Start Gateway #2 (Channel 2)

On Pi Zero 2W #2:

```bash
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --port /dev/ttyUSB0 \
  --channel-idx 2
```

Both gateways forward messages to the same bot server, which maintains separate sessions per `channel_idx`.

### Load Balancing (Advanced)

For very high-traffic deployments, run multiple bot server instances on different ports and distribute gateways across them:

```bash
# Bot server 1: channels 1-2
python3 adventure_bot.py --distributed-mode --http-port 5000

# Bot server 2: channels 3-4
python3 adventure_bot.py --distributed-mode --http-port 5001
```

Then configure gateways to point to the appropriate server URL.

---

## Node ID Configuration

Each radio gateway should have a unique `--node-id` to identify it in logs and avoid conflicts:

```bash
# Gateway at north location
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --node-id GATEWAY_NORTH \
  --channel-idx 1

# Gateway at south location
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --node-id GATEWAY_SOUTH \
  --channel-idx 2
```

**Node ID guidelines:**
- Use uppercase letters, numbers, and underscores
- Keep it short and descriptive (max ~12 characters)
- Must be unique across all gateways on the same mesh
- Examples: `GW_NORTH`, `GW_CH1`, `GW_EAST`, `BOT1`

---

## Session Management

### How Sessions Work Across Multiple Bots

MCADV maintains sessions in `adventure_sessions.json`. Each session is uniquely identified by the player's sender ID and channel index. In a multi-bot setup:

- **Standalone bots:** Each bot maintains its own `adventure_sessions.json`
- **Shared bot server:** One `adventure_sessions.json` handles all channels

### Session Expiry

Sessions expire after **1 hour of inactivity** (`SESSION_EXPIRY_SECONDS = 3600`). After **24 hours** without any activity (`INACTIVITY_RESET_SECONDS = 86400`), the session is reset to the beginning.

These timeouts apply per player across all channels. A player who was active on channel 1 will have their session expire on both channels simultaneously (if using a shared bot server).

### Preventing Session Conflicts

When running multiple **standalone** bots (not distributed), each bot writes to its own session file. To avoid confusion if you ever merge session files, keep session files in separate working directories:

```bash
# Bot 1 sessions
WorkingDirectory=/home/pi/MCADV_ch1

# Bot 2 sessions
WorkingDirectory=/home/pi/MCADV_ch2
```

Or simply run bots from different directories with symlinked code:

```bash
mkdir -p /home/pi/bot_ch1 && cd /home/pi/bot_ch1
python3 /home/pi/MCADV/adventure_bot.py --channel-idx 1
```

---

## Systemd Service Naming

Use descriptive service names to manage multiple bots easily.

### Naming Convention

```
mcadv_bot_ch1.service  ← standalone bot, channel 1
mcadv_bot_ch2.service  ← standalone bot, channel 2
mcadv_bot_server.service ← shared bot server (distributed)
radio_gateway_ch1.service ← gateway for channel 1
radio_gateway_ch2.service ← gateway for channel 2
```

### Example: Bot Channel 1 Service

Create `/etc/systemd/system/mcadv_bot_ch1.service`:

```ini
[Unit]
Description=MCADV Adventure Bot - Channel 1 (Fantasy)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MCADV
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --channel-idx 1 \
  --theme fantasy \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b \
  --announce
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Example: Bot Channel 2 Service

Create `/etc/systemd/system/mcadv_bot_ch2.service`:

```ini
[Unit]
Description=MCADV Adventure Bot - Channel 2 (Sci-Fi)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MCADV
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --channel-idx 2 \
  --theme scifi \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b \
  --announce
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable and Start All Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcadv_bot_ch1 mcadv_bot_ch2
sudo systemctl start mcadv_bot_ch1 mcadv_bot_ch2
```

### Managing All MCADV Services at Once

```bash
# Status of all MCADV services
sudo systemctl status 'mcadv_bot_*'

# Stop all bots
sudo systemctl stop 'mcadv_bot_*'

# View logs for all bots
sudo journalctl -u 'mcadv_bot_*' -f
```

---

## Configuration File Management

### Separate Working Directories (Standalone Bots)

If running multiple standalone bots on **one machine**, use separate working directories so session files don't conflict:

```bash
# Create directories
mkdir -p /home/pi/mcadv_ch1 /home/pi/mcadv_ch2

# Update systemd service WorkingDirectory accordingly
```

### Shared Configuration (Distributed Mode)

With a shared bot server, a single `adventure_sessions.json` in the bot server's working directory handles all channels automatically.

### Backup and Restore Sessions

```bash
# Backup all session files
cp /home/pi/MCADV/adventure_sessions.json \
   /home/pi/backups/adventure_sessions_$(date +%Y%m%d).json

# Restore sessions
cp /home/pi/backups/adventure_sessions_20250101.json \
   /home/pi/MCADV/adventure_sessions.json
```

---

## Monitoring Multiple Instances

### View All Logs Together

```bash
# Follow logs for all MCADV services simultaneously
sudo journalctl -f -u mcadv_bot_ch1 -u mcadv_bot_ch2 -u radio_gateway_ch1
```

### Check All Service Statuses

```bash
for svc in mcadv_bot_ch1 mcadv_bot_ch2 radio_gateway_ch1 radio_gateway_ch2; do
  echo "--- $svc ---"
  sudo systemctl is-active $svc
done
```

### Memory Usage per Bot

```bash
# Memory for each adventure_bot process
ps aux | grep adventure_bot | awk '{print $1, $4, $11}'

# Memory for each radio_gateway process
ps aux | grep radio_gateway | awk '{print $1, $4, $11}'
```

### Simple Health Check Script

Create `/home/pi/check_bots.sh`:

```bash
#!/bin/bash
for svc in mcadv_bot_ch1 mcadv_bot_ch2; do
  status=$(systemctl is-active $svc)
  if [ "$status" != "active" ]; then
    echo "WARNING: $svc is $status"
    sudo systemctl restart $svc
  else
    echo "OK: $svc is running"
  fi
done
```

Run it via cron every 5 minutes:

```bash
*/5 * * * * /home/pi/check_bots.sh >> /home/pi/bot_health.log 2>&1
```

---

## Testing Multi-Bot Setups

### Step 1: Verify Each Bot Responds

Use the bot server health endpoint (distributed mode):

```bash
curl http://localhost:5000/health
```

Or send a test message directly:

```bash
curl -X POST http://localhost:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "tester", "content": "start", "channel_idx": 1}'

curl -X POST http://localhost:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "tester", "content": "start", "channel_idx": 2}'
```

### Step 2: Verify Channel Isolation

Send the same player name to two different channels and confirm they get different responses (different story states):

```bash
# Channel 1 - Fantasy
curl -X POST http://localhost:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "Alice", "content": "status", "channel_idx": 1}'

# Channel 2 - Sci-Fi
curl -X POST http://localhost:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "Alice", "content": "status", "channel_idx": 2}'
```

The responses should show different story contexts.

### Step 3: Test with Real LoRa Radios

Tune two phones to different channels in the MeshCore app and confirm each receives responses from the correct bot.

---

## Troubleshooting

### Bots Interfering with Each Other

**Symptom:** Messages from channel 1 being processed by the channel 2 bot.

**Cause:** Both bots are listening on the same `--channel-idx`, or no channel filter is set.

**Fix:** Ensure each bot/gateway uses a distinct `--channel-idx`:

```bash
python3 adventure_bot.py --channel-idx 1   # Bot 1
python3 adventure_bot.py --channel-idx 2   # Bot 2
```

### Two Processes on One Serial Port

**Symptom:** `SerialException: [Errno 11] Resource temporarily unavailable`

**Cause:** Two Python processes trying to read from the same `/dev/ttyUSB0`.

**Fix:** Use the distributed architecture — one gateway process owns the serial port, and multiple bot logic processes connect via HTTP:

```
radio_gateway.py (owns /dev/ttyUSB0) → HTTP → adventure_bot.py (port 5000)
```

### Bot Server Overloaded

**Symptom:** Slow responses or timeouts when multiple gateways are active.

**Fix:**
- Use a more powerful bot server (Pi 5 or Jetson instead of Pi 4)
- Use a faster/smaller LLM model
- Scale to multiple bot server instances, each handling a subset of channels

### Session File Corruption

**Symptom:** Bot crashes on startup with a JSON parse error.

**Fix:**

```bash
# Remove corrupted session file (sessions will be lost)
rm ~/MCADV/adventure_sessions.json

# Restart the bot
sudo systemctl restart mcadv_bot_ch1
```

---

## Next Steps

- Set up distributed architecture: [DISTRIBUTED_ARCHITECTURE.md](DISTRIBUTED_ARCHITECTURE.md)
- Configure LoRa radio: [LORA_CONFIGURATION.md](LORA_CONFIGURATION.md)
- Production hardening: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- Cloud LLM options: [CLOUD_LLM_SETUP.md](CLOUD_LLM_SETUP.md)

---

## Quick Links

- [Main README](../README.md)
- [Other Guides](README.md)
- [Hardware Guide](../HARDWARE.md)
- [Performance Guide](../PERFORMANCE.md)

---

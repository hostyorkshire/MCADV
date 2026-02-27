# Distributed Architecture Setup Guide

**Quick reference guide for Pi Zero 2W + LLM server configurations.**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Diagram](#architecture-diagram)
4. [Why Use Distributed Mode](#why-use-distributed-mode)
5. [Hardware Requirements](#hardware-requirements)
6. [Network Setup](#network-setup)
7. [Radio Gateway Setup (Pi Zero 2W)](#radio-gateway-setup-pi-zero-2w)
8. [Bot Server Setup (Pi 4/5 or Jetson)](#bot-server-setup-pi-45-or-jetson)
9. [Configuration Reference](#configuration-reference)
10. [Testing the Setup](#testing-the-setup)
11. [Systemd Services](#systemd-services)
12. [Troubleshooting](#troubleshooting)
13. [Performance Monitoring](#performance-monitoring)
14. [Next Steps](#next-steps)

---

## Overview

MCADV supports a **distributed architecture** that splits the system into two separate components:

| Component | Hardware | Role |
|-----------|----------|------|
| **Radio Gateway** | Pi Zero 2W | LoRa radio I/O only (~15MB RAM) |
| **Bot Server** | Pi 4/5, Jetson, Ubuntu PC | Game logic, sessions, LLM (~200MB+ RAM) |

The radio gateway forwards player messages to the bot server over HTTP, receives the generated responses, and sends them back via LoRa. This keeps the Pi Zero 2W's RAM usage extremely low while offloading all compute to a more capable device.

---

## Prerequisites

- Two devices: a Pi Zero 2W (or equivalent) and a Pi 4/5, Jetson, or Ubuntu PC
- Both devices on the same local network (WiFi or Ethernet)
- MeshCore LoRa radio connected to the Pi Zero 2W via USB
- MCADV repository cloned on **both** devices
- Python 3.7+ installed on both devices

---

## Architecture Diagram

```
[ LoRa Mesh Network ]
        │
        ▼  (radio)
┌─────────────────┐      HTTP POST/GET      ┌──────────────────────────┐
│  Pi Zero 2W     │ ─────────────────────►  │  Pi 4/5 / Jetson / PC    │
│  radio_gateway  │ ◄─────────────────────  │  adventure_bot.py        │
│  ~15MB RAM      │   http://pi5.local:5000 │  --distributed-mode      │
└─────────────────┘                         │  + Ollama / Groq / OpenAI│
                                            └──────────────────────────┘
```

**Message flow:**

1. Player sends a message via LoRa mesh radio
2. Pi Zero 2W receives the message via `radio_gateway.py`
3. Gateway forwards the message to the bot server via HTTP POST
4. Bot server processes the message, calls the LLM (or offline trees)
5. Bot server returns the response to the gateway
6. Gateway sends the response back via LoRa

---

## Why Use Distributed Mode

### Memory Efficiency

The Pi Zero 2W has only **512MB RAM**. Running a full bot with Ollama locally is impractical:

| Setup | Pi Zero 2W RAM | Bot Server RAM |
|-------|----------------|----------------|
| Standalone (all-in-one) | ~200MB | — |
| Distributed (gateway only) | ~15MB ✅ | ~200MB on Pi 5 |
| Distributed + Ollama | ~15MB ✅ | ~2GB on Pi 5 |

### Scalability

- Add more radio gateways (on different channels) without adding bot server instances
- Upgrade the bot server hardware without replacing radio gateway hardware
- Run GPU-accelerated LLMs on a Jetson while keeping the radio interface cheap

### Reliability

- Radio gateway is extremely simple — very little to fail
- Bot server can be restarted without affecting radio connectivity
- Separate logs make debugging easier

---

## Hardware Requirements

### Radio Gateway (Pi Zero 2W)

| Item | Specification |
|------|---------------|
| **Board** | Raspberry Pi Zero 2W |
| **RAM** | 512MB (built-in) — sufficient |
| **Storage** | 16GB microSD card (Class 10) |
| **Power** | 5V 2.5A micro-USB supply |
| **Radio** | MeshCore LoRa radio (USB) |
| **Network** | WiFi 2.4GHz to reach bot server |

### Bot Server (Pi 4/5 recommended)

| Item | Specification |
|------|---------------|
| **Board** | Raspberry Pi 4/5 (4GB+ RAM) |
| **RAM** | 4GB minimum, 8GB recommended |
| **Storage** | 64GB+ microSD or USB SSD |
| **Power** | Official USB-C supply (5V 5A for Pi 5) |
| **Network** | WiFi or Ethernet |

See [HARDWARE.md](../HARDWARE.md) for full hardware recommendations including Jetson and Mini PC options.

---

## Network Setup

Both devices must be able to reach each other over the local network.

### Assign Static IP Addresses

**On Pi Zero 2W (radio gateway)** — edit `/etc/dhcpcd.conf`:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the bottom:

```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

**On Pi 4/5 (bot server)** — assign a static IP the same way:

```
interface wlan0
static ip_address=192.168.1.50/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Apply changes:

```bash
sudo systemctl restart dhcpcd
```

### Hostname Resolution (Optional but Recommended)

Add bot server hostname to the gateway's hosts file:

```bash
# On Pi Zero 2W
sudo nano /etc/hosts
```

Add:

```
192.168.1.50  pi5bot  pi5bot.local
```

This lets you use `http://pi5bot:5000` as the bot server URL instead of the IP address.

### Verify Connectivity

```bash
# From Pi Zero 2W, ping the bot server
ping 192.168.1.50

# From bot server, ping the gateway
ping 192.168.1.100
```

---

## Radio Gateway Setup (Pi Zero 2W)

### Step 1: Clone MCADV

```bash
cd ~
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV
```

### Step 2: Run the Setup Script

```bash
bash scripts/setup_radio_gateway.sh
```

The script will:
- Create a Python virtual environment
- Install dependencies (`requests`, `pyserial`, `flask`)
- Auto-detect the MeshCore serial port
- Prompt for the bot server URL
- Install and enable the `radio_gateway` systemd service

### Step 3: Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create logs directory
mkdir -p logs
```

### Step 4: Test the Gateway

Run the gateway manually first to verify it works:

```bash
# Replace with your bot server URL and serial port
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --port /dev/ttyUSB0 \
  --baud 115200 \
  --channel-idx 1

# With debug output
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  -d
```

Expected output:

```
[INFO] RadioGateway: Starting radio gateway...
[INFO] RadioGateway: Bot server: http://192.168.1.50:5000
[INFO] RadioGateway: Serial port: /dev/ttyUSB0
[INFO] RadioGateway: Listening on channel_idx=1
[INFO] RadioGateway: Gateway running. Waiting for messages...
```

### Gateway Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--bot-server-url` | *required* | URL of the bot server |
| `--port` | auto-detect | Serial port for LoRa radio |
| `--baud` | `115200` | Serial baud rate |
| `--channel-idx` | `1` | LoRa channel index to listen on |
| `--node-id` | `GATEWAY` | MeshCore node identifier |
| `--timeout` | `30` | HTTP request timeout (seconds) |
| `-d` | off | Enable debug logging |

---

## Bot Server Setup (Pi 4/5 or Jetson)

### Step 1: Clone MCADV

```bash
cd ~
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV
```

### Step 2: Run the Setup Script

```bash
bash scripts/setup_bot_server.sh
```

The script installs dependencies and creates a `mcadv_bot_server` systemd service that runs the bot in `--distributed-mode`.

### Step 3: Manual Setup (Alternative)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create logs directory
mkdir -p logs
```

### Step 4: (Optional) Install Ollama

For AI-powered storytelling, install Ollama on the bot server:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b   # Small/fast model
# or
ollama pull llama3.2:3b   # Better quality
```

See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for detailed Ollama configuration.

### Step 5: Test the Bot Server

Run the bot server manually:

```bash
# Offline (no LLM) — good for initial testing
python3 adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --channel-idx 1

# With Ollama (local)
python3 adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --channel-idx 1 \
  --ollama-url http://localhost:11434 \
  --model llama3.2:1b
```

Expected output:

```
[INFO] AdventureBot: Starting in distributed mode on port 5000
[INFO] AdventureBot: LLM backend: ollama (http://localhost:11434)
[INFO] AdventureBot: Listening for HTTP requests...
```

### Bot Server Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--distributed-mode` | off | Run as HTTP server (no direct radio) |
| `--http-port` | `5000` | HTTP port for gateway connections |
| `--channel-idx` | `1` | Default channel for new sessions |
| `--ollama-url` | none | Ollama server URL |
| `--model` | `llama3.2:1b` | LLM model name |
| `--groq-key` | none | Groq API key |
| `--openai-key` | none | OpenAI API key |
| `--theme` | `fantasy` | Default adventure theme |
| `--announce` | off | Announce bot presence on startup |
| `-d` | off | Enable debug logging |

---

## Configuration Reference

### HTTP API Routes

The bot server exposes these HTTP endpoints when running in `--distributed-mode`:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/message` | Submit a player message |
| `GET` | `/health` | Health check |

**POST `/message` request body:**

```json
{
  "sender": "PlayerName",
  "content": "go north",
  "channel_idx": 1,
  "channel": "MeshCore Channel 1"
}
```

**Response:**

```json
{
  "response": "You walk north into the dark forest...",
  "sender": "PlayerName"
}
```

### Environment Variables

You can set the bot server URL in the gateway environment instead of passing it on the command line:

```bash
export BOT_SERVER_URL=http://192.168.1.50:5000
```

---

## Testing the Setup

### Step 1: Start the Bot Server

```bash
# On Pi 4/5
python3 adventure_bot.py --distributed-mode --http-port 5000 --channel-idx 1
```

### Step 2: Verify Health Endpoint

```bash
# From Pi Zero 2W (or any machine)
curl http://192.168.1.50:5000/health
# Expected: {"status": "ok"}
```

### Step 3: Test Message Forwarding

```bash
# Send a test message directly to the bot server
curl -X POST http://192.168.1.50:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "TestUser", "content": "start", "channel_idx": 1}'
```

### Step 4: Start the Radio Gateway

```bash
# On Pi Zero 2W
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --port /dev/ttyUSB0 \
  --channel-idx 1
```

### Step 5: Send a Message via LoRa

Using a MeshCore app on your phone or another node, send a message to channel 1. You should see:

- Gateway logs: `Received message from PlayerName, forwarding to bot server`
- Bot server logs: `Processing message from PlayerName on channel 1`
- LoRa response sent back to the player

---

## Systemd Services

### Bot Server Service

The setup script creates `/etc/systemd/system/mcadv_bot_server.service`:

```ini
[Unit]
Description=MCADV Bot Server (Distributed Mode)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MCADV
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --channel-idx 1
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Manage the service:

```bash
sudo systemctl start mcadv_bot_server
sudo systemctl stop mcadv_bot_server
sudo systemctl status mcadv_bot_server
sudo journalctl -u mcadv_bot_server -f
```

### Radio Gateway Service

The setup script creates `/etc/systemd/system/radio_gateway.service`:

```ini
[Unit]
Description=MCADV Radio Gateway (Distributed Mode)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MCADV
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --port /dev/ttyUSB0 \
  --baud 115200 \
  --channel-idx 1
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Manage the service:

```bash
sudo systemctl start radio_gateway
sudo systemctl stop radio_gateway
sudo systemctl status radio_gateway
sudo journalctl -u radio_gateway -f
```

### Enable Both Services on Boot

```bash
# On bot server
sudo systemctl enable mcadv_bot_server

# On Pi Zero 2W
sudo systemctl enable radio_gateway
```

---

## Troubleshooting

### Gateway Cannot Reach Bot Server

```
[ERROR] RadioGateway: Connection refused: http://192.168.1.50:5000
```

**Checks:**
1. Is the bot server running? `sudo systemctl status mcadv_bot_server`
2. Is the IP address correct? `ping 192.168.1.50`
3. Is port 5000 open? `curl http://192.168.1.50:5000/health`
4. Is there a firewall blocking the port? `sudo ufw status`

**Fix firewall (on bot server):**

```bash
sudo ufw allow 5000/tcp
```

### Serial Port Not Found

```
[ERROR] MeshCore: No serial port found
```

**Checks:**

```bash
# List serial ports
ls /dev/tty* | grep -E 'USB|ACM|AMA'

# Check USB device
lsusb

# Check if user is in dialout group
groups $USER
```

**Fix:**

```bash
# Add user to dialout group (requires logout/login)
sudo usermod -a -G dialout $USER

# Manually specify port
python3 radio_gateway.py --port /dev/ttyACM0 ...
```

### Bot Server Out of Memory

```
[ERROR] Killed (Out of memory)
```

**Fix:**
- Use a smaller Ollama model: `ollama pull llama3.2:1b`
- Increase swap: `sudo dphys-swapfile swapoff && sudo nano /etc/dphys-swapfile` (set `CONF_SWAPSIZE=2048`)

### Messages Not Being Forwarded

**Debug steps:**

```bash
# Enable debug on gateway
python3 radio_gateway.py --bot-server-url http://... --channel-idx 1 -d

# Check bot server is receiving
sudo journalctl -u mcadv_bot_server -f

# Test HTTP directly
curl -X POST http://192.168.1.50:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "test", "content": "hello", "channel_idx": 1}'
```

---

## Performance Monitoring

### Check Memory Usage

```bash
# Pi Zero 2W (gateway)
free -h
ps aux | grep radio_gateway

# Bot server
free -h
ps aux | grep adventure_bot
```

### Monitor Logs in Real-Time

```bash
# Gateway logs
sudo journalctl -u radio_gateway -f

# Bot server logs
sudo journalctl -u mcadv_bot_server -f
tail -f ~/MCADV/logs/meshcore.log
```

### Check CPU Usage

```bash
top -p $(pgrep -f radio_gateway)
top -p $(pgrep -f adventure_bot)
```

### Network Latency

```bash
# Measure round-trip time from gateway to bot server
time curl http://192.168.1.50:5000/health
```

Typical performance figures:

| Metric | Expected |
|--------|----------|
| Gateway RAM | ~15MB |
| Bot server RAM (offline) | ~30MB |
| Bot server RAM (+ Ollama) | ~2GB |
| HTTP round-trip (LAN) | <5ms |
| Offline response time | <50ms |
| Ollama response time | 500ms–5s |

---

## Next Steps

- Configure Ollama on the bot server: [OLLAMA_SETUP.md](OLLAMA_SETUP.md)
- Run multiple gateways: [MULTI_BOT_DEPLOYMENTS.md](MULTI_BOT_DEPLOYMENTS.md)
- Production hardening: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- Hardware selection: [HARDWARE.md](../HARDWARE.md)

---

## Quick Links

- [Main README](../README.md)
- [Other Guides](README.md)
- [Hardware Guide](../HARDWARE.md)
- [Performance Guide](../PERFORMANCE.md)

---

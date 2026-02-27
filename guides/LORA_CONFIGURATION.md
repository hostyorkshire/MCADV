# LoRa Radio Configuration Guide

**Quick reference guide for optimizing MeshCore radio settings for better performance.**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [MeshCore Protocol Overview](#meshcore-protocol-overview)
4. [Serial Port Configuration](#serial-port-configuration)
5. [Channel Configuration](#channel-configuration)
6. [Message Size Limits](#message-size-limits)
7. [Radio Performance Tuning](#radio-performance-tuning)
8. [Antenna Considerations](#antenna-considerations)
9. [Range Optimization](#range-optimization)
10. [Testing Radio Connectivity](#testing-radio-connectivity)
11. [Debugging Serial Communication](#debugging-serial-communication)
12. [Common Error Messages](#common-error-messages)
13. [Next Steps](#next-steps)

---

## Overview

MCADV communicates with players via a **MeshCore LoRa radio** connected over USB serial. This guide explains how to configure and optimize the radio link for reliable message delivery.

The radio layer is handled by `meshcore.py`, which implements the MeshCore companion radio binary protocol. MCADV sends and receives plain-text messages; the MeshCore firmware on the radio handles all LoRa parameters (spreading factor, bandwidth, coding rate) internally.

---

## Prerequisites

- A MeshCore-compatible LoRa radio (e.g., T-Beam, LILYGO T3-S3)
- MeshCore firmware flashed on the radio
- MCADV installed and its Python virtual environment activated
- USB cable connecting the radio to your Pi or PC

---

## MeshCore Protocol Overview

MCADV uses the **MeshCore Companion Radio Binary Protocol** over USB serial. The protocol uses two special start bytes:

| Constant | Value | Direction | Description |
|----------|-------|-----------|-------------|
| `_FRAME_OUT` | `0x3E` (`>`) | Radio → App | Outbound frame (radio sends to MCADV) |
| `_FRAME_IN` | `0x3C` (`<`) | App → Radio | Inbound frame (MCADV sends to radio) |

### Key Protocol Commands

| Command | Code | Description |
|---------|------|-------------|
| `_CMD_APP_START` | `1` | Initialize companion radio session |
| `_CMD_SYNC_NEXT_MSG` | `10` | Fetch next queued message |
| `_CMD_SEND_CHAN_MSG` | `3` | Send a channel (flood) text message |
| `_CMD_GET_DEVICE_TIME` | `5` | Request current device time |

### Key Protocol Responses

| Response | Code | Description |
|----------|------|-------------|
| `_PUSH_MSG_WAITING` | `0x83` | A new message is queued |
| `_PUSH_CHAN_MSG` | `0x88` | Inline channel message delivery |
| `_RESP_CHANNEL_MSG` | `8` | Channel message received |
| `_RESP_CHANNEL_MSG_V3` | `17` | V3 channel message (includes SNR) |
| `_RESP_NO_MORE_MSGS` | `10` | Message queue is empty |

### V3 Protocol Format

Newer MeshCore firmware versions use the V3 message format, which includes **SNR (Signal-to-Noise Ratio)** data. MCADV detects V3 messages automatically.

| Format | Header Size | Extra Info |
|--------|-------------|------------|
| Old format | 8 bytes | No SNR |
| V3 format | 11 bytes | Includes SNR (dB) |

The maximum valid frame payload size is **300 bytes** (`_MAX_FRAME_SIZE`).

---

## Serial Port Configuration

### Auto-Detection

MCADV automatically scans for MeshCore radios on startup. The scan order is:

```
/dev/ttyUSB0 → /dev/ttyUSB1 → /dev/ttyACM0 → /dev/ttyAMA0
```

To see detected ports:

```bash
# List all serial-like devices
ls /dev/tty* | grep -E 'USB|ACM|AMA'

# See what USB devices are connected
lsusb

# Check which port your radio is on
dmesg | tail -20 | grep tty
```

### Manual Port Selection

Override auto-detection with `--port`:

```bash
python3 adventure_bot.py --port /dev/ttyUSB0 --baud 115200 --channel-idx 1
python3 radio_gateway.py --port /dev/ttyACM0 --baud 115200 ...
```

### Baud Rate

MCADV defaults to **115200 baud**, which is the standard rate for MeshCore companion radios.

```bash
# Standard (default)
python3 adventure_bot.py --baud 115200 --channel-idx 1

# If your radio requires a different rate
python3 adventure_bot.py --baud 9600 --channel-idx 1
```

**Common baud rates for MeshCore:**

| Baud Rate | Usage |
|-----------|-------|
| `115200` | Standard — use this in almost all cases |
| `9600` | Legacy or non-standard firmware |

### User Permissions for Serial Port

By default, `/dev/ttyUSB*` and `/dev/ttyACM*` are owned by the `dialout` group. Add your user:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for the change to take effect
```

Verify:

```bash
groups $USER
# Should include: dialout
```

### Port Stability with udev Rules

USB serial ports can change device names after a reboot if multiple USB devices are present. Create a persistent udev rule to fix the device name:

```bash
# Find the vendor/product ID of your radio
udevadm info -a -n /dev/ttyUSB0 | grep -E 'idVendor|idProduct'
```

Create `/etc/udev/rules.d/99-meshcore.rules`:

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="meshcore"
```

Replace `idVendor` and `idProduct` with your radio's values. After creating the rule:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
# Your radio will now appear as /dev/meshcore
```

Use `/dev/meshcore` as your `--port` value for stable addressing.

---

## Channel Configuration

### Channel Index

MeshCore supports multiple channels (0–7). MCADV uses the **channel index** to filter messages:

```bash
# Listen on channel 1 (recommended default)
python3 adventure_bot.py --channel-idx 1

# Listen on channel 0
python3 adventure_bot.py --channel-idx 0
```

**Channel index range:** `0` to `7` (`_MAX_VALID_CHANNEL_IDX = 7`)

### How Channels Work

Each MeshCore channel is a separate **LoRa broadcast domain**. All nodes tuned to the same channel and frequency can hear each other. MCADV filters incoming messages by `channel_idx` so multiple bots can run on the same mesh without interfering.

```
Channel 0 ─── General chat (not MCADV)
Channel 1 ─── MCADV adventure bot ← default
Channel 2 ─── Second MCADV instance (different theme)
...
```

### Multi-Channel Support

The `allowed_channel_idx` parameter in the radio gateway restricts which channel is forwarded to the bot server:

```bash
# Gateway forwards only channel 1 messages
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000 \
  --channel-idx 1

# Gateway forwards all channels (None = no filter)
python3 radio_gateway.py \
  --bot-server-url http://192.168.1.50:5000
```

### Channel Index Constants

The channel index values are validated against these bounds defined in `meshcore.py`:

```python
# From meshcore.py
_MAX_VALID_CHANNEL_IDX = 7   # Channels 0-7 are valid
_MIN_REALISTIC_SNR = 20      # Minimum expected SNR in dB
_MAX_REALISTIC_SNR = 60      # Maximum expected SNR in dB
```

---

## Message Size Limits

### The 230-Byte Limit

MeshCore channel messages are limited to **230 bytes** of text content (`MAX_MSG_LEN = 230` in `adventure_bot.py`). MCADV automatically truncates responses to fit within this limit.

```python
MAX_MSG_LEN = 230  # bytes — maximum outgoing message length
```

> **Why 230 bytes?** LoRa payloads are typically limited to 255 bytes. MeshCore uses some bytes for protocol overhead (header fields), leaving approximately 230 bytes for text content.

### Message Splitting

Long LLM responses are split into multiple messages. The bot server handles splitting automatically, sending each chunk as a separate LoRa transmission.

### Optimizing Response Length

If responses are being cut off, configure the LLM to generate shorter outputs. For Ollama:

```bash
python3 adventure_bot.py \
  --ollama-url http://localhost:11434 \
  --model llama3.2:1b \
  --channel-idx 1
```

The system prompt instructs the LLM to keep responses short and suitable for mesh radio. If you customize the prompt, keep responses under ~200 characters to avoid splitting.

---

## Radio Performance Tuning

### Signal-to-Noise Ratio (SNR)

MCADV logs the SNR for each received message (V3 protocol only). Higher SNR = better signal quality.

| SNR Range | Signal Quality | Typical Scenario |
|-----------|----------------|------------------|
| 50–60 dB | Excellent | Same room, line of sight |
| 35–50 dB | Good | Indoor, <100m |
| 20–35 dB | Fair | Urban, 100m–1km |
| <20 dB | Poor | Edge of range, obstructions |

Check SNR in debug mode:

```bash
python3 adventure_bot.py --channel-idx 1 -d
# Look for: [DEBUG] SNR: 42dB
```

### Serial Read Interval

MCADV polls the radio for new messages in a tight loop. On a Pi Zero 2W, this is CPU-efficient because the loop sleeps between polls. No tuning is required for typical deployments.

### Connection Recovery

If the serial connection drops (e.g., radio unplugged), MCADV will log an error and attempt to reconnect automatically. The service will restart via systemd's `Restart=on-failure` if reconnection fails.

---

## Antenna Considerations

The antenna quality has the biggest impact on range. General guidelines:

### Antenna Types

| Antenna Type | Gain | Best For |
|--------------|------|----------|
| Stock whip (included) | 0–2 dBi | Indoor, short range |
| Upgraded 5dBi fiberglass | 5 dBi | Outdoor, up to 2km |
| Directional Yagi | 10–14 dBi | Long range, point-to-point |

### Placement Tips

- Mount the antenna **vertically** (polarization should match the mesh nodes)
- Keep the antenna **away from metal surfaces** — 15cm minimum
- For outdoor deployment, use a **weatherproof enclosure** with the antenna protruding outside
- Higher is better — rooftop or elevated mounting significantly increases range

### Frequency Band

Most MeshCore radios operate on **868 MHz** (EU) or **915 MHz** (US/AU). Ensure your antenna is rated for the correct band. Using an 868MHz antenna at 915MHz (or vice versa) will reduce effective range.

---

## Range Optimization

### Line of Sight

LoRa signals work best with **line of sight** between nodes. Common obstacles and their impact:

| Obstacle | Range Impact |
|----------|-------------|
| Open field | Maximum range (2–10km) |
| Suburban residential | 500m–2km |
| Urban dense | 100m–500m |
| Inside buildings | 50m–200m |
| Concrete/steel walls | 50m–100m |

### LoRa Spreading Factor

MeshCore firmware manages the spreading factor (SF) configuration. Higher SF = longer range but slower data rate. The default MeshCore configuration is typically:

- SF9 or SF10 for balanced range/speed
- Bandwidth: 125 kHz
- Coding Rate: 4/5

These are set in the MeshCore firmware, not in MCADV. Refer to the MeshCore documentation for firmware-level configuration.

### Relay Nodes

For deployments spanning large areas, place intermediate **relay nodes** (standard MeshCore nodes, no MCADV) to extend coverage. The mesh automatically routes messages through relays.

---

## Testing Radio Connectivity

### Step 1: Verify Serial Connection

```bash
# Check the port is accessible
python3 -c "
import serial
s = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print('Port opened successfully')
s.close()
"
```

### Step 2: Run MCADV in Debug Mode

```bash
python3 adventure_bot.py --channel-idx 1 -d
```

Look for these startup lines:

```
[INFO] MeshCore: Connecting to /dev/ttyUSB0 at 115200 baud...
[INFO] MeshCore: Connected successfully
[INFO] MeshCore: Companion radio session initialized
```

### Step 3: Send a Test Message

Using the MeshCore app on your phone (or another node), send a message to the channel MCADV is listening on. In debug mode you should see:

```
[DEBUG] MeshCore: Frame received, type=0x88
[DEBUG] MeshCore: Channel message from PlayerName on channel_idx=1
[INFO] AdventureBot: Processing message from PlayerName: "hello"
```

### Step 4: Check Message Delivery

Confirm the response was sent back:

```
[INFO] MeshCore: Sending channel message (47 bytes) to channel_idx=1
[INFO] MeshCore: Message sent successfully
```

### Loopback Test

If you have two MeshCore radios, connect one to the Pi running MCADV and use the other (via phone app) to send and receive messages. This tests the full send/receive cycle.

---

## Debugging Serial Communication

### Enable Debug Logging

```bash
python3 adventure_bot.py --channel-idx 1 -d 2>&1 | tee /tmp/mcadv_debug.log
```

### Check for Serial Errors

Common serial errors logged by `meshcore.py`:

```
[ERROR] MeshCore: SerialException: [Errno 13] Permission denied: '/dev/ttyUSB0'
→ Fix: sudo usermod -a -G dialout $USER (then log out/in)

[ERROR] MeshCore: SerialException: [Errno 2] No such file or directory: '/dev/ttyUSB0'
→ Fix: Check cable connection, run: ls /dev/tty*

[ERROR] MeshCore: Frame size 350 exceeds maximum 300
→ Indicates corrupted data; check baud rate matches radio firmware
```

### Monitor Raw Serial Data

```bash
# Watch raw bytes from the radio (press Ctrl+C to stop)
sudo cat /dev/ttyUSB0 | xxd | head -50
```

### Check System Logs for USB Issues

```bash
dmesg | grep -i 'usb\|tty' | tail -30
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `No serial port found` | Radio not connected or wrong port | Check USB cable, try `--port /dev/ttyACM0` |
| `Permission denied: /dev/ttyUSB0` | User not in dialout group | `sudo usermod -a -G dialout $USER` |
| `Frame size N exceeds maximum 300` | Baud rate mismatch or corrupted data | Verify `--baud 115200` matches firmware |
| `Connection refused (bot server)` | Bot server not running | `sudo systemctl start mcadv_bot_server` |
| `Serial port opened but no data received` | Wrong port selected | Run `dmesg | grep tty` to find correct port |
| `OSError: [Errno 6] No such device` | Radio disconnected during operation | Reconnect USB, restart service |

---

## Next Steps

- Set up distributed architecture: [DISTRIBUTED_ARCHITECTURE.md](DISTRIBUTED_ARCHITECTURE.md)
- Deploy multiple bots: [MULTI_BOT_DEPLOYMENTS.md](MULTI_BOT_DEPLOYMENTS.md)
- Production hardening: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- Hardware selection: [HARDWARE.md](../HARDWARE.md)

---

## Quick Links

- [Main README](../README.md)
- [Other Guides](README.md)
- [Hardware Guide](../HARDWARE.md)
- [Performance Guide](../PERFORMANCE.md)

---

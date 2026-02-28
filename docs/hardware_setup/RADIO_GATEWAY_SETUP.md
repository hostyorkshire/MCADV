# Radio Gateway Setup Guide

The **Radio Gateway** is the LoRa mesh interface for MCADV. It runs on a Raspberry Pi Zero 2W, listens for messages from MeshCore LoRa radios, and forwards them to the Bot Server over HTTP.

## Hardware Requirements

| Component | Details |
|-----------|---------|
| **Raspberry Pi Zero 2W** | Required – matched to low power LoRa workload |
| **LoRa Radio** | MeshCore-compatible (e.g., T-Beam, T-Echo) |
| **USB OTG cable** | micro-USB to USB-A adapter for radio |
| **microSD card** | 16 GB minimum (Class 10 / A1) |
| **Power supply** | 5 V 2.5 A micro-USB |

## Power Specifications

| Component | Power Draw |
|-----------|------------|
| Pi Zero 2W (idle) | ~0.4 W |
| Pi Zero 2W (load) | ~1.5 W |
| LoRa radio (idle) | ~0.1 W |
| LoRa radio (TX) | ~0.5–1 W |
| **Total (typical)** | **~1–2.5 W** |

## Setup Steps

### 1. Install Raspberry Pi OS Lite

- Flash **Raspberry Pi OS Lite (64-bit)** using Raspberry Pi Imager
- Enable SSH: add empty `ssh` file to boot partition, or use Imager's settings
- Set hostname (e.g., `mcadv-gateway`) and Wi-Fi credentials in Imager

### 2. First Boot

```bash
# SSH into the Pi Zero 2W
ssh pi@mcadv-gateway.local

# Update packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip
```

### 3. Clone Repository

```bash
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV
```

### 4. Run Interactive Setup

```bash
./full_setup.sh
# Select: Radio Gateway (option 2)
```

### 5. Connect LoRa Radio

```bash
# Connect radio via USB OTG, then verify detection
ls /dev/ttyUSB* /dev/ttyACM*

# Add user to dialout group for serial access
sudo usermod -aG dialout $USER
# Log out and back in, or: newgrp dialout
```

### 6. Configure Bot Server URL

Set the Bot Server URL before starting the gateway:

```bash
# In .env or environment
export BOT_SERVER_URL=http://pi5.local:5000
# or for IP address:
export BOT_SERVER_URL=http://192.168.1.100:5000
```

### 7. Verify Setup

```bash
./scripts/pre_deployment_check.sh
./scripts/testing/test_radio_gateway.sh --bot-server pi5.local
```

### 8. Start the Gateway

```bash
./run_radio_gateway.sh
```

## Configuration

Key settings in `config.yaml`:

```yaml
radio:
  port: "/dev/ttyUSB0"   # LoRa serial port
  baud: 115200

# Bot server connection
bot_server_url: "http://pi5.local:5000"
```

## Serial Permissions

If you see `Permission denied` when accessing `/dev/ttyUSB0`:

```bash
sudo usermod -aG dialout $USER
# Then log out and back in
```

## Network Configuration

For reliable operation, assign a static IP or use a predictable hostname:

```bash
# /etc/dhcpcd.conf – static IP example
interface wlan0
static ip_address=192.168.1.101/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

## Monitoring

```bash
# Check radio and network status
./scripts/testing/test_radio_gateway.sh

# Power and temperature
./scripts/monitoring/monitor_power_temp.sh --once

# Network connectivity to bot server
./scripts/testing/test_network_connectivity.sh --bot-server pi5.local
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No serial device | Check USB OTG cable; try `dmesg \| tail` after plugging in |
| Permission denied | Add user to `dialout` group; log out and back in |
| Cannot reach bot server | Verify bot server URL and Wi-Fi connectivity |
| High memory usage | Restart gateway; check for log file growth |

See [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for more.

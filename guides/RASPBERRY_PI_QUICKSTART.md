# Raspberry Pi Quick Start Guide for MCADV

This comprehensive guide will walk you through setting up Raspberry Pi 5, Pi Zero 2, and Ubuntu Desktop from scratch, including downloading the OS, configuring it, and running MCADV with Ollama locally using the recommended models.

---

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Ubuntu Desktop Setup (Development)](#ubuntu-desktop-setup-development)
3. [Download Raspberry Pi OS](#download-raspberry-pi-os)
4. [Flash OS to SD Card](#flash-os-to-sd-card)
5. [Initial Pi Configuration](#initial-pi-configuration)
6. [Pi 5 Setup (Bot Server with Ollama)](#pi-5-setup-bot-server-with-ollama)
7. [Pi Zero 2 Setup (Lightweight Bot)](#pi-zero-2-setup-lightweight-bot)
8. [Installing Ollama](#installing-ollama)
9. [Downloading Recommended Models](#downloading-recommended-models)
10. [Installing MCADV](#installing-mcadv)
11. [Testing Your Setup](#testing-your-setup)
12. [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

### For Ubuntu Desktop (Development/Testing) ⭐ RECOMMENDED FOR DEVELOPMENT

**Required:**
- Desktop or laptop running Ubuntu 20.04 LTS or newer (64-bit)
- 8GB RAM minimum (16GB+ recommended)
- 20GB free disk space (50GB+ recommended for multiple models)
- USB port for LoRa radio
- Internet connection

**Why Ubuntu Desktop for Development?**
- ✅ **Zero cost** - Use your existing computer
- ✅ **Fast iteration** - More powerful than Pi
- ✅ **Easy debugging** - Full IDE and debugging tools available
- ✅ **Same OS family** - Ubuntu/Debian-based like Raspberry Pi OS
- ✅ **Test before deploying** - Verify everything works before buying Pi hardware
- ✅ **Portable code** - Same Python code runs on Pi later

**Note:** Ubuntu Desktop acts as a Pi 5 simulator for development. Once your code works on Ubuntu, it will work on Pi 5 with minimal or no changes.

### For Raspberry Pi 5 (Recommended Bot Server)

**Required:**
- Raspberry Pi 5 (8GB RAM recommended, 4GB minimum)
- 32GB microSD card (Class 10 or UHS-1) - for OS
- USB-C power supply (5V 5A/27W official recommended)
- USB SSD (256GB+ recommended) - for Ollama model storage
- MicroHDMI to HDMI cable (for initial setup)
- USB keyboard and mouse (for initial setup)
- LoRa MeshCore radio with USB connection

**Optional:**
- Active cooling fan (recommended for sustained workloads)
- Case with ventilation
- Ethernet cable (more reliable than WiFi)

### For Raspberry Pi Zero 2 W (Lightweight Bot)

**Required:**
- Raspberry Pi Zero 2 W
- 32GB microSD card (Class 10 or UHS-1)
- 5V 2.5A micro-USB power supply
- Mini-HDMI to HDMI adapter (for initial setup)
- USB OTG adapter (for keyboard/mouse during setup)
- USB keyboard and mouse (for initial setup)
- LoRa MeshCore radio with USB connection

**Optional:**
- Case
- USB Ethernet adapter (for more stable networking)

### For Both Pi Models

- Monitor/TV with HDMI input (for initial setup)
- Computer for flashing SD card
- Stable WiFi network or Ethernet connection

---

## Ubuntu Desktop Setup (Development)

**⭐ Start here if you want to develop/test before deploying to Raspberry Pi hardware.**

This section covers setting up Ubuntu Desktop as a development environment. Your Ubuntu machine will act as a Pi 5 simulator, running both MCADV and Ollama locally. This is the fastest way to get started and test everything before investing in Pi hardware.

### Prerequisites

- Ubuntu 20.04 LTS or newer (64-bit)
- 8GB+ RAM (16GB recommended)
- LoRa MeshCore radio connected via USB

### Step 1: Update System

```bash
# Update package lists
sudo apt update

# Upgrade packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y git curl wget build-essential
```

### Step 2: Install Python and Dependencies

```bash
# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv python3-serial

# Verify versions
python3 --version    # Should be 3.8 or newer
pip3 --version

# Install useful development tools
sudo apt install -y htop net-tools
```

### Step 3: Install Ollama

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Check service status
systemctl status ollama

# Ollama should be running on http://localhost:11434
```

### Step 4: Download Recommended Models

```bash
# Start with the recommended model for CYOA
ollama pull llama3.2:1b    # 1.3GB, fast, good quality

# Optional: Pull additional models for comparison
# ollama pull llama3.2:3b    # 3.2GB, better quality, slower
# ollama pull llama3.1:8b    # 4.9GB, best quality (if you have powerful hardware)
```

### Step 5: Test Ollama

```bash
# Test the model
ollama run llama3.2:1b "Write a short fantasy story in 2 sentences."

# Press Ctrl+D to exit

# Test API endpoint
curl http://localhost:11434/api/version
# Should return: {"version":"0.x.x"}
```

### Step 6: Clone and Install MCADV

```bash
# Navigate to your projects directory
cd ~

# Clone MCADV repository
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 7: Connect LoRa Radio

**Physical connection:**

1. Connect your LoRa MeshCore radio to a USB port
2. Wait for the device to be recognized

**Identify the device:**

```bash
# List USB serial devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Typically: /dev/ttyUSB0 or /dev/ttyACM0
# Note down the device path

# Check permissions
ls -l /dev/ttyUSB0

# Add your user to dialout group (if needed)
sudo usermod -a -G dialout $USER

# Log out and log back in for group change to take effect
# Or use: newgrp dialout
```

### Step 8: Test MCADV

```bash
cd ~/MCADV
source venv/bin/activate

# Test with Ollama (adjust device path if needed)
# Note: --channel-idx 1 = #adventure hashtag channel
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --model llama3.2:1b \
  --debug

# You should see:
# "Initializing bot..."
# "Ollama available at http://localhost:11434"
# "Model 'llama3.2:1b' is ready"
# "Bot started successfully"
# "Listening on channel 1 (#adventure)..."

# Press Ctrl+C to stop
```

**Important:** The bot only responds on the **#adventure** MeshCore hashtag channel (channel index 1). All players must be on this channel to interact with the bot.

### Step 9: Test on LoRa Network

From another device with LoRa MeshCore radio configured to the **#adventure** channel:

1. **Ensure you're on the #adventure channel** (channel index 1)
2. Send `!adv` to start an adventure
3. Bot should respond with a story scene and choices
4. Reply with `1`, `2`, or `3` to make a choice
5. Continue the adventure!

### Step 10: Development Workflow

**Your Ubuntu development setup is complete! Here's your workflow:**

1. **Develop on Ubuntu:**
   ```bash
   cd ~/MCADV
   source venv/bin/activate
   # Edit code, test changes
   python3 adventure_bot.py --port /dev/ttyUSB0 --debug
   ```

2. **Test different models:**
   ```bash
   ollama pull llama3.2:3b
   python3 adventure_bot.py --port /dev/ttyUSB0 --model llama3.2:3b
   ```

3. **Monitor performance:**
   ```bash
   htop                              # System resources
   journalctl -u ollama -f          # Ollama logs
   tail -f logs/adventure_bot.log   # Bot logs
   ```

4. **When ready, deploy to Pi:**
   - Same code works on Pi with no changes
   - Same Ollama commands
   - Same model files

### Optional: Create Systemd Service on Ubuntu

If you want the bot to auto-start on Ubuntu:

```bash
# Create service file
sudo nano /etc/systemd/system/adventure_bot.service
```

Add this content (adjust paths for your username):

```ini
[Unit]
Description=MCADV Adventure Bot
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/MCADV
Environment="OLLAMA_URL=http://localhost:11434"
Environment="OLLAMA_MODEL=llama3.2:1b"
# --channel-idx 1 = #adventure hashtag channel (REQUIRED)
ExecStart=/home/YOUR_USERNAME/MCADV/venv/bin/python3 /home/YOUR_USERNAME/MCADV/adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable adventure_bot
sudo systemctl start adventure_bot
sudo systemctl status adventure_bot
```

### Ubuntu Desktop: Summary

✅ **You now have a full development environment on Ubuntu!**

**What you can do:**
- Develop and test code faster than on Pi
- Test with multiple models easily
- Debug with full IDE support (VSCode, PyCharm, etc.)
- Simulate Pi 5 behavior exactly
- Deploy to Pi when ready with minimal changes

**Next steps:**
- Experiment with different models and settings
- Test your adventures thoroughly
- When satisfied, deploy to actual Pi hardware (skip to [Download Raspberry Pi OS](#download-raspberry-pi-os))

---

## Download Raspberry Pi OS

**Note:** If you're using Ubuntu Desktop for development only, you can skip this section and the Pi-specific sections below.

We'll use **Raspberry Pi OS Lite (64-bit)** - a minimal installation without desktop environment, perfect for headless operation.

### Step 1: Download Raspberry Pi Imager

**On Windows/Mac/Linux:**

1. Go to https://www.raspberrypi.com/software/
2. Download **Raspberry Pi Imager** for your operating system
3. Install and launch the application

### Step 2: Select the OS

**In Raspberry Pi Imager:**

1. Click "CHOOSE OS"
2. Select "Raspberry Pi OS (other)"
3. Select "**Raspberry Pi OS Lite (64-bit)**"
   - This is the headless, 64-bit version without desktop
   - Size: ~500MB download
   - Based on Debian Bookworm

**Why 64-bit Lite?**
- ✅ Required for Ollama (only works on 64-bit ARM)
- ✅ Smaller footprint = faster boot, less memory usage
- ✅ No desktop GUI = more resources for bot and LLM
- ✅ Same OS works on both Pi 5 and Pi Zero 2

---

## Flash OS to SD Card

### Step 1: Insert SD Card

1. Insert your microSD card into your computer (use an SD card adapter if needed)
2. Note: All data on the card will be erased

### Step 2: Configure Settings (IMPORTANT)

Before flashing, configure advanced settings:

1. In Raspberry Pi Imager, click "CHOOSE STORAGE"
2. Select your SD card
3. Click the **⚙️ Settings** icon (bottom right)
4. Configure the following:

**General Settings:**
- ✅ **Set hostname:** 
  - For Pi 5: `pi5` or `mcadv-server`
  - For Pi Zero 2: `pizero` or `mcadv-bot`
- ✅ **Enable SSH:**
  - Select "Use password authentication"
- ✅ **Set username and password:**
  - Username: `pi` (or your choice)
  - Password: Choose a secure password
- ✅ **Configure wireless LAN:**
  - SSID: Your WiFi network name
  - Password: Your WiFi password
  - Wireless LAN country: Your country code (e.g., US, GB, CA)
- ✅ **Set locale settings:**
  - Time zone: Your timezone
  - Keyboard layout: Your keyboard layout

**Services:**
- ✅ **Enable SSH** (critical for headless setup)

5. Click "SAVE"

### Step 3: Flash the SD Card

1. Click "WRITE"
2. Confirm you want to erase the SD card
3. Wait for the process to complete (5-10 minutes)
4. When done, safely eject the SD card

**Repeat for second Pi:**
- Flash a second SD card for your second Pi (if you have both Pi 5 and Pi Zero 2)
- Use different hostnames (e.g., `pi5` and `pizero`)

---

## Initial Pi Configuration

### Step 1: First Boot

**For both Pi 5 and Pi Zero 2:**

1. Insert the flashed microSD card into your Pi
2. Connect power supply
3. Wait 1-2 minutes for first boot (green LED will blink)

**Optional: Connect Monitor (First Time)**
- If you want to see the boot process, connect monitor and keyboard
- You'll see boot messages and eventually a login prompt
- Login with username `pi` and the password you set

### Step 2: Find Your Pi on the Network

**From your computer:**

```bash
# Option 1: Use hostname (if mDNS/Avahi works)
ping pi5.local        # For Pi 5
ping pizero.local     # For Pi Zero 2

# Option 2: Scan your network for Raspberry Pi devices
# On Linux/Mac:
arp -a | grep -i "b8:27:eb\|dc:a6:32\|e4:5f:01"

# On Windows (PowerShell):
arp -a | findstr "b8-27-eb dc-a6-32 e4-5f-01"

# Option 3: Check your router's DHCP client list
# Login to your router and look for devices named "pi5" or "pizero"
```

Note down the IP address (e.g., `192.168.1.50`)

### Step 3: Connect via SSH

**From your computer:**

```bash
# Using hostname (recommended)
ssh pi@pi5.local        # For Pi 5
ssh pi@pizero.local     # For Pi Zero 2

# Or using IP address
ssh pi@192.168.1.50

# First time: Accept the SSH fingerprint by typing "yes"
```

**If SSH fails:**
- Verify Pi is powered on and connected to network
- Check WiFi credentials are correct
- Try connecting Pi directly to router with Ethernet cable
- Connect monitor and keyboard to troubleshoot

### Step 4: Update System

**On your Pi (via SSH):**

```bash
# Update package lists
sudo apt update

# Upgrade all packages (this may take 10-30 minutes on first boot)
sudo apt upgrade -y

# Install essential tools
sudo apt install -y git curl wget nano htop

# Reboot to apply any kernel updates
sudo reboot
```

Wait 1-2 minutes, then reconnect via SSH.

### Step 5: Configure System Settings

**On your Pi (via SSH):**

```bash
# Run Raspberry Pi configuration tool
sudo raspi-config
```

**Important settings to configure:**

1. **System Options → Boot/Auto Login**
   - Select: "Console" (no auto-login)

2. **Interface Options → SSH**
   - Ensure SSH is enabled

3. **Interface Options → Serial Port** (if using LoRa)
   - "Would you like a login shell accessible over serial?" → **No**
   - "Would you like the serial port hardware enabled?" → **Yes**

4. **Performance Options → GPU Memory** (Pi 5 only)
   - Set to minimum: **16 MB** (we don't need GPU for headless)

5. **Localisation Options**
   - Verify timezone, locale, keyboard are correct

6. **Advanced Options → Expand Filesystem**
   - Ensure full SD card space is available

7. Select "Finish" and reboot when prompted

```bash
# After reboot, verify settings
df -h        # Check SD card is fully expanded
free -h      # Check available RAM
uname -a     # Verify 64-bit kernel (should show "aarch64")
```

### Step 6: Configure Static IP (Optional but Recommended)

**On your Pi (via SSH):**

For more reliable networking, set a static IP:

```bash
# Edit dhcpcd configuration
sudo nano /etc/dhcpcd.conf
```

Add at the end (adjust to your network):

```bash
# Static IP configuration
interface wlan0
static ip_address=192.168.1.50/24    # For Pi 5, or .51 for Pi Zero 2
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8

# If using Ethernet instead:
# interface eth0
# static ip_address=192.168.1.50/24
# static routers=192.168.1.1
# static domain_name_servers=192.168.1.1 8.8.8.8
```

Save and exit (Ctrl+X, Y, Enter), then reboot:

```bash
sudo reboot
```

Reconnect using the new static IP:

```bash
ssh pi@192.168.1.50
```

---

## Pi 5 Setup (Bot Server with Ollama)

This setup is for running MCADV with Ollama on Raspberry Pi 5.

### Step 1: Setup USB SSD (Recommended)

**Why use an SSD?**
- LLM models load 3-10x faster than microSD
- Better reliability for continuous writes
- More capacity for multiple models
- Extends microSD card lifespan

**Connect USB SSD:**

1. Connect your USB SSD to one of the Pi 5's USB 3.0 ports (blue ports)

2. Identify the drive:

```bash
# List all storage devices
lsblk

# You should see something like:
# sda           8:0    0  238G  0 disk    ← Your SSD
```

### Step 2: Format and Mount SSD

**⚠️ Warning: This will erase all data on the SSD!**

```bash
# Partition the drive (if needed)
sudo fdisk /dev/sda

# Press 'n' for new partition, then Enter several times to accept defaults
# Press 'w' to write changes and exit

# Format as ext4
sudo mkfs.ext4 /dev/sda1

# Create mount point
sudo mkdir -p /mnt/ssd

# Mount the SSD
sudo mount /dev/sda1 /mnt/ssd

# Verify it's mounted
df -h | grep ssd
# Should show: /dev/sda1  238G  ... /mnt/ssd
```

### Step 3: Configure Auto-Mount on Boot

```bash
# Get UUID of the partition
sudo blkid /dev/sda1

# Copy the UUID (the part in quotes after UUID=)
# Example: UUID="a1b2c3d4-e5f6-..."

# Edit fstab
sudo nano /etc/fstab

# Add this line at the end (replace UUID with yours):
UUID=a1b2c3d4-e5f6-... /mnt/ssd ext4 defaults,nofail 0 2

# Save and exit (Ctrl+X, Y, Enter)

# Test the mount
sudo umount /mnt/ssd
sudo mount -a
df -h | grep ssd    # Verify it mounted correctly
```

### Step 4: Set Permissions

```bash
# Give your user ownership of the SSD
sudo chown -R pi:pi /mnt/ssd

# Create directory for Ollama models
mkdir -p /mnt/ssd/ollama

# Verify
ls -la /mnt/ssd
```

### Step 5: Install Python and Dependencies

```bash
# Install Python and essential packages
sudo apt install -y python3 python3-pip python3-venv python3-serial

# Install build tools (needed for some Python packages)
sudo apt install -y build-essential python3-dev

# Verify installation
python3 --version    # Should show 3.11.x or newer
pip3 --version
```

---

## Pi Zero 2 Setup (Lightweight Bot)

This setup is for running MCADV on Pi Zero 2 W (without local Ollama).

### Step 1: Verify 64-bit OS

```bash
# Check architecture
uname -m

# Should output: aarch64 (64-bit)
# If it shows "armv7l" (32-bit), you need to reflash with 64-bit OS
```

### Step 2: Install Python and Dependencies

```bash
# Install Python and essential packages
sudo apt install -y python3 python3-pip python3-venv python3-serial

# Verify installation
python3 --version    # Should show 3.11.x or newer
```

**Note:** Pi Zero 2 has limited resources (512MB RAM), so we won't install Ollama here. Instead, it will connect to Ollama running on Pi 5 or another server.

### Step 3: Optimize for Limited Resources

```bash
# Disable unnecessary services to free up RAM
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
sudo systemctl disable triggerhappy

# Reboot to apply
sudo reboot
```

After reboot, check available memory:

```bash
free -h
# You should have ~350-400MB available RAM
```

---

## Installing Ollama

### On Pi 5 (or Pi Zero 2 if you have 8GB variant)

**Note:** Only install Ollama on Pi 5. Pi Zero 2 W (512MB RAM) cannot run LLM models.

### Step 1: Install Ollama

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
# Should show: ollama version is 0.x.x
```

### Step 2: Configure Ollama to Use SSD (Pi 5 only)

```bash
# Set environment variable for Ollama models directory
echo 'export OLLAMA_MODELS=/mnt/ssd/ollama' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $OLLAMA_MODELS
# Should show: /mnt/ssd/ollama
```

### Step 3: Configure Ollama for Network Access (If using distributed setup)

If you want Pi Zero 2 to access Ollama on Pi 5:

```bash
# Edit Ollama service
sudo systemctl edit ollama

# Add these lines in the editor that opens:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/mnt/ssd/ollama"

# Save and exit (Ctrl+X, Y, Enter)

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Verify Ollama is running
sudo systemctl status ollama
```

### Step 4: Test Ollama Installation

```bash
# Check if service is running
curl http://localhost:11434/api/version

# Should return: {"version":"0.x.x"}

# If network access is enabled, test from another device:
curl http://192.168.1.50:11434/api/version  # Use Pi 5's IP
```

---

## Downloading Recommended Models

Based on the [MCADV documentation](../README.md#quick-model-selection-guide), here are the recommended models:

### For Raspberry Pi 5 (4GB RAM)

**Recommended: llama3.2:1b**

```bash
# Pull the model (on Pi 5)
ollama pull llama3.2:1b

# This will download ~1.3GB and store it in /mnt/ssd/ollama
# Download time: 5-15 minutes depending on internet speed
```

**Model details:**
- Size: 1.3 GB
- Speed: Fast (2-3s per scene)
- Quality: Good for interactive storytelling
- RAM usage: ~2-3GB when running

### For Raspberry Pi 5 (8GB RAM)

**Recommended: llama3.2:3b** (Better quality)

```bash
# Pull the model (on Pi 5 8GB)
ollama pull llama3.2:3b

# This will download ~3.2GB
# Download time: 10-30 minutes depending on internet speed
```

**Model details:**
- Size: 3.2 GB
- Speed: Medium (4-6s per scene)
- Quality: Very good for storytelling
- RAM usage: ~4-5GB when running

### Alternative Models

**For testing/lightweight:**

```bash
# TinyLlama (smallest, fastest, lower quality)
ollama pull tinyllama    # 638MB

# Very fast but basic storytelling
```

**For best quality (if you have powerful hardware):**

```bash
# For 8GB+ RAM (Jetson, PC, or powerful server)
ollama pull llama3.1:8b    # ~4.9GB - Best storytelling quality ⭐

# For 48GB+ VRAM (high-end server only)
ollama pull llama3.3:70b   # ~43GB - Outstanding quality
```

### Step 5: Verify Model Installation

```bash
# List installed models
ollama list

# Should show:
# NAME              ID              SIZE      MODIFIED
# llama3.2:1b      a1b2c3d4        1.3 GB    x minutes ago

# Test the model
ollama run llama3.2:1b "Write a short fantasy story in 2 sentences."

# You should see a creative response
# Press Ctrl+D to exit the interactive prompt
```

### Step 6: Pre-load Model (Optional, for faster first request)

```bash
# Keep model loaded in memory for 24 hours
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "test",
  "keep_alive": "24h"
}'
```

---

## Installing MCADV

### For Both Pi 5 and Pi Zero 2

### Step 1: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone MCADV repository
git clone https://github.com/hostyorkshire/MCADV.git

# Navigate into directory
cd MCADV

# Verify files
ls -la
# Should see: adventure_bot.py, meshcore.py, requirements.txt, etc.
```

### Step 2: Create Virtual Environment

```bash
# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Your prompt should now show (venv)
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install MCADV requirements
pip install -r requirements.txt

# Verify installation
pip list
# Should show: pyserial, requests, and other dependencies
```

### Step 4: Connect LoRa Radio

**Physical connection:**

1. Connect your LoRa MeshCore radio to a USB port
2. Wait for the device to be recognized (green LED should blink)

**Identify the device:**

```bash
# List USB serial devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Usually: /dev/ttyUSB0 or /dev/ttyACM0
# Note down the device path

# Check permissions
ls -l /dev/ttyUSB0

# If you see "crw-rw---- ... root dialout", add your user to dialout group:
sudo usermod -a -G dialout pi

# Log out and back in for group change to take effect
exit
ssh pi@pi5.local    # Reconnect
```

### Step 5: Test MCADV (Basic Test)

**Important:** The bot is configured to listen **only on channel index 1**, which corresponds to the **#adventure** MeshCore hashtag channel. All your MeshCore devices must be configured to use this channel.

**On Pi 5 (with Ollama):**

```bash
cd ~/MCADV
source venv/bin/activate

# Test with Ollama (adjust device path if needed)
# --channel-idx 1 = #adventure hashtag channel (REQUIRED)
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --model llama3.2:1b \
  --debug

# You should see:
# "Initializing bot..."
# "Ollama available at http://localhost:11434"
# "Model 'llama3.2:1b' is ready"
# "Bot started successfully"
# "Listening on channel 1 (#adventure)..."
```

**On Pi Zero 2 (connecting to Pi 5's Ollama):**

```bash
cd ~/MCADV
source venv/bin/activate

# Test connecting to Pi 5's Ollama (replace with Pi 5's IP)
# --channel-idx 1 = #adventure hashtag channel (REQUIRED)
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b \
  --debug

# You should see:
# "Initializing bot..."
# "Ollama available at http://192.168.1.50:11434"
# "Model 'llama3.2:1b' is ready"
# "Bot started successfully"
# "Listening on channel 1 (#adventure)..."
```

**Test offline mode (without Ollama):**

```bash
# Run without LLM (uses built-in story trees)
# --channel-idx 1 = #adventure hashtag channel (REQUIRED)
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --debug

# Should start instantly without Ollama
```

Press `Ctrl+C` to stop the bot.

**Channel Configuration Note:** 
- The bot **must** use `--channel-idx 1` to listen on the #adventure channel
- All players must have their MeshCore devices set to the #adventure channel
- The bot will ignore messages from all other channels

### Step 6: Configure as System Service (Auto-start on boot)

**On Pi 5:**

```bash
# Create systemd service file
sudo nano /etc/systemd/system/adventure_bot.service
```

Add this content:

```ini
[Unit]
Description=MCADV Adventure Bot
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MCADV
Environment="OLLAMA_URL=http://localhost:11434"
Environment="OLLAMA_MODEL=llama3.2:1b"
# Bot listens ONLY on channel 1 = #adventure hashtag channel
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**On Pi Zero 2 (connecting to Pi 5):**

```bash
sudo nano /etc/systemd/system/adventure_bot.service
```

Add this content (note the different OLLAMA_URL):

```ini
[Unit]
Description=MCADV Adventure Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MCADV
Environment="OLLAMA_URL=http://192.168.1.50:11434"
Environment="OLLAMA_MODEL=llama3.2:1b"
# Bot listens ONLY on channel 1 = #adventure hashtag channel
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start the service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable adventure_bot

# Start service now
sudo systemctl start adventure_bot

# Check status
sudo systemctl status adventure_bot

# You should see: "active (running)"

# Watch logs in real-time
sudo journalctl -u adventure_bot -f
```

Press `Ctrl+C` to stop watching logs.

---

## Testing Your Setup

### Step 1: Verify Services Are Running

**On Pi 5:**

```bash
# Check Ollama service
sudo systemctl status ollama
# Should show: active (running)

# Check MCADV service
sudo systemctl status adventure_bot
# Should show: active (running)

# Check Ollama API
curl http://localhost:11434/api/version
# Should return: {"version":"0.x.x"}
```

**On Pi Zero 2:**

```bash
# Check MCADV service
sudo systemctl status adventure_bot
# Should show: active (running)

# Check connection to Pi 5's Ollama
curl http://192.168.1.50:11434/api/version
# Should return: {"version":"0.x.x"}
```

### Step 2: Monitor Logs

```bash
# Watch MCADV logs
tail -f ~/MCADV/logs/adventure_bot.log

# Or using systemd:
sudo journalctl -u adventure_bot -f

# Look for:
# - "Ollama available at ..."
# - "Model 'llama3.2:1b' is ready"
# - "Bot started successfully"
# - No error messages
```

### Step 3: Test on LoRa Network

**IMPORTANT:** Your MeshCore radio must be configured to the **#adventure** channel (channel index 1) to communicate with the bot.

From another device with LoRa MeshCore radio on the **#adventure** channel:

1. **Verify you're on the correct channel:**
   - Configure your MeshCore device to channel index 1 (#adventure)
   - All communication with the bot must be on this channel

2. **Start an adventure:**
   ```
   Send message: !adv
   ```

3. **Bot should respond with:**
   ```
   🎲 Starting FANTASY adventure...
   [Story scene with 3 choices]
   Reply 1, 2, or 3 to choose
   ```

4. **Make a choice:**
   ```
   Send: 1
   ```

5. **Continue the adventure:**
   - Bot generates next scene based on your choice
   - Keep playing until you reach "THE END"

6. **Test other commands:**
   ```
   !adv help       - Show help
   !adv status     - Show current adventure status
   !adv quit       - Quit current adventure
   !adv fantasy    - Start fantasy theme
   !adv scifi      - Start sci-fi theme
   !adv horror     - Start horror theme
   ```

**Troubleshooting:** If the bot doesn't respond, verify:
- Bot is running and shows "Listening on channel 1 (#adventure)..."
- Your MeshCore device is set to channel index 1 (#adventure)
- Radio connection is working (check other MeshCore messages)

### Step 4: Performance Check

**Monitor resource usage:**

```bash
# Check memory usage
free -h

# Check CPU usage
htop

# Pi 5 should have:
# - ~2-3GB RAM used (with llama3.2:1b loaded)
# - ~20-40% CPU idle
# - Story generation: 2-5 seconds

# Pi Zero 2 should have:
# - ~50-100MB RAM used (without Ollama)
# - ~60-80% CPU idle
# - Story generation: depends on Pi 5's speed
```

**Test story generation speed:**

```bash
# Time a story generation
time curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "Write a short fantasy story scene.",
  "stream": false
}'

# On Pi 5 with llama3.2:1b: 2-5 seconds
# On Ubuntu Desktop (typical PC): 0.5-2 seconds (faster due to more powerful CPU)
```

---

## Troubleshooting

### Ubuntu Desktop Specific Issues

#### Issue: Ollama not installed or service not running

**Solution:**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Check if service is running
systemctl status ollama

# If not running, start it:
sudo systemctl start ollama
sudo systemctl enable ollama
```

#### Issue: LoRa radio not detected on Ubuntu

**Solution:**

```bash
# Check if device is detected
lsusb
dmesg | tail -20

# Check for USB serial devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# If driver issue, install USB serial drivers:
sudo apt install -y linux-headers-$(uname -r)

# For CH340/CH341 USB serial:
sudo modprobe ch341

# Check permissions
sudo usermod -a -G dialout $USER
# Log out and back in
```

#### Issue: Python virtual environment issues on Ubuntu

**Solution:**

```bash
# Ensure venv package is installed
sudo apt install -y python3-venv

# Remove and recreate venv
cd ~/MCADV
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Issue: Ubuntu goes to sleep and bot stops

**Solution:**

```bash
# Disable suspend/sleep
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'

# Or use systemd inhibit:
systemd-inhibit --what=sleep --who="MCADV Bot" --why="Running adventure bot" sleep infinity &
```

### Raspberry Pi Specific Issues

#### Issue: "ollama: command not found"

**Solution:**

```bash
# Reinstall Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
which ollama
# Should show: /usr/local/bin/ollama

# Check service
sudo systemctl status ollama
```

### Issue: "Cannot connect to Ollama" or "Connection refused"

**On Pi 5:**

```bash
# Check if Ollama is running
sudo systemctl status ollama

# If not running, start it:
sudo systemctl start ollama

# Check if listening on correct port
sudo netstat -tlnp | grep 11434
# Should show: 0.0.0.0:11434 or 127.0.0.1:11434

# If shows 127.0.0.1 only, edit service for network access:
sudo systemctl edit ollama
# Add: Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**On Pi Zero 2 (connecting to Pi 5):**

```bash
# Test network connectivity to Pi 5
ping -c 3 192.168.1.50    # Use your Pi 5's IP

# Test Ollama API endpoint
curl http://192.168.1.50:11434/api/version

# If fails, check Pi 5's firewall:
# On Pi 5:
sudo ufw status
# If active, allow port 11434:
sudo ufw allow 11434/tcp
```

### Issue: "Model 'llama3.2:1b' not found"

**Solution:**

```bash
# Check installed models
ollama list

# If model is missing, pull it:
ollama pull llama3.2:1b

# Verify model files exist
ls -lh /mnt/ssd/ollama/models/manifests/registry.ollama.ai/library/llama3.2/
```

### Issue: "Out of memory" or Pi becomes unresponsive

**On Pi 5:**

```bash
# Check memory usage
free -h

# If RAM is full, try smaller model:
ollama pull tinyllama
# Update bot to use tinyllama instead

# Or add swap space:
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**On Pi Zero 2:**

```bash
# Pi Zero 2 (512MB) should NOT run Ollama locally
# Always use remote Ollama on Pi 5 or another server

# Free up memory:
sudo systemctl stop bluetooth
sudo systemctl stop avahi-daemon
```

### Issue: "Permission denied" on /dev/ttyUSB0

**Solution:**

```bash
# Add user to dialout group
sudo usermod -a -G dialout pi

# Log out and back in
exit
ssh pi@pi5.local

# Verify group membership
groups
# Should show: ... dialout ...

# Check device permissions
ls -l /dev/ttyUSB0
# Should show: crw-rw---- ... root dialout
```

### Issue: SSD not mounting on boot

**Solution:**

```bash
# Check if SSD is detected
lsblk
# Should show sda with partition sda1

# Check fstab entry
cat /etc/fstab | grep ssd

# Test manual mount
sudo mount -a

# Check for errors
dmesg | tail -20

# If UUID changed, update fstab:
sudo blkid /dev/sda1    # Get new UUID
sudo nano /etc/fstab     # Update UUID line
```

### Issue: Slow story generation (>10 seconds)

**Solutions:**

1. **Use smaller model:**
   ```bash
   ollama pull tinyllama
   # Update bot config to use tinyllama
   ```

2. **Reduce output length:**
   Edit `adventure_bot.py`, find line ~595:
   ```python
   "options": {"num_predict": 50, "temperature": 0.8}  # Reduced from 80
   ```

3. **Pre-load model:**
   ```bash
   # Keep model in memory
   curl http://localhost:11434/api/generate -d '{
     "model": "llama3.2:1b",
     "prompt": "test",
     "keep_alive": "24h"
   }'
   ```

4. **Check CPU throttling:**
   ```bash
   vcgencmd get_throttled
   # 0x0 = good, anything else = throttling
   
   # Check temperature
   vcgencmd measure_temp
   # Should be < 80°C, add cooling fan if higher
   ```

### Issue: Bot not responding on LoRa network

**Most common cause:** Wrong channel configuration!

**Solutions:**

```bash
# 1. Check bot is running and listening on correct channel
sudo systemctl status adventure_bot

# 2. Check logs - should show "Listening on channel 1 (#adventure)..."
tail -50 ~/MCADV/logs/adventure_bot.log
# Or: sudo journalctl -u adventure_bot -n 50

# 3. Verify your MeshCore radio is on the #adventure channel (channel index 1)
# The bot ONLY responds on channel 1 (#adventure)
# Check your MeshCore device configuration!

# 4. Verify radio is connected
ls -l /dev/ttyUSB0

# 5. Test radio connectivity with other MeshCore devices
# Can you send/receive regular messages on the #adventure channel?

# 6. Restart bot
sudo systemctl restart adventure_bot
sudo journalctl -u adventure_bot -f  # Watch for "Listening on channel 1..."
```

**Channel Configuration Checklist:**
- ✅ Bot command includes `--channel-idx 1`
- ✅ Your MeshCore device is set to channel index 1
- ✅ Channel is named "#adventure" or matches channel 1
- ✅ Other devices on same channel can communicate
- ❌ Bot will NOT respond on any other channel

# Restart bot
sudo systemctl restart adventure_bot
```

### Issue: WiFi connection drops

**Solution:**

```bash
# Disable WiFi power management
sudo nano /etc/rc.local

# Add before "exit 0":
/sbin/iwconfig wlan0 power off

# Reboot
sudo reboot

# Or use Ethernet connection (more reliable)
```

### Issue: "pip install" fails with "externally-managed-environment"

**Solution:**

```bash
# Always use virtual environment (recommended method)
cd ~/MCADV
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Or use --break-system-packages flag (not recommended):
pip install --break-system-packages -r requirements.txt
```

---

## Next Steps

### ✅ You're all set! Here's what you can do now:

1. **If using Ubuntu for development:**
   - Iterate quickly with full debugging tools
   - Test multiple models easily (your PC is more powerful than Pi)
   - Use your favorite IDE (VSCode, PyCharm, etc.)
   - When satisfied, deploy to Pi with the same code
   ```bash
   cd ~/MCADV
   source venv/bin/activate
   python3 adventure_bot.py --port /dev/ttyUSB0 --debug
   ```

2. **Explore different themes:**
   - Send `!adv fantasy` for fantasy adventures
   - Send `!adv scifi` for sci-fi adventures
   - Send `!adv horror` for horror adventures

3. **Try different models:**
   ```bash
   # On Ubuntu/Pi 5, pull additional models:
   ollama pull llama3.2:3b    # Better quality (if 8GB+ RAM)
   ollama pull llama3.1:8b    # Best quality (if powerful hardware)
   ollama pull phi3:mini      # Alternative engine
   
   # Test a model:
   python3 adventure_bot.py --port /dev/ttyUSB0 --model llama3.2:3b
   
   # Update service to use new model (if using systemd):
   sudo systemctl edit adventure_bot
   # Change: Environment="OLLAMA_MODEL=llama3.2:3b"
   sudo systemctl restart adventure_bot
   ```

4. **Monitor performance:**
   ```bash
   # Watch system resources
   htop
   
   # Watch logs
   tail -f ~/MCADV/logs/adventure_bot.log
   # Or: sudo journalctl -u adventure_bot -f (if using systemd)
   
   # Check model loading times
   sudo journalctl -u ollama -f
   ```

5. **Scale up (when ready for production):**
   - Deploy from Ubuntu to Pi 5 (same code!)
   - Add more Pi Zero 2 devices as bot nodes
   - Share one Pi 5/Ubuntu Ollama server across multiple bots
   - See [HARDWARE.md](../HARDWARE.md) for distributed architecture

6. **Optimize:**
   - Adjust model parameters for your preferences
   - See [PERFORMANCE.md](../PERFORMANCE.md) for tuning tips
   - See [guides/OLLAMA_SETUP.md](OLLAMA_SETUP.md) for advanced Ollama configuration

---

## Additional Resources

- **Main README:** [../README.md](../README.md)
- **Hardware Guide:** [../HARDWARE.md](../HARDWARE.md)
- **Ollama Setup Guide:** [OLLAMA_SETUP.md](OLLAMA_SETUP.md)
- **Performance Guide:** [../PERFORMANCE.md](../PERFORMANCE.md)
- **Ollama Documentation:** https://github.com/ollama/ollama
- **Ollama Models:** https://ollama.com/library
- **MeshCore Project:** https://github.com/meshcore-dev/MeshCore

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check logs:**
   ```bash
   tail -100 ~/MCADV/logs/adventure_bot.log
   sudo journalctl -u adventure_bot -n 100
   sudo journalctl -u ollama -n 100
   ```

2. **Enable debug mode:**
   ```bash
   sudo systemctl stop adventure_bot
   cd ~/MCADV
   source venv/bin/activate
   python3 adventure_bot.py --debug --port /dev/ttyUSB0
   ```

3. **Test each component separately:**
   - Ollama: `curl http://localhost:11434/api/version`
   - Model: `ollama run llama3.2:1b "test"`
   - Network: `ping 192.168.1.50`
   - Radio: `ls -l /dev/ttyUSB0`

4. **Open an issue on GitHub:**
   - https://github.com/hostyorkshire/MCADV/issues
   - Include logs and configuration details
   - Describe what you were trying to do

---

## Summary

Congratulations! Depending on your setup, you've successfully:

### Ubuntu Desktop (Development)
✅ Installed Ubuntu with all dependencies
✅ Installed Ollama and downloaded recommended models
✅ Installed MCADV adventure bot
✅ Connected LoRa radio via USB serial
✅ Tested your setup on LoRa network
✅ Created a fast development environment

**Your Ubuntu development setup is ready! Test and iterate quickly before deploying to Pi.**

### Raspberry Pi (Production)
✅ Downloaded and flashed Raspberry Pi OS Lite (64-bit)
✅ Configured SSH, WiFi, and system settings
✅ Set up USB SSD for model storage (Pi 5)
✅ Installed Ollama and downloaded recommended models
✅ Installed MCADV adventure bot
✅ Configured auto-start on boot
✅ Tested your setup on LoRa network

**Your Pi setup is now ready for interactive AI-powered adventures over LoRa mesh networks!**

### Development to Production Path

1. **Develop on Ubuntu** - Fast iteration and testing
2. **Test thoroughly** - Verify all features work
3. **Deploy to Pi 5** - Same code, same models
4. **Scale with Pi Zero 2** - Add lightweight nodes
5. **Enjoy!** - Reliable field deployment

---

Happy adventuring! 🎲🗺️🚀

# Comprehensive Ollama Setup Guide for MCADV

This guide covers setting up Ollama for use with MCADV, both locally (on the same device) and over your local area network (LAN).

---

## Table of Contents

1. [What is Ollama?](#what-is-ollama)
2. [Why Use Ollama with MCADV?](#why-use-ollama-with-mcadv)
3. [Prerequisites](#prerequisites)
4. [Local Setup (Same Device)](#local-setup-same-device)
5. [LAN Setup (Separate Devices)](#lan-setup-separate-devices)
6. [Choosing the Right Model](#choosing-the-right-model)
7. [Configuration Examples](#configuration-examples)
8. [Testing Your Setup](#testing-your-setup)
9. [Troubleshooting](#troubleshooting)
10. [Performance Tuning](#performance-tuning)
11. [Security Considerations](#security-considerations)

---

## What is Ollama?

Ollama is a tool that makes it easy to run large language models (LLMs) locally on your own hardware. It provides a simple REST API that applications like MCADV can use to generate AI-powered content without relying on cloud services.

**Key benefits:**
- 🔒 **Privacy** - Your data never leaves your network
- 💰 **Cost** - Free to use (no API charges)
- 📡 **Offline** - Works without internet connection
- ⚡ **Low latency** - Direct network communication

---

## Why Use Ollama with MCADV?

MCADV is an AI-powered adventure bot for LoRa mesh networks. While it includes offline story trees, using Ollama provides:

1. **Dynamic storytelling** - AI generates unique stories based on player choices
2. **Unlimited themes** - Not limited to the 3 built-in themes (fantasy, sci-fi, horror)
3. **Better narrative flow** - More creative and contextual responses
4. **No internet required** - Perfect for remote/field deployments
5. **No API costs** - Unlike OpenAI/Groq, completely free

---

## Prerequisites

### For Ollama Server

**Minimum Hardware Requirements:**
- **CPU:** Quad-core ARM (Pi 4/5) or x86 processor
- **RAM:** 4GB minimum (8GB+ recommended)
- **Storage:** 10-20GB free space (models are 2-8GB each)
- **OS:** Linux (Ubuntu, Debian, Raspberry Pi OS), macOS, or Windows

**Recommended Hardware:**
- Raspberry Pi 5 (8GB) - Budget option
- NVIDIA Jetson Orin Nano - Best performance with GPU
- Mini PC with 16GB+ RAM - Maximum capability

See [HARDWARE.md](../HARDWARE.md) for detailed hardware recommendations.

### For MCADV Bot

- Raspberry Pi Zero 2W or better
- Python 3.7+
- Network connectivity to Ollama server (WiFi or Ethernet)

---

## Local Setup (Same Device)

Use this setup when running both Ollama and MCADV on the same device (e.g., Raspberry Pi 4 or 5).

### Step 1: Install Ollama

```bash
# Install Ollama (works on Linux and macOS)
curl -fsSL https://ollama.com/install.sh | sh
```

**For Raspberry Pi OS (64-bit):**
```bash
# Ensure you're running 64-bit OS
uname -m  # Should output: aarch64

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

**For other platforms:**
- **macOS:** Download from [ollama.com/download](https://ollama.com/download)
- **Windows:** Download installer from [ollama.com/download](https://ollama.com/download)

### Step 2: Verify Installation

```bash
# Check Ollama version
ollama --version

# Check if service is running
systemctl status ollama  # Linux
# or
ps aux | grep ollama     # macOS/manual installs
```

### Step 3: Pull a Model

Start with a small, fast model suitable for Raspberry Pi:

```bash
# Pull llama3.2:1b (smallest, fastest - recommended for Pi 4/5)
ollama pull llama3.2:1b

# Alternative models (larger, better quality, slower):
# ollama pull llama3.2:3b    # Medium quality, needs 8GB RAM
# ollama pull tinyllama      # Very fast, lower quality
# ollama pull phi3:mini      # Good balance, 4GB RAM
```

**Model download sizes:**
- `llama3.2:1b` - ~1.3GB
- `tinyllama` - ~638MB
- `llama3.2:3b` - ~3.2GB
- `phi3:mini` - ~2.3GB

### Step 4: Test Ollama

```bash
# Test with a simple prompt
ollama run llama3.2:1b "Tell me a short fantasy story in 50 words."
```

If you see a story response, Ollama is working!

### Step 5: Configure MCADV

Since Ollama runs on the same device, use the default localhost URL:

```bash
cd /home/runner/work/MCADV/MCADV

# Option A: Run manually with default settings
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --model llama3.2:1b

# Option B: Set environment variables
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2:1b
python3 adventure_bot.py --port /dev/ttyUSB0
```

**Note:** The default `--ollama-url` is already `http://localhost:11434`, so you can omit it if Ollama is running locally.

### Step 6: Install as a Service (Optional)

Edit the systemd service file to include Ollama settings:

```bash
# Edit the service configuration
sudo nano /etc/systemd/system/adventure_bot.service
```

Add environment variables:
```ini
[Service]
Environment="OLLAMA_URL=http://localhost:11434"
Environment="OLLAMA_MODEL=llama3.2:1b"
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart adventure_bot
```

---

## LAN Setup (Separate Devices)

Use this setup when running Ollama on a more powerful device (Pi 5, Jetson, PC) and MCADV on a Pi Zero 2W.

### Architecture Overview

```
┌──────────────────┐         Local Network         ┌──────────────────┐
│  Pi Zero 2W      │ ←─────────────────────────→ │  Ollama Server   │
│  (MCADV Bot)     │    HTTP (Port 11434)          │  (Pi 5/PC/etc)   │
├──────────────────┤                                ├──────────────────┤
│ • LoRa Radio     │                                │ • Ollama         │
│ • Message Handle │                                │ • LLM Models     │
│ • Session Mgmt   │                                │ • Story Gen      │
└──────────────────┘                                └──────────────────┘
```

### Step 1: Install Ollama on Server

On your Pi 5, Jetson, or PC:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2:1b

# For more powerful hardware, use a better model:
# ollama pull llama3.2:3b    # Pi 5 8GB
# ollama pull phi3:mini      # Pi 5 8GB / Jetson
```

### Step 2: Configure Ollama for Network Access

By default, Ollama only listens on localhost. To accept connections from other devices:

**Option A: Environment Variable (Recommended)**

```bash
# Edit the Ollama service file
sudo systemctl edit ollama

# Add this content in the editor that opens:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Save and exit (Ctrl+X, Y, Enter in nano)

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**Option B: Systemd Drop-in File**

```bash
# Create override directory
sudo mkdir -p /etc/systemd/system/ollama.service.d/

# Create override file
sudo nano /etc/systemd/system/ollama.service.d/override.conf

# Add this content:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Save and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**Option C: Manual Start (Testing)**

For quick testing without modifying the service:

```bash
# Stop the service
sudo systemctl stop ollama

# Run manually with network binding
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### Step 3: Find Server IP Address

On the Ollama server, find its IP address:

```bash
# Get IP address
hostname -I

# Or for specific interface
ip addr show eth0    # Ethernet
ip addr show wlan0   # WiFi
```

Example output: `192.168.1.50`

**Alternative: Use hostname (requires mDNS/Avahi)**

If both devices support mDNS (most Linux systems do):

```bash
# On Ollama server, check hostname
hostname

# Example: "pi5" or "jetson"
# You can use: http://pi5.local:11434
```

### Step 4: Test Network Connection

From your MCADV device (Pi Zero 2W), test connectivity:

```bash
# Test network connectivity
ping -c 3 192.168.1.50

# Test Ollama API endpoint
curl http://192.168.1.50:11434/api/version

# Expected response:
# {"version":"0.1.x"}
```

If the curl command returns a version, Ollama is accessible!

### Step 5: Configure MCADV

On your Pi Zero 2W (or device running MCADV):

```bash
cd /home/runner/work/MCADV/MCADV

# Option A: Command line arguments
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b

# Option B: Environment variables
export OLLAMA_URL=http://192.168.1.50:11434
export OLLAMA_MODEL=llama3.2:1b
python3 adventure_bot.py --port /dev/ttyUSB0

# Option C: Using hostname (if mDNS works)
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --ollama-url http://pi5.local:11434 \
  --model llama3.2:1b
```

### Step 6: Configure Systemd Service

Edit the service file on your MCADV device:

```bash
sudo nano /etc/systemd/system/adventure_bot.service
```

Modify the `ExecStart` line or add environment variables:

```ini
[Service]
# Option A: Use environment variables
Environment="OLLAMA_URL=http://192.168.1.50:11434"
Environment="OLLAMA_MODEL=llama3.2:1b"
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1

# Option B: Use command line arguments
# ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
#   --port /dev/ttyUSB0 \
#   --channel-idx 1 \
#   --ollama-url http://192.168.1.50:11434 \
#   --model llama3.2:1b
```

Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart adventure_bot
sudo journalctl -u adventure_bot -f  # Watch logs
```

### Step 7: Configure Firewall (If Needed)

If you have a firewall enabled on the Ollama server:

**On Ubuntu/Debian:**
```bash
sudo ufw allow 11434/tcp
sudo ufw status
```

**On Raspberry Pi OS (if ufw installed):**
```bash
sudo ufw allow from 192.168.1.0/24 to any port 11434
```

**Check if firewall is blocking:**
```bash
sudo iptables -L -n | grep 11434
```

---

## Choosing the Right Model

Different models have different trade-offs between speed, quality, and resource usage.

### Model Comparison

| Model | Size | RAM Needed | Speed (Pi 5) | Quality | Best For |
|-------|------|------------|--------------|---------|----------|
| `tinyllama` | 638MB | 2GB | Very Fast (~1s) | Basic | Testing, Pi Zero with small server |
| `llama3.2:1b` | 1.3GB | 3GB | Fast (~2-3s) | Good | **Recommended for Pi 4/5** |
| `phi3:mini` | 2.3GB | 4GB | Medium (~3-4s) | Better | Pi 5 8GB |
| `llama3.2:3b` | 3.2GB | 6GB | Slower (~5-8s) | Very Good | Pi 5 8GB, Jetson |
| `llama3:8b` | 4.7GB | 8GB+ | Slow (~10-15s) | Excellent | Jetson, Mini PC |

### Recommendations by Hardware

**Raspberry Pi 4/5 (4GB):**
- Primary: `llama3.2:1b`
- Alternative: `tinyllama`

**Raspberry Pi 5 (8GB):**
- Primary: `llama3.2:3b`
- Alternative: `phi3:mini`

**NVIDIA Jetson Orin Nano:**
- Primary: `llama3.2:3b`
- Alternative: `llama3:8b` (with GPU)

**Mini PC / Desktop:**
- Primary: `llama3:8b`
- Alternative: `mistral:7b`

### Model Selection Strategy

1. **Start small** - Begin with `llama3.2:1b`
2. **Test performance** - Check response times
3. **Upgrade if needed** - Move to larger model if Pi can handle it
4. **Balance speed vs quality** - Faster responses = better UX on LoRa

### Storage Capacity Planning

**Understanding your storage constraints:**

Ollama models are relatively small compared to modern storage capacities. Here's what you need to know:

**Typical Storage Scenarios:**

| Available Storage | What You Can Do | Recommended Setup |
|-------------------|-----------------|-------------------|
| **32-64 GB** | Limited capacity | 1-2 small models (llama3.2:1b + tinyllama) |
| **128 GB** | Comfortable | 3-4 models of various sizes |
| **239 GB** | **Plenty of space!** | All recommended models + room for growth |
| **500+ GB** | Extensive | Full model library, multiple versions |

**For 239 GB SSD (Your Scenario):**

With 239 GB of storage, you have MORE than enough space for any CYOA bot deployment. Here's the breakdown:

```
Total Space:        239 GB
OS + System:        -20 GB (typical)
MCADV Bot:          -0.1 GB
Logs & Data:        -1 GB
Available for LLM:  ~218 GB
```

**What fits comfortably:**

1. **Conservative Setup** (~8 GB used):
   - `llama3.2:1b` (1.3 GB) - Fast, good quality
   - `llama3.2:3b` (3.2 GB) - Better quality, slower
   - `tinyllama` (638 MB) - Backup/testing
   - **Remaining:** ~210 GB free

2. **Balanced Setup** (~15 GB used):
   - `llama3.2:1b` (1.3 GB) - Production default
   - `llama3.2:3b` (3.2 GB) - High quality option
   - `llama3:8b` (4.7 GB) - Best quality (if hardware supports)
   - `phi3:mini` (2.3 GB) - Alternative engine
   - `mistral:7b` (4.1 GB) - Another excellent option
   - **Remaining:** ~204 GB free

3. **Comprehensive Setup** (~25 GB used):
   - All models from Balanced Setup
   - `qwen2.5:7b` (4.7 GB) - Alternative 7B model
   - `gemma2:9b` (5.4 GB) - Google's model
   - Multiple model versions/quantizations
   - **Remaining:** ~194 GB free

**Recommendation for 239 GB:**

Since you have abundant storage, we recommend the **Balanced Setup**:

```bash
# Install multiple models for flexibility
ollama pull llama3.2:1b    # 1.3 GB - Fast daily driver
ollama pull llama3.2:3b    # 3.2 GB - Better quality
ollama pull phi3:mini      # 2.3 GB - Microsoft's efficient model
```

**Why multiple models?**
- **Development/Testing:** Use `llama3.2:1b` for fast iteration
- **Production:** Use `llama3.2:3b` for better story quality
- **Experimentation:** Try `phi3:mini` for different narrative styles
- **Failover:** If one model has issues, switch to another
- **Theme-specific:** Use different models for different adventure themes

**Storage is NOT your bottleneck:**

With 239 GB, focus on these factors instead:
1. **RAM capacity** - Limits which models can run simultaneously
2. **CPU/GPU speed** - Determines response time
3. **Network bandwidth** - If using distributed setup

**Bottom Line:**
- ✅ 239 GB = Plenty of space for any model combination
- ✅ You can install 20+ models and still have room
- ✅ Storage won't be a limiting factor
- ⚠️ RAM and CPU will be your real constraints

**Best Model for CYOA Bot with 239 GB Storage:**

**For Raspberry Pi 4/5 (4-8GB RAM):**
```bash
ollama pull llama3.2:1b
# Storage used: 1.3 GB
# Remaining: ~237 GB
# Speed: Fast (2-3s per story)
# Quality: Good - perfect for CYOA
```

**For more powerful hardware (Jetson/PC with 8GB+ RAM):**
```bash
ollama pull llama3.2:3b
# Storage used: 3.2 GB
# Remaining: ~236 GB
# Speed: Medium (4-6s per story)
# Quality: Very good - excellent CYOA narratives
```

**Pro Tip:** Install both and switch based on your needs:
```bash
# Fast mode for testing
python3 adventure_bot.py --model llama3.2:1b

# Quality mode for production
python3 adventure_bot.py --model llama3.2:3b
```

---

## Configuration Examples

### Example 1: Pi Zero 2W + Pi 5 (Recommended Budget Setup)

**On Pi 5 (192.168.1.50):**
```bash
# Install and configure Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b

# Enable network access
sudo systemctl edit ollama
# Add: Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**On Pi Zero 2W:**
```bash
cd ~/MCADV
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b
```

### Example 2: Pi 4 Standalone (All-in-One)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b

# Run MCADV (will use localhost by default)
cd ~/MCADV
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --model llama3.2:1b
```

### Example 3: Multiple Bots Sharing One Server

**On Server (192.168.1.100):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b

# Configure for network access
sudo systemctl edit ollama
# Add: Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**On Bot 1 (192.168.1.101):**
```bash
cd ~/MCADV
export OLLAMA_URL=http://192.168.1.100:11434
python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1
```

**On Bot 2 (192.168.1.102):**
```bash
cd ~/MCADV
export OLLAMA_URL=http://192.168.1.100:11434
python3 adventure_bot.py --port /dev/ttyUSB1 --channel-idx 2
```

### Example 4: Using Docker for Ollama

If you prefer Docker:

```bash
# Run Ollama in Docker
docker run -d \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  --name ollama \
  ollama/ollama

# Pull a model
docker exec ollama ollama pull llama3.2:1b

# Configure MCADV
export OLLAMA_URL=http://localhost:11434
python3 adventure_bot.py --port /dev/ttyUSB0 --model llama3.2:1b
```

---

## Testing Your Setup

### Step 1: Test Ollama Directly

```bash
# Test with ollama command (on Ollama server)
ollama run llama3.2:1b "Write a 2-line fantasy story."

# Test API endpoint (from any device)
curl http://192.168.1.50:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "Write a short adventure scene.",
  "stream": false
}'
```

### Step 2: Test MCADV Bot

```bash
# Start MCADV in debug mode
cd ~/MCADV
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --channel-idx 1 \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b \
  --debug

# Watch the logs for Ollama connection messages
```

### Step 3: Test on LoRa Network

1. Send `!adv` on the configured MeshCore channel
2. Bot should respond with a story scene and choices
3. Reply with `1`, `2`, or `3` to make a choice
4. Continue until you see "THE END"

### Step 4: Check Logs

```bash
# Watch MCADV logs
tail -f ~/MCADV/logs/adventure_bot.log

# Watch Ollama logs (if systemd service)
sudo journalctl -u ollama -f

# Check for errors
grep -i error ~/MCADV/logs/adventure_bot.log
```

---

## Troubleshooting

### Problem: "Connection refused" or "Cannot connect to Ollama"

**Symptoms:**
- MCADV logs show: "Ollama unavailable: Connection refused"
- Bot falls back to offline stories

**Solutions:**

1. **Check if Ollama is running:**
   ```bash
   systemctl status ollama
   # or
   curl http://localhost:11434/api/version
   ```

2. **Verify Ollama is listening on network:**
   ```bash
   sudo netstat -tlnp | grep 11434
   # Should show: 0.0.0.0:11434 (not 127.0.0.1:11434)
   ```

3. **Check OLLAMA_HOST environment variable:**
   ```bash
   sudo systemctl show ollama | grep OLLAMA_HOST
   # Should show: Environment=OLLAMA_HOST=0.0.0.0:11434
   ```

4. **Restart Ollama service:**
   ```bash
   sudo systemctl restart ollama
   sudo systemctl status ollama
   ```

### Problem: "Model not found"

**Symptoms:**
- Error: "model 'llama3.2:1b' not found"

**Solutions:**

1. **Pull the model:**
   ```bash
   ollama pull llama3.2:1b
   ```

2. **List available models:**
   ```bash
   ollama list
   ```

3. **Verify model name in MCADV config:**
   ```bash
   # Check if model name matches exactly
   python3 adventure_bot.py --help | grep model
   ```

### Problem: Slow Response Times

**Symptoms:**
- Stories take >10 seconds to generate
- LoRa timeouts or frustrated users

**Solutions:**

1. **Use a smaller model:**
   ```bash
   ollama pull llama3.2:1b  # Instead of 3b or 8b
   ```

2. **Reduce num_predict tokens:**
   Edit `adventure_bot.py` (around line 595):
   ```python
   "options": {"num_predict": 60, "temperature": 0.8},  # Reduced from 80
   ```

3. **Check CPU/RAM usage:**
   ```bash
   # While generating a story
   top
   # Look for high CPU/RAM usage
   ```

4. **Use a more powerful device:**
   - Consider upgrading to Pi 5 or Jetson
   - See [HARDWARE.md](../HARDWARE.md)

### Problem: Network Connectivity Issues

**Symptoms:**
- Intermittent connection failures
- "Connection timeout" errors

**Solutions:**

1. **Use static IP instead of hostname:**
   ```bash
   # Instead of: http://pi5.local:11434
   # Use: http://192.168.1.50:11434
   ```

2. **Check network stability:**
   ```bash
   ping -c 100 192.168.1.50
   # Should have 0% packet loss
   ```

3. **Test from MCADV device:**
   ```bash
   curl -v http://192.168.1.50:11434/api/version
   ```

4. **Check WiFi signal strength:**
   ```bash
   iwconfig wlan0 | grep Signal
   ```

### Problem: Out of Memory Errors

**Symptoms:**
- Ollama crashes or restarts
- System becomes unresponsive

**Solutions:**

1. **Use a smaller model:**
   ```bash
   ollama pull tinyllama  # Only ~638MB
   ```

2. **Add swap space (Pi):**
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

3. **Check available memory:**
   ```bash
   free -h
   ```

4. **Close other applications:**
   ```bash
   # Stop unnecessary services
   sudo systemctl stop bluetooth
   sudo systemctl stop avahi-daemon
   ```

### Problem: Firewall Blocking Connections

**Symptoms:**
- Connection works from localhost but not from other devices
- `telnet 192.168.1.50 11434` fails

**Solutions:**

1. **Check firewall status:**
   ```bash
   sudo ufw status
   # or
   sudo iptables -L -n
   ```

2. **Allow Ollama port:**
   ```bash
   sudo ufw allow 11434/tcp
   sudo ufw reload
   ```

3. **Temporarily disable firewall (testing only):**
   ```bash
   sudo ufw disable
   # Test connection, then re-enable:
   sudo ufw enable
   ```

### Problem: "Ollama unavailable" but manual curl works

**Symptoms:**
- `curl http://192.168.1.50:11434/api/generate` works
- MCADV still shows "Ollama unavailable"

**Solutions:**

1. **Check URL format in MCADV:**
   ```bash
   # Ensure no trailing slash
   --ollama-url http://192.168.1.50:11434
   # NOT: http://192.168.1.50:11434/
   ```

2. **Verify Python requests library:**
   ```bash
   pip list | grep requests
   # Should show: requests  x.x.x
   ```

3. **Test with Python directly:**
   ```python
   import requests
   resp = requests.get('http://192.168.1.50:11434/api/version')
   print(resp.json())
   ```

4. **Check debug logs:**
   ```bash
   python3 adventure_bot.py --debug --port /dev/ttyUSB0 2>&1 | grep -i ollama
   ```

---

## Performance Tuning

### Optimize Ollama Settings

Edit `/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
# Bind to all interfaces
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Limit concurrent requests (helps with limited RAM)
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Keep models in memory longer (faster repeated requests)
Environment="OLLAMA_KEEP_ALIVE=10m"

# For GPU users (Jetson/NVIDIA)
# Environment="OLLAMA_NUM_GPU=1"
```

Then restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Optimize Model Parameters

For faster responses, edit `adventure_bot.py` (around line 595):

```python
"options": {
    "num_predict": 60,      # Reduced from 80 (shorter responses)
    "temperature": 0.7,     # More consistent (was 0.8)
    "top_k": 40,           # Focus on likely tokens
    "top_p": 0.9,          # Nucleus sampling
    "repeat_penalty": 1.1   # Reduce repetition
}
```

### Network Optimization

1. **Use wired Ethernet when possible:**
   - Lower latency than WiFi
   - More reliable connection

2. **Optimize WiFi settings:**
   ```bash
   # Disable power management on WiFi
   sudo iwconfig wlan0 power off
   ```

3. **Use static IP addresses:**
   - Faster than mDNS hostname resolution
   - More reliable

### Pre-load Models

To avoid cold start delays:

```bash
# On Ollama server, keep model loaded
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "test",
  "keep_alive": "24h"
}'
```

Or set globally (in service override):
```ini
Environment="OLLAMA_KEEP_ALIVE=24h"
```

---

## Security Considerations

### Network Security

1. **Firewall Rules:**
   - Only allow connections from trusted devices
   - Use source IP restrictions:
     ```bash
     sudo ufw allow from 192.168.1.0/24 to any port 11434
     ```

2. **Network Isolation:**
   - Keep Ollama on a private network
   - Don't expose port 11434 to the internet

3. **VPN/Tunnel for Remote Access:**
   - Use WireGuard or Tailscale instead of port forwarding
   - Never expose Ollama directly to the internet

### Access Control

1. **No Authentication:**
   - Ollama has no built-in authentication
   - Trust is based on network access only

2. **Reverse Proxy (Advanced):**
   - Add nginx/Apache with authentication
   - Example nginx config:
     ```nginx
     location /ollama/ {
       auth_basic "Restricted";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://localhost:11434/;
     }
     ```

### Resource Limits

1. **Prevent DoS:**
   - Limit concurrent connections
   - Set rate limits on network level

2. **Monitor Usage:**
   ```bash
   # Watch Ollama resource usage
   watch -n 1 'ps aux | grep ollama'
   ```

3. **Set System Limits:**
   Edit `/etc/systemd/system/ollama.service.d/override.conf`:
   ```ini
   [Service]
   MemoryMax=6G
   CPUQuota=400%
   ```

---

## Next Steps

### Verify Everything Works

1. ✅ Ollama is installed and running
2. ✅ Model is downloaded (`ollama list`)
3. ✅ Network access is configured (if LAN setup)
4. ✅ MCADV can connect to Ollama
5. ✅ Test adventure works on LoRa network

### Monitor and Maintain

```bash
# Check Ollama status regularly
systemctl status ollama

# Monitor logs
sudo journalctl -u ollama -f
tail -f ~/MCADV/logs/adventure_bot.log

# Update Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Update models
ollama pull llama3.2:1b
```

### Experiment and Optimize

- Try different models to find the best balance
- Adjust `num_predict` and `temperature` for your preferences
- Consider adding more powerful hardware for better models

---

## Additional Resources

- **Ollama Documentation:** https://github.com/ollama/ollama
- **Ollama Model Library:** https://ollama.com/library
- **MCADV Hardware Guide:** [HARDWARE.md](../HARDWARE.md)
- **MCADV Performance Guide:** [PERFORMANCE.md](../PERFORMANCE.md)
- **MeshCore Project:** https://github.com/meshcore-dev/MeshCore

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check MCADV logs:**
   ```bash
   tail -100 ~/MCADV/logs/adventure_bot.log
   ```

2. **Check Ollama logs:**
   ```bash
   sudo journalctl -u ollama -n 100
   ```

3. **Enable debug mode:**
   ```bash
   python3 adventure_bot.py --debug --port /dev/ttyUSB0
   ```

4. **Test each component separately:**
   - Ollama API (curl)
   - Network connectivity (ping)
   - Model loading (ollama run)

5. **Open an issue:**
   - GitHub: https://github.com/hostyorkshire/MCADV/issues
   - Include logs and configuration details

---

## Summary

This guide covered:

✅ Installing Ollama locally and on LAN  
✅ Configuring MCADV to use Ollama  
✅ Choosing the right model for your hardware  
✅ Testing and troubleshooting your setup  
✅ Performance tuning and security best practices

**Quick Reference Commands:**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.2:1b

# Run MCADV with Ollama
python3 adventure_bot.py \
  --port /dev/ttyUSB0 \
  --ollama-url http://192.168.1.50:11434 \
  --model llama3.2:1b
```

Happy adventuring! 🎲🗺️

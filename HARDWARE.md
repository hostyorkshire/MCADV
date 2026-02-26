# Hardware Recommendations for MCADV Setup

## Architecture Clarification 🤖

### Where Does the Bot Run?

**The bot (adventure_bot.py) with all game logic runs on the compute device:**
- ✅ **Pi 4/5** - Connects to LoRa radio via USB, runs bot + LLM
- ✅ **Desktop PC (Ubuntu)** - For development/testing, acts like Pi 4/5
- ❌ **Pi Zero 2W** - Only for radio gateway (future implementation)

### Current vs. Future Architecture

**Current Implementation (Standalone Mode):**
```
Player → LoRa → Pi 4/5 (adventure_bot.py via USB) → LLM → Response
                   |
              Bot runs here
              Radio + Logic + LLM
```

**Future Implementation (Distributed Mode):**
```
Player → LoRa → Pi Zero 2W → Network → Pi 4/5 (adventure_bot.py) → LLM → Response
                   |                        |
              Radio Only              Bot runs here
              (radio_gateway.py)      All game logic + LLM
```

> **Note:** Distributed mode components (radio_gateway.py for Pi Zero 2W) are planned 
> but not yet implemented. Currently, use standalone mode on Pi 4/5.

---

## Problem Statement

The **Raspberry Pi Zero 2W** (1GHz quad-core, 512MB RAM) is excellent for handling LoRa radio communication but lacks the compute power and memory for running the bot or LLMs. A distributed architecture solves this by separating radio I/O from bot logic and LLM processing.

---

## Recommended Distributed Architecture (Future)

```
┌──────────────────┐         Local Network (WiFi/Ethernet)         ┌─────────────────┐
│  Pi Zero 2W      │ ←────────────────────────────────────────────→ │  Pi 4/5         │
│  (Radio Gateway) │         HTTP REST API (Port 5000)              │  (Bot Server)   │
├──────────────────┤                                                 ├─────────────────┤
│ • LoRa Radio     │                                                 │ • adventure_bot │
│ • MeshCore       │                                                 │ • Ollama/LLM    │
│ • radio_gateway  │                                                 │ • Story Gen     │
│ • ~15MB RAM      │                                                 │ • SSD storage   │
└──────────────────┘                                                 └─────────────────┘
```

**Key Point:** The bot (adventure_bot.py) runs on Pi 4/5, NOT on Pi Zero 2W.

---

## Hardware Options for Bot Server (Pi 4/5 or PC)

### Option 1: Raspberry Pi 4/5 (8GB) ⭐ RECOMMENDED

**Specs:**
- 2.4GHz quad-core ARM Cortex-A76
- 8GB LPDDR4X-4267 RAM
- PCIe 2.0 x1 interface (for NVMe SSD)
- Dual 4K display output
- Active cooling available

**Pros:**
- ✅ Same ecosystem as Pi Zero (Raspberry Pi OS)
- ✅ Low power (~10W max)
- ✅ Can run Ollama with small models (llama3.2:1b, tinyllama)
- ✅ Affordable (~$80 for 8GB model)
- ✅ Good community support
- ✅ Easy networking with Pi Zero

**Cons:**
- ❌ Limited to small quantized models
- ❌ CPU-only inference (slower)
- ❌ 8GB max RAM limits model size

**Best For:** Budget-conscious deployments, small to medium models

**Current Standalone Setup (Pi 4/5 with USB LoRa):**
```bash
# On Pi 4/5 - runs the bot with radio connected via USB
sudo apt-get install -y python3-pip python3-serial python3-venv
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Connect LoRa radio via USB (/dev/ttyUSB0)
venv/bin/python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1

# Optional: Set up SSD for LLM storage
sudo mkdir -p /mnt/ssd
sudo mount /dev/sda1 /mnt/ssd
export OLLAMA_MODELS=/mnt/ssd/ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```

**Future Distributed Setup:**
```bash
# On Pi Zero 2W (radio gateway only)
python3 radio_gateway.py --bot-server-url http://pi5.local:5000

# On Pi 4/5 (bot server)
python3 adventure_bot.py --distributed-mode
```

---

### Option 2: Desktop PC (Ubuntu) ⭐ DEVELOPMENT

**Specs:**
- Any modern desktop/laptop with Ubuntu
- 8GB+ RAM recommended
- USB port for LoRa radio

**Pros:**
- ✅ Fast development iteration
- ✅ More powerful than Pi
- ✅ Easy debugging tools
- ✅ Can run larger models
- ✅ Same OS as Pi (Ubuntu/Debian-based)

**Cons:**
- ❌ Not portable
- ❌ Higher power consumption
- ❌ Not suitable for field deployment

**Best For:** Development, testing, and experimentation before Pi deployment

**Setup:**
```bash
# On Ubuntu desktop - same as Pi 4/5
sudo apt-get install -y python3-pip python3-serial python3-venv
git clone https://github.com/hostyorkshire/MCADV
cd MCADV
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Connect LoRa radio via USB and run
venv/bin/python3 adventure_bot.py --port /dev/ttyUSB0 --channel-idx 1 --debug
```

---

### Option 3: NVIDIA Jetson Nano/Orin Nano ⭐⭐ BEST PERFORMANCE

**Jetson Orin Nano 8GB Specs:**
- 6-core ARM Cortex-A78AE
- 8GB LPDDR5 RAM
- **1024-core NVIDIA Ampere GPU** (40 TOPS)
- PCIe Gen4, M.2 NVMe support

**Pros:**
- ✅ GPU acceleration for LLM inference (10-50x faster than CPU)
- ✅ Can run larger models (7B quantized, some 13B)
- ✅ TensorRT optimization for speed
- ✅ Low latency inference (<500ms)
- ✅ Built for AI workloads
- ✅ 20W power consumption

**Cons:**
- ❌ More expensive (~$250-500)
- ❌ Requires active cooling
- ❌ Different OS (Ubuntu/JetPack)

**Best For:** Production deployments, low latency requirements, larger models

**Current Standalone Setup:**
```bash
# On Jetson - runs bot with radio via USB
docker run -d -p 11434:11434 --gpus all ollama/ollama
ollama pull llama3.2:3b-instruct-q4_K_M

# Connect LoRa radio via USB
python3 adventure_bot.py --port /dev/ttyUSB0 --ollama-url http://localhost:11434
```

**Future Distributed Setup:**
```bash
# On Pi Zero 2W (radio gateway)
python3 radio_gateway.py --bot-server-url http://jetson.local:5000

# On Jetson (bot server)
python3 adventure_bot.py --distributed-mode
```

---

### Option 4: Mini PC / NUC ⭐⭐⭐ MAXIMUM POWER

**Intel NUC 13 Pro / AMD Ryzen Mini PC:**
- Intel Core i5/i7 or AMD Ryzen 5/7
- 16-32GB DDR4/DDR5 RAM
- NVMe SSD storage
- Optional: RTX 4060/4070 GPU

**Pros:**
- ✅ Can run any model size (up to 70B with quantization)
- ✅ Fast inference with CPU/GPU
- ✅ Lots of RAM for large contexts
- ✅ Standard x86 software compatibility
- ✅ Easy to upgrade

**Cons:**
- ❌ Higher power consumption (30-150W)
- ❌ More expensive (~$400-1500)
- ❌ Larger physical size
- ❌ Requires wall power

**Best For:** Home server, multiple bots, experimentation, maximum capability

---

### Option 4: Orange Pi 5 Plus / Rock 5B (Budget Alternative)

**Orange Pi 5 Plus Specs:**
- 8-core RK3588 (4x Cortex-A76 + 4x Cortex-A55)
- Up to 16GB RAM
- NPU with 6 TOPS
- PCIe 3.0 M.2 slot
- ~$150

**Pros:**
- ✅ More RAM than Pi 5 (up to 16GB)
- ✅ NPU for AI acceleration
- ✅ Better CPU performance than Pi 5
- ✅ Affordable
- ✅ Low power (~15W)

**Cons:**
- ❌ Less mature software ecosystem
- ❌ Ollama support varies
- ❌ Community support smaller

---

## Comparison Table

| Device | Price | RAM | Compute | Power | Storage | Best Use Case |
|--------|-------|-----|---------|-------|---------|---------------|
| **Ubuntu Desktop** | $0 | 8GB+ | Fast CPU/GPU | 50-300W | Built-in SSD | Development/testing |
| **Pi 4/5 8GB** | $80 | 8GB | CPU-only | 10W | USB SSD ($40) | Budget, standalone |
| **Jetson Orin Nano** | $250-500 | 8GB | GPU (1024 cores) | 20W | NVMe SSD | Production, low latency |
| **Mini PC (no GPU)** | $400-600 | 16-32GB | Fast CPU | 30-50W | NVMe SSD | Large models, multi-bot |
| **Mini PC (w/ GPU)** | $800-1500 | 16-32GB | RTX 4060+ | 100-150W | NVMe SSD | Maximum capability |
| **Orange Pi 5+** | $150 | 16GB | CPU+NPU | 15W | eMMC/NVMe | Budget alternative |

**Pi Zero 2W** ($15) is only used as a radio gateway in distributed mode (future feature).

---

## Recommended Configurations

### Configuration A: Development Setup ($0 - Use Existing PC)
```
Desktop PC running Ubuntu + LoRa radio via USB

Capabilities:
- Full bot testing on your desktop
- Fast iteration and debugging
- Any LLM model you can run
- Acts as Pi 4/5 substitute
- Easy migration to Pi later
```

### Configuration B: Standalone Pi Setup ($160 total)
```
Pi 4/5 8GB ($80) + USB SSD ($40) + LoRa radio via USB + Power supply ($20) + Case ($20)

Capabilities:
- Small models: llama3.2:1b, tinyllama
- Inference: 2-5 seconds per story
- Concurrent users: 5-10
- Power: ~12W total
- SSD storage for LLM models
- Bot runs directly on Pi 4/5
```

### Configuration C: Distributed Pi Setup (Future - $250 total)
```
Pi Zero 2W ($15) + Pi 4/5 8GB ($80) + USB SSD ($40) + Power supplies ($40) + Cases/cooling ($75)

Capabilities:
- Pi Zero 2W: Radio gateway only
- Pi 4/5: Bot + LLM server
- Small models: llama3.2:1b
- Inference: 2-5 seconds per story
- Scalable: Add more Pi Zero 2W nodes
- Total power: ~12W
```

### Configuration D: Distributed Jetson Setup (Future - $400 total)
```
Pi Zero 2W ($15) + Jetson Orin Nano 8GB ($250) + Power/accessories ($135)

Capabilities:
- Pi Zero 2W: Radio gateway only
- Jetson: Bot + GPU-accelerated LLM
- Medium models: llama3.2:3b, phi-3-mini
- Inference: 500ms-2s per story
- Concurrent users: 20-30
- Power: ~25W total
- GPU acceleration
```

### Configuration E: High-End Distributed Setup (Future - $650+ total)
```
Pi Zero 2W ($15) + Mini PC ($500+) + Accessories ($135+)

Capabilities:
- Pi Zero 2W: Radio gateway only
- Mini PC: Bot + powerful LLM
- Large models: llama3:8b, mistral:7b
- Inference: 300ms-1s per story
- Concurrent users: 50+
- Power: ~65W total
- Upgradeable
```

> **Note:** Configurations C, D, and E require distributed mode (radio_gateway.py) which 
> is not yet implemented. Currently use Configuration A or B.

---

## Network Setup

### Option 1: Direct WiFi Connection
```
Pi Zero 2W (WiFi) ←→ WiFi Router ←→ LLM Server (WiFi/Ethernet)

Setup:
1. Both devices on same network
2. Use .local hostnames (mDNS/Avahi)
3. Configure firewall if needed
```

### Option 2: Direct Ethernet Connection
```
Pi Zero 2W (USB Ethernet) ←→ Ethernet Cable ←→ LLM Server

Setup:
1. USB-to-Ethernet adapter for Pi Zero 2W
2. Static IP addresses (e.g., 192.168.2.1 and 192.168.2.2)
3. Direct connection (no router needed)
4. Lower latency, more reliable
```

### Option 3: Access Point Mode
```
Pi Zero 2W (WiFi Client) ←→ LLM Server (WiFi AP)

Setup:
1. LLM server creates WiFi access point
2. Pi Zero connects directly to it
3. Isolated network
4. Good for portable deployments
```

---

## Power Budget

### Battery Operation Options

**For portable/field deployment:**

| Setup | Power Draw | Battery Life (10,000mAh) |
|-------|-----------|--------------------------|
| Pi Zero + Pi 5 | ~12W | ~4-5 hours |
| Pi Zero + Jetson | ~25W | ~2 hours |
| Pi Zero + Mini PC | ~60W+ | <1 hour (not practical) |

**Recommended Battery:**
- **Anker PowerCore 26800mAh** ($60)
  - PD 30W output
  - Powers Pi Zero + Pi 5 for ~10 hours
  - Compact, portable

- **Jackery Explorer 240** ($200)
  - 240Wh (67,000mAh @ 3.6V)
  - AC outlet + USB-C PD
  - Powers any setup for hours/days

---

## Storage Recommendations

### Pi Zero 2W (Radio Gateway - Future)
- **Minimum:** 16GB microSD (Class 10)
- **Recommended:** 32GB microSD (UHS-1)
- Only stores logs and message queue (~100MB)
- No LLM storage needed

### Pi 4/5 or PC (Bot Server)
- **Minimum:** 64GB (can use microSD on Pi, but slower)
- **Recommended:** 256GB+ USB SSD (Pi) or NVMe SSD (PC)
- **Why SSD via USB for Pi?**
  - LLM models: 2-8GB per model
  - Fast storage = faster model loading (3-10x faster than microSD)
  - Better reliability than microSD for constant writes
  - Easy to upgrade storage capacity
- **Model sizes:**
  - llama3.2:1b: ~1.3GB
  - llama3.2:3b: ~2.0GB
  - llama3:8b: ~4.7GB
  - mistral:7b: ~4.1GB

**SSD Setup for Pi 4/5:**
```bash
# 1. Connect USB SSD to Pi
# 2. Format and mount
sudo mkdir -p /mnt/ssd
sudo mkfs.ext4 /dev/sda1
sudo mount /dev/sda1 /mnt/ssd

# 3. Add to /etc/fstab for auto-mount on boot
echo "/dev/sda1 /mnt/ssd ext4 defaults 0 2" | sudo tee -a /etc/fstab

# 4. Set Ollama to use SSD for models
echo "export OLLAMA_MODELS=/mnt/ssd/ollama" >> ~/.bashrc
source ~/.bashrc
```

### Desktop PC (Development)
- Use existing SSD/NVMe storage
- Store models in default location or custom path
- Typically much faster than Pi microSD or USB SSD

---

## Cooling Requirements

| Device | Cooling | Why |
|--------|---------|-----|
| Desktop PC | Built-in fans | Standard PC cooling |
| Pi Zero 2W | Passive heatsink | Light workload (radio only) |
| Pi 4/5 | Active fan (recommended) | Sustained CPU load for LLM |
| Jetson Orin | Active fan (required) | GPU heat dissipation |
| Mini PC | Built-in fans | High power components |

---

## Our Recommendations: 🏆 

### For Development: **Ubuntu Desktop PC**

**Why:**
1. ✅ Zero cost (use existing PC)
2. ✅ Fast development iteration
3. ✅ Easy debugging and testing
4. ✅ More powerful than Pi
5. ✅ Test before deploying to Pi
6. ✅ Same code runs on Pi later

### For Production (Standalone): **Raspberry Pi 4/5 (8GB) with USB SSD**

**Why:**
1. ✅ Complete standalone solution
2. ✅ Low power consumption (~10W)
3. ✅ Affordable (~$160 total)
4. ✅ Runs small models well
5. ✅ SSD for reliable LLM storage
6. ✅ Battery operation possible
7. ✅ Easy to set up and maintain

### For Production (Distributed - Future): **Pi Zero 2W + Pi 5**

**Why:**
1. ✅ Separates radio from compute
2. ✅ Pi Zero handles radio perfectly
3. ✅ Pi 5 runs bot with more resources
4. ✅ Scalable (multiple Pi Zeros → one Pi 5)
5. ✅ Same Raspberry Pi ecosystem
6. ✅ Low combined power (~12W)

### For Performance (Distributed - Future): **Pi Zero 2W + Jetson Orin Nano**

**Why:**
1. ✅ GPU acceleration (10-50x faster)
2. ✅ Low latency responses (<1s)
3. ✅ Better user experience
4. ✅ Can run larger models
5. ✅ Still relatively low power (~25W)

---

## Example Shopping Lists

### Scenario 1: Development Setup ($0 - $60)
Use your existing Ubuntu desktop PC for development and testing.

| Item | Price | Source | Notes |
|------|-------|--------|-------|
| Ubuntu Desktop PC | $0 | You have it | 8GB+ RAM recommended |
| LoRa MeshCore Radio | $50-60 | MeshCore project | Connect via USB |
| USB Cable | Included | - | For radio connection |
| **Total** | **$50-60** | | Ready to develop! |

### Scenario 2: Standalone Pi Setup ($160 - $210)
Pi 4/5 with LoRa radio directly connected via USB.

| Item | Price | Source | Notes |
|------|-------|--------|-------|
| Pi 4/5 (8GB) | $80 | Official retailers | Runs bot + LLM |
| USB SSD (256GB) | $40 | Amazon | For LLM model storage |
| LoRa MeshCore Radio | $50-60 | MeshCore project | Via USB |
| Power supply (USB-C 5V 3A) | $20 | Amazon | Official recommended |
| microSD card (32GB) | $10 | Amazon | For OS |
| Active cooler | $5 | Official | Keep Pi cool |
| Case | $15 | Amazon/3D print | Protection |
| **Total** | **$210-220** | | Complete standalone! |

### Scenario 3: Distributed Pi Setup (Future - $250 - $310)
Separate radio gateway and bot server.

| Item | Price | Source | Notes |
|------|-------|--------|-------|
| Pi Zero 2W | $15 | Adafruit/PiShop | Radio gateway only |
| Pi 4/5 (8GB) | $80 | Official retailers | Bot server |
| USB SSD (256GB) | $40 | Amazon | For Pi 4/5 LLM storage |
| LoRa MeshCore Radio | $50-60 | MeshCore project | Connects to Pi Zero |
| 2x Power supplies | $40 | Amazon | One for each Pi |
| 2x microSD cards (32GB) | $20 | Amazon | OS for both |
| Pi 5 active cooler | $5 | Official | For bot server |
| Cases | $30 | Amazon/3D print | Both Pis |
| **Total** | **$280-310** | | Distributed setup! |

**Optional:**
- USB Ethernet adapter ($15) - for direct connection between Pis
- Portable battery pack ($60) - for field use
- Longer USB cables ($10) - for flexible placement

---

## Deployment Scenarios

### Scenario 1: Development on Desktop PC
```
Setup: Ubuntu desktop + LoRa radio via USB
Bot runs: On your desktop (adventure_bot.py)
Network: Not needed (standalone)
Power: Wall power
Cost: ~$50-60 (just the radio)
Use: Development, testing, experimentation
```

### Scenario 2: Standalone Pi Production
```
Setup: Pi 4/5 (8GB) + USB SSD + LoRa radio via USB
Bot runs: On Pi 4/5 (adventure_bot.py)
Network: Optional (for Ollama LAN or cloud LLM)
Power: Wall power or battery
Cost: ~$210
Use: Production deployment, all-in-one unit
```

### Scenario 3: Portable Field Unit (Future)
```
Setup: Pi Zero 2W + Pi 4/5 in portable case
Bot runs: On Pi 4/5 (adventure_bot.py)
Radio: On Pi Zero 2W (radio_gateway.py)
Network: Direct WiFi or Ethernet between devices
Power: Battery pack
Cost: ~$340 (with battery)
Use: Field operations, portable events
```

### Scenario 4: Multiple Radio Nodes (Future)
```
Setup: 3x Pi Zero 2W + 1x Pi 4/5 (shared bot server)
Bot runs: On Pi 4/5 (adventure_bot.py)
Radio: On each Pi Zero 2W (radio_gateway.py)
Network: WiFi network connecting all devices
Power: Mixed (wall + battery)
Cost: ~$315 (economy of scale)
Use: Multi-location coverage, mesh expansion
```

---

## Next Steps

### For Development:
1. **Install on Ubuntu desktop** - Use existing PC
2. **Connect LoRa radio via USB** - /dev/ttyUSB0
3. **Follow installation guide** - See README.md
4. **Test and develop** - Iterate quickly
5. **Migrate to Pi when ready** - Same code!

### For Production:
1. **Choose hardware** based on budget and requirements
2. **Order components** from the shopping list
3. **Install on Pi 4/5** - Follow README.md installation section
4. **Set up USB SSD** - For LLM model storage
5. **Deploy and enjoy!** - Fast, responsive bot

### For Future Distributed Setup:
1. **Wait for radio_gateway.py** - Not yet implemented
2. **Use standalone mode** - Until distributed is ready
3. **Plan network layout** - WiFi or Ethernet
4. **Order Pi Zero 2W** - When feature is available

---

## Questions?

- **Q: Where does the bot run?**
  - A: **On Pi 4/5 or Ubuntu PC**, NOT on Pi Zero 2W. Pi Zero 2W only handles radio (future).

- **Q: Can I use my Ubuntu desktop for development?**
  - A: **Yes!** It acts exactly like Pi 4/5. Same code, same setup. Perfect for testing.

- **Q: Do I need an SSD?**
  - A: **Recommended for Pi 4/5**. LLM models load 3-10x faster. Use USB SSD on Pi.

- **Q: Can I use a Pi 4 instead of Pi 5?**
  - A: Yes! Pi 4 8GB works well. Slightly slower but still good.

- **Q: Do I need GPU for LLM?**
  - A: No, but it helps a lot. CPU-only works with small models on Pi 4/5.

- **Q: Can multiple Pi Zeros share one bot server?**
  - A: Yes! (Future feature) One Pi 4/5 can serve 3-5 Pi Zero 2W radio gateways.

- **Q: What about cloud LLM (OpenAI/Groq)?**
  - A: Still works! This setup gives you the option for local or cloud LLM.

- **Q: Can I upgrade later?**
  - A: Yes! Start with Pi 4/5, upgrade to Jetson/Mini PC later. Or start on Ubuntu desktop.

# Hardware Recommendations for Distributed MCADV Setup

## Problem Statement

The **Raspberry Pi Zero 2W** (1GHz quad-core, 512MB RAM) is excellent for handling LoRa radio communication but lacks the compute power and memory for running LLMs locally. A distributed architecture solves this by pairing the Pi Zero with a more powerful compute device.

---

## Recommended Distributed Architecture

```
┌──────────────────┐         Local Network (WiFi/Ethernet)         ┌─────────────────┐
│  Pi Zero 2W      │ ←────────────────────────────────────────────→ │  LLM Server     │
│  (Radio Gateway) │         HTTP REST API (Port 5000)              │  (Compute Node) │
├──────────────────┤                                                 ├─────────────────┤
│ • LoRa Radio     │                                                 │ • Ollama        │
│ • MeshCore       │                                                 │ • Story Gen     │
│ • Session Mgmt   │                                                 │ • Model Cache   │
│ • Message Parse  │                                                 │ • GPU (opt)     │
└──────────────────┘                                                 └─────────────────┘
```

---

## Hardware Options for LLM Server

### Option 1: Raspberry Pi 5 (8GB) ⭐ RECOMMENDED

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

**Example Setup:**
```bash
# On Pi 5
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
ollama serve

# On Pi Zero 2W
python3 radio_gateway.py --llm-server-url http://pi5.local:11434
```

---

### Option 2: NVIDIA Jetson Nano/Orin Nano ⭐⭐ BEST PERFORMANCE

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

**Example Setup:**
```bash
# On Jetson
docker run -d -p 11434:11434 --gpus all ollama/ollama
ollama pull llama3.2:3b-instruct-q4_K_M

# On Pi Zero 2W
python3 radio_gateway.py --llm-server-url http://jetson.local:11434
```

---

### Option 3: Mini PC / NUC ⭐⭐⭐ MAXIMUM POWER

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

| Device | Price | RAM | Compute | Power | Best Use Case |
|--------|-------|-----|---------|-------|---------------|
| **Pi 5 8GB** | $80 | 8GB | CPU-only | 10W | Budget, small models |
| **Jetson Orin Nano** | $250-500 | 8GB | GPU (1024 cores) | 20W | Production, low latency |
| **Mini PC (no GPU)** | $400-600 | 16-32GB | Fast CPU | 30-50W | Large models, multi-bot |
| **Mini PC (w/ GPU)** | $800-1500 | 16-32GB | RTX 4060+ | 100-150W | Maximum capability |
| **Orange Pi 5+** | $150 | 16GB | CPU+NPU | 15W | Budget alternative |

---

## Recommended Configurations

### Configuration A: Budget Setup ($160 total)
```
Pi Zero 2W ($15) + Pi 5 8GB ($80) + Power supplies ($30) + Case/cooling ($35)

Capabilities:
- Small models: llama3.2:1b, tinyllama
- Inference: 2-5 seconds per story
- Concurrent users: 5-10
- Power: ~12W total
```

### Configuration B: Balanced Setup ($350 total)
```
Pi Zero 2W ($15) + Jetson Orin Nano 8GB ($250) + Power/accessories ($85)

Capabilities:
- Medium models: llama3.2:3b, phi-3-mini
- Inference: 500ms-2s per story
- Concurrent users: 20-30
- Power: ~25W total
- GPU acceleration
```

### Configuration C: High-End Setup ($600+ total)
```
Pi Zero 2W ($15) + Mini PC ($500+) + Accessories ($85+)

Capabilities:
- Large models: llama3:8b, mistral:7b
- Inference: 300ms-1s per story
- Concurrent users: 50+
- Power: ~60W total
- Upgradeable
```

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

### Pi Zero 2W (Radio Gateway)
- **Minimum:** 16GB microSD (Class 10)
- **Recommended:** 32GB microSD (UHS-1)
- Only stores logs and sessions (~100MB)

### LLM Server
- **Minimum:** 64GB SSD/eMMC
- **Recommended:** 256GB+ NVMe SSD
- Model storage: 2-8GB per model
- Fast storage = faster model loading

---

## Cooling Requirements

| Device | Cooling | Why |
|--------|---------|-----|
| Pi Zero 2W | Passive heatsink | Light workload |
| Pi 5 | Active fan (recommended) | Sustained CPU load |
| Jetson Orin | Active fan (required) | GPU heat dissipation |
| Mini PC | Built-in fans | High power components |

---

## Our Recommendation: 🏆 

**For most users:** **Raspberry Pi 5 (8GB) + Pi Zero 2W**

**Why:**
1. ✅ Same Raspberry Pi ecosystem
2. ✅ Easy to set up and maintain
3. ✅ Low power consumption
4. ✅ Affordable (~$160 total)
5. ✅ Runs small models well
6. ✅ Expandable (add SSD, better cooling)
7. ✅ Battery operation possible

**For performance:** **Jetson Orin Nano + Pi Zero 2W**

**Why:**
1. ✅ GPU acceleration (10-50x faster)
2. ✅ Low latency responses
3. ✅ Better user experience
4. ✅ Can run larger models
5. ✅ Still relatively low power

---

## Example Shopping List (Budget Setup)

| Item | Price | Source |
|------|-------|--------|
| Pi Zero 2W | $15 | Adafruit/PiShop |
| Pi 5 8GB | $80 | Official retailers |
| 2x Power supplies (USB-C 5V 3A) | $30 | Amazon |
| 2x microSD cards (32GB) | $20 | Amazon |
| Pi 5 active cooler | $5 | Official |
| Cases | $20 | Amazon/3D print |
| **Total** | **~$170** | |

**Optional:**
- USB Ethernet adapter ($15) - for direct connection
- Portable battery pack ($60) - for field use
- NVMe SSD for Pi 5 ($40) - faster storage

---

## Deployment Scenarios

### Scenario 1: Home Server
```
Setup: Pi Zero 2W (near radio) + Pi 5 (server closet)
Network: WiFi or Ethernet
Power: Wall power
Cost: ~$170
```

### Scenario 2: Portable Field Unit
```
Setup: Pi Zero 2W + Pi 5 in portable case
Network: Direct WiFi or Ethernet
Power: Battery pack
Cost: ~$230 (with battery)
```

### Scenario 3: Multiple Radio Nodes
```
Setup: 3x Pi Zero 2W + 1x Pi 5 (shared)
Network: WiFi network
Power: Mixed (wall + battery)
Cost: ~$215 (economy of scale)
```

---

## Next Steps

1. **Choose hardware** based on budget and requirements
2. **Order components** from the shopping list
3. **Follow setup guide** (coming in next commit)
4. **Deploy distributed architecture**
5. **Enjoy fast, responsive bot!**

---

## Questions?

- **Q: Can I use a Pi 4 instead of Pi 5?**
  - A: Yes! Pi 4 8GB works well. Slightly slower but still good.

- **Q: Do I need GPU for LLM?**
  - A: No, but it helps a lot. CPU-only works with small models.

- **Q: Can multiple Pi Zeros share one LLM server?**
  - A: Yes! That's a great use case. One Pi 5 can serve 3-5 Pi Zeros.

- **Q: What about cloud LLM (OpenAI/Groq)?**
  - A: Still works! This setup gives you the option for local LLM.

- **Q: Can I upgrade later?**
  - A: Yes! Start with Pi 5, upgrade to Jetson/Mini PC later.

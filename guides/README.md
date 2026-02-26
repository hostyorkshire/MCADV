# MCADV Setup Guides

This directory contains comprehensive setup guides for various aspects of MCADV deployment and configuration.

## Available Guides

### 🚀 [Raspberry Pi Quick Start Guide](RASPBERRY_PI_QUICKSTART.md) ⭐ NEW
Complete step-by-step guide for setting up Raspberry Pi 5 and Pi Zero 2 from scratch with MCADV and Ollama.

**Topics covered:**
- Downloading and flashing Raspberry Pi OS Lite (64-bit)
- Initial Pi configuration (SSH, WiFi, static IP)
- USB SSD setup for model storage (Pi 5)
- Installing and configuring Ollama
- Downloading recommended models (llama3.2:1b, llama3.2:3b)
- Installing MCADV bot
- Auto-start configuration with systemd
- Testing and troubleshooting

**Recommended for:**
- New users starting from scratch
- Setting up Pi 5 as bot server with local Ollama
- Setting up Pi Zero 2 W as lightweight bot client
- Anyone wanting a complete, tested setup guide

### 📡 [Ollama Setup Guide](OLLAMA_SETUP.md)
Complete guide for setting up Ollama (local and LAN) for AI-powered story generation.

**Topics covered:**
- Local setup (same device)
- LAN setup (separate devices on network)
- Installation instructions for various platforms
- Model selection and recommendations
- Configuration examples
- Troubleshooting common issues
- Performance tuning
- Security considerations

**Recommended for:**
- Users wanting to run local AI models
- Distributed Pi Zero 2W + Pi 5 setups
- Users seeking privacy and complete offline operation (no internet required)
- Advanced Ollama configuration

---

## Coming Soon

Future guides will cover:
- **Distributed Architecture Setup** - Complete guide for Pi Zero 2W + LLM server configurations
- **LoRa Radio Configuration** - Optimizing MeshCore radio settings
- **Multi-Bot Deployments** - Running multiple bots on one network
- **Cloud LLM Setup** - Configuring OpenAI and Groq backends
- **Production Deployment** - Best practices for reliable field deployment

---

## Quick Links

- [Main README](../README.md)
- [Hardware Recommendations](../HARDWARE.md)
- [Performance Guide](../PERFORMANCE.md)
- [Repository Structure](../STRUCTURE.md)

---

## Contributing

Have suggestions for additional guides? Open an issue on GitHub!

https://github.com/hostyorkshire/MCADV/issues

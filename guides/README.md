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

### 🏗️ [Distributed Architecture Guide](DISTRIBUTED_ARCHITECTURE.md)
Complete documentation for Pi Zero 2W + LLM server configurations.

**Topics covered:**
- Overview of distributed architecture (radio gateway + bot server separation)
- Why use distributed mode (memory efficiency, scalability)
- Hardware requirements for each component
- Network setup (WiFi, static IPs, hostname resolution)
- Step-by-step setup for Pi Zero 2W as radio gateway
- Step-by-step setup for Pi 4/5/Jetson as bot server
- Configuration of the `--distributed-mode` flag and HTTP API routes
- Testing the setup end-to-end
- Systemd service configuration for both components
- Troubleshooting common issues

**Recommended for:**
- Users with Pi Zero 2W + Pi 4/5 hardware
- Deployments requiring LLM on separate hardware
- Anyone wanting lightweight radio gateway

### 📻 [LoRa Radio Configuration Guide](LORA_CONFIGURATION.md)
Optimizing MeshCore radio settings for better performance.

**Topics covered:**
- MeshCore protocol overview and binary protocol constants
- Serial port configuration (auto-detection, manual selection, baud rates)
- Channel configuration (channel index, multi-channel support)
- Message size limits and optimization (230 bytes max)
- Radio performance tuning and SNR monitoring
- Antenna considerations
- Range optimization tips
- Testing radio connectivity
- Debugging serial communication issues
- Common error messages and solutions

**Recommended for:**
- Users experiencing radio connectivity issues
- Anyone wanting to understand the MeshCore protocol
- Optimizing range and reliability

### 🤖 [Multi-Bot Deployments Guide](MULTI_BOT_DEPLOYMENTS.md)
Instructions for running multiple bots on one mesh network.

**Topics covered:**
- Why run multiple bots (coverage, redundancy, different themes/channels)
- Architecture options (multiple standalone vs shared bot server)
- Channel separation strategies (one bot per channel)
- Node ID configuration to prevent conflicts
- Shared bot server with multiple radio gateways (distributed mode)
- Session management across multiple bots
- Systemd service naming conventions
- Monitoring multiple bot instances
- Testing multi-bot setups
- Troubleshooting conflicts and issues

**Recommended for:**
- Events requiring coverage across multiple locations
- Deployments with multiple themed channels
- Advanced multi-instance setups

### ☁️ [Cloud LLM Setup Guide](CLOUD_LLM_SETUP.md)
Documentation for configuring OpenAI and Groq backends (alternative to Ollama).

**Topics covered:**
- Overview of cloud LLM options (OpenAI, Groq)
- Pros and cons vs local Ollama (cost, latency, internet dependency, privacy)
- Getting API keys for Groq (free tier) and OpenAI
- Configuration with `--groq-key` and `--openai-key` flags
- Model selection for each provider
- Cost estimates and usage limits
- API rate limiting and error handling
- Securing API keys (environment files)
- Testing cloud LLM connectivity
- Switching between Ollama and cloud LLMs

**Recommended for:**
- Pi Zero 2W deployments without a separate Pi 4/5
- Users who don't want to run local hardware
- Groq free tier for cost-free cloud AI

### 🚀 [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)
Best practices for reliable field deployment.

**Topics covered:**
- Pre-deployment checklist
- Hardware considerations (power, weatherproofing, cooling)
- Software configuration best practices
- Systemd service setup and auto-restart configuration
- Log management (rotation, monitoring, size limits)
- Resource monitoring (CPU, memory, disk, temperature)
- Backup and recovery procedures
- Session persistence across reboots
- Security hardening (firewall, SSH keys, user permissions)
- Remote monitoring and management
- Field testing procedures
- Maintenance schedule recommendations
- Update procedures (software updates, model updates)
- Battery power considerations
- Troubleshooting in the field

**Recommended for:**
- Anyone deploying MCADV at a live event
- Long-term / always-on installations
- Security-conscious deployments

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

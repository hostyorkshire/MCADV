# Migrating from Ubuntu Desktop to Raspberry Pi 5

This guide walks through migrating a working MCADV Bot Server from an Ubuntu Desktop (development) to a Raspberry Pi 5 (production).

## Prerequisites

Before starting:

- [ ] MCADV Bot Server running and tested on Ubuntu Desktop
- [ ] Integration tested with Pi Zero 2W Radio Gateway
- [ ] Raspberry Pi 5 (8 GB recommended) with Raspberry Pi OS installed
- [ ] Both devices on the same network

## Migration Steps

### 1. Backup Desktop Configuration

On the Ubuntu Desktop:

```bash
cd /path/to/MCADV
./scripts/backup_config.sh
# Creates: backup/mcadv_config_YYYYMMDD_HHMMSS.tar.gz
```

Note the backup file path shown.

### 2. Transfer Backup to Pi 5

```bash
# Replace pi5.local with your Pi 5's IP or hostname
scp backup/mcadv_config_*.tar.gz pi@pi5.local:~/
```

### 3. Set Up Pi 5

SSH into the Pi 5 and prepare the environment:

```bash
ssh pi@pi5.local

# Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip curl

# Clone repository
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV

# Restore configuration
./scripts/restore_config.sh ~/mcadv_config_*.tar.gz

# Run setup
./full_setup.sh
# Select: Bot Server
```

### 4. Install and Configure Ollama on Pi 5

```bash
curl -fsSL https://ollama.ai/install.sh | sh

# Re-pull models (listed during restore step)
ollama pull llama3.2:1b

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

> **Note for Pi 5:** The `llama3.2:1b` or `llama3.2:3b` model is recommended.
> Avoid `llama3.1:8b` unless you have the full 8 GB Pi 5 and are comfortable
> with 10–20 s per scene.

### 5. Test Pi 5 Setup

```bash
./scripts/pre_deployment_check.sh
./scripts/testing/test_bot_server.sh
```

### 6. Update Radio Gateway

On the Pi Zero 2W, update the bot server URL:

```bash
# Edit environment configuration
nano ~/.mcadv_config
# Change: BOT_SERVER_URL=http://pi5.local:5000

# Or set in .env
echo 'BOT_SERVER_URL=http://pi5.local:5000' >> .env
```

### 7. Test Integration

From the Radio Gateway:

```bash
./scripts/testing/test_network_connectivity.sh --bot-server pi5.local
./scripts/testing/test_radio_gateway.sh --bot-server pi5.local
```

From either device:

```bash
./scripts/testing/test_distributed_integration.sh --bot-server pi5.local
```

### 8. Decommission Desktop Bot Server

Once the Pi 5 is verified:

```bash
# On Ubuntu Desktop – stop the service
sudo systemctl stop mcadv-bot
sudo systemctl disable mcadv-bot

# Optional: keep desktop config as backup
./scripts/backup_config.sh --output ~/mcadv_desktop_backup
```

## Key Differences: Desktop vs Pi 5

| Aspect | Ubuntu Desktop | Raspberry Pi 5 |
|--------|---------------|----------------|
| Ollama model recommendation | `llama3.1:8b` | `llama3.2:1b` or `llama3.2:3b` |
| Story generation speed | 1–3 s/scene | 3–10 s/scene |
| Idle power | ~20 W | ~5 W |
| Battery operation | Not practical | ~8–10 hr on 25,000 mAh |
| Thermal management | Built-in | Active cooling fan recommended |
| Startup time | ~30 s | ~60 s |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Pi 5 unreachable after setup | Check Wi-Fi/Ethernet; use IP address instead of hostname |
| Ollama slow to respond | Use smaller model; check temperature with `monitor_power_temp.sh` |
| Radio gateway can't reach Pi 5 | Verify `BOT_SERVER_URL`; check firewall (`sudo ufw allow 5000/tcp`) |
| Config restore fails | Ensure backup was created with `backup_config.sh`; check tar.gz integrity |

## Rollback

If the Pi 5 setup fails, simply restart the desktop service:

```bash
# On Ubuntu Desktop
sudo systemctl start mcadv-bot
```

The Radio Gateway will resume using the desktop as the bot server.

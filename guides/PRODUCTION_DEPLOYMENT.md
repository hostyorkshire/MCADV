# Production Deployment Guide

**Quick reference guide for best practices for reliable field deployment.**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Hardware Considerations](#hardware-considerations)
5. [Software Configuration Best Practices](#software-configuration-best-practices)
6. [Systemd Service Setup](#systemd-service-setup)
7. [Log Management](#log-management)
8. [Resource Monitoring](#resource-monitoring)
9. [Session Persistence](#session-persistence)
10. [Security Hardening](#security-hardening)
11. [Backup and Recovery](#backup-and-recovery)
12. [Remote Monitoring and Management](#remote-monitoring-and-management)
13. [Field Testing Procedures](#field-testing-procedures)
14. [Update Procedures](#update-procedures)
15. [Battery Power Considerations](#battery-power-considerations)
16. [Maintenance Schedule](#maintenance-schedule)
17. [Performance Optimization](#performance-optimization)
18. [Troubleshooting in the Field](#troubleshooting-in-the-field)
19. [Testing and Deployment Scripts](#testing-and-deployment-scripts)
20. [Next Steps](#next-steps)

---

## Overview

This guide covers everything needed to deploy MCADV reliably in a production or field environment — from hardware setup and security hardening to log management and recovery procedures.

Production deployments differ from development setups in several key ways:
- The system must **auto-start** on boot and **recover from failures** automatically
- **Logs** must be managed to prevent disk exhaustion
- **Security** must be hardened against unauthorized access
- The system must be **remotely manageable** without physical access

---

## Prerequisites

- MCADV installed and tested locally (see [RASPBERRY_PI_QUICKSTART.md](RASPBERRY_PI_QUICKSTART.md))
- LLM backend decided (Ollama, Groq, OpenAI, or offline)
- Hardware provisioned and tested
- Network infrastructure in place

---

## Pre-Deployment Checklist

Use this checklist before taking a deployment to the field:

### Software

- [ ] MCADV cloned and virtual environment created
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Bot tested locally with `python3 adventure_bot.py --channel-idx 1`
- [ ] LLM backend configured and tested (Ollama, Groq, or OpenAI)
- [ ] Serial port detected correctly for LoRa radio
- [ ] Systemd service installed and tested: `sudo systemctl start mcadv_bot`
- [ ] Service survives a reboot: `sudo reboot && sudo systemctl status mcadv_bot`
- [ ] Logs directory exists and has write permissions: `ls -la ~/MCADV/logs/`

### Hardware

- [ ] Power supply rated correctly for the board
- [ ] LoRa radio connected and recognized: `ls /dev/ttyUSB*`
- [ ] Radio sends/receives messages (tested with MeshCore app)
- [ ] Storage has adequate free space: `df -h`
- [ ] Cooling is adequate for sustained operation (Pi 5 needs active cooling)
- [ ] Enclosure and cable management complete

### Network

- [ ] Device has a stable IP address (static recommended)
- [ ] SSH access confirmed from remote machine
- [ ] Internet access (if using Groq/OpenAI): `curl https://api.groq.com`
- [ ] Firewall rules configured (SSH allowed, unnecessary ports blocked)

### Security

- [ ] Default `pi` password changed (if applicable)
- [ ] SSH key authentication configured
- [ ] API keys stored securely (not hardcoded in service file)
- [ ] Firewall enabled: `sudo ufw status`

---

## Hardware Considerations

### Power Supply

Insufficient power causes random crashes and data corruption.

| Hardware | Required Power Supply |
|----------|-----------------------|
| Pi Zero 2W | 5V 2.5A micro-USB |
| Pi 4 (4GB) | 5V 3A USB-C |
| Pi 5 (8GB) | 5V 5A USB-C (official 27W) |
| Jetson Orin Nano | 5V 4A barrel jack (DC) |

**Field power tips:**
- Use the **official Raspberry Pi power supplies** — third-party supplies often underdeliver
- For events, use a dedicated power strip/UPS (uninterruptible power supply)
- A mini UPS provides 5–30 minutes of backup power during outages

### Weatherproofing

For outdoor deployments:

- Use an **IP65-rated enclosure** for full weather protection
- Mount the LoRa antenna **outside** the enclosure for best RF performance
- Use cable glands for waterproof cable pass-throughs
- Include silica gel desiccant sachets to manage internal humidity
- Orient the enclosure with ventilation holes facing downward to prevent rain entry

### Thermal Management

| Hardware | Idle Temp | Load Temp | Action at >80°C |
|----------|-----------|-----------|-----------------|
| Pi Zero 2W | 40–50°C | 60–70°C | CPU throttles |
| Pi 4 | 45–55°C | 65–80°C | CPU throttles |
| Pi 5 | 50–60°C | 70–85°C | CPU throttles; active cooling essential |

For Pi 5 in a sealed enclosure, use an **active cooler** (official or third-party fan case). Thermal throttling causes slow LLM responses.

Check temperature:

```bash
vcgencmd measure_temp       # Raspberry Pi
cat /sys/class/thermal/thermal_zone0/temp  # General Linux (divide by 1000)
```

### Storage

| Use Case | Minimum Storage | Recommended |
|----------|----------------|-------------|
| Offline stories only | 8GB microSD | 16GB |
| With Ollama (small model) | 32GB | 64GB USB SSD |
| With Ollama (large model) | 64GB | 256GB USB SSD |

For Pi 5 with Ollama: store models on a **USB SSD** (3–10× faster than microSD for model loading).

---

## Software Configuration Best Practices

### Use a Dedicated User

Run MCADV as a dedicated user with limited privileges (not root):

```bash
sudo useradd -m -s /bin/bash mcadv
sudo usermod -a -G dialout mcadv  # Serial port access
```

### Fix File Permissions

```bash
# MCADV directory owned by service user
sudo chown -R mcadv:mcadv /home/mcadv/MCADV

# Logs directory writable
chmod 755 /home/mcadv/MCADV/logs

# Session file accessible only by service user
chmod 600 /home/mcadv/MCADV/adventure_sessions.json
```

### Use an Environment File for Secrets

Never store API keys in the service ExecStart line. Use an environment file:

```bash
sudo mkdir -p /etc/mcadv
sudo nano /etc/mcadv/secrets.env
```

Content:

```
GROQ_API_KEY=gsk_YOUR_KEY
OPENAI_API_KEY=sk-YOUR_KEY
```

```bash
sudo chmod 600 /etc/mcadv/secrets.env
sudo chown mcadv:mcadv /etc/mcadv/secrets.env
```

### Configure for Your Use Case

Choose the configuration that matches your deployment:

```bash
# Pure offline (no internet required, minimal resources)
python3 adventure_bot.py --channel-idx 1 --announce

# With local Ollama (Pi 4/5 recommended)
python3 adventure_bot.py \
  --channel-idx 1 \
  --ollama-url http://localhost:11434 \
  --model llama3.2:1b \
  --announce

# With Groq cloud LLM
python3 adventure_bot.py \
  --channel-idx 1 \
  --groq-key $GROQ_API_KEY \
  --model llama-3.1-8b-instant \
  --announce

# Distributed mode (gateway + bot server)
python3 adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --ollama-url http://localhost:11434 \
  --model llama3.2:1b
```

---

## Systemd Service Setup

### Complete Production Service File

Create `/etc/systemd/system/mcadv_bot.service`:

> **Note:** Replace `User=pi` and `Group=pi` with your actual username, or use `mcadv` if you created a dedicated user as described in [Use a Dedicated User](#use-a-dedicated-user) above.

```ini
[Unit]
Description=MCADV Adventure Bot
Documentation=https://github.com/hostyorkshire/MCADV
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/MCADV

# Load secrets from environment file (API keys, etc.)
EnvironmentFile=-/etc/mcadv/secrets.env

ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --channel-idx 1 \
  --announce

# Restart policy: restart on any non-zero exit
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=60

# Output to journal (use: journalctl -u mcadv_bot -f)
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mcadv_bot

# Resource limits
# Adjust MemoryMax based on your configuration:
#   Offline (no LLM): 256M is sufficient
#   With Groq/OpenAI: 256M is sufficient
#   With local Ollama: Remove or increase to 2G+
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

Key production settings:

| Setting | Value | Purpose |
|---------|-------|---------|
| `Restart=on-failure` | always | Auto-restart on crash |
| `RestartSec=10` | 10s | Wait before restarting |
| `StartLimitBurst=5` | 5 | Max 5 restarts in 60s (prevents restart loop) |
| `MemoryMax=512M` | 512MB | Prevent memory leak crashes |
| `CPUQuota=80%` | 80% | Leave CPU headroom for OS |

### Install and Enable the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcadv_bot
sudo systemctl start mcadv_bot
sudo systemctl status mcadv_bot
```

### Verify Auto-Start on Boot

```bash
sudo reboot
# After reboot:
sudo systemctl status mcadv_bot
# Should show: active (running)
```

---

## Log Management

MCADV uses rotating log files configured in `logging_config.py`:

| Log File | Max Size | Backups | Total |
|----------|----------|---------|-------|
| `logs/meshcore.log` | 5MB | 3 | 20MB |
| `logs/errors.log` | 5MB | 3 | 20MB |

This keeps total log usage under **40MB** indefinitely — suitable for all storage configurations.

### Monitor Log Size

```bash
# Check log directory size
du -sh ~/MCADV/logs/

# List log files with sizes
ls -lh ~/MCADV/logs/
```

### View Logs

```bash
# Real-time (most recent activity)
tail -f ~/MCADV/logs/meshcore.log

# Errors only
tail -f ~/MCADV/logs/errors.log

# Systemd journal (includes stdout/stderr)
sudo journalctl -u mcadv_bot -f

# Last 100 lines of journal
sudo journalctl -u mcadv_bot -n 100

# Logs from today
sudo journalctl -u mcadv_bot --since today
```

### Journald Size Limit

Prevent systemd journal from growing too large:

```bash
sudo nano /etc/systemd/journald.conf
```

Add or uncomment:

```ini
[Journal]
SystemMaxUse=50M
SystemMaxFileSize=10M
RuntimeMaxUse=20M
```

```bash
sudo systemctl restart systemd-journald
```

---

## Resource Monitoring

### Quick Resource Check

```bash
# CPU and memory overview
htop

# Or without htop installed
top

# Memory breakdown
free -h

# Disk usage
df -h

# Network activity
ifstat  # or ip -s link
```

### MCADV-Specific Metrics

```bash
# Memory usage of the bot process
ps aux | grep adventure_bot | grep -v grep | awk '{print "CPU:", $3"%", "MEM:", $4"%", "RSS:", $6"KB"}'

# Check if bot is responsive (distributed mode)
curl -s http://localhost:5000/health && echo " - OK" || echo " - FAILED"

# Count active sessions
grep -c '"active"' ~/MCADV/adventure_sessions.json 2>/dev/null || echo "0 sessions"
```

### Automated Monitoring Script

Create `/home/pi/monitor_mcadv.sh`:

```bash
#!/bin/bash
LOG=/home/pi/mcadv_monitor.log
echo "$(date '+%Y-%m-%d %H:%M:%S') - MCADV Health Check" >> $LOG

# Check service status
if ! systemctl is-active --quiet mcadv_bot; then
    echo "$(date) WARNING: mcadv_bot is not running - restarting" >> $LOG
    sudo systemctl restart mcadv_bot
fi

# Log resource usage
MEM=$(free -m | awk '/Mem:/{print $3"/"$2"MB"}')
CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
DISK=$(df -h / | awk 'NR==2{print $5}')
TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 || echo "N/A")

echo "$(date '+%Y-%m-%d %H:%M:%S') - MEM:$MEM CPU:${CPU}% DISK:$DISK TEMP:$TEMP" >> $LOG
```

Add to cron (every 5 minutes):

```bash
crontab -e
# Add:
*/5 * * * * /home/pi/monitor_mcadv.sh
```

---

## Session Persistence

MCADV automatically saves sessions to `adventure_sessions.json`. Sessions survive:
- Bot restarts
- Service restarts
- System reboots

Sessions are **loaded on startup** and **saved every 5 seconds** (batched I/O for efficiency).

### Verify Session Persistence

```bash
# Start a session (via LoRa or HTTP test)
# ...

# Stop the bot
sudo systemctl stop mcadv_bot

# Check sessions were saved
cat ~/MCADV/adventure_sessions.json | python3 -m json.tool | head -20

# Restart the bot - sessions should be restored
sudo systemctl start mcadv_bot
```

### Session File Backup

Schedule automatic session backups:

```bash
crontab -e
# Daily backup at 02:00
0 2 * * * cp ~/MCADV/adventure_sessions.json ~/backups/sessions_$(date +\%Y\%m\%d).json
# Keep only last 7 days
0 3 * * * find ~/backups/ -name 'sessions_*.json' -mtime +7 -delete
```

---

## Security Hardening

### Change Default Password

```bash
passwd  # Change pi or current user password
```

### SSH Key Authentication

On your management laptop, generate a key pair if you don't have one:

```bash
ssh-keygen -t ed25519 -C "mcadv-management"
```

Copy public key to the Pi:

```bash
ssh-copy-id pi@192.168.1.50
```

Disable password authentication on the Pi:

```bash
sudo nano /etc/ssh/sshd_config
# Set:
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```

```bash
sudo systemctl restart sshd
```

### Firewall Configuration

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (management)
sudo ufw allow ssh

# Allow bot server HTTP port (distributed mode only)
sudo ufw allow 5000/tcp

# Check rules
sudo ufw status verbose
```

### Disable Unnecessary Services

```bash
# List enabled services
sudo systemctl list-unit-files --state=enabled

# Disable Bluetooth (if not needed)
sudo systemctl disable bluetooth

# Disable Avahi/mDNS (if not needed)
sudo systemctl disable avahi-daemon
```

### Keep Software Updated

```bash
# Update OS packages
sudo apt update && sudo apt upgrade -y

# Update MCADV
cd ~/MCADV && git pull

# Update Python dependencies
source venv/bin/activate && pip install -r requirements.txt
```

---

## Backup and Recovery

### What to Back Up

| Item | Location | Frequency |
|------|----------|-----------|
| Session data | `~/MCADV/adventure_sessions.json` | Daily |
| Config customizations | `~/MCADV/` | After changes |
| Systemd service files | `/etc/systemd/system/mcadv_*.service` | After changes |
| API key secrets | `/etc/mcadv/secrets.env` | Encrypted, after changes |
| SSH keys | `~/.ssh/` | One-time |

### Full Backup Script

Create `/home/pi/backup_mcadv.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/home/pi/backups/$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Session data
cp ~/MCADV/adventure_sessions.json $BACKUP_DIR/ 2>/dev/null

# Service files
sudo cp /etc/systemd/system/mcadv_*.service $BACKUP_DIR/ 2>/dev/null
sudo cp /etc/systemd/system/radio_gateway*.service $BACKUP_DIR/ 2>/dev/null

echo "Backup saved to $BACKUP_DIR"
```

### Recovery Procedure

If the bot fails to start after an update or error:

```bash
# 1. Check what's failing
sudo journalctl -u mcadv_bot -n 50

# 2. Common fix: restore session file from backup
cp ~/backups/LATEST/adventure_sessions.json ~/MCADV/adventure_sessions.json

# 3. Or clear corrupted session file
rm ~/MCADV/adventure_sessions.json

# 4. Restart
sudo systemctl restart mcadv_bot
sudo systemctl status mcadv_bot
```

---

## Remote Monitoring and Management

### SSH Access

```bash
ssh pi@192.168.1.50
# or using hostname
ssh pi@pi5bot.local
```

### Remote Log Tailing

```bash
# View logs remotely
ssh pi@192.168.1.50 "sudo journalctl -u mcadv_bot -f"
ssh pi@192.168.1.50 "tail -f ~/MCADV/logs/meshcore.log"
```

### Remote Restart

```bash
ssh pi@192.168.1.50 "sudo systemctl restart mcadv_bot"
```

### LTE/Cellular for Remote Access (Advanced)

For deployments without WiFi, a USB LTE stick provides remote SSH access:

```bash
# Install ModemManager
sudo apt install modemmanager network-manager -y

# Check LTE modem is detected
sudo mmcli -L

# Configure APN
sudo nmcli connection add type gsm ifname '*' \
  apn YOUR_APN_HERE connection.id lte-connection
```

This lets you SSH into the Pi over cellular when the event WiFi is unreliable.

---

## Field Testing Procedures

Run these tests before going live at an event:

### Pre-Event Test (Day Before)

```bash
# 1. Verify service is running
sudo systemctl status mcadv_bot

# 2. Check memory usage
free -h

# 3. Check disk space
df -h

# 4. Check logs for errors
sudo journalctl -u mcadv_bot -n 50 | grep -i error

# 5. Test radio (send message from MeshCore app, verify response)

# 6. Test LLM (send "start" and verify AI response)
```

### Load Test (Simulate Multiple Players)

```bash
# Send 10 rapid messages to the bot server (distributed mode)
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:5000/message \
    -H "Content-Type: application/json" \
    -d "{\"sender\": \"player$i\", \"content\": \"start\", \"channel_idx\": 1}" &
done
wait

# Check response times and errors in logs
sudo journalctl -u mcadv_bot -n 50
```

### Network Reliability Test

```bash
# Test connectivity to LLM backend
curl -s http://localhost:11434/api/tags | python3 -m json.tool  # Ollama
curl -s https://api.groq.com/ | head                             # Groq
```

### Restart Recovery Test

```bash
# Kill the bot abruptly
sudo systemctl kill -s SIGKILL mcadv_bot

# Verify it restarts automatically
sleep 15
sudo systemctl status mcadv_bot  # Should show: active (running)
```

---

## Update Procedures

### MCADV Software Update

```bash
# Stop the service
sudo systemctl stop mcadv_bot

# Pull latest changes
cd ~/MCADV && git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart the service
sudo systemctl start mcadv_bot
sudo systemctl status mcadv_bot
```

### Ollama Model Update

```bash
# Pull updated model
ollama pull llama3.2:1b

# Restart bot to use new model
sudo systemctl restart mcadv_bot
```

### OS Security Updates

```bash
# Install security updates only
sudo apt update
sudo apt upgrade -y

# Full dist-upgrade (more changes)
sudo apt full-upgrade -y
sudo reboot
```

### Rollback if Something Breaks

```bash
# Revert to previous MCADV version
cd ~/MCADV
git log --oneline -10  # Find the commit to roll back to
git checkout COMMIT_HASH

# Restart service
sudo systemctl restart mcadv_bot
```

---

## Battery Power Considerations

For off-grid deployments powered by batteries or solar:

### Power Consumption

| Device | Idle | Under Load |
|--------|------|-----------|
| Pi Zero 2W | 0.4W | 1.4W |
| Pi 4 (4GB) | 3W | 7W |
| Pi 5 (8GB) | 4W | 12W |
| LoRa radio (USB) | 0.5W | 1W |

### Battery Sizing

For a **12-hour event** using Pi Zero 2W (1.5W average with radio):

```
1.5W × 12h = 18 Wh
Battery needed: 18 Wh ÷ 0.8 (efficiency) = 22.5 Wh
A 10,000 mAh power bank (37 Wh) gives >16 hours with margin
```

For **Pi 4 with Ollama** (10W average):

```
10W × 12h = 120 Wh
Battery needed: 120 Wh ÷ 0.8 = 150 Wh
Use a 20,000+ mAh power bank or small LiFePO4 battery
```

### Graceful Shutdown on Low Battery

Install `ups-lite` or similar battery monitoring. For a UPS HAT:

```bash
# Install monitoring script
pip install smbus2

# Create /etc/cron.d/battery-check
* * * * * root /home/pi/check_battery.sh
```

Sample `check_battery.sh`:

```bash
#!/bin/bash
VOLTAGE=$(cat /sys/class/power_supply/BAT0/voltage_now 2>/dev/null)
if [ ! -z "$VOLTAGE" ] && [ $VOLTAGE -lt 3500000 ]; then
    echo "Low battery, shutting down..."
    sudo systemctl stop mcadv_bot
    sync
    sudo poweroff
fi
```

### Solar Power

For permanent outdoor installations:

- **Pi Zero 2W:** 5W solar panel + 10,000 mAh LiFePO4 battery
- **Pi 4/5:** 20W solar panel + 20,000 mAh LiFePO4 battery
- Use a solar charge controller (e.g., CN3791) between panel and battery

---

## Maintenance Schedule

### Daily (Automated)

- Session file backup (via cron)
- Health check and auto-restart (via cron or systemd watchdog)
- Log size check

### Weekly (Manual)

```bash
# Review logs for errors
sudo journalctl -u mcadv_bot --since "7 days ago" | grep -i error

# Check disk space
df -h

# Check for OS updates
sudo apt update && apt list --upgradable
```

### Monthly (Manual)

```bash
# Apply OS security updates
sudo apt upgrade -y

# Pull latest MCADV changes
cd ~/MCADV && git pull && pip install -r requirements.txt

# Review and rotate API keys

# Test backup and recovery procedure
```

### After Events

```bash
# Archive session data
cp ~/MCADV/adventure_sessions.json ~/archives/sessions_EVENT_$(date +%Y%m%d).json

# Review logs for performance issues
grep "response time" ~/MCADV/logs/meshcore.log | tail -100

# Update documentation with lessons learned
```

---

## Performance Optimization

See [PERFORMANCE.md](../PERFORMANCE.md) for detailed optimization tips. Key production optimizations:

### Memory

```bash
# Check memory at peak load
free -h

# If memory is tight, use a smaller model
--model llama3.2:1b   # instead of llama3.2:3b
```

### Disk I/O

MCADV batches session saves every 5 seconds to minimize disk writes — this is already optimized for microSD longevity.

### Startup Time

```bash
# Measure startup time
time python3 adventure_bot.py --channel-idx 1 --no-announce &
# Expected: <2 seconds
```

### LLM Response Time

| Backend | Typical Response Time |
|---------|----------------------|
| Offline | <10ms |
| Ollama (llama3.2:1b on Pi 4) | 2–5s |
| Ollama (llama3.2:1b on Pi 5) | 1–3s |
| Groq cloud | 1–3s |
| OpenAI cloud | 1–5s |

---

## Troubleshooting in the Field

### Bot Not Responding to Messages

```bash
# Check service status
sudo systemctl status mcadv_bot

# Check for errors
sudo journalctl -u mcadv_bot -n 50

# Restart if needed
sudo systemctl restart mcadv_bot
```

### Serial Port Issues (Radio Not Connecting)

```bash
# Check if radio is detected
ls /dev/ttyUSB* /dev/ttyACM*

# Reconnect USB cable, then
sudo systemctl restart mcadv_bot
```

### Out of Memory

```bash
# Check memory
free -h

# Kill memory-hungry processes
sudo systemctl stop ollama  # Temporarily free memory

# Use smaller model going forward
```

### Disk Full

```bash
# Check what's using space
du -sh ~/MCADV/logs/* /var/log/ ~/.ollama/models/

# Clear old logs
sudo journalctl --vacuum-size=50M

# Delete old session backups
find ~/backups/ -name '*.json' -mtime +7 -delete
```

### LLM API Down (Cloud)

MCADV falls back to offline story trees automatically. Confirm:

```bash
# Check logs for fallback message
sudo journalctl -u mcadv_bot | grep -i "fallback\|offline\|error"
```

Players will continue to receive responses from the built-in story trees.

---

## Testing and Deployment Scripts

MCADV includes a comprehensive set of scripts to simplify deployment and testing.

### Quick Setup Verification

Run the full setup check before any deployment:

```bash
./scripts/setup_check.sh
```

This verifies all 11 prerequisites in one command.

### Guided First-Time Setup

For new installations, use the interactive wizard:

```bash
./scripts/quick_start.sh
```

This walks you through every setup step with prompts.

### Testing Scripts

| Script | Purpose |
|--------|---------|
| `scripts/testing/test_hardware.sh` | Detect and test LoRa radio |
| `scripts/testing/test_ollama.sh` | Test Ollama connectivity and models |
| `scripts/testing/test_bot_integration.sh` | End-to-end bot functionality test |
| `scripts/testing/field_test_monitor.sh` | Live tmux monitoring dashboard |

See [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md) for full testing documentation.

### Systemd Service Installation

Install and manage the bot as a systemd service:

```bash
# Install the service
sudo ./scripts/deployment/install_service.sh

# Manage the service interactively
./scripts/deployment/manage_service.sh

# Set up log rotation
sudo ./scripts/deployment/setup_logrotate.sh
```

The service template at `scripts/deployment/mcadv-bot.service` uses:
- `Restart=always` with 10s delay
- `MemoryHigh=1800M` (soft limit, no hard kills)
- `CPUQuota=80%`
- Log files in `logs/systemd_output.log` and `logs/systemd_error.log`

### Monitoring Scripts

| Script | Purpose |
|--------|---------|
| `scripts/monitoring/monitor_bot.sh` | Real-time status dashboard |
| `scripts/monitoring/tune_performance.sh` | Hardware-specific recommendations |
| `scripts/monitoring/check_resources.sh` | Cron-friendly health check |
| `scripts/monitoring/alert_config.sh.example` | Alert configuration template |

Run the dashboard:

```bash
# Run once
./scripts/monitoring/monitor_bot.sh --once

# Auto-refresh every 30 seconds
./scripts/monitoring/monitor_bot.sh
```

Set up automated health checks:

```bash
crontab -e
# Add:
*/5 * * * * /path/to/MCADV/scripts/monitoring/check_resources.sh >> /dev/null 2>&1
```

### Log Rotation Setup

Prevent log files from filling disk:

```bash
sudo ./scripts/deployment/setup_logrotate.sh
```

This configures daily rotation with 7 days retention and compression.

---

## Next Steps

- Distributed architecture setup: [DISTRIBUTED_ARCHITECTURE.md](DISTRIBUTED_ARCHITECTURE.md)
- Running multiple bots: [MULTI_BOT_DEPLOYMENTS.md](MULTI_BOT_DEPLOYMENTS.md)
- Cloud LLM options: [CLOUD_LLM_SETUP.md](CLOUD_LLM_SETUP.md)
- Performance tuning: [PERFORMANCE.md](../PERFORMANCE.md)
- Hardware selection: [HARDWARE.md](../HARDWARE.md)
- Testing guide: [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)
- Field testing: [docs/FIELD_TESTING.md](../docs/FIELD_TESTING.md)

---

## Quick Links

- [Main README](../README.md)
- [Other Guides](README.md)
- [Hardware Guide](../HARDWARE.md)
- [Performance Guide](../PERFORMANCE.md)
- [Testing Guide](../docs/TESTING_GUIDE.md)

---

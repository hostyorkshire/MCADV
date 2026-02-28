# MCADV Testing Guide

Testing MCADV before deployment ensures reliability during actual events.

## Pre-Deployment Testing

### 1. Hardware Testing

**Script:** `scripts/testing/test_hardware.sh`

**What it checks:**
- Auto-detects LoRa radios on `/dev/ttyUSB*` and `/dev/ttyACM*`
- Tests serial port read/write accessibility
- Verifies baud rate compatibility (9600, 115200, 230400)
- Displays device vendor/model information

**When to run:** Before first deployment, after hardware changes, after USB reconnection.

```bash
./scripts/testing/test_hardware.sh
```

**Exit codes:** `0` = success, `1` = warnings, `2` = no radios found

---

### 2. Ollama Testing

**Script:** `scripts/testing/test_ollama.sh`

**What it checks:**
- Ollama connectivity on `localhost:11434`
- Available models and disk space
- RAM availability with model recommendations
- Story generation with a sample prompt

**When to run:** Before first deployment, after model changes, after Ollama updates.

```bash
./scripts/testing/test_ollama.sh

# Test with a specific model
./scripts/testing/test_ollama.sh --model llama3.2:1b

# Test against a remote Ollama instance
./scripts/testing/test_ollama.sh --url http://192.168.1.50:11434
```

**Exit codes:** `0` = success, `1` = warnings, `2` = Ollama unreachable

---

### 3. Integration Testing

**Script:** `scripts/testing/test_bot_integration.sh`

**What it checks:**
- Bot HTTP API connectivity
- `!help` command response
- `!adv` command (adventure start)
- Numeric choice responses
- Session persistence (`adventure_sessions.json`)
- Collaborative mode (multiple users on same channel)
- `!reset` command

**When to run:** Before each deployment, after code changes.

**Prerequisite:** Bot must be running in distributed mode:

```bash
# Start bot in test mode first
source venv/bin/activate
python3 adventure_bot.py --distributed-mode --http-port 5000 &

# Then run integration tests
./scripts/testing/test_bot_integration.sh
```

**Exit codes:** `0` = all passed, `1` = some failures

---

### 4. Field Testing Monitor

**Script:** `scripts/testing/field_test_monitor.sh`

**What it does:**
- Launches a tmux 4-pane dashboard:
  - Pane 1: Live `adventure_bot.log` tail
  - Pane 2: Live `meshcore.log` tail
  - Pane 3: Resource monitor (memory, disk, CPU)
  - Pane 4: Active sessions display

**When to run:** During user acceptance testing and live events.

```bash
./scripts/testing/field_test_monitor.sh
```

**Controls:**
| Key | Action |
|-----|--------|
| `Ctrl+B, arrow keys` | Navigate between panes |
| `Ctrl+B, d` | Detach (keep monitoring) |
| `Ctrl+B, &` | Kill session |

To re-attach: `tmux attach -t mcadv-monitor`

**Requirements:** `tmux` must be installed (`sudo apt install tmux`)

---

## Field Testing Checklist

Use this checklist before each deployment:

### Software Checks
- [ ] Run `scripts/setup_check.sh` — all 11 checks pass
- [ ] Run `scripts/testing/test_hardware.sh` — radio detected
- [ ] Run `scripts/testing/test_ollama.sh` — models available
- [ ] Bot starts without errors in test run
- [ ] `!help` responds with command list
- [ ] `!adv` starts an adventure
- [ ] Numeric choices advance the story

### Hardware Checks
- [ ] LoRa radio detected: `ls /dev/ttyUSB* /dev/ttyACM*`
- [ ] Radio receives messages (tested with MeshCore app)
- [ ] Power supply adequate for hardware
- [ ] Cooling sufficient (Pi 5: active cooling required)
- [ ] Storage has 10GB+ free space

### Production Checks
- [ ] Systemd service installed and running
- [ ] Logs directory writable
- [ ] Session file backup configured
- [ ] Log rotation configured

---

## Troubleshooting Common Issues

### Bot Not Responding to LoRa Messages

```bash
# Check radio detection
ls /dev/ttyUSB* /dev/ttyACM*

# Check serial permissions
ls -la /dev/ttyUSB0
# If needed: sudo usermod -aG dialout $USER

# Run hardware test
./scripts/testing/test_hardware.sh

# Check bot logs
tail -50 logs/meshcore.log
```

### Ollama Story Generation Fails

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check available models
ollama list

# Pull recommended model
ollama pull llama3.1:8b

# Run Ollama test
./scripts/testing/test_ollama.sh
```

### Integration Tests Failing

```bash
# Ensure bot is running in distributed mode
python3 adventure_bot.py --distributed-mode --http-port 5000

# Check bot health endpoint
curl http://localhost:5000/api/health

# Check for errors
tail -50 logs/adventure_bot.log
```

### High Memory Usage

```bash
# Check current memory
free -h

# Run performance tuner
./scripts/monitoring/tune_performance.sh

# Use a smaller model
./scripts/testing/test_ollama.sh --model llama3.2:1b
```

---

## Automated Health Monitoring

Set up continuous monitoring with cron:

```bash
crontab -e
# Add (runs every 5 minutes):
*/5 * * * * /path/to/MCADV/scripts/monitoring/check_resources.sh >> /dev/null 2>&1
```

Configure alerts in `scripts/monitoring/alert_config.sh.example`:

```bash
cp scripts/monitoring/alert_config.sh.example scripts/monitoring/alert_config.sh
nano scripts/monitoring/alert_config.sh
```

---

## Quick Reference

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `scripts/setup_check.sh` | Full setup verification | Before deployment |
| `scripts/testing/test_hardware.sh` | LoRa radio test | Hardware changes |
| `scripts/testing/test_ollama.sh` | Ollama + models test | Model changes |
| `scripts/testing/test_bot_integration.sh` | End-to-end bot test | Before each deploy |
| `scripts/testing/field_test_monitor.sh` | Live monitoring dashboard | During events |
| `scripts/monitoring/monitor_bot.sh` | Status dashboard | Ongoing monitoring |
| `scripts/monitoring/check_resources.sh` | Cron health check | Automated |
| `scripts/monitoring/tune_performance.sh` | Hardware recommendations | Initial setup |

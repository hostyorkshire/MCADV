# MCADV Field Testing Guide

Detailed procedures for testing MCADV with real users in the field.

## Overview

Field testing validates that MCADV works end-to-end with:
- Real LoRa radio hardware
- Actual MeshCore mesh network
- Real users sending messages from their devices
- Production Ollama instance (or offline mode)

---

## Pre-Field Testing Setup

### 1. Run Setup Verification

```bash
./scripts/setup_check.sh
```

All 11 checks should pass before taking the system to the field.

### 2. Run Hardware Tests

```bash
./scripts/testing/test_hardware.sh
```

Verify the LoRa radio is detected and accessible.

### 3. Run Ollama Tests

```bash
./scripts/testing/test_ollama.sh
```

Verify models are available and story generation works.

### 4. Final Pre-Deploy Integration Test

```bash
# Start bot in background
source venv/bin/activate
python3 adventure_bot.py --distributed-mode --http-port 5000 &

# Run integration tests
./scripts/testing/test_bot_integration.sh

# Stop test instance
kill %1
```

---

## Field Test Scenarios

### Scenario 1: Single User Adventure

**Objective:** Verify basic MCADV functionality with one user.

**Steps:**
1. User sends `!help` from MeshCore app
2. Verify bot responds with command list
3. User sends `!adv` to start adventure
4. Verify opening story text received
5. User sends `1` to make first choice
6. Verify story continues
7. User sends `!status` to check session
8. User sends `!reset` to end session

**Success Criteria:**
- Each message receives a response within 30 seconds
- Story text is coherent and readable on small LoRa screen
- Commands work as documented

---

### Scenario 2: Collaborative Storytelling

**Objective:** Verify multiple users share a story on the same channel.

**Steps:**
1. User A sends `!adv` on channel #adventures
2. Verify User A receives opening story
3. User B sends `!adv` on same channel
4. Verify User B receives **same** story state (not a new story)
5. User A sends choice `1`
6. Verify story advances for **both** User A and User B
7. User B makes next choice
8. User A should see story update

**Success Criteria:**
- Both users share the same story progression
- Choices from any user advance the story for all

---

### Scenario 3: Load/Stress Test

**Objective:** Verify bot handles multiple simultaneous users.

**Steps (using distributed mode HTTP API):**

```bash
# Send 5 rapid messages from different "users"
for i in $(seq 1 5); do
    curl -s -X POST http://localhost:5000/message \
        -H "Content-Type: application/json" \
        -d "{\"sender\": \"loadtest_$i\", \"content\": \"!adv\", \"channel_idx\": 99}" &
done
wait

# Check response times in logs
tail -50 logs/meshcore.log
```

**Success Criteria:**
- All 5 requests receive responses
- Response time under 60 seconds per request
- No errors in logs
- Memory stays under 90%

---

### Scenario 4: Recovery Test

**Objective:** Verify bot recovers from crash and restores sessions.

**Steps:**
1. Start a session with `!adv`
2. Make 2-3 story choices
3. Note the current story state
4. Kill the bot: `sudo systemctl kill -s SIGKILL mcadv-bot`
5. Wait 15 seconds for auto-restart
6. Send `!status` to check session
7. Verify session was restored from `adventure_sessions.json`

**Success Criteria:**
- Bot restarts automatically within 30 seconds
- Session data is preserved
- Story continues from where it left off

---

### Scenario 5: Extended Duration Test

**Objective:** Verify bot is stable over several hours of operation.

**Duration:** 2-4 hours

**Monitoring:**
```bash
# Launch monitoring dashboard
./scripts/testing/field_test_monitor.sh
```

**Metrics to Track:**
- Memory usage (should not grow indefinitely)
- CPU usage (should not spike constantly)
- Disk usage (logs should not fill disk)
- Error count (should remain low)
- Session count (should match active users)

**Success Criteria:**
- No crashes or unexpected restarts
- Memory usage stable (< 90%)
- Disk usage stable (log rotation working)
- All user messages receive responses

---

## Data Collection Template

Record these metrics during field tests:

```
Test Date: ___________
Location: ___________
Hardware: Raspberry Pi / Jetson / Other: ___________
RAM: _____ GB
Ollama Model: ___________
Number of Test Users: _____

Performance Metrics:
  Average response time: _____ seconds
  Max response time: _____ seconds
  Message success rate: _____% (N/total)
  Bot crashes: _____

User Feedback:
  Story quality (1-5): _____
  Response speed (1-5): _____
  Ease of use (1-5): _____
  Comments: ___________

Issues Found:
  1. ___________
  2. ___________

Recommendations:
  1. ___________
```

---

## Feedback Collection

Questions to ask test users:

1. **Usability:** "Were the commands easy to understand?"
2. **Story Quality:** "Was the story engaging and coherent?"
3. **Response Time:** "Did the bot respond quickly enough?"
4. **Collaborative:** "Did you enjoy sharing the story with other players?"
5. **Issues:** "Did you encounter any problems?"

---

## Performance Benchmarks

Target benchmarks for a healthy deployment:

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Response time (offline) | < 500ms | 1-2s | > 5s |
| Response time (Ollama) | < 10s | 10-30s | > 60s |
| Memory usage | < 70% | 70-90% | > 90% |
| Disk usage | < 80% | 80-90% | > 90% |
| Uptime (4hr test) | 100% | < 100% | < 95% |

---

## Post-Event Review

After each field test:

```bash
# Archive session data
cp adventure_sessions.json archives/sessions_$(date +%Y%m%d).json

# Review error summary
grep -c "ERROR\|CRITICAL" logs/meshcore.log 2>/dev/null || echo "0 errors"

# Check memory peaks (from health log)
grep "CRITICAL\|WARNING" logs/health_check.log | tail -20

# Generate log summary
echo "=== Log Summary ==="
echo "Bot log lines: $(wc -l < logs/adventure_bot.log 2>/dev/null || echo 0)"
echo "Errors: $(grep -c 'ERROR' logs/meshcore.log 2>/dev/null || echo 0)"
echo "Sessions: $(python3 -c "import json; d=json.load(open('adventure_sessions.json')); print(len(d))" 2>/dev/null || echo 0)"
```

---

## Quick Reference Checklist

```
Pre-Event:
  [ ] setup_check.sh - all 11 checks pass
  [ ] test_hardware.sh - radio detected
  [ ] test_ollama.sh - models available
  [ ] Systemd service running
  [ ] Logs directory writable
  [ ] 10GB+ disk space free

During Event:
  [ ] field_test_monitor.sh running in background
  [ ] check_resources.sh running via cron
  [ ] At least 1 test message sent and received
  [ ] Memory < 80% at start

Post-Event:
  [ ] Archive session data
  [ ] Review error logs
  [ ] Document performance metrics
  [ ] Note user feedback
  [ ] Identify improvements
```

# Troubleshooting Guide

## Serial Port Issues

**Symptom:** `SerialException: [Errno 2] No such file or directory: '/dev/ttyUSB0'`

**Solutions:**
1. Verify the radio is plugged in: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`
2. Check user permissions: `sudo usermod -aG dialout $USER` (then log out and back in)
3. Let auto-detection find the port: omit `--port` flag

---

**Symptom:** `Permission denied: '/dev/ttyUSB0'`

**Solution:** Add your user to the `dialout` group (see above) or run with `sudo` (not recommended for production).

---

## Ollama Connection Errors

**Symptom:** `Failed to contact Ollama at http://localhost:11434`

**Solutions:**
1. Start Ollama: `ollama serve`
2. Pull the model: `ollama pull llama3.1:8b`
3. Test manually: `curl http://localhost:11434/api/tags`
4. The bot falls back to built-in story trees automatically when Ollama is unavailable.

---

**Symptom:** Very slow LLM responses or timeouts

**Solutions:**
1. Use a smaller model: `--model llama3.2:1b`
2. Increase timeout in `config.yaml`: `llm.timeout: 60`
3. Run Ollama on a more powerful device and point `OLLAMA_URL` at it

---

## Session File Corruption

**Symptom:** `Failed to load sessions: Expecting value: line 1 column 1 (char 0)`

**Solutions:**
1. Delete the corrupted file: `rm adventure_sessions.json`
2. The bot will start fresh with no sessions
3. Restore from backup: `scripts/restore_sessions.sh <backup_file>`

---

## Network Problems (Distributed Mode)

**Symptom:** Gateway cannot reach bot server

**Solutions:**
1. Verify bot server is running: `curl http://<bot-ip>:5000/api/health`
2. Check firewall: `sudo ufw allow 5000/tcp`
3. Use IP address instead of hostname if DNS resolution fails
4. Ensure both devices are on the same network

---

## Performance Issues

**Symptom:** High message latency / slow responses

**Solutions:**
1. Enable debug logging to identify the slow step: `--debug`
2. Check LLM response time – if slow, use fallback-only mode by setting `features.llm_generation: false`
3. Monitor active sessions: high session count can slow session expiry scans

---

## Common Error Messages

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `No active adventure` | Session expired or not started | Send `!adv` to restart |
| `Bot server unreachable` | Network or firewall issue | Check connectivity |
| `Invalid channel index` | channel_idx > 7 | Use 0–7 only |
| `Rate limit exceeded` | Too many messages | Wait 60 seconds |

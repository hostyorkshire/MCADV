# logs/

This directory is created automatically at runtime. It contains:

| File | Contents |
|------|----------|
| `adventure_bot.log` | Main application log (rotated, 10 MB max) |
| `adventure_bot_error.log` | Error-only log |
| `meshcore.log` | MeshCore serial/protocol log |
| `meshcore_error.log` | MeshCore error-only log |
| `sessions.json` | Active player sessions (survives reboots) |
| `channels.json` | Active LoRa channel tracking |

All log files and `sessions.json` are excluded from version control via `.gitignore`.

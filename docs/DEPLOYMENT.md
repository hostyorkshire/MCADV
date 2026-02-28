# Deployment Guide

## Production Checklist

- [ ] Set `BOT_DEBUG=false`
- [ ] Configure `OLLAMA_URL` to point at your LLM host
- [ ] Set `RADIO_PORT` to your serial device (or rely on auto-detection)
- [ ] Review rate limits in `config.yaml`
- [ ] Set up log rotation for `logs/`
- [ ] Configure a systemd service or Docker container for auto-restart

---

## Systemd Service Setup

### Bot Server (`adventure_bot.service`)

```ini
[Unit]
Description=MCADV Adventure Bot Server
After=network.target

[Service]
Type=simple
User=mcadv
WorkingDirectory=/opt/mcadv
ExecStart=/opt/mcadv/venv/bin/python adventure_bot.py --distributed-mode
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp adventure_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adventure_bot
sudo systemctl start adventure_bot
```

### Radio Gateway (`radio_gateway.service`)

```ini
[Unit]
Description=MCADV Radio Gateway
After=network.target

[Service]
Type=simple
User=mcadv
WorkingDirectory=/opt/mcadv
ExecStart=/opt/mcadv/venv/bin/python radio_gateway.py \
  --bot-server-url http://bot-server.local:5000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Docker Deployment

### Single-node (bot + Ollama)

```bash
docker compose --profile gpu up -d
```

### Bot only (external Ollama)

```bash
OLLAMA_URL=http://192.168.1.10:11434 docker compose up -d bot-server
```

### With Prometheus monitoring

```bash
docker compose --profile monitoring up -d
```

---

## Monitoring Setup

1. Start Prometheus: `docker compose --profile monitoring up -d prometheus`
2. Point Prometheus at `http://bot-server:5000/api/metrics`
3. Import the provided Grafana dashboard from `config/grafana_dashboard.json`

---

## Backup Procedures

### Manual backup

```bash
./scripts/backup_sessions.sh
```

Backups are saved to `logs/backups/` with a timestamp suffix.

### Restore

```bash
./scripts/restore_sessions.sh logs/backups/adventure_sessions_20240101_120000.json
```

### Automated backup (cron)

```cron
0 * * * * /opt/mcadv/scripts/backup_sessions.sh
```

# API Reference

## Base URL

```
http://<host>:<port>
```

Default: `http://localhost:5000`

---

## POST /api/message

Send a message to the adventure bot and receive a response.

### Request

```json
{
  "sender": "Alice",
  "content": "!adv fantasy",
  "channel_idx": 1
}
```

| Field         | Type    | Required | Description                              |
|---------------|---------|----------|------------------------------------------|
| `sender`      | string  | yes      | Display name of the sender               |
| `content`     | string  | yes      | Message text                             |
| `channel_idx` | integer | no       | LoRa channel index (0–7, default 0)      |
| `timestamp`   | float   | no       | Unix timestamp (auto-set if omitted)     |

### Response

```json
{
  "response": "You stand at a crossroads...\n1:North 2:East 3:South"
}
```

| Field      | Type            | Description                            |
|------------|-----------------|----------------------------------------|
| `response` | string or null  | Bot reply, or null if no reply needed  |

### Status codes

| Code | Meaning                         |
|------|---------------------------------|
| 200  | Success                         |
| 400  | Malformed JSON                  |
| 500  | Internal server error           |

### Example

```bash
curl -s -X POST http://localhost:5000/api/message \
  -H "Content-Type: application/json" \
  -d '{"sender":"Alice","content":"!adv","channel_idx":1}'
```

---

## GET /api/health

Health-check endpoint used by the gateway and load-balancer.

### Response

```json
{
  "status": "healthy"
}
```

### Status codes

| Code | Meaning   |
|------|-----------|
| 200  | Healthy   |

### Example

```bash
curl -s http://localhost:5000/api/health
```

---

## GET /api/metrics

Prometheus-format metrics (requires `monitoring.metrics_enabled: true`).

### Response

Plain text in [Prometheus exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/):

```
mcadv_uptime_seconds 3600.00
mcadv_active_sessions 5
mcadv_message_latency_avg 0.002345
mcadv_llm_response_time_avg 1.234567
mcadv_errors_total{type="http"} 2
```

### Example

```bash
curl -s http://localhost:5000/api/metrics
```

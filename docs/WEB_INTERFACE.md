# MCADV Web Interface

The MCADV web interface lets players enjoy adventures directly from their browser without Meshtastic hardware.

## Enabling the Web Interface

The web interface is enabled by default. Control it via the `WEB_INTERFACE_ENABLED` environment variable:

```bash
WEB_INTERFACE_ENABLED=true   # default — enables CORS and web API endpoints
WEB_INTERFACE_ENABLED=false  # disables CORS (API endpoints still exist)
```

## CORS Configuration

Set allowed origins via `CORS_ALLOWED_ORIGINS` (comma-separated):

```bash
CORS_ALLOWED_ORIGINS=http://localhost:5000,https://yourdomain.com
```

The default is `*` (all origins). Restrict this in production.

## API Endpoints

All endpoints return `application/json`.

### `GET /api/health`

Returns server health and mode.

```json
{ "status": "healthy", "mode": "http" }
```

### `GET /api/themes`

Returns all available adventure themes.

```json
{ "themes": ["fantasy", "scifi", "horror", "cyberpunk", ...] }
```

### `POST /api/adventure/start`

Start a new adventure session.

**Body:**
```json
{
  "theme": "fantasy",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "session_id": "12345678-...",
  "story": "You stand at a crossroads...",
  "choices": ["North", "East", "South"],
  "status": "active"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `theme` | string | No | Adventure theme (default: `fantasy`) |
| `session_id` | UUID | No | Reuse a session ID; a new UUID is generated if omitted |

**Error codes:** `400` — invalid theme or session_id format.

### `POST /api/adventure/choice`

Make a choice to advance the story.

**Body:**
```json
{ "session_id": "12345678-...", "choice": "1" }
```

`choice` must be `"1"`, `"2"`, or `"3"`.

**Response:**
```json
{
  "story": "The forest is thick and eerie...",
  "choices": ["Investigate", "Keep walking", "Turn back"],
  "status": "active"
}
```

When `status` is `"finished"` the session is automatically cleared and `choices` will be empty.

**Error codes:** `400` — invalid session_id or choice value; `404` — session not found or not active.

### `GET /api/adventure/status`

Check the status of a session.

```
GET /api/adventure/status?session_id=12345678-...
```

**Response:**
```json
{
  "status": "active",
  "theme": "fantasy",
  "history_length": 3
}
```

`status` is one of `"active"`, `"finished"`, or `"none"` (session not found).

**Error codes:** `400` — missing or invalid session_id.

### `POST /api/adventure/quit`

End an adventure session.

**Body:**
```json
{ "session_id": "12345678-..." }
```

**Response:**
```json
{ "message": "Adventure ended", "status": "quit" }
```

**Error codes:** `400` — missing or invalid session_id.

## Session Management

Web sessions use the key format `web_{uuid}` internally, which means they are completely isolated from mesh/channel sessions (`channel_{idx}`). Multiple concurrent web players are fully supported.

Sessions expire after 1 hour of inactivity (same as mesh sessions).

## Security Considerations

- **Input validation:** All inputs are validated. Theme must be in the allowed list. `session_id` must match UUID format. Choice must be `1`, `2`, or `3`.
- **CORS:** Configure `CORS_ALLOWED_ORIGINS` to restrict cross-origin access in production.
- **No sensitive data:** Session responses never include internal state beyond what is needed by the client.
- **Rate limiting:** Consider using a reverse proxy (nginx, Caddy) with rate limiting in production.

## Deployment

### Local development

```bash
python adventure_bot.py --http-host 0.0.0.0 --http-port 5000
```

Open `website/play.html` in your browser (or serve it with any static file server) pointing at `http://localhost:5000`.

### Docker

```bash
docker-compose up adventure-bot
```

The `website/` directory can be served by nginx or any static host alongside the Python API.

### Cloud

Deploy the Python service to any platform that supports Python/Flask (Fly.io, Railway, Heroku, etc.).  
Set `CORS_ALLOWED_ORIGINS` to your frontend domain.

## Backward Compatibility

- Existing `/api/message` and `/api/health` endpoints are unchanged.
- Mesh/channel sessions are unaffected.
- Setting `WEB_INTERFACE_ENABLED=false` disables CORS but keeps all endpoints functional.

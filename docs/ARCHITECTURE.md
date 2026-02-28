# Architecture

## Component Diagram

```
                         LoRa Radio Network
                               │
                    ┌──────────▼──────────┐
                    │   Pi Zero 2W         │
                    │   radio_gateway.py   │
                    │   (MeshCore serial)  │
                    └──────────┬──────────┘
                               │ HTTP POST /api/message
                    ┌──────────▼──────────┐
                    │   Bot Server         │
                    │   adventure_bot.py   │
                    │   (Flask + sessions) │
                    └──────────┬──────────┘
                               │ HTTP POST /api/generate
                    ┌──────────▼──────────┐
                    │   Ollama / LLM API   │
                    │   (llama3.1:8b)      │
                    └─────────────────────┘
```

## Data Flow

1. A player sends a message via LoRa radio
2. `MeshCore` (on the Pi Zero 2W) receives the frame and deserialises it into a `MeshCoreMessage`
3. `RadioGateway.handle_message()` filters by channel and forwards via HTTP to the bot server
4. `AdventureBot.handle_message()` parses the command, manages session state, and generates a response
5. The response is returned in the HTTP reply and sent back over LoRa by the gateway

## Design Decisions

### Session Keyed by Channel
All users on the same LoRa channel share one adventure session.  This enables
collaborative storytelling without requiring user accounts.

### Fallback Story Trees
When Ollama is unavailable the bot serves deterministic story trees so gameplay
never breaks due to LLM downtime.

### Distributed Architecture
Splitting radio I/O (Pi Zero 2W) from game logic (Pi 4 / PC) keeps the gateway
lightweight (~15 MB RAM) and allows the LLM host to be upgraded independently.

### No Persistent State on Gateway
The gateway is stateless; all session state lives on the bot server.  The gateway
can be restarted at any time without data loss.

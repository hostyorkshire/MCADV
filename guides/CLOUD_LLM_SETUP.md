# Cloud LLM Setup Guide

**Quick reference guide for configuring OpenAI and Groq backends as an alternative to Ollama.**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Cloud LLM Options](#cloud-llm-options)
4. [Pros and Cons vs Local Ollama](#pros-and-cons-vs-local-ollama)
5. [Getting API Keys](#getting-api-keys)
6. [Groq Configuration](#groq-configuration)
7. [OpenAI Configuration](#openai-configuration)
8. [Model Selection](#model-selection)
9. [Cost Estimates](#cost-estimates)
10. [Securing Your API Keys](#securing-your-api-keys)
11. [Network Requirements](#network-requirements)
12. [Rate Limiting and Error Handling](#rate-limiting-and-error-handling)
13. [Testing Cloud LLM Connectivity](#testing-cloud-llm-connectivity)
14. [Monitoring API Usage](#monitoring-api-usage)
15. [Switching Between Backends](#switching-between-backends)
16. [Troubleshooting](#troubleshooting)
17. [Next Steps](#next-steps)

---

## Overview

MCADV supports three LLM backends for AI-powered story generation:

| Backend | Type | Cost | Internet Required |
|---------|------|------|-------------------|
| **Ollama** | Local | Free | No |
| **Groq** | Cloud | Free tier available | Yes |
| **OpenAI** | Cloud | Paid | Yes |
| **Offline** | Built-in story trees | Free | No |

Cloud LLMs are ideal when local hardware cannot run Ollama (e.g., Pi Zero 2W running standalone without a Pi 5 bot server), or when you want the highest response quality without investing in powerful hardware.

---

## Prerequisites

- MCADV installed with virtual environment set up
- Internet connectivity on the device running `adventure_bot.py`
- API key from Groq and/or OpenAI
- Python `requests` library (already in `requirements.txt`)

---

## Cloud LLM Options

### Groq

[Groq](https://groq.com) provides a **free tier** with generous rate limits. It uses custom hardware (LPUs) to deliver very fast inference — often faster than a local Pi 5 running Ollama.

- **Free tier:** Yes — no credit card required for basic use
- **Latency:** Typically 1–3 seconds (very fast)
- **Models:** Llama 3.x, Mixtral, Gemma
- **Best for:** Free cloud LLM, fast responses, minimal setup

### OpenAI

[OpenAI](https://openai.com) provides GPT-4o, GPT-4o-mini, and other models. It is a paid service but offers high quality responses.

- **Free tier:** No (prepaid credits required)
- **Latency:** 1–5 seconds
- **Models:** gpt-4o-mini, gpt-4o, gpt-3.5-turbo
- **Best for:** Highest quality responses, complex storytelling, proven reliability

---

## Pros and Cons vs Local Ollama

| Factor | Ollama (Local) | Groq (Cloud) | OpenAI (Cloud) |
|--------|----------------|--------------|----------------|
| **Cost** | Free | Free tier | Paid |
| **Privacy** | ✅ Data stays local | ⚠️ Data sent to cloud | ⚠️ Data sent to cloud |
| **Internet needed** | No | Yes | Yes |
| **Setup complexity** | Medium | Low | Low |
| **Response quality** | Good (depends on model) | Good | Best |
| **Response speed** | 0.5s–5s (hardware dependent) | 1–3s (fast) | 1–5s |
| **Pi Zero 2W support** | ❌ Needs separate server | ✅ Direct | ✅ Direct |
| **Offline operation** | ✅ | ❌ | ❌ |
| **Rate limits** | None | 30 req/min (free) | Based on tier |

**Recommendation:**
- Use **Ollama** for privacy-sensitive deployments, offline events, or when you have a Pi 4/5 available
- Use **Groq** for simplicity on a Pi Zero 2W or when you don't want to run local hardware
- Use **OpenAI** when you need maximum story quality for special events

---

## Getting API Keys

### Groq API Key (Free)

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account (no credit card required)
3. Click **API Keys** in the left sidebar
4. Click **Create API Key**
5. Give it a name (e.g., `mcadv-bot`)
6. Copy the key — it starts with `gsk_`

> **Important:** The key is only shown once. Copy and store it securely.

### OpenAI API Key (Paid)

1. Visit [https://platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Go to **Settings → API Keys**
4. Click **Create new secret key**
5. Give it a name (e.g., `mcadv-bot`)
6. Copy the key — it starts with `sk-`
7. Add billing information and purchase credits

> **Tip:** Start with a small credit balance ($5–$10) to test before committing.

---

## Groq Configuration

### Basic Setup

```bash
python3 adventure_bot.py \
  --channel-idx 1 \
  --groq-key gsk_YOUR_GROQ_KEY_HERE
```

### With Specific Model

```bash
python3 adventure_bot.py \
  --channel-idx 1 \
  --groq-key gsk_YOUR_GROQ_KEY_HERE \
  --model llama-3.1-8b-instant
```

### In Distributed Mode (Bot Server)

```bash
python3 adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --channel-idx 1 \
  --groq-key gsk_YOUR_GROQ_KEY_HERE \
  --model llama-3.1-8b-instant
```

### Systemd Service with Groq

Edit `/etc/systemd/system/mcadv_bot.service` (or your service file):

```ini
[Service]
...
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --baud 115200 \
  --channel-idx 1 \
  --announce \
  --groq-key gsk_YOUR_KEY_HERE
```

> **Security note:** Storing the key directly in the service file is convenient but exposes it to anyone who can read the file. See [Securing Your API Keys](#securing-your-api-keys) for better options.

---

## OpenAI Configuration

### Basic Setup

```bash
python3 adventure_bot.py \
  --channel-idx 1 \
  --openai-key sk-YOUR_OPENAI_KEY_HERE
```

### With Specific Model

```bash
python3 adventure_bot.py \
  --channel-idx 1 \
  --openai-key sk-YOUR_OPENAI_KEY_HERE \
  --model gpt-4o-mini
```

### In Distributed Mode (Bot Server)

```bash
python3 adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --channel-idx 1 \
  --openai-key sk-YOUR_OPENAI_KEY_HERE \
  --model gpt-4o-mini
```

### Systemd Service with OpenAI

```ini
[Service]
...
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --baud 115200 \
  --channel-idx 1 \
  --announce \
  --openai-key sk-YOUR_KEY_HERE
```

---

## Model Selection

### Groq Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.1-8b-instant` | ⚡ Very fast | Good | Default — fast responses |
| `llama-3.3-70b-versatile` | Moderate | Better | Higher quality stories |
| `mixtral-8x7b-32768` | Fast | Good | Creative writing |
| `gemma2-9b-it` | Fast | Good | Budget-friendly |

```bash
# Fast and free (recommended default)
--groq-key gsk_... --model llama-3.1-8b-instant

# Higher quality
--groq-key gsk_... --model llama-3.3-70b-versatile
```

Check the latest available models at [https://console.groq.com/docs/models](https://console.groq.com/docs/models).

### OpenAI Models

| Model | Speed | Quality | Cost per 1M tokens |
|-------|-------|---------|-------------------|
| `gpt-4o-mini` | Fast | Very good | ~$0.15 input / $0.60 output |
| `gpt-4o` | Moderate | Excellent | ~$2.50 input / $10 output |
| `gpt-3.5-turbo` | Fast | Good | ~$0.50 input / $1.50 output |

```bash
# Recommended default (good quality, low cost)
--openai-key sk-... --model gpt-4o-mini

# Best quality (higher cost)
--openai-key sk-... --model gpt-4o
```

Check the latest pricing at [https://openai.com/pricing](https://openai.com/pricing).

---

## Cost Estimates

### Groq (Free Tier)

Groq's free tier limits (as of 2025):

| Limit | Value |
|-------|-------|
| Requests per minute | 30 |
| Tokens per minute | 14,400 |
| Tokens per day | 14,400 |

For an MCADV bot at a typical event with ~50 players and ~200 messages/hour:
- Each message generates ~300 tokens (prompt + response)
- ~200 messages × 300 tokens = 60,000 tokens/hour
- **Free tier covers ~14,000 tokens/day** — suitable for light use

For heavier use, upgrade to Groq's paid tier.

### OpenAI Costs

Approximate cost for an active event with 50 players and 200 messages/hour:

| Scenario | Daily Tokens | Daily Cost |
|----------|-------------|-----------|
| Light (50 messages/hr) | ~15K | ~$0.01 |
| Moderate (200 messages/hr) | ~60K | ~$0.05 |
| Heavy (500 messages/hr) | ~150K | ~$0.12 |

Using `gpt-4o-mini`, a full day of heavy usage costs approximately **$0.12**. A week-long event would cost ~$1. These are very low costs.

---

## Securing Your API Keys

### Using Environment Variables (Recommended)

Instead of passing keys on the command line (visible in `ps aux`), use environment variables:

```bash
# Set environment variable
export GROQ_API_KEY=gsk_YOUR_KEY_HERE
export OPENAI_API_KEY=sk-YOUR_KEY_HERE

# Run bot (reads from environment)
python3 adventure_bot.py --channel-idx 1 --groq-key $GROQ_API_KEY
```

### Systemd Environment File

Create `/etc/mcadv/secrets.env` (readable only by the service user):

```bash
sudo mkdir -p /etc/mcadv
sudo nano /etc/mcadv/secrets.env
```

Content:

```
GROQ_API_KEY=gsk_YOUR_KEY_HERE
OPENAI_API_KEY=sk-YOUR_KEY_HERE
```

Restrict permissions:

```bash
sudo chmod 600 /etc/mcadv/secrets.env
sudo chown pi:pi /etc/mcadv/secrets.env
```

Reference in the systemd service:

```ini
[Service]
EnvironmentFile=/etc/mcadv/secrets.env
ExecStart=/home/pi/MCADV/venv/bin/python3 /home/pi/MCADV/adventure_bot.py \
  --channel-idx 1 \
  --groq-key ${GROQ_API_KEY}
```

### Key Rotation

Rotate API keys regularly (every 90 days is recommended):

1. Generate a new key in the provider console
2. Update `/etc/mcadv/secrets.env` with the new key
3. Restart the service: `sudo systemctl restart mcadv_bot`
4. Revoke the old key in the provider console

---

## Network Requirements

### Connectivity

Cloud LLMs require a **reliable internet connection**. Requirements:

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Download speed | 1 Mbps | 5 Mbps+ |
| Upload speed | 0.5 Mbps | 2 Mbps+ |
| Latency to cloud | <500ms | <200ms |
| Connection type | WiFi | Ethernet or LTE |

### DNS Resolution

Both Groq and OpenAI APIs require DNS resolution:

```bash
# Test DNS
nslookup api.groq.com
nslookup api.openai.com
```

If DNS fails, check `/etc/resolv.conf`:

```bash
cat /etc/resolv.conf
# Should include: nameserver 8.8.8.8 or similar
```

### Firewall Rules

Ensure outbound HTTPS (port 443) is not blocked:

```bash
curl -I https://api.groq.com
curl -I https://api.openai.com
```

If blocked, update firewall rules:

```bash
sudo ufw allow out 443/tcp
```

### Offline Fallback

If internet connectivity is lost during an event, MCADV falls back to **built-in offline story trees** automatically. Players will continue to receive responses, but they will be from the pre-written story trees rather than AI-generated content.

---

## Rate Limiting and Error Handling

### Groq Rate Limits

Groq enforces rate limits on the free tier. If exceeded, the API returns a `429 Too Many Requests` error. MCADV logs this as:

```
[ERROR] LLM: Groq API error 429: Rate limit exceeded
[INFO] LLM: Falling back to offline story trees
```

The bot automatically falls back to offline mode and retries cloud LLM on subsequent messages.

**To avoid rate limit issues:**
- Use `llama-3.1-8b-instant` (faster, uses fewer tokens per second)
- Reduce concurrent players per bot instance
- Upgrade to Groq's paid tier for higher limits

### OpenAI Rate Limits

OpenAI rate limits are based on your account tier. For new accounts:

- **Tier 1** (≥$5 spent): 500 RPM, 200,000 TPM
- **Tier 2** (≥$50 spent): 5,000 RPM, 2,000,000 TPM

At Tier 1, MCADV can handle ~100 concurrent players comfortably.

### Error Handling

MCADV handles these API errors gracefully:

| Error | Behavior |
|-------|----------|
| `401 Unauthorized` | Log error; fall back to offline trees |
| `429 Rate Limited` | Log warning; fall back to offline trees |
| `500/503 Server Error` | Log error; fall back to offline trees |
| Network timeout | Log error; fall back to offline trees |
| DNS failure | Log error; use offline trees indefinitely |

Players continue to receive responses even when cloud APIs are unavailable.

---

## Testing Cloud LLM Connectivity

### Step 1: Test API Key

```bash
# Test Groq API key
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer gsk_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": "Say hello in 5 words."}],
    "max_tokens": 20
  }'

# Test OpenAI API key
curl -s https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer sk-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say hello in 5 words."}],
    "max_tokens": 20
  }'
```

Expected response includes a `choices[0].message.content` field.

### Step 2: Run MCADV with Debug Mode

```bash
python3 adventure_bot.py \
  --channel-idx 1 \
  --groq-key gsk_YOUR_KEY \
  --model llama-3.1-8b-instant \
  -d
```

Look for:

```
[INFO] AdventureBot: LLM backend: groq
[INFO] AdventureBot: Model: llama-3.1-8b-instant
[DEBUG] LLM: Calling Groq API...
[DEBUG] LLM: Response received in 1.2s
```

### Step 3: Send a Test Message

```bash
# Via HTTP (distributed mode)
curl -X POST http://localhost:5000/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "tester", "content": "start", "channel_idx": 1}'
```

The response should be AI-generated story text, not from the offline trees.

---

## Monitoring API Usage

### Groq Usage Dashboard

Visit [https://console.groq.com/usage](https://console.groq.com/usage) to see:
- Requests per day
- Tokens used
- Rate limit status

### OpenAI Usage Dashboard

Visit [https://platform.openai.com/usage](https://platform.openai.com/usage) to see:
- Daily token usage
- Cost breakdown per model
- Rate limit status

### Local Log Monitoring

MCADV logs LLM call timings and errors. Check:

```bash
tail -f ~/MCADV/logs/meshcore.log | grep -i 'llm\|groq\|openai\|error'
```

### Set Spending Limits

**Groq:** Configure usage limits in the Groq console under **Settings → Limits**.

**OpenAI:** Set a monthly spending limit under **Settings → Limits → Set monthly budget**.

---

## Switching Between Backends

You can switch between Ollama, Groq, OpenAI, and offline at any time by changing command-line flags.

### Backend Selection Priority

MCADV selects the backend in this order (first configured wins):

1. `--groq-key` → Groq API
2. `--openai-key` → OpenAI API
3. `--ollama-url` → Ollama
4. *(none)* → Offline story trees

### Switch to Groq

```bash
# Edit service file
sudo nano /etc/systemd/system/mcadv_bot.service

# Change ExecStart to use Groq key
ExecStart=... adventure_bot.py --channel-idx 1 --groq-key gsk_...

sudo systemctl daemon-reload
sudo systemctl restart mcadv_bot
```

### Switch to Ollama

```bash
# Edit service file
ExecStart=... adventure_bot.py --channel-idx 1 \
  --ollama-url http://localhost:11434 --model llama3.2:1b

sudo systemctl daemon-reload
sudo systemctl restart mcadv_bot
```

### Switch to Offline

```bash
# Remove LLM flags entirely
ExecStart=... adventure_bot.py --channel-idx 1

sudo systemctl daemon-reload
sudo systemctl restart mcadv_bot
```

---

## Troubleshooting

### API Key Invalid

```
[ERROR] LLM: Groq API error 401: Invalid API key
```

**Fix:** Verify the key is correct and hasn't been rotated:

```bash
# Test key directly
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer gsk_YOUR_KEY"
```

### No Internet Connectivity

```
[ERROR] LLM: Connection error: Failed to establish connection to api.groq.com
[INFO] LLM: Falling back to offline story trees
```

**Fix:**

```bash
# Check internet connectivity
ping -c 3 8.8.8.8

# Check DNS
nslookup api.groq.com

# Check proxy settings (if in a corporate environment)
echo $http_proxy $https_proxy
```

### Rate Limit Exceeded (Groq Free Tier)

```
[ERROR] LLM: Groq API error 429: Rate limit exceeded. Retrying after 60s.
```

**Options:**
1. Wait for the rate limit to reset (1 minute)
2. Switch to a faster model: `--model llama-3.1-8b-instant`
3. Upgrade to Groq's paid tier
4. Switch to OpenAI or local Ollama

### Slow Responses

Cloud API responses should arrive in 1–5 seconds. If responses are consistently slower:

1. Check your internet latency: `ping api.groq.com`
2. Try a different model (smaller models are faster)
3. Check if the API is experiencing an outage: [status.groq.com](https://status.groq.com)

---

## Next Steps

- Set up local Ollama for offline use: [OLLAMA_SETUP.md](OLLAMA_SETUP.md)
- Deploy in distributed mode: [DISTRIBUTED_ARCHITECTURE.md](DISTRIBUTED_ARCHITECTURE.md)
- Production hardening: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- Hardware selection: [HARDWARE.md](../HARDWARE.md)

---

## Quick Links

- [Main README](../README.md)
- [Other Guides](README.md)
- [Hardware Guide](../HARDWARE.md)
- [Performance Guide](../PERFORMANCE.md)

---

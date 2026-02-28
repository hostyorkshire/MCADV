#!/bin/bash
# test_bot_server.sh - Test Bot Server functionality (Pi 5 or Ubuntu Desktop)
#
# Verifies Ollama connectivity, model loading, HTTP API endpoints,
# session management and resource availability.
#
# Usage:
#   ./scripts/testing/test_bot_server.sh [-h|--help] [--ollama-url URL]
#
# Exit codes:
#   0 - All tests passed
#   1 - Warnings
#   2 - Failures

set -euo pipefail

if [[ -z "${NO_COLOR:-}" && -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    GREEN='' YELLOW='' RED='' BLUE='' CYAN='' NC=''
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OLLAMA_URL="http://localhost:11434"
BOT_PORT=5000
PASS=0 WARN=0 FAIL=0

usage() {
    cat <<EOF
Usage: $0 [-h|--help] [--ollama-url URL] [--port PORT]

Test Bot Server (Pi 5 / Ubuntu Desktop) functionality.

Options:
  --ollama-url URL   Ollama server URL (default: ${OLLAMA_URL})
  --port PORT        Bot HTTP port (default: ${BOT_PORT})
  -h, --help         Show this help and exit

Exit codes:
  0 - All tests passed
  1 - Warnings
  2 - Failures
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)     usage ;;
        --ollama-url)  OLLAMA_URL="$2"; shift 2 ;;
        --port)        BOT_PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()     { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$(( PASS + 1 )); }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$(( WARN + 1 )); }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$(( FAIL + 1 )); }
info()   { echo -e "       ${BLUE}→${NC} $1"; }
header() { echo -e "\n${CYAN}─── $1 ───${NC}"; }

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  MCADV Bot Server Test                       ║${NC}"
echo -e "${GREEN}║  [BOT SERVER]                                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Repo:      ${REPO_DIR}"
echo "  Timestamp: $(date)"

# ---------------------------------------------------------------------------
# 1. Ollama connectivity
# ---------------------------------------------------------------------------
header "Ollama Connectivity"
if command -v ollama &>/dev/null; then
    ok "Ollama binary found: $(ollama --version 2>/dev/null | head -1 || echo 'version unknown')"
else
    warn "Ollama not installed (offline story mode will still work)"
    info "Install: curl -fsSL https://ollama.ai/install.sh | sh"
fi

if curl -s --connect-timeout 5 "${OLLAMA_URL}/api/tags" &>/dev/null; then
    ok "Ollama API reachable at ${OLLAMA_URL}"
else
    warn "Ollama not running at ${OLLAMA_URL}"
    info "Start: ollama serve"
fi

# ---------------------------------------------------------------------------
# 2. Model loading
# ---------------------------------------------------------------------------
header "Model Availability"
if curl -s --connect-timeout 5 "${OLLAMA_URL}/api/tags" &>/dev/null; then
    MODELS="$(curl -s "${OLLAMA_URL}/api/tags" | python3 -c "
import json, sys
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print('\n'.join(models))
" 2>/dev/null || true)"
    if [[ -n "$MODELS" ]]; then
        ok "Models available:"
        while IFS= read -r m; do
            [[ -n "$m" ]] && info "$m"
        done <<< "$MODELS"
    else
        warn "No models downloaded"
        info "Pull: ollama pull llama3.2:1b"
    fi
else
    warn "Skipping (Ollama not running)"
fi

# ---------------------------------------------------------------------------
# 3. HTTP API endpoints
# ---------------------------------------------------------------------------
header "HTTP API Endpoints"
BOT_BASE="http://localhost:${BOT_PORT}"
if curl -s --connect-timeout 3 "${BOT_BASE}/health" &>/dev/null; then
    HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "${BOT_BASE}/health" 2>/dev/null || echo '000')"
    if [[ "$HTTP_CODE" == "200" ]]; then
        ok "Health endpoint /health → HTTP 200"
    else
        warn "Health endpoint returned HTTP ${HTTP_CODE}"
    fi
    HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "${BOT_BASE}/status" 2>/dev/null || echo '000')"
    if [[ "$HTTP_CODE" == "200" ]]; then
        ok "Status endpoint /status → HTTP 200"
    else
        info "/status returned HTTP ${HTTP_CODE} (may not be enabled)"
    fi
else
    warn "Bot HTTP API not reachable at ${BOT_BASE}"
    info "Start bot with HTTP enabled: ./run_adventure_bot.sh"
fi

# ---------------------------------------------------------------------------
# 4. Resource availability
# ---------------------------------------------------------------------------
header "Resource Availability"
# RAM
TOTAL_KB="$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)"
TOTAL_MB=$(( TOTAL_KB / 1024 ))
FREE_KB="$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)"
FREE_MB=$(( FREE_KB / 1024 ))
if [[ $TOTAL_MB -ge 2048 ]]; then
    ok "RAM: ${TOTAL_MB} MB total, ${FREE_MB} MB available"
else
    fail "RAM: ${TOTAL_MB} MB total (minimum 2 GB recommended)"
fi

# Disk
FREE_DISK_KB="$(df -k "${REPO_DIR}" | awk 'NR==2{print $4}')"
FREE_DISK_GB=$(( FREE_DISK_KB / 1024 / 1024 ))
if [[ $FREE_DISK_GB -ge 10 ]]; then
    ok "Disk: ${FREE_DISK_GB} GB free"
else
    warn "Disk: ${FREE_DISK_GB} GB free (10 GB+ recommended for LLM models)"
fi

# Port 5000
if command -v ss &>/dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ":${BOT_PORT} "; then
        ok "Port ${BOT_PORT} is listening (bot running)"
    else
        info "Port ${BOT_PORT} not in use (bot not started yet)"
    fi
fi

# ---------------------------------------------------------------------------
# 5. Python + dependencies
# ---------------------------------------------------------------------------
header "Python Environment"
if [[ -f "${REPO_DIR}/venv/bin/python3" ]]; then
    ok "Virtual environment found"
    if "${REPO_DIR}/venv/bin/python3" -c "import flask, requests" &>/dev/null; then
        ok "Core dependencies (flask, requests) importable"
    else
        fail "Core dependencies missing"
        info "Run: cd ${REPO_DIR} && source venv/bin/activate && pip install -r requirements.txt"
    fi
else
    fail "Virtual environment not found"
    info "Create: cd ${REPO_DIR} && ./setup_venv.sh"
fi

# ---------------------------------------------------------------------------
# 6. Session management smoke test
# ---------------------------------------------------------------------------
header "Session Management Smoke Test"
if [[ -f "${REPO_DIR}/venv/bin/python3" && -f "${REPO_DIR}/adventure_bot.py" ]]; then
    IMPORT_TEST="$(cd "${REPO_DIR}" && \
        "${REPO_DIR}/venv/bin/python3" -c "import adventure_bot; print('OK')" 2>&1 | head -1 || true)"
    if [[ "$IMPORT_TEST" == "OK" ]]; then
        ok "adventure_bot module imports successfully"
    else
        warn "adventure_bot module import issue: ${IMPORT_TEST}"
    fi
else
    warn "Skipping (venv or adventure_bot.py missing)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}  ❌ Bot server test FAILED${NC}"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}  ⚠  Bot server test passed with warnings${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ Bot server tests passed!${NC}"
    exit 0
fi

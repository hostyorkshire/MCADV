#!/bin/bash
# test_distributed_integration.sh - Test complete distributed MCADV setup
#
# Verifies radio gateway → bot server communication, end-to-end message flow,
# response times and basic load testing.
#
# Usage:
#   ./scripts/testing/test_distributed_integration.sh [-h|--help] --bot-server HOST
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
BOT_HOST=""
BOT_PORT=5000
PASS=0 WARN=0 FAIL=0

usage() {
    cat <<EOF
Usage: $0 [-h|--help] --bot-server HOST [--port PORT]

Test the complete distributed MCADV setup (radio gateway ↔ bot server).

Options:
  --bot-server HOST   Hostname or IP of the bot server (required)
  --port PORT         Bot server HTTP port (default: ${BOT_PORT})
  -h, --help          Show this help and exit

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
        --bot-server)  BOT_HOST="$2"; shift 2 ;;
        --port)        BOT_PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$BOT_HOST" ]]; then
    echo "Error: --bot-server HOST is required"
    echo ""
    usage
fi

BOT_BASE="http://${BOT_HOST}:${BOT_PORT}"

ok()     { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$(( PASS + 1 )); }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$(( WARN + 1 )); }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$(( FAIL + 1 )); }
info()   { echo -e "       ${BLUE}→${NC} $1"; }
header() { echo -e "\n${CYAN}─── $1 ───${NC}"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  MCADV Distributed Integration Test          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Bot Server: ${BOT_BASE}"
echo "  Timestamp:  $(date)"

# ---------------------------------------------------------------------------
# 1. Basic connectivity
# ---------------------------------------------------------------------------
header "Basic Connectivity"
if ping -c 2 -W 3 "$BOT_HOST" &>/dev/null 2>&1; then
    ok "Ping to bot server (${BOT_HOST})"
else
    fail "Cannot ping bot server (${BOT_HOST})"
    info "Verify network connectivity and hostname/IP"
fi

if curl -s --connect-timeout 5 "${BOT_BASE}/health" &>/dev/null; then
    ok "Bot server health endpoint reachable"
else
    fail "Bot server not reachable at ${BOT_BASE}"
    info "Ensure adventure_bot.py is running on ${BOT_HOST}"
fi

# ---------------------------------------------------------------------------
# 2. Radio gateway → bot server communication
# ---------------------------------------------------------------------------
header "Gateway → Bot Server Communication"
if [[ -f "${REPO_DIR}/venv/bin/python3" ]]; then
    FWD_TEST="$("${REPO_DIR}/venv/bin/python3" - <<'PYEOF' 2>&1 || true
import sys, os
sys.path.insert(0, os.environ.get('REPO_DIR', '.'))
try:
    import requests
    url = os.environ.get('BOT_BASE', 'http://localhost:5000') + '/health'
    r = requests.get(url, timeout=5)
    print('OK' if r.status_code == 200 else f'HTTP {r.status_code}')
except Exception as e:
    print(f'ERROR: {e}')
PYEOF
)"
    if [[ "$FWD_TEST" == "OK" ]]; then
        ok "Python requests library can reach bot server"
    else
        warn "Python connectivity test: ${FWD_TEST}"
    fi
else
    warn "Skipping Python connectivity test (venv not found)"
fi

# ---------------------------------------------------------------------------
# 3. End-to-end message flow
# ---------------------------------------------------------------------------
header "End-to-End Message Flow"
if curl -s --connect-timeout 5 "${BOT_BASE}/health" &>/dev/null; then
    # Check /status endpoint (session info)
    HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "${BOT_BASE}/status" 2>/dev/null || echo '000')"
    if [[ "$HTTP_CODE" == "200" ]]; then
        ok "Status endpoint /status → HTTP 200"
        SESSION_DATA="$(curl -s --connect-timeout 5 "${BOT_BASE}/status" 2>/dev/null || true)"
        if echo "$SESSION_DATA" | python3 -c "import json,sys; json.load(sys.stdin); print('valid JSON')" &>/dev/null 2>&1; then
            ok "Status response is valid JSON"
        else
            warn "Status response is not valid JSON"
        fi
    elif [[ "$HTTP_CODE" == "404" ]]; then
        info "/status endpoint not available (HTTP 404) – may not be enabled"
    else
        warn "/status returned HTTP ${HTTP_CODE}"
    fi
else
    fail "Cannot reach bot server for end-to-end test"
fi

# ---------------------------------------------------------------------------
# 4. Response time measurements
# ---------------------------------------------------------------------------
header "Response Time Measurements"
if command -v curl &>/dev/null && curl -s --connect-timeout 3 "${BOT_BASE}/health" &>/dev/null; then
    TIMES=()
    for i in 1 2 3; do
        T="$(curl -s -o /dev/null -w '%{time_total}' --connect-timeout 5 "${BOT_BASE}/health" 2>/dev/null || echo '0')"
        TIMES+=("$T")
    done
    # Calculate average using python3 (more portable than bc)
    AVG_MS="$(python3 -c "
times = [${TIMES[0]}, ${TIMES[1]}, ${TIMES[2]}]
avg = sum(times) / len(times) * 1000
print(int(avg))
" 2>/dev/null || echo '?')"

    if [[ "$AVG_MS" != "?" ]]; then
        if [[ $AVG_MS -lt 500 ]]; then
            ok "Average HTTP latency: ${AVG_MS} ms (excellent)"
        elif [[ $AVG_MS -lt 2000 ]]; then
            ok "Average HTTP latency: ${AVG_MS} ms (acceptable)"
        else
            warn "Average HTTP latency: ${AVG_MS} ms (high – may cause timeouts)"
        fi
    else
        warn "Could not measure HTTP latency"
    fi
else
    warn "Skipping latency test (curl not available or server unreachable)"
fi

# ---------------------------------------------------------------------------
# 5. Basic load test (5 rapid requests)
# ---------------------------------------------------------------------------
header "Basic Load Test (5 requests)"
if command -v curl &>/dev/null && curl -s --connect-timeout 3 "${BOT_BASE}/health" &>/dev/null; then
    LOAD_PASS=0
    for i in $(seq 1 5); do
        CODE="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "${BOT_BASE}/health" 2>/dev/null || echo '000')"
        [[ "$CODE" == "200" ]] && LOAD_PASS=$(( LOAD_PASS + 1 ))
    done
    if [[ $LOAD_PASS -eq 5 ]]; then
        ok "Load test: 5/5 requests succeeded"
    elif [[ $LOAD_PASS -ge 3 ]]; then
        warn "Load test: ${LOAD_PASS}/5 requests succeeded"
    else
        fail "Load test: ${LOAD_PASS}/5 requests succeeded (server may be overwhelmed)"
    fi
else
    warn "Skipping load test (curl not available or server unreachable)"
fi

# ---------------------------------------------------------------------------
# 6. LoRa radio on this device
# ---------------------------------------------------------------------------
header "Local LoRa Radio"
RADIO_FOUND=false
for pattern in /dev/ttyUSB* /dev/ttyACM*; do
    for port in $pattern; do
        if [[ -e "$port" ]]; then
            ok "LoRa radio detected locally: ${port}"
            RADIO_FOUND=true
        fi
    done
done
if [[ "$RADIO_FOUND" == false ]]; then
    warn "No local LoRa radio detected"
    info "Radio gateway may be running on a separate device"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}  ❌ Integration test FAILED${NC}"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}  ⚠  Integration test passed with warnings${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ Distributed integration tests passed!${NC}"
    exit 0
fi

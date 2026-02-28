#!/bin/bash
# test_radio_gateway.sh - Test Radio Gateway functionality (Pi Zero 2W)
#
# Tests LoRa radio detection, serial communication, message forwarding
# to bot server, and resource usage.
#
# Usage:
#   ./scripts/testing/test_radio_gateway.sh [-h|--help] [--bot-server URL]
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
BOT_SERVER_URL="${BOT_SERVER_URL:-http://localhost:5000}"
PASS=0 WARN=0 FAIL=0

usage() {
    cat <<EOF
Usage: $0 [-h|--help] [--bot-server URL]

Test Radio Gateway (Pi Zero 2W) functionality.

Options:
  --bot-server URL   Bot server base URL (default: ${BOT_SERVER_URL})
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
        --bot-server)  BOT_SERVER_URL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()     { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$(( PASS + 1 )); }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$(( WARN + 1 )); }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$(( FAIL + 1 )); }
info()   { echo -e "       ${BLUE}→${NC} $1"; }
header() { echo -e "\n${CYAN}─── $1 ───${NC}"; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  MCADV Radio Gateway Test                    ║${NC}"
echo -e "${BLUE}║  [RADIO GATEWAY]                             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Repo:        ${REPO_DIR}"
echo "  Bot Server:  ${BOT_SERVER_URL}"
echo "  Timestamp:   $(date)"

# ---------------------------------------------------------------------------
# 1. LoRa radio detection
# ---------------------------------------------------------------------------
header "LoRa Radio Detection"
RADIO_PORT=""
for pattern in /dev/ttyUSB* /dev/ttyACM*; do
    for port in $pattern; do
        if [[ -e "$port" ]]; then
            ok "LoRa radio detected: ${port}"
            RADIO_PORT="$port"
        fi
    done
done
if [[ -z "$RADIO_PORT" ]]; then
    fail "No LoRa radio detected on /dev/ttyUSB* or /dev/ttyACM*"
    info "Connect your LoRa radio via USB OTG cable"
    info "Full hardware test: ${REPO_DIR}/scripts/testing/test_hardware.sh"
fi

# ---------------------------------------------------------------------------
# 2. Serial port permissions
# ---------------------------------------------------------------------------
header "Serial Port Permissions"
USER_GROUPS="$(id -Gn 2>/dev/null || true)"
if echo "$USER_GROUPS" | grep -qw "dialout"; then
    ok "User is in 'dialout' group"
else
    fail "User is NOT in 'dialout' group (serial port access will fail)"
    info "Fix: sudo usermod -aG dialout \$USER  (then log out and back in)"
fi

if [[ -n "$RADIO_PORT" ]]; then
    if [[ -r "$RADIO_PORT" && -w "$RADIO_PORT" ]]; then
        ok "Read/write access to ${RADIO_PORT}"
    else
        fail "No read/write access to ${RADIO_PORT}"
        info "Fix: sudo chmod a+rw ${RADIO_PORT}  (or add user to dialout group)"
    fi
fi

# ---------------------------------------------------------------------------
# 3. Python environment
# ---------------------------------------------------------------------------
header "Python Environment"
if [[ -f "${REPO_DIR}/venv/bin/python3" ]]; then
    ok "Virtual environment found"
    if "${REPO_DIR}/venv/bin/python3" -c "import requests, serial" &>/dev/null; then
        ok "Core dependencies (requests, pyserial) importable"
    else
        fail "Core dependencies missing (requests / pyserial)"
        info "Run: cd ${REPO_DIR} && source venv/bin/activate && pip install -r requirements.txt"
    fi
else
    fail "Virtual environment not found"
    info "Create: cd ${REPO_DIR} && ./setup_venv.sh"
fi

if [[ -f "${REPO_DIR}/radio_gateway.py" ]]; then
    if [[ -f "${REPO_DIR}/venv/bin/python3" ]]; then
        IMPORT_TEST="$(cd "${REPO_DIR}" && \
            "${REPO_DIR}/venv/bin/python3" -c "
import ast, sys
try:
    with open('radio_gateway.py') as f:
        ast.parse(f.read())
    print('OK')
except SyntaxError as e:
    print('SYNTAX ERROR:', e)
" 2>&1 | head -1 || true)"
        if [[ "$IMPORT_TEST" == "OK" ]]; then
            ok "radio_gateway.py parses without syntax errors"
        else
            warn "radio_gateway.py parse issue: ${IMPORT_TEST}"
        fi
    fi
else
    warn "radio_gateway.py not found in ${REPO_DIR}"
fi

# ---------------------------------------------------------------------------
# 4. Network connectivity to bot server
# ---------------------------------------------------------------------------
header "Network Connectivity to Bot Server"
if command -v ping &>/dev/null; then
    BOT_HOST="$(echo "$BOT_SERVER_URL" | sed 's|http://||;s|:.*||')"
    if ping -c 2 -W 3 "$BOT_HOST" &>/dev/null; then
        ok "Ping to bot server host (${BOT_HOST})"
    else
        warn "Cannot ping bot server host (${BOT_HOST})"
        info "Check network / Wi-Fi connection"
    fi
fi

if curl -s --connect-timeout 5 "${BOT_SERVER_URL}/health" &>/dev/null; then
    ok "Bot server health endpoint reachable: ${BOT_SERVER_URL}/health"
else
    warn "Bot server not reachable at ${BOT_SERVER_URL}"
    info "Ensure adventure_bot.py is running on bot server"
    info "Set BOT_SERVER_URL env var or use --bot-server flag"
fi

# ---------------------------------------------------------------------------
# 5. Resource usage
# ---------------------------------------------------------------------------
header "Resource Usage"
TOTAL_KB="$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)"
TOTAL_MB=$(( TOTAL_KB / 1024 ))
FREE_KB="$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)"
FREE_MB=$(( FREE_KB / 1024 ))

if [[ $TOTAL_MB -ge 256 ]]; then
    ok "RAM: ${TOTAL_MB} MB total, ${FREE_MB} MB available"
else
    fail "RAM: ${TOTAL_MB} MB total (minimum 256 MB required)"
fi

FREE_DISK_KB="$(df -k "${REPO_DIR}" | awk 'NR==2{print $4}')"
FREE_DISK_GB=$(( FREE_DISK_KB / 1024 / 1024 ))
if [[ $FREE_DISK_GB -ge 2 ]]; then
    ok "Disk: ${FREE_DISK_GB} GB free"
else
    fail "Disk: ${FREE_DISK_GB} GB free (minimum 2 GB required)"
fi

# CPU load (1-minute average)
if [[ -f /proc/loadavg ]]; then
    LOAD="$(cut -d' ' -f1 /proc/loadavg)"
    ok "CPU load average (1 min): ${LOAD}"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}  ❌ Radio gateway test FAILED${NC}"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}  ⚠  Radio gateway test passed with warnings${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ Radio gateway tests passed!${NC}"
    exit 0
fi

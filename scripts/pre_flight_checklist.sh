#!/bin/bash
# pre_flight_checklist.sh - MCADV interactive pre-flight checklist
#
# Menu-driven checklist that guides through hardware- and role-specific
# deployment steps.
#
# Usage:
#   ./scripts/pre_flight_checklist.sh [-h|--help] [--role bot_server|radio_gateway]
#
# Exit codes:
#   0 - Checklist completed (all critical items checked)
#   1 - Checklist incomplete or cancelled

set -euo pipefail

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
if [[ -z "${NO_COLOR:-}" && -t 1 ]]; then
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    GREEN='' BLUE='' YELLOW='' RED='' CYAN='' NC=''
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FORCE_ROLE=""

usage() {
    cat <<EOF
Usage: $0 [-h|--help] [--role bot_server|radio_gateway]

Interactive pre-flight checklist for MCADV deployment.

Options:
  --role ROLE   Override auto-detected role (bot_server or radio_gateway)
  -h, --help    Show this help and exit

Exit codes:
  0 - Checklist completed
  1 - Cancelled or incomplete
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --role) FORCE_ROLE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# ---------------------------------------------------------------------------
# Hardware role detection (same logic as pre_deployment_check.sh)
# ---------------------------------------------------------------------------
detect_role() {
    local model=""
    [[ -f /proc/device-tree/model ]] && model="$(cat /proc/device-tree/model 2>/dev/null || true)"
    if echo "$model" | grep -qi "zero 2"; then echo "radio_gateway"
    elif echo "$model" | grep -qiE "pi [45]|pi 3"; then echo "bot_server"
    elif grep -qi "ubuntu" /etc/os-release 2>/dev/null; then echo "bot_server"
    elif pgrep -f "radio_gateway.py" &>/dev/null 2>&1; then echo "radio_gateway"
    elif pgrep -f "adventure_bot.py" &>/dev/null 2>&1; then echo "bot_server"
    else echo "unknown"
    fi
}

get_platform_label() {
    local model=""
    [[ -f /proc/device-tree/model ]] && model="$(cat /proc/device-tree/model 2>/dev/null || true)"
    if echo "$model" | grep -qi "zero 2"; then echo "Pi Zero 2W"
    elif echo "$model" | grep -qi "pi 5"; then echo "Pi 5"
    elif echo "$model" | grep -qi "pi 4"; then echo "Pi 4"
    elif grep -qi "ubuntu" /etc/os-release 2>/dev/null; then echo "Ubuntu Desktop"
    else echo "Unknown Hardware"
    fi
}

# ---------------------------------------------------------------------------
# Checklist item helpers
# ---------------------------------------------------------------------------
declare -A ITEM_STATUS  # "pass" | "fail" | "skip" | "pending"

auto_check() {
    local key="$1"
    local description="$2"
    shift 2
    # Remaining args are the test command
    if "$@" &>/dev/null 2>&1; then
        ITEM_STATUS["$key"]="pass"
        echo -e "  ${GREEN}[✓]${NC} ${description}"
    else
        ITEM_STATUS["$key"]="fail"
        echo -e "  ${RED}[ ]${NC} ${description}"
    fi
}

manual_check() {
    local key="$1"
    local description="$2"
    local default="${3:-n}"
    local answer
    echo -ne "  ${YELLOW}[?]${NC} ${description} (y/n) [${default}]: "
    read -r answer
    answer="${answer:-$default}"
    case "$answer" in
        [Yy]*) ITEM_STATUS["$key"]="pass"; echo -e "  ${GREEN}[✓]${NC} Marked as done" ;;
        *)     ITEM_STATUS["$key"]="skip"; echo -e "  ${YELLOW}[ ]${NC} Skipped / not done" ;;
    esac
}

section() { echo -e "\n${CYAN}$1${NC}"; }

# ---------------------------------------------------------------------------
# Bot Server checklist
# ---------------------------------------------------------------------------
run_bot_server_checklist() {
    section "SOFTWARE CHECKS:"
    auto_check "python"   "Python 3.7+ installed"          python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)"
    auto_check "venv"     "Virtual environment created"     test -f "${REPO_DIR}/venv/bin/python3"
    auto_check "deps"     "Dependencies installed"          "${REPO_DIR}/venv/bin/python3" -c "import flask, requests"
    auto_check "ollama"   "Ollama service running"          curl -s --connect-timeout 5 http://localhost:11434/api/tags
    auto_check "model"    "LLM model downloaded"            bash -c "curl -s http://localhost:11434/api/tags | grep -q 'name'"
    manual_check "config" "Configuration file reviewed"

    section "HARDWARE CHECKS:"
    auto_check "ram"      "Adequate RAM (≥2 GB)" \
        bash -c "awk '/MemTotal/{print \$2}' /proc/meminfo | awk '\$1 >= 2097152{exit 0} {exit 1}'"
    auto_check "disk"     "Adequate disk space (≥10 GB)" \
        bash -c "df -k '${REPO_DIR}' | awk 'NR==2{exit (\$4 >= 10485760 ? 0 : 1)}'"
    auto_check "port"     "Port 5000 available" \
        bash -c "! ss -tlnp 2>/dev/null | grep -q ':5000 '"
    manual_check "cooling" "Temperature monitoring / cooling configured"

    section "NETWORK CHECKS (Distributed Mode):"
    manual_check "gw_reach" "Radio gateway reachable"
    manual_check "firewall" "Firewall rules configured"
    manual_check "static_ip" "Static IP or hostname configured"

    section "OPERATIONAL CHECKS:"
    manual_check "power"   "Power solution identified"
    manual_check "backup"  "Backup strategy defined"
    manual_check "monitor" "Monitoring dashboard tested"
}

# ---------------------------------------------------------------------------
# Radio Gateway checklist
# ---------------------------------------------------------------------------
run_radio_gateway_checklist() {
    section "SOFTWARE CHECKS:"
    auto_check "python"   "Python 3.7+ installed"          python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)"
    auto_check "venv"     "Virtual environment created"     test -f "${REPO_DIR}/venv/bin/python3"
    auto_check "deps"     "Dependencies installed"          "${REPO_DIR}/venv/bin/python3" -c "import requests, serial"
    manual_check "config" "Configuration file reviewed (BOT_SERVER_URL set)"

    section "HARDWARE CHECKS:"
    auto_check "lora"     "LoRa radio detected" \
        bash -c "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | grep -q ."
    auto_check "serial"   "Serial port permissions (dialout group)" \
        bash -c "id -Gn | grep -qw dialout"
    auto_check "ram"      "Adequate RAM (≥256 MB)" \
        bash -c "awk '/MemTotal/{print \$2}' /proc/meminfo | awk '\$1 >= 262144{exit 0} {exit 1}'"
    auto_check "disk"     "Adequate disk space (≥2 GB)" \
        bash -c "df -k '${REPO_DIR}' | awk 'NR==2{exit (\$4 >= 2097152 ? 0 : 1)}'"

    section "NETWORK CHECKS:"
    local bot_url="${BOT_SERVER_URL:-http://localhost:5000}"
    auto_check "bot_reach" "Bot server reachable (${bot_url})" \
        curl -s --connect-timeout 5 "${bot_url}/health"
    manual_check "static_ip" "Static IP or hostname configured"

    section "OPERATIONAL CHECKS:"
    manual_check "power"   "Power solution identified"
    manual_check "antenna" "Antenna positioned vertically"
    manual_check "enclosure" "Enclosure / weatherproofing in place"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
ROLE="${FORCE_ROLE:-$(detect_role)}"
PLATFORM_LABEL="$(get_platform_label)"

if [[ "$ROLE" == "bot_server" ]]; then
    ROLE_COLOUR="$GREEN"
    ROLE_LABEL="BOT SERVER"
elif [[ "$ROLE" == "radio_gateway" ]]; then
    ROLE_COLOUR="$BLUE"
    ROLE_LABEL="RADIO GATEWAY"
else
    ROLE_COLOUR="$YELLOW"
    ROLE_LABEL="UNKNOWN ROLE"
fi

clear
echo ""
echo -e "${ROLE_COLOUR}==========================================${NC}"
echo -e "${ROLE_COLOUR}  MCADV Pre-Flight Checklist${NC}"
echo -e "${ROLE_COLOUR}  Hardware Role: [${ROLE_LABEL} - ${PLATFORM_LABEL}]${NC}"
echo -e "${ROLE_COLOUR}==========================================${NC}"

case "$ROLE" in
    bot_server)    run_bot_server_checklist ;;
    radio_gateway) run_radio_gateway_checklist ;;
    *)
        echo -e "\n${YELLOW}Hardware role could not be determined.${NC}"
        echo "Override with: $0 --role bot_server"
        echo "           or: $0 --role radio_gateway"
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Automated test offer
# ---------------------------------------------------------------------------
echo ""
echo -ne "${CYAN}Would you like to run automated pre-deployment checks? (y/n) [y]: ${NC}"
read -r run_auto
run_auto="${run_auto:-y}"
if [[ "$run_auto" =~ ^[Yy] ]]; then
    echo ""
    bash "${SCRIPT_DIR}/pre_deployment_check.sh" --role "$ROLE" || true
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=${#ITEM_STATUS[@]}
PASSED=0
FAILED=0
for val in "${ITEM_STATUS[@]}"; do
    [[ "$val" == "pass" ]] && PASSED=$(( PASSED + 1 ))
    [[ "$val" == "fail" ]] && FAILED=$(( FAILED + 1 ))
done

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "  Checklist: ${GREEN}${PASSED}/${TOTAL} items done${NC}  ${RED}${FAILED} incomplete${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}  ✅ Pre-flight checklist complete!${NC}"
    exit 0
else
    echo -e "${YELLOW}  ⚠  Some checklist items need attention before deployment${NC}"
    exit 1
fi

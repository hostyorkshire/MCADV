#!/bin/bash
# pre_deployment_check.sh - MCADV master pre-deployment verification
#
# Auto-detects hardware role and runs role-specific checks.
#
# Usage:
#   ./scripts/pre_deployment_check.sh [-h|--help] [--role bot_server|radio_gateway]
#
# Exit codes:
#   0 - All checks passed
#   1 - Warnings (non-critical)
#   2 - One or more failures

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour codes (disabled when NO_COLOR is set or not a terminal)
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
PASS=0
WARN=0
FAIL=0
FORCE_ROLE=""

usage() {
    cat <<EOF
Usage: $0 [-h|--help] [--role bot_server|radio_gateway]

MCADV master pre-deployment verification script.

Auto-detects hardware role and runs role-specific checks.

Options:
  --role ROLE   Override auto-detected role (bot_server or radio_gateway)
  -h, --help    Show this help and exit

Exit codes:
  0 - All checks passed
  1 - Warnings (non-critical issues found)
  2 - Failures (critical issues found)
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --role) FORCE_ROLE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------
ok()     { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$(( PASS + 1 )); }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$(( WARN + 1 )); }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$(( FAIL + 1 )); }
info()   { echo -e "       ${BLUE}→${NC} $1"; }
header() { echo -e "\n${CYAN}─── $1 ───${NC}"; }

# ---------------------------------------------------------------------------
# Hardware role detection
# ---------------------------------------------------------------------------
detect_role() {
    local model=""
    [[ -f /proc/device-tree/model ]] && model="$(cat /proc/device-tree/model 2>/dev/null || true)"

    if echo "$model" | grep -qi "zero 2"; then
        echo "radio_gateway"
    elif echo "$model" | grep -qiE "pi [45]|pi 3"; then
        echo "bot_server"
    elif grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
        echo "bot_server"
    elif pgrep -f "radio_gateway.py" &>/dev/null 2>&1; then
        echo "radio_gateway"
    elif pgrep -f "adventure_bot.py" &>/dev/null 2>&1; then
        echo "bot_server"
    else
        echo "unknown"
    fi
}

get_platform_label() {
    local model=""
    [[ -f /proc/device-tree/model ]] && model="$(cat /proc/device-tree/model 2>/dev/null || true)"

    if echo "$model" | grep -qi "zero 2"; then
        echo "Pi Zero 2W"
    elif echo "$model" | grep -qi "pi 5"; then
        echo "Pi 5"
    elif echo "$model" | grep -qi "pi 4"; then
        echo "Pi 4"
    elif echo "$model" | grep -qi "pi 3"; then
        echo "Pi 3"
    elif grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
        echo "Ubuntu Desktop"
    else
        echo "Unknown Hardware"
    fi
}

# ---------------------------------------------------------------------------
# Shared checks
# ---------------------------------------------------------------------------
check_python() {
    header "Python Environment"
    if command -v python3 &>/dev/null; then
        local ver
        ver="$(python3 --version 2>&1)"
        local major minor
        major="$(python3 -c 'import sys; print(sys.version_info.major)')"
        minor="$(python3 -c 'import sys; print(sys.version_info.minor)')"
        if [[ $major -ge 3 && $minor -ge 7 ]]; then
            ok "Python: $ver"
        else
            fail "Python too old: $ver (need 3.7+)"
        fi
    else
        fail "python3 not found"
        info "Install: sudo apt install python3"
    fi

    if [[ -f "${REPO_DIR}/venv/bin/python3" ]]; then
        ok "Virtual environment exists"
    else
        warn "Virtual environment not found"
        info "Create: cd ${REPO_DIR} && ./setup_venv.sh"
    fi

    if [[ -f "${REPO_DIR}/venv/bin/python3" && -f "${REPO_DIR}/requirements.txt" ]]; then
        local missing
        missing="$(cd "${REPO_DIR}" && "${REPO_DIR}/venv/bin/python3" -c "
import pkg_resources
try:
    with open('requirements.txt') as f:
        pkg_resources.require(f.readlines())
    print('OK')
except Exception as e:
    print(str(e))
" 2>/dev/null || echo "ERROR")"
        if [[ "$missing" == "OK" ]]; then
            ok "All dependencies installed"
        else
            warn "Dependency issue: $missing"
            info "Run: cd ${REPO_DIR} && source venv/bin/activate && pip install -r requirements.txt"
        fi
    fi
}

check_disk_space() {
    local min_gb="$1"
    header "Disk Space"
    local free_kb free_gb
    free_kb="$(df -k "${REPO_DIR}" | awk 'NR==2{print $4}')"
    free_gb=$(( free_kb / 1024 / 1024 ))
    if [[ $free_gb -ge $min_gb ]]; then
        ok "Disk space: ${free_gb} GB free (minimum ${min_gb} GB required)"
    else
        fail "Disk space: ${free_gb} GB free (need at least ${min_gb} GB)"
        info "Free up disk space before deploying"
    fi
}

check_ram() {
    local min_mb="$1"
    header "RAM"
    local total_kb total_mb
    total_kb="$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)"
    total_mb=$(( total_kb / 1024 ))
    if [[ $total_mb -ge $min_mb ]]; then
        ok "RAM: ${total_mb} MB total (minimum ${min_mb} MB required)"
    else
        fail "RAM: ${total_mb} MB total (need at least ${min_mb} MB)"
    fi
}

# ---------------------------------------------------------------------------
# Bot Server checks
# ---------------------------------------------------------------------------
run_bot_server_checks() {
    echo -e "\n${GREEN}Running BOT SERVER checks…${NC}"

    check_python
    check_ram 2048
    check_disk_space 10

    header "Ollama"
    if command -v ollama &>/dev/null; then
        ok "Ollama installed: $(ollama --version 2>/dev/null | head -1 || echo 'version unknown')"
        if curl -s --connect-timeout 5 http://localhost:11434/api/tags &>/dev/null; then
            ok "Ollama running on localhost:11434"
        else
            warn "Ollama installed but not running"
            info "Start: ollama serve   (or: sudo systemctl start ollama)"
        fi
    else
        warn "Ollama not installed (offline mode will still work)"
        info "Install: curl -fsSL https://ollama.ai/install.sh | sh"
    fi

    header "Port 5000"
    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ':5000 '; then
            warn "Port 5000 already in use"
            info "Another process is listening on port 5000"
        else
            ok "Port 5000 is available"
        fi
    else
        info "Cannot check port 5000 (ss not available)"
    fi

    header "Temperature Monitoring"
    if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
        local temp
        temp="$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0)"
        temp_c=$(( temp / 1000 ))
        ok "CPU temperature readable: ${temp_c}°C"
    elif command -v vcgencmd &>/dev/null; then
        ok "vcgencmd available for temperature monitoring"
    else
        info "Temperature monitoring not available on this platform"
    fi
}

# ---------------------------------------------------------------------------
# Radio Gateway checks
# ---------------------------------------------------------------------------
run_radio_gateway_checks() {
    echo -e "\n${BLUE}Running RADIO GATEWAY checks…${NC}"

    check_python
    check_ram 256
    check_disk_space 2

    header "LoRa Radio Detection"
    local radio_found=false
    for pattern in /dev/ttyUSB* /dev/ttyACM*; do
        for port in $pattern; do
            if [[ -e "$port" ]]; then
                ok "LoRa radio detected: $port"
                radio_found=true
            fi
        done
    done
    if [[ "$radio_found" == false ]]; then
        fail "No LoRa radio detected on /dev/ttyUSB* or /dev/ttyACM*"
        info "Connect your LoRa radio via USB"
        info "Test: ${REPO_DIR}/scripts/testing/test_hardware.sh"
    fi

    header "Serial Port Permissions"
    local user_groups
    user_groups="$(id -Gn 2>/dev/null || true)"
    if echo "$user_groups" | grep -qw "dialout"; then
        ok "User is in 'dialout' group (serial port access)"
    else
        warn "User is NOT in 'dialout' group"
        info "Fix: sudo usermod -aG dialout \$USER  (then log out and back in)"
    fi

    header "Network Connectivity to Bot Server"
    local bot_url="${BOT_SERVER_URL:-http://localhost:5000}"
    if curl -s --connect-timeout 5 "${bot_url}/health" &>/dev/null; then
        ok "Bot server reachable at ${bot_url}"
    else
        warn "Bot server not reachable at ${bot_url}"
        info "Set BOT_SERVER_URL environment variable or start bot server"
        info "Test: ${REPO_DIR}/scripts/testing/test_network_connectivity.sh --bot-server <hostname>"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
ROLE="${FORCE_ROLE:-$(detect_role)}"
PLATFORM_LABEL="$(get_platform_label)"

# Banner
echo ""
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

echo -e "${ROLE_COLOUR}╔══════════════════════════════════════════════╗${NC}"
echo -e "${ROLE_COLOUR}║  MCADV Pre-Deployment Check                  ║${NC}"
echo -e "${ROLE_COLOUR}║  [${ROLE_LABEL} - ${PLATFORM_LABEL}]${NC}"
echo -e "${ROLE_COLOUR}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Repo:      ${REPO_DIR}"
echo "  Timestamp: $(date)"
echo "  Role:      ${ROLE_LABEL}"

case "$ROLE" in
    bot_server)     run_bot_server_checks ;;
    radio_gateway)  run_radio_gateway_checks ;;
    *)
        warn "Hardware role unknown – running generic checks only"
        check_python
        check_disk_space 2
        ;;
esac

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}  ❌ Pre-deployment check FAILED – fix failures before deploying${NC}"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}  ⚠  Pre-deployment check PASSED with warnings${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ All pre-deployment checks passed!${NC}"
    exit 0
fi

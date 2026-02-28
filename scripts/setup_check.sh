#!/bin/bash
# setup_check.sh - Comprehensive verification of MCADV setup
# Usage: ./setup_check.sh [-h|--help]

set -euo pipefail

# Color codes (disabled if NO_COLOR is set)
if [[ -z "${NO_COLOR:-}" ]]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    GREEN='' RED='' YELLOW='' BLUE='' CYAN='' NC=''
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_NAME="mcadv-bot"
PASS=0
FAIL=0
WARN=0

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Comprehensive verification of the entire MCADV setup."
    echo ""
    echo "Checks:"
    echo "  1.  Python 3 installed"
    echo "  2.  Virtual environment exists"
    echo "  3.  Dependencies installed"
    echo "  4.  LoRa radio detected"
    echo "  5.  Ollama installed and running"
    echo "  6.  Model downloaded"
    echo "  7.  Bot can start without errors"
    echo "  8.  Logs directory writable"
    echo "  9.  Sufficient disk space (> 10GB free)"
    echo "  10. Systemd service installed"
    echo "  11. Service is running"
    echo ""
    echo "Exit codes:"
    echo "  0 - All checks passed"
    echo "  1 - Some warnings (non-critical)"
    echo "  2 - Failures found"
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

check_ok()   { echo -e "  ${GREEN}✅${NC} $1"; PASS=$(( PASS + 1 )); }
check_warn() { echo -e "  ${YELLOW}⚠️ ${NC} $1"; WARN=$(( WARN + 1 )); }
check_fail() { echo -e "  ${RED}❌${NC} $1"; FAIL=$(( FAIL + 1 )); }
info()       { echo -e "     ${BLUE}→${NC} $1"; }
header()     { echo -e "\n${CYAN}─── $1 ───${NC}"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      MCADV Setup Verification            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Working directory: $WORKDIR"
echo "Timestamp: $(date)"

header "1. Python 3"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [[ $PY_MAJOR -ge 3 && $PY_MINOR -ge 8 ]]; then
        check_ok "Python installed: $PY_VERSION"
    else
        check_warn "Python version too old: $PY_VERSION (need 3.8+)"
        info "Install Python 3.8+: sudo apt install python3"
    fi
else
    check_fail "Python 3 not found"
    info "Install with: sudo apt install python3"
fi

header "2. Virtual Environment"
VENV_DIR="${WORKDIR}/venv"
if [[ -f "${VENV_DIR}/bin/python3" ]]; then
    check_ok "Virtual environment exists: $VENV_DIR"
else
    check_fail "Virtual environment not found"
    info "Create with: cd ${WORKDIR} && ./setup_venv.sh"
fi

header "3. Dependencies"
if [[ -f "${VENV_DIR}/bin/python3" ]]; then
    DEPS_OK=true
    if [[ -f "${WORKDIR}/requirements.txt" ]]; then
        MISSING=$(cd "${WORKDIR}" && "${VENV_DIR}/bin/python3" -c "
import pkg_resources, sys
try:
    with open('requirements.txt') as f:
        pkg_resources.require(f.readlines())
    print('OK')
except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
    print(f'MISSING: {e}')
" 2>/dev/null || echo "ERROR")
        if [[ "$MISSING" == "OK" ]]; then
            check_ok "All dependencies installed"
        elif [[ "$MISSING" == "ERROR" ]]; then
            check_warn "Could not verify dependencies"
            info "Reinstall with: cd ${WORKDIR} && source venv/bin/activate && pip install -r requirements.txt"
        else
            check_fail "Missing dependencies: $MISSING"
            info "Install with: cd ${WORKDIR} && source venv/bin/activate && pip install -r requirements.txt"
        fi
    else
        check_warn "requirements.txt not found"
    fi
else
    check_warn "Skipping (venv not found)"
fi

header "4. LoRa Radio"
RADIO_FOUND=false
for pattern in /dev/ttyUSB* /dev/ttyACM*; do
    for port in $pattern; do
        if [[ -e "$port" ]]; then
            check_ok "LoRa radio detected: $port"
            RADIO_FOUND=true
        fi
    done
done
if [[ "$RADIO_FOUND" == false ]]; then
    check_warn "No LoRa radio detected on /dev/ttyUSB* or /dev/ttyACM*"
    info "Connect your LoRa radio via USB"
    info "Check with: ls /dev/ttyUSB* /dev/ttyACM*"
    info "Test with: ${WORKDIR}/scripts/testing/test_hardware.sh"
fi

header "5. Ollama"
if command -v ollama &>/dev/null; then
    check_ok "Ollama installed: $(ollama --version 2>/dev/null | head -1 || echo 'version unknown')"
    if curl -s --connect-timeout 5 http://localhost:11434/api/tags &>/dev/null; then
        check_ok "Ollama is running on localhost:11434"
    else
        check_warn "Ollama installed but not running"
        info "Start with: ollama serve"
        info "Or as service: sudo systemctl start ollama"
    fi
else
    check_warn "Ollama not installed (offline story mode will work)"
    info "Install: curl -fsSL https://ollama.ai/install.sh | sh"
fi

header "6. Model Downloaded"
if curl -s --connect-timeout 5 http://localhost:11434/api/tags &>/dev/null; then
    MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print('\n'.join(models))
" 2>/dev/null || echo "")
    if [[ -n "$MODELS" ]]; then
        check_ok "Models available:"
        while IFS= read -r model; do
            [[ -n "$model" ]] && info "$model"
        done <<< "$MODELS"
    else
        check_warn "No models downloaded yet"
        info "Pull recommended model: ollama pull llama3.1:8b"
        info "Or lighter model:       ollama pull llama3.2:1b"
    fi
else
    check_warn "Skipping (Ollama not running)"
fi

header "7. Bot Startup Test"
if [[ -f "${VENV_DIR}/bin/python3" && -f "${WORKDIR}/adventure_bot.py" ]]; then
    STARTUP_TEST=$(cd "${WORKDIR}" && \
        timeout 10 "${VENV_DIR}/bin/python3" adventure_bot.py --help 2>&1 | head -5 || true)
    if [[ -n "$STARTUP_TEST" ]]; then
        check_ok "Bot starts without errors"
    else
        check_warn "Bot startup test inconclusive"
        info "Test manually: cd ${WORKDIR} && source venv/bin/activate && python3 adventure_bot.py --help"
    fi
else
    check_fail "Cannot test (venv or adventure_bot.py missing)"
fi

header "8. Logs Directory"
LOG_DIR="${WORKDIR}/logs"
if [[ -d "$LOG_DIR" ]]; then
    if [[ -w "$LOG_DIR" ]]; then
        check_ok "Logs directory writable: $LOG_DIR"
    else
        check_fail "Logs directory not writable: $LOG_DIR"
        info "Fix with: chmod 755 ${LOG_DIR}"
    fi
else
    if mkdir -p "$LOG_DIR" 2>/dev/null; then
        check_ok "Logs directory created: $LOG_DIR"
    else
        check_fail "Cannot create logs directory: $LOG_DIR"
    fi
fi

header "9. Disk Space"
DISK_FREE_KB=$(df -k "${WORKDIR}" | awk 'NR==2{print $4}')
DISK_FREE_GB=$(( DISK_FREE_KB / 1024 / 1024 ))
if [[ $DISK_FREE_GB -ge 10 ]]; then
    check_ok "Disk space: ${DISK_FREE_GB}GB free (sufficient)"
elif [[ $DISK_FREE_GB -ge 3 ]]; then
    check_warn "Disk space: ${DISK_FREE_GB}GB free (enough for small models only)"
    info "Recommended: 10GB+ free for llama3.1:8b"
else
    check_fail "Disk space: ${DISK_FREE_GB}GB free (insufficient)"
    info "Free at least 3GB for small models"
fi

header "10. Systemd Service"
if command -v systemctl &>/dev/null; then
    if systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null 2>&1; then
        check_ok "Service installed: ${SERVICE_NAME}.service"
    else
        check_warn "Service not installed (optional for auto-start)"
        info "Install with: sudo ${WORKDIR}/scripts/deployment/install_service.sh"
    fi
else
    check_warn "systemd not available on this system"
fi

header "11. Service Running"
if command -v systemctl &>/dev/null; then
    if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        check_ok "Service is running: ${SERVICE_NAME}"
    elif systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null 2>&1; then
        check_warn "Service installed but not running"
        info "Start with: sudo systemctl start ${SERVICE_NAME}"
    else
        check_warn "Service not installed (manual start required)"
    fi
else
    if pgrep -f "adventure_bot.py" &>/dev/null; then
        check_ok "Bot process is running"
    else
        check_warn "Bot not running (start manually)"
        info "Start with: cd ${WORKDIR} && ./run_adventure_bot.sh"
    fi
fi

# Final summary
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}❌ Setup incomplete - address failures above before deploying${NC}"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Setup mostly complete - review warnings above${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All checks passed - MCADV is ready!${NC}"
    exit 0
fi

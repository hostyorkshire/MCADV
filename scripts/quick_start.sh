#!/bin/bash
# quick_start.sh - Interactive guided setup wizard for MCADV
# Usage: ./quick_start.sh [-h|--help]

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
CONFIG_FILE="${WORKDIR}/.mcadv_config"
SERVICE_NAME="mcadv-bot"
READ_TIMEOUT=30

ok()     { echo -e "${GREEN}✓${NC} $1"; }
err()    { echo -e "${RED}✗${NC} $1"; }
warn()   { echo -e "${YELLOW}⚠${NC} $1"; }
info()   { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}═══ $1 ═══${NC}"; }
step()   { echo -e "\n${CYAN}Step $1:${NC} $2"; }
ask()    { echo -e "${YELLOW}?${NC} $1"; }

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Interactive guided setup wizard for MCADV."
    echo ""
    echo "Steps:"
    echo "  1. Check prerequisites"
    echo "  2. Setup virtual environment (if needed)"
    echo "  3. Detect/select LoRa radio serial port"
    echo "  4. Check Ollama, offer to install if missing"
    echo "  5. Download recommended model if needed"
    echo "  6. Test bot with simple command"
    echo "  7. Offer to install systemd service"
    echo "  8. Offer to enable auto-start"
    echo "  9. Display next steps"
    echo ""
    echo "Saves choices to: ${CONFIG_FILE}"
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

# Load existing config if present
SAVED_PORT=""
SAVED_MODEL=""
SAVED_CHANNEL=""
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       MCADV Quick Start Wizard               ║${NC}"
echo -e "${CYAN}║  MeshCore Adventure Bot Setup                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "Working directory: $WORKDIR"
echo "Config file: $CONFIG_FILE"
echo ""
echo "This wizard will guide you through setting up MCADV."
echo "Press Ctrl+C at any time to exit."

# ─── Step 1: Prerequisites ────────────────────────────────────────────────────
step "1" "Checking Prerequisites"

PREREQ_OK=true

# Python 3
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1)
    ok "Python: $PY_VER"
else
    err "Python 3 not found"
    info "Install: sudo apt install python3 python3-pip python3-venv"
    PREREQ_OK=false
fi

# pip/venv
if python3 -m venv --help &>/dev/null; then
    ok "python3-venv available"
else
    warn "python3-venv not found"
    info "Install: sudo apt install python3-venv"
fi

# curl
if command -v curl &>/dev/null; then
    ok "curl available"
else
    warn "curl not found (needed for Ollama tests)"
    info "Install: sudo apt install curl"
fi

if [[ "$PREREQ_OK" == false ]]; then
    err "Prerequisites not met. Please install missing tools and re-run."
    exit 2
fi

# ─── Step 2: Virtual Environment ─────────────────────────────────────────────
step "2" "Virtual Environment"

VENV_DIR="${WORKDIR}/venv"
if [[ -f "${VENV_DIR}/bin/python3" ]]; then
    ok "Virtual environment already exists: $VENV_DIR"
else
    warn "Virtual environment not found"
    ask "Create virtual environment now? [Y/n]"
    read -r -t $READ_TIMEOUT CREATE_VENV || CREATE_VENV="y"
    if [[ "${CREATE_VENV,,}" != "n" ]]; then
        if [[ -f "${WORKDIR}/setup_venv.sh" ]]; then
            cd "$WORKDIR" && bash setup_venv.sh
            ok "Virtual environment created"
        else
            python3 -m venv "${VENV_DIR}"
            "${VENV_DIR}/bin/pip" install --upgrade pip -q
            "${VENV_DIR}/bin/pip" install -r "${WORKDIR}/requirements.txt" -q
            ok "Virtual environment created and dependencies installed"
        fi
    else
        warn "Skipping venv creation - bot may not work without it"
    fi
fi

# ─── Step 3: LoRa Radio Port ──────────────────────────────────────────────────
step "3" "LoRa Radio Serial Port"

SERIAL_PORTS=()
for pattern in /dev/ttyUSB* /dev/ttyACM*; do
    for port in $pattern; do
        [[ -e "$port" ]] && SERIAL_PORTS+=("$port")
    done
done

SELECTED_PORT="${SAVED_PORT:-}"
if [[ ${#SERIAL_PORTS[@]} -eq 0 ]]; then
    warn "No serial devices found on /dev/ttyUSB* or /dev/ttyACM*"
    info "Connect your LoRa radio and re-run, or run in HTTP-only mode"
    SELECTED_PORT="auto"
elif [[ ${#SERIAL_PORTS[@]} -eq 1 ]]; then
    SELECTED_PORT="${SERIAL_PORTS[0]}"
    ok "Auto-detected radio: $SELECTED_PORT"
else
    ok "Multiple serial ports found:"
    for i in "${!SERIAL_PORTS[@]}"; do
        info "  $((i+1)). ${SERIAL_PORTS[$i]}"
    done
    ask "Select port number [1-${#SERIAL_PORTS[@]}] (default: 1):"
    read -r -t $READ_TIMEOUT PORT_CHOICE || PORT_CHOICE="1"
    PORT_IDX=$(( ${PORT_CHOICE:-1} - 1 ))
    SELECTED_PORT="${SERIAL_PORTS[$PORT_IDX]:-${SERIAL_PORTS[0]}}"
    ok "Selected: $SELECTED_PORT"
fi

# ─── Step 4: Ollama ───────────────────────────────────────────────────────────
step "4" "Ollama LLM Backend"

OLLAMA_RUNNING=false
if curl -s --connect-timeout 5 http://localhost:11434/api/tags &>/dev/null; then
    ok "Ollama is already running"
    OLLAMA_RUNNING=true
elif command -v ollama &>/dev/null; then
    warn "Ollama installed but not running"
    ask "Start Ollama now? [Y/n]"
    read -r -t $READ_TIMEOUT START_OLLAMA || START_OLLAMA="y"
    if [[ "${START_OLLAMA,,}" != "n" ]]; then
        ollama serve &>/dev/null &
        sleep 3
        if curl -s --connect-timeout 5 http://localhost:11434/api/tags &>/dev/null; then
            ok "Ollama started"
            OLLAMA_RUNNING=true
        else
            warn "Ollama may still be starting - check with: curl http://localhost:11434/api/tags"
        fi
    fi
else
    warn "Ollama not installed"
    info "MCADV will work with offline story trees without Ollama"
    ask "Install Ollama now? [y/N]"
    read -r -t $READ_TIMEOUT INSTALL_OLLAMA || INSTALL_OLLAMA="n"
    if [[ "${INSTALL_OLLAMA,,}" == "y" ]]; then
        if command -v curl &>/dev/null; then
            curl -fsSL https://ollama.ai/install.sh | sh
            ok "Ollama installed"
            ollama serve &>/dev/null &
            sleep 3
            OLLAMA_RUNNING=true
        else
            err "curl not found - cannot install Ollama automatically"
            info "Install manually: https://ollama.ai"
        fi
    fi
fi

# ─── Step 5: Model Download ───────────────────────────────────────────────────
step "5" "Ollama Model"

SELECTED_MODEL="${SAVED_MODEL:-llama3.1:8b}"
if [[ "$OLLAMA_RUNNING" == true ]]; then
    MEM_MB=$(free -m | awk '/Mem:/{print $2}')
    if [[ $MEM_MB -ge 6000 ]]; then
        DEFAULT_MODEL="llama3.1:8b"
    elif [[ $MEM_MB -ge 3000 ]]; then
        DEFAULT_MODEL="llama3.2:3b"
    else
        DEFAULT_MODEL="llama3.2:1b"
    fi

    info "RAM detected: ${MEM_MB}MB - recommended model: $DEFAULT_MODEL"

    EXISTING=$(curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('\n'.join(m['name'] for m in data.get('models', [])))
" 2>/dev/null || echo "")

    if [[ -n "$EXISTING" ]]; then
        ok "Models already downloaded:"
        while IFS= read -r m; do [[ -n "$m" ]] && info "  - $m"; done <<< "$EXISTING"
        ask "Download additional model? (press Enter to skip, or enter model name):"
        read -r -t $READ_TIMEOUT EXTRA_MODEL || EXTRA_MODEL=""
        if [[ -n "$EXTRA_MODEL" ]]; then
            ollama pull "$EXTRA_MODEL"
            SELECTED_MODEL="$EXTRA_MODEL"
        else
            SELECTED_MODEL=$(echo "$EXISTING" | head -1)
        fi
    else
        ask "Download $DEFAULT_MODEL now? (~3-5GB, may take several minutes) [Y/n]:"
        read -r -t $READ_TIMEOUT DOWNLOAD_MODEL || DOWNLOAD_MODEL="y"
        if [[ "${DOWNLOAD_MODEL,,}" != "n" ]]; then
            ollama pull "$DEFAULT_MODEL"
            SELECTED_MODEL="$DEFAULT_MODEL"
            ok "Model downloaded: $SELECTED_MODEL"
        fi
    fi
fi

# ─── Step 6: Test Bot ─────────────────────────────────────────────────────────
step "6" "Bot Test"

SELECTED_CHANNEL="${SAVED_CHANNEL:-1}"
ask "Which channel index to use? [default: 1]:"
read -r -t $READ_TIMEOUT CHAN_INPUT || CHAN_INPUT="1"
SELECTED_CHANNEL="${CHAN_INPUT:-1}"

if [[ -f "${VENV_DIR}/bin/python3" ]]; then
    info "Testing bot startup..."
    if timeout 5 "${VENV_DIR}/bin/python3" "${WORKDIR}/adventure_bot.py" --help &>/dev/null; then
        ok "Bot responds to --help"
    else
        warn "Bot startup test inconclusive"
    fi
fi

# ─── Step 7: Systemd Service ─────────────────────────────────────────────────
step "7" "Systemd Service (optional)"

if command -v systemctl &>/dev/null; then
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    if [[ -f "$SERVICE_FILE" ]]; then
        ok "Service already installed: $SERVICE_FILE"
    else
        ask "Install systemd service for auto-start? [y/N]:"
        read -r -t $READ_TIMEOUT INSTALL_SVC || INSTALL_SVC="n"
        if [[ "${INSTALL_SVC,,}" == "y" ]]; then
            if [[ -f "${WORKDIR}/scripts/deployment/install_service.sh" ]]; then
                sudo bash "${WORKDIR}/scripts/deployment/install_service.sh"
            else
                warn "install_service.sh not found"
                info "Install manually: sudo cp scripts/deployment/mcadv-bot.service /etc/systemd/system/"
            fi
        fi
    fi
else
    warn "systemd not available - manual start required"
fi

# ─── Step 8: Enable Auto-Start ────────────────────────────────────────────────
step "8" "Auto-Start on Boot"

if command -v systemctl &>/dev/null; then
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    if [[ -f "$SERVICE_FILE" ]]; then
        if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
            ok "Auto-start already enabled"
        else
            ask "Enable auto-start on boot? [y/N]:"
            read -r -t $READ_TIMEOUT ENABLE_BOOT || ENABLE_BOOT="n"
            if [[ "${ENABLE_BOOT,,}" == "y" ]]; then
                sudo systemctl enable "${SERVICE_NAME}"
                ok "Auto-start enabled"
            fi
        fi
    fi
fi

# ─── Save Config ─────────────────────────────────────────────────────────────
cat > "$CONFIG_FILE" << EOF
# MCADV Configuration - saved by quick_start.sh on $(date)
SAVED_PORT="${SELECTED_PORT}"
SAVED_MODEL="${SELECTED_MODEL}"
SAVED_CHANNEL="${SELECTED_CHANNEL}"
EOF
ok "Configuration saved to $CONFIG_FILE"

# ─── Step 9: Next Steps ───────────────────────────────────────────────────────
step "9" "Setup Complete - Next Steps"
echo ""
echo -e "${GREEN}✅ MCADV is configured!${NC}"
echo ""
echo "Your configuration:"
info "  Port:    ${SELECTED_PORT}"
info "  Model:   ${SELECTED_MODEL}"
info "  Channel: ${SELECTED_CHANNEL}"
echo ""
echo "To start the bot manually:"
if [[ "$SELECTED_PORT" != "auto" && -n "$SELECTED_PORT" ]]; then
    echo "  cd ${WORKDIR}"
    echo "  source venv/bin/activate"
    if [[ "$OLLAMA_RUNNING" == true ]]; then
        echo "  python3 adventure_bot.py --port ${SELECTED_PORT} --channel-idx ${SELECTED_CHANNEL} \\"
        echo "    --ollama-url http://localhost:11434 --model ${SELECTED_MODEL} --announce"
    else
        echo "  python3 adventure_bot.py --port ${SELECTED_PORT} --channel-idx ${SELECTED_CHANNEL} --announce"
    fi
else
    echo "  cd ${WORKDIR} && ./run_adventure_bot.sh --channel-idx ${SELECTED_CHANNEL}"
fi
echo ""
echo "Useful commands:"
echo "  Monitor:    ${WORKDIR}/scripts/monitoring/monitor_bot.sh"
echo "  Check setup: ${WORKDIR}/scripts/setup_check.sh"
echo "  Test hardware: ${WORKDIR}/scripts/testing/test_hardware.sh"
echo "  Manage service: ${WORKDIR}/scripts/deployment/manage_service.sh"
echo ""
echo "Documentation:"
echo "  guides/PRODUCTION_DEPLOYMENT.md"
echo "  docs/TESTING_GUIDE.md"

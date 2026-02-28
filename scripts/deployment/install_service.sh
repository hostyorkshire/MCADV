#!/bin/bash
# install_service.sh - Install MCADV bot as a systemd service
# Usage: ./install_service.sh [-h|--help]

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
WORKDIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"
SERVICE_NAME="mcadv-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TEMPLATE="${SCRIPT_DIR}/mcadv-bot.service"

ok()   { echo -e "${GREEN}✓${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Install MCADV adventure bot as a systemd service."
    echo ""
    echo "This script will:"
    echo "  1. Verify prerequisites (venv, Ollama)"
    echo "  2. Create service file from template"
    echo "  3. Install to /etc/systemd/system/"
    echo "  4. Reload systemd daemon"
    echo "  5. Optionally enable auto-start on boot"
    echo ""
    echo "Requires sudo privileges."
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

header "MCADV Service Installation"
echo "Timestamp: $(date)"
echo "Working directory: $WORKDIR"
echo "Service user: $CURRENT_USER"

# Check sudo privileges
if [[ $EUID -ne 0 ]]; then
    err "This script must be run with sudo"
    echo ""
    echo "Run: sudo $0"
    exit 2
fi

# Check systemd
header "Prerequisites"
if command -v systemctl &>/dev/null; then
    ok "systemd available"
else
    err "systemd not found - cannot install service"
    exit 2
fi

# Check template exists
if [[ -f "$TEMPLATE" ]]; then
    ok "Service template found: $TEMPLATE"
else
    err "Service template not found: $TEMPLATE"
    exit 2
fi

# Check virtual environment
if [[ -f "${WORKDIR}/venv/bin/python3" ]]; then
    ok "Virtual environment found: ${WORKDIR}/venv"
else
    err "Virtual environment not found at ${WORKDIR}/venv"
    echo ""
    echo "Create it with:"
    echo "  cd ${WORKDIR}"
    echo "  ./setup_venv.sh"
    exit 2
fi

# Check adventure_bot.py
if [[ -f "${WORKDIR}/adventure_bot.py" ]]; then
    ok "adventure_bot.py found"
else
    err "adventure_bot.py not found in ${WORKDIR}"
    exit 2
fi

# Check Ollama (warning only - may use offline mode)
if curl -s --connect-timeout 3 http://localhost:11434/api/tags &>/dev/null; then
    ok "Ollama is running"
else
    warn "Ollama is not running (offline story mode will still work)"
    info "  Start with: ollama serve"
fi

# Create logs directory
header "Setup"
LOG_DIR="${WORKDIR}/logs"
mkdir -p "$LOG_DIR"
chown "${CURRENT_USER}:${CURRENT_USER}" "$LOG_DIR" 2>/dev/null || true
ok "Logs directory ready: $LOG_DIR"

# Generate service file from template
TMP_SERVICE=$(mktemp /tmp/mcadv-bot.service.XXXXX)
sed \
    -e "s|__USER__|${CURRENT_USER}|g" \
    -e "s|__WORKDIR__|${WORKDIR}|g" \
    "$TEMPLATE" > "$TMP_SERVICE"

ok "Service file generated"
info "  User: $CURRENT_USER"
info "  WorkDir: $WORKDIR"
info "  Python: ${WORKDIR}/venv/bin/python3"

# Install service file
header "Installation"
cp "$TMP_SERVICE" "$SERVICE_FILE"
rm -f "$TMP_SERVICE"
chmod 644 "$SERVICE_FILE"
ok "Service file installed: $SERVICE_FILE"

# Reload systemd
systemctl daemon-reload
ok "systemd daemon reloaded"

# Ask about auto-start
echo ""
echo -e "${YELLOW}Enable auto-start on boot?${NC} [y/N]"
read -r -t 30 ENABLE_AUTOSTART || ENABLE_AUTOSTART="n"

if [[ "${ENABLE_AUTOSTART,,}" == "y" ]]; then
    systemctl enable "${SERVICE_NAME}"
    ok "Auto-start enabled"
else
    info "Auto-start not enabled"
    info "  Enable later with: sudo systemctl enable ${SERVICE_NAME}"
fi

# Summary
header "Installation Complete"
echo ""
echo "Service management commands:"
echo "  sudo systemctl start ${SERVICE_NAME}    # Start the bot"
echo "  sudo systemctl stop ${SERVICE_NAME}     # Stop the bot"
echo "  sudo systemctl restart ${SERVICE_NAME}  # Restart the bot"
echo "  sudo systemctl status ${SERVICE_NAME}   # View status"
echo ""
echo "Log monitoring:"
echo "  tail -f ${WORKDIR}/logs/systemd_output.log"
echo "  tail -f ${WORKDIR}/logs/systemd_error.log"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "To start the bot now:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo ""
ok "Installation complete!"

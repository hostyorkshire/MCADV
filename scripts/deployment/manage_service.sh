#!/bin/bash
# manage_service.sh - Interactive management for the MCADV systemd service
# Usage: ./manage_service.sh [-h|--help]

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
SERVICE_NAME="mcadv-bot"
LOG_DIR="${WORKDIR}/logs"

ok()   { echo -e "${GREEN}✓${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Interactive menu for managing the MCADV systemd service."
    echo ""
    echo "Available operations:"
    echo "  1. Start service"
    echo "  2. Stop service"
    echo "  3. Restart service"
    echo "  4. View status"
    echo "  5. View logs (last 50 lines)"
    echo "  6. Follow logs (live tail)"
    echo "  7. Enable auto-start on boot"
    echo "  8. Disable auto-start"
    echo "  9. Uninstall service"
    echo "  0. Exit"
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

show_status() {
    echo ""
    echo -e "${CYAN}--- Service Status ---${NC}"
    systemctl status "${SERVICE_NAME}" --no-pager 2>&1 || true
    echo ""
}

check_service_installed() {
    if ! systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null; then
        err "Service '${SERVICE_NAME}' is not installed"
        echo "Install it with: sudo ${SCRIPT_DIR}/install_service.sh"
        return 1
    fi
    return 0
}

do_start() {
    header "Starting Service"
    sudo systemctl start "${SERVICE_NAME}" && ok "Service started" || err "Failed to start service"
    show_status
}

do_stop() {
    header "Stopping Service"
    sudo systemctl stop "${SERVICE_NAME}" && ok "Service stopped" || err "Failed to stop service"
    show_status
}

do_restart() {
    header "Restarting Service"
    sudo systemctl restart "${SERVICE_NAME}" && ok "Service restarted" || err "Failed to restart service"
    show_status
}

do_status() {
    header "Service Status"
    show_status
}

do_view_logs() {
    header "Recent Logs (last 50 lines)"
    echo ""
    if [[ -f "${LOG_DIR}/systemd_output.log" ]]; then
        echo -e "${CYAN}--- systemd_output.log ---${NC}"
        tail -50 "${LOG_DIR}/systemd_output.log" 2>/dev/null || true
    fi
    if [[ -f "${LOG_DIR}/systemd_error.log" ]]; then
        echo ""
        echo -e "${CYAN}--- systemd_error.log ---${NC}"
        tail -50 "${LOG_DIR}/systemd_error.log" 2>/dev/null || true
    fi
    echo ""
    echo -e "${CYAN}--- systemd journal (last 50 lines) ---${NC}"
    sudo journalctl -u "${SERVICE_NAME}" -n 50 --no-pager 2>/dev/null || true
}

do_follow_logs() {
    header "Following Logs (Ctrl+C to stop)"
    echo ""
    echo "Press Ctrl+C to return to menu."
    echo ""
    sudo journalctl -u "${SERVICE_NAME}" -f --no-pager 2>/dev/null || \
        tail -f "${LOG_DIR}/systemd_output.log" 2>/dev/null || true
}

do_enable() {
    header "Enabling Auto-Start"
    sudo systemctl enable "${SERVICE_NAME}" && ok "Auto-start enabled" || err "Failed to enable"
    show_status
}

do_disable() {
    header "Disabling Auto-Start"
    sudo systemctl disable "${SERVICE_NAME}" && ok "Auto-start disabled" || err "Failed to disable"
    show_status
}

do_uninstall() {
    header "Uninstall Service"
    echo -e "${RED}This will remove the systemd service. Continue? [y/N]${NC}"
    read -r -t 30 CONFIRM || CONFIRM="n"
    if [[ "${CONFIRM,,}" != "y" ]]; then
        info "Uninstall cancelled"
        return
    fi
    sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    ok "Service uninstalled"
}

# Main menu loop
while true; do
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       MCADV Service Manager              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo "  1) Start service"
    echo "  2) Stop service"
    echo "  3) Restart service"
    echo "  4) View status"
    echo "  5) View logs (last 50 lines)"
    echo "  6) Follow logs (live tail)"
    echo "  7) Enable auto-start on boot"
    echo "  8) Disable auto-start"
    echo "  9) Uninstall service"
    echo "  0) Exit"
    echo ""
    echo -n "Enter choice [0-9]: "
    read -r -t 60 CHOICE || CHOICE="0"

    case "$CHOICE" in
        1) do_start ;;
        2) do_stop ;;
        3) do_restart ;;
        4) do_status ;;
        5) do_view_logs ;;
        6) do_follow_logs ;;
        7) do_enable ;;
        8) do_disable ;;
        9) do_uninstall ;;
        0) echo ""; info "Exiting"; exit 0 ;;
        *) warn "Invalid choice: '$CHOICE'" ;;
    esac

    echo ""
    echo "Press Enter to continue..."
    read -r -t 30 _ || true
done

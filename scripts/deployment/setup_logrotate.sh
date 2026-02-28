#!/bin/bash
# setup_logrotate.sh - Configure log rotation for MCADV logs
# Usage: ./setup_logrotate.sh [-h|--help]

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
TEMPLATE="${SCRIPT_DIR}/logrotate.conf"
LOGROTATE_DEST="/etc/logrotate.d/mcadv"

ok()   { echo -e "${GREEN}✓${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Set up log rotation for MCADV log files."
    echo ""
    echo "Configures daily rotation with:"
    echo "  - 7 days retention"
    echo "  - Compression of old logs"
    echo "  - Auto-create new log files"
    echo ""
    echo "Requires sudo privileges."
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

header "MCADV Log Rotation Setup"
echo "Timestamp: $(date)"
echo "Working directory: $WORKDIR"
echo "User: $CURRENT_USER"

# Check sudo
if [[ $EUID -ne 0 ]]; then
    err "This script must be run with sudo"
    echo "Run: sudo $0"
    exit 2
fi

# Check logrotate
header "Prerequisites"
if command -v logrotate &>/dev/null; then
    ok "logrotate available"
else
    err "logrotate not found"
    echo "Install with: sudo apt install logrotate"
    exit 2
fi

if [[ -f "$TEMPLATE" ]]; then
    ok "Template found: $TEMPLATE"
else
    err "Template not found: $TEMPLATE"
    exit 2
fi

# Ensure logs directory exists
header "Setup"
LOG_DIR="${WORKDIR}/logs"
mkdir -p "$LOG_DIR"
chown "${CURRENT_USER}:${CURRENT_USER}" "$LOG_DIR" 2>/dev/null || true
ok "Logs directory ready: $LOG_DIR"

# Generate config from template
TMP_CONF=$(mktemp /tmp/mcadv-logrotate.XXXXX)
sed \
    -e "s|__USER__|${CURRENT_USER}|g" \
    -e "s|__WORKDIR__|${WORKDIR}|g" \
    "$TEMPLATE" > "$TMP_CONF"

ok "Config generated"

# Install config
header "Installation"
cp "$TMP_CONF" "$LOGROTATE_DEST"
rm -f "$TMP_CONF"
chmod 644 "$LOGROTATE_DEST"
ok "Config installed: $LOGROTATE_DEST"

# Show installed config
info "Installed configuration:"
cat "$LOGROTATE_DEST"
echo ""

# Test with logrotate -d
header "Verification"
info "Testing config with logrotate -d (dry run)..."
if logrotate -d "$LOGROTATE_DEST" 2>&1 | grep -v "^$" | head -20; then
    ok "Config validation passed"
else
    warn "Config validation produced warnings (may be normal if no logs exist yet)"
fi

header "Setup Complete"
echo ""
echo "Log rotation is now configured:"
echo "  Config: $LOGROTATE_DEST"
echo "  Logs:   ${WORKDIR}/logs/*.log"
echo "  Runs:   Daily (via cron or systemd-timer)"
echo ""
echo "Manual rotation (for testing):"
echo "  sudo logrotate -f $LOGROTATE_DEST"
echo ""
echo "Check rotation status:"
echo "  sudo logrotate -v $LOGROTATE_DEST"
echo ""
ok "Log rotation setup complete!"

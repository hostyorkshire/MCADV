#!/bin/bash
# backup_config.sh - Backup MCADV configuration for migration
#
# Creates a tarball containing all configuration needed to restore MCADV
# on a new device (e.g., migrating from Ubuntu Desktop → Pi 5).
#
# Usage:
#   ./scripts/backup_config.sh [-h|--help] [--output DIR]
#
# Exit codes:
#   0 - Backup created successfully
#   1 - Error creating backup

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
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${REPO_DIR}/backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${OUTPUT_DIR}/mcadv_config_${TIMESTAMP}.tar.gz"

usage() {
    cat <<EOF
Usage: $0 [-h|--help] [--output DIR]

Backup MCADV configuration for migration to a new device.

Creates: mcadv_config_YYYYMMDD_HHMMSS.tar.gz

Contents:
  - config.yaml
  - .env (if present)
  - adventure_sessions.json (if present)
  - logs/ (last 100 lines of each log)
  - Installed Ollama model list

Options:
  --output DIR   Directory to save backup (default: ${OUTPUT_DIR})
  -h, --help     Show this help and exit

Exit codes:
  0 - Backup created successfully
  1 - Error
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)  usage ;;
        --output)   OUTPUT_DIR="$2"; BACKUP_FILE="${OUTPUT_DIR}/mcadv_config_${TIMESTAMP}.tar.gz"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  MCADV Configuration Backup                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Source: ${REPO_DIR}"
echo "  Output: ${BACKUP_FILE}"
echo ""

# ---------------------------------------------------------------------------
# Collect files into a staging directory
# ---------------------------------------------------------------------------
STAGING="$(mktemp -d)"
trap 'rm -rf "${STAGING}"' EXIT

STAGE_DIR="${STAGING}/mcadv_backup"
mkdir -p "${STAGE_DIR}"

# config.yaml
if [[ -f "${REPO_DIR}/config.yaml" ]]; then
    cp "${REPO_DIR}/config.yaml" "${STAGE_DIR}/"
    ok "config.yaml"
else
    warn "config.yaml not found"
fi

# .env
if [[ -f "${REPO_DIR}/.env" ]]; then
    cp "${REPO_DIR}/.env" "${STAGE_DIR}/.env"
    ok ".env"
else
    info ".env not present (skipping)"
fi

# adventure_sessions.json
if [[ -f "${REPO_DIR}/adventure_sessions.json" ]]; then
    cp "${REPO_DIR}/adventure_sessions.json" "${STAGE_DIR}/"
    ok "adventure_sessions.json"
else
    info "adventure_sessions.json not present (skipping)"
fi

# Recent log tails (last 100 lines each)
if [[ -d "${REPO_DIR}/logs" ]]; then
    mkdir -p "${STAGE_DIR}/logs"
    for log in "${REPO_DIR}/logs"/*.log; do
        [[ -f "$log" ]] || continue
        tail -100 "$log" > "${STAGE_DIR}/logs/$(basename "$log")"
    done
    ok "logs/ (last 100 lines)"
fi

# Ollama model list
MODELS_FILE="${STAGE_DIR}/ollama_models.txt"
if command -v ollama &>/dev/null && curl -s --connect-timeout 3 http://localhost:11434/api/tags &>/dev/null; then
    curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(m['name'])
" 2>/dev/null > "${MODELS_FILE}" || true
    if [[ -s "$MODELS_FILE" ]]; then
        ok "Ollama model list:"
        while IFS= read -r m; do
            info "$m"
        done < "${MODELS_FILE}"
    else
        info "No Ollama models found"
    fi
else
    echo "(Ollama not running – model list unavailable)" > "${MODELS_FILE}"
    info "Ollama not running – model list not captured"
fi

# Systemd service file
for svc in /etc/systemd/system/mcadv*.service /etc/systemd/system/adventure_bot*.service; do
    [[ -f "$svc" ]] || continue
    cp "$svc" "${STAGE_DIR}/"
    ok "Systemd service: $(basename "$svc")"
done

# Write metadata
cat > "${STAGE_DIR}/backup_info.txt" <<EOF
MCADV Configuration Backup
===========================
Created:    $(date)
Hostname:   $(hostname)
User:       $(whoami)
Repo:       ${REPO_DIR}
EOF
ok "backup_info.txt"

# ---------------------------------------------------------------------------
# Create tarball
# ---------------------------------------------------------------------------
mkdir -p "${OUTPUT_DIR}"
tar -czf "${BACKUP_FILE}" -C "${STAGING}" mcadv_backup

BACKUP_SIZE="$(du -sh "${BACKUP_FILE}" | cut -f1)"
echo ""
echo -e "${GREEN}✅ Backup created:${NC} ${BACKUP_FILE} (${BACKUP_SIZE})"
echo ""
echo "To restore on another device:"
echo "  scp ${BACKUP_FILE} user@new-device:~/"
echo "  ./scripts/restore_config.sh ~/$(basename "${BACKUP_FILE}")"

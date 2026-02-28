#!/bin/bash
# restore_config.sh - Restore MCADV configuration from backup
#
# Extracts a backup created by backup_config.sh and places files
# in the correct locations.
#
# Usage:
#   ./scripts/restore_config.sh BACKUP_FILE.tar.gz [-h|--help]
#
# Exit codes:
#   0 - Restore completed successfully
#   1 - Error

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

usage() {
    cat <<EOF
Usage: $0 BACKUP_FILE.tar.gz [-h|--help]

Restore MCADV configuration from a backup created by backup_config.sh.

Restores:
  - config.yaml
  - .env (if present in backup)
  - adventure_sessions.json (if present in backup)
  - Displays Ollama model list (models must be re-pulled manually)

Arguments:
  BACKUP_FILE   Path to the .tar.gz backup file (required)

Options:
  -h, --help    Show this help and exit

Exit codes:
  0 - Restore completed successfully
  1 - Error
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
BACKUP_FILE=""
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage ;;
        *) BACKUP_FILE="$arg" ;;
    esac
done

if [[ -z "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: backup file argument required${NC}"
    echo ""
    usage
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  MCADV Configuration Restore                 ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Backup: ${BACKUP_FILE}"
echo "  Target: ${REPO_DIR}"
echo ""

# ---------------------------------------------------------------------------
# Extract backup
# ---------------------------------------------------------------------------
STAGING="$(mktemp -d)"
trap 'rm -rf "${STAGING}"' EXIT

tar -xzf "${BACKUP_FILE}" -C "${STAGING}"

STAGE_DIR="${STAGING}/mcadv_backup"
if [[ ! -d "$STAGE_DIR" ]]; then
    err "Unexpected backup structure (mcadv_backup/ directory not found)"
    exit 1
fi

# Show backup metadata
if [[ -f "${STAGE_DIR}/backup_info.txt" ]]; then
    echo -e "${CYAN}Backup information:${NC}"
    cat "${STAGE_DIR}/backup_info.txt"
    echo ""
fi

# ---------------------------------------------------------------------------
# Restore files
# ---------------------------------------------------------------------------
echo -e "${CYAN}Restoring files…${NC}"
echo ""

# config.yaml
if [[ -f "${STAGE_DIR}/config.yaml" ]]; then
    if [[ -f "${REPO_DIR}/config.yaml" ]]; then
        cp "${REPO_DIR}/config.yaml" "${REPO_DIR}/config.yaml.bak_$(date +%Y%m%d_%H%M%S)"
        warn "Existing config.yaml backed up"
    fi
    cp "${STAGE_DIR}/config.yaml" "${REPO_DIR}/config.yaml"
    ok "config.yaml restored"
else
    info "config.yaml not in backup"
fi

# .env
if [[ -f "${STAGE_DIR}/.env" ]]; then
    if [[ -f "${REPO_DIR}/.env" ]]; then
        cp "${REPO_DIR}/.env" "${REPO_DIR}/.env.bak_$(date +%Y%m%d_%H%M%S)"
        warn "Existing .env backed up"
    fi
    cp "${STAGE_DIR}/.env" "${REPO_DIR}/.env"
    ok ".env restored"
else
    info ".env not in backup"
fi

# adventure_sessions.json
if [[ -f "${STAGE_DIR}/adventure_sessions.json" ]]; then
    if [[ -f "${REPO_DIR}/adventure_sessions.json" ]]; then
        cp "${REPO_DIR}/adventure_sessions.json" \
           "${REPO_DIR}/adventure_sessions.json.bak_$(date +%Y%m%d_%H%M%S)"
        warn "Existing adventure_sessions.json backed up"
    fi
    cp "${STAGE_DIR}/adventure_sessions.json" "${REPO_DIR}/adventure_sessions.json"
    ok "adventure_sessions.json restored"
else
    info "adventure_sessions.json not in backup"
fi

# Logs (informational only – do not overwrite)
if [[ -d "${STAGE_DIR}/logs" ]]; then
    mkdir -p "${REPO_DIR}/logs/restored_backup"
    cp -r "${STAGE_DIR}/logs/." "${REPO_DIR}/logs/restored_backup/"
    ok "Backup logs copied to logs/restored_backup/"
fi

# Ollama models
if [[ -f "${STAGE_DIR}/ollama_models.txt" ]]; then
    echo ""
    echo -e "${CYAN}Ollama models from backup (re-pull manually if needed):${NC}"
    while IFS= read -r m; do
        [[ -z "$m" || "$m" == *"not running"* ]] && continue
        echo "  ollama pull ${m}"
    done < "${STAGE_DIR}/ollama_models.txt"
fi

echo ""
echo -e "${GREEN}✅ Restore complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review restored config.yaml"
echo "  2. Run: ./full_setup.sh  (to complete environment setup)"
echo "  3. Re-pull Ollama models listed above"
echo "  4. Run: ./scripts/pre_deployment_check.sh"

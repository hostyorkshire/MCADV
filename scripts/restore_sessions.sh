#!/usr/bin/env bash
# Restore adventure_sessions.json from a backup file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_FILE="$REPO_ROOT/adventure_sessions.json"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_file>"
  echo ""
  echo "Available backups:"
  ls -1t "$REPO_ROOT/logs/backups/" 2>/dev/null | head -10 || echo "  (none found)"
  exit 1
fi

BACKUP="$1"

if [[ ! -f "$BACKUP" ]]; then
  echo "Error: Backup file not found: $BACKUP"
  exit 1
fi

if [[ -f "$SESSION_FILE" ]]; then
  SAFEGUARD="$SESSION_FILE.pre_restore_$(date +%Y%m%d_%H%M%S)"
  cp "$SESSION_FILE" "$SAFEGUARD"
  echo "Current sessions saved to: $SAFEGUARD"
fi

cp "$BACKUP" "$SESSION_FILE"
echo "Restored sessions from: $BACKUP"

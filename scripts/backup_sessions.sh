#!/usr/bin/env bash
# Backup adventure_sessions.json with a timestamp.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_FILE="$REPO_ROOT/adventure_sessions.json"
BACKUP_DIR="$REPO_ROOT/logs/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/adventure_sessions_${TIMESTAMP}.json"

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$SESSION_FILE" ]]; then
  echo "No session file found at $SESSION_FILE – nothing to back up."
  exit 0
fi

cp "$SESSION_FILE" "$BACKUP_FILE"
echo "Backed up to: $BACKUP_FILE"

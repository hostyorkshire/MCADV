#!/bin/bash
# cpanel-deploy.sh
# Cron-based deployment script for MCADV website on cPanel.
# Usage: bash /home/<username>/mcadv-repo/scripts/cpanel-deploy.sh
# Recommended cron: */15 * * * * /bin/bash /home/<username>/mcadv-repo/scripts/cpanel-deploy.sh >> /home/<username>/logs/deploy.log 2>&1

set -euo pipefail

# ────────────────────────────────────────────────────────────
# Configuration – edit these variables for your environment
# ────────────────────────────────────────────────────────────
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
BRANCH="${BRANCH:-main}"
LOG_DIR="${LOG_DIR:-$HOME/logs}"
MAX_LOG_LINES="${MAX_LOG_LINES:-1000}"

# ────────────────────────────────────────────────────────────
# Setup
# ────────────────────────────────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="$LOG_DIR/deploy.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$TIMESTAMP] $*"
}

error() {
    echo "[$TIMESTAMP] ERROR: $*" >&2
}

# ────────────────────────────────────────────────────────────
# Trim log file to prevent unbounded growth
# ────────────────────────────────────────────────────────────
trim_log() {
    if [ -f "$LOG_FILE" ]; then
        local line_count
        line_count=$(wc -l < "$LOG_FILE")
        if [ "$line_count" -gt "$MAX_LOG_LINES" ]; then
            local tmp
            tmp=$(mktemp)
            tail -n "$MAX_LOG_LINES" "$LOG_FILE" > "$tmp"
            mv "$tmp" "$LOG_FILE"
        fi
    fi
}

# ────────────────────────────────────────────────────────────
# Main deployment logic
# ────────────────────────────────────────────────────────────
main() {
    log "Starting deployment..."

    # Verify repository directory exists
    if [ ! -d "$REPO_DIR/.git" ]; then
        error "Not a git repository: $REPO_DIR"
        exit 1
    fi

    cd "$REPO_DIR"

    # Fetch latest changes from remote
    log "Fetching from origin..."
    if ! git fetch origin "$BRANCH" 2>&1; then
        error "git fetch failed. Check network connectivity and authentication."
        exit 1
    fi

    # Check whether an update is available
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse FETCH_HEAD 2>/dev/null || echo "unknown")

    if [ "$LOCAL" = "$REMOTE" ]; then
        log "Already up to date ($(git rev-parse --short HEAD))."
        trim_log
        exit 0
    fi

    log "Update available: $(git rev-parse --short HEAD) → $(git rev-parse --short FETCH_HEAD 2>/dev/null || echo 'unknown')"

    # Pull latest changes
    if ! git pull origin "$BRANCH" 2>&1; then
        error "git pull failed. Check for merge conflicts or permission issues."
        exit 1
    fi

    DEPLOYED_SHA=$(git rev-parse --short HEAD)
    DEPLOYED_MSG=$(git log -1 --pretty=format:"%s" HEAD)

    log "Deployment complete. Deployed commit: $DEPLOYED_SHA – $DEPLOYED_MSG"
    trim_log
}

main "$@"

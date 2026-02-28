#!/bin/bash
# check_resources.sh - Quick health check suitable for cron jobs
# Usage: ./check_resources.sh [-h|--help]
# Cron example: */5 * * * * /path/to/check_resources.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SERVICE_NAME="mcadv-bot"
LOG_FILE="${WORKDIR}/logs/health_check.log"
HEALTH_STATUS=0

# Alert thresholds
MEM_WARN_PCT=80
MEM_CRIT_PCT=90
DISK_WARN_FREE_PCT=20
DISK_CRIT_FREE_PCT=10
ERROR_WINDOW_MINUTES=5

# Optional alert config
ALERT_CONFIG="${SCRIPT_DIR}/alert_config.sh"
[[ -f "$ALERT_CONFIG" ]] && source "$ALERT_CONFIG" 2>/dev/null || true

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Quick health check for MCADV bot. Suitable for cron (every 5 minutes)."
    echo ""
    echo "Checks:"
    echo "  1. Service running"
    echo "  2. Memory usage < ${MEM_CRIT_PCT}%"
    echo "  3. Disk space > ${DISK_CRIT_FREE_PCT}% free"
    echo "  4. Ollama responding"
    echo "  5. No recent errors in logs (last ${ERROR_WINDOW_MINUTES} min)"
    echo ""
    echo "Exit codes:"
    echo "  0 - Healthy"
    echo "  1 - Warning"
    echo "  2 - Critical"
    echo ""
    echo "Logs results to: $LOG_FILE"
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
MESSAGES=()

log_msg() {
    local level="$1"
    local msg="$2"
    echo "${TIMESTAMP} [${level}] ${msg}" >> "$LOG_FILE"
    MESSAGES+=("[${level}] ${msg}")
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Check 1: Service running
if command -v systemctl &>/dev/null; then
    if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        log_msg "OK" "Service ${SERVICE_NAME}: running"
    elif systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null 2>&1; then
        log_msg "CRITICAL" "Service ${SERVICE_NAME}: not running"
        HEALTH_STATUS=2
    else
        # Check for process directly
        if pgrep -f "adventure_bot.py" &>/dev/null; then
            log_msg "OK" "Bot process: running (no systemd service)"
        else
            log_msg "WARNING" "Bot process: not running (no systemd service installed)"
            [[ $HEALTH_STATUS -lt 1 ]] && HEALTH_STATUS=1
        fi
    fi
fi

# Check 2: Memory usage
MEM_TOTAL=$(free -m | awk '/Mem:/{print $2}')
MEM_USED=$(free -m | awk '/Mem:/{print $3}')
if [[ $MEM_TOTAL -gt 0 ]]; then
    MEM_PCT=$(( MEM_USED * 100 / MEM_TOTAL ))
    if [[ $MEM_PCT -ge $MEM_CRIT_PCT ]]; then
        log_msg "CRITICAL" "Memory: ${MEM_PCT}% used (${MEM_USED}MB/${MEM_TOTAL}MB)"
        HEALTH_STATUS=2
    elif [[ $MEM_PCT -ge $MEM_WARN_PCT ]]; then
        log_msg "WARNING" "Memory: ${MEM_PCT}% used (${MEM_USED}MB/${MEM_TOTAL}MB)"
        [[ $HEALTH_STATUS -lt 1 ]] && HEALTH_STATUS=1
    else
        log_msg "OK" "Memory: ${MEM_PCT}% used (${MEM_USED}MB/${MEM_TOTAL}MB)"
    fi
fi

# Check 3: Disk space
DISK_TOTAL=$(df / | awk 'NR==2{print $2}')
DISK_FREE=$(df / | awk 'NR==2{print $4}')
if [[ $DISK_TOTAL -gt 0 ]]; then
    DISK_FREE_PCT=$(( DISK_FREE * 100 / DISK_TOTAL ))
    DISK_FREE_GB=$(( DISK_FREE / 1024 / 1024 ))
    if [[ $DISK_FREE_PCT -le $DISK_CRIT_FREE_PCT ]]; then
        log_msg "CRITICAL" "Disk /: ${DISK_FREE_PCT}% free (${DISK_FREE_GB}GB)"
        HEALTH_STATUS=2
    elif [[ $DISK_FREE_PCT -le $DISK_WARN_FREE_PCT ]]; then
        log_msg "WARNING" "Disk /: ${DISK_FREE_PCT}% free (${DISK_FREE_GB}GB)"
        [[ $HEALTH_STATUS -lt 1 ]] && HEALTH_STATUS=1
    else
        log_msg "OK" "Disk /: ${DISK_FREE_PCT}% free (${DISK_FREE_GB}GB)"
    fi
fi

# Check 4: Ollama responding
if command -v curl &>/dev/null; then
    if curl -s --connect-timeout 5 http://localhost:11434/api/tags &>/dev/null; then
        log_msg "OK" "Ollama: responding on localhost:11434"
    else
        log_msg "WARNING" "Ollama: not responding (offline mode active)"
        [[ $HEALTH_STATUS -lt 1 ]] && HEALTH_STATUS=1
    fi
fi

# Check 5: Recent errors in logs
# Use a timestamp reference file to detect errors in the last N minutes
REF_FILE="/tmp/mcadv_check_ref_$$"
touch -t "$(date -d "${ERROR_WINDOW_MINUTES} minutes ago" '+%Y%m%d%H%M' 2>/dev/null || date '+%Y%m%d%H%M')" \
    "$REF_FILE" 2>/dev/null || touch "$REF_FILE"

RECENT_ERRORS=0
for log_file in "${WORKDIR}/logs/errors.log" "${WORKDIR}/logs/meshcore.log" \
                "${WORKDIR}/logs/systemd_error.log"; do
    if [[ -f "$log_file" ]]; then
        # Count errors in files modified since the reference timestamp
        if [[ "$log_file" -nt "$REF_FILE" ]]; then
            ERROR_COUNT=$(tail -100 "$log_file" | grep -c "ERROR\|CRITICAL\|Exception" 2>/dev/null || echo "0")
        else
            ERROR_COUNT=0
        fi
        RECENT_ERRORS=$(( RECENT_ERRORS + ERROR_COUNT ))
    fi
done
rm -f "$REF_FILE"

if [[ $RECENT_ERRORS -gt 10 ]]; then
    log_msg "WARNING" "Recent errors: ${RECENT_ERRORS} in logs"
    [[ $HEALTH_STATUS -lt 1 ]] && HEALTH_STATUS=1
else
    log_msg "OK" "Recent errors: ${RECENT_ERRORS}"
fi

# Send alert if critical and alert config is set
if [[ $HEALTH_STATUS -eq 2 ]]; then
    ALERT_MSG="MCADV CRITICAL on $(hostname): ${MESSAGES[*]}"

    # Email alert (if configured)
    if [[ -n "${ALERT_EMAIL:-}" ]] && command -v mail &>/dev/null; then
        echo "$ALERT_MSG" | mail -s "MCADV Alert - $(hostname)" "$ALERT_EMAIL" 2>/dev/null || true
    fi

    # Webhook alert (if configured)
    if [[ -n "${ALERT_WEBHOOK_URL:-}" ]] && command -v curl &>/dev/null; then
        curl -s -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"${ALERT_MSG}\"}" &>/dev/null || true
    fi
fi

# Output summary
echo "${TIMESTAMP} health_check status=${HEALTH_STATUS} $(IFS='; '; echo "${MESSAGES[*]}")" >> "$LOG_FILE"

# Print to stdout
case $HEALTH_STATUS in
    0) echo "HEALTHY: ${MESSAGES[*]}" ;;
    1) echo "WARNING: ${MESSAGES[*]}" ;;
    2) echo "CRITICAL: ${MESSAGES[*]}" ;;
esac

exit $HEALTH_STATUS

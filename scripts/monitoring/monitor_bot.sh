#!/bin/bash
# monitor_bot.sh - MCADV bot monitoring dashboard
# Usage: ./monitor_bot.sh [-h|--help] [--once] [--interval SECONDS]

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
REFRESH_INTERVAL=30
RUN_ONCE=false
HEALTH_STATUS=0

usage() {
    echo "Usage: $0 [-h|--help] [--once] [--interval SECONDS]"
    echo ""
    echo "Display MCADV monitoring dashboard."
    echo ""
    echo "Options:"
    echo "  --once              Run once and exit (default: refresh loop)"
    echo "  --interval SECONDS  Refresh interval (default: 30)"
    echo ""
    echo "Exit codes:"
    echo "  0 - Healthy"
    echo "  1 - Warnings"
    echo "  2 - Critical"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --once) RUN_ONCE=true; shift ;;
        --interval) REFRESH_INTERVAL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()     { echo -e "  ${GREEN}●${NC} $1"; }
err()    { echo -e "  ${RED}●${NC} $1"; HEALTH_STATUS=2; }
warn()   { echo -e "  ${YELLOW}●${NC} $1"; [[ $HEALTH_STATUS -lt 1 ]] && HEALTH_STATUS=1; }
info()   { echo -e "  ${BLUE}○${NC} $1"; }
section() { echo -e "\n${CYAN}$1${NC}"; }

display_dashboard() {
    HEALTH_STATUS=0
    clear 2>/dev/null || true

    echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           MCADV Bot Monitoring Dashboard              ║${NC}"
    echo -e "${CYAN}║  $(date '+%Y-%m-%d %H:%M:%S')  $(uname -n)                     ${NC}${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

    # Service Status
    section "📡 Service Status"
    if command -v systemctl &>/dev/null; then
        if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
            ok "mcadv-bot: active (running)"
            UPTIME=$(systemctl show "${SERVICE_NAME}" --property=ActiveEnterTimestamp \
                --value 2>/dev/null | xargs -I{} date -d "{}" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")
            info "  Started: $UPTIME"
        elif systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null 2>&1; then
            warn "mcadv-bot: inactive (installed but not running)"
            info "  Start with: sudo systemctl start ${SERVICE_NAME}"
        else
            warn "mcadv-bot: not installed (running manually or not started)"
        fi
    else
        # Check for running python process
        if pgrep -f "adventure_bot.py" &>/dev/null; then
            ok "adventure_bot.py: running (process found)"
        else
            warn "adventure_bot.py: not running"
        fi
    fi

    # Memory Usage
    section "💾 Memory Usage"
    MEM_TOTAL=$(free -m 2>/dev/null | awk '/Mem:/{print $2}' || echo "0")
    MEM_USED=$(free -m 2>/dev/null | awk '/Mem:/{print $3}' || echo "0")
    if [[ $MEM_TOTAL -gt 0 ]]; then
        MEM_PCT=$(( MEM_USED * 100 / MEM_TOTAL ))
        if [[ $MEM_PCT -lt 70 ]]; then
            ok "System: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PCT}%)"
        elif [[ $MEM_PCT -lt 90 ]]; then
            warn "System: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PCT}%) - getting high"
        else
            err "System: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PCT}%) - critical"
        fi
    fi

    # Bot process memory
    BOT_MEM=$(ps aux 2>/dev/null | grep "adventure_bot.py" | grep -v grep | \
        awk '{sum+=$6} END {printf "%.0f", sum/1024}' || echo "0")
    if [[ -n "$BOT_MEM" && "$BOT_MEM" != "0" ]]; then
        info "Bot process: ${BOT_MEM}MB RSS"
    fi

    # Disk Space
    section "💿 Disk Space"
    for partition in / /home; do
        if df "$partition" &>/dev/null 2>&1; then
            DISK_INFO=$(df -h "$partition" | awk 'NR==2{print $3"/"$2" ("$5" used)"}')
            DISK_PCT=$(df "$partition" | awk 'NR==2{gsub(/%/,"",$5); print $5}')
            if [[ $DISK_PCT -lt 80 ]]; then
                ok "$partition: $DISK_INFO"
            elif [[ $DISK_PCT -lt 90 ]]; then
                warn "$partition: $DISK_INFO - getting full"
            else
                err "$partition: $DISK_INFO - nearly full!"
            fi
        fi
    done

    # Active Sessions
    section "👥 Active Sessions"
    SESS_FILE="${WORKDIR}/adventure_sessions.json"
    if [[ -f "$SESS_FILE" ]]; then
        SESSION_COUNT=$(python3 -c "
import json
try:
    with open('${SESS_FILE}') as f:
        data = json.load(f)
    print(len(data))
except:
    print(0)
" 2>/dev/null || echo "0")
        ok "Sessions: ${SESSION_COUNT} active"
        info "  File: $SESS_FILE"
    else
        info "No session file found (bot not started yet)"
    fi

    # Recent Errors
    section "⚠️  Recent Errors (last 5)"
    ERRORS_FOUND=false
    for log_file in "${WORKDIR}/logs/errors.log" "${WORKDIR}/logs/meshcore.log" \
                    "${WORKDIR}/logs/systemd_error.log"; do
        if [[ -f "$log_file" ]]; then
            RECENT_ERRORS=$(tail -100 "$log_file" 2>/dev/null | grep -i "error\|exception\|critical" | tail -5 || true)
            if [[ -n "$RECENT_ERRORS" ]]; then
                warn "Errors in $(basename $log_file):"
                while IFS= read -r line; do
                    info "  ${line:0:80}"
                done <<< "$RECENT_ERRORS"
                ERRORS_FOUND=true
            fi
        fi
    done
    if [[ "$ERRORS_FOUND" == false ]]; then
        ok "No recent errors found"
    fi

    # Ollama Status
    section "🤖 Ollama Status"
    if curl -s --connect-timeout 3 http://localhost:11434/api/tags &>/dev/null; then
        ok "Ollama: running on localhost:11434"
        MODELS=$(curl -s --connect-timeout 3 http://localhost:11434/api/tags 2>/dev/null | \
            python3 -c "
import json, sys
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print(', '.join(models[:3]) if models else 'none')
" 2>/dev/null || echo "unknown")
        info "  Models: $MODELS"
    else
        warn "Ollama: not running (offline mode active)"
    fi

    # Radio Status
    section "📻 Radio Status"
    RADIO_FOUND=false
    for pattern in /dev/ttyUSB* /dev/ttyACM*; do
        for port in $pattern; do
            if [[ -e "$port" ]]; then
                ok "Radio detected: $port"
                RADIO_FOUND=true
            fi
        done
    done
    if [[ "$RADIO_FOUND" == false ]]; then
        warn "No LoRa radio detected on /dev/ttyUSB* or /dev/ttyACM*"
    fi

    # Service Uptime
    section "🔄 Uptime"
    if command -v systemctl &>/dev/null && systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        ACTIVE_SINCE=$(systemctl show "${SERVICE_NAME}" --property=ActiveEnterTimestamp \
            --value 2>/dev/null || echo "")
        if [[ -n "$ACTIVE_SINCE" ]]; then
            info "Service active since: $ACTIVE_SINCE"
        fi
    fi
    SYSTEM_UPTIME=$(uptime -p 2>/dev/null || uptime 2>/dev/null | awk '{print $3,$4}' || echo "unknown")
    info "System uptime: $SYSTEM_UPTIME"

    echo ""
    echo -e "${CYAN}──────────────────────────────────────────────────────${NC}"
    if [[ $HEALTH_STATUS -eq 0 ]]; then
        echo -e "  ${GREEN}✅ System healthy${NC}"
    elif [[ $HEALTH_STATUS -eq 1 ]]; then
        echo -e "  ${YELLOW}⚠️  System has warnings${NC}"
    else
        echo -e "  ${RED}❌ System needs attention${NC}"
    fi
    echo ""

    if [[ "$RUN_ONCE" == false ]]; then
        echo -e "  Refreshing every ${REFRESH_INTERVAL}s — Press Ctrl+C to exit"
    fi
}

if [[ "$RUN_ONCE" == true ]]; then
    display_dashboard
    exit $HEALTH_STATUS
fi

# Refresh loop
while true; do
    display_dashboard
    sleep "$REFRESH_INTERVAL"
done

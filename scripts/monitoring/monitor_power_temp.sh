#!/bin/bash
# monitor_power_temp.sh - MCADV power and temperature monitoring
#
# Monitors CPU temperature, throttle state, estimated power draw,
# and battery level (if supported).
#
# Usage:
#   ./scripts/monitoring/monitor_power_temp.sh [-h|--help] [--once] [--interval SECS]
#
# Exit codes:
#   0 - Healthy
#   1 - Warnings (high temperature / low battery)
#   2 - Critical (throttling / dangerous temperature)

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
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUN_ONCE=false
INTERVAL=30
HEALTH=0  # 0=ok 1=warn 2=critical

# Temperature thresholds (°C)
TEMP_WARN=70
TEMP_CRIT=80

usage() {
    cat <<EOF
Usage: $0 [-h|--help] [--once] [--interval SECS]

MCADV power and temperature monitor.

Options:
  --once            Run a single check and exit
  --interval SECS   Refresh interval in seconds (default: ${INTERVAL})
  -h, --help        Show this help and exit

Thresholds:
  Temperature warning:  ${TEMP_WARN}°C
  Temperature critical: ${TEMP_CRIT}°C

Exit codes:
  0 - Healthy
  1 - Warnings
  2 - Critical
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --once)    RUN_ONCE=true; shift ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()     { echo -e "  ${GREEN}●${NC} $1"; }
warn()   { echo -e "  ${YELLOW}●${NC} $1"; [[ $HEALTH -lt 1 ]] && HEALTH=1; }
crit()   { echo -e "  ${RED}●${NC} $1"; HEALTH=2; }
info()   { echo -e "    ${BLUE}→${NC} $1"; }
header() { echo -e "\n${CYAN}── $1 ──${NC}"; }

# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------
check_temperature() {
    header "CPU Temperature"
    local temp_raw temp_c

    # Linux sysfs
    if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
        temp_raw="$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0)"
        temp_c=$(( temp_raw / 1000 ))
        if [[ $temp_c -ge $TEMP_CRIT ]]; then
            crit "CPU temperature: ${temp_c}°C (CRITICAL – above ${TEMP_CRIT}°C)"
            info "Improve cooling immediately!"
        elif [[ $temp_c -ge $TEMP_WARN ]]; then
            warn "CPU temperature: ${temp_c}°C (warning – above ${TEMP_WARN}°C)"
            info "Check cooling / airflow"
        else
            ok "CPU temperature: ${temp_c}°C (normal)"
        fi
        return
    fi

    # vcgencmd (Raspberry Pi)
    if command -v vcgencmd &>/dev/null; then
        local vcg_out
        vcg_out="$(vcgencmd measure_temp 2>/dev/null || true)"
        if [[ "$vcg_out" =~ temp=([0-9]+) ]]; then
            temp_c="${BASH_REMATCH[1]}"
            if [[ $temp_c -ge $TEMP_CRIT ]]; then
                crit "CPU temperature: ${temp_c}°C (CRITICAL)"
            elif [[ $temp_c -ge $TEMP_WARN ]]; then
                warn "CPU temperature: ${temp_c}°C (warning)"
            else
                ok "CPU temperature: ${temp_c}°C (normal)"
            fi
            return
        fi
    fi

    info "Temperature sensor not available on this platform"
}

check_throttling() {
    header "CPU Throttle Status"

    # vcgencmd get_throttled (Pi)
    if command -v vcgencmd &>/dev/null; then
        local throttle_hex
        throttle_hex="$(vcgencmd get_throttled 2>/dev/null | sed 's/throttled=//' || true)"
        if [[ -n "$throttle_hex" ]]; then
            local throttle_val
            throttle_val=$(( 16#${throttle_hex#0x} ))
            if (( (throttle_val & 0xF) != 0 )); then
                crit "CPU is CURRENTLY THROTTLED (flags: ${throttle_hex})"
                info "Possible causes: under-voltage, overheating, or power supply issue"
            elif (( (throttle_val & 0xF0000) != 0 )); then
                warn "Throttling has occurred since last boot (flags: ${throttle_hex})"
                info "Check power supply and cooling"
            else
                ok "No throttling detected (flags: ${throttle_hex})"
            fi
            return
        fi
    fi

    info "Throttle detection not available (non-Pi hardware or vcgencmd missing)"
}

check_power() {
    header "Estimated Power Draw"

    # Simple CPU-load-based estimate
    if [[ -f /proc/loadavg ]]; then
        local load cpu_count idle_watts
        load="$(cut -d' ' -f1 /proc/loadavg)"
        cpu_count="$(nproc 2>/dev/null || echo 1)"

        # Normalise by CPU count; clamp to [0,100]
        local load_pct
        load_pct="$(python3 -c "
load = float('${load}')
cpus = int('${cpu_count}')
pct = min(100, (load / cpus) * 100)
print(int(pct))
" 2>/dev/null || echo 0)"

        idle_watts=2
        local est_w
        est_w="$(python3 -c "print(round(${idle_watts} + 0.08 * ${load_pct}, 1))" 2>/dev/null || echo '?')"
        ok "Estimated power draw: ~${est_w} W (CPU load ${load_pct}%)"
    else
        info "Power estimation not available (/proc/loadavg missing)"
    fi
}

check_battery() {
    header "Battery / UPS"
    local found=false

    for path in /sys/class/power_supply/BAT0 /sys/class/power_supply/BAT1 \
                /sys/class/power_supply/battery; do
        if [[ -d "$path" ]]; then
            found=true
            local cap status
            cap="$(cat "${path}/capacity" 2>/dev/null || echo '?')"
            status="$(cat "${path}/status" 2>/dev/null || echo 'unknown')"
            if [[ "$cap" != "?" ]]; then
                if [[ $cap -le 10 ]]; then
                    crit "Battery: ${cap}% (${status}) – CRITICAL"
                elif [[ $cap -le 20 ]]; then
                    warn "Battery: ${cap}% (${status}) – LOW"
                else
                    ok "Battery: ${cap}% (${status})"
                fi
            else
                info "Battery capacity unreadable at ${path}"
            fi
        fi
    done

    if [[ "$found" == false ]]; then
        info "No battery / UPS detected (running on mains power)"
    fi
}

# ---------------------------------------------------------------------------
# Single measurement pass
# ---------------------------------------------------------------------------
run_checks() {
    HEALTH=0
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  MCADV Power & Temperature Monitor           ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo "  Timestamp: $(date)"

    check_temperature
    check_throttling
    check_power
    check_battery

    echo ""
    if [[ $HEALTH -eq 2 ]]; then
        echo -e "${RED}  ❌ CRITICAL – immediate attention required${NC}"
    elif [[ $HEALTH -eq 1 ]]; then
        echo -e "${YELLOW}  ⚠  WARNINGS detected – review above${NC}"
    else
        echo -e "${GREEN}  ✅ All metrics nominal${NC}"
    fi
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
if [[ "$RUN_ONCE" == true ]]; then
    run_checks
    exit $HEALTH
fi

# Continuous loop
while true; do
    run_checks
    echo ""
    echo -e "${BLUE}  Next refresh in ${INTERVAL} seconds (Ctrl+C to stop)…${NC}"
    sleep "$INTERVAL"
    clear
done

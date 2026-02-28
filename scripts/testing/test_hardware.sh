#!/bin/bash
# test_hardware.sh - Auto-detect and test LoRa radios for MCADV
# Usage: ./test_hardware.sh [-h|--help]

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

PASS=0
FAIL=0
WARN=0

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Auto-detect LoRa radios and test serial port accessibility."
    echo "Checks /dev/ttyUSB* and /dev/ttyACM* devices."
    echo ""
    echo "Exit codes:"
    echo "  0 - All tests passed"
    echo "  1 - Warnings (radios found but some issues)"
    echo "  2 - Critical failure (no radios found)"
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

ok()   { echo -e "${GREEN}✓${NC} $1"; PASS=$(( PASS + 1 )); }
err()  { echo -e "${RED}✗${NC} $1"; FAIL=$(( FAIL + 1 )); }
warn() { echo -e "${YELLOW}⚠${NC} $1"; WARN=$(( WARN + 1 )); }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

header "MCADV Hardware Test"
echo "Timestamp: $(date)"
echo "Platform: $(uname -m) / $(uname -s)"

# Check for required tools
header "Prerequisites"
for cmd in ls file; do
    if command -v "$cmd" &>/dev/null; then
        ok "Command '$cmd' available"
    else
        err "Command '$cmd' not found"
    fi
done

STTY_AVAILABLE=false
if command -v stty &>/dev/null; then
    ok "Command 'stty' available (baud rate testing enabled)"
    STTY_AVAILABLE=true
else
    warn "Command 'stty' not found - baud rate testing skipped"
fi

# Detect serial devices
header "Serial Port Detection"

RADIO_PORTS=()
ALL_PORTS=()

# Gather all candidate ports
for pattern in /dev/ttyUSB* /dev/ttyACM*; do
    for port in $pattern; do
        [[ -e "$port" ]] && ALL_PORTS+=("$port")
    done
done

if [[ ${#ALL_PORTS[@]} -eq 0 ]]; then
    err "No serial devices found on /dev/ttyUSB* or /dev/ttyACM*"
    echo ""
    echo "Possible causes:"
    echo "  - LoRa radio not connected via USB"
    echo "  - USB cable is power-only (needs data cable)"
    echo "  - Driver not loaded (try: sudo modprobe cp210x)"
    echo "  - Device permission denied (try: sudo usermod -aG dialout \$USER)"
    exit 2
else
    ok "Found ${#ALL_PORTS[@]} serial device(s)"
    for port in "${ALL_PORTS[@]}"; do
        info "  Detected: $port"
    done
fi

# Test each port
header "Serial Port Accessibility"

BAUD_RATES=(9600 115200 230400)

for port in "${ALL_PORTS[@]}"; do
    echo ""
    info "Testing: $port"

    # Check readability
    if [[ -r "$port" ]]; then
        ok "  $port is readable"
    else
        err "  $port is not readable (permission denied)"
        echo "     Fix: sudo usermod -aG dialout \$USER  (then log out and back in)"
        continue
    fi

    # Check writability
    if [[ -w "$port" ]]; then
        ok "  $port is writable"
    else
        warn "  $port is not writable"
    fi

    # Get device info
    if command -v udevadm &>/dev/null; then
        VENDOR=$(udevadm info "$port" 2>/dev/null | grep -i "ID_VENDOR=" | head -1 | cut -d= -f2 || true)
        MODEL=$(udevadm info "$port" 2>/dev/null | grep -i "ID_MODEL=" | head -1 | cut -d= -f2 || true)
        if [[ -n "$VENDOR" || -n "$MODEL" ]]; then
            info "  Device: ${VENDOR:-unknown} ${MODEL:-unknown}"
        fi
    fi

    # Test baud rates
    if [[ "$STTY_AVAILABLE" == true ]]; then
        for baud in "${BAUD_RATES[@]}"; do
            if stty -F "$port" "$baud" 2>/dev/null; then
                ok "  Baud rate $baud: compatible"
                RADIO_PORTS+=("$port")
                break
            else
                warn "  Baud rate $baud: failed"
            fi
        done
    else
        RADIO_PORTS+=("$port")
    fi
done

# Summary
header "Summary"

if [[ ${#RADIO_PORTS[@]} -gt 0 ]]; then
    ok "Radio port(s) accessible: ${RADIO_PORTS[*]}"
    echo ""
    echo "To use with MCADV, add to your run command:"
    echo "  python3 adventure_bot.py --port ${RADIO_PORTS[0]} --baud 115200 --channel-idx 1"
else
    err "No accessible radio ports found"
fi

echo ""
echo -e "Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"

if [[ $FAIL -gt 0 ]]; then
    exit 2
elif [[ $WARN -gt 0 ]]; then
    exit 1
else
    exit 0
fi

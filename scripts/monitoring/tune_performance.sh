#!/bin/bash
# tune_performance.sh - Auto-detect hardware and recommend/apply performance settings
# Usage: ./tune_performance.sh [-h|--help] [--apply]

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
SERVICE_NAME="mcadv-bot"
APPLY_SETTINGS=false

ok()     { echo -e "${GREEN}✓${NC} $1"; }
warn()   { echo -e "${YELLOW}⚠${NC} $1"; }
info()   { echo -e "${BLUE}ℹ${NC} $1"; }
rec()    { echo -e "${CYAN}→${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

usage() {
    echo "Usage: $0 [-h|--help] [--apply]"
    echo ""
    echo "Auto-detect hardware and display performance recommendations."
    echo ""
    echo "Options:"
    echo "  --apply   Apply recommended settings to systemd service"
    echo ""
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --apply) APPLY_SETTINGS=true; shift ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Hardware detection
header "Hardware Detection"

# Detect Raspberry Pi
HW_TYPE="other"
HW_DESC="Unknown Linux system"

if [[ -f /proc/device-tree/model ]]; then
    MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "")
    if [[ "$MODEL" == *"Raspberry Pi 5"* ]]; then
        HW_TYPE="pi5"
        HW_DESC="Raspberry Pi 5"
    elif [[ "$MODEL" == *"Raspberry Pi 4"* ]]; then
        HW_TYPE="pi4"
        HW_DESC="Raspberry Pi 4"
    elif [[ "$MODEL" == *"Raspberry Pi Zero 2"* ]]; then
        HW_TYPE="pizero2"
        HW_DESC="Raspberry Pi Zero 2W"
    elif [[ "$MODEL" == *"Raspberry Pi"* ]]; then
        HW_TYPE="pi_other"
        HW_DESC="Raspberry Pi (older)"
    elif [[ "$MODEL" == *"Jetson"* ]]; then
        HW_TYPE="jetson"
        HW_DESC="NVIDIA Jetson"
    fi
elif [[ -f /etc/nv_tegra_release ]]; then
    HW_TYPE="jetson"
    HW_DESC="NVIDIA Jetson"
fi

ok "Detected hardware: $HW_DESC"

# Get RAM
MEM_MB=$(free -m | awk '/Mem:/{print $2}')
ok "Total RAM: ${MEM_MB}MB"

# Get CPU cores
CPU_CORES=$(nproc 2>/dev/null || echo "1")
ok "CPU cores: $CPU_CORES"

# Check storage type (SD card vs SSD)
STORAGE_TYPE="unknown"
ROOT_DEV=$(df / | awk 'NR==2{print $1}' | sed 's|/dev/||' | sed 's|[0-9]*$||')
if [[ "$ROOT_DEV" == mmcblk* ]] || [[ "$ROOT_DEV" == mmc* ]]; then
    STORAGE_TYPE="sdcard"
    warn "Running from SD card (slower I/O)"
elif [[ "$ROOT_DEV" == sd* ]] || [[ "$ROOT_DEV" == nvme* ]]; then
    STORAGE_TYPE="ssd"
    ok "Running from SSD/USB drive (good I/O)"
fi

# Recommendations
header "Performance Recommendations"

# Model recommendation based on RAM
echo ""
echo "🤖 Recommended Ollama Model:"
if [[ $MEM_MB -ge 15000 ]]; then
    RECOMMENDED_MODEL="llama3.1:8b"
    MEMORY_LIMIT="4000M"
    rec "llama3.1:8b - Best storytelling quality (needs 8GB+ free RAM)"
elif [[ $MEM_MB -ge 6000 ]]; then
    RECOMMENDED_MODEL="llama3.1:8b"
    MEMORY_LIMIT="3000M"
    rec "llama3.1:8b - Good choice for 8GB systems"
elif [[ $MEM_MB -ge 3500 ]]; then
    RECOMMENDED_MODEL="llama3.2:3b"
    MEMORY_LIMIT="2000M"
    rec "llama3.2:3b - Good balance for 4GB systems"
elif [[ $MEM_MB -ge 1500 ]]; then
    RECOMMENDED_MODEL="llama3.2:1b"
    MEMORY_LIMIT="1200M"
    rec "llama3.2:1b - Lightweight, suitable for 2GB systems"
else
    RECOMMENDED_MODEL="llama3.2:1b"
    MEMORY_LIMIT="800M"
    warn "Very low RAM - consider running without Ollama (offline story mode)"
    rec "llama3.2:1b - Minimum viable model"
fi

echo ""
echo "📊 Resource Limits:"
rec "MemoryHigh=${MEMORY_LIMIT} (soft limit for the bot process)"
rec "CPUQuota=$((CPU_CORES * 80))% (80% of all cores)"

echo ""
echo "🔄 Restart Policy:"
rec "Restart=always"
rec "RestartSec=10"
rec "StartLimitBurst=5"

# Raspberry Pi specific
if [[ "$HW_TYPE" == pi* ]]; then
    echo ""
    echo "🍓 Raspberry Pi Optimizations:"

    # Check for thermal throttling
    if command -v vcgencmd &>/dev/null; then
        THROTTLED=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2 || echo "0x0")
        if [[ "$THROTTLED" != "0x0" ]]; then
            warn "Thermal throttling detected! (status: $THROTTLED)"
            rec "Add a heatsink or active cooling fan"
        else
            ok "No thermal throttling detected"
        fi

        TEMP_RAW=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | tr -d "'C" || echo "0")
        TEMP=$(echo "$TEMP_RAW" | cut -d. -f1)
        if [[ "$TEMP" -gt 70 ]]; then
            warn "CPU temperature: ${TEMP}°C - Add cooling!"
            rec "Install active cooling (fan case or heatsink)"
        elif [[ "$TEMP" -gt 60 ]]; then
            warn "CPU temperature: ${TEMP}°C - Monitor closely"
        else
            ok "CPU temperature: ${TEMP}°C (normal)"
        fi
    fi

    # SD card advice
    if [[ "$STORAGE_TYPE" == "sdcard" ]]; then
        warn "Running from SD card"
        rec "Use a USB SSD for Ollama models (3-10x faster loading)"
        rec "Store models on SSD: OLLAMA_MODELS=/mnt/ssd/.ollama/models ollama serve"
    fi

    # Swap check
    SWAP_TOTAL=$(free -m | awk '/Swap:/{print $2}')
    if [[ $SWAP_TOTAL -eq 0 ]]; then
        warn "No swap configured"
        rec "Add 2GB swap for Ollama stability:"
        rec "  sudo dphys-swapfile swapconf  # edit CONF_SWAPSIZE=2048"
        rec "  sudo dphys-swapfile setup && sudo dphys-swapfile swapon"
    else
        ok "Swap: ${SWAP_TOTAL}MB configured"
    fi
fi

# Current resource usage
header "Current Resource Usage"
echo ""
MEM_USED=$(free -m | awk '/Mem:/{print $3}')
MEM_PCT=$(( MEM_USED * 100 / MEM_MB ))
echo "Memory: ${MEM_USED}MB / ${MEM_MB}MB (${MEM_PCT}%)"

if command -v top &>/dev/null; then
    CPU_IDLE=$(top -bn1 2>/dev/null | grep "Cpu" | awk '{print $8}' | cut -d. -f1 || echo "unknown")
    if [[ "$CPU_IDLE" != "unknown" ]]; then
        CPU_USED=$(( 100 - ${CPU_IDLE:-100} ))
        echo "CPU usage: approx ${CPU_USED}%"
    fi
fi

DISK_FREE=$(df -h / | awk 'NR==2{print $4}')
echo "Disk free (/): $DISK_FREE"

# Apply settings
if [[ "$APPLY_SETTINGS" == true ]]; then
    header "Applying Settings"

    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    if [[ ! -f "$SERVICE_FILE" ]]; then
        warn "Service file not found: $SERVICE_FILE"
        info "Install the service first: sudo ${WORKDIR}/scripts/deployment/install_service.sh"
    elif [[ $EUID -ne 0 ]]; then
        warn "Sudo required to apply settings"
        info "Run: sudo $0 --apply"
    else
        # Update MemoryHigh
        sed -i "s|^MemoryHigh=.*|MemoryHigh=${MEMORY_LIMIT}|" "$SERVICE_FILE"
        # Update CPUQuota
        sed -i "s|^CPUQuota=.*|CPUQuota=$((CPU_CORES * 80))%|" "$SERVICE_FILE"
        systemctl daemon-reload
        ok "Settings applied to $SERVICE_FILE"
        info "Restart service to apply: sudo systemctl restart ${SERVICE_NAME}"
    fi
fi

# Log rotation setup check
header "Log Rotation"
if [[ -f "/etc/logrotate.d/mcadv" ]]; then
    ok "Log rotation configured"
else
    warn "Log rotation not configured"
    rec "Set up log rotation: sudo ${WORKDIR}/scripts/deployment/setup_logrotate.sh"
fi

header "Summary"
echo ""
info "Recommended model: $RECOMMENDED_MODEL"
info "Memory limit: $MEMORY_LIMIT"
echo ""
if [[ "$APPLY_SETTINGS" == false ]]; then
    info "To apply recommended settings to the service:"
    info "  sudo $0 --apply"
fi

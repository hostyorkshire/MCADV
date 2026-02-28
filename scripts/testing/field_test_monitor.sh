#!/bin/bash
# field_test_monitor.sh - Multi-pane monitoring for MCADV field testing
# Usage: ./field_test_monitor.sh [-h|--help]

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
SESSION_NAME="mcadv-monitor"

usage() {
    echo "Usage: $0 [-h|--help]"
    echo ""
    echo "Launch a tmux monitoring dashboard with 4 panes:"
    echo "  Pane 1 (top-left):     adventure_bot.log tail"
    echo "  Pane 2 (top-right):    meshcore.log tail"
    echo "  Pane 3 (bottom-left):  Resource monitor (memory, disk)"
    echo "  Pane 4 (bottom-right): Active sessions display"
    echo ""
    echo "Controls:"
    echo "  Ctrl+B, arrow   Navigate between panes"
    echo "  Ctrl+B, d       Detach (monitoring continues)"
    echo "  Ctrl+B, &       Kill session"
    echo "  tmux attach -t $SESSION_NAME  Re-attach"
    exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

info() { echo -e "${BLUE}ℹ${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }

# Check for tmux
if ! command -v tmux &>/dev/null; then
    err "tmux is not installed"
    echo ""
    echo "Install tmux:"
    echo "  Raspberry Pi / Debian / Ubuntu:"
    echo "    sudo apt install tmux"
    echo ""
    echo "Alternatively, monitor manually with these commands in separate terminals:"
    echo "  tail -f ${WORKDIR}/logs/adventure_bot.log"
    echo "  tail -f ${WORKDIR}/logs/meshcore.log"
    echo "  watch -n 5 'free -h && df -h /'"
    echo "  watch -n 10 'python3 -c \"import json; d=json.load(open(\\\"${WORKDIR}/adventure_sessions.json\\\")) if __import__(\\\"os\\\").path.exists(\\\"${WORKDIR}/adventure_sessions.json\\\") else {}; print(f\\\"Active sessions: {len(d)}\\\")\"'"
    exit 1
fi

# Ensure logs directory and files exist
mkdir -p "${WORKDIR}/logs"
touch "${WORKDIR}/logs/adventure_bot.log" 2>/dev/null || true
touch "${WORKDIR}/logs/meshcore.log" 2>/dev/null || true

# Resource monitor command
RESOURCE_CMD="while true; do
    echo '=== $(date) ===';
    echo '';
    echo '--- Memory ---';
    free -h;
    echo '';
    echo '--- Disk ---';
    df -h / 2>/dev/null || df -h .;
    echo '';
    echo '--- CPU (1s sample) ---';
    top -bn1 2>/dev/null | grep 'Cpu' | head -1 || true;
    echo '';
    sleep 10;
done"

# Sessions display command
SESSIONS_CMD="while true; do
    echo '=== Active Sessions: $(date) ===';
    echo '';
    SESS_FILE=${WORKDIR}/adventure_sessions.json;
    if [ -f \"\$SESS_FILE\" ]; then
        python3 -c \"
import json, sys
try:
    with open('${WORKDIR}/adventure_sessions.json') as f:
        data = json.load(f)
    print(f'Total sessions: {len(data)}')
    for k, v in list(data.items())[:10]:
        state = v.get('state', 'unknown')
        channel = v.get('channel_idx', '?')
        print(f'  User: {k[:20]} | State: {state} | Channel: {channel}')
    if len(data) > 10:
        print(f'  ... and {len(data)-10} more')
except Exception as e:
    print(f'Error reading sessions: {e}')
\" 2>/dev/null || echo 'No session data';
    else
        echo 'No session file found';
        echo \"Expected: \$SESS_FILE\";
    fi;
    echo '';
    sleep 10;
done"

# Kill existing session if it exists
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

ok "Starting MCADV monitoring dashboard..."
info "Working directory: $WORKDIR"

# Create tmux session
tmux new-session -d -s "$SESSION_NAME" -x 220 -y 50

# Pane 1 (top-left): adventure_bot.log
tmux send-keys -t "${SESSION_NAME}:0.0" \
    "echo '=== adventure_bot.log ==='; tail -f '${WORKDIR}/logs/adventure_bot.log'" Enter

# Split horizontally for Pane 2 (top-right): meshcore.log
tmux split-window -t "${SESSION_NAME}:0.0" -h
tmux send-keys -t "${SESSION_NAME}:0.1" \
    "echo '=== meshcore.log ==='; tail -f '${WORKDIR}/logs/meshcore.log'" Enter

# Select pane 0, split vertically for Pane 3 (bottom-left): resource monitor
tmux select-pane -t "${SESSION_NAME}:0.0"
tmux split-window -t "${SESSION_NAME}:0.0" -v
tmux send-keys -t "${SESSION_NAME}:0.2" \
    "echo '=== Resource Monitor ==='; ${RESOURCE_CMD}" Enter

# Select pane 1, split vertically for Pane 4 (bottom-right): sessions
tmux select-pane -t "${SESSION_NAME}:0.1"
tmux split-window -t "${SESSION_NAME}:0.1" -v
tmux send-keys -t "${SESSION_NAME}:0.3" \
    "echo '=== Active Sessions ==='; ${SESSIONS_CMD}" Enter

# Set pane titles
tmux select-pane -t "${SESSION_NAME}:0.0" -T "Bot Log"
tmux select-pane -t "${SESSION_NAME}:0.1" -T "MeshCore Log"
tmux select-pane -t "${SESSION_NAME}:0.2" -T "Resources"
tmux select-pane -t "${SESSION_NAME}:0.3" -T "Sessions"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MCADV Field Test Monitor Ready       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Dashboard layout:"
echo "  ┌─────────────────┬─────────────────┐"
echo "  │ adventure_bot   │ meshcore.log    │"
echo "  │ .log            │                 │"
echo "  ├─────────────────┼─────────────────┤"
echo "  │ Resource Monitor│ Active Sessions │"
echo "  └─────────────────┴─────────────────┘"
echo ""
echo "Attaching to monitoring session..."
echo ""
echo -e "${YELLOW}Controls:${NC}"
echo "  Ctrl+B, arrow keys  Navigate panes"
echo "  Ctrl+B, d           Detach (keep monitoring)"
echo "  Ctrl+B, &           Kill session"
echo ""
echo "To re-attach later:  tmux attach -t $SESSION_NAME"
echo ""

# Attach to the session
tmux attach-session -t "$SESSION_NAME"

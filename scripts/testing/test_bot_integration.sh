#!/bin/bash
# test_bot_integration.sh - Full integration tests for MCADV adventure bot
# Usage: ./test_bot_integration.sh [-h|--help] [--url URL] [--port PORT]

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

# Defaults
BOT_URL="http://localhost:5000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BOT_PID=""
TEST_SESSION_IDS=()

usage() {
    echo "Usage: $0 [-h|--help] [--url URL]"
    echo ""
    echo "Run integration tests against a running MCADV bot instance."
    echo ""
    echo "Options:"
    echo "  --url URL   Bot HTTP API URL (default: http://localhost:5000)"
    echo ""
    echo "The bot must be running in distributed mode with --http-port 5000."
    echo "See: python3 adventure_bot.py --distributed-mode --http-port 5000"
    echo ""
    echo "Exit codes:"
    echo "  0 - All tests passed"
    echo "  1 - Some tests failed"
    echo "  2 - Cannot connect to bot"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --url) BOT_URL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()   { echo -e "${GREEN}✓ PASS${NC} $1"; PASS=$(( PASS + 1 )); }
err()  { echo -e "${RED}✗ FAIL${NC} $1"; FAIL=$(( FAIL + 1 )); }
warn() { echo -e "${YELLOW}⚠ WARN${NC} $1"; WARN=$(( WARN + 1 )); }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

cleanup() {
    if [[ ${#TEST_SESSION_IDS[@]} -gt 0 ]]; then
        info "Cleaning up test sessions..."
        for sid in "${TEST_SESSION_IDS[@]}"; do
            curl -s -X POST "${BOT_URL}/message" \
                -H "Content-Type: application/json" \
                -d "{\"sender\": \"${sid}\", \"content\": \"!reset\", \"channel_idx\": 99}" \
                &>/dev/null || true
        done
    fi
}
trap cleanup EXIT

send_message() {
    local sender="$1"
    local content="$2"
    local channel="${3:-99}"
    curl -s --connect-timeout 10 --max-time 30 \
        -X POST "${BOT_URL}/message" \
        -H "Content-Type: application/json" \
        -d "{\"sender\": \"${sender}\", \"content\": \"${content}\", \"channel_idx\": ${channel}}" \
        2>/dev/null || echo ""
}

header "MCADV Bot Integration Tests"
echo "Timestamp: $(date)"
echo "Bot URL: $BOT_URL"
echo "Working directory: $WORKDIR"

# Check prerequisites
header "Prerequisites"
if command -v curl &>/dev/null; then
    ok "curl available"
else
    err "curl not found - required for HTTP tests"
    exit 2
fi

if command -v python3 &>/dev/null; then
    ok "python3 available"
else
    err "python3 not found"
    exit 2
fi

# Check bot connectivity
header "Bot Connectivity"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 "${BOT_URL}/api/health" 2>/dev/null || echo "000")

if [[ "$HEALTH_STATUS" == "200" ]]; then
    ok "Bot health endpoint responding (HTTP 200)"
elif [[ "$HEALTH_STATUS" == "000" ]]; then
    err "Cannot connect to bot at $BOT_URL"
    echo ""
    echo "Start the bot in distributed mode first:"
    echo "  cd $WORKDIR"
    echo "  source venv/bin/activate"
    echo "  python3 adventure_bot.py --distributed-mode --http-port 5000"
    exit 2
else
    warn "Bot health endpoint returned HTTP $HEALTH_STATUS"
fi

# Test 1: !help command
header "Test 1: !help Command"
RESPONSE=$(send_message "test_user_help" "!help" 99)
TEST_SESSION_IDS+=("test_user_help")

if [[ -n "$RESPONSE" ]]; then
    REPLY=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('response', data.get('message', '')))
" 2>/dev/null || echo "")
    if [[ "$REPLY" == *"!"* ]] || [[ "$REPLY" == *"help"* ]] || [[ "$REPLY" == *"adv"* ]]; then
        ok "!help returned help text"
    else
        warn "!help response may not contain expected content"
        info "  Response: ${REPLY:0:100}"
    fi
else
    err "!help returned no response"
fi

# Test 2: !adv command (start adventure)
header "Test 2: !adv Command (Start Adventure)"
RESPONSE=$(send_message "test_user_adv" "!adv" 99)
TEST_SESSION_IDS+=("test_user_adv")

if [[ -n "$RESPONSE" ]]; then
    REPLY=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('response', data.get('message', '')))
" 2>/dev/null || echo "")
    if [[ -n "$REPLY" ]]; then
        ok "!adv started an adventure session"
        info "  Opening: ${REPLY:0:100}"
    else
        err "!adv returned empty response"
    fi
else
    err "!adv returned no response"
fi

# Test 3: Numeric choice
header "Test 3: Numeric Choice Response"
# First start a session
send_message "test_user_choice" "!adv" 99 &>/dev/null
TEST_SESSION_IDS+=("test_user_choice")
sleep 1

RESPONSE=$(send_message "test_user_choice" "1" 99)
if [[ -n "$RESPONSE" ]]; then
    REPLY=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('response', data.get('message', '')))
" 2>/dev/null || echo "")
    if [[ -n "$REPLY" ]]; then
        ok "Numeric choice '1' processed successfully"
    else
        warn "Numeric choice returned empty response"
    fi
else
    err "Numeric choice returned no response"
fi

# Test 4: Session persistence
header "Test 4: Session Persistence"
SESS_FILE="${WORKDIR}/adventure_sessions.json"
if [[ -f "$SESS_FILE" ]]; then
    SESSION_COUNT=$(python3 -c "
import json
with open('${SESS_FILE}') as f:
    data = json.load(f)
print(len(data))
" 2>/dev/null || echo "0")
    ok "Session file exists with ${SESSION_COUNT} session(s)"
else
    warn "Session file not found at $SESS_FILE"
fi

# Test 5: Collaborative mode (multiple users, same channel)
header "Test 5: Collaborative Mode (Multiple Users, Same Channel)"
COLLAB_CHANNEL=88

RESPONSE1=$(send_message "test_collab_user1" "!adv" $COLLAB_CHANNEL)
TEST_SESSION_IDS+=("test_collab_user1")
sleep 0.5
RESPONSE2=$(send_message "test_collab_user2" "!adv" $COLLAB_CHANNEL)
TEST_SESSION_IDS+=("test_collab_user2")

if [[ -n "$RESPONSE1" && -n "$RESPONSE2" ]]; then
    ok "Multiple users can interact on same channel"
else
    warn "Collaborative mode test inconclusive"
fi

# Test 6: !reset command
header "Test 6: !reset Command"
send_message "test_user_reset" "!adv" 99 &>/dev/null
TEST_SESSION_IDS+=("test_user_reset")
sleep 0.5

RESPONSE=$(send_message "test_user_reset" "!reset" 99)
if [[ -n "$RESPONSE" ]]; then
    ok "!reset command processed"
else
    warn "!reset returned no response"
fi

# Summary
header "Test Summary"
echo ""
echo -e "Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo "❌ Integration tests failed - review errors above"
    exit 1
elif [[ $WARN -gt 0 ]]; then
    echo "⚠️  Tests completed with warnings"
    exit 0
else
    echo "✅ All integration tests passed"
    exit 0
fi

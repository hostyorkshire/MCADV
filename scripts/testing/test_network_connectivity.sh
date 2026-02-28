#!/bin/bash
# test_network_connectivity.sh - MCADV network connectivity tester
#
# Tests connectivity between Radio Gateway and Bot Server.
#
# Usage:
#   ./scripts/testing/test_network_connectivity.sh --bot-server <hostname>
#   ./scripts/testing/test_network_connectivity.sh --listen
#   ./scripts/testing/test_network_connectivity.sh --full-test <hostname>
#
# Exit codes:
#   0 - All tests passed
#   1 - Warnings
#   2 - Failures

set -euo pipefail

if [[ -z "${NO_COLOR:-}" && -t 1 ]]; then
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    GREEN='' BLUE='' YELLOW='' RED='' CYAN='' NC=''
fi

PASS=0
WARN=0
FAIL=0
MODE=""
TARGET_HOST=""
BOT_PORT=5000

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

MCADV network connectivity tester for distributed (radio gateway ↔ bot server) mode.

Options:
  --bot-server HOST   Test connectivity FROM this device TO the bot server at HOST
  --listen            Run on bot server: verify port ${BOT_PORT} is accessible
  --full-test HOST    Run comprehensive bi-directional connectivity tests to HOST
  --port PORT         Bot server HTTP port (default: ${BOT_PORT})
  -h, --help          Show this help and exit

Examples:
  # On Radio Gateway – test bot server connection
  $0 --bot-server pi5.local

  # On Bot Server – verify it is reachable
  $0 --listen

  # Full bi-directional test
  $0 --full-test pi5.local

Exit codes:
  0 - All tests passed
  1 - Warnings
  2 - Failures
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --bot-server) MODE="client"; TARGET_HOST="$2"; shift 2 ;;
        --listen)     MODE="listen"; shift ;;
        --full-test)  MODE="full";   TARGET_HOST="$2"; shift 2 ;;
        --port)       BOT_PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$MODE" ]] && usage

ok()     { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$(( PASS + 1 )); }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$(( WARN + 1 )); }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$(( FAIL + 1 )); }
info()   { echo -e "       ${BLUE}→${NC} $1"; }
header() { echo -e "\n${CYAN}─── $1 ───${NC}"; }

# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------
test_ping() {
    local host="$1"
    header "Ping Connectivity"
    if ping -c 3 -W 3 "$host" &>/dev/null 2>&1; then
        local latency
        latency="$(ping -c 3 -W 3 "$host" 2>/dev/null | tail -1 | awk -F '/' '{print $5}' || echo '?')"
        ok "Ping to ${host}: avg ${latency} ms"
    else
        fail "Cannot ping ${host}"
        info "Check: network cable / Wi-Fi / mDNS"
    fi
}

test_dns() {
    local host="$1"
    header "DNS Resolution"
    # Skip DNS test for bare IP addresses
    if echo "$host" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        info "Skipping DNS test (IP address provided)"
        return
    fi
    if command -v getent &>/dev/null; then
        if getent hosts "$host" &>/dev/null; then
            local ip
            ip="$(getent hosts "$host" | awk '{print $1}')"
            ok "DNS resolved: ${host} → ${ip}"
        else
            fail "DNS resolution failed for: ${host}"
            info "Try using IP address instead, or configure /etc/hosts"
        fi
    elif command -v nslookup &>/dev/null; then
        if nslookup "$host" &>/dev/null; then
            ok "DNS resolved: ${host}"
        else
            fail "DNS resolution failed for: ${host}"
        fi
    else
        warn "No DNS lookup tool available (getent / nslookup)"
    fi
}

test_http_port() {
    local host="$1"
    local port="$2"
    header "HTTP Port ${port}"
    if command -v nc &>/dev/null; then
        if nc -z -w 5 "$host" "$port" &>/dev/null 2>&1; then
            ok "Port ${port} is reachable on ${host}"
        else
            fail "Port ${port} is NOT reachable on ${host}"
            info "Check: firewall, service running, correct host/port"
        fi
    elif command -v curl &>/dev/null; then
        if curl -s --connect-timeout 5 "http://${host}:${port}/" &>/dev/null; then
            ok "HTTP connection to ${host}:${port} succeeded"
        else
            fail "HTTP connection to ${host}:${port} failed"
        fi
    else
        warn "nc and curl not available – cannot test port connectivity"
    fi
}

test_api_health() {
    local host="$1"
    local port="$2"
    header "API Health Endpoint"
    local url="http://${host}:${port}/health"
    if command -v curl &>/dev/null; then
        local http_code
        http_code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "$url" 2>/dev/null || echo '000')"
        if [[ "$http_code" == "200" ]]; then
            ok "Health endpoint ${url} returned HTTP 200"
        elif [[ "$http_code" == "000" ]]; then
            fail "Health endpoint ${url} is not reachable"
            info "Ensure adventure_bot.py is running with --http flag"
        else
            warn "Health endpoint returned HTTP ${http_code}"
        fi
    else
        warn "curl not available – skipping API health check"
    fi
}

test_latency() {
    local host="$1"
    local port="$2"
    header "Latency Measurement"
    if command -v curl &>/dev/null; then
        local time_ms
        time_ms="$(curl -s -o /dev/null -w '%{time_total}' --connect-timeout 5 "http://${host}:${port}/health" 2>/dev/null || echo '0')"
        local time_ms_int
        time_ms_int="$(echo "$time_ms * 1000" | bc 2>/dev/null | cut -d. -f1 || echo '?')"
        if [[ "$time_ms_int" != "?" && "$time_ms_int" -lt 2000 ]]; then
            ok "HTTP latency to ${host}:${port}: ${time_ms_int} ms"
        elif [[ "$time_ms_int" == "?" ]]; then
            warn "Could not measure HTTP latency (bc not available)"
        else
            warn "High HTTP latency: ${time_ms_int} ms (>2000 ms)"
        fi
    else
        warn "curl not available – skipping latency test"
    fi
}

test_firewall() {
    header "Firewall Status"
    if command -v ufw &>/dev/null; then
        local ufw_status
        ufw_status="$(ufw status 2>/dev/null | head -1 || echo 'unknown')"
        if echo "$ufw_status" | grep -qi "inactive"; then
            ok "UFW firewall is inactive (all ports open)"
        elif echo "$ufw_status" | grep -qi "active"; then
            if ufw status 2>/dev/null | grep -q "${BOT_PORT}"; then
                ok "UFW firewall active and port ${BOT_PORT} is allowed"
            else
                warn "UFW firewall active but port ${BOT_PORT} may not be allowed"
                info "Allow: sudo ufw allow ${BOT_PORT}/tcp"
            fi
        else
            info "UFW status: ${ufw_status}"
        fi
    elif command -v iptables &>/dev/null; then
        info "iptables present – manual firewall review recommended"
    else
        info "No recognised firewall tool found (ufw / iptables)"
    fi
}

test_listen_mode() {
    header "Listen Mode – Bot Server Port Check"
    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":${BOT_PORT} "; then
            ok "Port ${BOT_PORT} is listening"
        else
            warn "Port ${BOT_PORT} is NOT currently listening"
            info "Start bot: ./run_adventure_bot.sh  (or systemctl start mcadv-bot)"
        fi
    else
        warn "ss not available – cannot verify listening port"
    fi
    test_firewall
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  MCADV Network Connectivity Tester           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Mode:      ${MODE}"
[[ -n "$TARGET_HOST" ]] && echo "  Target:    ${TARGET_HOST}:${BOT_PORT}"
echo "  Timestamp: $(date)"

case "$MODE" in
    client)
        test_ping     "$TARGET_HOST"
        test_dns      "$TARGET_HOST"
        test_http_port "$TARGET_HOST" "$BOT_PORT"
        test_api_health "$TARGET_HOST" "$BOT_PORT"
        ;;
    listen)
        test_listen_mode
        ;;
    full)
        test_ping     "$TARGET_HOST"
        test_dns      "$TARGET_HOST"
        test_http_port "$TARGET_HOST" "$BOT_PORT"
        test_api_health "$TARGET_HOST" "$BOT_PORT"
        test_latency  "$TARGET_HOST" "$BOT_PORT"
        test_firewall
        ;;
esac

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}  ❌ Connectivity test FAILED${NC}"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}  ⚠  Connectivity test passed with warnings${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ All connectivity tests passed!${NC}"
    exit 0
fi

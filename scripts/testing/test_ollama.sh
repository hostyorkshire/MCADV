#!/bin/bash
# test_ollama.sh - Check Ollama connectivity, models, and story generation
# Usage: ./test_ollama.sh [-h|--help] [--url URL] [--model MODEL]

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
OLLAMA_URL="http://localhost:11434"
MODEL="llama3.1:8b"

usage() {
    echo "Usage: $0 [-h|--help] [--url URL] [--model MODEL]"
    echo ""
    echo "Check Ollama connectivity, model availability, and story generation."
    echo ""
    echo "Options:"
    echo "  --url URL      Ollama URL (default: http://localhost:11434)"
    echo "  --model MODEL  Model to test (default: llama3.1:8b)"
    echo ""
    echo "Exit codes:"
    echo "  0 - All checks passed"
    echo "  1 - Warnings"
    echo "  2 - Critical failure"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --url) OLLAMA_URL="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

ok()   { echo -e "${GREEN}✓${NC} $1"; PASS=$(( PASS + 1 )); }
err()  { echo -e "${RED}✗${NC} $1"; FAIL=$(( FAIL + 1 )); }
warn() { echo -e "${YELLOW}⚠${NC} $1"; WARN=$(( WARN + 1 )); }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

header "MCADV Ollama Test"
echo "Timestamp: $(date)"
echo "Ollama URL: $OLLAMA_URL"
echo "Model: $MODEL"

# Check curl availability
header "Prerequisites"
if command -v curl &>/dev/null; then
    ok "curl available"
else
    err "curl not found - required for HTTP tests"
    exit 2
fi

# Check disk space
header "Disk Space"
DISK_FREE_KB=$(df -k / | awk 'NR==2{print $4}')
DISK_FREE_GB=$(( DISK_FREE_KB / 1024 / 1024 ))

if [[ $DISK_FREE_GB -ge 10 ]]; then
    ok "Disk space: ${DISK_FREE_GB}GB free (sufficient for models)"
elif [[ $DISK_FREE_GB -ge 3 ]]; then
    warn "Disk space: ${DISK_FREE_GB}GB free (enough for small models only)"
    info "  Suggested lighter models: llama3.2:1b (~1.3GB), llama3.2:3b (~3.2GB)"
else
    err "Disk space: ${DISK_FREE_GB}GB free (insufficient for most models)"
    info "  Free at least 3GB for small models or 10GB for recommended models"
fi

# Check memory
MEM_MB=$(free -m 2>/dev/null | awk '/Mem:/{print $2}' || echo "0")
if [[ $MEM_MB -ge 8000 ]]; then
    ok "RAM: ${MEM_MB}MB - sufficient for llama3.1:8b"
elif [[ $MEM_MB -ge 4000 ]]; then
    warn "RAM: ${MEM_MB}MB - consider llama3.2:3b or llama3.2:1b for better performance"
    info "  Suggested: ollama pull llama3.2:3b"
elif [[ $MEM_MB -ge 2000 ]]; then
    warn "RAM: ${MEM_MB}MB - use llama3.2:1b for best results"
    info "  Suggested: ollama pull llama3.2:1b"
else
    warn "RAM: ${MEM_MB}MB - very limited, Ollama may be slow"
fi

# Check Ollama service
header "Ollama Connectivity"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${OLLAMA_URL}/api/tags" 2>/dev/null; true)
HTTP_STATUS="${HTTP_STATUS:-000}"

if [[ "$HTTP_STATUS" == "200" ]]; then
    ok "Ollama is running at $OLLAMA_URL (HTTP $HTTP_STATUS)"
else
    err "Ollama not reachable at $OLLAMA_URL (HTTP $HTTP_STATUS)"
    echo ""
    echo "To start Ollama:"
    echo "  ollama serve"
    echo ""
    echo "To install Ollama:"
    echo "  curl -fsSL https://ollama.ai/install.sh | sh"
    exit 2
fi

# Check available models
header "Model Availability"

MODELS_JSON=$(curl -s --connect-timeout 5 "${OLLAMA_URL}/api/tags" 2>/dev/null || echo '{"models":[]}')
AVAILABLE_MODELS=$(echo "$MODELS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print('\n'.join(models))
" 2>/dev/null || echo "")

if [[ -z "$AVAILABLE_MODELS" ]]; then
    warn "No models downloaded yet"
    info "  Pull recommended model: ollama pull llama3.1:8b"
    info "  Or lighter model:       ollama pull llama3.2:1b"
else
    ok "Models available:"
    while IFS= read -r model; do
        [[ -n "$model" ]] && info "  - $model"
    done <<< "$AVAILABLE_MODELS"
fi

# Check if requested model is available
MODEL_FOUND=false
while IFS= read -r m; do
    if [[ "$m" == "$MODEL" || "$m" == "${MODEL}:latest" ]]; then
        MODEL_FOUND=true
        break
    fi
done <<< "$AVAILABLE_MODELS"

if [[ "$MODEL_FOUND" == true ]]; then
    ok "Requested model '$MODEL' is available"
else
    warn "Requested model '$MODEL' not found locally"
    info "  Pull it with: ollama pull $MODEL"
fi

# Test story generation
header "Story Generation Test"

if [[ "$MODEL_FOUND" == true ]]; then
    info "Sending test story prompt to Ollama (this may take 10-30 seconds)..."

    PROMPT='Write a 2-sentence adventure story opening. Be creative and concise.'
    RESPONSE=$(curl -s --connect-timeout 30 --max-time 60 \
        -X POST "${OLLAMA_URL}/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"${MODEL}\", \"prompt\": \"${PROMPT}\", \"stream\": false}" \
        2>/dev/null || echo "")

    if [[ -n "$RESPONSE" ]]; then
        STORY=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('response', '').strip()[:200])
" 2>/dev/null || echo "")

        if [[ -n "$STORY" ]]; then
            ok "Story generation successful"
            info "  Sample output: ${STORY:0:150}..."
        else
            err "Story generation returned empty response"
        fi
    else
        err "Story generation request failed (timeout or connection error)"
    fi
else
    warn "Skipping story generation test (model not available)"
    info "  Pull model first: ollama pull $MODEL"
fi

# Summary
header "Summary"
echo -e "Results: ${GREEN}${PASS} passed${NC}  ${YELLOW}${WARN} warnings${NC}  ${RED}${FAIL} failed${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo "❌ Ollama setup needs attention before deploying MCADV"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo "⚠️  Ollama is running but some items need attention"
    exit 1
else
    echo "✅ Ollama is ready for MCADV deployment"
    exit 0
fi

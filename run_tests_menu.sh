#!/usr/bin/env bash
# =============================================================================
# MCADV Interactive Test Menu
# =============================================================================
# A comprehensive, color-coded, interactive testing interface.
# Usage: ./run_tests_menu.sh [--verbose | --quiet]
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors & formatting
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/logs/test_results"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LAST_RESULT_FILE="$RESULTS_DIR/last_run_${TIMESTAMP}.txt"
VERBOSE=0
QUIET=0
PASS_COUNT=0
FAIL_COUNT=0
PYTHON="python3"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --verbose|-v) VERBOSE=1 ;;
    --quiet|-q)   QUIET=1   ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo -e "${CYAN}${BOLD}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}${BOLD}[PASS]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}${BOLD}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}${BOLD}[FAIL]${RESET}  $*"; }
header()  { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════${RESET}"; \
            echo -e " ${BOLD}$*${RESET}"; \
            echo -e "${BOLD}${BLUE}══════════════════════════════════════════${RESET}\n"; }

spinner() {
  local pid=$1 msg=$2
  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r${CYAN}%s${RESET} %s" "${spin:i++%${#spin}:1}" "$msg"
    sleep 0.1
  done
  printf "\r"
}

mkdir -p "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Virtual environment detection
# ---------------------------------------------------------------------------
detect_venv() {
  if [[ -d "$SCRIPT_DIR/venv" ]]; then
    source "$SCRIPT_DIR/venv/bin/activate" 2>/dev/null || true
    PYTHON="$SCRIPT_DIR/venv/bin/python3"
  elif [[ -d "$SCRIPT_DIR/.venv" ]]; then
    source "$SCRIPT_DIR/.venv/bin/activate" 2>/dev/null || true
    PYTHON="$SCRIPT_DIR/.venv/bin/python3"
  fi
  if ! command -v "$PYTHON" &>/dev/null; then
    PYTHON="$(command -v python3 || command -v python)"
  fi
}

# ---------------------------------------------------------------------------
# Pre-flight dependency check
# ---------------------------------------------------------------------------
preflight() {
  local ok=1
  header "Pre-flight Checks"
  for pkg in pytest flask requests; do
    if "$PYTHON" -c "import $pkg" 2>/dev/null; then
      success "$pkg"
    else
      warn "$pkg not installed – run: pip install -r requirements.txt"
      ok=0
    fi
  done
  [[ $ok -eq 1 ]] && success "All dependencies available" || warn "Some dependencies missing"
}

# ---------------------------------------------------------------------------
# Run pytest with a label and optional extra args
# ---------------------------------------------------------------------------
run_pytest() {
  local label="$1"; shift
  local args=("$@")
  local out_file="$RESULTS_DIR/${label}_${TIMESTAMP}.txt"
  local extra=()
  [[ $VERBOSE -eq 1 ]] && extra+=("-v")
  [[ $QUIET -eq 1 ]]   && extra+=("-q")

  header "Running: $label"

  if [[ $QUIET -eq 0 ]]; then
    "$PYTHON" -m pytest "${args[@]}" "${extra[@]}" --tb=short 2>&1 | tee "$out_file"
  else
    "$PYTHON" -m pytest "${args[@]}" "${extra[@]}" --tb=short >"$out_file" 2>&1 &
    spinner $! "Running $label…"
  fi

  local exit_code=${PIPESTATUS[0]:-$?}
  if [[ $exit_code -eq 0 ]]; then
    success "$label PASSED"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    error "$label FAILED (see $out_file)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Save to last-run log
  cat "$out_file" >> "$LAST_RESULT_FILE" 2>/dev/null || true
  return $exit_code
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_summary() {
  header "Test Summary"
  echo -e "  ${GREEN}${BOLD}Passed:${RESET} $PASS_COUNT"
  echo -e "  ${RED}${BOLD}Failed:${RESET} $FAIL_COUNT"
  echo -e "  Results saved to: $LAST_RESULT_FILE"
}

# ---------------------------------------------------------------------------
# Compare last two runs
# ---------------------------------------------------------------------------
compare_runs() {
  header "Comparing Last Two Runs"
  local files=("$RESULTS_DIR"/last_run_*.txt)
  if [[ ${#files[@]} -lt 2 ]]; then
    warn "Need at least two saved runs to compare."
    return
  fi
  local prev="${files[-2]}" curr="${files[-1]}"
  echo "Previous: $prev"
  echo "Current : $curr"
  diff --color=always "$prev" "$curr" || true
}

# ---------------------------------------------------------------------------
# Menu functions
# ---------------------------------------------------------------------------

menu_quick() {
  run_pytest "quick" tests/test_adventure_bot.py tests/test_meshcore.py
}

menu_all() {
  run_pytest "all_tests" tests/
}

menu_category() {
  header "Select Test Category"
  echo "  1) Unit tests (adventure_bot)"
  echo "  2) Integration tests"
  echo "  3) Serial / MeshCore tests"
  echo "  4) LLM integration tests"
  echo "  5) Session / state tests"
  echo "  6) Security tests"
  echo "  7) Performance tests"
  echo "  8) Back"
  echo ""
  read -rp "Category: " choice
  case $choice in
    1) run_pytest "unit"        tests/test_adventure_bot.py ;;
    2) run_pytest "integration" tests/test_integration.py  ;;
    3) run_pytest "serial"      tests/test_meshcore.py tests/test_radio_gateway.py ;;
    4) run_pytest "llm"         tests/test_llm_integration.py ;;
    5) run_pytest "session"     tests/test_adventure_bot.py -k "Session" ;;
    6) run_pytest "security"    tests/test_security.py ;;
    7) run_pytest "performance" tests/test_performance.py ;;
    8) return ;;
    *) warn "Invalid choice" ;;
  esac
}

menu_coverage() {
  header "Coverage Report"
  "$PYTHON" -m pytest tests/ --cov=. --cov-report=term-missing --tb=short
}

menu_lint() {
  header "Linting with flake8"
  "$PYTHON" -m flake8 . \
    --count \
    --max-line-length=120 \
    --extend-ignore=E501,W503 \
    --exclude=venv,.venv,__pycache__,.git \
    --statistics && success "Lint passed" || error "Lint issues found"
}

menu_html_report() {
  header "Generating HTML Coverage Report"
  "$PYTHON" -m pytest tests/ --cov=. --cov-report=html --tb=short
  success "Report saved to htmlcov/index.html"
}

menu_view_results() {
  header "Recent Results"
  ls -1t "$RESULTS_DIR"/*.txt 2>/dev/null | head -10 || warn "No results yet."
  echo ""
  read -rp "Open a result file? Enter number (or 0 to skip): " n
  if [[ "$n" -gt 0 ]]; then
    local f; f="$(ls -1t "$RESULTS_DIR"/*.txt | sed -n "${n}p")"
    [[ -f "$f" ]] && less "$f" || warn "File not found."
  fi
}

menu_clean() {
  header "Cleaning Test Artifacts"
  find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
  find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true
  rm -rf "$SCRIPT_DIR/htmlcov" "$SCRIPT_DIR/.coverage" 2>/dev/null || true
  success "Cleaned"
}

menu_help() {
  header "Help"
  cat <<EOF
  MCADV Test Menu – keyboard shortcuts:
    1  Quick Test        Run smoke tests (fast)
    2  All Tests         Full test suite
    3  Category          Choose a specific test category
    4  Coverage          Run with coverage report
    5  Lint              Run flake8 linter
    6  Integration       Run integration tests
    7  Performance       Run performance benchmarks
    8  View Results      Browse saved result files
    9  HTML Report       Generate htmlcov/ report
    c  Clean             Remove __pycache__ and coverage files
    r  Compare Runs      Diff last two result files
    h  Help              Show this message
    q  Quit

  Flags: --verbose / --quiet can be passed on the command line.
EOF
}

# ---------------------------------------------------------------------------
# Main menu loop
# ---------------------------------------------------------------------------
main() {
  detect_venv
  clear

  while true; do
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${BLUE}║   MCADV Interactive Test Menu        ║${RESET}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════╝${RESET}"
    echo ""
    echo "  1) Quick Test"
    echo "  2) All Tests"
    echo "  3) Specific Category"
    echo "  4) Coverage"
    echo "  5) Lint"
    echo "  6) Integration Tests"
    echo "  7) Performance"
    echo "  8) View Results"
    echo "  9) HTML Report"
    echo "  c) Clean"
    echo "  r) Compare Last Two Runs"
    echo "  h) Help"
    echo "  q) Quit"
    echo ""
    read -rp "Choice: " choice

    case "$choice" in
      1) menu_quick ;;
      2) menu_all ;;
      3) menu_category ;;
      4) menu_coverage ;;
      5) menu_lint ;;
      6) run_pytest "integration" tests/test_integration.py ;;
      7) run_pytest "performance" tests/test_performance.py ;;
      8) menu_view_results ;;
      9) menu_html_report ;;
      c|C) menu_clean ;;
      r|R) compare_runs ;;
      h|H) menu_help ;;
      q|Q) print_summary; echo ""; info "Goodbye!"; exit 0 ;;
      p) preflight ;;
      *) warn "Unknown option: $choice" ;;
    esac
  done
}

main "$@"

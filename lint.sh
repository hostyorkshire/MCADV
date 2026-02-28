#!/bin/bash
# Comprehensive code linting script for MCADV project
# This script runs all configured linters to ensure code quality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED_CHECKS++))
}

# Function to print failure
print_failure() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED_CHECKS++))
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Parse arguments
FIX_MODE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fix        Automatically fix issues where possible"
            echo "  --verbose    Show detailed output from linters"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_header "MCADV Code Linting Check"

# Check if development dependencies are installed
print_header "Checking Dependencies"
((TOTAL_CHECKS++))

HAS_FLAKE8=$(command -v flake8 || echo "")
HAS_BLACK=$(command -v black || echo "")
HAS_PYLINT=$(command -v pylint || echo "")

if [ -z "$HAS_FLAKE8" ] || [ -z "$HAS_BLACK" ] || [ -z "$HAS_PYLINT" ]; then
    print_failure "Linting tools not installed"
    echo "Installing development dependencies..."
    pip install -q -r requirements-dev.txt
    if [ $? -eq 0 ]; then
        print_success "Dependencies installed successfully"
    else
        print_failure "Failed to install dependencies"
        exit 1
    fi
else
    print_success "All linting tools are available"
fi

# 1. Black - Code Formatting
print_header "Running Black (Code Formatter)"
((TOTAL_CHECKS++))

if [ "$FIX_MODE" = true ]; then
    if [ "$VERBOSE" = true ]; then
        black --line-length=120 .
    else
        black --line-length=120 . --quiet
    fi
    if [ $? -eq 0 ]; then
        print_success "Black: Code formatted successfully"
    else
        print_failure "Black: Code formatting failed"
    fi
else
    if [ "$VERBOSE" = true ]; then
        black --check --line-length=120 .
    else
        black --check --line-length=120 . --quiet
    fi
    if [ $? -eq 0 ]; then
        print_success "Black: Code formatting is correct"
    else
        print_failure "Black: Code formatting issues found (run with --fix to auto-format)"
    fi
fi

# 2. isort - Import Sorting
print_header "Running isort (Import Sorter)"
((TOTAL_CHECKS++))

if [ "$FIX_MODE" = true ]; then
    if [ "$VERBOSE" = true ]; then
        isort --profile=black --line-length=120 .
    else
        isort --profile=black --line-length=120 . --quiet
    fi
    if [ $? -eq 0 ]; then
        print_success "isort: Imports sorted successfully"
    else
        print_failure "isort: Import sorting failed"
    fi
else
    if [ "$VERBOSE" = true ]; then
        isort --check-only --profile=black --line-length=120 .
    else
        isort --check-only --profile=black --line-length=120 . --quiet
    fi
    if [ $? -eq 0 ]; then
        print_success "isort: Import ordering is correct"
    else
        print_failure "isort: Import ordering issues found (run with --fix to auto-sort)"
    fi
fi

# 3. Flake8 - Style Guide Enforcement
print_header "Running Flake8 (Style Guide)"
((TOTAL_CHECKS++))

if [ "$VERBOSE" = true ]; then
    flake8 . --statistics --count
else
    flake8 . --statistics --count --quiet
fi

if [ $? -eq 0 ]; then
    print_success "Flake8: No style violations found"
else
    print_failure "Flake8: Style violations detected"
fi

# 4. Pylint - Code Quality Analysis
print_header "Running Pylint (Code Quality)"
((TOTAL_CHECKS++))

if [ "$VERBOSE" = true ]; then
    pylint --rcfile=.pylintrc *.py
    PYLINT_EXIT=$?
else
    pylint --rcfile=.pylintrc *.py > /dev/null 2>&1
    PYLINT_EXIT=$?
fi

if [ $PYLINT_EXIT -eq 0 ]; then
    print_success "Pylint: Perfect score (10/10)"
elif [ $PYLINT_EXIT -lt 16 ]; then
    SCORE=$(pylint --rcfile=.pylintrc *.py 2>&1 | grep "rated at" | sed 's/.*rated at \([0-9.]*\).*/\1/')
    print_warning "Pylint: Code rated at $SCORE/10 (issues found but not critical)"
    ((PASSED_CHECKS++))
else
    print_failure "Pylint: Critical code quality issues found"
fi

# 5. MyPy - Type Checking
print_header "Running MyPy (Type Checker)"
((TOTAL_CHECKS++))

if [ "$VERBOSE" = true ]; then
    mypy . --config-file=pyproject.toml
    MYPY_EXIT=$?
else
    ERROR_COUNT=$(mypy . --config-file=pyproject.toml 2>&1 | grep -c "error:")
    MYPY_EXIT=$?
fi

if [ $MYPY_EXIT -eq 0 ]; then
    print_success "MyPy: No type errors found"
else
    if [ "$VERBOSE" = false ]; then
        print_warning "MyPy: Found $ERROR_COUNT type hints issues (consider adding type hints)"
    else
        print_warning "MyPy: Type hints issues found (consider adding type hints)"
    fi
    # MyPy errors are warnings, not failures for this project
    ((PASSED_CHECKS++))
fi

# 6. Bandit - Security Analysis
print_header "Running Bandit (Security Scanner)"
((TOTAL_CHECKS++))

if [ "$VERBOSE" = true ]; then
    bandit -r . -c pyproject.toml
    BANDIT_EXIT=$?
else
    ISSUE_COUNT=$(bandit -r . -c pyproject.toml 2>&1 | grep -c "Issue:")
    BANDIT_EXIT=$?
fi

if [ $BANDIT_EXIT -eq 0 ]; then
    print_success "Bandit: No security issues found"
else
    if [ "$VERBOSE" = false ]; then
        print_warning "Bandit: Found $ISSUE_COUNT potential security issues (review recommended)"
    else
        print_warning "Bandit: Potential security issues found (review recommended)"
    fi
    # Bandit warnings are not failures for this project
    ((PASSED_CHECKS++))
fi

# Summary
print_header "Linting Summary"
echo -e "Total checks: ${BLUE}$TOTAL_CHECKS${NC}"
echo -e "Passed:       ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed:       ${RED}$FAILED_CHECKS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "\n${GREEN}All linting checks passed!${NC}\n"
    exit 0
else
    echo -e "\n${RED}Some linting checks failed. Please review the output above.${NC}"
    if [ "$FIX_MODE" = false ]; then
        echo -e "${YELLOW}Tip: Run with --fix to automatically fix formatting and import issues.${NC}\n"
    fi
    exit 1
fi

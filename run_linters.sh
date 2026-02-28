#!/bin/bash
# Simple linting script for MCADV project
# Runs all configured linters and reports results

echo "========================================"
echo "Running Code Linting Checks"
echo "========================================"
echo ""

# Track results
FAILED=0

# 1. Black - Code Formatting
echo "1. Running Black (code formatter)..."
if black --check --line-length=120 . --quiet; then
    echo "   ✓ Black: No formatting issues"
else
    echo "   ✗ Black: Formatting issues found (run 'black .' to fix)"
    FAILED=1
fi
echo ""

# 2. isort - Import Sorting  
echo "2. Running isort (import sorter)..."
if isort --check-only --profile=black --line-length=120 . --quiet; then
    echo "   ✓ isort: Import order is correct"
else
    echo "   ✗ isort: Import order issues found (run 'isort .' to fix)"
    FAILED=1
fi
echo ""

# 3. Flake8 - Style Guide
echo "3. Running Flake8 (style checker)..."
flake8 . --statistics --count > /tmp/flake8_output.txt 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Flake8: No style violations"
else
    echo "   ✗ Flake8: Style violations found"
    cat /tmp/flake8_output.txt
    FAILED=1
fi
echo ""

# 4. Pylint - Code Quality
echo "4. Running Pylint (code quality analyzer)..."
pylint --rcfile=.pylintrc *.py > /tmp/pylint_output.txt 2>&1
PYLINT_EXIT=$?
SCORE=$(grep "rated at" /tmp/pylint_output.txt | head -1 | sed 's/.*rated at \([0-9.]*\).*/\1/' || echo "0")
if [ $PYLINT_EXIT -eq 0 ]; then
    echo "   ✓ Pylint: Perfect score (10/10)"
elif [ "$SCORE" != "0" ]; then
    # Use bc for float comparison if available, otherwise string comparison
    if command -v bc >/dev/null 2>&1; then
        IS_PASSING=$(echo "$SCORE >= 9.0" | bc)
    else
        # Simple check: if score starts with 9 or 10, it's passing
        IS_PASSING=$(echo "$SCORE" | grep -E "^(9\.|10\.)" >/dev/null && echo "1" || echo "0")
    fi
    
    if [ "$IS_PASSING" = "1" ]; then
        echo "   ✓ Pylint: Code rated at $SCORE/10 (passing)"
    else
        echo "   ⚠ Pylint: Code rated at $SCORE/10 (consider improvements)"
    fi
else
    echo "   ✗ Pylint: Critical issues found"
    tail -20 /tmp/pylint_output.txt
    FAILED=1
fi
echo ""

# 5. MyPy - Type Checking
echo "5. Running MyPy (type checker)..."
mypy . --config-file=pyproject.toml > /tmp/mypy_output.txt 2>&1
MYPY_EXIT=$?
if [ $MYPY_EXIT -eq 0 ]; then
    echo "   ✓ MyPy: No type errors"
else
    ERROR_COUNT=$(grep -c "error:" /tmp/mypy_output.txt)
    echo "   ⚠ MyPy: Found $ERROR_COUNT type hint issues (not critical)"
fi
echo ""

# 6. Bandit - Security Scanner
echo "6. Running Bandit (security scanner)..."
bandit -r . -c pyproject.toml > /tmp/bandit_output.txt 2>&1
BANDIT_EXIT=$?
if [ $BANDIT_EXIT -eq 0 ]; then
    echo "   ✓ Bandit: No security issues"
else
    ISSUE_COUNT=$(grep -c "Issue:" /tmp/bandit_output.txt)
    echo "   ⚠ Bandit: Found $ISSUE_COUNT potential security issues (review recommended)"
fi
echo ""

# Summary
echo "========================================"
echo "Summary"
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo "✓ All critical linting checks passed!"
    exit 0
else
    echo "✗ Some linting checks failed. Please fix the issues above."
    echo ""
    echo "Quick fixes:"
    echo "  - Run 'black .' to auto-format code"
    echo "  - Run 'isort .' to auto-sort imports"
    exit 1
fi

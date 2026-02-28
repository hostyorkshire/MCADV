# Development Guide

## Setting Up Development Environment

### 1. Install Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

This will run automated checks before each commit.

### 2. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 3. Run Tests Locally

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_adventure_bot.py
```

### 4. Code Quality Checks

```bash
# Format code
black .
isort .

# Lint code
flake8 .
pylint *.py

# Type checking
mypy adventure_bot.py meshcore.py radio_gateway.py

# Security scanning
bandit -r .
```

## GitHub Actions

All tests and checks run automatically on:
- Every push to main/develop
- Every pull request
- Weekly security scans (Sundays)

## Dependabot

Dependabot automatically:
- Checks for dependency updates weekly (Mondays)
- Creates PRs for security vulnerabilities
- Updates GitHub Actions versions

## Code Coverage

Coverage reports are uploaded to Codecov automatically.
View detailed reports at: https://codecov.io/gh/hostyorkshire/MCADV

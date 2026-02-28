# Code Linting Guide

This document describes the code linting setup and how to use it for the MCADV project.

## Overview

The MCADV project uses multiple linting tools to ensure code quality, consistency, and security:

1. **Black** - Code formatter for consistent style
2. **isort** - Import sorter for organized imports
3. **Flake8** - PEP 8 style guide enforcement
4. **Pylint** - Comprehensive code quality analyzer
5. **MyPy** - Static type checker
6. **Bandit** - Security vulnerability scanner

## Quick Start

### Running All Linters

To run all linting checks at once:

```bash
./run_linters.sh
```

This will check your code against all configured linters and provide a summary report.

### Auto-fixing Issues

Some linters can automatically fix issues:

```bash
# Auto-format code with Black
black .

# Auto-sort imports with isort
isort .
```

## Individual Linters

### Black - Code Formatter

Black enforces a consistent code style across the project.

**Check formatting:**
```bash
black --check .
```

**Auto-format code:**
```bash
black .
```

**Configuration:** `pyproject.toml` (line length: 120)

### isort - Import Sorter

isort organizes imports according to PEP 8 guidelines.

**Check import order:**
```bash
isort --check-only .
```

**Auto-sort imports:**
```bash
isort .
```

**Configuration:** `pyproject.toml` (profile: black, line length: 120)

### Flake8 - Style Guide Checker

Flake8 checks code against PEP 8 style guide and finds common errors.

**Run checks:**
```bash
flake8 .
```

**Configuration:** `.flake8` file

### Pylint - Code Quality Analyzer

Pylint provides detailed code quality analysis and suggestions.

**Run analysis:**
```bash
pylint --rcfile=.pylintrc *.py
```

**Configuration:** `.pylintrc` file

**Current score:** 9.52/10 (excellent)

### MyPy - Type Checker

MyPy performs static type checking to catch type-related errors.

**Run type checks:**
```bash
mypy . --config-file=pyproject.toml
```

**Configuration:** `pyproject.toml`

### Bandit - Security Scanner

Bandit scans for common security vulnerabilities in Python code.

**Run security scan:**
```bash
bandit -r . -c pyproject.toml
```

**Configuration:** `pyproject.toml`

## Pre-commit Hooks

The project includes pre-commit hooks that automatically run linters before each commit.

**Install pre-commit hooks:**
```bash
pre-commit install
```

**Run hooks manually:**
```bash
pre-commit run --all-files
```

**Configuration:** `.pre-commit-config.yaml`

## CI/CD Integration

Linting checks should be integrated into your CI/CD pipeline to ensure all code meets quality standards before merging.

Example GitHub Actions workflow:

```yaml
- name: Install dependencies
  run: pip install -r requirements-dev.txt

- name: Run linters
  run: ./run_linters.sh
```

## Linting Standards

### Code Quality Targets

- **Flake8:** Zero violations (enforced)
- **Pylint:** Score ≥ 9.0/10 (current: 9.52/10)
- **Black:** All code must be formatted (enforced)
- **isort:** All imports must be sorted (enforced)
- **MyPy:** Type hints encouraged but not enforced
- **Bandit:** Review and address security issues

### Common Issues and Fixes

#### Black/isort formatting issues
**Solution:** Run `black .` and `isort .` to auto-fix

#### Flake8 line length violations
**Solution:** Break long lines or refactor code. Max line length is 120 characters.

#### Pylint warnings
**Solution:** Review suggestions and refactor code or suppress with inline comments if appropriate

#### MyPy type errors
**Solution:** Add type hints to function signatures and variables

#### Bandit security warnings
**Solution:** Review each warning and either fix the issue or document why it's safe

## IDE Integration

### VS Code

Install these extensions:
- Python (Microsoft)
- Pylance
- Black Formatter

Add to `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=120"],
  "editor.formatOnSave": true
}
```

### PyCharm

1. Go to Settings → Tools → Black
2. Enable "Run Black on save"
3. Go to Settings → Tools → External Tools
4. Add configurations for flake8, pylint, isort

## Troubleshooting

### Linters not found
**Solution:** Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Conflicting formatting
**Solution:** Run black and isort in order:
```bash
isort .
black .
```

### Pre-commit hooks failing
**Solution:** Run hooks manually to see errors:
```bash
pre-commit run --all-files
```

## Additional Resources

- [Black documentation](https://black.readthedocs.io/)
- [isort documentation](https://pycqa.github.io/isort/)
- [Flake8 documentation](https://flake8.pycqa.org/)
- [Pylint documentation](https://pylint.pycqa.org/)
- [MyPy documentation](https://mypy.readthedocs.io/)
- [Bandit documentation](https://bandit.readthedocs.io/)
- [Pre-commit documentation](https://pre-commit.com/)

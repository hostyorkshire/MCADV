# Contributing to MCADV

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/your-org/MCADV.git
cd MCADV
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov flake8
```

## Code Style

- Follow **PEP 8** with a max line length of **120 characters**
- Use type hints for function signatures
- Write docstrings for public classes and methods
- Run `flake8 .` before submitting – CI will fail on lint errors

## Testing Requirements

- All new features must include tests
- Maintain ≥ 80% code coverage on core modules
- Tests must not require hardware or a running server (mock everything)
- Run the full suite before submitting: `python -m pytest tests/ -v`

## Pull Request Process

1. Fork the repository and create a feature branch: `git checkout -b feature/my-feature`
2. Write tests for your change
3. Ensure all tests pass and linting is clean
4. Update relevant documentation in `docs/`
5. Open a pull request with a clear description of the change and why it is needed

## Commit Messages

Use the imperative mood in the subject line, e.g.:

```
Add rate limiting to InputValidator
Fix session expiry race condition
```

## Reporting Bugs

Open a GitHub issue with:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output (redact any sensitive data)

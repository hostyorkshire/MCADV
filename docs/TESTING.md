# Testing Guide

## Running Tests

### Quick run (all tests)

```bash
python -m pytest tests/ -v
```

### Interactive test menu

```bash
./run_tests_menu.sh
```

The menu provides options for:
- Quick smoke test
- Full test suite
- Tests by category
- Coverage report
- Linting
- HTML report

### Simple wrapper

```bash
./run_all_tests.sh
```

---

## Test Categories

| Category      | File                          | Description                              |
|---------------|-------------------------------|------------------------------------------|
| Unit          | `test_adventure_bot.py`       | AdventureBot core logic                  |
| MeshCore      | `test_meshcore.py`            | Message construction, constants          |
| Gateway       | `test_radio_gateway.py`       | HTTP forwarding, channel filtering       |
| Integration   | `test_integration.py`         | End-to-end flows, multi-user scenarios   |
| LLM           | `test_llm_integration.py`     | Ollama API, timeouts, fallbacks          |
| Security      | `test_security.py`            | Input validation, rate limiting, XSS     |
| Performance   | `test_performance.py`         | Throughput and latency benchmarks        |
| Utilities     | `test_utils.py`               | Test factory helpers                     |

---

## Running Specific Categories

```bash
# Unit tests only
python -m pytest tests/test_adventure_bot.py -v

# Security tests only
python -m pytest tests/test_security.py -v

# All except performance
python -m pytest tests/ -v --ignore=tests/test_performance.py
```

---

## Coverage

```bash
python -m pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

Coverage requirements: **80%** minimum for core modules.

---

## Writing New Tests

1. Create `tests/test_<module>.py`
2. Add the sys.path fix at the top:
   ```python
   import sys, os
   sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
   ```
3. Use fixtures from `conftest.py` (e.g., `bot`, `make_msg`, `temp_dir`)
4. Mock hardware and network with `unittest.mock`
5. Run your new tests: `python -m pytest tests/test_<module>.py -v`

---

## Dependencies

Install test dependencies:

```bash
pip install pytest pytest-cov flake8
```

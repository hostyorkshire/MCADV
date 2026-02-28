#!/usr/bin/env bash
# Run all tests with coverage report.
cd "$(dirname "$0")"
python -m pytest tests/ -v --tb=short "$@"

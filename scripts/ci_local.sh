#!/usr/bin/env bash
set -euo pipefail

echo "Running format (black)"
python -m black .

echo "Running import sort (isort)"
python -m isort .

echo "Running flake8"
python -m flake8 .

echo "Running bandit (baseline)"
bandit -x tests,docs -r . -f json -b bandit_baseline.json > /tmp/bandit.json || true
echo "Bandit completed (non-zero exit tolerated if only findings)"

echo "Running tests (fast) with coverage"
python run_tests.py --type fast --coverage

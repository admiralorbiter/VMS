#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

Write-Host "Running format (black)"
python -m black .

Write-Host "Running import sort (isort)"
python -m isort .

Write-Host "Running flake8"
python -m flake8 .

Write-Host "Running bandit (baseline)"
bandit -x tests,docs -r . -f json -b bandit_baseline.json | Out-Null
Write-Host "Bandit completed (non-zero exit tolerated if only findings)"

Write-Host "Running tests (fast) with coverage"
python .\run_tests.py --type fast --coverage

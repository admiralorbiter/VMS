#!/bin/bash
# Validation System CLI Wrapper for Unix/Linux/Mac
# Run this from the project root directory

if [ $# -eq 0 ]; then
    echo "Usage: ./run_validation.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  fast                    - Run fast validation"
    echo "  slow                    - Run slow validation"
    echo "  count [entity-type]     - Run count validation"
    echo "  status [run-id]         - Show validation run status"
    echo "  recent [limit]          - Show recent validation runs"
    echo "  results [run-id]        - Show validation run results"
    echo "  test                    - Run basic tests"
    echo "  help                    - Show detailed help"
    echo ""
    echo "Examples:"
    echo "  ./run_validation.sh fast"
    echo "  ./run_validation.sh count volunteer"
    echo "  ./run_validation.sh test"
    exit 1
fi

if [ "$1" = "test" ]; then
    python scripts/validation/test_validation_basic.py
elif [ "$1" = "help" ]; then
    python scripts/validation/run_validation.py --help
else
    python scripts/validation/run_validation.py "$@"
fi

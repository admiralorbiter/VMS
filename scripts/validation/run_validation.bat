@echo off
REM Validation System CLI Wrapper for Windows
REM Run this from the project root directory

if "%1"=="" (
    echo Usage: run_validation.bat [command] [options]
    echo.
    echo Commands:
    echo   fast                    - Run fast validation
    echo   slow                    - Run slow validation
    echo   count [entity-type]     - Run count validation
    echo   status [run-id]         - Show validation run status
    echo   recent [limit]          - Show recent validation runs
    echo   results [run-id]        - Show validation run results
    echo   test                    - Run basic tests
    echo   help                    - Show detailed help
    echo.
    echo Examples:
    echo   run_validation.bat fast
    echo   run_validation.bat count volunteer
    echo   run_validation.bat test
    exit /b 1
)

if "%1"=="test" (
    python scripts\validation\test_validation_basic.py
) else if "%1"=="help" (
    python scripts\validation\run_validation.py --help
) else (
    python scripts\validation\run_validation.py %*
)

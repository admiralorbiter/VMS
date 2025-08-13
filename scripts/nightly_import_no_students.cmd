@echo off
REM Nightly import (exclude students) for Windows Task Scheduler
setlocal enabledelayedexpansion

REM Optional: set VENV_PATH to your venv Scripts dir
REM set VENV_PATH=C:\path\to\venv\Scripts

set REPO_ROOT=%~dp0\..
pushd %REPO_ROOT%

IF NOT "%VENV_PATH%"=="" (
  call "%VENV_PATH%\activate.bat"
)

IF "%VMS_BASE_URL%"=="" (
  set VMS_BASE_URL=http://localhost:5050
)

python manage_imports.py --sequential --exclude students --timeout 0 --base-url %VMS_BASE_URL%

popd
endlocal

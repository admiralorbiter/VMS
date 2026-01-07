#!/usr/bin/env bash
set -euo pipefail

# Nightly import (exclude students) wrapper for cron/PythonAnywhere
#
# Env vars read by manage_imports.py:
#   - ADMIN_USERNAME, ADMIN_PASSWORD (recommended)
#   - VMS_BASE_URL (defaults to http://localhost:5050 if not set)
#   - IMPORT_LOG_FILE (optional)
# Optional: set VENV_PATH to activate a virtualenv before running

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
cd "${REPO_ROOT}"

if [[ -n "${VENV_PATH:-}" && -d "${VENV_PATH}" ]]; then
  # shellcheck disable=SC1090
  source "${VENV_PATH}/bin/activate"
fi

: "${VMS_BASE_URL:=${VMS_BASE_URL:-https://yourusername.pythonanywhere.com}}"

python scripts/cli/manage_imports.py \
  --sequential \
  --exclude students \
  --timeout 0 \
  --base-url "${VMS_BASE_URL}"

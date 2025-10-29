#!/usr/bin/env python3
"""
Manage Imports CLI
==================

One-click sequential importer that triggers existing web import endpoints.

Features:
- Session login using the regular /login form (CSRF-aware)
- Sequential import execution mirroring Admin UI order
- --only flag to run a specific step or a comma-separated subset
- --exclude flag to skip specific steps when running sequentially
- --plan-only to print the plan and exit without making any changes
- --students-max-chunks to stop the student import after N chunks (fast testing)
- Structured logging to file and console
- Clear exit codes
 - --fail-fast to stop the run at the first failed step

Usage examples:
    # Full run
    python scripts/cli/manage_imports.py --sequential \
        --base-url http://localhost:5050 \
        --username admin --password admin123

    # Targeted run for teachers only
    python scripts/cli/manage_imports.py --only teachers \
        --base-url http://localhost:5050 \
        --username admin --password admin123

    # Full run but skip heavy steps (schools, classes, students)
    python scripts/cli/manage_imports.py --sequential --exclude schools,classes,students \
        --base-url http://localhost:5050 \
        --username admin --password admin123

    # Fast test: run only students for a single chunk
    python scripts/cli/manage_imports.py --only students --students-max-chunks 1 \
        --base-url http://localhost:5050 \
        --username admin --password admin123

Environment variables:
    ADMIN_USERNAME, ADMIN_PASSWORD  (used if flags not provided)

Notes:
- The script requires the Flask app to be running and reachable at --base-url.
- Students import runs in chunks until completion unless --students-max-chunks is set.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    import requests
except Exception as exc:  # pragma: no cover
    print(
        "Error: The 'requests' package is required. Please install it with 'pip install requests'."
    )
    raise

# Optional .env loading for convenience when running as a standalone script
try:  # pragma: no cover
    from dotenv import find_dotenv, load_dotenv

    # Load a default .env if present (does not override existing env)
    _default_env = find_dotenv()
    if _default_env:
        load_dotenv(_default_env, override=False)
except Exception:  # pragma: no cover
    load_dotenv = None


LOGIN_PATH = "/login"


@dataclass
class ImportStep:
    name: str
    route: str
    chunked: bool = False
    requires_json_body: bool = False


SEQUENCE: List[ImportStep] = [
    ImportStep("organizations", "/organizations/import-from-salesforce"),
    ImportStep("schools", "/management/import-schools"),
    ImportStep("classes", "/management/import-classes"),
    ImportStep("teachers", "/teachers/import-from-salesforce"),
    ImportStep(
        "students",
        "/students/import-from-salesforce",
        chunked=True,
        requires_json_body=True,
    ),
    ImportStep("volunteers", "/volunteers/import-from-salesforce"),
    ImportStep("affiliations", "/organizations/import-affiliations-from-salesforce"),
    ImportStep("events", "/events/import-from-salesforce"),
    ImportStep("history", "/history/import-from-salesforce"),
    # Sync unaffiliated events
    ImportStep("pathway_events_sync", "/pathway-events/sync-unaffiliated-events"),
]


def setup_logger(log_file: Optional[str]) -> logging.Logger:
    logger = logging.getLogger("manage_imports")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sequential Salesforce import runner")
    parser.add_argument(
        "--base-url", default=os.environ.get("VMS_BASE_URL", "http://localhost:5050")
    )
    parser.add_argument("--username", default=os.environ.get("ADMIN_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    parser.add_argument(
        "--env-file",
        help="Optional path to a .env file to load before parsing env vars",
    )
    parser.add_argument(
        "--sequential", action="store_true", help="Run all steps in order"
    )
    parser.add_argument(
        "--only",
        help=(
            "Run only specific steps (comma-separated names). Available: "
            + ", ".join(step.name for step in SEQUENCE)
        ),
    )
    parser.add_argument(
        "--exclude",
        help=(
            "Skip specific steps when running sequentially (comma-separated names). Available: "
            + ", ".join(step.name for step in SEQUENCE)
        ),
    )
    parser.add_argument(
        "--log-file", default=os.environ.get("IMPORT_LOG_FILE", "logs/import.log")
    )
    parser.add_argument("--students-chunk-size", type=int, default=2000)
    parser.add_argument("--students-sleep-ms", type=int, default=200)
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for each request. Use 0 or negative for no timeout (wait indefinitely).",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=None,
        help="Optional connect timeout override (seconds). If provided with --read-timeout, overrides --timeout.",
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=None,
        help="Optional read timeout override (seconds). If provided with --connect-timeout, overrides --timeout.",
    )
    parser.add_argument(
        "--students-max-chunks",
        type=int,
        default=None,
        help="For testing: stop student import after N chunks; omit for full import",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Print the resolved plan (steps to execute) and exit without performing any imports",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first failed step (default is to continue and report all results)",
    )
    return parser.parse_args()


def fetch_csrf_token(
    session: requests.Session, base_url: str
) -> Tuple[str, Dict[str, str]]:
    resp = session.get(f"{base_url}{LOGIN_PATH}", timeout=30)
    resp.raise_for_status()

    # Extract CSRF token from form
    match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"', resp.text, re.IGNORECASE
    )
    if not match:
        raise RuntimeError("Could not find CSRF token on login page")
    csrf_token = match.group(1)
    return csrf_token, dict(resp.cookies)


def login(
    session: requests.Session,
    base_url: str,
    username: str,
    password: str,
    logger: logging.Logger,
) -> None:
    csrf_token, _cookies = fetch_csrf_token(session, base_url)
    payload = {
        "username": username,
        "password": password,
        "csrf_token": csrf_token,
        "submit": "Login",
    }
    resp = session.post(
        f"{base_url}{LOGIN_PATH}", data=payload, timeout=30, allow_redirects=True
    )
    if resp.status_code not in (200, 302):
        raise RuntimeError(f"Login failed with status {resp.status_code}")

    # Heuristic: after successful login we should not be on the login page
    if resp.url.endswith(LOGIN_PATH) and "Invalid username" in resp.text:
        raise RuntimeError("Login failed: invalid credentials")
    logger.info("Authenticated successfully")


def run_step(
    session: requests.Session,
    base_url: str,
    step: ImportStep,
    logger: logging.Logger,
    students_chunk_size: int,
    students_sleep_ms: int,
    timeout: int,
    connect_timeout: Optional[float] = None,
    read_timeout: Optional[float] = None,
    students_max_chunks: Optional[int] = None,
) -> bool:
    url = f"{base_url}{step.route}"
    # Determine timeout value for requests
    if connect_timeout is not None and read_timeout is not None:
        timeout_value = (connect_timeout, read_timeout)
    else:
        timeout_value = None if timeout is not None and timeout <= 0 else timeout
    if step.chunked:
        # Students import runs in chunks until completion
        last_id: Optional[str] = None
        total_processed = 0
        chunk_index = 0
        while True:
            body = {"chunk_size": students_chunk_size}
            if last_id:
                body["last_id"] = last_id
            logger.info(
                json.dumps({"step": step.name, "action": "chunk", "payload": body})
            )
            resp = session.post(url, json=body, timeout=timeout_value)
            if resp.status_code != 200:
                logger.error(
                    f"{step.name}: HTTP {resp.status_code} - {resp.text[:200]}..."
                )
                return False
            try:
                data = resp.json()
            except Exception:
                logger.error(f"{step.name}: Non-JSON response: {resp.text[:200]}...")
                return False

            if data.get("status") == "error":
                logger.error(
                    json.dumps(
                        {
                            "step": step.name,
                            "error": data.get("message"),
                            "errors": data.get("errors", []),
                        }
                    )
                )
                return False

            total_processed += int(data.get("processed_count", 0))
            last_id = data.get("next_id")
            logger.info(
                json.dumps(
                    {
                        "step": step.name,
                        "chunk_result": {
                            "processed": data.get("processed_count"),
                            "next_id": last_id,
                            "is_complete": data.get("is_complete"),
                        },
                    }
                )
            )

            chunk_index += 1
            if students_max_chunks is not None and chunk_index >= students_max_chunks:
                logger.info(
                    json.dumps(
                        {
                            "step": step.name,
                            "status": "stopped_early",
                            "reason": f"Reached students-max-chunks={students_max_chunks}",
                            "total_processed": total_processed,
                            "next_id": last_id,
                        }
                    )
                )
                # Treat as success for testing purposes
                return True

            if data.get("is_complete") or not last_id:
                logger.info(
                    json.dumps(
                        {
                            "step": step.name,
                            "status": "complete",
                            "total_processed": total_processed,
                        }
                    )
                )
                return True

            # Gentle pacing between chunk requests
            time.sleep(max(0, students_sleep_ms) / 1000.0)

    # Non-chunked endpoints: simple POST
    logger.info(json.dumps({"step": step.name, "action": "post", "url": url}))
    resp = session.post(url, timeout=timeout_value)
    if resp.status_code != 200:
        logger.error(f"{step.name}: HTTP {resp.status_code} - {resp.text[:200]}...")
        return False
    try:
        data = resp.json()
        if not data.get("success", True):
            logger.error(json.dumps({"step": step.name, "error": data}))
            return False
    except Exception:
        # Some endpoints may return HTML; treat 200 as success
        pass
    logger.info(json.dumps({"step": step.name, "status": "ok"}))
    return True


def main() -> int:
    args = parse_args()
    logger = setup_logger(args.log_file)

    # Load an explicit env file if provided, then re-resolve username/password defaults if needed
    if args.env_file:
        if load_dotenv is None:
            logger.warning("python-dotenv not available; --env-file ignored")
        else:
            if not os.path.exists(args.env_file):
                logger.error("Specified --env-file not found: %s", args.env_file)
                return 2
            load_dotenv(args.env_file, override=False)
            # Re-fill from env if flags were not provided
            if not args.username:
                args.username = os.environ.get("ADMIN_USERNAME")
            if not args.password:
                args.password = os.environ.get("ADMIN_PASSWORD")

    if not args.username or not args.password:
        logger.error(
            "Username and password are required. Provide --username/--password or set ADMIN_USERNAME/ADMIN_PASSWORD."
        )
        return 2

    # Build list of steps to run
    if args.only:
        only_set = {s.strip().lower() for s in args.only.split(",") if s.strip()}
        steps = [s for s in SEQUENCE if s.name in only_set]
        if not steps:
            logger.error(
                "--only specified but no matching steps. Available: %s",
                ", ".join(step.name for step in SEQUENCE),
            )
            return 2
    elif args.sequential:
        steps = SEQUENCE
    else:
        logger.error("Specify --sequential or --only.")
        return 2

    # Apply exclude filter if provided
    if args.exclude:
        exclude_set = {s.strip().lower() for s in args.exclude.split(",") if s.strip()}
        steps = [s for s in steps if s.name not in exclude_set]
        if not steps:
            logger.error("All steps were excluded. Nothing to do.")
            return 2

    # If plan-only, print the intended plan and exit
    if args.plan_only:
        plan = {
            "base_url": args.base_url,
            "steps": [s.name for s in steps],
            "students_chunk_size": args.students_chunk_size,
            "students_max_chunks": args.students_max_chunks,
        }
        logger.info("%s", json.dumps({"plan_only": plan}))
        return 0

    session = requests.Session()
    try:
        login(session, args.base_url, args.username, args.password, logger)
    except Exception as exc:
        logger.error(f"Login failed: {exc}")
        return 2

    overall_ok = True
    for step in steps:
        logger.info("=== Running step: %s ===", step.name)
        ok = run_step(
            session,
            args.base_url,
            step,
            logger,
            students_chunk_size=args.students_chunk_size,
            students_sleep_ms=args.students_sleep_ms,
            timeout=args.timeout,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
            students_max_chunks=(
                args.students_max_chunks if step.name == "students" else None
            ),
        )
        if not ok:
            overall_ok = False
            logger.error("Step failed: %s", step.name)
            if args.fail_fast:
                logger.error("Fail-fast enabled, aborting subsequent steps")
                break
            # Continue to next step for resiliency; rerun with --only to retry

    return 0 if overall_ok else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

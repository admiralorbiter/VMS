"""
Salesforce Client Helper
========================

Centralized Salesforce connection management with retry logic and connection pooling.
This module provides a single source of truth for Salesforce API connections.

Usage:
    from services.salesforce_client import get_salesforce_client, safe_query_all

    # Get a client
    sf = get_salesforce_client()

    # Query with automatic retry
    results = safe_query_all(sf, "SELECT Id FROM Account")
"""

import time
from functools import wraps

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from config import Config

# Connection cache for reuse within a request context
_sf_client_cache = {}


def get_salesforce_client(force_new: bool = False) -> Salesforce:
    """
    Get an authenticated Salesforce client.

    Uses cached connection if available to avoid repeated auth.
    Set force_new=True to create a fresh connection.

    Args:
        force_new: If True, creates a new connection even if cached exists

    Returns:
        Authenticated Salesforce client

    Raises:
        SalesforceAuthenticationFailed: If credentials are invalid
    """
    cache_key = "default"

    if not force_new and cache_key in _sf_client_cache:
        return _sf_client_cache[cache_key]

    sf = Salesforce(
        username=Config.SF_USERNAME,
        password=Config.SF_PASSWORD,
        security_token=Config.SF_SECURITY_TOKEN,
        domain="login",
    )

    _sf_client_cache[cache_key] = sf
    return sf


def clear_client_cache():
    """Clear the Salesforce client cache. Used for testing or credential rotation."""
    global _sf_client_cache
    _sf_client_cache = {}


def retry_on_failure(
    max_attempts: int = 3, initial_delay: float = 1.0, backoff: float = 2.0
):
    """
    Decorator that retries a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 1.0)
        backoff: Multiplier for delay after each retry (default: 2.0)

    Retries on:
        - Connection errors
        - Timeout errors
        - Salesforce API errors (except authentication)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except SalesforceAuthenticationFailed:
                    # Don't retry auth failures - credentials are wrong
                    raise
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        print(
                            f"Salesforce API error (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        print(
                            f"Salesforce API error after {max_attempts} attempts: {e}"
                        )
                        raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


@retry_on_failure(max_attempts=3, initial_delay=1.0, backoff=2.0)
def safe_query_all(sf: Salesforce, query: str) -> dict:
    """
    Execute a Salesforce SOQL query with automatic retry.

    Args:
        sf: Authenticated Salesforce client
        query: SOQL query string

    Returns:
        Query result dictionary with 'records' key

    Raises:
        Exception: After max retries if still failing
    """
    return sf.query_all(query)


@retry_on_failure(max_attempts=3, initial_delay=1.0, backoff=2.0)
def safe_query(sf: Salesforce, query: str) -> dict:
    """
    Execute a Salesforce SOQL query (non-bulk) with automatic retry.

    Args:
        sf: Authenticated Salesforce client
        query: SOQL query string

    Returns:
        Query result dictionary
    """
    return sf.query(query)


# Import dependency definitions
IMPORT_DEPENDENCIES = {
    "volunteers": ["organizations"],
    "affiliations": ["organizations", "volunteers"],
    "events": ["organizations", "schools", "teachers"],
    "history": ["events", "volunteers", "students"],
    "teachers": ["schools"],
    "students": ["schools", "classes", "teachers"],
    "classes": ["schools"],
    "student_participations": ["events", "students"],
}


def check_import_dependencies(import_type: str) -> dict:
    """
    Check if dependencies for an import type have been synced.

    Args:
        import_type: The type of import to check (e.g., 'events', 'students')

    Returns:
        Dictionary with:
            - 'satisfied': Boolean indicating if all deps are met
            - 'missing': List of dependency types that haven't been synced
            - 'warnings': List of deps that were synced but are stale (>24h)
    """
    from datetime import datetime, timedelta, timezone

    from models.sync_log import SyncLog

    deps = IMPORT_DEPENDENCIES.get(import_type, [])
    if not deps:
        return {"satisfied": True, "missing": [], "warnings": []}

    missing = []
    warnings = []
    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

    for dep in deps:
        last_sync = (
            SyncLog.query.filter_by(sync_type=dep)
            .order_by(SyncLog.completed_at.desc())
            .first()
        )

        if not last_sync:
            missing.append(dep)
        elif last_sync.completed_at and last_sync.completed_at < stale_threshold:
            warnings.append(
                f"{dep} was last synced {last_sync.completed_at.strftime('%Y-%m-%d %H:%M')}"
            )

    return {
        "satisfied": len(missing) == 0,
        "missing": missing,
        "warnings": warnings,
    }

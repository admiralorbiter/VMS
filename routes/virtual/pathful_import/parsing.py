"""
Parsing utilities and constants for Pathful imports.

Provides date/name parsing, type coercion helpers, column definitions,
and the admin_or_tenant_required decorator.
"""

from datetime import datetime
from functools import wraps

import pandas as pd
from flask import current_app, flash, redirect, url_for
from flask_login import current_user

from models.user import TenantRole
from services.scoping import is_staff_user, is_tenant_user

# Constants
REQUIRED_SESSION_COLUMNS = [
    "Session ID",
    "Title",
    "Date",
    "Status",
    "SignUp Role",
    "Name",
]

OPTIONAL_SESSION_COLUMNS = [
    "Duration",
    "User Auth Id",
    "School",
    "District or Company",
    "Partner",
    "Registered Student Count",
    "Attended Student Count",
    "Career Cluster",
    "Work Based Learning",
    "Series or Event Title",
    "State",
]

EXPECTED_COLUMNS = REQUIRED_SESSION_COLUMNS + OPTIONAL_SESSION_COLUMNS

PARTNER_FILTER = "PREP-KC"  # Only import rows with this partner


def admin_or_tenant_required(f):
    """
    Decorator to allow access for admins OR tenant admins/coordinators.

    Phase D-3: District Admin Access (DEC-009)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        # Allow staff/admin users
        if is_staff_user(current_user):
            return f(*args, **kwargs)

        # Allow tenant admin/coordinator
        if is_tenant_user(current_user):
            if current_user.tenant_role in [
                TenantRole.ADMIN,
                TenantRole.COORDINATOR,
                TenantRole.VIRTUAL_ADMIN,
            ]:
                return f(*args, **kwargs)

        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("index"))

    return decorated_function


def parse_pathful_date(date_value):
    """
    Parse date from Pathful export.

    Handles formats like:
    - '2018-05-17 00:00:00'
    - '2018-05-17'
    - datetime objects

    Args:
        date_value: Date value from Pathful export

    Returns:
        datetime or None
    """
    if pd.isna(date_value) or date_value is None:
        return None

    # Handle pandas Timestamp
    if hasattr(date_value, "to_pydatetime"):
        try:
            return date_value.to_pydatetime()
        except Exception:
            return None

    if isinstance(date_value, datetime):
        return date_value

    date_str = str(date_value).strip()

    # Handle NaT (Not a Time) string representation
    if date_str.lower() in ("nat", "nan", "none", ""):
        return None

    formats_to_try = [
        "%Y-%m-%d %H:%M:%S",  # 2018-05-17 00:00:00
        "%Y-%m-%d",  # 2018-05-17
        "%m/%d/%Y %H:%M:%S",  # 05/17/2018 00:00:00
        "%m/%d/%Y",  # 05/17/2018
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    current_app.logger.warning(f"Could not parse date: {date_value}")
    return None


def parse_name(full_name):
    """
    Parse full name into first and last name components.

    Handles common name patterns and prefixes (Dr., Mr., Mrs., etc.)

    Args:
        full_name: Full name string

    Returns:
        tuple: (first_name, last_name)
    """
    if not full_name or pd.isna(full_name):
        return "", ""

    name = str(full_name).strip()

    # Remove common prefixes
    prefixes = [
        "dr.",
        "dr ",
        "mr.",
        "mr ",
        "mrs.",
        "mrs ",
        "ms.",
        "ms ",
        "prof.",
        "prof ",
    ]
    name_lower = name.lower()
    for prefix in prefixes:
        if name_lower.startswith(prefix):
            name = name[len(prefix) :].strip()
            break

    parts = name.split()

    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return "", parts[0]  # Single name becomes last name
    else:
        first_name = " ".join(parts[:-1])
        last_name = parts[-1]
        return first_name, last_name


def safe_int(value, default=0):
    """Safely convert a value to int, handling NaN and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_str(value):
    """Safely convert a value to string, handling NaN and None."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def serialize_row_for_json(row):
    """
    Convert a pandas DataFrame row to a JSON-serializable dict.

    Handles pandas Timestamp, NaT, and other non-serializable types.

    Args:
        row: DataFrame row (Series or dict-like)

    Returns:
        dict: JSON-serializable dictionary
    """
    data = row.to_dict() if hasattr(row, "to_dict") else dict(row)

    result = {}
    for key, value in data.items():
        # Handle NaN/NaT/None
        if pd.isna(value) or value is None:
            result[key] = None
        # Handle pandas Timestamp
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        # Handle numpy types
        elif hasattr(value, "item"):
            result[key] = value.item()
        else:
            # Try to convert to string if not a basic type
            if not isinstance(value, (str, int, float, bool, list, dict)):
                result[key] = str(value)
            else:
                result[key] = value

    return result


def validate_session_report_columns(df):
    """
    Validate that required columns exist in the DataFrame.

    Args:
        df: pandas DataFrame

    Returns:
        tuple: (is_valid, missing_columns)
    """
    missing = []
    for col in REQUIRED_SESSION_COLUMNS:
        if col not in df.columns:
            missing.append(col)

    return len(missing) == 0, missing

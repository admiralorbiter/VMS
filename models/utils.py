from datetime import datetime, UTC

def get_utc_now():
    """Centralized UTC datetime generator"""
    return datetime.now(UTC) 
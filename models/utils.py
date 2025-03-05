from datetime import datetime, timezone

def get_utc_now():
    """Get current UTC datetime"""
    return datetime.now(timezone.utc) 
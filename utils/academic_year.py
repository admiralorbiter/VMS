"""
Utility functions for academic year calculations
"""

from datetime import datetime, timezone


def get_current_academic_year():
    """
    Get the current academic year in YYYY-YYYY format
    Academic year runs from July 1st to June 30th
    """
    today = datetime.now(timezone.utc)
    month = today.month
    year = today.year

    if month >= 7:  # July or later
        return f"{year}-{year+1}"
    else:  # January to June
        return f"{year-1}-{year}"


def get_academic_year_for_date(date):
    """
    Get the academic year for a specific date
    """
    month = date.month
    year = date.year

    if month >= 7:  # July or later
        return f"{year}-{year+1}"
    else:  # January to June
        return f"{year-1}-{year}"


def parse_academic_year(academic_year_str):
    """
    Parse academic year string and return start/end years
    Returns tuple of (start_year, end_year)
    """
    if not academic_year_str or "-" not in academic_year_str:
        raise ValueError("Invalid academic year format. Expected YYYY-YYYY")

    try:
        start_year, end_year = academic_year_str.split("-")
        return int(start_year), int(end_year)
    except ValueError:
        raise ValueError("Invalid academic year format. Expected YYYY-YYYY")


def validate_academic_year(academic_year_str):
    """
    Validate academic year format
    Returns True if valid, False otherwise
    """
    try:
        start_year, end_year = parse_academic_year(academic_year_str)
        return end_year == start_year + 1
    except (ValueError, TypeError):
        return False


def get_academic_year_range(start_year=2018, end_year=2032):
    """
    Generate a list of academic years from start to end (exclusive of end_year)
    """
    academic_years = []
    for year in range(start_year, end_year):
        academic_years.append(f"{year}-{year+1}")
    return academic_years

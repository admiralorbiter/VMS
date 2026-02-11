"""
Academic Year Service
=====================

Shared utilities for academic year, semester, and date range calculations.
Used by both virtual usage routes and tenant teacher usage routes.
"""

from datetime import datetime


def get_current_academic_year() -> str:
    """
    Get the current academic year string based on today's date.

    Academic year runs from August 1 to July 31.

    Returns:
        str: Academic year in format "YYYY-YYYY" (e.g., "2025-2026")
    """
    today = datetime.now()
    if today.month >= 8:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"


def get_current_semester() -> str:
    """
    Get the current semester based on today's date.

    - Fall semester: August - December
    - Spring semester: January - July

    Returns:
        str: Either "fall" or "spring"
    """
    today = datetime.now()
    if today.month >= 8:
        return "fall"
    return "spring"


def get_academic_year_dates(academic_year: str) -> tuple[datetime, datetime]:
    """
    Calculate the start and end dates for a given academic year.

    Args:
        academic_year: The academic year string (e.g., "2025-2026")

    Returns:
        tuple: (start_date, end_date) where start is Aug 1 and end is Jul 31
    """
    try:
        start_year = int(academic_year.split("-")[0])
    except (ValueError, IndexError):
        start_year = datetime.now().year

    date_from = datetime(start_year, 8, 1)
    date_to = datetime(start_year + 1, 7, 31, 23, 59, 59)

    return date_from, date_to


def get_semester_dates(academic_year: str, semester: str) -> tuple[datetime, datetime]:
    """
    Calculate start and end dates for a specific semester.

    Args:
        academic_year: The academic year string (e.g., "2025-2026")
        semester: Either "fall" or "spring"

    Returns:
        tuple: (start_date, end_date) for the semester

    Note:
        - Fall Semester: August 1 - December 31
        - Spring Semester: January 1 - July 31
    """
    try:
        start_year = int(academic_year.split("-")[0])
    except (ValueError, IndexError):
        start_year = datetime.now().year

    if semester == "fall":
        date_from = datetime(start_year, 8, 1)
        date_to = datetime(start_year, 12, 31, 23, 59, 59)
    else:  # spring
        date_from = datetime(start_year + 1, 1, 1)
        date_to = datetime(start_year + 1, 7, 31, 23, 59, 59)

    return date_from, date_to


def generate_academic_year_options(
    start_year: int = 2018, end_year: int = None
) -> list[str]:
    """
    Generate a list of academic year strings for dropdowns.

    Args:
        start_year: First calendar year to include
        end_year: Last calendar year to include (defaults to current + 1)

    Returns:
        list: Academic year strings in descending order
    """
    if end_year is None:
        end_year = datetime.now().year + 1

    years = []
    for year in range(end_year, start_year - 1, -1):
        years.append(f"{year}-{year + 1}")

    return years

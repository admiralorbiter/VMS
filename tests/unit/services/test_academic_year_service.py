"""
Unit tests for services/academic_year_service.py

All functions are pure (no DB, no Flask context), so these are true unit tests.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from services.academic_year_service import (
    generate_academic_year_options,
    get_academic_year_dates,
    get_current_academic_year,
    get_current_semester,
    get_school_year_dates,
    get_semester_dates,
)

# ── get_current_academic_year ─────────────────────────────────────────


class TestGetCurrentAcademicYear:
    """Academic year runs Aug 1 – Jul 31."""

    def test_fall_semester_returns_current_dash_next(self):
        """Oct 15 2025 → '2025-2026'"""
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 10, 15)
            assert get_current_academic_year() == "2025-2026"

    def test_august_1_is_start_of_new_year(self):
        """Aug 1 2025 → '2025-2026'"""
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 8, 1)
            assert get_current_academic_year() == "2025-2026"

    def test_spring_semester_returns_previous_dash_current(self):
        """Mar 10 2026 → '2025-2026'"""
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 10)
            assert get_current_academic_year() == "2025-2026"

    def test_july_31_is_last_day_of_academic_year(self):
        """Jul 31 2026 → '2025-2026' (still spring)."""
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 31)
            assert get_current_academic_year() == "2025-2026"

    def test_january_1_is_spring(self):
        """Jan 1 2026 → '2025-2026'."""
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1)
            assert get_current_academic_year() == "2025-2026"

    def test_december_31_is_fall(self):
        """Dec 31 2025 → '2025-2026'."""
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 31)
            assert get_current_academic_year() == "2025-2026"


# ── get_current_semester ──────────────────────────────────────────────


class TestGetCurrentSemester:
    """Fall = Aug-Dec, Spring = Jan-Jul."""

    def test_october_is_fall(self):
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 10, 1)
            assert get_current_semester() == "fall"

    def test_august_is_fall(self):
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 8, 1)
            assert get_current_semester() == "fall"

    def test_march_is_spring(self):
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 15)
            assert get_current_semester() == "spring"

    def test_july_is_spring(self):
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 31)
            assert get_current_semester() == "spring"

    def test_january_is_spring(self):
        with patch("services.academic_year_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1)
            assert get_current_semester() == "spring"


# ── get_academic_year_dates ───────────────────────────────────────────


class TestGetAcademicYearDates:

    def test_normal_year(self):
        start, end = get_academic_year_dates("2025-2026")
        assert start == datetime(2025, 8, 1)
        assert end == datetime(2026, 7, 31, 23, 59, 59)

    def test_different_year(self):
        start, end = get_academic_year_dates("2023-2024")
        assert start == datetime(2023, 8, 1)
        assert end == datetime(2024, 7, 31, 23, 59, 59)

    def test_invalid_string_falls_back_to_current_year(self):
        """Invalid format → fallback to current year."""
        start, end = get_academic_year_dates("invalid")
        assert start.month == 8
        assert start.day == 1
        assert end.month == 7
        assert end.day == 31


# ── get_semester_dates ────────────────────────────────────────────────


class TestGetSemesterDates:

    def test_fall_semester(self):
        start, end = get_semester_dates("2025-2026", "fall")
        assert start == datetime(2025, 8, 1)
        assert end == datetime(2025, 12, 31, 23, 59, 59)

    def test_spring_semester(self):
        start, end = get_semester_dates("2025-2026", "spring")
        assert start == datetime(2026, 1, 1)
        assert end == datetime(2026, 7, 31, 23, 59, 59)

    def test_invalid_year_falls_back(self):
        start, end = get_semester_dates("bogus", "fall")
        # Should not crash; uses current year as fallback
        assert start.month == 8
        assert end.month == 12


# ── generate_academic_year_options ────────────────────────────────────


class TestGenerateAcademicYearOptions:

    def test_returns_descending_order(self):
        options = generate_academic_year_options(start_year=2022, end_year=2025)
        assert options[0] == "2025-2026"
        assert options[-1] == "2022-2023"

    def test_count_matches_range(self):
        options = generate_academic_year_options(start_year=2020, end_year=2024)
        assert len(options) == 5  # 2024, 2023, 2022, 2021, 2020

    def test_single_year(self):
        options = generate_academic_year_options(start_year=2025, end_year=2025)
        assert options == ["2025-2026"]


# ── get_school_year_dates ─────────────────────────────────────────────


class TestGetSchoolYearDates:
    """School year runs Jun 1 – May 31 (different from academic year!)."""

    def test_four_digit_years(self):
        start, end = get_school_year_dates("2024-2025")
        assert start == datetime(2024, 6, 1)
        assert end == datetime(2025, 5, 31)

    def test_two_digit_years(self):
        start, end = get_school_year_dates("24-25")
        assert start == datetime(2024, 6, 1)
        assert end == datetime(2025, 5, 31)

    def test_another_two_digit_range(self):
        start, end = get_school_year_dates("23-24")
        assert start == datetime(2023, 6, 1)
        assert end == datetime(2024, 5, 31)

    def test_invalid_format_returns_fallback(self):
        """Invalid input should not crash — should return a sensible fallback."""
        start, end = get_school_year_dates("invalid-input")
        # Should return some valid date range, not crash
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_empty_string_returns_fallback(self):
        """Empty string should not crash."""
        start, end = get_school_year_dates("")
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_single_number_returns_fallback(self):
        """Single number without dash should not crash."""
        start, end = get_school_year_dates("2025")
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

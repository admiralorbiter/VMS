"""
Unit tests for routes.reports.common utility functions.

Tests get_school_year_date_range and get_current_school_year to ensure
correct date parsing and edge case handling.
"""

from datetime import datetime

import pytest

from routes.reports.common import get_current_school_year, get_school_year_date_range


class TestGetSchoolYearDateRange:
    """Tests for get_school_year_date_range function."""

    def test_valid_school_year(self):
        """Test standard school year parsing: '2324' → Aug 2023 to Jul 2024."""
        start_date, end_date = get_school_year_date_range("2324")
        assert start_date == datetime(2023, 8, 1)
        assert end_date == datetime(2024, 7, 31)

    def test_valid_school_year_2526(self):
        """Test '2526' → Aug 2025 to Jul 2026."""
        start_date, end_date = get_school_year_date_range("2526")
        assert start_date == datetime(2025, 8, 1)
        assert end_date == datetime(2026, 7, 31)

    def test_valid_school_year_2021(self):
        """Test '2021' → Aug 2020 to Jul 2021."""
        start_date, end_date = get_school_year_date_range("2021")
        assert start_date == datetime(2020, 8, 1)
        assert end_date == datetime(2021, 7, 31)

    def test_all_time_raises_value_error(self):
        """Test that 'all_time' raises ValueError — callers must guard against this."""
        with pytest.raises(ValueError):
            get_school_year_date_range("all_time")

    def test_empty_string_raises_error(self):
        """Test that an empty string raises an error."""
        with pytest.raises((ValueError, IndexError)):
            get_school_year_date_range("")

    def test_non_numeric_raises_value_error(self):
        """Test that non-numeric strings raise ValueError."""
        with pytest.raises(ValueError):
            get_school_year_date_range("abcd")


class TestGetCurrentSchoolYear:
    """Tests for get_current_school_year function."""

    def test_returns_four_char_string(self):
        """Current school year should be a 4-character numeric string."""
        result = get_current_school_year()
        assert len(result) == 4
        assert result.isdigit()

    def test_year_is_parseable(self):
        """The returned value should be parseable by get_school_year_date_range."""
        school_year = get_current_school_year()
        start_date, end_date = get_school_year_date_range(school_year)
        assert start_date < end_date
        assert start_date.month == 8
        assert end_date.month == 7

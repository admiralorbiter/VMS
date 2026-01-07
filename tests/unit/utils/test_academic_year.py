"""
Unit tests for utils/academic_year.py academic year utility functions.
"""

from datetime import datetime, timezone

import pytest

from utils.academic_year import (
    get_academic_year_for_date,
    get_academic_year_range,
    get_current_academic_year,
    parse_academic_year,
    validate_academic_year,
)


class TestGetCurrentAcademicYear:
    """Test get_current_academic_year function."""

    def test_returns_valid_format(self):
        """Test that returned year is in YYYY-YYYY format."""
        result = get_current_academic_year()
        assert len(result) == 9
        assert result[4] == "-"
        assert result[:4].isdigit()
        assert result[5:].isdigit()

    def test_format_continuity(self):
        """Test that years are consecutive."""
        result = get_current_academic_year()
        start, end = result.split("-")
        assert int(end) == int(start) + 1


class TestGetAcademicYearForDate:
    """Test get_academic_year_for_date function."""

    def test_date_in_first_half_returns_previous_year(self):
        """Test dates Jan-Jun return previous academic year."""
        # January should be in previous year's academic year
        date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        result = get_academic_year_for_date(date)
        assert result == "2024-2025"

        # June should also be in previous year's academic year
        date = datetime(2025, 6, 30, tzinfo=timezone.utc)
        result = get_academic_year_for_date(date)
        assert result == "2024-2025"

    def test_date_in_second_half_returns_current_year(self):
        """Test dates Jul-Dec return current academic year."""
        # July starts new academic year
        date = datetime(2025, 7, 1, tzinfo=timezone.utc)
        result = get_academic_year_for_date(date)
        assert result == "2025-2026"

        # December should be in current academic year
        date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        result = get_academic_year_for_date(date)
        assert result == "2025-2026"

    def test_boundary_june_30(self):
        """Test boundary on June 30."""
        date = datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
        result = get_academic_year_for_date(date)
        assert result == "2024-2025"

    def test_boundary_july_1(self):
        """Test boundary on July 1."""
        date = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = get_academic_year_for_date(date)
        assert result == "2025-2026"


class TestParseAcademicYear:
    """Test parse_academic_year function."""

    def test_valid_format_returns_tuple(self):
        """Test that valid format returns tuple of ints."""
        start, end = parse_academic_year("2024-2025")
        assert start == 2024
        assert end == 2025
        assert isinstance(start, int)
        assert isinstance(end, int)

    def test_invalid_format_missing_dash_raises(self):
        """Test that format without dash raises ValueError."""
        with pytest.raises(ValueError, match="Invalid academic year format"):
            parse_academic_year("20242025")

    def test_invalid_format_extra_parts_raises(self):
        """Test that format with extra parts raises ValueError."""
        with pytest.raises(ValueError):
            parse_academic_year("2024-2025-2026")

    def test_invalid_format_non_digits_raises(self):
        """Test that format with non-digits raises ValueError."""
        with pytest.raises(ValueError):
            parse_academic_year("abcd-efgh")

    def test_empty_string_raises(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse_academic_year("")

    def test_none_raises(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError):
            parse_academic_year(None)


class TestValidateAcademicYear:
    """Test validate_academic_year function."""

    def test_valid_years_return_true(self):
        """Test that valid years return True."""
        assert validate_academic_year("2024-2025") is True
        assert validate_academic_year("2020-2021") is True

    def test_invalid_format_returns_false(self):
        """Test that invalid formats return False."""
        assert validate_academic_year("2024") is False
        assert validate_academic_year("2024-2024") is False  # Same year
        assert validate_academic_year("2024-2026") is False  # Gap too large
        assert validate_academic_year("abc-def") is False

    def test_off_by_one_errors_return_false(self):
        """Test that years where end != start+1 return False."""
        assert validate_academic_year("2024-2024") is False
        assert validate_academic_year("2024-2026") is False

    def test_non_string_handled_gracefully(self):
        """Test that non-string inputs return False without raising."""
        assert validate_academic_year(None) is False
        assert validate_academic_year(2024) is False
        assert validate_academic_year([]) is False


class TestGetAcademicYearRange:
    """Test get_academic_year_range function."""

    def test_default_range(self):
        """Test default range (2018-2032)."""
        years = get_academic_year_range()
        assert len(years) > 0
        assert years[0] == "2018-2019"
        assert "2031-2032" in years

    def test_custom_range(self):
        """Test custom range."""
        years = get_academic_year_range(2020, 2023)
        assert len(years) == 3
        assert "2020-2021" in years
        assert "2021-2022" in years
        assert "2022-2023" in years

    def test_range_end_exclusive(self):
        """Test that end_year is exclusive."""
        years = get_academic_year_range(2020, 2022)
        assert len(years) == 2
        assert "2020-2021" in years
        assert "2021-2022" in years
        assert "2022-2023" not in years

    def test_range_equal_start_end_empty(self):
        """Test that equal start and end returns empty list."""
        years = get_academic_year_range(2020, 2020)
        assert years == []

# Test Coverage Gaps – utils/academic_year.py

This document summarizes coverage for academic year utilities in `utils/academic_year.py`, lists edge cases, and recommends tests.

## Summary
- Covered in tests: `get_current_academic_year`, `validate_academic_year` (see `tests/unit/test_google_sheets.py`).
- Not directly covered: `get_academic_year_for_date`, `parse_academic_year`, `get_academic_year_range`.

## Functions and Gaps

### get_current_academic_year()
- Current coverage: format-only assertions.
- Additional edge cases to test:
  - Boundary behavior: dates around June 30 and July 1 (requires controllable clock or injecting date).

### get_academic_year_for_date(date)
- Current coverage: none.
- Edge cases:
  - Dates on 06-30 and 07-01 boundaries.
  - Dates across different years to validate correct rollover.

### parse_academic_year(academic_year_str)
- Current coverage: none.
- Edge cases:
  - Valid inputs → tuple of ints.
  - Invalid formats: missing dash, extra parts, non-digits, empty/None → ValueError.

### validate_academic_year(academic_year_str)
- Current coverage: valid/invalid basic cases.
- Additional edge cases:
  - Off-by-one errors where end != start+1.
  - Non-string inputs (TypeError handled gracefully → False).

### get_academic_year_range(start_year=2018, end_year=2032)
- Current coverage: none.
- Edge cases:
  - Default range length and first/last items.
  - Custom start/end; end exclusive.
  - start_year == end_year → empty list.

## Recommended Unit Tests (high-priority set)
- tests/unit/utils/test_academic_year.py
  - `test_get_academic_year_for_date_boundaries`
  - `test_parse_academic_year_valid_and_invalid`
  - `test_validate_academic_year_non_string_and_off_by_one`
  - `test_get_academic_year_range_defaults_and_custom`
  - Optional: refactor `get_current_academic_year` to accept an override date or monkeypatch datetime to test boundaries deterministically.

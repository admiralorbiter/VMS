# Test Coverage Gaps – utils/validators/*

This document summarizes current coverage for validator modules in `utils/validators/` and proposes high-value unit tests.

## Summary
- No direct unit tests found for validator modules.
- Integration flows likely exercise them indirectly; explicit unit coverage for invalid inputs and boundary conditions is missing.

## Modules Reviewed
- `business_rule_validator.py`
- `count_validator.py`
- `data_type_validator.py`
- `field_completeness_validator.py`
- `relationship_validator.py`

## High-Value Test Targets and Edge Cases

### business_rule_validator
- Complex rule evaluation with mixed truthy/falsey conditions.
- Handling of missing fields and default behaviors.
- Proper error messages and codes.

### count_validator
- Zero, negative, and extremely large counts.
- Boundary comparisons (<=, <, ==, >, >=) correctness.
- Null/None handling (skip vs fail depending on design).

### data_type_validator
- Type coercion failures vs strict validation.
- Date/time parsing errors and timezone awareness expectations.
- Numeric strings, booleans in string form, lists/dicts type checks.

### field_completeness_validator
- Required fields with empty strings, whitespace, and None.
- Conditional required fields (when X then Y is required).
- Aggregated reporting of multiple missing fields.

### relationship_validator
- Foreign key presence vs orphan detection.
- Many-to-many integrity (dangling through-table rows).
- Cyclical relationships or self-referential links if applicable.

## Recommended Unit Tests (by file)
- tests/unit/validators/test_business_rule_validator.py
  - `test_mixed_condition_evaluation`
  - `test_missing_fields_defaults`
  - `test_error_payload_structure`
- tests/unit/validators/test_count_validator.py
  - `test_boundaries_and_negatives`
  - `test_null_handling`
- tests/unit/validators/test_data_type_validator.py
  - `test_strict_types_and_coercion_failures`
  - `test_datetime_parsing_and_tz`
- tests/unit/validators/test_field_completeness_validator.py
  - `test_required_vs_empty_and_none`
  - `test_conditional_requirements`
- tests/unit/validators/test_relationship_validator.py
  - `test_foreign_key_and_m2m_integrity`
  - `test_orphans_and_cycles`

## Notes
- Where validators depend on DB, use lightweight fixtures and minimal models.
- Ensure error reporting is asserted (message keys, codes, field paths).

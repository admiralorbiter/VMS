# Test Coverage Gaps – routes/utils.py

This document summarizes current direct test coverage for utility functions in `routes/utils.py`, identifies edge cases, and recommends tests to add.

## Summary
- Direct unit tests found in `tests/**` referencing these functions: none.
- Behavior may be indirectly exercised by integration tests, but edge-case handling is not explicitly validated.

## Functions and Gaps

### parse_date(date_str)
- Current coverage: none
- Critical edge cases to test:
  - None/empty string → None
  - ISO with milliseconds/timezone (e.g., `2025-03-05T14:15:00.000+0000`) → parsed to second precision
  - CSV with time `YYYY-MM-DD HH:MM:SS`
  - CSV without seconds `YYYY-MM-DD HH:MM`
  - Date-only `YYYY-MM-DD`
  - Malformed strings → None (no exception)

### clean_skill_name(skill_name)
- Current coverage: none
- Edge cases:
  - Leading/trailing whitespace
  - Upper/mixed case inputs
  - Empty/whitespace-only string
  - Strings with non-letter characters

### parse_skills(text_skills, comma_skills)
- Current coverage: none
- Edge cases:
  - Deduplication across sources
  - Empty values and extra separators
  - Mixed whitespace and casing normalization via `clean_skill_name`

### get_email_addresses(row)
- Current coverage: none
- Edge cases:
  - Preferred type selection (`npe01__Preferred_Email__c`)
  - Missing columns; empty strings
  - Duplicate emails across fields (ensure single instance)
  - Primary designation fallback to `Email` when no preference
  - Type mapping (personal/home/alternate/work)

### get_phone_numbers(row)
- Current coverage: none
- Edge cases:
  - Preferred type (`npe01__PreferredPhone__c`) – currently unused
  - Remove non-digits consistently
  - Duplicates across fields
  - Missing columns; empty strings
  - Note: function currently builds `phones` list but never appends; tests should assert current behavior and/or guide fix when appropriate

### map_session_type(salesforce_type)
- Current coverage: none
- Edge cases:
  - Known values map to correct `EventType`
  - Unknown/None → default to `EventType.CLASSROOM_ACTIVITY`

### map_cancellation_reason(reason)
- Current coverage: none
- Edge cases:
  - Exact match "Inclement Weather Cancellation" → `CancellationReason.WEATHER`
  - Unknown/None → None

### map_event_format(format_str)
- Current coverage: none
- Edge cases:
  - "In-Person" → `EventFormat.IN_PERSON`
  - "Virtual" → `EventFormat.VIRTUAL`
  - Unknown/None → default `EventFormat.IN_PERSON`

### parse_event_skills(skills_str, is_needed=False)
- Current coverage: none
- Edge cases:
  - Empty/None → []
  - Quotes removal and trimming
  - Prefix mappings (PWY-, Skills-, CCE-, CSCs-, ACT-)
  - `is_needed=True` appends " (Required)"

### log_audit_action(action, resource_type, resource_id=None, metadata=None)
- Current coverage: none
- Edge cases:
  - Works without authenticated user (user_id None)
  - Handles DB exceptions by rolling back silently
  - Includes request context fields when available (method, path, IP)

## Recommended Unit Tests (high-priority set)
- tests/unit/routes/test_routes_utils.py
  - `test_parse_date_variants_and_failures`
  - `test_clean_skill_name_cases`
  - `test_parse_skills_merging_and_dedup`
  - `test_get_email_addresses_preferred_primary_and_dedup`
  - `test_get_phone_numbers_strips_non_digits_and_dedup` (document current non-append behavior)
  - `test_map_session_type_known_and_unknown`
  - `test_map_cancellation_reason_known_and_unknown`
  - `test_map_event_format_known_and_unknown`
  - `test_parse_event_skills_prefixes_quotes_needed_flag`
  - `test_log_audit_action_happy_path_and_db_failure`

## Notes
- `get_phone_numbers` appears incomplete (collects `cleaned_number` but does not append any Phone objects). Add tests to capture current behavior before any fix to avoid breaking changes.
- These tests focus on pure function behavior and should not depend on templates or route rendering.

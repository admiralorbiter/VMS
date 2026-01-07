# Test Coverage Gaps – routes/decorators.py

This document summarizes coverage for security decorators in `routes/decorators.py`, lists edge cases, and recommends tests.

## Summary
- No direct unit tests reference these decorators.
- Behavior may be indirectly exercised in integration tests via protected routes, but permission boundary and error payloads are not explicitly asserted.

## Decorators and Gaps

### district_scoped_required
- Ensures global users bypass checks.
- Requires `district_name` from kwargs or query string; returns 400 if missing.
- Denies access (403) if `current_user.can_view_district(district_name)` is False.

Edge cases to test:
- Global user → wrapped function executes.
- District-scoped user with allowed/denied district.
- Missing `district_name` in route args and query → 400 JSON error.
- `allowed_districts` malformed JSON (handled by model method) leading to denial.

### security_level_required(required_level)
- Requires `current_user.has_permission_level(required_level)`.
- Returns 403 JSON payload with required and user levels when insufficient.

Edge cases to test:
- User exactly at required level.
- User above required level (allowed).
- User below required level (403 with structured payload).
- Anonymous/not authenticated user where `has_permission_level` is False.

### school_scoped_required
- Similar to district-scoped; requires `school_id` in kwargs or query; 400 if missing.
- Uses `current_user.can_view_school(school_id)`.

Edge cases to test:
- Global user bypass.
- Missing `school_id` → 400.
- Denied access → 403 JSON error.

### global_users_only
- Only allows users with `scope_type == "global"`.
- Returns 403 JSON payload for non-global users.

Edge cases to test:
- Global user allowed.
- District/school scoped user denied with expected payload.

## Recommended Unit Tests (high-priority set)
- tests/unit/routes/test_decorators.py (using Flask app context and a mock user):
  - `test_district_scoped_required_global_user_allows`
  - `test_district_scoped_required_missing_param_returns_400`
  - `test_district_scoped_required_denied_returns_403`
  - `test_security_level_required_exact_boundary_and_above`
  - `test_security_level_required_below_returns_structured_403`
  - `test_school_scoped_required_missing_param_returns_400`
  - `test_global_users_only_denies_non_global`

## Notes
- Prefer function-wrapped endpoints within tests to isolate decorator behavior.
- Validate JSON payload keys (`error`, `required_level`, `user_level`) for 403 responses.
- Use parametrization to cover multiple permission levels succinctly.

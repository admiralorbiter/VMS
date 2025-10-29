# Test Coverage Summary – What’s Covered vs Gaps

This summary consolidates findings from recent coverage analysis and lists high-priority test additions.

## Current Strengths
- Broad integration coverage across routes (auth, attendance, events, organizations, volunteers, reports, virtual, API) – all passing.
- Solid unit coverage for models and some utilities (`get_current_academic_year`, `validate_academic_year`).

## Identified Gaps (by area)
- Route utilities (`routes/utils.py`): no direct unit tests for parsing/mapping helpers; propose tests for `parse_date`, `parse_skills`, email/phone extraction, enum mappings, `log_audit_action`.
- Decorators (`routes/decorators.py`): no direct tests for permission boundary cases and structured 403 payloads.
- Academic year utils: missing tests for `get_academic_year_for_date`, `parse_academic_year`, `get_academic_year_range`, and boundary behavior for `get_current_academic_year`.
- Services (`utils/services/*`): no direct unit tests for aggregation, scoring, thresholds, history, organization rollups.
- Validators (`utils/validators/*`): no direct unit tests for invalid inputs and boundary conditions.
- Cache scheduler (`utils/cache_refresh_scheduler.py` + management routes): no tests for scheduler controls, idempotency, status payloads, or failure paths.
- Pathway events (`routes/events/pathway_events.py`): no tests; complex SF/DC/DB integration warrants targeted coverage.
- Salesforce client (`utils/salesforce_client.py`): no unit tests; external dependency needs mocking.

## High-Priority Test Additions
1. Route utilities: parsing/mapping and audit logging unit tests.
2. Decorators: permission boundary tests with JSON payload assertions.
3. Academic year: boundary/date-driven tests; parsing/range tests.
4. Services: scoring/aggregation/threshold deterministic tests.
5. Validators: negative-path and boundary tests.
6. Cache scheduler: start/stop, status payloads, refresh success/failure.
7. Pathway events: unit and integration tests with mocked Salesforce.
8. Salesforce client: connection, rate limiting, query success/error, samples.

## Next Steps
- Add unit test modules per gap docs in `tests/unit/...` and `tests/integration/...`.
- Focus on pure-function areas first (low flake risk), then DB-dependent and external-integration tests.

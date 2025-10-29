# Test Coverage Gaps – routes/events/pathway_events.py

This document summarizes coverage for the pathway event sync blueprint and proposes tests.

## Summary
- No direct unit or integration tests for pathway events sync endpoints/utilities.
- High complexity (Salesforce integration, DB joins, data parsing) warrants targeted tests.

## Key Areas and Edge Cases
- Authentication/authorization on sync endpoints.
- Salesforce client failures: auth errors, timeouts, partial responses.
- Event creation vs update: idempotency and duplicate handling.
- District inference from student participation; missing/ambiguous data.
- Skill parsing and mappings; unknown prefixes.
- Volunteer participation linking; missing volunteers or skills.
- Performance on large batches; pagination across Salesforce queries.

## Recommended Tests
- tests/unit/events/test_pathway_events_utils.py
  - `test_create_event_from_salesforce_minimal_and_full_payloads`
  - `test_district_inference_from_students`
  - `test_skill_parsing_and_prefix_mapping`
  - `test_volunteer_participation_linking`
- tests/integration/events/test_pathway_events_routes.py
  - `test_sync_unaffiliated_events_auth_required`
  - `test_salesforce_auth_failure_returns_error`
  - `test_sync_creates_and_updates_events_idempotently`
  - `test_pagination_and_large_batch_handling`

## Notes
- Mock `simple_salesforce` responses for deterministic tests.
- Use app/db fixtures; isolate expensive flows and avoid hitting external services.

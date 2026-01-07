# Test Coverage Gaps – utils/salesforce_client.py

This document summarizes coverage for `SalesforceClient` and proposes unit tests.

## Summary
- No direct unit tests found. External dependency (`simple_salesforce`) and environment reliance need mocking.

## High-Value Test Targets
- Connection logic
  - `_connect` retry limits and spacing via `_last_connection_attempt`.
  - Behavior when `simple_salesforce` not installed.
  - Successful connection resets attempts.
- Rate limiting
  - `_rate_limit` enforces minimum interval (use time.monkeypatch/fast-forward).
- Query methods
  - `get_*_count` methods: successful path parses `totalSize`.
  - Error path raises `SalesforceClientError` and logs.
  - Local DB counts (`get_school_count`, `get_district_count`) happy/error paths.
- Sample methods
  - Strip `attributes` key; limit respected; caching no-ops tolerated.
- Health and lifecycle
  - `get_health_status` with/without established connection.
  - `clear_cache` returns 0; `close` sets `sf=None`.
- Convenience
  - `get_entity_count` dispatch and invalid entity type raises `ValueError`.

## Recommended Tests
- tests/unit/utils/test_salesforce_client.py
  - `test_connect_success_and_retry_limits`
  - `test_connect_when_simple_salesforce_missing`
  - `test_rate_limit_interval_enforced`
  - `test_get_entity_counts_success_and_errors`
  - `test_local_db_counts_success_and_failure`
  - `test_samples_strip_attributes_and_respect_limit`
  - `test_get_health_status_connected_and_not`
  - `test_get_entity_count_dispatch_and_invalid_type`

## Notes
- Mock `simple_salesforce.Salesforce` and `.query()/.describe()`.
- Use app/db fixtures for local DB queries.

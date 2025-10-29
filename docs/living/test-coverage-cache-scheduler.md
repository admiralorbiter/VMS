# Test Coverage Gaps – utils/cache_refresh_scheduler.py and routes/management/cache_management.py

This document summarizes coverage for the cache refresh scheduler and management routes, and proposes tests.

## Summary
- No direct unit tests for scheduler controls or refresh functions.
- Management routes are covered by integration tests generically, but not asserting scheduler behavior or status payloads.

## Functions and Gaps (utils/cache_refresh_scheduler.py)
- `CacheRefreshScheduler.start/stop`:
  - Multiple start calls (idempotency warning vs error).
  - Stop joins thread safely; stop when not started.
- `_run_scheduler` loop:
  - Error path increments stats and records last_error.
  - Sleep interval correctness (can monkeypatch `time.sleep`).
- `_refresh_all_caches` and specific refresh methods:
  - Successful path updates stats and last_refresh.
  - Failure path increments failed and sets last_error; rolls back when needed.
  - Date range and school year formatting correctness.
- Public API:
  - `start_cache_refresh_scheduler`, `stop_cache_refresh_scheduler`
  - `refresh_all_caches`, `refresh_specific_cache`
  - `get_cache_status` returns expected fields and values.

## Routes and Gaps (routes/management/cache_management.py)
- Admin-only restrictions enforced for all endpoints.
- Endpoints:
  - `/management/cache/status` returns scheduler status.
  - `/management/cache/refresh` triggers manual refresh.
  - `/management/cache/scheduler/start|stop` control scheduler.
- Gaps:
  - Status payload content assertions.
  - Start/stop idempotency behavior.
  - Non-admin access denied.

## Recommended Tests
- tests/unit/utils/test_cache_refresh_scheduler.py
  - `test_start_stop_idempotency`
  - `test_refresh_all_updates_stats_and_last_refresh`
  - `test_refresh_specific_cache_invalid_type_raises`
  - `test_get_cache_status_payload`
  - `test_refresh_failures_increment_failed_and_record_error`
- tests/integration/management/test_cache_management_routes.py
  - `test_status_requires_admin_and_returns_expected_fields`
  - `test_manual_refresh_triggers_scheduler_call`
  - `test_scheduler_start_stop_controls`

## Notes
- Use monkeypatch to bypass real sleeping and background threads when testing `_run_scheduler`.
- Prefer isolating side effects (DB writes) with transactional tests.

# Test Coverage Gaps – utils/services/*

This document summarizes current coverage for service-layer modules in `utils/services/` and recommends high-value unit tests.

## Summary
- No direct unit tests found referencing service modules.
- Some behavior appears covered via integration routes and validation scripts, but core service logic and edge cases lack explicit unit coverage.

## Modules Reviewed
- `aggregation_service.py`
- `history_service.py`
- `organization_service.py`
- `quality_scoring_service.py`
- `score_calculator.py`
- `score_weighting_engine.py`
- `threshold_manager.py`

## High-Value Test Targets and Edge Cases

### aggregation_service
- Test aggregation with empty datasets, single-item, and large sets.
- Verify handling of None/NaN values, zero division safeguards.
- Validate date range filters and boundary inclusivity.

### history_service
- Event lifecycle operations (create/update/delete) produce expected entries.
- Idempotency: repeated calls should not duplicate history improperly.
- Error handling on DB failures (rollbacks, no partial state).

### organization_service
- Organization rollups: totals, summaries, caches correct under joins and filters.
- Edge cases: organizations with no volunteers/events; mixed district filters.

### quality_scoring_service / score_calculator / score_weighting_engine
- Deterministic scoring for known inputs.
- Weighting combinations and normalization (sum to 1, or expected scaling).
- Threshold crossing behavior (just below/at/above thresholds).
- Missing metrics defaulting and resilience (None values).

### threshold_manager
- CRUD of thresholds; defaults when missing.
- Boundary behavior when values sit exactly at threshold.

## Recommended Unit Tests (by file)
- tests/unit/services/test_aggregation_service.py
  - `test_aggregate_empty_and_single`
  - `test_aggregate_with_nans_and_zeros`
  - `test_date_filter_boundaries`
- tests/unit/services/test_history_service.py
  - `test_create_update_delete_history_entries`
  - `test_idempotent_operations`
  - `test_db_failure_rollback`
- tests/unit/services/test_organization_service.py
  - `test_rollups_with_and_without_data`
  - `test_district_filtering_and_combination`
- tests/unit/services/test_scoring.py
  - `test_score_calculation_deterministic`
  - `test_weighting_normalization_and_combinations`
  - `test_threshold_crossings`
  - `test_missing_metrics_defaults`
- tests/unit/services/test_threshold_manager.py
  - `test_threshold_crud_and_defaults`
  - `test_boundary_conditions`

## Notes
- Prefer pure-function testing by isolating DB access via fakes/mocks where possible.
- For DB-dependent flows, use existing app/db fixtures to validate transactional safety.

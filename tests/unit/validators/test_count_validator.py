"""
Unit tests for utils/validators/count_validator.py focusing on discrepancy context and severity.
"""

import pytest

from utils.validators.count_validator import CountValidator


@pytest.fixture
def validator(monkeypatch):
    v = CountValidator(entity_type="volunteer")
    # Avoid metric internals and external close
    monkeypatch.setattr(v, "create_metric", lambda **kwargs: object())
    monkeypatch.setattr(v, "add_metric", lambda metric: None)
    return v


def test_expected_discrepancy_info_severity(validator, monkeypatch):
    """Volunteer tolerance 5%: within threshold -> info severity expected."""
    monkeypatch.setattr(validator, "_get_vms_count", lambda e: 100)
    monkeypatch.setattr(validator, "_get_salesforce_count", lambda e: 98)  # 2% diff

    before = len(validator.results)
    validator._validate_count_with_context("volunteer")
    after = len(validator.results)

    assert after == before + 1
    assert validator.results[-1].is_info


def test_unexpected_discrepancy_warning_or_error(validator, monkeypatch):
    """Volunteer 5% tolerance: ~12% diff -> error; higher diffs map to error/critical."""
    # Case 1: ~12% -> error per mapping (<= tolerance*5)
    monkeypatch.setattr(validator, "_get_vms_count", lambda e: 100)
    monkeypatch.setattr(validator, "_get_salesforce_count", lambda e: 88)
    validator._validate_count_with_context("volunteer")
    assert validator.results[-1].is_error or validator.results[-1].is_critical

    # Case 2: ~30% -> error/critical
    monkeypatch.setattr(validator, "_get_vms_count", lambda e: 100)
    monkeypatch.setattr(validator, "_get_salesforce_count", lambda e: 70)
    validator._validate_count_with_context("volunteer")
    assert validator.results[-1].is_error or validator.results[-1].is_critical


def test_event_expected_large_discrepancy_still_expected(monkeypatch):
    """Events have import filtering; even large percentage is expected per logic."""
    v = CountValidator(entity_type="event")
    monkeypatch.setattr(v, "create_metric", lambda **kwargs: object())
    monkeypatch.setattr(v, "add_metric", lambda metric: None)
    monkeypatch.setattr(v, "_get_vms_count", lambda e: 100)
    monkeypatch.setattr(v, "_get_salesforce_count", lambda e: 30)  # 70% diff

    before = len(v.results)
    v._validate_count_with_context("event")
    after = len(v.results)

    assert after == before + 1
    assert v.results[-1].is_info  # expected discrepancy

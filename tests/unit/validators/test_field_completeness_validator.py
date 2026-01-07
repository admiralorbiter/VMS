"""
Unit tests for utils/validators/field_completeness_validator.py focusing on required fields and ranges.
"""

from datetime import datetime, timezone

import pytest

from utils.validators.field_completeness_validator import FieldCompletenessValidator


@pytest.fixture
def validator(monkeypatch):
    v = FieldCompletenessValidator(entity_type="organization")
    # Avoid depending on ValidationMetric.create_metric internals
    monkeypatch.setattr(v, "create_metric", lambda **kwargs: object())
    monkeypatch.setattr(v, "add_metric", lambda metric: None)
    return v


def test_required_fields_and_formats(validator, monkeypatch):
    """Validate that required fields and formats are enforced for a sample."""
    validator.required_fields = {"organization": ["Name", "Email", "Employees"]}
    validator.field_formats = {
        "organization": {
            "Email": {"type": "email"},
        }
    }
    validator.field_ranges = {
        "organization": {
            "Employees": {"min": 1, "max": 100000},
        }
    }

    sample = [
        {
            "Id": "001xx000003DGSuAAO",
            "Name": "Good Org",
            "Email": "contact@example.com",
            "Employees": 10,
        },
        {"Id": "001xx000003DGSvAAO", "Name": "", "Email": "bad-email", "Employees": 0},
    ]

    monkeypatch.setattr(
        validator, "_get_salesforce_sample", lambda et, limit=100: sample
    )

    before = len(validator.results)
    validator._validate_entity_completeness("organization")
    after = len(validator.results)

    assert after == before + 1


def test_range_and_string_length_helpers(validator):
    """Directly test _validate_field_range and _validate_field_format helpers."""
    res = validator._validate_field_range("organization", "Employees", 5)
    assert res["valid"] is True
    validator.field_ranges = {"organization": {"Employees": {"min": 10, "max": 20}}}
    res = validator._validate_field_range("organization", "Employees", 5)
    assert res["valid"] is False and "below minimum" in res["error"]
    res = validator._validate_field_range("organization", "Employees", 25)
    assert res["valid"] is False and "above maximum" in res["error"]

    validator.field_ranges = {
        "organization": {"Code": {"min_length": 3, "max_length": 5}}
    }
    res = validator._validate_field_range("organization", "Code", "AB")
    assert res["valid"] is False and "below minimum" in res["error"]
    res = validator._validate_field_range("organization", "Code", "ABCDEF")
    assert res["valid"] is False and "above maximum" in res["error"]

    validator.field_formats = {"organization": {"Email": {"type": "email"}}}
    res = validator._validate_field_format("organization", "Email", "bad")
    assert res["valid"] is False and "Invalid email" in res["error"]
    res = validator._validate_field_format("organization", "Email", "ok@example.com")
    assert res["valid"] is True

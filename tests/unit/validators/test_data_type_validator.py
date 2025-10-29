"""
Unit tests for utils/validators/data_type_validator.py focusing on format validation.
"""

from datetime import datetime, timezone

import pytest

from utils.validators.data_type_validator import DataTypeValidator


@pytest.fixture
def validator(monkeypatch):
    v = DataTypeValidator(entity_type="volunteer")
    # Avoid depending on ValidationMetric.create_metric internals
    monkeypatch.setattr(v, "create_metric", lambda **kwargs: object())
    monkeypatch.setattr(v, "add_metric", lambda metric: None)
    return v


def test_validate_record_data_types_email_phone_url_and_date(validator, monkeypatch):
    """Validate mixed field formats using validator's internal logic."""
    validator.format_rules = {
        "volunteer": {
            "Email": {"type": "email", "required": True},
            "Phone": {"type": "phone", "required": True},
            "Website": {"type": "url", "required": False},
            "StartDate": {"type": "date", "required": True, "format": "ISO8601"},
        }
    }

    sample = [
        {
            "Email": "valid@example.com",
            "Phone": "+15551234567",
            "Website": "https://example.com",
            "StartDate": datetime(2025, 3, 5, 14, 15, tzinfo=timezone.utc).isoformat(),
        },
        {
            "Email": "bad-email",
            "Phone": "(555) 123-4567",
            "Website": "http://example.com/page",
            "StartDate": "2025-03-05T14:15:00Z",
        },
    ]

    monkeypatch.setattr(
        validator, "_get_salesforce_sample", lambda et, limit=100: sample
    )

    before = len(validator.results)
    validator._validate_entity_data_types("volunteer")
    after = len(validator.results)

    assert after == before + 1


def test_validate_enum_and_regex_fields(validator, monkeypatch):
    """Validate enum and custom regex patterns."""
    validator.format_rules = {
        "volunteer": {
            "Status": {
                "type": "enum",
                "allowed_values": ["Active", "Inactive"],
                "required": True,
            },
            "Code": {"pattern": r"^[A-Z]{3}-\d{3}$", "required": True},
        }
    }

    sample = [
        {"Status": "Active", "Code": "ABC-123"},
        {"Status": "Unknown", "Code": "abc-123"},
    ]

    monkeypatch.setattr(
        validator, "_get_salesforce_sample", lambda et, limit=100: sample
    )

    before = len(validator.results)
    validator._validate_entity_data_types("volunteer")
    after = len(validator.results)

    assert after == before + 1


def test_required_field_null_is_error(validator):
    """Directly exercise _validate_field_format handling of None with required=True."""
    res = validator._validate_field_format(
        "Email", None, {"type": "email", "required": True}
    )
    assert res["valid"] is False and "Required" in res["error"]

    res = validator._validate_field_format(
        "Email", None, {"type": "email", "required": False}
    )
    assert res["valid"] is True

"""
Unit tests for utils/validators/business_rule_validator.py focusing on business rule checks.
"""

from datetime import datetime, timedelta

import pytest

from utils.validators.business_rule_validator import BusinessRuleValidator


@pytest.fixture
def validator(monkeypatch):
    v = BusinessRuleValidator(entity_type="event")
    # Avoid metric internals
    monkeypatch.setattr(v, "add_metric", lambda metric: None)
    monkeypatch.setattr(v, "_add_summary_metrics", lambda results: None)
    return v


def test_status_date_capacity_rules(validator, monkeypatch):
    """Validate status in allowed set, date range ordering, and capacity constraints."""
    # Configure rules for 'event'
    validator.business_rules = {
        "event": {
            # status_transition: define allowed values (treated as present statuses set)
            "status_rule": {
                "type": "status_transition",
                "status_field": "Status__c",
                "allowed_transitions": {
                    "Planned": ["Confirmed", "Cancelled"],
                    "Confirmed": ["Completed"],
                },
            },
            # date_range
            "date_rule": {
                "type": "date_range",
                "start_field": "StartDate__c",
                "end_field": "EndDate__c",
                "min_duration_days": 0,
                "max_duration_days": 365,
            },
            # capacity_limit
            "capacity_rule": {
                "type": "capacity_limit",
                "capacity_field": "Capacity__c",
                "current_field": "Registered__c",
                "max_capacity": 1000,
            },
        }
    }

    now = datetime.now()
    sample = [
        # Valid record
        {
            "Id": "a00xx00000OK1",
            "Status__c": "Planned",
            "StartDate__c": now.isoformat(),
            "EndDate__c": (now + timedelta(days=1)).isoformat(),
            "Capacity__c": 30,
            "Registered__c": 10,
        },
        # Invalid status and reversed dates, capacity exceeded
        {
            "Id": "a00xx00000OK2",
            "Status__c": "Unknown",
            "StartDate__c": (now + timedelta(days=1)).isoformat(),
            "EndDate__c": now.isoformat(),
            "Capacity__c": 20,
            "Registered__c": 25,
        },
    ]
    monkeypatch.setattr(validator, "_get_salesforce_sample", lambda et: sample)

    results = validator._validate_entity_business_rules("event")

    # Expect warnings for invalid status and errors for date reversed and capacity exceeded
    assert any(
        r.validation_type == "business_rules"
        and r.field_name == "Status__c"
        and r.is_warning
        for r in results
    )
    assert any(
        r.validation_type == "business_rules"
        and r.field_name == "StartDate__c_EndDate__c"
        and r.is_error
        for r in results
    )
    assert any(
        r.validation_type == "business_rules"
        and r.field_name == "Capacity__c_Registered__c"
        and r.is_error
        for r in results
    )


def test_cross_field_summary_and_required(validator, monkeypatch):
    """Validate cross-field rule statistics and summary severity selection."""
    validator.business_rules = {
        "event": {
            "cross": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "Format__c",
                        "if_value": "Virtual",
                        "then_field": "Meeting_Link__c",
                        "then_required": True,
                        "message": "Virtual events require meeting link",
                    }
                ],
            }
        }
    }

    sample = [
        {"Id": "a00xx1", "Format__c": "Virtual", "Meeting_Link__c": ""},
        {"Id": "a00xx2", "Format__c": "Virtual", "Meeting_Link__c": None},
        {"Id": "a00xx3", "Format__c": "In-Person", "Meeting_Link__c": None},
    ]
    monkeypatch.setattr(validator, "_get_salesforce_sample", lambda et: sample)

    results = validator._validate_entity_business_rules("event")

    # Expect a cross-field summary result and at least one individual missing entry (may be error or critical)
    assert any(
        r.validation_type == "business_rules" and r.field_name.endswith("_summary")
        for r in results
    )
    assert any(
        r.validation_type == "business_rules"
        and r.field_name == "Meeting_Link__c"
        and (r.is_error or r.is_critical)
        for r in results
    )

"""
Unit tests for utils/validators/relationship_validator.py focusing on relationship checks.
"""

import pytest

from utils.validators.relationship_validator import RelationshipValidator


@pytest.fixture
def validator(monkeypatch):
    v = RelationshipValidator(entity_type="contact")
    # Avoid metric creation internals
    monkeypatch.setattr(v, "add_metric", lambda metric: None)
    monkeypatch.setattr(v, "_add_summary_metrics", lambda results: None)
    return v


def test_required_and_optional_relationships_and_orphans(validator, monkeypatch):
    """Validate required/optional relationships and orphan detection."""
    # Configure relationships for a fake entity 'contact'
    validator.entity_relationships = {
        "contact": {
            "required_relationships": {
                "AccountId": {"type": "lookup", "severity": "error"}
            },
            "optional_relationships": {"Primary_Affiliation__c": {"type": "lookup"}},
        }
    }
    validator.validation_settings = {
        "orphaned_record_detection": True,
        "circular_reference_detection": True,
        "validation_thresholds": {"orphaned_records": 0.0},
    }

    # Sample records: one good, one orphan, one with invalid optional lookup
    sample = [
        {
            "Id": "003xx000003DGSuAAO",
            "AccountId": "001xx000003DGSuAAO",
            "Primary_Affiliation__c": "001xx000003DGSvAAO",
        },
        {"Id": "003xx000003DGSvAAO", "AccountId": "", "Primary_Affiliation__c": None},
        {
            "Id": "003xx000003DGSwAAO",
            "AccountId": "001xx000003DGSwAAO",
            "Primary_Affiliation__c": "bad-id",
        },
    ]
    monkeypatch.setattr(
        validator, "_get_salesforce_sample", lambda et, limit=100: sample
    )

    results = validator._validate_entity_relationships("contact")

    # Expect: one error for missing required, one warning for invalid optional lookup, and orphaned summary
    assert any(
        r.validation_type == "required_relationship" and r.is_error for r in results
    )
    assert any(
        r.validation_type == "relationship_format" and r.is_warning for r in results
    )
    assert any(
        r.validation_type in ("relationship_completeness", "orphaned_records_summary")
        for r in results
    )


def test_circular_reference_detection(validator, monkeypatch):
    """Detect self-referential circular reference on required lookup."""
    validator.entity_relationships = {
        "contact": {"required_relationships": {"Manager__c": {"type": "lookup"}}}
    }
    validator.validation_settings = {
        "circular_reference_detection": True,
    }

    sample = [
        {"Id": "003xx000003ABCdAAO", "Manager__c": "003xx000003ABCdAAO"},  # circular
        {"Id": "003xx000003ABCeAAO", "Manager__c": "003xx000003ABCfAAO"},  # OK
    ]
    monkeypatch.setattr(
        validator, "_get_salesforce_sample", lambda et, limit=100: sample
    )

    results = validator._validate_entity_relationships("contact")

    assert any(
        r.validation_type == "circular_reference" and r.is_error for r in results
    )

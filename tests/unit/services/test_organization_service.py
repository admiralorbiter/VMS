import pytest

from models import db
from models.organization import Organization, OrganizationAlias
from services.organization_service import (
    clean_organization_suffix,
    resolve_organization,
)


def test_clean_organization_suffix():
    assert clean_organization_suffix("Prep-KC, Inc.") == "prepkc"
    assert clean_organization_suffix("Apple Computer, Corp.") == "apple computer"
    assert clean_organization_suffix("IBM Corporation") == "ibm"
    assert clean_organization_suffix("Google LLC") == "google"
    assert clean_organization_suffix("H&R Block") == "hr block"
    assert clean_organization_suffix("") == ""
    assert clean_organization_suffix("  Messy   Name  ") == "messy   name"


def test_tier1_cache_match(app):
    with app.app_context():
        # Fake organization in cache
        fake_org = Organization(id=999, name="Cached Org")
        caches = {"organization_by_name": {"cached org": fake_org}}

        result = resolve_organization("Cached ORG", caches)
        assert result is not None
        assert result.id == 999


def test_tier2_exact_db_match(app):
    with app.app_context():
        # Create an org
        org = Organization(name="Exact Match Company")
        db.session.add(org)
        db.session.commit()

        # Test exact match (case insensitive)
        result = resolve_organization("EXACT match COMPANY")
        assert result is not None
        assert result.id == org.id


def test_tier3_alias_match(app):
    with app.app_context():
        # Create org and alias
        org = Organization(name="Canonical Company")
        db.session.add(org)
        db.session.flush()

        alias = OrganizationAlias(name="Weird Alias Name", organization_id=org.id)
        db.session.add(alias)
        db.session.commit()

        # Resolve by alias
        result = resolve_organization("WEIRD alias name")
        assert result is not None
        assert result.id == org.id


def test_tier4_quarantine_first(app):
    """B2: T4 now returns None instead of auto-writing an alias.

    Before B2, resolve_organization() would auto-write an OrganizationAlias
    and return the matched org. After B2 (quarantine-first), it must return
    None and leave alias creation to admin confirmation.
    """
    with app.app_context():
        from models.organization import Organization, OrganizationAlias
        from services.organization_service import resolve_organization

        org = Organization(name="Next Level")
        db.session.add(org)
        db.session.commit()

        incoming_name = "Next Level, Inc."

        # Initially, it shouldn't exist as an alias
        assert OrganizationAlias.query.filter_by(name=incoming_name).first() is None

        # B2: T4 now returns None (quarantine-first, no auto-alias)
        result = resolve_organization(incoming_name)
        assert result is None  # NOT the org — quarantine-first

        # Critical: verify the alias was NOT auto-written
        learned_alias = OrganizationAlias.query.filter_by(name=incoming_name).first()
        assert learned_alias is None  # B2: no auto-alias


def test_unresolvable_organization(app):
    with app.app_context():
        result = resolve_organization("Completely Unknown Entity LLC")
        assert result is None

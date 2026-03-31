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


def test_tier4_suffix_auto_learning(app):
    with app.app_context():
        # Create an org with a clean name
        org = Organization(name="Next Level")
        db.session.add(org)
        db.session.commit()

        # Pathful sends us "Next Level, Inc."
        incoming_name = "Next Level, Inc."

        # Initially, it shouldn't exist as an alias
        assert OrganizationAlias.query.filter_by(name=incoming_name).first() is None

        # Resolve triggers auto-learning
        result = resolve_organization(incoming_name)
        assert result is not None
        assert result.id == org.id

        # Verify the auto-learned alias was saved to DB
        learned_alias = OrganizationAlias.query.filter_by(name=incoming_name).first()
        assert learned_alias is not None
        assert learned_alias.organization_id == org.id
        assert learned_alias.is_auto_generated is True


def test_unresolvable_organization(app):
    with app.app_context():
        result = resolve_organization("Completely Unknown Entity LLC")
        assert result is None

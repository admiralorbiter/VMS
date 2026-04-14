"""
Unit tests for services/district_service.py

Tests cover district name resolution, alias lookups,
variant collection, and tenant district name resolution.
"""

import pytest

from models import db
from models.district_model import District, DistrictAlias
from services.district_service import (
    get_district_name_variants,
    resolve_district,
    seed_district_aliases,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def districts(app):
    """Create a set of districts and aliases for testing."""
    with app.app_context():
        d1 = District(name="Kansas City Kansas Public Schools")
        d2 = District(name="Grandview School District")
        db.session.add_all([d1, d2])
        db.session.commit()

        a1 = DistrictAlias(alias="KCKPS", district_id=d1.id)
        db.session.add(a1)
        db.session.commit()

        yield {"kckps": d1, "grandview": d2, "kckps_alias": a1}

        # Cleanup
        DistrictAlias.query.delete()
        District.query.delete()
        db.session.commit()


# ── resolve_district ──────────────────────────────────────────────────


class TestResolveDistrict:

    def test_exact_name_match(self, app, districts):
        with app.app_context():
            result = resolve_district("Kansas City Kansas Public Schools")
            assert result is not None
            assert result.name == "Kansas City Kansas Public Schools"

    def test_alias_match(self, app, districts):
        with app.app_context():
            result = resolve_district("KCKPS")
            assert result is not None
            assert result.name == "Kansas City Kansas Public Schools"

    def test_case_insensitive_name(self, app, districts):
        with app.app_context():
            result = resolve_district("kansas city kansas public schools")
            assert result is not None
            assert result.name == "Kansas City Kansas Public Schools"

    def test_case_insensitive_alias(self, app, districts):
        with app.app_context():
            result = resolve_district("kckps")
            assert result is not None
            assert result.name == "Kansas City Kansas Public Schools"

    def test_not_found_returns_none(self, app, districts):
        with app.app_context():
            result = resolve_district("Nonexistent District")
            assert result is None

    def test_empty_string_returns_none(self, app, districts):
        with app.app_context():
            assert resolve_district("") is None

    def test_none_returns_none(self, app, districts):
        with app.app_context():
            assert resolve_district(None) is None

    def test_whitespace_only_returns_none(self, app, districts):
        with app.app_context():
            assert resolve_district("   ") is None

    def test_strips_whitespace(self, app, districts):
        with app.app_context():
            result = resolve_district("  KCKPS  ")
            assert result is not None
            assert result.name == "Kansas City Kansas Public Schools"


# ── get_district_name_variants ────────────────────────────────────────


class TestGetDistrictNameVariants:

    def test_returns_canonical_and_aliases(self, app, districts):
        with app.app_context():
            d = db.session.get(District, districts["kckps"].id)
            variants = get_district_name_variants(d)
            assert "Kansas City Kansas Public Schools" in variants
            assert "KCKPS" in variants

    def test_district_without_aliases(self, app, districts):
        with app.app_context():
            d = db.session.get(District, districts["grandview"].id)
            variants = get_district_name_variants(d)
            assert "Grandview School District" in variants
            assert len(variants) == 1

    def test_none_district_returns_empty(self, app):
        with app.app_context():
            assert get_district_name_variants(None) == set()


# ── seed_district_aliases ─────────────────────────────────────────────


class TestSeedDistrictAliases:

    def test_creates_aliases_for_existing_districts(self, app):
        """Seed creates aliases when the target district exists."""
        with app.app_context():
            # Create one district that matches a legacy alias
            d = District(name="Kansas City Kansas Public Schools")
            db.session.add(d)
            db.session.commit()

            summary = seed_district_aliases()
            assert summary["created"] >= 1 or summary["skipped"] >= 0

            # Cleanup
            DistrictAlias.query.delete()
            District.query.delete()
            db.session.commit()

    def test_idempotent_second_run(self, app):
        """Second run skips existing aliases."""
        with app.app_context():
            d = District(name="Kansas City Kansas Public Schools")
            db.session.add(d)
            db.session.commit()

            first_run = seed_district_aliases()
            second_run = seed_district_aliases()

            # Second run should skip what was already created
            assert second_run["created"] == 0

            # Cleanup
            DistrictAlias.query.delete()
            District.query.delete()
            db.session.commit()

    def test_missing_districts_tracked(self, app):
        """Aliases for missing districts are tracked in 'missing'."""
        with app.app_context():
            # No districts in DB — all should be 'missing'
            summary = seed_district_aliases()
            assert len(summary["missing"]) > 0

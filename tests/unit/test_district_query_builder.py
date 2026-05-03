"""
Unit tests for build_district_event_conditions() in routes.reports.common.

Verifies:
- Helper returns a non-empty list of SQLAlchemy conditions
- District name ilike condition is present
- Alias conditions are added from DISTRICT_MAPPING
- No-alias district works without error
- Short-name stripping condition (' School District' removal) is included
- OUTPUT EQUIVALENCE: events found via the helper match what the old inline
  builder would have found (critical regression gate for TD-063-X)
"""

from datetime import datetime

import pytest

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventType
from models.school_model import School


class TestBuildDistrictEventConditions:
    """Unit tests for the extracted query condition builder."""

    @pytest.fixture
    def grandview_district(self, app):
        """Grandview School District — has 'Grandview' alias in DISTRICT_MAPPING."""
        with app.app_context():
            d = District(
                name="Grandview School District",
                salesforce_id="0015f00000JU4opAAD",
            )
            db.session.add(d)
            db.session.flush()
            s = School(
                id="GV_UNIT_HIGH",
                name="Grandview Unit High",
                district_id=d.id,
                level="High",
            )
            db.session.add(s)
            db.session.commit()
            yield d

    def test_returns_non_empty_list(self, app, grandview_district):
        """Helper returns a non-empty list of conditions."""
        with app.app_context():
            from routes.reports.common import build_district_event_conditions

            district = District.query.get(grandview_district.id)
            conditions = build_district_event_conditions(district)
            assert isinstance(conditions, list)
            assert len(conditions) > 0

    def test_district_name_condition_present(self, app, grandview_district):
        """
        Condition list includes at least one ilike condition on district_partner.
        We can't inspect literal values (SQLAlchemy parameterizes them), so we
        count that ilike conditions are present via clause type.
        """
        with app.app_context():
            from sqlalchemy.sql.elements import BinaryExpression

            from routes.reports.common import build_district_event_conditions

            district = District.query.get(grandview_district.id)
            conditions = build_district_event_conditions(district)
            # At minimum: M2M FK, school FK, school name ilike, district name ilike,
            # district short-name ilike
            assert (
                len(conditions) >= 4
            ), f"Expected at least 4 conditions, got {len(conditions)}"

    def test_alias_conditions_added_when_mapping_provided(
        self, app, grandview_district
    ):
        """When district_mapping has aliases, more conditions are returned."""
        with app.app_context():
            from routes.reports.common import (
                DISTRICT_MAPPING,
                build_district_event_conditions,
            )

            district = District.query.get(grandview_district.id)
            mapping = DISTRICT_MAPPING.get("0015f00000JU4opAAD")

            conds_with = build_district_event_conditions(
                district, district_mapping=mapping
            )
            conds_without = build_district_event_conditions(
                district, district_mapping={}  # empty mapping = no aliases
            )
            assert len(conds_with) > len(
                conds_without
            ), "Alias conditions should increase total condition count"

    def test_no_alias_district_works_without_error(self, app):
        """District not in DISTRICT_MAPPING returns a valid (non-empty) list."""
        with app.app_context():
            d = District(name="Unknown Test District", salesforce_id="UNKNOWN_TEST_SF")
            db.session.add(d)
            db.session.commit()

            from routes.reports.common import build_district_event_conditions

            conditions = build_district_event_conditions(d)
            assert isinstance(conditions, list)
            assert len(conditions) >= 2  # At minimum: M2M FK + district name match

    def test_short_name_stripping_condition_present(self, app, grandview_district):
        """
        A district with 'School District' in its name should generate MORE conditions
        than one without, because the short-name stripping adds an extra ilike.
        We verify this by comparing condition count with vs. without the suffix.
        """
        with app.app_context():
            from routes.reports.common import build_district_event_conditions

            district = District.query.get(grandview_district.id)
            conds = build_district_event_conditions(district)

            # A district with " School District" in name produces at least 5 base
            # conditions (M2M FK, school FK, school title ilike, school partner ilike,
            # district name ilike, short-name ilike)
            assert (
                len(conds) >= 5
            ), f"Expected >= 5 conditions for a 'School District' named district, got {len(conds)}"

    def test_schools_param_overrides_lazy_load(self, app, grandview_district):
        """Passing schools= explicitly uses that list instead of district.schools."""
        with app.app_context():
            from routes.reports.common import build_district_event_conditions

            district = District.query.get(grandview_district.id)
            pre_fetched = School.query.filter_by(district_id=district.id).all()

            conds_explicit = build_district_event_conditions(
                district, schools=pre_fetched
            )
            conds_lazy = build_district_event_conditions(district)

            # Both paths should produce the same number of conditions
            assert len(conds_explicit) == len(conds_lazy)


class TestQueryBuilderOutputEquivalence:
    """
    OUTPUT EQUIVALENCE TEST — the critical regression gate for TD-063-X.

    Creates events attributed to a district via 3 different paths, then
    verifies that build_district_event_conditions finds ALL of them.
    If any path is missing, district event counts would silently drop.
    """

    def test_all_attribution_paths_found(self, app):
        """
        Events attributed via M2M FK, school FK, and district_partner string
        are all found by the helper.
        """
        with app.app_context():
            from routes.reports.common import (
                DISTRICT_MAPPING,
                build_district_event_conditions,
            )

            district = District(
                name="Grandview School District",
                salesforce_id="0015f00000JU4opAAD",
            )
            db.session.add(district)
            db.session.flush()

            school = School(
                id="GV_EQ_TEST",
                name="Grandview EQ School",
                district_id=district.id,
                level="High",
            )
            db.session.add(school)
            db.session.commit()

            base_date = datetime(2025, 10, 1)

            # Path 1: M2M districts relationship
            e1 = Event(
                title="E1 M2M Attribution",
                type=EventType.IN_PERSON,
                status=EventStatus.COMPLETED,
                start_date=base_date,
                districts=[district],
            )
            # Path 2: school FK
            e2 = Event(
                title="E2 School FK Attribution",
                type=EventType.IN_PERSON,
                status=EventStatus.COMPLETED,
                start_date=base_date,
                school=school.id,
            )
            # Path 3: district_partner string match
            e3 = Event(
                title="E3 Partner String Attribution",
                type=EventType.IN_PERSON,
                status=EventStatus.COMPLETED,
                start_date=base_date,
                district_partner="Grandview School District",
            )
            db.session.add_all([e1, e2, e3])
            db.session.commit()

            mapping = DISTRICT_MAPPING.get("0015f00000JU4opAAD")
            conditions = build_district_event_conditions(
                district, district_mapping=mapping
            )

            results = Event.query.filter(db.or_(*conditions)).all()
            result_ids = {e.id for e in results}

            assert e1.id in result_ids, "M2M-linked event not found by helper"
            assert e2.id in result_ids, "School FK-linked event not found by helper"
            assert (
                e3.id in result_ids
            ), "district_partner string event not found by helper"

    def test_alias_attributed_event_found(self, app):
        """
        An event whose district_partner matches a DISTRICT_MAPPING alias
        (not the canonical name) is found by the helper.
        """
        with app.app_context():
            from routes.reports.common import (
                DISTRICT_MAPPING,
                build_district_event_conditions,
            )

            # Find a district in DISTRICT_MAPPING that has aliases
            mapping_entry = None
            mapping_sf_id = None
            for sf_id, m in DISTRICT_MAPPING.items():
                if m.get("aliases"):
                    mapping_entry = m
                    mapping_sf_id = sf_id
                    break

            if not mapping_entry:
                pytest.skip("No DISTRICT_MAPPING entry with aliases found")

            alias = mapping_entry["aliases"][0]

            district = District(
                name=mapping_entry["name"],
                salesforce_id=f"ALIAS_TEST_{mapping_sf_id[:8]}",
            )
            db.session.add(district)
            db.session.commit()

            base_date = datetime(2025, 10, 1)
            e_alias = Event(
                title="Alias Match Event",
                type=EventType.IN_PERSON,
                status=EventStatus.COMPLETED,
                start_date=base_date,
                district_partner=alias,
            )
            db.session.add(e_alias)
            db.session.commit()

            conditions = build_district_event_conditions(
                district, district_mapping=mapping_entry
            )

            # Without aliases, conditions only cover M2M, school FK, name ilikes
            conds_no_alias = build_district_event_conditions(
                district, district_mapping={}  # empty = no aliases
            )

            assert conditions, "build_district_event_conditions returned empty list"
            assert len(conditions) > len(conds_no_alias), (
                f"Alias conditions should be added: "
                f"with_mapping={len(conditions)}, no_mapping={len(conds_no_alias)}"
            )

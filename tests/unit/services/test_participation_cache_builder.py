"""
Unit tests for build_participation_caches() in services.salesforce.utils.

Verifies that the returned dicts contain correct SF ID -> local ID mappings
and that the function handles edge cases (missing SF IDs, empty DB) without error.
"""

import pytest

from models import db
from models.event import Event, EventStatus, EventType
from models.volunteer import Volunteer


class TestBuildParticipationCaches:
    """Tests for the build_participation_caches() utility (D-2)."""

    def test_returns_tuple_of_two_dicts(self, app):
        """Return type is a 2-tuple of dicts."""
        with app.app_context():
            from services.salesforce.utils import build_participation_caches

            result = build_participation_caches()
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], dict)
            assert isinstance(result[1], dict)

    def test_volunteers_cache_maps_sf_id_to_local_id(self, app):
        """volunteers_cache maps salesforce_individual_id -> volunteer.id."""
        with app.app_context():
            vol = Volunteer(
                first_name="Cache",
                last_name="Test",
                salesforce_individual_id="003CACHE_VOL_001",
            )
            db.session.add(vol)
            db.session.commit()

            from services.salesforce.utils import build_participation_caches

            vol_cache, _ = build_participation_caches()

            assert "003CACHE_VOL_001" in vol_cache
            assert vol_cache["003CACHE_VOL_001"] == vol.id

    def test_events_cache_maps_sf_id_to_local_id(self, app):
        """events_cache maps salesforce_id -> event.id."""
        with app.app_context():
            from datetime import datetime

            event = Event(
                title="Cache Test Event",
                type=EventType.IN_PERSON,
                status=EventStatus.DRAFT,
                salesforce_id="SF_CACHE_EVT_001",
                start_date=datetime(2025, 1, 1),
            )
            db.session.add(event)
            db.session.commit()

            from services.salesforce.utils import build_participation_caches

            _, evt_cache = build_participation_caches()

            assert "SF_CACHE_EVT_001" in evt_cache
            assert evt_cache["SF_CACHE_EVT_001"] == event.id

    def test_volunteer_without_sf_id_excluded(self, app):
        """Volunteers without salesforce_individual_id are not in the cache."""
        with app.app_context():
            vol = Volunteer(
                first_name="No",
                last_name="SF",
                salesforce_individual_id=None,
            )
            db.session.add(vol)
            db.session.commit()

            from services.salesforce.utils import build_participation_caches

            vol_cache, _ = build_participation_caches()
            assert None not in vol_cache

    def test_multiple_volunteers_all_cached(self, app):
        """Multiple volunteers with SF IDs are all present in the cache."""
        with app.app_context():
            ids = [f"003MULTI_CACHE_{i:03d}" for i in range(5)]
            vols = [
                Volunteer(
                    first_name=f"Multi{i}",
                    last_name="Cache",
                    salesforce_individual_id=ids[i],
                )
                for i in range(5)
            ]
            db.session.add_all(vols)
            db.session.commit()

            from services.salesforce.utils import build_participation_caches

            vol_cache, _ = build_participation_caches()

            for sf_id in ids:
                assert sf_id in vol_cache

    def test_empty_db_returns_no_error(self, app):
        """Empty database returns dicts without raising exceptions."""
        with app.app_context():
            from services.salesforce.utils import build_participation_caches

            vol_cache, evt_cache = build_participation_caches()
            assert isinstance(vol_cache, dict)
            assert isinstance(evt_cache, dict)

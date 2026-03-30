"""
Unit tests for services/cache_service.py

Tests cover cache CRUD operations for VirtualSessionReportCache
and VirtualSessionDistrictCache models.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from models import db
from models.reports import VirtualSessionDistrictCache, VirtualSessionReportCache
from services.cache_service import (
    get_virtual_session_cache,
    get_virtual_session_district_cache,
    invalidate_virtual_session_caches,
    save_virtual_session_cache,
    save_virtual_session_district_cache,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_caches(app):
    """Clean up cache tables before/after each test."""
    yield
    with app.app_context():
        VirtualSessionReportCache.query.delete()
        VirtualSessionDistrictCache.query.delete()
        db.session.commit()


# ── save / get virtual session cache ──────────────────────────────────


class TestVirtualSessionReportCache:

    def test_save_creates_new_record(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)
            save_virtual_session_cache(
                virtual_year="24-25",
                date_from=date_from,
                date_to=date_to,
                session_data={"sessions": []},
                district_summaries={"KCKPS": {}},
                overall_summary={"total": 10},
                filter_options={"years": ["24-25"]},
            )
            record = VirtualSessionReportCache.query.filter_by(
                virtual_year="24-25"
            ).first()
            assert record is not None
            assert record.session_data == {"sessions": []}

    def test_save_updates_existing_record(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)

            # First save
            save_virtual_session_cache(
                "24-25", date_from, date_to, {"v": 1}, {}, {}, {}
            )

            # Second save (update)
            save_virtual_session_cache(
                "24-25", date_from, date_to, {"v": 2}, {}, {}, {}
            )

            records = VirtualSessionReportCache.query.filter_by(
                virtual_year="24-25"
            ).all()
            assert len(records) == 1
            assert records[0].session_data == {"v": 2}

    def test_get_returns_valid_cache(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)
            save_virtual_session_cache(
                "24-25", date_from, date_to, {"cached": True}, {}, {}, {}
            )

            # Patch is_cache_valid to always return True for this test
            with patch("services.cache_service.is_cache_valid", return_value=True):
                result = get_virtual_session_cache("24-25", date_from, date_to)
                assert result is not None
                assert result.session_data == {"cached": True}

    def test_get_returns_none_for_expired(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)
            save_virtual_session_cache("24-25", date_from, date_to, {}, {}, {}, {})

            with patch("services.cache_service.is_cache_valid", return_value=False):
                result = get_virtual_session_cache("24-25", date_from, date_to)
                assert result is None

    def test_get_returns_none_when_no_record(self, app):
        with app.app_context():
            with patch("services.cache_service.is_cache_valid", return_value=True):
                result = get_virtual_session_cache(
                    "99-00", datetime(2099, 1, 1), datetime(2100, 1, 1)
                )
                assert result is None


# ── save / get virtual session district cache ─────────────────────────


class TestVirtualSessionDistrictCache:

    def test_save_creates_new_district_record(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)
            save_virtual_session_district_cache(
                district_name="KCKPS",
                virtual_year="24-25",
                date_from=date_from,
                date_to=date_to,
                session_data={"sessions": []},
                monthly_stats={},
                school_breakdown={},
                teacher_breakdown={},
                summary_stats={"total": 5},
            )
            record = VirtualSessionDistrictCache.query.filter_by(
                district_name="KCKPS", virtual_year="24-25"
            ).first()
            assert record is not None
            assert record.summary_stats == {"total": 5}

    def test_save_updates_existing_district_record(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)

            save_virtual_session_district_cache(
                "KCKPS", "24-25", date_from, date_to, {"v": 1}, {}, {}, {}, {}
            )
            save_virtual_session_district_cache(
                "KCKPS", "24-25", date_from, date_to, {"v": 2}, {}, {}, {}, {}
            )

            records = VirtualSessionDistrictCache.query.filter_by(
                district_name="KCKPS", virtual_year="24-25"
            ).all()
            assert len(records) == 1
            assert records[0].session_data == {"v": 2}

    def test_get_returns_valid_district_cache(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)
            save_virtual_session_district_cache(
                "KCKPS", "24-25", date_from, date_to, {"d": True}, {}, {}, {}, {}
            )
            with patch("services.cache_service.is_cache_valid", return_value=True):
                result = get_virtual_session_district_cache(
                    "KCKPS", "24-25", date_from, date_to
                )
                assert result is not None
                assert result.session_data == {"d": True}


# ── invalidate_virtual_session_caches ─────────────────────────────────


class TestInvalidateVirtualSessionCaches:

    def test_invalidate_specific_year(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)

            save_virtual_session_cache("24-25", date_from, date_to, {}, {}, {}, {})
            save_virtual_session_cache("23-24", date_from, date_to, {}, {}, {}, {})

            invalidate_virtual_session_caches("24-25")

            remaining = VirtualSessionReportCache.query.all()
            assert len(remaining) == 1
            assert remaining[0].virtual_year == "23-24"

    def test_invalidate_all_years(self, app):
        with app.app_context():
            date_from = datetime(2025, 6, 1)
            date_to = datetime(2026, 5, 31)

            save_virtual_session_cache("24-25", date_from, date_to, {}, {}, {}, {})
            save_virtual_session_cache("23-24", date_from, date_to, {}, {}, {}, {})

            invalidate_virtual_session_caches()

            assert VirtualSessionReportCache.query.count() == 0

    def test_invalidate_nonexistent_year_is_safe(self, app):
        with app.app_context():
            # Should not raise
            invalidate_virtual_session_caches("99-00")

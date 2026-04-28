from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.sync_log import SyncLog, SyncStatus
from services.salesforce.delta_sync import (
    DeltaSyncHelper,
    create_sync_log_with_watermark,
)


@pytest.fixture
def clean_sync_logs(app):
    """Fixture to ensure a clean sync_logs table for testing."""
    with app.app_context():
        SyncLog.query.delete()
        db.session.commit()
        yield
        SyncLog.query.delete()
        db.session.commit()


def test_get_watermark_no_previous_runs(clean_sync_logs, app):
    """Scenario 1: get_watermark() with no previous runs returns None."""
    with app.app_context():
        helper = DeltaSyncHelper("test_sync")
        assert helper.get_watermark() is None


def test_get_watermark_after_success(clean_sync_logs, app):
    """Scenario 2: get_watermark() after a SUCCESS run returns watermark - 1hr buffer."""
    with app.app_context():
        # Create a successful sync log 2 hours ago
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        log = create_sync_log_with_watermark(
            sync_type="test_sync", started_at=base_time, status=SyncStatus.SUCCESS.value
        )
        # Manually backdate the watermark for testing
        log.last_sync_watermark = base_time
        db.session.add(log)
        db.session.commit()

        helper = DeltaSyncHelper("test_sync")
        watermark = helper.get_watermark()

        # Should be base_time minus 1 hour (DEFAULT_BUFFER_HOURS)
        expected = base_time - timedelta(hours=1)
        assert watermark is not None
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert abs((watermark - expected).total_seconds()) < 1


def test_get_watermark_after_partial(clean_sync_logs, app):
    """Scenario 3: get_watermark() after a PARTIAL run returns watermark - 1hr buffer."""
    with app.app_context():
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        log = create_sync_log_with_watermark(
            sync_type="test_sync", started_at=base_time, status=SyncStatus.PARTIAL.value
        )
        log.last_sync_watermark = base_time
        db.session.add(log)
        db.session.commit()

        helper = DeltaSyncHelper("test_sync")
        watermark = helper.get_watermark()

        expected = base_time - timedelta(hours=1)
        assert watermark is not None
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert abs((watermark - expected).total_seconds()) < 1


def test_get_watermark_after_failed(clean_sync_logs, app):
    """Scenario 4: get_watermark() after a FAILED run returns watermark - 48hr buffer."""
    with app.app_context():
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        # create_sync_log_with_watermark handles the 48 logic in A2
        log = create_sync_log_with_watermark(
            sync_type="test_sync", started_at=base_time, status=SyncStatus.FAILED.value
        )
        log.last_sync_watermark = base_time
        db.session.add(log)
        db.session.commit()

        helper = DeltaSyncHelper("test_sync")
        watermark = helper.get_watermark()

        # Should use FAILED_SYNC_BUFFER_HOURS (48)
        expected = base_time - timedelta(hours=48)
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert watermark is not None
        assert abs((watermark - expected).total_seconds()) < 1


def test_create_sync_log_with_watermark_failed(clean_sync_logs, app):
    """Scenario 5: create_sync_log_with_watermark() with status='failed'."""
    with app.app_context():
        log = create_sync_log_with_watermark(
            sync_type="test_sync",
            started_at=datetime.now(timezone.utc),
            status=SyncStatus.FAILED.value,
        )

        assert log.last_sync_watermark is not None
        assert log.recovery_buffer_hours == 48


def test_get_watermark_failed_then_success(clean_sync_logs, app):
    """Scenario 6: After failed + new success run, buffer reverts to 1hr."""
    with app.app_context():
        base_time1 = datetime.now(timezone.utc) - timedelta(hours=10)
        base_time2 = datetime.now(timezone.utc) - timedelta(hours=2)

        # First failed run
        log1 = create_sync_log_with_watermark(
            sync_type="test_sync", started_at=base_time1, status=SyncStatus.FAILED.value
        )
        log1.last_sync_watermark = base_time1
        db.session.add(log1)
        db.session.commit()

        # Then successful run
        log2 = create_sync_log_with_watermark(
            sync_type="test_sync",
            started_at=base_time2,
            status=SyncStatus.SUCCESS.value,
        )
        log2.last_sync_watermark = base_time2
        db.session.add(log2)
        db.session.commit()

        helper = DeltaSyncHelper("test_sync")
        watermark = helper.get_watermark()

        # Should be base_time2 minus 1 hour (since the MOST RECENT run was success)
        expected = base_time2 - timedelta(hours=1)
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert watermark is not None
        assert abs((watermark - expected).total_seconds()) < 1

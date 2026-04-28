from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.sync_log import SyncLog, SyncStatus


@pytest.fixture
def clean_sync_logs(app):
    """Fixture to ensure a clean sync_logs table for testing."""
    with app.app_context():
        SyncLog.query.delete()
        db.session.commit()
        yield
        SyncLog.query.delete()
        db.session.commit()


def test_get_watermark_with_buffer_empty(clean_sync_logs, app):
    """When no logs exist, returns (None, 1)."""
    with app.app_context():
        watermark, buffer = SyncLog.get_watermark_with_buffer("test_sync")
        assert watermark is None
        assert buffer == 1


def test_get_watermark_with_buffer_success(clean_sync_logs, app):
    """When last log is success, returns its watermark and buffer=1."""
    with app.app_context():
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        log = SyncLog(
            sync_type="test_sync",
            started_at=base_time,
            status=SyncStatus.SUCCESS.value,
            last_sync_watermark=base_time,
            recovery_buffer_hours=1,
        )
        db.session.add(log)
        db.session.commit()

        watermark, buffer = SyncLog.get_watermark_with_buffer("test_sync")
        assert watermark is not None
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert abs((watermark - base_time).total_seconds()) < 1
        assert buffer == 1


def test_get_watermark_with_buffer_failure(clean_sync_logs, app):
    """When last log is failure, returns its watermark and its recovery buffer."""
    with app.app_context():
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        log = SyncLog(
            sync_type="test_sync",
            started_at=base_time,
            status=SyncStatus.FAILED.value,
            last_sync_watermark=base_time,
            recovery_buffer_hours=48,
        )
        db.session.add(log)
        db.session.commit()

        watermark, buffer = SyncLog.get_watermark_with_buffer("test_sync")
        assert watermark is not None
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert abs((watermark - base_time).total_seconds()) < 1
        assert buffer == 48


def test_get_watermark_with_buffer_ignores_null_watermarks(clean_sync_logs, app):
    """Should skip logs where last_sync_watermark is None."""
    with app.app_context():
        time1 = datetime.now(timezone.utc) - timedelta(hours=2)
        time2 = datetime.now(timezone.utc) - timedelta(hours=1)

        # Older log with watermark
        log1 = SyncLog(
            sync_type="test_sync",
            started_at=time1,
            status=SyncStatus.SUCCESS.value,
            last_sync_watermark=time1,
            recovery_buffer_hours=1,
        )
        # Newer log with NO watermark
        log2 = SyncLog(
            sync_type="test_sync",
            started_at=time2,
            status=SyncStatus.FAILED.value,
            last_sync_watermark=None,
            recovery_buffer_hours=48,
        )
        db.session.add_all([log1, log2])
        db.session.commit()

        watermark, buffer = SyncLog.get_watermark_with_buffer("test_sync")

        # Should return the data from log1
        assert watermark is not None
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        assert abs((watermark - time1).total_seconds()) < 1
        assert buffer == 1

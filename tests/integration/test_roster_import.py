"""
Integration Tests for Roster Import (TC-030, TC-031)
===================================================

Verifies the safe merge/upsert strategy for importing teacher rosters.
"""

from datetime import datetime

import pytest

from models import db
from models.roster_import_log import RosterImportLog
from models.teacher_progress import TeacherProgress
from utils.roster_import import import_roster


@pytest.fixture
def clean_db():
    """Clean up TeacherProgress and RosterImportLog tables."""
    TeacherProgress.query.delete()
    RosterImportLog.query.delete()
    db.session.commit()
    yield
    db.session.rollback()


def test_new_teacher_import_tc030(app, clean_db):
    """TC-030: New teacher appears with Not Started status."""
    with app.app_context():
        # Setup import data
        roster_data = [
            {
                "building": "School A",
                "name": "New Teacher",
                "email": "new@test.com",
                "grade": "K",
                "is_active": True,
            }
        ]

        # Run import
        log = import_roster(
            district_name="Test District",
            academic_year="2025-2026",
            teacher_data=roster_data,
            user_id=1,
        )

        # Verify log
        assert log.status == "success"
        assert log.records_added == 1

        # Verify record created
        teacher = TeacherProgress.query.filter_by(email="new@test.com").first()
        assert teacher is not None
        assert teacher.name == "New Teacher"
        assert teacher.is_active is True

        # Verify status defaults
        status = teacher.get_progress_status(0, 0)
        assert status["status"] == "not_started"


def test_removed_teacher_soft_delete_tc031(app, clean_db):
    """TC-031: Removed teacher behavior (Soft Delete)."""
    with app.app_context():
        # 1. Initial Import
        roster_data_1 = [
            {
                "building": "School A",
                "name": "Stay Teacher",
                "email": "stay@test.com",
                "grade": "1",
                "is_active": True,
            },
            {
                "building": "School A",
                "name": "Remove Teacher",
                "email": "remove@test.com",
                "grade": "2",
                "is_active": True,
            },
        ]
        import_roster("Test District", "2025-2026", roster_data_1, 1)

        # Verify both exist
        assert TeacherProgress.query.count() == 2

        # 2. Second Import (Remove one)
        roster_data_2 = [
            {
                "building": "School A",
                "name": "Stay Teacher",
                "email": "stay@test.com",
                "grade": "1",
                "is_active": True,
            }
        ]
        log = import_roster("Test District", "2025-2026", roster_data_2, 1)

        # Verify log
        assert log.records_deactivated == 1
        assert log.records_updated == 1  # The 'stay' teacher is strictly an update

        # Verify "Remove Teacher" is soft deleted (is_active=False)
        removed_teacher = TeacherProgress.query.filter_by(
            email="remove@test.com"
        ).first()
        assert removed_teacher.is_active is False

        # Verify "Stay Teacher" is still active
        stay_teacher = TeacherProgress.query.filter_by(email="stay@test.com").first()
        assert stay_teacher.is_active is True


def test_roster_update_merge(app, clean_db):
    """Verify updates to existing records (Merge)."""
    with app.app_context():
        # 1. Initial Import
        roster_data = [
            {
                "building": "School A",
                "name": "Old Name",
                "email": "update@test.com",
                "grade": "1",
                "is_active": True,
            }
        ]
        import_roster("Test District", "2025-2026", roster_data, 1)

        # 2. Update Import
        roster_data_update = [
            {
                "building": "New School",
                "name": "New Name",
                "email": "update@test.com",
                "grade": "2",
                "is_active": True,
            }
        ]
        log = import_roster("Test District", "2025-2026", roster_data_update, 1)

        # Verify log
        assert log.records_updated == 1
        assert log.records_added == 0

        # Verify update
        teacher = TeacherProgress.query.filter_by(email="update@test.com").first()
        assert teacher.name == "New Name"
        assert teacher.building == "New School"
        assert teacher.grade == "2"

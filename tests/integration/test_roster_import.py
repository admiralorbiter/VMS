"""
Integration Tests for Roster Import (TC-030, TC-031)
===================================================

Verifies the safe merge/upsert strategy for importing teacher rosters.
"""

from datetime import datetime

import pytest

from models import db
from models.audit_log import AuditLog
from models.roster_import_log import RosterImportLog
from models.teacher_progress import DeactivationSource, TeacherProgress
from models.tenant import Tenant
from models.user import User
from utils.roster_import import import_roster


@pytest.fixture
def clean_db():
    """Clean up TeacherProgress and RosterImportLog tables."""
    TeacherProgress.query.delete()
    RosterImportLog.query.delete()
    # Ensure no lingering data affects tests
    db.session.commit()
    yield
    db.session.rollback()


def test_new_teacher_import_tc030(app, clean_db, test_admin):
    """TC-030: New teacher appears with Not Started status."""
    print(f"DEBUG: Using Admin ID: {test_admin.id}")
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
            user_id=test_admin.id,
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


def test_removed_teacher_soft_delete_tc031(app, clean_db, test_admin):
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
        import_roster("Test District", "2025-2026", roster_data_1, test_admin.id)

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
        log = import_roster("Test District", "2025-2026", roster_data_2, test_admin.id)

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


def test_roster_update_merge(app, clean_db, test_admin):
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
        import_roster("Test District", "2025-2026", roster_data, test_admin.id)

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
        log = import_roster(
            "Test District", "2025-2026", roster_data_update, test_admin.id
        )

        # Verify log
        assert log.records_updated == 1
        assert log.records_added == 0

        # Verify update
        teacher = TeacherProgress.query.filter_by(email="update@test.com").first()
        assert teacher.name == "New Name"
        assert teacher.building == "New School"
        assert teacher.grade == "2"


def test_manual_deactivation_sets_flag(client, app, clean_db, test_admin_headers):
    """Sprint 1: Manual deactivation sets deactivation_source=MANUAL_ADMIN."""
    with app.app_context():
        tenant = Tenant(name="Test Tenant", slug="test-tenant", is_active=True)
        db.session.add(tenant)
        db.session.commit()

        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School",
            name="Manual Remove",
            email="manual@test.com",
        )
        tp.tenant_id = tenant.id
        tp.is_active = True
        db.session.add(tp)
        db.session.commit()
        tp_id = tp.id
        t_id = tenant.id

    # Add tenant_id to the request args so require_tenant_context works
    response = client.post(
        f"/district/teacher-import/teachers/{tp_id}/deactivate?tenant_id={t_id}",
        data={"reason": "Left district", "notes": "Test notes"},
        headers=test_admin_headers,
    )
    assert response.status_code == 200

    with app.app_context():
        tp_after = db.session.get(TeacherProgress, tp_id)
        assert tp_after.is_active is False
        assert tp_after.deactivation_source == DeactivationSource.MANUAL_ADMIN
        assert tp_after.deactivation_reason == "Left district"
        assert tp_after.deactivation_notes == "Test notes"
        assert tp_after.deactivated_at is not None


def test_manual_deactivation_writes_audit_log(
    client, app, clean_db, test_admin_headers
):
    """Sprint 1: Deactivation always writes an AuditLog entry."""
    with app.app_context():
        tenant = Tenant(name="Test Tenant", slug="test-tenant", is_active=True)
        db.session.add(tenant)
        db.session.commit()

        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School",
            name="Audit Teacher",
            email="audit@test.com",
        )
        tp.tenant_id = tenant.id
        db.session.add(tp)
        db.session.commit()
        tp_id = tp.id
        t_id = tenant.id

    client.post(
        f"/district/teacher-import/teachers/{tp_id}/deactivate?tenant_id={t_id}",
        data={"reason": "Retired"},
        headers=test_admin_headers,
    )

    with app.app_context():
        audit = AuditLog.query.filter_by(action="teacher_deactivated").first()
        assert audit is not None
        assert audit.resource_type == "teacher_progress"
        assert audit.resource_id == str(tp_id)
        assert audit.meta["reason"] == "Retired"
        assert audit.meta["source"] == "manual_admin"


def test_deactivation_reason_required(client, app, clean_db, test_admin_headers):
    """Sprint 1: Invalid reason returns 400."""
    with app.app_context():
        tenant = Tenant(name="Test Tenant", slug="test-tenant", is_active=True)
        db.session.add(tenant)
        db.session.commit()

        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School",
            name="Bad Reason",
            email="bad@test.com",
        )
        tp.tenant_id = tenant.id
        db.session.add(tp)
        db.session.commit()
        tp_id = tp.id
        t_id = tenant.id

    response = client.post(
        f"/district/teacher-import/teachers/{tp_id}/deactivate?tenant_id={t_id}",
        data={"reason": "Garbage"},  # Not in DEACTIVATION_REASONS
        headers=test_admin_headers,
    )
    assert response.status_code == 400

    with app.app_context():
        tp_after = db.session.get(TeacherProgress, tp_id)
        assert tp_after.is_active is True  # Not deactivated


def test_import_skips_reactivation_of_manual_deactivated_teachers(
    app, clean_db, test_admin
):
    """Sprint 3: Import does not re-activate MANUAL_ADMIN records."""
    with app.app_context():
        # Setup: Manually deactivated teacher
        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School",
            name="Protected Teacher",
            email="protected@test.com",
        )
        tp.is_active = False
        tp.deactivation_source = DeactivationSource.MANUAL_ADMIN
        tp.deactivated_by = test_admin.id
        tp.deactivation_reason = "Retired"
        tp.district_name = "Test District"
        db.session.add(tp)
        db.session.commit()

        roster_data = [
            {
                "building": "School",
                "name": "Protected Teacher",
                "email": "protected@test.com",
                "grade": "K",
                "is_active": True,
            }
        ]

        log = import_roster("Test District", "2025-2026", roster_data, test_admin.id)

        # Verify
        tp_after = TeacherProgress.query.filter_by(email="protected@test.com").first()
        assert tp_after.is_active is False
        assert log.records_flagged == 1


def test_import_populates_flagged_details_on_skip(app, clean_db, test_admin):
    """Sprint 3: RosterImportLog flagged_details is populated as JSON."""
    with app.app_context():
        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School",
            name="JSON Flag",
            email="json@test.com",
        )
        tp.is_active = False
        tp.deactivation_source = DeactivationSource.MANUAL_ADMIN
        tp.district_name = "Test District"
        db.session.add(tp)
        db.session.commit()

        roster_data = [
            {
                "building": "School",
                "name": "JSON Flag",
                "email": "json@test.com",
                "grade": "1",
            }
        ]

        log = import_roster("Test District", "2025-2026", roster_data, test_admin.id)

        import json

        details = json.loads(log.flagged_details)
        assert len(details) == 1
        assert details[0]["email"] == "json@test.com"
        assert details[0]["reason"] == "Intentional Admin Removal"


def test_import_diff_sets_deactivation_source(app, clean_db, test_admin):
    """Sprint 3: Teachers removed via missing from import get IMPORT_DIFF."""
    with app.app_context():
        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School",
            name="Diff Teacher",
            email="diff@test.com",
        )
        tp.is_active = True
        tp.district_name = "Test District"
        db.session.add(tp)
        db.session.commit()

        # Import empty roster
        import_roster("Test District", "2025-2026", [], test_admin.id)

        tp_after = TeacherProgress.query.filter_by(email="diff@test.com").first()
        assert tp_after.is_active is False
        assert tp_after.deactivation_source == DeactivationSource.IMPORT_DIFF

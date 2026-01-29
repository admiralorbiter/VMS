"""
Integration Tests for Teacher Matching (TC-032, TC-033, TC-034)
==============================================================

Verifies the auto-matching logic and manual matching interface.
"""

import pytest

from models import db
from models.contact import ContactTypeEnum, Email
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from routes.virtual.usage import match_teacher_progress_to_teachers


@pytest.fixture
def clean_db():
    """Clean up TeacherProgress and Teacher tables."""
    # Order matters for foreign keys
    TeacherProgress.query.delete()
    # Delete emails associated with teachers? cascades might handle it if set up,
    # but safe to just rely on transaction rollback from fixture usually.
    # But here we are explicit.
    Email.query.delete()
    Teacher.query.delete()
    db.session.commit()
    yield
    db.session.rollback()


def test_auto_match_email_tc032(app, clean_db):
    """TC-032: Auto-match by email."""
    with app.app_context():
        # 1. Create Teacher
        teacher = Teacher(
            first_name="Jane",
            last_name="Doe",
            school_id="0015f00000TEST123",  # Use a fake ID string
            active=True,
        )
        db.session.add(teacher)
        db.session.commit()  # Commit to get ID

        # Add email
        email = Email(
            contact_id=teacher.id,
            email="jane.doe@example.com",
            type=ContactTypeEnum.professional,
            primary=True,
        )
        db.session.add(email)
        db.session.commit()

        # 2. Create TeacherProgress (exact email match)
        tp = TeacherProgress(
            name="Jane Doe",
            email="jane.doe@example.com",
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Test School",
        )
        db.session.add(tp)
        db.session.commit()

        # 3. Run matching
        stats = match_teacher_progress_to_teachers(virtual_year="2025-2026")

        # 4. Verify match
        assert stats["matched_by_email"] == 1
        assert stats["total_processed"] == 1

        # Reload TP and check relationship
        updated_tp = TeacherProgress.query.filter_by(
            email="jane.doe@example.com"
        ).first()
        assert updated_tp.teacher_id == teacher.id


def test_auto_match_fuzzy_name_tc033(app, clean_db):
    """TC-033: Auto-match by fuzzy name."""
    with app.app_context():
        # 1. Create Teacher
        teacher = Teacher(
            first_name="Robert",
            last_name="Smith",
            school_id="0015f00000TEST456",
            active=True,
        )
        db.session.add(teacher)
        db.session.commit()

        # Add email
        email = Email(
            contact_id=teacher.id,
            email="robert.smith@example.com",
            type=ContactTypeEnum.professional,
            primary=True,
        )
        db.session.add(email)
        db.session.commit()

        # 2. Create TeacherProgress (different email, similar name)
        tp = TeacherProgress(
            name="Robert A. Smith",
            email="rsmith@external.com",  # Different email
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Test School",
        )
        db.session.add(tp)
        db.session.commit()

        # 3. Run matching
        stats = match_teacher_progress_to_teachers(virtual_year="2025-2026")

        # 4. Verify match
        assert stats["matched_by_name"] == 1

        updated_tp = TeacherProgress.query.filter_by(name="Robert A. Smith").first()
        assert updated_tp.teacher_id == teacher.id


def test_manual_match_tc034(client, app, clean_db, test_admin_headers):
    """TC-034: Manual match via API."""
    with app.app_context():
        # 1. Create Teacher and TeacherProgress unmatched
        teacher = Teacher(
            first_name="Manual",
            last_name="Match",
            school_id="0015f00000TEST789",
            active=True,
        )
        db.session.add(teacher)
        db.session.commit()
        teacher_id = teacher.id  # Store ID

        # Add email just to be safe
        email = Email(
            contact_id=teacher_id,
            email="manual.match@example.com",
            type=ContactTypeEnum.professional,
            primary=True,
        )
        db.session.add(email)
        db.session.commit()

        tp = TeacherProgress(
            name="Manual Match TP",
            email="nomatch@example.com",
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Test School",
        )
        db.session.add(tp)
        db.session.commit()
        tp_id = tp.id  # Store ID

        # 2. Call Match API
        url = "/virtual/usage/district/Kansas City Kansas Public Schools/teacher-progress/matching/match"
        payload = {"teacher_progress_id": tp_id, "teacher_id": teacher_id}

        response = client.post(url, json=payload, headers=test_admin_headers)

        # 3. Verify Response
        assert response.status_code == 200
        assert response.json["success"] is True
        assert "Matched" in response.json["message"]

        # 4. Verify DB
        updated_tp = TeacherProgress.query.get(tp_id)
        assert updated_tp.teacher_id == teacher_id

        # 5. Test Unmatch
        payload_unmatch = {"teacher_progress_id": tp_id, "teacher_id": None}
        response = client.post(url, json=payload_unmatch, headers=test_admin_headers)

        assert response.status_code == 200
        assert "Removed match" in response.json["message"]

        updated_tp = TeacherProgress.query.get(tp_id)
        assert updated_tp.teacher_id is None

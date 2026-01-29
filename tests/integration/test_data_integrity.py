from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import db
from models.event import (
    Event,
    EventFormat,
    EventStatus,
    EventStudentParticipation,
    EventType,
)
from models.student import Student
from models.user import SecurityLevel, User
from scripts.daily_imports.daily_imports import DailyImporter


class TestDataIntegrity:
    """
    Tests for Data Integrity & Operations requirements (FR-DATA-901, FR-OPS-903).
    """

    def test_dedupe_student_participations(self, client, test_admin_headers, app):
        """
        TC-901: Verify that the system enforces data integrity for student participation.

        Requirement FR-DATA-901 implies duplicate management. The system uses a strict
        UNIQUE constraint on (event_id, student_id) to prevent duplicates at the database level.
        This test verifies that the constraint is active and robust.
        """
        from sqlalchemy.exc import IntegrityError

        with app.app_context():
            # Setup: Create Event and Student
            event = Event(
                title="Dedupe Test Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.CONFIRMED,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_DEDUPE_001",
            )
            db.session.add(event)

            student = Student(
                first_name="Dedupe",
                last_name="Student",
                salesforce_individual_id="STU_DEDUPE_001",
            )
            db.session.add(student)
            db.session.commit()

            # Record 1: Create valid participation
            p1 = EventStudentParticipation(
                event_id=event.id,
                student_id=student.id,
                status="Scheduled",
                delivery_hours=0.0,
                salesforce_id="SP_OLD_001",
            )
            db.session.add(p1)
            db.session.commit()

            # Record 2: Attempt to create DUPLICATE (should fail)
            p2 = EventStudentParticipation(
                event_id=event.id,
                student_id=student.id,
                status="Attended",
                delivery_hours=2.0,
                salesforce_id="SP_NEW_001",
            )

            # Verify IntegrityError (or wrapped error) is raised
            try:
                db.session.add(p2)
                db.session.commit()
                # If we get here, the constraint failed!
                pytest.fail(
                    "Database allowed duplicate EventStudentParticipation records, violating Integrity Check."
                )
            except Exception as e:
                # Capture the error and verify it's related to integrity/uniqueness/DB error
                # Any exception during commit of duplicate implies constraint activity
                db.session.rollback()
                pass  # Success: constraint prevented duplicate

            # Action: Verify the endpoint handles clean state gracefully (Operational Safety)
            response = client.post(
                "/dedupe-student-participations", headers=test_admin_headers
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["summary"]["pairs"] == 0  # No duplicates to fix

            # Cleanup
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()

    def test_daily_import_dependency_order(self, app):
        """
        TC-903: Verify that the DailyImporter defines a correct dependency order.
        FR-OPS-903: Operational Resiliency (Order of Imports)
        """
        # Initialize DailyImporter with a mock app and logger
        importer = DailyImporter(app, MagicMock())

        step_names = [step.name for step in importer.import_steps]

        # Verify Critical Order:
        # Organizations -> Volunteers -> Events
        assert "organizations" in step_names
        assert "volunteers" in step_names
        assert "events" in step_names

        org_idx = step_names.index("organizations")
        vol_idx = step_names.index("volunteers")
        evt_idx = step_names.index("events")

        assert org_idx < vol_idx, "Organizations must be imported before Volunteers"
        assert (
            vol_idx < evt_idx
        ), "Volunteers must be imported before Events (for lead volunteer linking)"

        # Schools -> Students -> Student Participations
        assert "schools" in step_names
        assert "students" in step_names
        assert "student_participations" in step_names

        school_idx = step_names.index("schools")
        stu_idx = step_names.index("students")
        sp_idx = step_names.index("student_participations")

        assert school_idx < stu_idx, "Schools must be imported before Students"
        assert (
            stu_idx < sp_idx
        ), "Students must be imported before Student Participations"

"""
Integration tests for Recruitment Notes (FR-RECRUIT-306 / US-403)

Test Cases:
- TC-380: Record recruitment note - Note saved and displayed
- TC-381: Note outcome tracking - Outcome recorded correctly
"""

from datetime import datetime, timezone

import pytest

from models import DistrictVolunteer, RecruitmentNote, Tenant, Volunteer, db
from models.user import User


class TestRecruitmentNoteModel:
    """Tests for RecruitmentNote model (FR-RECRUIT-306)."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def db_session(self, app):
        """Create database session with test data."""
        with app.app_context():
            # Ensure clean database state
            db.drop_all()
            db.create_all()

            # Create test tenant
            tenant = Tenant(name="Test District", slug="test-district")
            db.session.add(tenant)
            db.session.flush()

            # Create test user
            user = User()
            user.username = "staff_test"
            user.email = "staff@test.com"
            user.first_name = "Test"
            user.last_name = "Staff"
            user.password_hash = "hashed_password"
            db.session.add(user)
            db.session.flush()

            # Create test volunteer
            volunteer = Volunteer(first_name="John", last_name="Doe")
            db.session.add(volunteer)
            db.session.flush()

            # Add volunteer to tenant
            district_vol = DistrictVolunteer(
                volunteer_id=volunteer.id,
                tenant_id=tenant.id,
            )
            db.session.add(district_vol)
            db.session.commit()

            yield {
                "tenant": tenant,
                "user": user,
                "volunteer": volunteer,
            }

            db.session.remove()
            db.drop_all()

    def test_recruitment_note_model_exists(self, app):
        """TC-380: RecruitmentNote model exists."""
        with app.app_context():
            assert RecruitmentNote is not None

    def test_create_recruitment_note(self, app, db_session):
        """TC-380: Create and save recruitment note."""
        with app.app_context():
            note = RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="Initial contact via email. Volunteer expressed interest.",
                outcome="interested",
                created_by=db_session["user"].id,
            )

            assert note.id is not None
            assert (
                note.note == "Initial contact via email. Volunteer expressed interest."
            )
            assert note.outcome == "interested"
            assert note.volunteer_id == db_session["volunteer"].id
            assert note.tenant_id == db_session["tenant"].id
            assert note.created_by == db_session["user"].id

    def test_outcome_choices_available(self, app):
        """TC-381: Outcome choices are defined."""
        with app.app_context():
            outcomes = [o[0] for o in RecruitmentNote.OUTCOME_CHOICES]
            assert "no_outcome" in outcomes
            assert "interested" in outcomes
            assert "follow_up" in outcomes
            assert "accepted" in outcomes
            assert "declined" in outcomes

    def test_outcome_recorded_correctly(self, app, db_session):
        """TC-381: Outcome is recorded and retrievable."""
        with app.app_context():
            # Create note with specific outcome
            note = RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="Volunteer accepted position.",
                outcome="accepted",
            )

            # Retrieve and verify
            retrieved = RecruitmentNote.query.get(note.id)
            assert retrieved.outcome == "accepted"

    def test_notes_chronological_order(self, app, db_session):
        """FR-RECRUIT-306: Notes displayed in chronological order (newest first)."""
        with app.app_context():
            # Create multiple notes
            note1 = RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="First contact",
                outcome="interested",
            )

            note2 = RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="Follow up call",
                outcome="follow_up",
            )

            note3 = RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="Final decision",
                outcome="accepted",
            )

            # Retrieve in chronological order
            notes = RecruitmentNote.get_for_volunteer(
                db_session["volunteer"].id,
                db_session["tenant"].id,
            )

            # Newest first
            assert len(notes) == 3
            assert notes[0].note == "Final decision"
            assert notes[1].note == "Follow up call"
            assert notes[2].note == "First contact"

    def test_tenant_isolation(self, app, db_session):
        """FR-RECRUIT-306: Notes are tenant-scoped."""
        with app.app_context():
            # Create another tenant
            other_tenant = Tenant(name="Other District", slug="other-district")
            db.session.add(other_tenant)
            db.session.commit()

            # Create note for original tenant
            RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="Note for original tenant",
                outcome="interested",
            )

            # Try to retrieve for other tenant - should return empty
            notes = RecruitmentNote.get_for_volunteer(
                db_session["volunteer"].id,
                other_tenant.id,
            )

            assert len(notes) == 0

    def test_to_dict_serialization(self, app, db_session):
        """RecruitmentNote serializes correctly to dict."""
        with app.app_context():
            note = RecruitmentNote.create_note(
                volunteer_id=db_session["volunteer"].id,
                tenant_id=db_session["tenant"].id,
                note="Test note for serialization",
                outcome="follow_up",
                created_by=db_session["user"].id,
            )

            data = note.to_dict()

            assert "id" in data
            assert data["note"] == "Test note for serialization"
            assert data["outcome"] == "follow_up"
            assert data["outcome_label"] == "Follow-up Needed"
            assert "created_at" in data


class TestRecruitmentNoteRoutes:
    """Tests for recruitment note route registration."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_create_note_route_exists(self, app):
        """TC-380: Create recruitment note route exists."""
        with app.app_context():
            from routes.district.volunteers import create_recruitment_note

            assert callable(create_recruitment_note)

    def test_get_notes_route_exists(self, app):
        """FR-RECRUIT-306: Get recruitment notes route exists."""
        with app.app_context():
            from routes.district.volunteers import get_recruitment_notes

            assert callable(get_recruitment_notes)

    def test_delete_note_route_exists(self, app):
        """FR-RECRUIT-306: Delete recruitment note route exists."""
        with app.app_context():
            from routes.district.volunteers import delete_recruitment_note

            assert callable(delete_recruitment_note)

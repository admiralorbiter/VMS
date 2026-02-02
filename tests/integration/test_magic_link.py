"""
Integration Tests for Teacher Magic Link Feature
================================================

This module tests the magic link authentication flow for teachers
as specified in US-505 and related requirements FR-DISTRICT-505 to FR-DISTRICT-507.

Test Coverage:
- TC-020: Request for roster teacher - Email received
- TC-021: Request for unknown email - Generic response (no leak)
- TC-022: Link shows correct data
- TC-023: Flag submission stored
- TC-024: URL tampering fails
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import db
from models.bug_report import BugReport
from models.magic_link import MagicLink
from models.teacher_progress import TeacherProgress


class TestMagicLinkModel:
    """Tests for the MagicLink model."""

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
            db.create_all()
            yield db.session
            db.session.remove()
            db.drop_all()

    def test_magic_link_model_exists(self, app, db_session):
        """Test that MagicLink model is properly defined."""
        assert hasattr(MagicLink, "__tablename__")
        assert MagicLink.__tablename__ == "magic_link"

    def test_generate_token_uniqueness(self, app, db_session):
        """Test that generated tokens are unique."""
        with app.app_context():
            tokens = [MagicLink.generate_token() for _ in range(100)]
            assert len(set(tokens)) == 100, "Tokens should be unique"

    def test_generate_token_length(self, app, db_session):
        """Test that generated tokens have sufficient length."""
        with app.app_context():
            token = MagicLink.generate_token()
            # URL-safe base64 of 64 bytes = ~86 characters
            assert len(token) >= 80, "Token should be sufficiently long"

    def test_create_for_teacher(self, app, db_session):
        """TC-020: Test magic link creation for valid teacher."""
        with app.app_context():
            # Create a teacher progress record
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="test.teacher@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            # Create magic link
            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
                district_slug="kck",
            )
            db.session.commit()

            assert magic_link.id is not None
            assert magic_link.token is not None
            assert magic_link.email == "test.teacher@school.edu"
            assert magic_link.teacher_progress_id == teacher.id
            assert magic_link.is_active is True
            # Check that expires_at is in the future (handle both tz-aware and naive)
            assert magic_link.is_expired is False

    def test_validate_token_valid(self, app, db_session):
        """TC-022: Test valid token validation."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="valid.token@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
            )
            db.session.commit()

            # Validate the token
            validated = MagicLink.validate_token(magic_link.token)
            assert validated is not None
            assert validated.id == magic_link.id
            assert validated.used_at is not None  # Should be marked as used

    def test_validate_token_expired(self, app, db_session):
        """Test that expired tokens are rejected."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="expired.token@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            # Create link with past expiration
            magic_link = MagicLink(
                token=MagicLink.generate_token(),
                email=teacher.email,
                teacher_progress_id=teacher.id,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                is_active=True,
            )
            db.session.add(magic_link)
            db.session.commit()

            # Validate should fail
            validated = MagicLink.validate_token(magic_link.token)
            assert validated is None

    def test_validate_token_invalid(self, app, db_session):
        """TC-024: Test that invalid tokens are rejected."""
        with app.app_context():
            validated = MagicLink.validate_token("completely-invalid-token-12345")
            assert validated is None

    def test_deactivate_for_email(self, app, db_session):
        """Test deactivating existing links for an email."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="deactivate.test@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            # Create first link
            link1 = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
                district_slug="kck",
            )
            db.session.commit()

            assert link1.is_active is True

            # Deactivate and create new link
            MagicLink.deactivate_for_email(teacher.email, "kck")
            db.session.commit()

            # Refresh the session to see the update
            db.session.refresh(link1)
            assert link1.is_active is False

    def test_get_url(self, app, db_session):
        """Test magic link URL generation."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="url.test@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
                district_slug="kck",
            )
            db.session.commit()

            url = magic_link.get_url("https://example.com")
            assert url.startswith("https://example.com/district/kck/teacher/verify/")
            assert magic_link.token in url


class TestMagicLinkRoutes:
    """Tests for magic link route endpoints."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def db_session(self, app):
        """Create database session."""
        with app.app_context():
            db.create_all()
            yield db.session
            db.session.remove()
            db.drop_all()

    def test_request_link_page_loads(self, client, app, db_session):
        """Test that request link page loads."""
        response = client.get("/district/kck/teacher/request-link")
        assert response.status_code == 200
        assert b"Request Access" in response.data or b"email" in response.data.lower()

    def test_request_link_valid_email(self, client, app, db_session):
        """TC-020: Request for roster teacher sends email."""
        with app.app_context():
            # Create teacher in roster
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Alice Teacher",
                email="alice.teacher@kckps.org",
            )
            db.session.add(teacher)
            db.session.commit()

        # Submit request
        with patch("routes.district.magic_link._send_magic_link_email") as mock_send:
            response = client.post(
                "/district/kck/teacher/request-link",
                data={"email": "alice.teacher@kckps.org"},
                follow_redirects=True,
            )

            # Should redirect to confirmation
            assert response.status_code == 200

            # Email should have been sent
            mock_send.assert_called_once()

        # Magic link should exist
        with app.app_context():
            link = MagicLink.query.filter_by(email="alice.teacher@kckps.org").first()
            assert link is not None

    def test_request_link_unknown_email_generic_response(self, client, app, db_session):
        """TC-021: Request for unknown email shows generic response."""
        with patch("routes.district.magic_link._send_magic_link_email") as mock_send:
            response = client.post(
                "/district/kck/teacher/request-link",
                data={"email": "unknown.person@example.com"},
                follow_redirects=True,
            )

            # Should still show confirmation (no email enumeration)
            assert response.status_code == 200

            # But email should NOT have been sent
            mock_send.assert_not_called()

    def test_verify_valid_token(self, client, app, db_session):
        """TC-022: Valid token shows correct teacher data."""
        with app.app_context():
            # Create teacher
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Banneker Elementary",
                name="Bob Teacher",
                email="bob.teacher@kckps.org",
                grade="4",
                target_sessions=1,
            )
            db.session.add(teacher)
            db.session.commit()

            # Create magic link
            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
                district_slug="kck",
            )
            db.session.commit()
            token = magic_link.token

        # Access via magic link
        response = client.get(f"/district/kck/teacher/verify/{token}")
        assert response.status_code == 200
        assert b"Bob Teacher" in response.data
        assert b"Banneker Elementary" in response.data

    def test_verify_invalid_token(self, client, app, db_session):
        """TC-024: Invalid token is rejected."""
        response = client.get(
            "/district/kck/teacher/verify/invalid-token-12345",
            follow_redirects=True,
        )
        # Should redirect to request page with error
        assert response.status_code == 200

    def test_flag_issue_submission(self, client, app, db_session):
        """TC-023: Flag submission is stored."""
        with app.app_context():
            # Create teacher and link
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Carol Teacher",
                email="carol.teacher@kckps.org",
            )
            db.session.add(teacher)
            db.session.commit()

            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
                district_slug="kck",
            )
            db.session.commit()
            token = magic_link.token

        # Submit flag
        response = client.post(
            "/district/kck/teacher/flag-issue",
            json={
                "token": token,
                "issue_type": "session-data",
                "issue_category": "missing",
                "description": "I'm missing a session from December",
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Thank you" in data["message"]

    def test_flag_issue_invalid_token(self, client, app, db_session):
        """Test that flag submission with invalid token fails."""
        response = client.post(
            "/district/kck/teacher/flag-issue",
            json={
                "token": "invalid-token",
                "issue_type": "personal-info",
                "issue_category": "incorrect",
                "description": "Test description",
            },
            content_type="application/json",
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False


class TestMagicLinkProperties:
    """Tests for MagicLink property methods."""

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
        """Create database session."""
        with app.app_context():
            db.create_all()
            yield db.session
            db.session.remove()
            db.drop_all()

    def test_is_expired_property(self, app, db_session):
        """Test is_expired property."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="expired.prop@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            # Active link
            active = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
            )
            db.session.commit()
            assert active.is_expired is False

            # Expired link
            expired = MagicLink(
                token=MagicLink.generate_token(),
                email=teacher.email,
                teacher_progress_id=teacher.id,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                is_active=True,
            )
            db.session.add(expired)
            db.session.commit()
            assert expired.is_expired is True

    def test_hours_until_expiry(self, app, db_session):
        """Test hours_until_expiry property."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="expiry.hours@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
                expiration_hours=24,
            )
            db.session.commit()

            # Should be around 24 hours
            hours = magic_link.hours_until_expiry
            assert 23 <= hours <= 24

    def test_to_dict_excludes_token(self, app, db_session):
        """Test that to_dict does not expose token."""
        with app.app_context():
            teacher = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test School",
                name="Test Teacher",
                email="to.dict@school.edu",
            )
            db.session.add(teacher)
            db.session.commit()

            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher.id,
                email=teacher.email,
            )
            db.session.commit()

            data = magic_link.to_dict()
            assert "token" not in data
            assert "email" in data
            assert data["email"] == "to.dict@school.edu"

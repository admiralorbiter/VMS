"""
Tests for Teacher Service (Sprint 1)
=====================================

Tests the centralized find_or_create_teacher() function with all
match priority levels: salesforce_id, email, name, and creation.
"""

import pytest

from models import db
from models.contact import Email
from models.teacher import Teacher, TeacherStatus
from services.teacher_service import (
    MatchInfo,
    backfill_primary_emails,
    find_or_create_teacher,
)


class TestFindOrCreateTeacher:
    """Test the find_or_create_teacher() function."""

    def test_create_new_teacher(self, app):
        """When no match exists, a new teacher should be created."""
        with app.app_context():
            teacher, is_new, match_info = find_or_create_teacher(
                first_name="Alice",
                last_name="Newteacher",
                email="alice@school.org",
                import_source="manual",
            )
            db.session.commit()

            assert is_new is True
            assert teacher.id is not None
            assert teacher.first_name == "Alice"
            assert teacher.last_name == "Newteacher"
            assert teacher.cached_email == "alice@school.org"
            assert teacher.import_source == "manual"
            assert teacher.active is True
            assert match_info.method == "created"
            assert match_info.confidence == 1.0

            # Verify Email record was also created
            email_obj = Email.query.filter_by(contact_id=teacher.id).first()
            assert email_obj is not None
            assert email_obj.email == "alice@school.org"
            assert email_obj.primary is True

            # Cleanup
            db.session.delete(teacher)
            db.session.commit()

    def test_match_by_salesforce_id(self, app):
        """Salesforce ID match should be highest priority."""
        with app.app_context():
            # Create existing teacher with SF ID
            existing = Teacher(
                first_name="Bob",
                last_name="Existing",
                salesforce_individual_id="003SFID12345",
                active=True,
            )
            db.session.add(existing)
            db.session.commit()

            # Search with different name but same SF ID
            teacher, is_new, match_info = find_or_create_teacher(
                first_name="Robert",
                last_name="Different",
                salesforce_id="003SFID12345",
            )

            assert is_new is False
            assert teacher.id == existing.id
            assert match_info.method == "salesforce_id"
            assert match_info.confidence == 1.0

            # Cleanup
            db.session.delete(existing)
            db.session.commit()

    def test_match_by_cached_email(self, app):
        """Email match via cached_email should work."""
        with app.app_context():
            existing = Teacher(
                first_name="Carol",
                last_name="Teacher",
                cached_email="carol@school.org",
                active=True,
            )
            db.session.add(existing)
            db.session.commit()

            teacher, is_new, match_info = find_or_create_teacher(
                first_name="Carol",
                last_name="Teacher",
                email="Carol@School.ORG",  # Different case
            )

            assert is_new is False
            assert teacher.id == existing.id
            assert match_info.method == "email"
            assert match_info.confidence == 0.95

            # Cleanup
            db.session.delete(existing)
            db.session.commit()

    def test_match_by_email_model(self, app):
        """Email match via Email model should work when cached_email is empty."""
        with app.app_context():
            existing = Teacher(
                first_name="Dave",
                last_name="Teacher",
                active=True,
            )
            db.session.add(existing)
            db.session.flush()

            # Add Email record but don't set cached_email
            email_obj = Email(
                contact_id=existing.id,
                email="dave@school.org",
                type="personal",
                primary=True,
            )
            db.session.add(email_obj)
            db.session.commit()

            teacher, is_new, match_info = find_or_create_teacher(
                first_name="Dave",
                last_name="Teacher",
                email="dave@school.org",
            )

            assert is_new is False
            assert teacher.id == existing.id
            assert match_info.method == "email"
            assert match_info.confidence == 0.90
            # Should have cached the email for future
            assert teacher.cached_email == "dave@school.org"

            # Cleanup
            db.session.delete(existing)
            db.session.commit()

    def test_match_by_normalized_name(self, app):
        """Name match should work with normalization."""
        with app.app_context():
            existing = Teacher(
                first_name="Eva",
                last_name="O'Brien",
                active=True,
            )
            db.session.add(existing)
            db.session.commit()

            teacher, is_new, match_info = find_or_create_teacher(
                first_name="Eva",
                last_name="Obrien",  # No apostrophe
            )

            assert is_new is False
            assert teacher.id == existing.id
            assert match_info.method == "name"
            assert match_info.confidence >= 0.75

            # Cleanup
            db.session.delete(existing)
            db.session.commit()

    def test_salesforce_id_takes_priority_over_email(self, app):
        """SF ID match should win even if email matches a different teacher."""
        with app.app_context():
            sf_teacher = Teacher(
                first_name="Frank",
                last_name="SF",
                salesforce_individual_id="003SFID99999",
                active=True,
            )
            email_teacher = Teacher(
                first_name="Frank",
                last_name="Email",
                cached_email="frank@school.org",
                active=True,
            )
            db.session.add_all([sf_teacher, email_teacher])
            db.session.commit()

            teacher, is_new, match_info = find_or_create_teacher(
                first_name="Frank",
                last_name="Whoever",
                email="frank@school.org",
                salesforce_id="003SFID99999",
            )

            assert is_new is False
            assert teacher.id == sf_teacher.id
            assert match_info.method == "salesforce_id"

            # Cleanup
            db.session.delete(sf_teacher)
            db.session.delete(email_teacher)
            db.session.commit()

    def test_no_duplicate_creation(self, app):
        """Calling twice with same data should return existing teacher."""
        with app.app_context():
            teacher1, is_new1, _ = find_or_create_teacher(
                first_name="Grace",
                last_name="Single",
                email="grace@school.org",
                import_source="pathful",
            )
            db.session.commit()

            teacher2, is_new2, match_info = find_or_create_teacher(
                first_name="Grace",
                last_name="Single",
                email="grace@school.org",
            )

            assert is_new1 is True
            assert is_new2 is False
            assert teacher1.id == teacher2.id
            assert match_info.method == "email"

            # Cleanup
            db.session.delete(teacher1)
            db.session.commit()

    def test_update_fills_blanks_only(self, app):
        """Matching should fill blank fields but not overwrite existing ones."""
        with app.app_context():
            existing = Teacher(
                first_name="Hank",
                last_name="Teacher",
                cached_email="hank@school.org",
                school_id="SCHOOL_ORIGINAL",
                import_source="salesforce",
                active=True,
            )
            db.session.add(existing)
            db.session.commit()

            teacher, is_new, _ = find_or_create_teacher(
                first_name="Hank",
                last_name="Teacher",
                email="hank@school.org",
                school_id="SCHOOL_NEW",
                import_source="pathful",
            )

            assert is_new is False
            # Existing values should NOT be overwritten
            assert teacher.school_id == "SCHOOL_ORIGINAL"
            assert teacher.import_source == "salesforce"

            # Cleanup
            db.session.delete(existing)
            db.session.commit()

    def test_requires_name(self, app):
        """Should raise ValueError if no name provided."""
        with app.app_context():
            with pytest.raises(ValueError):
                find_or_create_teacher(first_name="", last_name="")


class TestBackfillPrimaryEmails:
    """Test the backfill_primary_emails() function."""

    def test_backfill_from_email_model(self, app):
        """Should populate cached_email from Email records."""
        with app.app_context():
            teacher = Teacher(
                first_name="Ivy",
                last_name="Backfill",
                active=True,
            )
            db.session.add(teacher)
            db.session.flush()

            email = Email(
                contact_id=teacher.id,
                email="ivy@school.org",
                type="personal",
                primary=True,
            )
            db.session.add(email)
            db.session.commit()

            assert teacher.cached_email is None

            stats = backfill_primary_emails()
            db.session.commit()

            # Refresh
            teacher = Teacher.query.get(teacher.id)
            assert teacher.cached_email == "ivy@school.org"
            assert stats["updated"] >= 1

            # Cleanup
            db.session.delete(teacher)
            db.session.commit()

    def test_backfill_skips_existing(self, app):
        """Should not overwrite already-set cached_email."""
        with app.app_context():
            teacher = Teacher(
                first_name="Jack",
                last_name="HasEmail",
                cached_email="jack@existing.org",
                active=True,
            )
            db.session.add(teacher)
            db.session.commit()

            backfill_primary_emails()
            db.session.commit()

            teacher = Teacher.query.get(teacher.id)
            assert teacher.cached_email == "jack@existing.org"

            # Cleanup
            db.session.delete(teacher)
            db.session.commit()


class TestMatchInfo:
    """Test MatchInfo dataclass."""

    def test_repr(self):
        info = MatchInfo(method="email", confidence=0.95, matched_value="test@test.com")
        assert "email" in repr(info)
        assert "0.95" in repr(info)

    def test_fields(self):
        info = MatchInfo(method="created", confidence=1.0)
        assert info.method == "created"
        assert info.confidence == 1.0
        assert info.matched_value is None

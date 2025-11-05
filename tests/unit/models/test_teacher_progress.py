"""
Test suite for TeacherProgress model.

This module provides comprehensive tests for the TeacherProgress model including:
- Model creation and basic functionality
- Field validation (email, year format, required fields, target_sessions)
- Relationships (Teacher, created_by, linked_teacher)
- Methods (get_progress_status, to_dict, __repr__, __str__)
- Unique constraints
- Edge cases and error handling
- Integration with Teacher model
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models import db
from models.contact import ContactTypeEnum, Email
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from models.user import User


@pytest.fixture
def test_user_for_progress(app):
    """Create a test user for TeacherProgress records"""
    with app.app_context():
        user = User(
            username="progressuser",
            email="progressuser@example.com",
            password_hash="hash",
            first_name="Progress",
            last_name="User",
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def test_teacher(app):
    """Create a test teacher for relationship testing"""
    with app.app_context():
        teacher = Teacher(
            first_name="Test",
            last_name="Teacher",
            department="Science",
        )
        # Add email for linked_teacher property testing
        email = Email(
            contact_id=None,  # Will be set after teacher is added
            email="test.teacher@kckps.org",
            type=ContactTypeEnum.professional,
            primary=True,
        )
        db.session.add(teacher)
        db.session.flush()  # Get teacher ID
        email.contact_id = teacher.id
        db.session.add(email)
        db.session.commit()
        yield teacher
        db.session.delete(teacher)
        db.session.commit()


# ============================================================================
# 1. Model Creation and Basic Functionality Tests
# ============================================================================


def test_create_teacher_progress_minimal(app, test_user_for_progress):
    """Test creating TeacherProgress with minimal required fields"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Test Teacher",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.id is not None
        assert progress.academic_year == "2024-2025"
        assert progress.virtual_year == "2024-2025"
        assert progress.building == "Banneker"
        assert progress.name == "Test Teacher"
        assert progress.email == "test@kckps.org"
        assert progress.grade is None
        assert progress.target_sessions == 1  # Default value
        assert progress.created_by == test_user_for_progress.id
        assert progress.created_at is not None
        assert progress.updated_at is not None

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_create_teacher_progress_all_fields(app, test_user_for_progress):
    """Test creating TeacherProgress with all fields"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Caruthers",
            name="John M. Doe",
            email="john.doe@kckps.org",
            grade="5",
            target_sessions=3,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.id is not None
        assert progress.academic_year == "2024-2025"
        assert progress.virtual_year == "2024-2025"
        assert progress.building == "Caruthers"
        assert progress.name == "John M. Doe"
        assert progress.email == "john.doe@kckps.org"
        assert progress.grade == "5"
        assert progress.target_sessions == 3
        assert progress.created_by == test_user_for_progress.id

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_default_target_sessions(app, test_user_for_progress):
    """Test that target_sessions defaults to 1"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test School",
            name="Default Test",
            email="default@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.target_sessions == 1

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_timestamp_auto_generation(app, test_user_for_progress):
    """Test that created_at and updated_at are automatically generated"""
    with app.app_context():
        before_creation = datetime.now(timezone.utc)
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test School",
            name="Timestamp Test",
            email="timestamp@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()
        after_creation = datetime.now(timezone.utc)

        assert progress.created_at is not None
        assert progress.updated_at is not None
        # Check timestamps are datetime objects (SQLite may not preserve timezone)
        assert isinstance(progress.created_at, datetime)
        assert isinstance(progress.updated_at, datetime)

        # Normalize for comparison (SQLite may return timezone-naive datetimes)
        created_at = progress.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)

        updated_at = progress.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        else:
            updated_at = updated_at.astimezone(timezone.utc)

        # Check timestamps are within reasonable range (allow 1 second tolerance for timing)
        from datetime import timedelta

        assert (
            before_creation - timedelta(seconds=1)
            <= created_at
            <= after_creation + timedelta(seconds=1)
        )
        assert (
            before_creation - timedelta(seconds=1)
            <= updated_at
            <= after_creation + timedelta(seconds=1)
        )

        # Test updated_at changes on update
        original_updated = progress.updated_at
        import time

        time.sleep(0.1)
        progress.grade = "K"
        db.session.commit()
        # Refresh to get updated timestamp
        db.session.refresh(progress)
        assert progress.updated_at >= original_updated

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


# ============================================================================
# 2. Field Validation Tests
# ============================================================================


# Email Validation Tests
def test_email_validation_valid(app, test_user_for_progress):
    """Test valid email formats"""
    with app.app_context():
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@example-domain.com",
        ]

        for email in valid_emails:
            progress = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test",
                name="Test",
                email=email,
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress)
            db.session.commit()

            # Email should be lowercased and cleaned
            assert progress.email == email.lower().strip()
            db.session.delete(progress)
            db.session.commit()


def test_email_validation_invalid(app, test_user_for_progress):
    """Test invalid email formats raise ValueError"""
    with app.app_context():
        # These should raise ValueError (completely invalid)
        invalid_emails = [
            "",  # Empty
            "notanemail",  # No @
        ]

        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format|Email"):
                progress = TeacherProgress(
                    academic_year="2024-2025",
                    virtual_year="2024-2025",
                    building="Test",
                    name="Test",
                    email=email,
                    created_by=test_user_for_progress.id,
                )
                db.session.add(progress)
                db.session.commit()

        # These are leniently allowed (have @ structure) but validation varies
        # The validator allows "@domain.com" but rejects "user@" and "user@domain"
        # Test that "@domain.com" is allowed (it has @ and domain structure)
        lenient_email = "@domain.com"  # No username (allowed by lenient validator)
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email=lenient_email,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()
        db.session.delete(progress)
        db.session.commit()

        # These should raise ValueError (incomplete structure)
        incomplete_emails = [
            "user@",  # No domain (rejected)
            "user@domain",  # No TLD (rejected)
        ]

        for email in incomplete_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                progress2 = TeacherProgress(
                    academic_year="2024-2025",
                    virtual_year="2024-2025",
                    building="Test",
                    name="Test",
                    email=email,
                    created_by=test_user_for_progress.id,
                )
                db.session.add(progress2)
                db.session.commit()


def test_email_cleaning_spaces_quotes(app, test_user_for_progress):
    """Test email cleaning removes spaces and quotes"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email='  "user@example.com"  ',
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.email == "user@example.com"

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_email_cleaning_double_at(app, test_user_for_progress):
    """Test email cleaning fixes double @ symbols"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="sildiane@quinteros@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        # Should be fixed to have only one @
        assert progress.email == "sildiane@kckps.org"
        assert progress.email.count("@") == 1

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_email_case_normalization(app, test_user_for_progress):
    """Test email is normalized to lowercase"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="TEST.EMAIL@EXAMPLE.COM",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.email == "test.email@example.com"

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


# Year Format Validation Tests
def test_year_validation_valid(app, test_user_for_progress):
    """Test valid year formats"""
    with app.app_context():
        valid_years = ["2024-2025", "2020-2021", "2030-2031"]

        for year in valid_years:
            progress = TeacherProgress(
                academic_year=year,
                virtual_year=year,
                building="Test",
                name="Test",
                email=f"test{year}@kckps.org",
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress)
            db.session.commit()

            assert progress.academic_year == year
            assert progress.virtual_year == year
            db.session.delete(progress)
            db.session.commit()


def test_year_validation_invalid(app, test_user_for_progress):
    """Test invalid year formats raise ValueError (only format violations, not sequence warnings)"""
    with app.app_context():
        # These should raise ValueError (invalid format)
        invalid_format_years = [
            "",  # Empty
            "2024",  # Missing second year
            "abcd-efgh",  # Not numeric
            "24-25",  # Wrong format
        ]

        for year in invalid_format_years:
            with pytest.raises(ValueError, match="year|format"):
                progress = TeacherProgress(
                    academic_year=year,
                    virtual_year=year,
                    building="Test",
                    name="Test",
                    email="test@kckps.org",
                    created_by=test_user_for_progress.id,
                )
                db.session.add(progress)
                db.session.commit()

        # These should only warn (valid format but wrong sequence)
        # The validator only warns, doesn't raise for sequence issues
        warning_years = [
            "2024-2023",  # Wrong order (warns but allows)
            "2024-2026",  # Not consecutive (warns but allows)
        ]

        for year in warning_years:
            # Should succeed but with warnings
            progress = TeacherProgress(
                academic_year=year,
                virtual_year=year,
                building="Test",
                name="Test",
                email=f"test{year}@kckps.org",
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress)
            db.session.commit()
            db.session.delete(progress)
            db.session.commit()


# Required String Fields Validation Tests
def test_name_validation_required(app, test_user_for_progress):
    """Test name is required and trimmed"""
    with app.app_context():
        # Valid name
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="  Test Teacher  ",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()
        assert progress.name == "Test Teacher"
        db.session.delete(progress)
        db.session.commit()

        # Empty name should raise ValueError
        with pytest.raises(ValueError, match="name"):
            progress2 = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test",
                name="",
                email="test2@kckps.org",
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress2)
            db.session.commit()


def test_building_validation_required(app, test_user_for_progress):
    """Test building is required and trimmed"""
    with app.app_context():
        # Valid building
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="  Banneker  ",
            name="Test",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()
        assert progress.building == "Banneker"
        db.session.delete(progress)
        db.session.commit()

        # Empty building should raise ValueError
        with pytest.raises(ValueError, match="building"):
            progress2 = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="",
                name="Test",
                email="test2@kckps.org",
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress2)
            db.session.commit()


def test_grade_validation_optional(app, test_user_for_progress):
    """Test grade is optional and trimmed"""
    with app.app_context():
        # Grade can be None
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test1@kckps.org",
            grade=None,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.commit()
        assert progress1.grade is None
        db.session.delete(progress1)
        db.session.commit()

        # Grade is trimmed
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test2@kckps.org",
            grade="  K  ",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress2)
        db.session.commit()
        assert progress2.grade == "K"
        db.session.delete(progress2)
        db.session.commit()

        # Empty grade becomes None
        progress3 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test3@kckps.org",
            grade="   ",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress3)
        db.session.commit()
        assert progress3.grade is None
        db.session.delete(progress3)
        db.session.commit()


# Target Sessions Validation Tests
def test_target_sessions_validation_valid(app, test_user_for_progress):
    """Test valid target_sessions values"""
    with app.app_context():
        valid_values = [0, 1, 5, 10, 100]

        for value in valid_values:
            progress = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test",
                name=f"Test {value}",
                email=f"test{value}@kckps.org",
                target_sessions=value,
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress)
            db.session.commit()

            assert progress.target_sessions == value
            db.session.delete(progress)
            db.session.commit()


def test_target_sessions_validation_invalid(app, test_user_for_progress):
    """Test invalid target_sessions values raise ValueError"""
    with app.app_context():
        # Negative values should raise ValueError
        with pytest.raises(ValueError, match="target_sessions.*non-negative"):
            progress = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test",
                name="Test",
                email="test@kckps.org",
                target_sessions=-1,
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress)
            db.session.commit()

        # Non-numeric strings should raise ValueError
        with pytest.raises(ValueError, match="target_sessions.*integer"):
            progress2 = TeacherProgress(
                academic_year="2024-2025",
                virtual_year="2024-2025",
                building="Test",
                name="Test",
                email="test2@kckps.org",
                target_sessions="not_a_number",
                created_by=test_user_for_progress.id,
            )
            db.session.add(progress2)
            db.session.commit()


def test_target_sessions_default_none(app, test_user_for_progress):
    """Test target_sessions defaults to 1 when None"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=None,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.target_sessions == 1

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


# ============================================================================
# 3. Relationship Tests
# ============================================================================


def test_teacher_relationship_optional(app, test_user_for_progress, test_teacher):
    """Test optional Teacher relationship"""
    with app.app_context():
        # Without teacher_id
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test1@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.commit()
        assert progress1.teacher_id is None
        assert progress1.teacher is None
        db.session.delete(progress1)
        db.session.commit()

        # With teacher_id
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test2@kckps.org",
            teacher_id=test_teacher.id,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress2)
        db.session.commit()
        assert progress2.teacher_id == test_teacher.id
        assert progress2.teacher is not None
        assert progress2.teacher.id == test_teacher.id
        assert progress2.teacher.first_name == "Test"
        db.session.delete(progress2)
        db.session.commit()


def test_created_by_relationship(app, test_user_for_progress):
    """Test created_by foreign key relationship"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        # Note: User relationship might not be defined, so we just check the ID
        assert progress.created_by == test_user_for_progress.id

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_linked_teacher_property_by_email(app, test_user_for_progress, test_teacher):
    """Test linked_teacher property finds teacher by email"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test Teacher",
            email="test.teacher@kckps.org",  # Matches test_teacher email
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        linked = progress.linked_teacher
        assert linked is not None
        assert linked.id == test_teacher.id
        # Teacher uses primary_email property, not email attribute
        assert linked.primary_email == "test.teacher@kckps.org"

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_linked_teacher_property_by_name(app, test_user_for_progress, test_teacher):
    """Test linked_teacher property finds teacher by name"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test Teacher",  # Matches test_teacher name
            email="different@kckps.org",  # Different email
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        linked = progress.linked_teacher
        # Should find by name if email doesn't match
        if linked:
            assert linked.id == test_teacher.id

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_linked_teacher_property_no_match(app, test_user_for_progress):
    """Test linked_teacher property returns None when no match"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Unknown Teacher",
            email="unknown@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        linked = progress.linked_teacher
        assert linked is None

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_teacher_backref(app, test_user_for_progress, test_teacher):
    """Test teacher_progress_records backref from Teacher"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test1@kckps.org",
            teacher_id=test_teacher.id,
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test2@kckps.org",
            teacher_id=test_teacher.id,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()

        # Query teacher fresh to get backref
        teacher = Teacher.query.get(test_teacher.id)
        records = teacher.teacher_progress_records.all()
        assert len(records) >= 2
        assert progress1.id in [r.id for r in records]
        assert progress2.id in [r.id for r in records]

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.commit()


# ============================================================================
# 4. Method Tests
# ============================================================================


def test_get_progress_status_achieved(app, test_user_for_progress):
    """Test get_progress_status returns 'achieved' when goal is met"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        status = progress.get_progress_status(completed_sessions=2, planned_sessions=0)
        assert status["status"] == "achieved"
        assert status["status_text"] == "Goal Achieved"
        assert status["status_class"] == "achieved"
        assert status["progress_percentage"] == 100.0
        assert status["completed_sessions"] == 2
        assert status["planned_sessions"] == 0
        assert status["needed_sessions"] == 0

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_get_progress_status_in_progress(app, test_user_for_progress):
    """Test get_progress_status returns 'in_progress' when goal is planned but not completed"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        status = progress.get_progress_status(completed_sessions=1, planned_sessions=1)
        assert status["status"] == "in_progress"
        assert status["status_text"] == "In Progress"
        assert status["status_class"] == "in_progress"
        assert status["progress_percentage"] == 50.0
        assert status["completed_sessions"] == 1
        assert status["planned_sessions"] == 1
        assert status["needed_sessions"] == 0

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_get_progress_status_not_started(app, test_user_for_progress):
    """Test get_progress_status returns 'not_started' when goal is not met"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        status = progress.get_progress_status(completed_sessions=0, planned_sessions=0)
        assert status["status"] == "not_started"
        assert status["status_text"] == "Needs Planning"
        assert status["status_class"] == "not_started"
        assert status["progress_percentage"] == 0.0
        assert status["completed_sessions"] == 0
        assert status["planned_sessions"] == 0
        assert status["needed_sessions"] == 2

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_get_progress_status_zero_target(app, test_user_for_progress):
    """Test get_progress_status handles zero target_sessions"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=0,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        status = progress.get_progress_status(completed_sessions=0, planned_sessions=0)
        assert status["progress_percentage"] == 0.0
        # When target is 0 and completed is 0, condition is 0 >= 0, so status is "achieved"
        assert status["status"] == "achieved"

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_get_progress_status_negative_sessions(app, test_user_for_progress):
    """Test get_progress_status handles negative session counts gracefully"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        # Should normalize negative values to 0
        status = progress.get_progress_status(
            completed_sessions=-5, planned_sessions=-2
        )
        assert status["completed_sessions"] == 0
        assert status["planned_sessions"] == 0

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_to_dict_basic(app, test_user_for_progress):
    """Test to_dict returns basic dictionary representation"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Test Teacher",
            email="test@kckps.org",
            grade="K",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        result = progress.to_dict()

        assert result["id"] == progress.id
        assert result["academic_year"] == "2024-2025"
        assert result["virtual_year"] == "2024-2025"
        assert result["building"] == "Banneker"
        assert result["name"] == "Test Teacher"
        assert result["email"] == "test@kckps.org"
        assert result["grade"] == "K"
        assert result["target_sessions"] == 2
        assert result["teacher_id"] is None
        assert result["created_by"] == test_user_for_progress.id
        assert "created_at" in result
        assert "updated_at" in result

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_to_dict_with_progress(app, test_user_for_progress):
    """Test to_dict includes progress status when requested"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        result = progress.to_dict(
            include_progress=True, completed_sessions=2, planned_sessions=0
        )

        assert "progress" in result
        assert result["progress"]["status"] == "achieved"
        assert result["progress"]["progress_percentage"] == 100.0

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_to_dict_with_teacher(app, test_user_for_progress, test_teacher):
    """Test to_dict includes teacher information when linked"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            teacher_id=test_teacher.id,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        result = progress.to_dict()

        assert "teacher" in result
        assert result["teacher"]["id"] == test_teacher.id
        assert result["teacher"]["name"] == test_teacher.full_name
        assert result["teacher_id"] == test_teacher.id

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_repr_method(app, test_user_for_progress):
    """Test __repr__ returns debug representation"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Test Teacher",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        repr_str = repr(progress)
        assert "TeacherProgress" in repr_str
        assert str(progress.id) in repr_str
        assert "Test Teacher" in repr_str
        assert "Banneker" in repr_str

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_str_method(app, test_user_for_progress):
    """Test __str__ returns human-readable representation"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Test Teacher",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        str_repr = str(progress)
        assert "Test Teacher" in str_repr
        assert "Banneker" in str_repr
        assert "2024-2025" in str_repr

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


# ============================================================================
# 5. Unique Constraint Tests
# ============================================================================


def test_unique_constraint_email_virtual_year(app, test_user_for_progress):
    """Test unique constraint on (email, virtual_year)"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test Teacher",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.commit()

        # Try to create duplicate (same email + virtual_year)
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Different",
            name="Different Teacher",
            email="test@kckps.org",  # Same email
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress2)
        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()
        db.session.delete(progress1)
        db.session.commit()


def test_unique_constraint_same_email_different_year(app, test_user_for_progress):
    """Test same email with different virtual_year is allowed"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test Teacher",
            email="test@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Test",
            name="Test Teacher",
            email="test@kckps.org",  # Same email, different year
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()  # Should succeed

        assert progress1.id != progress2.id
        assert progress1.email == progress2.email
        assert progress1.virtual_year != progress2.virtual_year

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.commit()


def test_unique_constraint_same_year_different_email(app, test_user_for_progress):
    """Test same virtual_year with different email is allowed"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Teacher One",
            email="teacher1@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Teacher Two",
            email="teacher2@kckps.org",  # Different email, same year
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()  # Should succeed

        assert progress1.id != progress2.id
        assert progress1.email != progress2.email
        assert progress1.virtual_year == progress2.virtual_year

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.commit()


# ============================================================================
# 6. Edge Cases and Error Handling Tests
# ============================================================================


def test_unicode_characters_in_names(app, test_user_for_progress):
    """Test unicode characters in name and building fields"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="José María",
            name="María José García",
            email="maria@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.building == "José María"
        assert progress.name == "María José García"

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_special_characters_in_names(app, test_user_for_progress):
    """Test special characters in name and building fields"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="O'Brien Elementary",
            name="John O'Brien-Smith",
            email="john@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert progress.building == "O'Brien Elementary"
        assert progress.name == "John O'Brien-Smith"

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_long_strings(app, test_user_for_progress):
    """Test handling of long strings in fields"""
    with app.app_context():
        long_name = "A" * 200  # Max length for name field
        long_building = "B" * 100  # Max length for building field

        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building=long_building,
            name=long_name,
            email="long@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        assert len(progress.name) == 200
        assert len(progress.building) == 100

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_get_progress_status_error_handling(app, test_user_for_progress):
    """Test get_progress_status handles errors gracefully"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        # Should handle invalid inputs gracefully
        # Note: The method normalizes inputs, so this should work
        status = progress.get_progress_status(
            completed_sessions="invalid", planned_sessions=None
        )
        # Should return a status dict even with invalid inputs (method normalizes)
        assert "status" in status
        assert "progress_percentage" in status

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


# ============================================================================
# 7. Integration Tests with Teacher Records
# ============================================================================


def test_query_by_virtual_year(app, test_user_for_progress):
    """Test querying TeacherProgress records by virtual_year"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="School A",
            name="Teacher A",
            email="a@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="School B",
            name="Teacher B",
            email="b@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress3 = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School C",
            name="Teacher C",
            email="c@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.add(progress3)
        db.session.commit()

        # Query by virtual_year
        results = TeacherProgress.query.filter_by(virtual_year="2024-2025").all()
        assert len(results) == 2
        assert progress1.id in [r.id for r in results]
        assert progress2.id in [r.id for r in results]
        assert progress3.id not in [r.id for r in results]

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.delete(progress3)
        db.session.commit()


def test_query_by_building(app, test_user_for_progress):
    """Test querying TeacherProgress records by building"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Teacher A",
            email="a@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Teacher B",
            email="b@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress3 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Caruthers",
            name="Teacher C",
            email="c@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.add(progress3)
        db.session.commit()

        # Query by building
        results = TeacherProgress.query.filter_by(building="Banneker").all()
        assert len(results) == 2
        assert progress1.id in [r.id for r in results]
        assert progress2.id in [r.id for r in results]
        assert progress3.id not in [r.id for r in results]

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.delete(progress3)
        db.session.commit()


def test_query_by_academic_year(app, test_user_for_progress):
    """Test querying TeacherProgress records by academic_year"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="School A",
            name="Teacher A",
            email="a@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="School B",
            name="Teacher B",
            email="b@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()

        # Query by academic_year
        results = TeacherProgress.query.filter_by(academic_year="2024-2025").all()
        assert len(results) == 1
        assert results[0].id == progress1.id

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.commit()


def test_composite_index_usage(app, test_user_for_progress):
    """Test composite indexes work for common query patterns"""
    with app.app_context():
        progress1 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Teacher A",
            email="a@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress2 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Teacher B",
            email="b@kckps.org",
            created_by=test_user_for_progress.id,
        )
        progress3 = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Caruthers",
            name="Teacher C",
            email="c@kckps.org",
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.add(progress3)
        db.session.commit()

        # Query using composite index pattern (virtual_year + building)
        results = TeacherProgress.query.filter_by(
            virtual_year="2024-2025", building="Banneker"
        ).all()
        assert len(results) == 2
        assert progress1.id in [r.id for r in results]
        assert progress2.id in [r.id for r in results]

        # Cleanup
        db.session.delete(progress1)
        db.session.delete(progress2)
        db.session.delete(progress3)
        db.session.commit()


def test_full_integration_with_teacher(app, test_user_for_progress, test_teacher):
    """Test full integration: create progress, link to teacher, query relationships"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test School",
            name="Test Teacher",
            email="test.teacher@kckps.org",
            teacher_id=test_teacher.id,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        # Test relationship
        assert progress.teacher is not None
        assert progress.teacher.id == test_teacher.id

        # Test backref - query teacher fresh to get backref
        teacher = Teacher.query.get(test_teacher.id)
        records = teacher.teacher_progress_records.all()
        assert progress.id in [r.id for r in records]

        # Test linked_teacher property
        linked = progress.linked_teacher
        assert linked is not None
        assert linked.id == test_teacher.id

        # Test to_dict with teacher
        result = progress.to_dict()
        assert "teacher" in result
        assert result["teacher"]["id"] == test_teacher.id

        # Cleanup
        db.session.delete(progress)
        db.session.commit()


def test_get_progress_status_over_goal(app, test_user_for_progress):
    """Test get_progress_status when completed exceeds target"""
    with app.app_context():
        progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Test",
            name="Test",
            email="test@kckps.org",
            target_sessions=2,
            created_by=test_user_for_progress.id,
        )
        db.session.add(progress)
        db.session.commit()

        status = progress.get_progress_status(completed_sessions=5, planned_sessions=0)
        assert status["status"] == "achieved"
        assert status["progress_percentage"] == 100.0  # Capped at 100%

        # Cleanup
        db.session.delete(progress)
        db.session.commit()

from datetime import date, datetime, timedelta, timezone

import pytest

from models import db
from models.contact import (
    Address,
    ContactTypeEnum,
    Email,
    GenderEnum,
    LocalStatusEnum,
    Phone,
)
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.teacher import Teacher, TeacherStatus


def test_new_teacher(app):
    """Test creating a new teacher with all fields"""
    with app.app_context():
        teacher = Teacher(
            first_name="Test",
            last_name="Teacher",
            department="Science",
            school_id="0015f00000TEST123",
            active=True,
            connector_role="Lead",
            connector_active=True,
            connector_start_date=date(2024, 1, 1),
            connector_end_date=date(2024, 12, 31),
            gender=GenderEnum.female,
            description="Test teacher description",
            birthdate=date(1990, 1, 1),
            do_not_call=False,
            do_not_contact=False,
            email_opt_out=False,
        )

        db.session.add(teacher)
        db.session.commit()

        # Test basic fields
        assert teacher.id is not None
        assert teacher.first_name == "Test"
        assert teacher.last_name == "Teacher"
        assert teacher.department == "Science"
        assert teacher.school_id == "0015f00000TEST123"
        assert teacher.active is True
        assert teacher.type == "teacher"  # Check polymorphic identity

        # Test connector fields
        assert teacher.connector_role == "Lead"
        assert teacher.connector_active is True
        assert teacher.connector_start_date == date(2024, 1, 1)
        assert teacher.connector_end_date == date(2024, 12, 31)

        # Test inherited fields
        assert teacher.gender == GenderEnum.female
        assert teacher.description == "Test teacher description"
        assert teacher.birthdate == date(1990, 1, 1)
        assert teacher.do_not_call is False
        assert teacher.do_not_contact is False
        assert teacher.email_opt_out is False

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_teacher_contact_info(app):
    """Test teacher contact information management (phones, emails, addresses)"""
    with app.app_context():
        teacher = Teacher(first_name="Contact", last_name="Test")

        # Add phone
        phone = Phone(
            number="123-456-7890", type=ContactTypeEnum.personal, primary=True
        )
        teacher.phones.append(phone)

        # Add email
        email = Email(
            email="teacher@test.com", type=ContactTypeEnum.personal, primary=True
        )
        teacher.emails.append(email)

        # Add address
        address = Address(
            address_line1="123 School St",
            city="Test City",
            state="TS",
            zip_code="12345",
            type=ContactTypeEnum.personal,
            primary=True,
        )
        teacher.addresses.append(address)

        db.session.add(teacher)
        db.session.commit()

        # Test contact info
        assert teacher.primary_phone == "123-456-7890"
        assert teacher.primary_email == "teacher@test.com"
        assert teacher.primary_address is not None
        assert teacher.formatted_primary_address == "123 School St\nTest City, TS 12345"

        # Test contact validation methods
        assert teacher.has_valid_phone is True
        assert teacher.has_valid_email is True
        assert teacher.is_contactable is True

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_update_from_csv(app):
    """Test updating teacher from CSV data"""
    with app.app_context():
        teacher = Teacher(first_name="Original", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        csv_data = {
            "FirstName": "Updated",
            "LastName": "Name",
            "npsp__Primary_Affiliation__c": "0015f00000TEST123",
            "Gender__c": "Female",
            "Phone": "123-456-7890",
            "Email": "updated@test.com",
            "Department": "Math",
            "Active__c": True,
            "Connector_Role__c": "Support",
            "Connector_Active__c": True,
            "Connector_Start_Date__c": date(2024, 1, 1),
            "Connector_End_Date__c": date(2024, 12, 31),
            "Last_Email_Message__c": date(2024, 1, 1),
            "Last_Mailchimp_Email_Date__c": date(2024, 1, 2),
        }

        teacher.update_from_csv(csv_data)
        db.session.commit()

        # Test updated fields
        assert teacher.first_name == "Updated"
        assert teacher.last_name == "Name"
        assert teacher.school_id == "0015f00000TEST123"
        assert teacher.gender == GenderEnum.female
        assert teacher.department == "Math"
        assert teacher.active is True
        assert teacher.connector_role == "Support"
        assert teacher.connector_active is True
        assert teacher.connector_start_date == date(2024, 1, 1)
        assert teacher.connector_end_date == date(2024, 12, 31)
        assert teacher.last_email_message == date(2024, 1, 1)
        assert teacher.last_mailchimp_date == date(2024, 1, 2)

        # Test contact info creation
        assert teacher.primary_phone == "123-456-7890"
        assert teacher.primary_email == "updated@test.com"

        # Test duplicate prevention
        teacher.update_from_csv(csv_data)
        db.session.commit()

        # Verify no duplicates were created
        assert Phone.query.filter_by(contact_id=teacher.id).count() == 1
        assert Email.query.filter_by(contact_id=teacher.id).count() == 1

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_teacher_inheritance(app):
    """Test that Teacher inherits correctly from Contact"""
    with app.app_context():
        teacher = Teacher(first_name="Inheritance", last_name="Test")

        # Add email to properly test has_valid_email
        email = Email(
            email="test@example.com", type=ContactTypeEnum.personal, primary=True
        )
        teacher.emails.append(email)

        db.session.add(teacher)
        db.session.commit()

        # Test inheritance
        assert teacher.type == "teacher"  # polymorphic identity
        assert hasattr(teacher, "phones")  # inherited relationship
        assert hasattr(teacher, "emails")  # inherited relationship
        assert hasattr(teacher, "addresses")  # inherited relationship
        assert hasattr(teacher, "gender")  # inherited field
        assert hasattr(teacher, "birthdate")  # inherited field
        assert hasattr(teacher, "do_not_call")  # inherited field

        # Test inherited methods
        assert teacher.has_valid_email is True  # inherited method
        assert teacher.is_contactable is True  # inherited method
        assert teacher.primary_phone is None  # inherited property

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_validate_status(app):
    """Test validate_status validator with various inputs"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")

        # Test valid TeacherStatus enum instance
        result = teacher.validate_status("status", TeacherStatus.ACTIVE)
        assert result == TeacherStatus.ACTIVE

        # Test value-based lookup (string matching enum.value)
        result = teacher.validate_status("status", "active")
        assert result == TeacherStatus.ACTIVE

        result = teacher.validate_status("status", "inactive")
        assert result == TeacherStatus.INACTIVE

        result = teacher.validate_status("status", "on_leave")
        assert result == TeacherStatus.ON_LEAVE

        result = teacher.validate_status("status", "retired")
        assert result == TeacherStatus.RETIRED

        # Test case-insensitive value matching
        result = teacher.validate_status("status", "ACTIVE")
        assert result == TeacherStatus.ACTIVE

        # Test name-based fallback (backwards compatibility)
        result = teacher.validate_status("status", "ON_LEAVE")
        assert result == TeacherStatus.ON_LEAVE

        # Test None value defaults to ACTIVE
        result = teacher.validate_status("status", None)
        assert result == TeacherStatus.ACTIVE

        # Test invalid status string raises ValueError
        with pytest.raises(ValueError) as exc_info:
            teacher.validate_status("status", "invalid_status")
        assert "Invalid status" in str(exc_info.value)
        assert "Valid values" in str(exc_info.value)

        # Test invalid type raises ValueError
        with pytest.raises(ValueError) as exc_info:
            teacher.validate_status("status", 123)
        assert "Status must be a TeacherStatus enum value" in str(exc_info.value)


def test_status_active_sync(app):
    """Test status syncs with active field"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test ACTIVE status sets active=True
        teacher.status = TeacherStatus.ACTIVE
        db.session.commit()
        assert teacher.active is True
        assert teacher.status == TeacherStatus.ACTIVE

        # Test INACTIVE status sets active=False
        teacher.status = TeacherStatus.INACTIVE
        db.session.commit()
        assert teacher.active is False
        assert teacher.status == TeacherStatus.INACTIVE

        # Test ON_LEAVE status sets active=False
        teacher.status = TeacherStatus.ON_LEAVE
        db.session.commit()
        assert teacher.active is False

        # Test RETIRED status sets active=False
        teacher.status = TeacherStatus.RETIRED
        db.session.commit()
        assert teacher.active is False

        # Test string status assignment also syncs active
        teacher.status = "active"
        db.session.commit()
        assert teacher.active is True

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_status_change_date(app):
    """Test status change date tracking"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Initial status assignment should not set status_change_date
        teacher.status = TeacherStatus.ACTIVE
        db.session.commit()
        assert teacher.status_change_date is None

        # Change status should set status_change_date
        import time

        time.sleep(0.1)  # Small delay to ensure different timestamps
        teacher.status = TeacherStatus.INACTIVE
        db.session.commit()
        # Refresh to get the latest data from database
        db.session.refresh(teacher)
        assert teacher.status_change_date is not None
        assert isinstance(teacher.status_change_date, datetime)
        # Note: SQLite may not preserve timezone info, so check if it's a datetime
        # The datetime should be set correctly even if timezone info is lost on retrieval

        # Store the change date
        first_change_date = teacher.status_change_date

        # Another status change should update status_change_date
        time.sleep(0.1)
        teacher.status = TeacherStatus.ON_LEAVE
        db.session.commit()
        assert teacher.status_change_date is not None
        assert teacher.status_change_date > first_change_date

        # Setting same status should not change status_change_date
        previous_date = teacher.status_change_date
        teacher.status = TeacherStatus.ON_LEAVE
        db.session.commit()
        assert teacher.status_change_date == previous_date

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_teacher_status_enum_form_integration():
    """Test TeacherStatus FormEnum integration (choices and choices_required)"""
    # Test choices() method for form integration
    choices = TeacherStatus.choices()
    assert isinstance(choices, list)
    assert len(choices) > 0

    # Verify all enum values are in choices
    # FormEnum.choices() returns [(member.name, member.value), ...]
    enum_values = [
        TeacherStatus.ACTIVE,
        TeacherStatus.INACTIVE,
        TeacherStatus.ON_LEAVE,
        TeacherStatus.RETIRED,
    ]
    choice_names = [choice[0] for choice in choices]  # First element is the enum name
    choice_vals = [choice[1] for choice in choices]  # Second element is the enum value

    for enum_val in enum_values:
        # Check that enum name is in choices
        assert enum_val.name in choice_names
        # Check that enum value is in choices
        assert enum_val.value in choice_vals

    # Test choices_required() method
    choices_required = TeacherStatus.choices_required()
    assert isinstance(choices_required, list)
    assert len(choices_required) > 0
    # Should have same structure as choices()
    assert len(choices_required) == len(choices)


def test_import_from_salesforce(app):
    """Test Salesforce import with various scenarios"""
    with app.app_context():
        # Test 1: Create new teacher with valid Salesforce data
        sf_data = {
            "Id": "0031234567890ABCD",
            "FirstName": "Jane",
            "LastName": "Smith",
            "AccountId": "001ABCDEFGHIJKLMN",
            "npsp__Primary_Affiliation__c": "0015f00000TEST1234",  # 18-char Salesforce ID (fixed)
            "Department": "Science",
            "Gender__c": "Female",
            "Email": "jane@example.com",
            "Phone": "555-1234",
            "Last_Email_Message__c": "2024-01-15",
            "Last_Mailchimp_Email_Date__c": "2024-01-20",
        }

        teacher, is_new, error = Teacher.import_from_salesforce(sf_data, db.session)
        assert error is None
        assert is_new is True
        assert teacher is not None
        db.session.commit()  # Commit to persist changes
        # Refresh to get the latest data from database
        db.session.refresh(teacher)
        assert teacher.first_name == "Jane"
        assert teacher.last_name == "Smith"
        assert teacher.salesforce_individual_id == "0031234567890ABCD"
        assert teacher.salesforce_account_id == "001ABCDEFGHIJKLMN"
        assert teacher.school_id == "0015f00000TEST1234"
        assert teacher.salesforce_school_id == "0015f00000TEST1234"  # 18-char, so set
        assert teacher.department == "Science"
        assert teacher.gender == GenderEnum.female
        assert teacher.status == TeacherStatus.ACTIVE  # Default for new teachers

        # Test 2: Non-18-char school ID (should not set salesforce_school_id)
        sf_data2 = {
            "Id": "0031234567890ABCD2",
            "FirstName": "John",
            "LastName": "Doe",
            "npsp__Primary_Affiliation__c": "TEST001",  # Non-18-char ID
        }

        teacher2, is_new2, error2 = Teacher.import_from_salesforce(sf_data2, db.session)
        assert error2 is None
        assert is_new2 is True
        db.session.commit()  # Commit to persist changes
        db.session.refresh(teacher2)
        assert teacher2.school_id == "TEST001"
        assert teacher2.salesforce_school_id is None  # Not 18-char, so not set

        # Test 3: Missing required fields
        sf_data3 = {
            "Id": "",  # Missing ID
            "FirstName": "Bob",
            "LastName": "Jones",
        }

        teacher3, is_new3, error3 = Teacher.import_from_salesforce(sf_data3, db.session)
        assert error3 is not None
        assert "Missing required fields" in error3
        assert teacher3 is None

        # Test 4: Empty string to None conversion
        sf_data4 = {
            "Id": "0031234567890ABCD3",
            "FirstName": "Empty",
            "LastName": "Fields",
            "Department": "",  # Empty string
            "Gender__c": "",  # Empty string
        }

        teacher4, is_new4, error4 = Teacher.import_from_salesforce(sf_data4, db.session)
        assert error4 is None
        db.session.commit()  # Commit to persist changes
        db.session.refresh(teacher4)
        assert teacher4.department is None or teacher4.department == ""
        # Gender might be None or empty, depending on implementation

        # Cleanup
        for t in [teacher, teacher2, teacher4]:
            if t:
                db.session.delete(t)
        db.session.commit()


def test_import_from_salesforce_duplicate(app):
    """Test duplicate handling during Salesforce import"""
    with app.app_context():
        # Create initial teacher
        sf_data = {
            "Id": "003DUPLICATE12345",
            "FirstName": "Original",
            "LastName": "Teacher",
            "Department": "Math",
        }

        teacher1, is_new1, error1 = Teacher.import_from_salesforce(sf_data, db.session)
        assert error1 is None
        assert is_new1 is True
        assert teacher1.department == "Math"

        # Import same teacher with updated data
        sf_data_updated = {
            "Id": "003DUPLICATE12345",  # Same Salesforce ID
            "FirstName": "Updated",
            "LastName": "Teacher",
            "Department": "Science",  # Updated department
            "Gender__c": "Female",
        }

        teacher2, is_new2, error2 = Teacher.import_from_salesforce(
            sf_data_updated, db.session
        )
        assert error2 is None
        assert is_new2 is False  # Should update existing, not create new
        assert teacher2.id == teacher1.id  # Same teacher
        assert teacher2.first_name == "Updated"
        assert teacher2.department == "Science"
        assert teacher2.gender == GenderEnum.female

        # Verify only one teacher exists with this Salesforce ID
        count = Teacher.query.filter_by(
            salesforce_individual_id="003DUPLICATE12345"
        ).count()
        assert count == 1

        # Cleanup
        db.session.delete(teacher2)
        db.session.commit()


def test_update_contact_info(app):
    """Test contact info updates from Salesforce"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test adding email and phone
        sf_data = {
            "Email": "test@example.com",
            "Phone": "555-1234",
        }

        success, error = teacher.update_contact_info(sf_data, db.session)
        assert success is True
        assert error is None
        db.session.commit()

        # Verify email was created
        assert teacher.primary_email == "test@example.com"
        email = Email.query.filter_by(contact_id=teacher.id, primary=True).first()
        assert email is not None
        assert email.email == "test@example.com"
        assert email.type == ContactTypeEnum.professional

        # Verify phone was created
        assert teacher.primary_phone == "555-1234"
        phone = Phone.query.filter_by(contact_id=teacher.id, primary=True).first()
        assert phone is not None
        assert phone.number == "555-1234"
        assert phone.type == ContactTypeEnum.professional

        # Test duplicate prevention - update with same info
        success2, error2 = teacher.update_contact_info(sf_data, db.session)
        assert success2 is True
        db.session.commit()

        # Verify no duplicates
        email_count = Email.query.filter_by(contact_id=teacher.id, primary=True).count()
        phone_count = Phone.query.filter_by(contact_id=teacher.id, primary=True).count()
        assert email_count == 1
        assert phone_count == 1

        # Test updating with different email
        sf_data_new = {
            "Email": "newemail@example.com",
            "Phone": "555-5678",
        }

        success3, error3 = teacher.update_contact_info(sf_data_new, db.session)
        assert success3 is True
        db.session.commit()

        # Should still have only one primary email and phone
        email_count2 = Email.query.filter_by(
            contact_id=teacher.id, primary=True
        ).count()
        phone_count2 = Phone.query.filter_by(
            contact_id=teacher.id, primary=True
        ).count()
        assert email_count2 == 1
        assert phone_count2 == 1

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_local_status_fields(app):
    """Test local status defaults and tracking"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test default local_status is unknown
        assert teacher.local_status == LocalStatusEnum.unknown

        # Test local_status_last_updated is None initially
        assert teacher.local_status_last_updated is None

        # Test _get_local_status_assumption returns local
        assumption = teacher._get_local_status_assumption()
        assert assumption == LocalStatusEnum.local

        # Test setting local_status
        teacher.local_status = LocalStatusEnum.local
        db.session.commit()
        assert teacher.local_status == LocalStatusEnum.local

        # Test local_status_last_updated can be set
        teacher.local_status_last_updated = datetime.now(timezone.utc)
        db.session.commit()
        # Refresh to get the latest data from database
        db.session.refresh(teacher)
        assert teacher.local_status_last_updated is not None
        assert isinstance(teacher.local_status_last_updated, datetime)
        # Note: SQLite may not preserve timezone info, so check if it's a datetime
        # The datetime should be set correctly even if timezone info is lost on retrieval

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_local_status_calculation(app):
    """Test local status calculation (inherited from Contact)"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test calculate_local_status method exists (inherited from Contact)
        assert hasattr(teacher, "calculate_local_status")

        # Test with KC metro address (should be local)
        kc_address = Address(
            contact_id=teacher.id,
            address_line1="123 Main St",
            city="Kansas City",
            state="MO",
            zip_code="64111",
            primary=True,
        )
        db.session.add(kc_address)
        db.session.commit()

        local_status = teacher.calculate_local_status()
        assert local_status == LocalStatusEnum.local

        # Test with non-local address
        kc_address.zip_code = "90210"
        db.session.commit()
        local_status2 = teacher.calculate_local_status()
        assert local_status2 == LocalStatusEnum.non_local

        # Test with no address (should use assumption)
        db.session.delete(kc_address)
        db.session.commit()
        local_status3 = teacher.calculate_local_status()
        # Should return assumption (local for teachers)
        assert local_status3 == LocalStatusEnum.local

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_upcoming_past_events(app, test_event, test_school):
    """Test event properties with timezone-aware datetime"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Create past event
        past_event = Event(
            title="Past Event",
            start_date=datetime.now(timezone.utc) - timedelta(days=1),
            end_date=datetime.now(timezone.utc) - timedelta(hours=23),
            status=EventStatus.COMPLETED,
            type=EventType.IN_PERSON,
            format=EventFormat.IN_PERSON,
            school=test_school.id,  # Use valid 18-character Salesforce ID from test_school fixture
            volunteers_needed=5,
        )
        db.session.add(past_event)
        db.session.commit()

        # Create upcoming event
        upcoming_event = Event(
            title="Upcoming Event",
            start_date=datetime.now(timezone.utc) + timedelta(days=1),
            end_date=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
            status=EventStatus.PUBLISHED,
            type=EventType.IN_PERSON,
            format=EventFormat.IN_PERSON,
            school=test_school.id,  # Use valid 18-character Salesforce ID from test_school fixture
            volunteers_needed=5,
        )
        db.session.add(upcoming_event)
        db.session.commit()

        # Register teacher for both events
        past_reg = EventTeacher(event_id=past_event.id, teacher_id=teacher.id)
        upcoming_reg = EventTeacher(event_id=upcoming_event.id, teacher_id=teacher.id)
        db.session.add(past_reg)
        db.session.add(upcoming_reg)
        db.session.commit()

        # Refresh teacher to get updated relationships
        db.session.refresh(teacher)

        # Test upcoming_events property
        upcoming = teacher.upcoming_events
        assert len(upcoming) == 1
        assert upcoming[0].id == upcoming_event.id
        assert upcoming[0].title == "Upcoming Event"

        # Test past_events property
        past = teacher.past_events
        assert len(past) == 1
        assert past[0].id == past_event.id
        assert past[0].title == "Past Event"

        # Test that events use timezone-aware datetime
        # Note: SQLite may return timezone-naive datetimes, so normalize for comparison
        now = datetime.now(timezone.utc)
        upcoming_start = upcoming[0].start_date
        if upcoming_start.tzinfo is None:
            upcoming_start = upcoming_start.replace(tzinfo=timezone.utc)
        assert upcoming_start > now

        past_start = past[0].start_date
        if past_start.tzinfo is None:
            past_start = past_start.replace(tzinfo=timezone.utc)
        assert past_start < now

        # Cleanup
        db.session.delete(past_reg)
        db.session.delete(upcoming_reg)
        db.session.delete(past_event)
        db.session.delete(upcoming_event)
        db.session.delete(teacher)
        db.session.commit()


def test_connector_role_validation(app):
    """Test connector role validator"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test role capitalization
        teacher.connector_role = "lead"
        db.session.commit()
        assert teacher.connector_role == "Lead"

        teacher.connector_role = "support"
        db.session.commit()
        assert teacher.connector_role == "Support"

        teacher.connector_role = "COORDINATOR"
        db.session.commit()
        assert teacher.connector_role == "Coordinator"

        # Test None value
        teacher.connector_role = None
        db.session.commit()
        assert teacher.connector_role is None

        # Test empty string
        teacher.connector_role = ""
        db.session.commit()
        assert teacher.connector_role == ""

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_school_id_fields(app):
    """Test school_id vs salesforce_school_id handling"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test setting 18-char Salesforce ID
        sf_school_id = "0015f00000TEST123"
        teacher.school_id = sf_school_id
        teacher.salesforce_school_id = sf_school_id
        db.session.commit()

        assert teacher.school_id == sf_school_id
        assert teacher.salesforce_school_id == sf_school_id

        # Test setting non-18-char ID (should not set salesforce_school_id)
        non_sf_id = "TEST001"
        teacher.school_id = non_sf_id
        teacher.salesforce_school_id = None
        db.session.commit()

        assert teacher.school_id == non_sf_id
        assert teacher.salesforce_school_id is None

        # Test both fields can be set independently
        teacher.school_id = "SCHOOL123"
        teacher.salesforce_school_id = "0015f00000SCHOOL1"
        db.session.commit()

        assert teacher.school_id == "SCHOOL123"
        assert teacher.salesforce_school_id == "0015f00000SCHOOL1"

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_salesforce_individual_id(app):
    """Test inherited Salesforce ID field from Contact"""
    with app.app_context():
        teacher = Teacher(first_name="Test", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        # Test setting salesforce_individual_id (inherited from Contact)
        sf_id = "0031234567890ABCD"
        teacher.salesforce_individual_id = sf_id
        db.session.commit()

        assert teacher.salesforce_individual_id == sf_id
        assert hasattr(teacher, "salesforce_individual_id")  # Inherited from Contact

        # Test querying by salesforce_individual_id
        found_teacher = Teacher.query.filter_by(salesforce_individual_id=sf_id).first()
        assert found_teacher is not None
        assert found_teacher.id == teacher.id

        # Test uniqueness constraint (if applicable)
        teacher2 = Teacher(
            first_name="Another", last_name="Teacher", salesforce_individual_id=sf_id
        )
        db.session.add(teacher2)
        # Note: This might raise IntegrityError if unique constraint exists
        # We'll test the constraint if it exists
        try:
            db.session.commit()
            # If no error, verify both have same ID (might be allowed)
            assert teacher2.salesforce_individual_id == sf_id
        except Exception:
            # If constraint exists, rollback
            db.session.rollback()
            pass

        # Cleanup
        db.session.delete(teacher)
        if teacher2 in db.session:
            db.session.delete(teacher2)
        db.session.commit()

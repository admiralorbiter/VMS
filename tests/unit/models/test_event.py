import sys
from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.district_model import District
from models.event import AttendanceStatus, CancellationReason, Event, EventAttendance, EventComment, EventFormat, EventStatus, EventType
from models.school_model import School
from models.volunteer import Skill, Volunteer


@pytest.fixture(autouse=True)
def setup_db(app):
    """Setup test database before each test"""
    with app.app_context():
        db.create_all()
        db.session.begin_nested()  # Create savepoint
        yield
        db.session.rollback()  # Rollback to savepoint
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_school(app):
    """Optional fixture for tests that need a school"""
    with app.app_context():
        # Only import School when needed
        try:
            school = School(id="TEST001", name="Test School")
            db.session.add(school)
            db.session.commit()
            return school
        except ImportError:
            # For tests that don't need school
            return None


def test_new_event(app):
    """Test creating a new event"""
    with app.app_context():
        event = Event(
            title="Test Event",
            description="Test Description",
            type=EventType.IN_PERSON,
            start_date=datetime.now(),
            volunteers_needed=5,  # Changed from volunteer_needed
        )
        db.session.add(event)
        db.session.commit()

        assert event.id is not None
        assert event.title == "Test Event"
        assert event.description == "Test Description"
        assert event.type == EventType.IN_PERSON
        assert event.volunteers_needed == 5  # Changed assertion


def test_event_relationships(app, test_event, test_volunteer, test_district, test_skill):
    """Test event relationships with volunteers, districts, and skills"""
    with app.app_context():
        # Start fresh session
        db.session.remove()
        db.session.begin()

        # Use db.session.get() instead of query.get()
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        district = db.session.get(District, test_district.id)
        skill = db.session.get(Skill, test_skill.id)

        try:
            # Test volunteer relationship
            event.volunteers.append(volunteer)
            db.session.flush()
            assert event.volunteers_needed == 5

            # Test district relationship
            event.districts.append(district)
            db.session.flush()
            assert len(event.districts) == 1

            # Test skill relationship
            event.skills.append(skill)
            db.session.flush()
            assert len(event.skills) == 1

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_event_comments(app, test_event):
    """Test event comments"""
    with app.app_context():
        comment = EventComment(event_id=test_event.id, content="Test comment")
        db.session.add(comment)
        db.session.commit()

        assert len(test_event.comments.all()) == 1
        assert test_event.comments.first().content == "Test comment"


def test_event_attendance(app, test_event):
    """Test event attendance tracking"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        try:
            attendance = EventAttendance(event_id=test_event.id, status=AttendanceStatus.COMPLETED, last_taken=datetime.now(timezone.utc))

            db.session.add(attendance)
            db.session.commit()

            # Use db.session.get() instead of query.get()
            event = db.session.get(Event, test_event.id)
            assert event.attendance is not None
            assert event.attendance.status == AttendanceStatus.COMPLETED

        except Exception as e:
            db.session.rollback()
            raise e
        finally:
            db.session.close()


def test_event_properties(test_event):
    """Test event property methods"""
    # Test display_status
    assert test_event.display_status == "Draft"

    # Test salesforce_url
    assert test_event.salesforce_url is None
    test_event.salesforce_id = "a005f000003XNa7AAG"
    assert test_event.salesforce_url == "https://prep-kc.lightning.force.com/lightning/r/Session__c/a005f000003XNa7AAG/view"

    # Test is_virtual
    assert not test_event.is_virtual
    test_event.type = EventType.VIRTUAL_SESSION
    assert test_event.is_virtual


@pytest.mark.parametrize(
    "invalid_data",
    [
        {
            "description": "Test Description",
            "type": EventType.IN_PERSON,
            "start_date": datetime.now(timezone.utc),
            # Missing required title
        },
        {
            "title": "Test Event",
            "description": "Test Description",
            "type": EventType.IN_PERSON,
            # Missing required start_date
        },
    ],
)
def test_invalid_event_data(app, invalid_data):
    """Test that invalid event data raises appropriate errors"""
    with app.app_context():
        with pytest.raises(Exception):
            invalid_event = Event(**invalid_data)
            db.session.add(invalid_event)
            db.session.commit()


def test_event_update_from_csv(app, test_event):
    """Test updating event from CSV data"""
    csv_data = {
        "Date": "12/25/2024",
        "Session ID": "TEST123",
        "Title": "Updated Event",
        "Series or Event Title": "Test Series",
        "Status": EventStatus.CONFIRMED,
        "Duration": "60",
        "School": "Test School",
        "District or Company": "Test District",
        "Registered Student Count": "20",
        "Attended Student Count": "15",
        "SignUp Role": "educator",
        "Name": "Test Educator",
        "User Auth Id": "EDU123",
        "Volunteers Needed": "8",  # Added this field if you're handling it in update_from_csv
    }

    test_event.update_from_csv(csv_data)

    assert test_event.session_id == "TEST123"
    assert test_event.title == "Updated Event"
    assert test_event.series == "Test Series"
    assert test_event.status == EventStatus.CONFIRMED
    assert test_event.duration == 60
    assert test_event.school == "Test School"
    assert test_event.district_partner == "Test District"
    assert test_event.registered_count == 20
    assert test_event.attended_count == 15
    assert test_event.educators == "Test Educator"
    assert test_event.educator_ids == "EDU123"
    assert test_event.volunteers_needed == 8  # Added assertion if handling this in update_from_csv


def test_event_merge_duplicate(app, test_event):
    """Test merging duplicate event data"""
    duplicate_data = {
        "Registered Student Count": "10",
        "Attended Student Count": "8",
        "SignUp Role": "professional",
        "Name": "John Doe",
        "District or Company": "Test Company",
    }

    initial_registered = test_event.registered_count
    initial_attended = test_event.attended_count

    test_event.merge_duplicate(duplicate_data)

    assert test_event.registered_count == initial_registered + 10
    assert test_event.attended_count == initial_attended + 8
    assert len(test_event.volunteers) == 1  # New volunteer should be added


def test_event_cancellation(app, test_event):
    """Test event cancellation"""
    with app.app_context():
        test_event.status = EventStatus.CANCELLED
        test_event.cancellation_reason = CancellationReason.WEATHER
        db.session.commit()

        assert test_event.status == EventStatus.CANCELLED
        assert test_event.cancellation_reason == CancellationReason.WEATHER


def test_event_virtual_fields(app, test_school):
    """Test virtual event specific fields"""
    with app.app_context():
        virtual_event = Event(
            title="Virtual Test Event",
            description="Virtual Test Description",
            type=EventType.VIRTUAL_SESSION,
            start_date=datetime.now(timezone.utc),
            status=EventStatus.DRAFT,
            format=EventFormat.VIRTUAL,
            session_id="TEST123",
            series="Test Series",
            duration=60,
            school="TEST001" if test_school else None,  # Make school optional
            district_partner="Test District",
            educators="Test Educator",
            educator_ids="EDU123",
            volunteers_needed=3,
        )
        db.session.add(virtual_event)
        db.session.commit()

        assert virtual_event.is_virtual
        assert virtual_event.session_id == "TEST123"

        db.session.delete(virtual_event)
        db.session.commit()


def test_event_merge_duplicate_with_educator(app, test_event):
    """Test merging duplicate event data with educator"""
    educator_data = {"Registered Student Count": "10", "Attended Student Count": "8", "SignUp Role": "educator", "Name": "Jane Smith", "User Auth Id": "EDU456"}

    test_event.merge_duplicate(educator_data)

    assert test_event.educators == "Jane Smith"
    assert test_event.educator_ids == "EDU456"


def test_event_merge_duplicate_professional_with_company(app, test_event):
    """Test merging duplicate event data with professional and company"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Use db.session.get() instead of query.get()
        event = db.session.get(Event, test_event.id)

        try:
            professional_data = {"SignUp Role": "professional", "Name": "John Professional", "District or Company": "Test Corp"}

            event.merge_duplicate(professional_data)
            db.session.flush()

            # Verify volunteer was created and linked
            assert len(event.volunteers) == 1
            volunteer = event.volunteers[0]
            assert volunteer.first_name == "John"
            assert volunteer.last_name == "Professional"

            # Verify organization was created and linked
            from models.organization import Organization

            org = Organization.query.filter_by(name="Test Corp").first()
            assert org is not None
            assert volunteer.volunteer_organizations[0].organization.name == "Test Corp"

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_event_update_from_csv_invalid_date(app, test_event):
    """Test updating event from CSV data with invalid date"""
    invalid_csv_data = {
        # Missing Date field
        "Session ID": "TEST123"
    }

    with pytest.raises(ValueError, match="Date is required"):
        test_event.update_from_csv(invalid_csv_data)


def test_event_update_from_csv_professional(app, test_event):
    """Test updating event from CSV data with professional"""
    csv_data = {
        "Date": "12/25/2024",
        "Title": "Updated Event",
        "SignUp Role": "professional",
        "Name": "Jane Professional",
        "District or Company": "Test Corp",
        "Status": EventStatus.CONFIRMED,
        "Duration": "60",
    }

    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Use db.session.get() instead of query.get()
        event = db.session.get(Event, test_event.id)

        try:
            with db.session.no_autoflush:
                event.update_from_csv(csv_data)
                db.session.flush()

                # Verify volunteer was created and linked
                assert len(event.volunteers) == 1
                volunteer = event.volunteers[0]
                assert volunteer.first_name == "Jane"
                assert volunteer.last_name == "Professional"

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_event_update_from_csv_handles_errors(app, test_event):
    """Test handling of errors during CSV update"""
    invalid_csv_data = {
        "Date": "12/25/2024",
        "Status": EventStatus.CONFIRMED,
        # Missing Title which is required
    }

    with app.app_context():
        db.session.begin_nested()
        try:
            with pytest.raises(ValueError) as exc_info:
                test_event.update_from_csv(invalid_csv_data)
            assert "Title is required" in str(exc_info.value)
            db.session.rollback()
        except:
            db.session.rollback()
            raise


def test_event_indexes(app):
    """Test that indexes are properly created"""
    with app.app_context():
        # Get table info from database
        inspector = db.inspect(db.engine)
        indexes = inspector.get_indexes("event")

        # Check for specific indexes
        index_names = [idx["name"] for idx in indexes]
        assert "idx_event_status_date" in index_names
        assert "idx_district_partner" in index_names


def test_event_date_validation(app):
    """Test date validation logic"""
    with app.app_context():
        # Test invalid dates
        event = Event(title="Test Event", start_date=datetime.now(), end_date=datetime.now() - timedelta(days=1))  # End date before start date

        with pytest.raises(ValueError, match="End date must be after start date"):
            event.validate_dates()


def test_event_count_validation(app):
    """Test attendance count validation"""
    with app.app_context():
        event = Event(title="Test Event", start_date=datetime.now(), registered_count=10, attended_count=15)  # More attended than registered

        with pytest.raises(ValueError, match="Attended count cannot exceed registered count"):
            event.validate_counts()


def test_event_time_properties(app):
    """Test time-related property methods"""
    with app.app_context():
        now = datetime.now(timezone.utc)

        # Past event
        past_event = Event(title="Past Event", start_date=now - timedelta(days=2), end_date=now - timedelta(days=1))
        assert past_event.is_past_event

        # Future event
        future_event = Event(title="Future Event", start_date=now + timedelta(days=1), end_date=now + timedelta(days=2))
        assert future_event.is_upcoming


def test_can_register_conditions(app):
    """Test various conditions for event registration"""
    with app.app_context():
        now = datetime.now(timezone.utc)

        # Test cancelled event
        cancelled_event = Event(title="Cancelled Event", start_date=now + timedelta(days=1), status=EventStatus.CANCELLED, available_slots=5)
        assert not cancelled_event.can_register()

        # Test past event
        past_event = Event(
            title="Past Event", start_date=(now - timedelta(days=1)).replace(tzinfo=timezone.utc), status=EventStatus.PUBLISHED, available_slots=5
        )
        assert not past_event.can_register()

        # Test full event
        full_event = Event(title="Full Event", start_date=now + timedelta(days=1), status=EventStatus.PUBLISHED, available_slots=0)
        assert not full_event.can_register()

        # Test registrable event
        open_event = Event(title="Open Event", start_date=now + timedelta(days=1), status=EventStatus.PUBLISHED, available_slots=5)
        assert open_event.can_register()


def test_local_start_date(app):
    """Test timezone conversion for start date"""
    with app.app_context():
        now = datetime.now(timezone.utc)
        event = Event(title="Test Event", start_date=now)
        assert event.local_start_date.tzinfo is not None


def test_event_attendance_cascade(app, test_event):
    """Test that attendance record is deleted when event is deleted"""
    with app.app_context():
        db.session.remove()  # Ensure clean session
        event = db.session.get(Event, test_event.id)  # Get fresh instance

        attendance = EventAttendance(event_id=event.id, status=AttendanceStatus.COMPLETED, total_attendance=10)
        db.session.add(attendance)
        db.session.commit()

        db.session.delete(event)
        db.session.commit()

        assert EventAttendance.query.filter_by(event_id=event.id).first() is None


def test_event_edge_cases(app):
    """Test edge cases for event creation and validation"""
    with app.app_context():
        # Test case 1: Event with end date before start date
        with pytest.raises(ValueError, match="End date must be after start date"):
            event = Event(title="Invalid Date Event", start_date=datetime.now(timezone.utc), end_date=datetime.now(timezone.utc) - timedelta(hours=1))
            event.validate_dates()

        # Test case 2: Event with max attendance counts
        event = Event(title="Max Attendance Event", start_date=datetime.now(timezone.utc), registered_count=sys.maxsize, attended_count=sys.maxsize)
        db.session.add(event)
        db.session.commit()
        assert event.registered_count == sys.maxsize

        # Test case 3: Event with empty required fields
        with pytest.raises(ValueError):
            Event(title="", start_date=datetime.now(timezone.utc))  # Empty title


def test_event_volunteer_capacity(app):
    """Test volunteer capacity constraints"""
    with app.app_context():
        event = Event(title="Capacity Test Event", start_date=datetime.now(timezone.utc), volunteers_needed=2)
        db.session.add(event)
        db.session.commit()

        # Add volunteers up to capacity
        for i in range(3):  # Try to add one more than needed
            volunteer = Volunteer(first_name=f"Test{i}", last_name="Volunteer", middle_name="")
            db.session.add(volunteer)
            event.volunteers.append(volunteer)

        # Verify volunteer count matches capacity
        assert len(event.volunteers) == 3  # Should allow over-assignment
        assert event.volunteer_count == 3


def test_event_status_transitions(app):
    """Test valid and invalid event status transitions"""
    with app.app_context():
        event = Event(title="Status Test Event", start_date=datetime.now(timezone.utc), status=EventStatus.DRAFT)
        db.session.add(event)
        db.session.commit()

        # Test valid transition
        event.status = EventStatus.PUBLISHED
        db.session.commit()
        assert event.status == EventStatus.PUBLISHED

        # Test completed to draft (should not be allowed)
        event.status = EventStatus.COMPLETED
        db.session.commit()
        with pytest.raises(ValueError):
            event.status = EventStatus.DRAFT
            event.validate_status_transition()


def test_event_duplicate_volunteer(app, test_event, test_volunteer):
    """Test handling of duplicate volunteer assignments"""
    with app.app_context():
        db.session.begin()
        try:
            # Get fresh instances in current session
            event = db.session.get(Event, test_event.id)
            volunteer = db.session.get(Volunteer, test_volunteer.id)

            # First addition
            event.add_volunteer(volunteer)  # Use add_volunteer instead of append
            db.session.flush()
            initial_count = len(event.volunteers)

            # Try second addition
            event.add_volunteer(volunteer)  # Use add_volunteer instead of append
            db.session.flush()

            # Verify count hasn't changed
            assert len(event.volunteers) == initial_count
            assert volunteer in event.volunteers

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def get_utc_now():
    return datetime.now(timezone.utc)


# Use in models
created_at = db.Column(db.DateTime, default=get_utc_now)


@property
def is_past_event(self):
    if not self.start_date:
        return False
    return self.start_date.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)

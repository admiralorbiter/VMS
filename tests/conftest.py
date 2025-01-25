import pytest
from app import app as flask_app
from models import db
from config import TestingConfig
from models.user import User
from werkzeug.security import generate_password_hash
from datetime import date, datetime, timedelta
from models.contact import *
from models.class_model import Class
from models.district_model import District
from models.event import *
from models.school_model import School
from models.student import Student
from models.contact import RaceEthnicityEnum
from models.teacher import Teacher
from models.contact import GenderEnum
from models.tech_job_board import JobOpportunity
from models.upcoming_events import UpcomingEvent
from models.volunteer import Volunteer, Skill, VolunteerSkill, Engagement, EventParticipation
from models.contact import EducationEnum, LocalStatusEnum, SkillSourceEnum
from models.history import History
from models.organization import Organization

@pytest.fixture
def app():
    flask_app.config.from_object(TestingConfig)
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Test',
        last_name='User',
        is_admin=False
    )
    with app.app_context():
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()

@pytest.fixture
def test_admin(app):
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('admin123'),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def auth_headers(test_user, client):
    # Login and get session cookie
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    return {'Cookie': response.headers.get('Set-Cookie', '')}

@pytest.fixture
def test_contact(app):
    with app.app_context():
        contact = Contact(
            type='contact',
            salesforce_individual_id='003TESTID123456789',
            first_name='John',
            last_name='Doe',
            salutation=SalutationEnum.mr,
            suffix=SuffixEnum.jr,
            gender=GenderEnum.male,
            birthdate=date(1990, 1, 1),
            notes='Test contact notes'
        )
        
        # Create all related objects
        phone = Phone(
            number='123-456-7890',
            type=ContactTypeEnum.personal,
            primary=True
        )
        email = Email(
            email='john.doe@example.com',
            type=ContactTypeEnum.personal,
            primary=True
        )
        address = Address(
            address_line1='123 Main St',
            city='Kansas City',
            state='MO',
            zip_code='64111',
            country='USA',
            type=ContactTypeEnum.personal,
            primary=True
        )
        
        # Set up relationships
        contact.phones.append(phone)
        contact.emails.append(email)
        contact.addresses.append(address)
        
        # Add and commit
        db.session.add(contact)
        db.session.commit()
        
        yield contact
        
        # Clean up
        db.session.delete(contact)
        db.session.commit()

@pytest.fixture
def test_class(app):
    """Fixture for creating a test class"""
    with app.app_context():
        from models.class_model import Class
        
        # Debug: Print test_class details before creation
        test_class = Class(
            salesforce_id='a005f000003XNa7AAG',
            name='Test Class 2024',
            school_salesforce_id='a015f000004XNa7AAG',
            class_year=2024
        )
        db.session.add(test_class)
        db.session.commit()
        
        # Verify the class was created using salesforce_id
        created_class = db.session.query(Class).filter_by(
            salesforce_id=test_class.salesforce_id
        ).first()
        assert created_class is not None
        
        yield test_class
        
        # Clean up
        existing = db.session.query(Class).filter_by(
            salesforce_id=test_class.salesforce_id
        ).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_district(app):
    """Fixture for creating a test district"""
    with app.app_context():
        district = District(
            id='0015f00000JVZsFAAX',
            name='Test School District',
            district_code='4045'
        )
        db.session.add(district)
        db.session.commit()
        yield district
        db.session.delete(district)
        db.session.commit()

@pytest.fixture
def test_event(app):
    """Fixture for creating a test event"""
    with app.app_context():
        event = Event(
            title='Test Event',
            description='Test Description',
            type=EventType.IN_PERSON,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(hours=2),
            status=EventStatus.DRAFT,
            format=EventFormat.IN_PERSON,
            volunteers_needed=5
        )
        db.session.add(event)
        db.session.commit()
        
        yield event
        
        # Clean up
        db.session.delete(event)
        db.session.commit()

@pytest.fixture
def test_event_comment(app, test_event):
    """Fixture for creating a test event comment"""
    with app.app_context():
        comment = EventComment(
            event_id=test_event.id,
            content='Test comment'
        )
        db.session.add(comment)
        db.session.commit()
        yield comment
        db.session.delete(comment)
        db.session.commit()

@pytest.fixture
def test_volunteer(app):
    """Fixture for creating a test volunteer"""
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer',
            middle_name='',
            organization_name='Test Corp',
            title='Software Engineer',
            department='Engineering',
            industry='Technology',
            education=EducationEnum.bachelors_degree,
            local_status=LocalStatusEnum.true,
            race_ethnicity=RaceEthnicityEnum.white
        )
        db.session.add(volunteer)
        db.session.commit()
        
        yield volunteer
        
        # Clean up
        existing = db.session.get(Volunteer, volunteer.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_skill(app):
    """Fixture for creating a test skill"""
    with app.app_context():
        skill = Skill(
            name='Python Programming'
        )
        db.session.add(skill)
        db.session.commit()
        
        yield skill
        
        # Clean up
        existing = db.session.get(Skill, skill.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_volunteer_skill(app, test_volunteer, test_skill):
    """Fixture for creating a test volunteer skill relationship"""
    with app.app_context():
        vol_skill = VolunteerSkill(
            volunteer_id=test_volunteer.id,
            skill_id=test_skill.id,
            source=SkillSourceEnum.self_reported,
            interest_level='High'
        )
        db.session.add(vol_skill)
        db.session.commit()
        
        yield vol_skill
        
        # Clean up
        db.session.delete(vol_skill)
        db.session.commit()

@pytest.fixture
def test_engagement(app, test_volunteer):
    """Fixture for creating a test engagement"""
    with app.app_context():
        engagement = Engagement(
            volunteer_id=test_volunteer.id,
            engagement_date=date(2024, 1, 1),
            engagement_type='Meeting',
            notes='Test engagement notes'
        )
        db.session.add(engagement)
        db.session.commit()
        
        yield engagement
        
        # Clean up
        existing = db.session.get(Engagement, engagement.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_event_participation(app, test_volunteer, test_event):
    """Fixture for creating a test event participation"""
    with app.app_context():
        participation = EventParticipation(
            volunteer_id=test_volunteer.id,
            event_id=test_event.id,
            status='Attended',
            delivery_hours=2.5,
            salesforce_id='a005f000003TEST789'
        )
        db.session.add(participation)
        db.session.commit()
        
        yield participation
        
        # Clean up
        existing = db.session.get(EventParticipation, participation.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_history(app, test_volunteer):
    """Fixture for creating a test history record"""
    with app.app_context():
        history = History(
            volunteer_id=test_volunteer.id,
            activity_date=datetime.now(),
            activity_type='Test Activity',
            notes='Test history notes',
            is_deleted=False
        )
        db.session.add(history)
        db.session.commit()
        
        yield history
        
        # Clean up
        existing = db.session.get(History, history.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_school(app, test_district):
    """Fixture for creating a test school"""
    with app.app_context():
        school = School(
            id='0015f00000TEST123',
            name='Test School',
            normalized_name='TEST SCHOOL',
            school_code='4045',
            district_id=test_district.id
        )
        db.session.add(school)
        db.session.commit()
        yield school
        
        # Clean up
        existing = db.session.get(School, school.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_student(app, test_school, test_class):
    """Fixture for creating a test student"""
    with app.app_context():
        student = Student(
            first_name='Test',
            last_name='Student',
            current_grade=9,
            legacy_grade='Freshman',
            student_id='ST12345',
            school_id=test_school.id,
            class_id=test_class.salesforce_id,
            racial_ethnic=RaceEthnicityEnum.white,
            school_code='4045',
            ell_language='Spanish',
            gifted=True,
            lunch_status='Free'
        )
        db.session.add(student)
        db.session.commit()
        yield student
        
        # Clean up
        existing = db.session.get(Student, student.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_student_no_school(app):
    """Fixture for creating a test student without school/class relationships"""
    with app.app_context():
        student = Student(
            first_name='Independent',
            last_name='Student',
            current_grade=10,
            racial_ethnic=RaceEthnicityEnum.white
        )
        db.session.add(student)
        db.session.commit()
        yield student
        
        # Clean up
        existing = db.session.get(Student, student.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_teacher(app):
    """Fixture for creating a test teacher"""
    with app.app_context():
        teacher = Teacher(
            first_name='Test',
            last_name='Teacher',
            department='Science',
            school_id='0015f00000TEST123',
            active=True,
            connector_role='Lead',
            connector_active=True,
            connector_start_date=date(2024, 1, 1),
            connector_end_date=date(2024, 12, 31),
            gender=GenderEnum.female
        )
        db.session.add(teacher)
        db.session.commit()
        
        yield teacher
        
        # Clean up
        existing = db.session.get(Teacher, teacher.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_job_opportunity(app):
    """Fixture for creating a test job opportunity"""
    with app.app_context():
        job_opp = JobOpportunity(
            company_name='Test Company',
            description='Test Description',
            industry='Technology',
            current_openings=5,
            opening_types='Software Engineer, Data Scientist',
            location='Kansas City, MO',
            entry_level_available=True,
            kc_based=True,
            remote_available=True,
            notes='Test notes',
            job_link='https://example.com/jobs',
            is_active=True
        )
        db.session.add(job_opp)
        db.session.commit()
        yield job_opp
        
        # Clean up
        existing = db.session.get(JobOpportunity, job_opp.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_upcoming_event(app):
    """Fixture for creating a test upcoming event"""
    with app.app_context():
        event = UpcomingEvent(
            salesforce_id='a005f000003TEST789',
            name='Test Upcoming Event',
            available_slots=10,
            filled_volunteer_jobs=5,
            date_and_time='01/01/2024 09:00 AM to 11:00 AM',
            event_type='In Person',
            registration_link='https://example.com/register',
            display_on_website=True,
            start_date=datetime(2024, 1, 1, 9, 0)
        )
        db.session.add(event)
        db.session.commit()
        yield event
        
        # Clean up
        existing = db.session.get(UpcomingEvent, event.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_organization(app):
    """Fixture for creating a test organization"""
    with app.app_context():
        organization = Organization(
            name='Test Organization',
            description='Test Description',
            type='Business',
            billing_street='123 Test St',
            billing_city='Test City',
            billing_state='Test State',
            billing_postal_code='12345',
            billing_country='USA'
        )
        db.session.add(organization)
        db.session.commit()
        
        yield organization
        
        # Clean up
        existing = db.session.get(Organization, organization.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()

@pytest.fixture
def test_volunteer_with_relationships(app, test_volunteer):
    """Fixture for creating a test volunteer with all relationships"""
    with app.app_context():
        # Add email
        email = Email(
            email='test.volunteer@example.com',
            type='personal',
            primary=True,
            contact_id=test_volunteer.id
        )
        
        # Add phone
        phone = Phone(
            number='123-456-7890',
            type='personal',
            primary=True,
            contact_id=test_volunteer.id
        )
        
        # Add skills
        skill1 = Skill(name='Python')
        skill2 = Skill(name='JavaScript')
        db.session.add_all([skill1, skill2])
        
        # Add volunteer skills
        test_volunteer.skills.extend([skill1, skill2])
        
        # Add email and phone
        db.session.add(email)
        db.session.add(phone)
        db.session.commit()
        
        yield test_volunteer
        
        # Cleanup is handled by test_volunteer fixture

@pytest.fixture
def test_admin_headers(test_admin, client):
    """Fixture for admin authentication headers"""
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    return {'Cookie': response.headers.get('Set-Cookie', '')}

@pytest.fixture
def test_calendar_events(app):
    """Fixture for creating test calendar events"""
    with app.app_context():
        # Create multiple events with different dates and statuses
        events = [
            Event(
                title='Past Event',
                description='A past event',
                type=EventType.IN_PERSON,
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now() - timedelta(days=7, hours=-2),
                location='Test Location',
                status=EventStatus.COMPLETED,
                format=EventFormat.IN_PERSON,
                volunteers_needed=5
            ),
            Event(
                title='Current Event',
                description='A current event',
                type=EventType.VIRTUAL_SESSION,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(hours=2),
                location='Virtual',
                status=EventStatus.CONFIRMED,
                format=EventFormat.VIRTUAL,
                volunteers_needed=3
            ),
            Event(
                title='Future Event',
                description='A future event',
                type=EventType.CAREER_FAIR,
                start_date=datetime.now() + timedelta(days=7),
                end_date=datetime.now() + timedelta(days=7, hours=4),
                location='Test Location 2',
                status=EventStatus.PUBLISHED,
                format=EventFormat.IN_PERSON,
                volunteers_needed=10
            )
        ]
        
        for event in events:
            db.session.add(event)
        db.session.commit()
        
        yield events
        
        # Clean up
        for event in events:
            existing = db.session.get(Event, event.id)
            if existing:
                db.session.delete(existing)
        db.session.commit() 
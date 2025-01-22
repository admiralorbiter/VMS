import pytest
from app import app as flask_app
from models import db
from config import TestingConfig
from models.user import User
from werkzeug.security import generate_password_hash
from datetime import date, datetime
from models.contact import *
from models.class_model import Class
from models.district_model import District
from models.event import *

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
        test_class = Class(
            salesforce_id='a005f000003XNa7AAG',
            name='Test Class 2024',
            school_salesforce_id='a015f000004XNa7AAG',
            class_year=2024
        )
        db.session.add(test_class)
        db.session.commit()
        yield test_class
        db.session.delete(test_class)
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
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            location='Test Location',
            status=EventStatus.DRAFT,
            volunteer_needed=5,
            format=EventFormat.IN_PERSON
        )
        db.session.add(event)
        db.session.commit()
        yield event
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
    from models.volunteer import Volunteer
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer',
            middle_name=''
        )
        db.session.add(volunteer)
        db.session.commit()
        yield volunteer
        db.session.delete(volunteer)
        db.session.commit()

@pytest.fixture
def test_skill(app):
    """Fixture for creating a test skill"""
    from models.volunteer import Skill
    with app.app_context():
        skill = Skill(
            name='Test Skill'
        )
        db.session.add(skill)
        db.session.commit()
        yield skill
        db.session.delete(skill)
        db.session.commit() 
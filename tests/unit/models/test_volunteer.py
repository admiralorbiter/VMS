import pytest
from models.organization import VolunteerOrganization
from models.volunteer import Volunteer, Skill, VolunteerSkill
from models.contact import EducationEnum, LocalStatusEnum, RaceEthnicityEnum
from models import db
from datetime import date, datetime
from models.contact import SkillSourceEnum
from models.volunteer import ConnectorData, ConnectorSubscriptionEnum
from models.contact import SalutationEnum, SuffixEnum, GenderEnum
from models.contact import Email, Phone, Address, ContactTypeEnum
from models.volunteer import Engagement, EventParticipation
from sqlalchemy.exc import IntegrityError

def test_new_volunteer(app):
    """Test creating a new volunteer"""
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer',
            middle_name='',
            organization_name='Test Corp',
            title='Software Engineer',
            department='Engineering',
            industry='Technology',
            education=EducationEnum.BACHELORS_DEGREE,
            local_status=LocalStatusEnum.local,
            race_ethnicity=RaceEthnicityEnum.white
        )
        
        db.session.add(volunteer)
        db.session.commit()
        
        # Test basic fields
        assert volunteer.id is not None
        assert volunteer.first_name == 'Test'
        assert volunteer.last_name == 'Volunteer'
        assert volunteer.organization_name == 'Test Corp'
        assert volunteer.title == 'Software Engineer'
        assert volunteer.department == 'Engineering'
        assert volunteer.industry == 'Technology'
        assert volunteer.education == EducationEnum.BACHELORS_DEGREE
        assert volunteer.local_status == LocalStatusEnum.local
        assert volunteer.race_ethnicity == RaceEthnicityEnum.white
        
        # Test default values
        assert volunteer.times_volunteered == 0
        assert volunteer.additional_volunteer_count == 0
        
        # Cleanup
        db.session.delete(volunteer)
        db.session.commit()

def test_volunteer_skills(app, test_volunteer, test_skill):
    """Test volunteer skills relationship"""
    with app.app_context():
        # Ensure test_volunteer is attached to the session
        test_volunteer = db.session.merge(test_volunteer)
        test_skill = db.session.merge(test_skill)
        
        # Create volunteer skill relationship
        volunteer_skill = VolunteerSkill(
            volunteer_id=test_volunteer.id,
            skill_id=test_skill.id,
            source=SkillSourceEnum.user_selected,
            interest_level='High'
        )
        
        db.session.add(volunteer_skill)
        db.session.commit()
        
        # Test relationships
        assert test_skill in test_volunteer.skills
        assert test_volunteer in test_skill.volunteers
        
        # Test relationship attributes
        vs = db.session.query(VolunteerSkill).filter_by(
            volunteer_id=test_volunteer.id,
            skill_id=test_skill.id
        ).first()
        assert vs.source == SkillSourceEnum.user_selected
        assert vs.interest_level == 'High'
        
        # Cleanup
        db.session.delete(vs)
        db.session.commit()

def test_volunteer_organization_relationship(app, test_volunteer, test_organization):
    """Test volunteer organization relationship"""
    with app.app_context():
        # Ensure test_volunteer is attached to the session
        test_volunteer = db.session.merge(test_volunteer)
        test_organization = db.session.merge(test_organization)
        
        # Add organization to volunteer
        test_volunteer.organizations.append(test_organization)
        db.session.commit()
        
        # Test relationships
        assert test_organization in test_volunteer.organizations
        assert test_volunteer in test_organization.volunteers
        
        # Test volunteer organization attributes
        vol_org = test_volunteer.volunteer_organizations[0]
        assert vol_org.volunteer_id == test_volunteer.id
        assert vol_org.organization_id == test_organization.id
        
        # Remove organization
        test_volunteer.organizations.remove(test_organization)
        db.session.commit()

def test_volunteer_engagement_history(app, test_volunteer):
    """Test volunteer engagement tracking"""
    with app.app_context():
        # Update volunteer engagement info
        test_volunteer.first_volunteer_date = date(2024, 1, 1)
        test_volunteer.last_volunteer_date = date(2024, 2, 1)
        test_volunteer.times_volunteered = 3
        test_volunteer.additional_volunteer_count = 2
        db.session.commit()
        
        # Test engagement summary
        # total_times_volunteered only includes event participations + additional_volunteer_count
        # It doesn't include times_volunteered field
        assert test_volunteer.total_times_volunteered == 2  # Only additional_volunteer_count
        assert test_volunteer.first_volunteer_date == date(2024, 1, 1)
        assert test_volunteer.last_volunteer_date == date(2024, 2, 1)

def test_active_histories(app, test_volunteer):
    """Test active histories property"""
    with app.app_context():
        from models.history import History
        
        # Create some histories
        active_history = History(
            volunteer_id=test_volunteer.id,
            activity_date=datetime.now(),
            activity_type='Test Activity',
            is_deleted=False
        )
        deleted_history = History(
            volunteer_id=test_volunteer.id,
            activity_date=datetime.now(),
            activity_type='Deleted Activity',
            is_deleted=True
        )
        
        db.session.add_all([active_history, deleted_history])
        db.session.commit()
        
        # Test active_histories property
        histories = test_volunteer.active_histories
        assert len(histories) == 1
        assert histories[0].activity_type == 'Test Activity'
        assert histories[0].is_deleted is False
        
        # Cleanup
        db.session.delete(active_history)
        db.session.delete(deleted_history)
        db.session.commit()

def test_volunteer_cascade_delete(app, test_volunteer):
    """Test cascade delete behavior for volunteer relationships"""
    with app.app_context():
        # Ensure test_volunteer is attached to current session
        test_volunteer = db.session.merge(test_volunteer)
        
        # Create related records
        connector = ConnectorData(
            volunteer_id=test_volunteer.id,
            active_subscription=ConnectorSubscriptionEnum.ACTIVE,
            role='Test Role'
        )
        db.session.add(connector)
        
        skill = Skill(name='Test Skill')
        db.session.add(skill)
        db.session.flush()
        
        vol_skill = VolunteerSkill(
            volunteer_id=test_volunteer.id,
            skill_id=skill.id,
            source=SkillSourceEnum.user_selected
        )
        db.session.add(vol_skill)
        db.session.commit()
        
        # Store IDs for verification
        connector_id = connector.id
        vol_skill_id = vol_skill.volunteer_id
        
        # Delete volunteer
        db.session.delete(test_volunteer)
        db.session.commit()
        
        # Verify cascade deletes
        assert db.session.get(ConnectorData, connector_id) is None
        assert db.session.query(VolunteerSkill).filter_by(
            volunteer_id=vol_skill_id).first() is None

def test_volunteer_validation(app):
    """Test volunteer field validation"""
    with app.app_context():
        with pytest.raises(ValueError):
            volunteer = Volunteer(
                first_name='Test',
                last_name='Volunteer',
                education='InvalidEducation'  # This should raise ValueError since it's not an EducationEnum
            )

def test_volunteer_required_fields(app):
    """Test volunteer creation with required fields"""
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer'
        )
        db.session.add(volunteer)
        db.session.commit()
        assert volunteer.id is not None
        
        # Test polymorphic identity
        assert volunteer.type == 'volunteer'
        
        db.session.delete(volunteer)
        db.session.commit()

def test_volunteer_contact_inheritance(app):
    """Test volunteer inherits contact properties correctly"""
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer',
            salutation=SalutationEnum.mr,
            suffix=SuffixEnum.phd,
            gender=GenderEnum.male,
            race_ethnicity=RaceEthnicityEnum.white
        )
        db.session.add(volunteer)
        db.session.commit()
        
        # Test inherited fields
        assert volunteer.salutation == SalutationEnum.mr
        assert volunteer.suffix == SuffixEnum.phd
        assert volunteer.gender == GenderEnum.male
        
        db.session.delete(volunteer)
        db.session.commit()

def test_volunteer_contact_info(app, test_volunteer):
    """Test volunteer contact information relationships"""
    with app.app_context():
        # Add email
        email = Email(
            email='test@example.com',
            type=ContactTypeEnum.personal,
            primary=True,
            contact_id=test_volunteer.id
        )
        
        # Add phone
        phone = Phone(
            number='123-456-7890',
            type=ContactTypeEnum.personal,
            primary=True,
            contact_id=test_volunteer.id
        )
        
        # Add address
        address = Address(
            address_line1='123 Test St',
            city='Kansas City',
            state='MO',
            zip_code='64111',
            type=ContactTypeEnum.personal,
            primary=True,
            contact_id=test_volunteer.id
        )
        
        db.session.add_all([email, phone, address])
        db.session.commit()
        
        # Test relationships
        assert test_volunteer.primary_email == 'test@example.com'
        assert test_volunteer.primary_phone == '123-456-7890'
        assert len(test_volunteer.addresses.all()) == 1
        
        # Test local status calculation
        assert test_volunteer.calculate_local_status() == LocalStatusEnum.local 

def test_volunteer_organization_details(app, test_volunteer, test_organization):
    """Test volunteer organization relationship with full details"""
    with app.app_context():
        vol_org = VolunteerOrganization(
            volunteer_id=test_volunteer.id,
            organization_id=test_organization.id,
            role='Software Engineer',
            start_date=datetime.now(),
            is_primary=True,
            status='Current'
        )
        db.session.add(vol_org)
        db.session.commit()
        
        # Test relationship details
        assert len(test_volunteer.volunteer_organizations) == 1
        org_rel = test_volunteer.volunteer_organizations[0]
        assert org_rel.role == 'Software Engineer'
        assert org_rel.is_primary is True
        assert org_rel.status == 'Current' 

def test_connector_data_lifecycle(app, test_volunteer):
    """Test connector data creation and updates"""
    with app.app_context():
        test_volunteer = db.session.merge(test_volunteer)
        
        connector = ConnectorData(
            volunteer_id=test_volunteer.id,
            active_subscription=ConnectorSubscriptionEnum.ACTIVE,
            role='Member',
            signup_role='Volunteer',
            profile_link='https://example.com/profile',
            industry='Technology'
        )
        db.session.add(connector)
        db.session.commit()
        
        # Refresh the session to ensure we get updated data
        db.session.refresh(test_volunteer)
        
        # Test update
        connector.active_subscription = ConnectorSubscriptionEnum.INACTIVE
        db.session.commit()
        db.session.refresh(test_volunteer)
        assert test_volunteer.connector.active_subscription == ConnectorSubscriptionEnum.INACTIVE

def test_volunteer_engagement_tracking(app, test_volunteer, test_event):
    """Test volunteer engagement tracking and history"""
    with app.app_context():
        test_volunteer = db.session.merge(test_volunteer)
        test_event = db.session.merge(test_event)
        
        # Create engagement
        engagement = Engagement(
            volunteer_id=test_volunteer.id,
            engagement_date=date.today(),
            engagement_type='Meeting',
            notes='Initial meeting'
        )
        db.session.add(engagement)
        db.session.commit()
        
        # Create event participation with valid event_id
        participation = EventParticipation(
            volunteer_id=test_volunteer.id,
            event_id=test_event.id,
            status='Confirmed',
            delivery_hours=2.5
        )
        db.session.add(participation)
        db.session.commit()
        
        # Refresh to get updated data
        db.session.refresh(test_volunteer)
        assert len(test_volunteer.engagements.all()) == 1
        assert len(test_volunteer.event_participations) == 1
        
        # Clean up participation before test_event fixture cleanup
        db.session.delete(participation)
        db.session.commit()

def test_local_status_calculation(app, test_volunteer):
    """Test local status calculation with different addresses"""
    with app.app_context():
        # Test KC metro address
        kc_address = Address(
            contact_id=test_volunteer.id,
            address_line1='123 Main St',
            city='Kansas City',
            state='MO',
            zip_code='64111',
            primary=True
        )
        db.session.add(kc_address)
        db.session.commit()
        assert test_volunteer.calculate_local_status() == LocalStatusEnum.local
        
        # Test non-local address
        kc_address.zip_code = '90210'
        db.session.commit()
        assert test_volunteer.calculate_local_status() == LocalStatusEnum.non_local 

def test_education_validation(app):
    """Test education validation"""
    with app.app_context():
        with pytest.raises(ValueError):
            volunteer = Volunteer(
                first_name='Test',
                last_name='Volunteer',
                education='Invalid Value'  # Should raise ValueError
            )
            db.session.add(volunteer)
            db.session.commit() 

def test_date_validation(app):
    """Test date field validation methods"""
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer'
        )
        
        # Test valid date string
        assert volunteer.validate_dates('first_volunteer_date', '2024-01-01') == date(2024, 1, 1)
        
        # Test invalid date string
        assert volunteer.validate_dates('first_volunteer_date', 'invalid-date') is None
        
        # Test None value
        assert volunteer.validate_dates('first_volunteer_date', None) is None
        
        # Test actual date object
        test_date = date(2024, 1, 1)
        assert volunteer.validate_dates('first_volunteer_date', test_date) == test_date

def test_count_validation(app):
    """Test count field validation methods"""
    with app.app_context():
        volunteer = Volunteer(
            first_name='Test',
            last_name='Volunteer'
        )
        
        # Test integer values
        assert volunteer.validate_counts('times_volunteered', 5) == 5
        
        # Test string numbers
        assert volunteer.validate_counts('times_volunteered', '5') == 5
        
        # Test float values
        assert volunteer.validate_counts('times_volunteered', 5.7) == 5
        
        # Test negative values (should return 0)
        assert volunteer.validate_counts('times_volunteered', -1) == 0
        
        # Test invalid values
        assert volunteer.validate_counts('times_volunteered', 'invalid') == 0
        assert volunteer.validate_counts('times_volunteered', None) == 0 

def test_local_status_edge_cases(app, test_volunteer):
    """Test local status calculation edge cases"""
    with app.app_context():
        # Ensure test_volunteer is attached to current session
        test_volunteer = db.session.merge(test_volunteer)
        
        # Test with no addresses
        assert test_volunteer.calculate_local_status() == LocalStatusEnum.unknown
        
        # Test with multiple addresses (primary and home)
        primary_addr = Address(
            contact_id=test_volunteer.id,
            address_line1='123 Main St',
            city='Kansas City',
            state='MO',
            zip_code='64111',
            type=ContactTypeEnum.professional,
            primary=True
        )
        home_addr = Address(
            contact_id=test_volunteer.id,
            address_line1='456 Home St',
            city='Lawrence',
            state='KS',
            zip_code='66044',
            type=ContactTypeEnum.personal,
            primary=False
        )
        
        # Add addresses and verify initial state
        db.session.add_all([primary_addr, home_addr])
        db.session.commit()
        
        assert test_volunteer.calculate_local_status() == LocalStatusEnum.local
        
        # Instead of raw SQL, modify the address object directly
        primary_addr.zip_code = None
        db.session.commit()
        
        # Force a clean reload of the volunteer and its relationships
        db.session.expire_all()
        test_volunteer = db.session.get(Volunteer, test_volunteer.id)
        
        assert test_volunteer.calculate_local_status() == LocalStatusEnum.partial

        print("\nDEBUG after zip_code change:")
        print("Primary address zip:", primary_addr.zip_code)
        print("All addresses:", [(a.zip_code, a.primary, a.type) for a in test_volunteer.addresses])

def test_connector_data_constraints(app, test_volunteer):
    """Test connector data constraints and unique fields"""
    with app.app_context():
        # Create first connector
        connector1 = ConnectorData(
            volunteer_id=test_volunteer.id,
            active_subscription=ConnectorSubscriptionEnum.ACTIVE,
            user_auth_id='ABC1234'
        )
        db.session.add(connector1)
        db.session.commit()
        
        # Test unique user_auth_id constraint
        with pytest.raises(IntegrityError):  # Changed from generic Exception
            connector2 = ConnectorData(
                volunteer_id=test_volunteer.id,
                active_subscription=ConnectorSubscriptionEnum.ACTIVE,
                user_auth_id='ABC1234'  # Duplicate user_auth_id
            )
            db.session.add(connector2)
            db.session.commit()
        
        db.session.rollback()
        
        # For one-to-one relationship test, we need to flush to see the error
        with pytest.raises(IntegrityError):  # Changed from generic Exception
            connector3 = ConnectorData(
                volunteer_id=test_volunteer.id,
                active_subscription=ConnectorSubscriptionEnum.ACTIVE,
                user_auth_id='XYZ9876'
            )
            db.session.add(connector3)
            db.session.flush()  # Changed from commit() to flush() 
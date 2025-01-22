import pytest
from models.volunteer import Volunteer, Skill, VolunteerSkill
from models.contact import EducationEnum, LocalStatusEnum, RaceEthnicityEnum
from models import db
from datetime import date, datetime
from models.contact import SkillSourceEnum

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
            education=EducationEnum.bachelors_degree,
            local_status=LocalStatusEnum.true,
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
        assert volunteer.education == EducationEnum.bachelors_degree
        assert volunteer.local_status == LocalStatusEnum.true
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
        assert test_volunteer.total_times_volunteered == 5
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
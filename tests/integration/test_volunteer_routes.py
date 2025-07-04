import pytest
from flask import url_for
from models import db
from models.volunteer import Volunteer, Skill
from models.contact import Email, Phone, GenderEnum, RaceEthnicityEnum, LocalStatusEnum
import json

def test_volunteers_list_view(client, auth_headers, test_volunteer):
    """Test the volunteers list view"""
    response = client.get('/volunteers', headers=auth_headers)
    assert response.status_code == 200
    assert b'Test Volunteer' in response.data

def test_volunteer_detail_view(client, auth_headers, test_volunteer):
    """Test viewing a single volunteer's details"""
    response = client.get(f'/volunteers/view/{test_volunteer.id}', headers=auth_headers)
    assert response.status_code == 200
    assert test_volunteer.first_name.encode() in response.data
    assert test_volunteer.last_name.encode() in response.data

def test_add_volunteer(client, auth_headers, app):
    """Test adding a new volunteer"""
    with app.app_context():
        # Create skills first
        skill_names = ["Python", "JavaScript"]
        for skill_name in skill_names:
            if not Skill.query.filter_by(name=skill_name).first():
                skill = Skill(name=skill_name)
                db.session.add(skill)
        db.session.commit()

        data = {
            'first_name': 'New',
            'last_name': 'Volunteer',
            'email': 'new.volunteer@example.com',
            'phone': '123-456-7890',
            'organization_name': 'Test Org',
            'title': 'Developer',
            'gender': GenderEnum.other.name,
            'local_status': LocalStatusEnum.local.name,
            'race_ethnicity': RaceEthnicityEnum.white.name,
            'skills': json.dumps(skill_names)  # JSON string of skills
        }
        
        response = client.post('/volunteers/add', 
                             data=data,
                             headers=auth_headers,
                             follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify volunteer was created
        volunteer = Volunteer.query.filter_by(
            first_name='New',
            last_name='Volunteer'
        ).first()
        assert volunteer is not None
        assert volunteer.organization_name == 'Test Org'
        
        # Verify email was created
        email = Email.query.filter_by(
            contact_id=volunteer.id,
            email='new.volunteer@example.com'
        ).first()
        assert email is not None
        
        # Verify phone was created
        phone = Phone.query.filter_by(
            contact_id=volunteer.id,
            number='123-456-7890'
        ).first()
        assert phone is not None
        
        # Verify skills were created
        assert len(volunteer.skills) == 2
        skill_names = {skill.name for skill in volunteer.skills}
        assert 'Python' in skill_names
        assert 'JavaScript' in skill_names

def test_edit_volunteer(client, auth_headers, test_volunteer, app):
    """Test editing an existing volunteer"""
    with app.app_context():
        # Ensure test_volunteer is attached to session
        volunteer = db.session.merge(test_volunteer)
        db.session.flush()
        
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'organization_name': 'New Org',
            'title': 'Senior Developer',
            'gender': GenderEnum.other.name,
            'local_status': LocalStatusEnum.local.name,
            'race_ethnicity': RaceEthnicityEnum.white.name,
            'phone': '987-654-3210',
            'phone_type': 'personal',
            'email': 'updated@example.com',
            'email_type': 'personal'
        }
        
        response = client.post(
            f'/volunteers/edit/{volunteer.id}',
            data=data,
            headers=auth_headers,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Get fresh instance from database
        updated_volunteer = db.session.get(Volunteer, volunteer.id)
        assert updated_volunteer is not None
        assert updated_volunteer.first_name == 'Updated'
        assert updated_volunteer.last_name == 'Name'
        assert updated_volunteer.organization_name == 'New Org'
        
        # Verify phone was updated
        phone = Phone.query.filter_by(contact_id=volunteer.id).first()
        assert phone is not None
        assert phone.number == '987-654-3210'

def test_delete_volunteer(client, auth_headers, test_volunteer, app):
    """Test deleting a volunteer"""
    with app.app_context():
        response = client.delete(
            f'/volunteers/delete/{test_volunteer.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json['success'] is True
        
        # Verify volunteer was deleted
        deleted_volunteer = db.session.get(Volunteer, test_volunteer.id)
        assert deleted_volunteer is None

def test_volunteer_search(client, auth_headers, test_volunteer, app):
    """Test searching for volunteers"""
    with app.app_context():
        # Test name search
        response = client.get(
            '/volunteers?search_name=Test',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert test_volunteer.first_name.encode() in response.data
        
        # Test organization search
        response = client.get(
            '/volunteers?org_search=Test Corp',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert test_volunteer.organization_name.encode() in response.data

def test_import_volunteers(client, auth_headers, test_admin, app):
    """Test importing volunteers from CSV"""
    with app.app_context():
        # Create CSV content
        csv_content = (
            "Id,FirstName,LastName,Title,Department\n"
            "003TEST123,CSV,Import,Developer,Engineering\n"
        )
        
        # Create file-like object
        from io import BytesIO
        file = (BytesIO(csv_content.encode()), 'test.csv')
        
        response = client.post(
            '/volunteers/import',
            data={'file': file},
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 200
        assert response.json['success'] is True
        
        # Verify volunteer was imported
        imported_volunteer = Volunteer.query.filter_by(
            first_name='CSV',
            last_name='Import'
        ).first()
        assert imported_volunteer is not None
        assert imported_volunteer.title == 'Developer'
        assert imported_volunteer.department == 'Engineering'

def test_volunteer_skills(client, auth_headers, test_volunteer, app):
    """Test volunteer skills management"""
    with app.app_context():
        # Create test skills
        skill1 = Skill(name="Python")
        skill2 = Skill(name="JavaScript")
        db.session.add_all([skill1, skill2])
        db.session.commit()

        # Test adding skills to volunteer
        data = {
            'first_name': test_volunteer.first_name,  # Keep existing data
            'last_name': test_volunteer.last_name,
            'skills': json.dumps(["Python", "JavaScript"]),
            # Add required form fields
            'gender': GenderEnum.other.name,
            'local_status': LocalStatusEnum.local.name,
            'race_ethnicity': RaceEthnicityEnum.white.name
        }
        
        response = client.post(
            f'/volunteers/edit/{test_volunteer.id}',
            data=data,
            headers=auth_headers,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Verify skills were added
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        assert len(volunteer.skills) == 2
        skill_names = {skill.name for skill in volunteer.skills}
        assert "Python" in skill_names
        assert "JavaScript" in skill_names

def test_volunteer_skill_model(app):
    """Test Skill model directly"""
    with app.app_context():
        # Test skill creation
        skill = Skill(name="Test Skill")
        db.session.add(skill)
        db.session.flush()  # This ensures the skill is in the session
        
        # Test string representation
        assert str(skill) == "Test Skill"
        
        # Test repr representation
        assert repr(skill) == "<Skill Test Skill>" 
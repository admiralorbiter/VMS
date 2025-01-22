import pytest
from models.school_model import School
from models import db

def test_new_school(app):
    """Test creating a new school"""
    with app.app_context():
        school = School(
            id='0015f00000TEST123',
            name='Test High School',
            normalized_name='TEST HIGH SCHOOL',
            school_code='4045'
        )
        
        db.session.add(school)
        db.session.commit()
        
        # Test basic fields
        assert school.id == '0015f00000TEST123'
        assert school.name == 'Test High School'
        assert school.normalized_name == 'TEST HIGH SCHOOL'
        assert school.school_code == '4045'
        
        # Test __repr__ method
        assert str(school) == '<School Test High School>'
        assert repr(school) == '<School Test High School>'
        
        # Cleanup
        db.session.delete(school)
        db.session.commit()

def test_school_district_relationship(app, test_district):
    """Test relationship between School and District"""
    with app.app_context():
        # Get a fresh instance of test_district
        district = db.session.get(test_district.__class__, test_district.id)
        
        school = School(
            id='0015f00000TEST456',
            name='District Test School',
            district_id=district.id
        )
        
        db.session.add(school)
        db.session.commit()
        
        # Get fresh instances
        school = db.session.get(School, school.id)
        district = db.session.get(district.__class__, district.id)
        
        # Test relationships
        assert school.district_id == district.id
        assert any(s.id == school.id for s in district.schools)
        
        # Cleanup
        db.session.delete(school)
        db.session.commit()

def test_school_cascade_delete(app):
    """Test cascade delete behavior"""
    with app.app_context():
        # Create district first
        from models.district_model import District
        district = District(
            id='0015f00000TEST999',
            name='Test District',
            district_code='9999'
        )
        db.session.add(district)
        db.session.commit()
        
        # Create school
        school = School(
            id='0015f00000TEST789',
            name='Cascade Test School',
            district_id=district.id
        )
        db.session.add(school)
        db.session.commit()
        
        # Store ID for verification
        school_id = school.id
        
        # Delete district
        db.session.delete(district)
        db.session.commit()
        
        # Verify school was deleted
        assert db.session.get(School, school_id) is None 
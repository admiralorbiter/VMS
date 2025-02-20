import pytest
from sqlalchemy.exc import IntegrityError
from models.district_model import District
from models import db

def test_new_district(app):
    """Test creating a new district"""
    with app.app_context():
        district = District(
            name='Test School District',
            district_code='4045',
            salesforce_id='0015f00000JVZsFAAX'
        )
        db.session.add(district)
        db.session.commit()
        
        assert district.name == 'Test School District'
        assert district.district_code == '4045'
        assert district.salesforce_id == '0015f00000JVZsFAAX'
        
        # Cleanup
        db.session.delete(district)
        db.session.commit()

def test_district_repr(app):
    """Test the string representation of a district"""
    with app.app_context():
        district = District(name='Test School District')
        assert str(district) == '<District Test School District>'
        assert repr(district) == '<District Test School District>'

def test_district_without_code(app):
    """Test creating a district without a district code"""
    with app.app_context():
        district = District(
            name='District Without Code',
            salesforce_id='0015f00000JVZsGAAX'
        )
        db.session.add(district)
        db.session.commit()
        
        assert district.district_code is None
        
        db.session.delete(district)
        db.session.commit()

@pytest.mark.parametrize('invalid_data,expected_error', [
    (
        {'salesforce_id': '0015f00000JVZsHAAX', 'name': None},  # Explicitly set name to None
        'NOT NULL constraint failed: district.name'
    )
])
def test_invalid_district_data(app, invalid_data, expected_error):
    """Test that invalid district data raises appropriate errors"""
    with app.app_context():
        district = District(**invalid_data)
        db.session.add(district)
        with pytest.raises(IntegrityError) as exc_info:
            db.session.flush()
        assert expected_error in str(exc_info.value)
        db.session.rollback()

def test_unique_salesforce_id(app):
    """Test that duplicate salesforce IDs are not allowed"""
    with app.app_context():
        district1 = District(
            name='Original District',
            salesforce_id='0015f00000JVZsIAAX'
        )
        db.session.add(district1)
        db.session.commit()
        
        duplicate_district = District(
            name='Duplicate District',
            salesforce_id='0015f00000JVZsIAAX'  # Same salesforce_id
        )
        with pytest.raises(IntegrityError):
            db.session.add(duplicate_district)
            db.session.flush()
        db.session.rollback()
        
        # Cleanup
        db.session.delete(district1)
        db.session.commit()

def test_district_name_update(app):
    """Test updating district name"""
    with app.app_context():
        district = District(
            name='Test School District',
            district_code='4045'
        )
        db.session.add(district)
        db.session.commit()
        
        district.name = 'Updated District Name'
        db.session.commit()
        
        assert district.name == 'Updated District Name'
        
        # Cleanup
        db.session.delete(district)
        db.session.commit()

def test_district_code_format(app):
    """Test different district code formats"""
    test_codes = ['4045', '48077-6080', 'ABC123', None]
    
    with app.app_context():
        for code in test_codes:
            district = District(
                name=f'District Test',
                district_code=code
            )
            db.session.add(district)
            db.session.commit()
            
            # Verify the code was saved correctly
            assert district.district_code == code
            
            db.session.delete(district)
            db.session.commit() 
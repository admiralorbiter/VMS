import pytest
from sqlalchemy.exc import IntegrityError
from models.district_model import District
from models import db

def test_new_district(test_district):
    """Test creating a new district"""
    assert test_district.id == '0015f00000JVZsFAAX'
    assert test_district.name == 'Test School District'
    assert test_district.district_code == '4045'

def test_district_repr(test_district):
    """Test the string representation of a district"""
    assert str(test_district) == '<District Test School District>'
    assert repr(test_district) == '<District Test School District>'

def test_district_without_code(app):
    """Test creating a district without a district code"""
    with app.app_context():
        district = District(
            id='0015f00000JVZsGAAX',
            name='District Without Code'
        )
        db.session.add(district)
        db.session.commit()
        
        assert district.district_code is None
        
        db.session.delete(district)
        db.session.commit()

@pytest.mark.parametrize('invalid_data,expected_error', [
    (
        {'name': 'Invalid District', 'id': None},  # Explicitly set id to None
        'NOT NULL constraint failed: district.id'
    ),
    (
        {'id': '0015f00000JVZsHAAX', 'name': None},  # Explicitly set name to None
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

def test_unique_district_id(app, test_district):
    """Test that duplicate district IDs are not allowed"""
    with app.app_context():
        duplicate_district = District(
            id=test_district.id,  # Same ID
            name='Duplicate District'
        )
        with pytest.raises(IntegrityError):
            db.session.add(duplicate_district)
            db.session.flush()  # Use flush instead of commit
        db.session.rollback()  # Roll back the failed transaction

def test_district_name_update(test_district):
    """Test updating district name"""
    test_district.name = 'Updated District Name'
    db.session.commit()
    
    assert test_district.name == 'Updated District Name'

def test_district_code_format(app):
    """Test different district code formats"""
    test_codes = ['4045', '48077-6080', 'ABC123', None]
    
    with app.app_context():
        for i, code in enumerate(test_codes):
            district = District(
                id=f'0015f00000JVZs{i}AAX',
                name=f'District {i}',
                district_code=code
            )
            db.session.add(district)
            db.session.commit()
            
            # Verify the code was saved correctly
            assert district.district_code == code
            
            db.session.delete(district)
            db.session.commit() 
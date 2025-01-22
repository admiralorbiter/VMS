import pytest
from datetime import datetime
from models.class_model import Class
from models import db

def test_new_class(test_class):
    """Test creating a new class"""
    assert test_class.salesforce_id == 'a005f000003XNa7AAG'
    assert test_class.name == 'Test Class 2024'
    assert test_class.school_salesforce_id == 'a015f000004XNa7AAG'
    assert test_class.class_year == 2024
    assert isinstance(test_class.created_at, datetime)
    assert isinstance(test_class.updated_at, datetime)

def test_class_repr(test_class):
    """Test the string representation of a class"""
    assert str(test_class) == '<Class Test Class 2024>'
    assert repr(test_class) == '<Class Test Class 2024>'

def test_class_timestamps(app):
    """Test that timestamps are automatically set"""
    with app.app_context():
        # Create a new class
        new_class = Class(
            salesforce_id='a005f000003XNa8AAG',
            name='Timestamp Test Class',
            school_salesforce_id='a015f000004XNa7AAG',
            class_year=2025
        )
        
        # Add to database
        db.session.add(new_class)
        db.session.commit()
        
        # Check timestamps were set
        assert new_class.created_at is not None
        assert new_class.updated_at is not None
        initial_updated_at = new_class.updated_at
        
        # Update the class
        new_class.name = 'Updated Test Class'
        db.session.commit()
        
        # Check that updated_at was changed but created_at wasn't
        assert new_class.updated_at > initial_updated_at
        
        # Cleanup
        db.session.delete(new_class)
        db.session.commit()

@pytest.mark.parametrize('invalid_data', [
    {
        'name': 'Invalid Class',
        'school_salesforce_id': 'a015f000004XNa7AAG',
        'class_year': 2024
        # Missing salesforce_id
    },
    {
        'salesforce_id': 'a005f000003XNa7AAG',
        'school_salesforce_id': 'a015f000004XNa7AAG',
        'class_year': 2024
        # Missing name
    },
    {
        'salesforce_id': 'a005f000003XNa7AAG',
        'name': 'Invalid Class',
        'class_year': 2024
        # Missing school_salesforce_id
    },
    {
        'salesforce_id': 'a005f000003XNa7AAG',
        'name': 'Invalid Class',
        'school_salesforce_id': 'a015f000004XNa7AAG'
        # Missing class_year
    }
])
def test_invalid_class_data(app, invalid_data):
    """Test that invalid class data raises appropriate errors"""
    with app.app_context():
        with pytest.raises(Exception):  # SQLAlchemy will raise an error for nullable=False violations
            invalid_class = Class(**invalid_data)
            db.session.add(invalid_class)
            db.session.commit()

def test_unique_salesforce_id(app, test_class):
    """Test that duplicate salesforce_ids are not allowed"""
    with app.app_context():
        duplicate_class = Class(
            salesforce_id=test_class.salesforce_id,  # Same salesforce_id
            name='Duplicate Class',
            school_salesforce_id='a015f000004XNa7AAG',
            class_year=2024
        )
        with pytest.raises(Exception):  # SQLAlchemy will raise an error for unique constraint violation
            db.session.add(duplicate_class)
            db.session.commit()

def test_class_year_validation(app):
    """Test class year validation"""
    with app.app_context():
        # Test with various class years
        valid_years = [2020, 2024, 2030]
        for year in valid_years:
            valid_class = Class(
                salesforce_id=f'a005f000003XNa{year}',
                name=f'Class of {year}',
                school_salesforce_id='a015f000004XNa7AAG',
                class_year=year
            )
            db.session.add(valid_class)
            db.session.commit()
            
            # Verify the year was saved correctly
            assert valid_class.class_year == year
            
            # Cleanup
            db.session.delete(valid_class)
            db.session.commit() 
import pytest
from datetime import datetime
from models.class_model import Class
from models import db
import sqlalchemy as sa
from sqlalchemy import text

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
    assert str(test_class) == f'<Class Test Class 2024 (2024)>'
    assert repr(test_class) == f'<Class Test Class 2024 (2024)>'

def test_class_timestamps(app, test_school):
    """Test that timestamps are automatically set"""
    with app.app_context():
        # Create a new class
        new_class = Class(
            salesforce_id='a005f000003XNa8AAG',
            name='Timestamp Test Class',
            school_salesforce_id=test_school.id,
            class_year=2025
        )
        
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

def test_relationship_school(app, test_class):
    """Test the relationship with School model"""
    with app.app_context():
        assert test_class.school is not None
        assert test_class.school.id == test_class.school_salesforce_id

def test_student_count_property(app, test_class):
    """Test the student_count property"""
    with app.app_context():
        print(f"\nDebug - students relationship type: {type(test_class.students)}")
        print(f"Debug - students count method available: {hasattr(test_class.students, 'count')}")
        assert test_class.student_count == 0

def test_salesforce_url_property(test_class):
    """Test the salesforce_url property"""
    expected_url = f"https://prep-kc.lightning.force.com/lightning/r/Class__c/{test_class.salesforce_id}/view"
    assert test_class.salesforce_url == expected_url

    # Use a new session to test with None salesforce_id
    with db.session.no_autoflush:
        test_class_none = Class(
            name='Test Class No SF',
            school_salesforce_id='a015f000004XNa7AAG',
            class_year=2024
        )
        assert test_class_none.salesforce_url is None

def test_to_dict_method(test_class):
    """Test the to_dict serialization method"""
    class_dict = test_class.to_dict()
    
    assert class_dict['id'] == test_class.id
    assert class_dict['salesforce_id'] == test_class.salesforce_id
    assert class_dict['name'] == test_class.name
    assert class_dict['school_salesforce_id'] == test_class.school_salesforce_id
    assert class_dict['class_year'] == test_class.class_year
    assert class_dict['student_count'] == test_class.student_count
    assert class_dict['created_at'] == test_class.created_at.isoformat()
    assert class_dict['updated_at'] == test_class.updated_at.isoformat()

def test_index_creation(app):
    """Test that indexes are properly created"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        indexes = inspector.get_indexes('class')
        
        # Print debug information
        print(f"\nDebug - Available indexes: {indexes}")
        
        # Check for required indexes
        index_columns = {tuple(idx['column_names']) for idx in indexes}
        required_indexes = {
            ('salesforce_id',),
            ('name',),
            ('school_salesforce_id',),
            ('class_year', 'school_salesforce_id')
        }
        
        for req_idx in required_indexes:
            assert req_idx in index_columns, f"Missing index for columns: {req_idx}"

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

def test_class_year_validation(app, test_school):
    """Test class year validation"""
    with app.app_context():
        valid_years = [2020, 2024, 2030]
        for year in valid_years:
            valid_class = Class(
                salesforce_id=f'a005f000003XNa{year}',
                name=f'Class of {year}',
                school_salesforce_id=test_school.id,
                class_year=year
            )
            db.session.add(valid_class)
            db.session.commit()
            
            # Verify the year was saved correctly
            assert valid_class.class_year == year
            
            # Cleanup
            db.session.delete(valid_class)
            db.session.commit()

def test_school_foreign_key_constraint(app):
    """Test that the foreign key constraint works"""
    with app.app_context():
        # Enable foreign key constraints for SQLite properly
        if str(db.engine.url).startswith('sqlite'):
            db.session.execute(text('PRAGMA foreign_keys=ON'))
            db.session.commit()
        
        with pytest.raises((sa.exc.IntegrityError, sa.exc.InvalidRequestError)):
            invalid_class = Class(
                salesforce_id='a005f000003XNa9AAG',
                name='Invalid School Class',
                school_salesforce_id='nonexistent_id',
                class_year=2024
            )
            db.session.add(invalid_class)
            db.session.commit() 
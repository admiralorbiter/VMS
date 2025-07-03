import pytest
import os
from models.google_sheet import GoogleSheet
from models.user import User
from models import db
from cryptography.fernet import Fernet

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            username='sheetuser',
            email='sheetuser@example.com',
            password_hash='hash',
            first_name='Sheet',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()

@pytest.fixture
def encryption_key():
    """Provide a test encryption key"""
    key = Fernet.generate_key()
    old_key = os.environ.get('ENCRYPTION_KEY')
    os.environ['ENCRYPTION_KEY'] = key.decode()
    yield key
    if old_key:
        os.environ['ENCRYPTION_KEY'] = old_key
    else:
        del os.environ['ENCRYPTION_KEY']

def test_create_google_sheet(app, test_user, encryption_key):
    with app.app_context():
        sheet_id = '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
        sheet = GoogleSheet(
            academic_year='2023-2024',
            sheet_id=sheet_id,
            created_by=test_user.id
        )
        db.session.add(sheet)
        db.session.commit()
        
        assert sheet.id is not None
        assert sheet.academic_year == '2023-2024'
        assert sheet.sheet_id != sheet_id  # Should be encrypted
        assert sheet.decrypted_sheet_id == sheet_id  # Should decrypt correctly
        assert sheet.created_by == test_user.id
        assert sheet.creator.username == 'sheetuser'
        assert sheet.created_at is not None
        assert sheet.updated_at is not None
        
        # Cleanup
        db.session.delete(sheet)
        db.session.commit()

def test_encryption_decryption(app, encryption_key):
    with app.app_context():
        original_sheet_id = 'test_sheet_id_12345'
        sheet = GoogleSheet(
            academic_year='2024-2025',
            sheet_id=original_sheet_id
        )
        db.session.add(sheet)
        db.session.commit()
        
        # Test that sheet_id is encrypted
        assert sheet.sheet_id != original_sheet_id
        assert len(sheet.sheet_id) > len(original_sheet_id)
        
        # Test decryption
        assert sheet.decrypted_sheet_id == original_sheet_id
        
        # Test update_sheet_id method
        new_sheet_id = 'new_sheet_id_67890'
        sheet.update_sheet_id(new_sheet_id)
        db.session.commit()
        assert sheet.decrypted_sheet_id == new_sheet_id
        
        db.session.delete(sheet)
        db.session.commit()

def test_academic_year_uniqueness(app, encryption_key):
    with app.app_context():
        sheet1 = GoogleSheet(
            academic_year='2023-2024',
            sheet_id='sheet1'
        )
        db.session.add(sheet1)
        db.session.commit()
        
        # Try to create another sheet with same academic year
        sheet2 = GoogleSheet(
            academic_year='2023-2024',
            sheet_id='sheet2'
        )
        db.session.add(sheet2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
        
        db.session.delete(sheet1)
        db.session.commit()

def test_user_relationship(app, test_user, encryption_key):
    with app.app_context():
        sheet = GoogleSheet(
            academic_year='2023-2024',
            sheet_id='test_sheet',
            created_by=test_user.id
        )
        db.session.add(sheet)
        db.session.commit()
        
        assert sheet.creator is not None
        assert sheet.creator.username == 'sheetuser'
        assert sheet.creator.email == 'sheetuser@example.com'
        
        db.session.delete(sheet)
        db.session.commit()

def test_to_dict_method(app, test_user, encryption_key):
    with app.app_context():
        sheet = GoogleSheet(
            academic_year='2023-2024',
            sheet_id='test_sheet_for_dict',
            created_by=test_user.id
        )
        db.session.add(sheet)
        db.session.commit()
        
        sheet_dict = sheet.to_dict()
        assert sheet_dict['id'] == sheet.id
        assert sheet_dict['academic_year'] == '2023-2024'
        assert sheet_dict['sheet_id'] == 'test_sheet_for_dict'  # Should be decrypted
        assert sheet_dict['created_by'] == test_user.id
        assert sheet_dict['creator_name'] == 'sheetuser'
        assert 'created_at' in sheet_dict
        assert 'updated_at' in sheet_dict
        
        db.session.delete(sheet)
        db.session.commit()

def test_missing_encryption_key(app):
    with app.app_context():
        # Remove encryption key from environment
        old_key = os.environ.get('ENCRYPTION_KEY')
        if 'ENCRYPTION_KEY' in os.environ:
            del os.environ['ENCRYPTION_KEY']
        
        try:
            # Should still work (generates new key)
            sheet = GoogleSheet(
                academic_year='2023-2024',
                sheet_id='test_sheet_no_key'
            )
            db.session.add(sheet)
            db.session.commit()
            
            # Should still be able to decrypt
            assert sheet.decrypted_sheet_id == 'test_sheet_no_key'
            
            db.session.delete(sheet)
            db.session.commit()
        finally:
            # Restore original key
            if old_key:
                os.environ['ENCRYPTION_KEY'] = old_key

def test_sheet_id_validation(app, encryption_key):
    with app.app_context():
        # Test with None sheet_id
        sheet = GoogleSheet(
            academic_year='2023-2024',
            sheet_id=None
        )
        db.session.add(sheet)
        db.session.commit()
        assert sheet.sheet_id is None
        assert sheet.decrypted_sheet_id is None
        
        # Test with empty string
        sheet2 = GoogleSheet(
            academic_year='2024-2025',
            sheet_id=''
        )
        db.session.add(sheet2)
        db.session.commit()
        assert sheet2.sheet_id is None
        assert sheet2.decrypted_sheet_id is None
        
        db.session.delete(sheet)
        db.session.delete(sheet2)
        db.session.commit()

def test_repr_method(app, encryption_key):
    with app.app_context():
        sheet = GoogleSheet(
            academic_year='2023-2024',
            sheet_id='test_sheet'
        )
        db.session.add(sheet)
        db.session.commit()
        
        assert repr(sheet) == '<GoogleSheet 2023-2024>'
        
        db.session.delete(sheet)
        db.session.commit() 
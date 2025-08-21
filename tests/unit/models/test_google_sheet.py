import os

import pytest

from models import db
from models.google_sheet import GoogleSheet
from models.user import User


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            username="sheetuser",
            email="sheetuser@example.com",
            password_hash="hash",
            first_name="Sheet",
            last_name="User",
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


def test_create_google_sheet(app, test_user):
    with app.app_context():
        sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        sheet = GoogleSheet(
            academic_year="2023-2024", sheet_id=sheet_id, created_by=test_user.id
        )
        db.session.add(sheet)
        db.session.commit()

        assert sheet.id is not None
        assert sheet.academic_year == "2023-2024"
        assert sheet.sheet_id == sheet_id  # Should be stored as plain text
        assert sheet.decrypted_sheet_id == sheet_id  # Should return the same value
        assert sheet.created_by == test_user.id
        assert sheet.creator.username == "sheetuser"
        assert sheet.created_at is not None
        assert sheet.updated_at is not None

        # Cleanup
        db.session.delete(sheet)
        db.session.commit()


def test_sheet_id_storage_and_retrieval(app):
    with app.app_context():
        original_sheet_id = "test_sheet_id_12345"
        sheet = GoogleSheet(academic_year="2024-2025", sheet_id=original_sheet_id)
        db.session.add(sheet)
        db.session.commit()

        # Test that sheet_id is stored as plain text
        assert sheet.sheet_id == original_sheet_id
        assert sheet.decrypted_sheet_id == original_sheet_id

        # Test update_sheet_id method
        new_sheet_id = "new_sheet_id_67890"
        sheet.update_sheet_id(new_sheet_id)
        db.session.commit()
        assert sheet.decrypted_sheet_id == new_sheet_id
        assert sheet.sheet_id == new_sheet_id

        db.session.delete(sheet)
        db.session.commit()


def test_multiple_district_reports_allowed(app):
    """Test that multiple district_reports sheets can be created for the same academic year"""
    with app.app_context():
        # Test that multiple district_reports sheets can be created for same academic year
        sheet1 = GoogleSheet(
            academic_year="2023-2024", sheet_id="sheet1", purpose="district_reports"
        )
        db.session.add(sheet1)
        db.session.commit()

        # Should be able to create another district_reports sheet with same academic year
        sheet2 = GoogleSheet(
            academic_year="2023-2024", sheet_id="sheet2", purpose="district_reports"
        )
        db.session.add(sheet2)
        db.session.commit()  # Should not raise an exception

        # Should be able to create a third one too
        sheet3 = GoogleSheet(
            academic_year="2023-2024", sheet_id="sheet3", purpose="district_reports"
        )
        db.session.add(sheet3)
        db.session.commit()  # Should not raise an exception

        # Verify all sheets exist
        sheets = GoogleSheet.query.filter_by(
            academic_year="2023-2024", purpose="district_reports"
        ).all()
        assert len(sheets) == 3

        # Cleanup
        db.session.delete(sheet1)
        db.session.delete(sheet2)
        db.session.delete(sheet3)
        db.session.commit()


def test_virtual_sessions_basic_functionality(app):
    """Test basic virtual sessions sheet functionality (constraint testing requires production DB)"""
    with app.app_context():
        # Test that virtual_sessions sheets can be created
        virtual_sheet = GoogleSheet(
            academic_year="2023-2024", sheet_id="virtual1", purpose="virtual_sessions"
        )
        db.session.add(virtual_sheet)
        db.session.commit()

        # Verify the sheet exists
        assert virtual_sheet.purpose == "virtual_sessions"
        assert virtual_sheet.academic_year == "2023-2024"

        # Cleanup
        db.session.delete(virtual_sheet)
        db.session.commit()


def test_user_relationship(app, test_user):
    with app.app_context():
        sheet = GoogleSheet(
            academic_year="2023-2024", sheet_id="test_sheet", created_by=test_user.id
        )
        db.session.add(sheet)
        db.session.commit()

        assert sheet.creator is not None
        assert sheet.creator.username == "sheetuser"
        assert sheet.creator.email == "sheetuser@example.com"

        db.session.delete(sheet)
        db.session.commit()


def test_to_dict_method(app, test_user):
    with app.app_context():
        sheet = GoogleSheet(
            academic_year="2023-2024",
            sheet_id="test_sheet_for_dict",
            created_by=test_user.id,
        )
        db.session.add(sheet)
        db.session.commit()

        sheet_dict = sheet.to_dict()
        assert sheet_dict["id"] == sheet.id
        assert sheet_dict["academic_year"] == "2023-2024"
        assert sheet_dict["sheet_id"] == "test_sheet_for_dict"  # Should be plain text
        assert sheet_dict["created_by"] == test_user.id
        assert sheet_dict["creator_name"] == "sheetuser"
        assert "created_at" in sheet_dict
        assert "updated_at" in sheet_dict

        db.session.delete(sheet)
        db.session.commit()


def test_sheet_id_validation(app):
    with app.app_context():
        # Test with None sheet_id
        sheet = GoogleSheet(academic_year="2023-2024", sheet_id=None)
        db.session.add(sheet)
        db.session.commit()
        assert sheet.sheet_id is None
        assert sheet.decrypted_sheet_id is None

        # Test with empty string
        sheet2 = GoogleSheet(academic_year="2024-2025", sheet_id="")
        db.session.add(sheet2)
        db.session.commit()
        assert sheet2.sheet_id == ""  # Empty string is stored as-is
        assert sheet2.decrypted_sheet_id == ""  # Empty string is returned as-is

        db.session.delete(sheet)
        db.session.delete(sheet2)
        db.session.commit()


def test_repr_method(app):
    with app.app_context():
        sheet = GoogleSheet(academic_year="2023-2024", sheet_id="test_sheet")
        db.session.add(sheet)
        db.session.commit()

        # The repr now includes the purpose field
        assert repr(sheet) == "<GoogleSheet 2023-2024 - district_reports>"

        # Test with virtual_sessions purpose
        virtual_sheet = GoogleSheet(
            academic_year="2024-2025",
            sheet_id="virtual_test_sheet",
            purpose="virtual_sessions",
        )
        db.session.add(virtual_sheet)
        db.session.commit()

        assert repr(virtual_sheet) == "<GoogleSheet 2024-2025 - virtual_sessions>"

        db.session.delete(sheet)
        db.session.delete(virtual_sheet)
        db.session.commit()

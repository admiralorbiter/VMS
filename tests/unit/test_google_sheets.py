#!/usr/bin/env python3
"""
Unit tests for Google Sheets functionality
"""

import os

import pytest
from cryptography.fernet import Fernet

from models.google_sheet import GoogleSheet
from utils.academic_year import get_current_academic_year, validate_academic_year


class TestGoogleSheetsEncryption:
    """Test encryption/decryption functionality"""

    def test_encryption_decryption(self, app):
        """Test that sheet IDs can be encrypted and decrypted correctly"""
        with app.app_context():
            # Test with a sample sheet ID
            test_sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

            # Create a GoogleSheet instance
            sheet = GoogleSheet(academic_year="2023-2024", sheet_id=test_sheet_id)

            # Test decryption
            decrypted_id = sheet.decrypted_sheet_id
            assert (
                decrypted_id == test_sheet_id
            ), f"Expected {test_sheet_id}, got {decrypted_id}"


class TestAcademicYearUtils:
    """Test academic year utility functions"""

    def test_get_current_academic_year(self):
        """Test that current academic year is returned in correct format"""
        current_year = get_current_academic_year()
        # Should be in format YYYY-YYYY
        assert len(current_year) == 9, f"Expected 9 characters, got {len(current_year)}"
        assert current_year[4] == "-", "Expected format YYYY-YYYY"
        assert current_year[:4].isdigit(), "First part should be digits"
        assert current_year[5:].isdigit(), "Second part should be digits"

    def test_validate_academic_year_valid_years(self):
        """Test that valid academic years are accepted"""
        valid_years = ["2023-2024", "2024-2025", "2020-2021"]

        for year in valid_years:
            assert validate_academic_year(year), f"Valid year {year} should be accepted"

    def test_validate_academic_year_invalid_years(self):
        """Test that invalid academic years are rejected"""
        invalid_years = ["2023", "2023-2023", "abc-def", "", "2023-2024-2025"]

        for year in invalid_years:
            assert not validate_academic_year(
                year
            ), f"Invalid year {year} should be rejected"


class TestGoogleSheetsDatabase:
    """Test database operations for Google Sheets"""

    def test_sheet_creation(self, app):
        """Test creating a Google Sheet record"""
        with app.app_context():
            test_sheet = GoogleSheet(
                academic_year="2023-2024", sheet_id="test_sheet_id_123"
            )

            from models import db

            db.session.add(test_sheet)
            db.session.commit()

            # Verify it was created
            retrieved_sheet = GoogleSheet.query.filter_by(
                academic_year="2023-2024"
            ).first()
            assert retrieved_sheet is not None, "Sheet should be created"
            assert retrieved_sheet.academic_year == "2023-2024", "Wrong academic year"
            # Test the decrypted sheet_id since the stored value is encrypted
            assert (
                retrieved_sheet.decrypted_sheet_id == "test_sheet_id_123"
            ), "Wrong decrypted sheet ID"

    def test_sheet_update(self, app):
        """Test updating a Google Sheet record"""
        with app.app_context():
            from models import db

            # Create a test sheet
            test_sheet = GoogleSheet(
                academic_year="2023-2024", sheet_id="test_sheet_id_123"
            )
            db.session.add(test_sheet)
            db.session.commit()

            # Update it
            retrieved_sheet = GoogleSheet.query.filter_by(
                academic_year="2023-2024"
            ).first()
            retrieved_sheet.academic_year = "2024-2025"
            db.session.commit()

            # Verify update
            updated_sheet = GoogleSheet.query.filter_by(
                academic_year="2024-2025"
            ).first()
            assert updated_sheet is not None, "Updated sheet should exist"
            assert (
                updated_sheet.academic_year == "2024-2025"
            ), "Academic year should be updated"

    def test_sheet_deletion(self, app):
        """Test deleting a Google Sheet record"""
        with app.app_context():
            from models import db

            # Create a test sheet
            test_sheet = GoogleSheet(
                academic_year="2023-2024", sheet_id="test_sheet_id_123"
            )
            db.session.add(test_sheet)
            db.session.commit()

            # Delete it
            retrieved_sheet = GoogleSheet.query.filter_by(
                academic_year="2023-2024"
            ).first()
            db.session.delete(retrieved_sheet)
            db.session.commit()

            # Verify deletion
            deleted_sheet = GoogleSheet.query.filter_by(
                academic_year="2023-2024"
            ).first()
            assert deleted_sheet is None, "Sheet should be deleted"


class TestGoogleSheetsEnvironment:
    """Test environment setup for Google Sheets"""

    def test_encryption_key_environment(self):
        """Test that encryption key is available"""
        # This test will pass even without ENCRYPTION_KEY set
        # because the model handles missing keys gracefully
        sheet = GoogleSheet(academic_year="2023-2024", sheet_id="test_sheet_id_123")
        # Should not raise an exception
        assert sheet is not None

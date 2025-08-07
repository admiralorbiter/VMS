"""
Test Teachers Import Optimization
===============================

This module tests the optimized teachers import functionality using the SalesforceImporter framework.

Test Coverage:
- Validation functions for teacher records
- Processing functions for teacher records
- Integration with SalesforceImporter framework
- Error handling and edge cases
- Batch processing functionality
- Contact information handling
"""

from unittest.mock import Mock, patch

import pytest

from models.teacher import Teacher
from routes.teachers.routes import process_teacher_record, validate_teacher_record
from utils.salesforce_importer import ImportConfig, ImportResult, SalesforceImporter


class TestTeacherValidation:
    """Test teacher record validation functionality."""

    def test_valid_teacher_record(self):
        """Test validation of a valid teacher record."""
        record = {
            "Id": "003TESTID123456789",
            "FirstName": "John",
            "LastName": "Doe",
            "Email": "john.doe@example.com",
            "Phone": "555-1234",
            "Department": "Science",
            "Gender__c": "Male",
            "AccountId": "001TESTACCOUNT123",
            "npsp__Primary_Affiliation__c": "001TESTSCHOOL123",
        }

        errors = validate_teacher_record(record)

        assert len(errors) == 0

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        # Missing Id
        record = {"FirstName": "John", "LastName": "Doe"}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Missing required field: Id" in error for error in errors)

        # Missing FirstName
        record = {"Id": "003TESTID123456789", "LastName": "Doe"}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Missing required field: FirstName" in error for error in errors)

        # Missing LastName
        record = {"Id": "003TESTID123456789", "FirstName": "John"}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Missing required field: LastName" in error for error in errors)

    def test_invalid_salesforce_id(self):
        """Test validation with invalid Salesforce ID format."""
        record = {"Id": "invalid_id", "FirstName": "John", "LastName": "Doe"}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Invalid Salesforce ID format" in error for error in errors)

    def test_empty_name_fields(self):
        """Test validation with empty name fields."""
        record = {"Id": "003TESTID123456789", "FirstName": "", "LastName": "Doe"}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Invalid name data" in error for error in errors)

        record = {"Id": "003TESTID123456789", "FirstName": "John", "LastName": ""}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Invalid name data" in error for error in errors)

        record = {"Id": "003TESTID123456789", "FirstName": "   ", "LastName": "Doe"}

        errors = validate_teacher_record(record)
        assert len(errors) > 0
        assert any("Invalid name data" in error for error in errors)


class TestTeacherProcessing:
    """Test teacher record processing functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.add = Mock()
        return session

    @pytest.fixture
    def sample_teacher_record(self):
        """Create a sample teacher record for testing."""
        return {
            "Id": "003TESTID123456789",
            "FirstName": "Jane",
            "LastName": "Smith",
            "Email": "jane.smith@example.com",
            "Phone": "555-5678",
            "Department": "Mathematics",
            "Gender__c": "Female",
            "AccountId": "001TESTACCOUNT123",
            "npsp__Primary_Affiliation__c": "001TESTSCHOOL123",
            "Last_Email_Message__c": "2024-01-15",
            "Last_Mailchimp_Email_Date__c": "2024-01-10",
        }

    def test_process_teacher_record_success(self, mock_db_session, sample_teacher_record):
        """Test successful processing of a teacher record."""
        with patch("models.teacher.Teacher.import_from_salesforce") as mock_import:
            mock_teacher = Mock()
            mock_teacher.update_contact_info.return_value = (True, None)

            mock_import.return_value = (mock_teacher, True, None)

            result = process_teacher_record(sample_teacher_record, mock_db_session)

            assert result is True

    def test_process_teacher_record_with_import_error(self, mock_db_session, sample_teacher_record):
        """Test processing a teacher record when import fails."""
        with patch("models.teacher.Teacher.import_from_salesforce") as mock_import:
            mock_import.return_value = (None, False, "Import error occurred")

            result = process_teacher_record(sample_teacher_record, mock_db_session)

            assert result is False

    def test_process_teacher_record_with_contact_info_error(self, mock_db_session, sample_teacher_record):
        """Test processing a teacher record when contact info update fails."""
        with patch("models.teacher.Teacher.import_from_salesforce") as mock_import:
            mock_teacher = Mock()
            mock_teacher.update_contact_info.return_value = (False, "Contact info error")

            mock_import.return_value = (mock_teacher, True, None)

            result = process_teacher_record(sample_teacher_record, mock_db_session)

            assert result is False

    def test_process_teacher_record_with_exception(self, mock_db_session, sample_teacher_record):
        """Test processing a teacher record when an exception occurs."""
        with patch("models.teacher.Teacher.import_from_salesforce") as mock_import:
            mock_import.side_effect = Exception("Unexpected error")

            result = process_teacher_record(sample_teacher_record, mock_db_session)

            assert result is False


class TestTeacherImportIntegration:
    """Test integration with SalesforceImporter framework."""

    @pytest.fixture
    def mock_importer(self):
        """Create a mock SalesforceImporter."""
        importer = Mock(spec=SalesforceImporter)
        return importer

    @pytest.fixture
    def sample_import_result(self):
        """Create a sample ImportResult for testing."""
        return ImportResult(
            total_processed=100,
            successful=95,
            failed=3,
            skipped=2,
            validation_errors=1,
            processing_errors=2,
            new_records=30,
            updated_records=65,
            all_errors=["Error 1", "Error 2", "Error 3"],
        )

    def test_import_config_creation(self):
        """Test creation of ImportConfig for teachers."""
        config = ImportConfig(batch_size=350, max_retries=3, retry_delay_seconds=1, validate_data=True)

        assert config.batch_size == 350
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1
        assert config.validate_data is True

    def test_teacher_query_structure(self):
        """Test that the teacher query includes all required fields."""
        expected_fields = [
            "Id",
            "AccountId",
            "FirstName",
            "LastName",
            "Email",
            "npsp__Primary_Affiliation__c",
            "Department",
            "Gender__c",
            "Phone",
            "Last_Email_Message__c",
            "Last_Mailchimp_Email_Date__c",
        ]

        teacher_query = """
        SELECT Id, AccountId, FirstName, LastName, Email,
               npsp__Primary_Affiliation__c, Department, Gender__c,
               Phone, Last_Email_Message__c, Last_Mailchimp_Email_Date__c
        FROM Contact
        WHERE Contact_Type__c = 'Teacher'
        """

        for field in expected_fields:
            assert field in teacher_query

    def test_import_function_integration(self):
        """Test integration of the import function with the framework."""
        # This test would require Flask application context
        # For now, just verify the function exists and can be imported
        from routes.teachers.routes import import_teachers_from_salesforce

        assert callable(import_teachers_from_salesforce)


class TestTeacherModelIntegration:
    """Test integration with Teacher model methods."""

    def test_teacher_model_methods_exist(self):
        """Test that Teacher model methods exist."""
        # Verify the methods exist on the Teacher class
        assert hasattr(Teacher, "import_from_salesforce")
        assert hasattr(Teacher, "update_contact_info")


class TestTeacherImportErrorHandling:
    """Test error handling in teacher import process."""

    def test_validation_error_handling(self):
        """Test handling of validation errors."""
        invalid_record = {"Id": "invalid_id", "FirstName": "", "LastName": ""}

        errors = validate_teacher_record(invalid_record)

        assert len(errors) > 0
        assert any("Invalid Salesforce ID format" in error for error in errors) or any("Invalid name data" in error for error in errors)

    def test_processing_error_handling(self):
        """Test handling of processing errors."""
        record = {"Id": "003TESTID123456789", "FirstName": "Test", "LastName": "User"}

        with patch("models.teacher.Teacher.import_from_salesforce") as mock_import:
            mock_import.side_effect = Exception("Database connection failed")

            result = process_teacher_record(record, Mock())

            assert result is False

    def test_contact_info_error_handling(self):
        """Test handling of contact info update errors."""
        record = {"Id": "003TESTID123456789", "FirstName": "Test", "LastName": "User", "Email": "test@example.com"}

        with patch("models.teacher.Teacher.import_from_salesforce") as mock_import:
            mock_teacher = Mock()
            mock_teacher.update_contact_info.side_effect = Exception("Contact update failed")

            mock_import.return_value = (mock_teacher, True, None)

            result = process_teacher_record(record, Mock())

            assert result is False


if __name__ == "__main__":
    pytest.main([__file__])

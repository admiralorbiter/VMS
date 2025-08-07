"""
Test Schools and Classes Import Functions
========================================

This module tests the optimized schools and classes import functions that use the new
SalesforceImporter framework.

Tests:
- District record validation
- District record processing
- School record validation
- School record processing
- Class record validation
- Class record processing
- Import function integration
"""

from unittest.mock import Mock, patch

from routes.management.management import (
    process_class_record,
    process_district_record,
    process_school_record,
    validate_class_record,
    validate_district_record,
    validate_school_record,
)


class TestDistrictValidation:
    """Test district record validation functions."""

    def test_validate_district_record_valid(self):
        """Test validation of a valid district record."""
        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test District",
            "School_Code_External_ID__c": "TD001",
        }

        is_valid, errors = validate_district_record(record)

        assert is_valid
        assert len(errors) == 0

    def test_validate_district_record_missing_id(self):
        """Test validation of district record missing Salesforce ID."""
        record = {
            "Name": "Test District",
            "School_Code_External_ID__c": "TD001",
        }

        is_valid, errors = validate_district_record(record)

        assert not is_valid
        assert "Missing Salesforce ID" in errors

    def test_validate_district_record_missing_name(self):
        """Test validation of district record missing name."""
        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "School_Code_External_ID__c": "TD001",
        }

        is_valid, errors = validate_district_record(record)

        assert not is_valid
        assert "Missing district name" in errors

    def test_validate_district_record_invalid_id_format(self):
        """Test validation of district record with invalid ID format."""
        record = {
            "Id": "123",  # Too short
            "Name": "Test District",
        }

        is_valid, errors = validate_district_record(record)

        assert not is_valid
        assert "Invalid Salesforce ID format" in errors

    def test_validate_district_record_name_too_long(self):
        """Test validation of district record with name too long."""
        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "A" * 300,  # Too long
        }

        is_valid, errors = validate_district_record(record)

        assert not is_valid
        assert "District name too long (max 255 characters)" in errors


class TestDistrictProcessing:
    """Test district record processing functions."""

    @patch("routes.management.management.ImportHelpers")
    def test_process_district_record_success(self, mock_helpers):
        """Test successful processing of a district record."""
        # Mock the helpers
        mock_district = Mock()
        mock_helpers.create_or_update_record.return_value = (mock_district, True)

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test District",
            "School_Code_External_ID__c": "TD001",
        }

        mock_session = Mock()

        success, error = process_district_record(record, mock_session)

        assert success
        assert error == ""
        mock_helpers.create_or_update_record.assert_called_once()

    @patch("routes.management.management.ImportHelpers")
    def test_process_district_record_error(self, mock_helpers):
        """Test error handling in district record processing."""
        # Mock the helpers to raise an exception
        mock_helpers.create_or_update_record.side_effect = Exception("Test error")

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test District",
        }

        mock_session = Mock()

        success, error = process_district_record(record, mock_session)

        assert not success
        assert "Test error" in error


class TestSchoolValidation:
    """Test school record validation functions."""

    def test_validate_school_record_valid(self):
        """Test validation of a valid school record."""
        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test School",
            "ParentId": "0011234567890ABCDE",  # 18 characters
            "Connector_Account_Name__c": "Test School Normalized",
            "School_Code_External_ID__c": "TS001",
        }

        is_valid, errors = validate_school_record(record)

        assert is_valid
        assert len(errors) == 0

    def test_validate_school_record_missing_id(self):
        """Test validation of school record missing Salesforce ID."""
        record = {
            "Name": "Test School",
            "ParentId": "0011234567890ABCDE",  # 18 characters
        }

        is_valid, errors = validate_school_record(record)

        assert not is_valid
        assert "Missing Salesforce ID" in errors

    def test_validate_school_record_missing_name(self):
        """Test validation of school record missing name."""
        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "ParentId": "0011234567890ABCDE",  # 18 characters
        }

        is_valid, errors = validate_school_record(record)

        assert not is_valid
        assert "Missing school name" in errors

    def test_validate_school_record_invalid_id_format(self):
        """Test validation of school record with invalid ID format."""
        record = {
            "Id": "123",  # Too short
            "Name": "Test School",
        }

        is_valid, errors = validate_school_record(record)

        assert not is_valid
        assert "Invalid Salesforce ID format" in errors

    def test_validate_school_record_name_too_long(self):
        """Test validation of school record with name too long."""
        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "A" * 300,  # Too long
        }

        is_valid, errors = validate_school_record(record)

        assert not is_valid
        assert "School name too long (max 255 characters)" in errors


class TestSchoolProcessing:
    """Test school record processing functions."""

    @patch("routes.management.management.School")
    @patch("routes.management.management.District")
    def test_process_school_record_success(self, mock_district, mock_school_class):
        """Test successful processing of a school record."""
        # Mock the session.query(School) call to return None (new school)
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session = Mock()
        mock_session.query.return_value = mock_query

        # Mock the district query
        mock_district_instance = Mock()
        mock_district_instance.id = 1
        mock_district.query.filter_by.return_value.first.return_value = mock_district_instance

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test School",
            "ParentId": "0011234567890ABCDE",  # 18 characters
            "Connector_Account_Name__c": "Test School Normalized",
            "School_Code_External_ID__c": "TS001",
        }

        success, error = process_school_record(record, mock_session)

        assert success
        assert error == ""
        # Verify that session.add was called for the new school
        mock_session.add.assert_called_once()

    @patch("routes.management.management.School")
    @patch("routes.management.management.District")
    def test_process_school_record_no_district(self, mock_district, mock_school_class):
        """Test processing of school record with no district found."""
        # Mock the session.query(School) call to return None (new school)
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session = Mock()
        mock_session.query.return_value = mock_query

        # Mock the district query to return None
        mock_district.query.filter_by.return_value.first.return_value = None

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test School",
            "ParentId": "0011234567890ABCDE",  # 18 characters
        }

        success, error = process_school_record(record, mock_session)

        assert success
        assert error == ""
        # Verify that session.add was called for the new school
        mock_session.add.assert_called_once()

    @patch("routes.management.management.School")
    @patch("routes.management.management.District")
    def test_process_school_record_error(self, mock_district, mock_school_class):
        """Test error handling in school record processing."""
        # Mock the session.query(School) call to raise an exception
        mock_query = Mock()
        mock_query.filter_by.side_effect = Exception("Test error")
        mock_session = Mock()
        mock_session.query.return_value = mock_query

        # Mock the district query to avoid Flask context issues
        mock_district.query.filter_by.return_value.first.return_value = None

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test School",
        }

        success, error = process_school_record(record, mock_session)

        assert not success
        assert "Test error" in error


class TestClassValidation:
    """Test class record validation functions."""

    def test_validate_class_record_valid(self):
        """Test validation of a valid class record."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert is_valid
        assert len(errors) == 0

    def test_validate_class_record_missing_id(self):
        """Test validation of class record missing Salesforce ID."""
        record = {
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Missing Salesforce ID" in errors

    def test_validate_class_record_missing_name(self):
        """Test validation of class record missing name."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Missing class name" in errors

    def test_validate_class_record_missing_school(self):
        """Test validation of class record missing school ID."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Missing school Salesforce ID" in errors

    def test_validate_class_record_missing_year(self):
        """Test validation of class record missing class year."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Missing class year" in errors

    def test_validate_class_record_invalid_id_format(self):
        """Test validation of class record with invalid ID format."""
        record = {
            "Id": "123",  # Too short
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Invalid Salesforce ID format" in errors

    def test_validate_class_record_invalid_school_id_format(self):
        """Test validation of class record with invalid school ID format."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "School__c": "123",  # Too short
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Invalid school Salesforce ID format" in errors

    def test_validate_class_record_name_too_long(self):
        """Test validation of class record with name too long."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "A" * 300,  # Too long
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Class name too long (max 255 characters)" in errors

    def test_validate_class_record_invalid_year(self):
        """Test validation of class record with invalid year."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "invalid",
        }

        is_valid, errors = validate_class_record(record)

        assert not is_valid
        assert "Class year must be a valid number" in errors


class TestClassProcessing:
    """Test class record processing functions."""

    @patch("routes.management.management.ImportHelpers")
    def test_process_class_record_success(self, mock_helpers):
        """Test successful processing of a class record."""
        # Mock the helpers
        mock_class = Mock()
        mock_helpers.create_or_update_record.return_value = (mock_class, True)

        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        mock_session = Mock()

        success, error = process_class_record(record, mock_session)

        assert success
        assert error == ""
        mock_helpers.create_or_update_record.assert_called_once()

    @patch("routes.management.management.ImportHelpers")
    def test_process_class_record_error(self, mock_helpers):
        """Test error handling in class record processing."""
        # Mock the helpers to raise an exception
        mock_helpers.create_or_update_record.side_effect = Exception("Test error")

        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
        }

        mock_session = Mock()

        success, error = process_class_record(record, mock_session)

        assert not success
        assert "Test error" in error

    @patch("routes.management.management.ImportHelpers")
    def test_process_class_record_verifies_salesforce_id_in_update_data(self, mock_helpers):
        """Test that salesforce_id is properly included in update_data for class records."""
        # Mock the helpers
        mock_class = Mock()
        mock_helpers.create_or_update_record.return_value = (mock_class, True)

        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "Name": "10th Grade Science",
            "School__c": "0011234567890ABCDE",  # 18 characters
            "Class_Year_Number__c": "2024",
        }

        mock_session = Mock()

        success, error = process_class_record(record, mock_session)

        assert success
        assert error == ""

        # Verify create_or_update_record was called with the correct parameters
        mock_helpers.create_or_update_record.assert_called_once()
        call_args = mock_helpers.create_or_update_record.call_args

        # Check that the first argument is the Class model
        assert call_args[0][0].__name__ == "Class"

        # Check that the second argument is the salesforce_id
        assert call_args[0][1] == "a0B1234567890ABCDE"

        # Check that the third argument (update_data) contains salesforce_id
        update_data = call_args[0][2]
        assert "salesforce_id" in update_data
        assert update_data["salesforce_id"] == "a0B1234567890ABCDE"

        # Check that the fourth argument is the session
        assert call_args[0][3] == mock_session


class TestImportIntegration:
    """Test integration with the SalesforceImporter framework."""

    def test_import_functions_exist(self):
        """Test that the import functions exist and are callable."""
        from routes.management.management import (
            import_classes,
            import_districts,
            import_schools,
        )

        # Verify the functions exist and are callable
        assert callable(import_classes)
        assert callable(import_districts)
        assert callable(import_schools)

    def test_validation_functions_exist(self):
        """Test that the validation functions exist and are callable."""
        from routes.management.management import (
            validate_class_record,
            validate_district_record,
            validate_school_record,
        )

        # Verify the functions exist and are callable
        assert callable(validate_district_record)
        assert callable(validate_school_record)
        assert callable(validate_class_record)

    def test_processing_functions_exist(self):
        """Test that the processing functions exist and are callable."""
        from routes.management.management import (
            process_class_record,
            process_district_record,
            process_school_record,
        )

        # Verify the functions exist and are callable
        assert callable(process_district_record)
        assert callable(process_school_record)
        assert callable(process_class_record)

    @patch("routes.management.management.ImportHelpers")
    def test_process_district_record_verifies_salesforce_id_in_update_data(self, mock_helpers):
        """Test that salesforce_id is properly included in update_data for district records."""
        # Mock the helpers
        mock_district = Mock()
        mock_helpers.create_or_update_record.return_value = (mock_district, True)

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test District",
            "School_Code_External_ID__c": "TD001",
        }

        mock_session = Mock()

        success, error = process_district_record(record, mock_session)

        assert success
        assert error == ""

        # Verify create_or_update_record was called with the correct parameters
        mock_helpers.create_or_update_record.assert_called_once()
        call_args = mock_helpers.create_or_update_record.call_args

        # Check that the first argument is the District model
        assert call_args[0][0].__name__ == "District"

        # Check that the second argument is the salesforce_id
        assert call_args[0][1] == "0011234567890ABCDE"

        # Check that the third argument (update_data) contains salesforce_id
        update_data = call_args[0][2]
        assert "salesforce_id" in update_data
        assert update_data["salesforce_id"] == "0011234567890ABCDE"

        # Check that the fourth argument is the session
        assert call_args[0][3] == mock_session

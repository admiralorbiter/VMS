"""
Test Organizations Import Functions
=================================

This module tests the optimized organizations import functions that use the new
SalesforceImporter framework.

Tests:
- Organization record validation
- Organization record processing
- Affiliation record validation
- Affiliation record processing
- Import function integration
"""

from datetime import datetime
from unittest.mock import Mock, patch

from routes.organizations.routes import process_affiliation_record, process_organization_record, validate_affiliation_record, validate_organization_record


class TestOrganizationValidation:
    """Test organization record validation functions."""

    def test_validate_organization_record_valid(self):
        """Test validation of a valid organization record."""
        record = {"Id": "0011234567890ABCDE", "Name": "Test Organization", "Type": "Business", "Description": "Test description"}  # 18 characters

        is_valid, errors = validate_organization_record(record)

        assert is_valid
        assert len(errors) == 0

    def test_validate_organization_record_missing_id(self):
        """Test validation of organization record missing Salesforce ID."""
        record = {"Name": "Test Organization", "Type": "Business"}

        is_valid, errors = validate_organization_record(record)

        assert not is_valid
        assert "Missing Salesforce ID" in errors

    def test_validate_organization_record_missing_name(self):
        """Test validation of organization record missing name."""
        record = {"Id": "0011234567890ABCDE", "Type": "Business"}  # 18 characters

        is_valid, errors = validate_organization_record(record)

        assert not is_valid
        assert "Missing organization name" in errors

    def test_validate_organization_record_invalid_id_format(self):
        """Test validation of organization record with invalid ID format."""
        record = {"Id": "123", "Name": "Test Organization"}  # Too short

        is_valid, errors = validate_organization_record(record)

        assert not is_valid
        assert "Invalid Salesforce ID format" in errors

    def test_validate_organization_record_name_too_long(self):
        """Test validation of organization record with name too long."""
        record = {"Id": "0011234567890ABCDE", "Name": "A" * 300}  # 18 characters  # Too long

        is_valid, errors = validate_organization_record(record)

        assert not is_valid
        assert "Organization name too long (max 255 characters)" in errors


class TestOrganizationProcessing:
    """Test organization record processing functions."""

    @patch("routes.organizations.routes.ImportHelpers")
    @patch("routes.organizations.routes.parse_date")
    def test_process_organization_record_success(self, mock_parse_date, mock_helpers):
        """Test successful processing of an organization record."""
        # Mock the helpers
        mock_org = Mock()
        mock_helpers.create_or_update_record.return_value = (mock_org, True)
        mock_parse_date.return_value = datetime(2023, 1, 1)

        record = {
            "Id": "0011234567890ABCDE",  # 18 characters
            "Name": "Test Organization",
            "Type": "Business",
            "Description": "Test description",
            "BillingStreet": "123 Main St",
            "BillingCity": "Test City",
            "BillingState": "TS",
            "BillingPostalCode": "12345",
            "BillingCountry": "USA",
            "LastActivityDate": "2023-01-01",
        }

        mock_session = Mock()

        success, error = process_organization_record(record, mock_session)

        assert success
        assert error == ""
        mock_helpers.create_or_update_record.assert_called_once()
        mock_parse_date.assert_called_once_with("2023-01-01")

    @patch("routes.organizations.routes.ImportHelpers")
    def test_process_organization_record_error(self, mock_helpers):
        """Test error handling in organization record processing."""
        # Mock the helpers to raise an exception
        mock_helpers.create_or_update_record.side_effect = Exception("Test error")

        record = {"Id": "0011234567890ABCDE", "Name": "Test Organization"}  # 18 characters

        mock_session = Mock()

        success, error = process_organization_record(record, mock_session)

        assert not success
        assert "Test error" in error


class TestAffiliationValidation:
    """Test affiliation record validation functions."""

    def test_validate_affiliation_record_valid(self):
        """Test validation of a valid affiliation record."""
        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "npe5__Organization__c": "0011234567890ABCDE",  # 18 characters
            "npe5__Contact__c": "0031234567890ABCDE",  # 18 characters
            "npe5__Role__c": "Employee",
            "npe5__Primary__c": "true",
            "npe5__Status__c": "Current",
        }

        is_valid, errors = validate_affiliation_record(record)

        assert is_valid
        assert len(errors) == 0

    def test_validate_affiliation_record_missing_organization(self):
        """Test validation of affiliation record missing organization ID."""
        record = {"Id": "a0B1234567890ABCDE", "npe5__Contact__c": "0031234567890ABCDE"}  # 18 characters  # 18 characters

        is_valid, errors = validate_affiliation_record(record)

        assert not is_valid
        assert "Missing organization Salesforce ID" in errors

    def test_validate_affiliation_record_missing_contact(self):
        """Test validation of affiliation record missing contact ID."""
        record = {"Id": "a0B1234567890ABCDE", "npe5__Organization__c": "0011234567890ABCDE"}  # 18 characters  # 18 characters

        is_valid, errors = validate_affiliation_record(record)

        assert not is_valid
        assert "Missing contact Salesforce ID" in errors


class TestAffiliationProcessing:
    """Test affiliation record processing functions."""

    @patch("routes.organizations.routes.Organization")
    @patch("routes.organizations.routes.Contact")
    @patch("routes.organizations.routes.VolunteerOrganization")
    @patch("routes.organizations.routes.parse_date")
    def test_process_affiliation_record_success(self, mock_parse_date, mock_vol_org, mock_contact, mock_org):
        """Test successful processing of an affiliation record."""
        # Mock the models
        mock_org_instance = Mock()
        mock_org.query.filter_by.return_value.first.return_value = mock_org_instance

        mock_contact_instance = Mock()
        mock_contact.query.filter_by.return_value.first.return_value = mock_contact_instance

        mock_vol_org_instance = Mock()
        mock_vol_org.query.filter_by.return_value.first.return_value = None  # New relationship
        mock_vol_org.return_value = mock_vol_org_instance

        mock_parse_date.return_value = datetime(2023, 1, 1)

        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "npe5__Organization__c": "0011234567890ABCDE",  # 18 characters
            "npe5__Contact__c": "0031234567890ABCDE",  # 18 characters
            "npe5__Role__c": "Employee",
            "npe5__Primary__c": "true",
            "npe5__Status__c": "Current",
            "npe5__StartDate__c": "2023-01-01",
            "npe5__EndDate__c": "2023-12-31",
        }

        mock_session = Mock()

        success, error = process_affiliation_record(record, mock_session)

        assert success
        assert error == ""
        mock_session.add.assert_called_with(mock_vol_org_instance)
        mock_parse_date.assert_called()

    @patch("routes.organizations.routes.Organization")
    @patch("routes.organizations.routes.Contact")
    @patch("routes.organizations.routes.School")
    @patch("routes.organizations.routes.District")
    def test_process_affiliation_record_missing_organization(self, mock_district, mock_school, mock_contact, mock_org):
        """Test processing of affiliation record with missing organization."""
        # Mock the models to return None for organization, school, and district
        mock_org.query.filter_by.return_value.first.return_value = None
        mock_school.query.filter_by.return_value.first.return_value = None
        mock_district.query.filter_by.return_value.first.return_value = None

        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "npe5__Organization__c": "0011234567890ABCDE",  # 18 characters
            "npe5__Contact__c": "0031234567890ABCDE",  # 18 characters
        }

        mock_session = Mock()

        success, error = process_affiliation_record(record, mock_session)

        assert not success
        assert "Organization/School/District with Salesforce ID" in error

    @patch("routes.organizations.routes.Organization")
    @patch("routes.organizations.routes.Contact")
    def test_process_affiliation_record_missing_contact(self, mock_contact, mock_org):
        """Test processing of affiliation record with missing contact."""
        # Mock the models
        mock_org_instance = Mock()
        mock_org.query.filter_by.return_value.first.return_value = mock_org_instance

        mock_contact.query.filter_by.return_value.first.return_value = None

        record = {
            "Id": "a0B1234567890ABCDE",  # 18 characters
            "npe5__Organization__c": "0011234567890ABCDE",  # 18 characters
            "npe5__Contact__c": "0031234567890ABCDE",  # 18 characters
        }

        mock_session = Mock()

        success, error = process_affiliation_record(record, mock_session)

        assert not success
        assert "Contact (Volunteer/Teacher) with Salesforce ID" in error


class TestImportIntegration:
    """Test integration with the SalesforceImporter framework."""

    def test_import_functions_exist(self):
        """Test that the import functions exist and are callable."""
        from routes.organizations.routes import import_affiliations_from_salesforce, import_organizations_from_salesforce

        # Verify the functions exist and are callable
        assert callable(import_organizations_from_salesforce)
        assert callable(import_affiliations_from_salesforce)

    def test_validation_functions_exist(self):
        """Test that the validation functions exist and are callable."""
        from routes.organizations.routes import validate_affiliation_record, validate_organization_record

        # Verify the functions exist and are callable
        assert callable(validate_organization_record)
        assert callable(validate_affiliation_record)

    def test_processing_functions_exist(self):
        """Test that the processing functions exist and are callable."""
        from routes.organizations.routes import process_affiliation_record, process_organization_record

        # Verify the functions exist and are callable
        assert callable(process_organization_record)
        assert callable(process_affiliation_record)

"""
Test Suite for Salesforce Import Framework
========================================

This module contains comprehensive tests for the SalesforceImporter framework,
including validation, error handling, batch processing, and performance tests.

Test Categories:
- Unit tests for core functionality
- Integration tests for Salesforce connection
- Performance tests for batch processing
- Error handling tests
- Validation tests
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from utils.salesforce_importer import ImportConfig, ImportHelpers, ImportResult, SalesforceImporter


class TestImportConfig(unittest.TestCase):
    """Test ImportConfig dataclass functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ImportConfig()
        self.assertEqual(config.batch_size, 1000)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.retry_delay_seconds, 5)
        self.assertTrue(config.validate_data)
        self.assertTrue(config.log_progress)

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ImportConfig(batch_size=500, max_retries=5, retry_delay_seconds=10, validate_data=False, log_progress=False)
        self.assertEqual(config.batch_size, 500)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.retry_delay_seconds, 10)
        self.assertFalse(config.validate_data)
        self.assertFalse(config.log_progress)


class TestImportHelpers(unittest.TestCase):
    """Test ImportHelpers utility functions."""

    def test_safe_parse_int(self):
        """Test safe integer parsing."""
        self.assertEqual(ImportHelpers.safe_parse_int("123"), 123)
        self.assertEqual(ImportHelpers.safe_parse_int("123.45"), 123)
        self.assertEqual(ImportHelpers.safe_parse_int(None), 0)
        self.assertEqual(ImportHelpers.safe_parse_int("invalid"), 0)
        self.assertEqual(ImportHelpers.safe_parse_int("123", default=5), 123)
        self.assertEqual(ImportHelpers.safe_parse_int(None, default=5), 5)

    def test_safe_parse_float(self):
        """Test safe float parsing."""
        self.assertEqual(ImportHelpers.safe_parse_float("123.45"), 123.45)
        self.assertEqual(ImportHelpers.safe_parse_float("123"), 123.0)
        self.assertEqual(ImportHelpers.safe_parse_float(None), 0.0)
        self.assertEqual(ImportHelpers.safe_parse_float("invalid"), 0.0)
        self.assertEqual(ImportHelpers.safe_parse_float("123.45", default=5.5), 123.45)
        self.assertEqual(ImportHelpers.safe_parse_float(None, default=5.5), 5.5)

    def test_clean_string(self):
        """Test string cleaning."""
        self.assertEqual(ImportHelpers.clean_string("  test  "), "test")
        self.assertEqual(ImportHelpers.clean_string(None), "")
        self.assertEqual(ImportHelpers.clean_string(123), "123")
        self.assertEqual(ImportHelpers.clean_string(""), "")

    def test_validate_required_fields(self):
        """Test required field validation."""
        record = {"Id": "123", "Name": "Test", "Type": "Business"}

        # Valid record
        errors = ImportHelpers.validate_required_fields(record, ["Id", "Name"])
        self.assertEqual(errors, [])

        # Missing required field
        errors = ImportHelpers.validate_required_fields(record, ["Id", "Name", "Missing"])
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required field: Missing", errors[0])

        # Empty record
        errors = ImportHelpers.validate_required_fields({}, ["Id", "Name"])
        self.assertEqual(len(errors), 2)


class TestSalesforceImporter(unittest.TestCase):
    """Test SalesforceImporter core functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = ImportConfig(batch_size=2, max_retries=2, retry_delay_seconds=1, validate_data=True, log_progress=False)  # Small batch size for testing
        self.importer = SalesforceImporter(self.config)

    @patch("utils.salesforce_importer.Salesforce")
    def test_connect_salesforce_success(self, mock_salesforce):
        """Test successful Salesforce connection."""
        mock_sf = Mock()
        mock_salesforce.return_value = mock_sf

        result = self.importer._connect_salesforce()
        self.assertEqual(result, mock_sf)
        mock_salesforce.assert_called_once()

    @patch("utils.salesforce_importer.Salesforce")
    def test_connect_salesforce_retry(self, mock_salesforce):
        """Test Salesforce connection with retry logic."""
        from simple_salesforce.exceptions import SalesforceAuthenticationFailed

        # First call fails, second succeeds
        mock_salesforce.side_effect = [SalesforceAuthenticationFailed(code="AUTH_FAILED", message="Auth failed"), Mock()]

        result = self.importer._connect_salesforce()
        self.assertIsNotNone(result)
        self.assertEqual(mock_salesforce.call_count, 2)

    @patch("utils.salesforce_importer.Salesforce")
    def test_connect_salesforce_failure(self, mock_salesforce):
        """Test Salesforce connection failure after all retries."""
        from simple_salesforce.exceptions import SalesforceAuthenticationFailed

        mock_salesforce.side_effect = SalesforceAuthenticationFailed(code="AUTH_FAILED", message="Auth failed")

        with self.assertRaises(SalesforceAuthenticationFailed):
            self.importer._connect_salesforce()

    def test_validate_record_basic(self):
        """Test basic record validation."""
        # Valid record
        record = {"Id": "123456789012345678", "Name": "Test"}
        is_valid, errors = self.importer._validate_record(record)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

        # Invalid record - missing ID
        record = {"Name": "Test"}
        is_valid, errors = self.importer._validate_record(record)
        self.assertFalse(is_valid)
        self.assertIn("Missing Salesforce ID", errors)

    def test_validate_record_custom_validation(self):
        """Test record validation with custom validation function."""

        def custom_validation(record):
            errors = []
            if not record.get("Name"):
                errors.append("Name is required")
            return errors

        # Valid record
        record = {"Id": "123456789012345678", "Name": "Test"}
        is_valid, errors = self.importer._validate_record(record, custom_validation)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

        # Invalid record
        record = {"Id": "123456789012345678"}
        is_valid, errors = self.importer._validate_record(record, custom_validation)
        self.assertFalse(is_valid)
        self.assertIn("Name is required", errors)

    def test_process_batch_success(self):
        """Test successful batch processing."""
        records = [{"Id": "123", "Name": "Test1"}, {"Id": "456", "Name": "Test2"}]

        def process_func(record, session):
            return True  # Always succeed

        stats = {"success_count": 0, "error_count": 0, "skipped_count": 0}

        errors = self.importer._process_batch(records, process_func, Mock(), stats)

        self.assertEqual(errors, [])
        self.assertEqual(stats["success_count"], 2)
        self.assertEqual(stats["error_count"], 0)
        self.assertEqual(stats["skipped_count"], 0)

    def test_process_batch_with_errors(self):
        """Test batch processing with errors."""
        records = [{"Id": "123", "Name": "Test1"}, {"Id": "", "Name": "Test2"}, {"Id": "789", "Name": "Test3"}]  # Invalid - missing ID

        def process_func(record, session):
            if record["Id"] == "789":
                raise Exception("Processing error")
            return True

        stats = {"success_count": 0, "error_count": 0, "skipped_count": 0}

        errors = self.importer._process_batch(records, process_func, Mock(), stats)

        self.assertEqual(len(errors), 2)  # One validation error, one processing error
        self.assertEqual(stats["success_count"], 1)
        self.assertEqual(stats["error_count"], 2)
        self.assertEqual(stats["skipped_count"], 0)


class TestImportResult(unittest.TestCase):
    """Test ImportResult dataclass."""

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        start_time = datetime.now()
        end_time = datetime.now()

        result = ImportResult(
            success=True,
            total_records=100,
            processed_count=95,
            success_count=90,
            error_count=5,
            skipped_count=0,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            duration_seconds=10.5,
            start_time=start_time,
            end_time=end_time,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.total_records, 100)
        self.assertEqual(result.processed_count, 95)
        self.assertEqual(result.success_count, 90)
        self.assertEqual(result.error_count, 5)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.duration_seconds, 10.5)
        self.assertEqual(result.start_time, start_time)
        self.assertEqual(result.end_time, end_time)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete import workflow."""

    @patch("utils.salesforce_importer.Salesforce")
    def test_complete_import_workflow(self, mock_salesforce):
        """Test complete import workflow with mocked Salesforce."""
        from app import app

        # Use existing Flask app context
        with app.app_context():
            # Mock Salesforce connection
            mock_sf = Mock()
            mock_salesforce.return_value = mock_sf

            # Mock query result
            mock_sf.query_all.return_value = {
                "records": [{"Id": "123456789012345678", "Name": "Test Org 1"}, {"Id": "876543210987654321", "Name": "Test Org 2"}]
            }

            # Create importer
            config = ImportConfig(batch_size=1, max_retries=1)
            importer = SalesforceImporter(config)

            # Define processing function
            def process_func(record, session):
                return True

            # Define validation function
            def validate_func(record):
                errors = []
                if not record.get("Id") or len(record["Id"]) != 18:
                    errors.append("Invalid Salesforce ID")
                return errors

            # Execute import
            result = importer.import_data(query="SELECT Id, Name FROM Account", process_func=process_func, validation_func=validate_func)

            # Verify results
            self.assertTrue(result.success)
            self.assertEqual(result.total_records, 2)
            self.assertEqual(result.success_count, 2)
            self.assertEqual(result.error_count, 0)
            self.assertEqual(result.skipped_count, 0)
            self.assertEqual(len(result.errors), 0)


if __name__ == "__main__":
    unittest.main()

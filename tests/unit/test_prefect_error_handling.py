"""
Unit Tests for Prefect Error Handling
====================================

Tests for the error_handling module functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from workflows.utils.error_handling import (
    PrefectErrorHandler,
    resilient_task,
    handle_salesforce_error,
    handle_database_error,
    validate_workflow_result,
    log_error_with_context,
    create_error_summary
)


class TestPrefectErrorHandler:
    """Test cases for PrefectErrorHandler class."""
    
    def test_classify_error_authentication(self):
        """Test authentication error classification."""
        error = Exception("Authentication failed")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "AUTHENTICATION_ERROR"
        
        error = Exception("Invalid login credentials")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "AUTHENTICATION_ERROR"
    
    def test_classify_error_rate_limit(self):
        """Test rate limit error classification."""
        error = Exception("Rate limit exceeded")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "RATE_LIMIT_ERROR"
        
        error = Exception("Too many requests")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "RATE_LIMIT_ERROR"
        
        error = Exception("HTTP 429")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "RATE_LIMIT_ERROR"
    
    def test_classify_error_network(self):
        """Test network error classification."""
        error = Exception("Connection timeout")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "NETWORK_ERROR"
        
        error = Exception("DNS resolution failed")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "NETWORK_ERROR"
        
        error = Exception("Socket connection error")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "NETWORK_ERROR"
    
    def test_classify_error_database(self):
        """Test database error classification."""
        error = Exception("Database constraint violation")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "DATABASE_ERROR"
        
        error = Exception("SQL syntax error")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "DATABASE_ERROR"
        
        error = Exception("Foreign key constraint failed")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "DATABASE_ERROR"
    
    def test_classify_error_validation(self):
        """Test validation error classification."""
        error = Exception("Validation failed")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "VALIDATION_ERROR"
        
        error = Exception("Required field missing")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "VALIDATION_ERROR"
        
        error = Exception("Invalid input data")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "VALIDATION_ERROR"
    
    def test_classify_error_timeout(self):
        """Test timeout error classification."""
        error = Exception("Operation timed out")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "TIMEOUT_ERROR"
        
        error = Exception("Request timed out")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "TIMEOUT_ERROR"
    
    def test_classify_error_unknown(self):
        """Test unknown error classification."""
        error = Exception("Some random error")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "UNKNOWN_ERROR"
    
    def test_get_error_description(self):
        """Test error description retrieval."""
        description = PrefectErrorHandler.get_error_description("AUTHENTICATION_ERROR")
        assert description == "Authentication or authorization errors"
        
        description = PrefectErrorHandler.get_error_description("RATE_LIMIT_ERROR")
        assert description == "API rate limit exceeded"
        
        description = PrefectErrorHandler.get_error_description("UNKNOWN_ERROR")
        assert description == "Unknown error type"
    
    def test_should_retry(self):
        """Test retry decision logic."""
        assert PrefectErrorHandler.should_retry("RATE_LIMIT_ERROR") is True
        assert PrefectErrorHandler.should_retry("NETWORK_ERROR") is True
        assert PrefectErrorHandler.should_retry("TIMEOUT_ERROR") is True
        assert PrefectErrorHandler.should_retry("AUTHENTICATION_ERROR") is False
        assert PrefectErrorHandler.should_retry("DATABASE_ERROR") is False
        assert PrefectErrorHandler.should_retry("VALIDATION_ERROR") is False
        assert PrefectErrorHandler.should_retry("UNKNOWN_ERROR") is False
    
    def test_get_retry_delay(self):
        """Test retry delay calculation."""
        # Rate limit error
        delay = PrefectErrorHandler.get_retry_delay("RATE_LIMIT_ERROR", 1)
        assert 48 <= delay <= 72  # 60 ± 20%
        
        delay = PrefectErrorHandler.get_retry_delay("RATE_LIMIT_ERROR", 2)
        assert 96 <= delay <= 144  # 120 ± 20%
        
        # Network error
        delay = PrefectErrorHandler.get_retry_delay("NETWORK_ERROR", 1)
        assert 24 <= delay <= 36  # 30 ± 20%
        
        # Timeout error
        delay = PrefectErrorHandler.get_retry_delay("TIMEOUT_ERROR", 1)
        assert 12 <= delay <= 18  # 15 ± 20%
        
        # Unknown error (default)
        delay = PrefectErrorHandler.get_retry_delay("UNKNOWN_ERROR", 1)
        assert 24 <= delay <= 36  # 30 ± 20%
    
    def test_get_retry_delay_minimum(self):
        """Test that retry delay is never less than 1 second."""
        delay = PrefectErrorHandler.get_retry_delay("TIMEOUT_ERROR", 10)
        assert delay >= 1


class TestResilientTask:
    """Test cases for resilient_task decorator."""
    
    def test_resilient_task_success(self):
        """Test resilient task with successful execution."""
        @resilient_task
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_resilient_task_retryable_error(self):
        """Test resilient task with retryable error."""
        call_count = 0
        
        @resilient_task
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Network timeout")
            return "success"
        
        # This should retry and eventually succeed
        result = test_function()
        assert result == "success"
        assert call_count == 3
    
    def test_resilient_task_non_retryable_error(self):
        """Test resilient task with non-retryable error."""
        @resilient_task
        def test_function():
            raise ValueError("Validation error")
        
        # This should not retry and fail immediately
        with pytest.raises(ValueError):
            test_function()


class TestErrorHandling:
    """Test cases for error handling functions."""
    
    def test_handle_salesforce_error(self, caplog):
        """Test Salesforce error handling."""
        error = Exception("Rate limit exceeded")
        context = {"operation": "query", "object": "Contact"}
        
        with caplog.at_level(logging.ERROR):
            error_info = handle_salesforce_error(error, context)
        
        assert error_info['error_type'] == "RATE_LIMIT_ERROR"
        assert error_info['error_description'] == "API rate limit exceeded"
        assert error_info['should_retry'] is True
        assert error_info['context'] == context
        assert "Salesforce error: RATE_LIMIT_ERROR" in caplog.text
    
    def test_handle_database_error(self, caplog):
        """Test database error handling."""
        error = Exception("Database constraint violation")
        context = {"table": "users", "operation": "insert"}
        
        with caplog.at_level(logging.ERROR):
            error_info = handle_database_error(error, context)
        
        assert error_info['error_type'] == "DATABASE_ERROR"
        assert error_info['error_description'] == "Database connection or query errors"
        assert error_info['should_retry'] is False
        assert error_info['context'] == context
        assert "Database error: DATABASE_ERROR" in caplog.text
    
    def test_validate_workflow_result_success(self):
        """Test successful workflow result validation."""
        result = {"status": "success", "count": 10}
        
        # Test with no validation
        assert validate_workflow_result(result) is True
        
        # Test with type validation
        assert validate_workflow_result(result, dict) is True
        
        # Test with required keys
        assert validate_workflow_result(result, dict, ["status"]) is True
    
    def test_validate_workflow_result_none(self):
        """Test workflow result validation with None."""
        with pytest.raises(ValueError, match="Result cannot be None"):
            validate_workflow_result(None)
    
    def test_validate_workflow_result_wrong_type(self):
        """Test workflow result validation with wrong type."""
        result = "string result"
        
        with pytest.raises(ValueError, match="Expected <class 'dict'>, got <class 'str'>"):
            validate_workflow_result(result, dict)
    
    def test_validate_workflow_result_missing_keys(self):
        """Test workflow result validation with missing keys."""
        result = {"status": "success"}
        
        with pytest.raises(ValueError, match="Missing required keys: \['count'\]"):
            validate_workflow_result(result, dict, ["status", "count"])
    
    def test_log_error_with_context(self, caplog):
        """Test error logging with context."""
        error = ValueError("Test error")
        context = {"param1": "value1", "param2": "value2"}
        
        with caplog.at_level(logging.ERROR):
            log_error_with_context(error, "test_workflow", "test_task", context)
        
        assert "Error in test_workflow (task: test_task): VALIDATION_ERROR" in caplog.text
        assert "Test error" in caplog.text
        assert "Context: {'param1': 'value1', 'param2': 'value2'}" in caplog.text
    
    def test_log_error_with_context_no_task(self, caplog):
        """Test error logging without task name."""
        error = ValueError("Test error")
        
        with caplog.at_level(logging.ERROR):
            log_error_with_context(error, "test_workflow")
        
        assert "Error in test_workflow: VALIDATION_ERROR" in caplog.text
        assert "Test error" in caplog.text
    
    def test_create_error_summary_empty(self):
        """Test error summary creation with empty list."""
        summary = create_error_summary([])
        
        assert summary['total_errors'] == 0
        assert summary['error_types'] == {}
        assert summary['sample_errors'] == []
    
    def test_create_error_summary_with_errors(self):
        """Test error summary creation with errors."""
        errors = [
            {"error_type": "NETWORK_ERROR", "error_message": "Connection failed"},
            {"error_type": "RATE_LIMIT_ERROR", "error_message": "Rate limit exceeded"},
            {"error_type": "NETWORK_ERROR", "error_message": "Timeout"},
            {"error_type": "VALIDATION_ERROR", "error_message": "Invalid data"},
            {"error_type": "NETWORK_ERROR", "error_message": "DNS failure"},
            {"error_type": "RATE_LIMIT_ERROR", "error_message": "Too many requests"}
        ]
        
        summary = create_error_summary(errors)
        
        assert summary['total_errors'] == 6
        assert summary['error_types']['NETWORK_ERROR'] == 3
        assert summary['error_types']['RATE_LIMIT_ERROR'] == 2
        assert summary['error_types']['VALIDATION_ERROR'] == 1
        assert len(summary['sample_errors']) == 5  # Only first 5 errors


# Import logging for caplog tests
import logging 
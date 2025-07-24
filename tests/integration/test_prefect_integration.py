"""
Integration Tests for Prefect Implementation
==========================================

Integration tests to verify Prefect setup and basic functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from workflows.base_workflow import salesforce_sync_flow
from workflows.utils.prefect_helpers import get_workflow_logger
from workflows.utils.error_handling import PrefectErrorHandler


class TestPrefectIntegration:
    """Integration tests for Prefect implementation."""
    
    def test_prefect_imports(self):
        """Test that all Prefect modules can be imported."""
        try:
            from prefect import flow, task, get_run_logger
            from prefect.client import get_client
            from prefect.retries import exponential_backoff
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import Prefect modules: {e}")
    
    def test_workflow_logger_creation(self):
        """Test that workflow logger can be created."""
        logger = get_workflow_logger("test_integration")
        assert logger is not None
        assert logger.name == "test_integration"
        assert logger.level <= 20  # INFO or lower
    
    def test_error_handler_classification(self):
        """Test error classification functionality."""
        # Test network error
        error = Exception("Connection timeout")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "NETWORK_ERROR"
        
        # Test rate limit error
        error = Exception("Rate limit exceeded")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "RATE_LIMIT_ERROR"
        
        # Test authentication error
        error = Exception("Authentication failed")
        error_type = PrefectErrorHandler.classify_error(error)
        assert error_type == "AUTHENTICATION_ERROR"
    
    def test_error_handler_retry_logic(self):
        """Test retry decision logic."""
        # Test retryable errors
        assert PrefectErrorHandler.should_retry("NETWORK_ERROR") is True
        assert PrefectErrorHandler.should_retry("RATE_LIMIT_ERROR") is True
        assert PrefectErrorHandler.should_retry("TIMEOUT_ERROR") is True
        
        # Test non-retryable errors
        assert PrefectErrorHandler.should_retry("AUTHENTICATION_ERROR") is False
        assert PrefectErrorHandler.should_retry("DATABASE_ERROR") is False
        assert PrefectErrorHandler.should_retry("VALIDATION_ERROR") is False
    
    @patch('workflows.base_workflow.validate_environment')
    @patch('workflows.base_workflow.salesforce_connection')
    @patch('workflows.base_workflow.database_connection')
    def test_salesforce_sync_flow_structure(self, mock_db_conn, mock_sf_conn, mock_env):
        """Test that the Salesforce sync flow has the correct structure."""
        # Mock successful environment validation
        mock_env.return_value = {
            'salesforce_configured': True,
            'database_configured': True,
            'errors': []
        }
        
        # Mock successful connections
        mock_sf_conn.return_value = MagicMock()
        mock_db_conn.return_value = MagicMock()
        
        # Test that the flow can be called (we'll mock the actual execution)
        with patch('prefect.flow') as mock_flow:
            mock_flow.return_value = lambda func: func
            result = salesforce_sync_flow()
            
            # Verify the flow returns expected structure
            assert isinstance(result, dict)
            assert 'status' in result
            assert 'environment_validated' in result
            assert 'connections_established' in result
            assert 'message' in result
    
    def test_prefect_configuration(self):
        """Test Prefect configuration and environment."""
        try:
            import prefect
            assert prefect.__version__ >= "2.10.0"
        except ImportError:
            pytest.fail("Prefect is not installed")
    
    def test_workflow_utilities_import(self):
        """Test that all workflow utilities can be imported."""
        try:
            from workflows.utils.prefect_helpers import (
                get_workflow_logger,
                log_workflow_start,
                log_workflow_completion,
                create_flow_run_record,
                get_environment_info,
                validate_workflow_parameters,
                format_duration
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import workflow utilities: {e}")
    
    def test_error_handling_utilities_import(self):
        """Test that all error handling utilities can be imported."""
        try:
            from workflows.utils.error_handling import (
                PrefectErrorHandler,
                resilient_task,
                handle_salesforce_error,
                handle_database_error,
                validate_workflow_result,
                log_error_with_context,
                create_error_summary
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import error handling utilities: {e}")
    
    def test_prefect_models_import(self):
        """Test that Prefect models can be imported."""
        try:
            from models.prefect_models import (
                PrefectFlowRun,
                PrefectTaskRun,
                PrefectWorkflowStats
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import Prefect models: {e}")
    
    def test_format_duration_functionality(self):
        """Test duration formatting functionality."""
        from workflows.utils.prefect_helpers import format_duration
        
        # Test seconds
        assert format_duration(30.5) == "30.5s"
        
        # Test minutes
        assert format_duration(90) == "1.5m"
        
        # Test hours
        assert format_duration(7200) == "2.0h"
    
    def test_environment_info_functionality(self):
        """Test environment information functionality."""
        from workflows.utils.prefect_helpers import get_environment_info
        
        env_info = get_environment_info()
        
        assert isinstance(env_info, dict)
        assert 'python_version' in env_info
        assert 'prefect_version' in env_info
        assert 'environment' in env_info
        assert 'database_url' in env_info
        assert 'salesforce_configured' in env_info
    
    def test_parameter_validation(self):
        """Test parameter validation functionality."""
        from workflows.utils.prefect_helpers import validate_workflow_parameters
        
        # Test successful validation
        params = {"param1": "value1", "param2": "value2"}
        required = ["param1", "param2"]
        assert validate_workflow_parameters(params, required) is True
        
        # Test missing parameter
        params = {"param1": "value1"}
        required = ["param1", "param2"]
        with pytest.raises(ValueError):
            validate_workflow_parameters(params, required)
    
    def test_error_summary_creation(self):
        """Test error summary creation functionality."""
        from workflows.utils.error_handling import create_error_summary
        
        # Test empty errors
        summary = create_error_summary([])
        assert summary['total_errors'] == 0
        assert summary['error_types'] == {}
        assert summary['sample_errors'] == []
        
        # Test with errors
        errors = [
            {"error_type": "NETWORK_ERROR", "error_message": "Connection failed"},
            {"error_type": "RATE_LIMIT_ERROR", "error_message": "Rate limit exceeded"}
        ]
        summary = create_error_summary(errors)
        assert summary['total_errors'] == 2
        assert summary['error_types']['NETWORK_ERROR'] == 1
        assert summary['error_types']['RATE_LIMIT_ERROR'] == 1
        assert len(summary['sample_errors']) == 2


class TestPrefectWorkflowStructure:
    """Test the structure and organization of Prefect workflows."""
    
    def test_workflow_directory_structure(self):
        """Test that the workflow directory structure is correct."""
        import os
        
        # Check that workflows directory exists
        assert os.path.exists("workflows")
        
        # Check that utils subdirectory exists
        assert os.path.exists("workflows/utils")
        
        # Check that __init__.py files exist
        assert os.path.exists("workflows/__init__.py")
        assert os.path.exists("workflows/utils/__init__.py")
    
    def test_workflow_modules_exist(self):
        """Test that all required workflow modules exist."""
        import os
        
        # Check core modules
        assert os.path.exists("workflows/base_workflow.py")
        assert os.path.exists("workflows/utils/prefect_helpers.py")
        assert os.path.exists("workflows/utils/error_handling.py")
        assert os.path.exists("models/prefect_models.py")
    
    def test_test_files_exist(self):
        """Test that all test files exist."""
        import os
        
        # Check unit tests
        assert os.path.exists("tests/unit/test_prefect_helpers.py")
        assert os.path.exists("tests/unit/test_prefect_error_handling.py")
        assert os.path.exists("tests/unit/models/test_prefect_models.py")
        
        # Check integration tests
        assert os.path.exists("tests/integration/test_prefect_integration.py") 
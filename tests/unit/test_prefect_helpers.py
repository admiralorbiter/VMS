"""
Unit Tests for Prefect Helper Utilities
======================================

Tests for the prefect_helpers module functionality.
"""

import pytest
import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from workflows.utils.prefect_helpers import (
    get_workflow_logger,
    log_workflow_start,
    log_workflow_completion,
    log_workflow_error,
    create_flow_run_record,
    get_environment_info,
    validate_workflow_parameters,
    format_duration,
    get_memory_usage,
    check_disk_space
)


class TestPrefectHelpers:
    """Test cases for Prefect helper utilities."""
    
    def test_get_workflow_logger(self):
        """Test logger creation and configuration."""
        logger = get_workflow_logger("test_logger")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
        
        # Test formatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, logging.Formatter)
    
    def test_get_workflow_logger_default_name(self):
        """Test logger creation with default name."""
        logger = get_workflow_logger()
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "workflows.utils.prefect_helpers"
    
    def test_log_workflow_start(self, caplog):
        """Test workflow start logging."""
        with caplog.at_level(logging.INFO):
            log_workflow_start("test_flow", {"param1": "value1"})
        
        assert "Starting workflow: test_flow" in caplog.text
        assert "Parameters: {'param1': 'value1'}" in caplog.text
    
    def test_log_workflow_start_no_parameters(self, caplog):
        """Test workflow start logging without parameters."""
        with caplog.at_level(logging.INFO):
            log_workflow_start("test_flow")
        
        assert "Starting workflow: test_flow" in caplog.text
        assert "Parameters:" not in caplog.text
    
    def test_log_workflow_completion(self, caplog):
        """Test workflow completion logging."""
        with caplog.at_level(logging.INFO):
            log_workflow_completion("test_flow", {"result": "success"}, 120.5)
        
        assert "Completed workflow: test_flow" in caplog.text
        assert "Duration: 120.50 seconds" in caplog.text
        assert "Result: {'result': 'success'}" in caplog.text
    
    def test_log_workflow_completion_no_result(self, caplog):
        """Test workflow completion logging without result."""
        with caplog.at_level(logging.INFO):
            log_workflow_completion("test_flow")
        
        assert "Completed workflow: test_flow" in caplog.text
        assert "Result:" not in caplog.text
    
    def test_log_workflow_error(self, caplog):
        """Test workflow error logging."""
        error = ValueError("Test error")
        context = {"param1": "value1"}
        
        with caplog.at_level(logging.ERROR):
            log_workflow_error("test_flow", error, context)
        
        assert "Error in workflow test_flow" in caplog.text
        assert "Test error" in caplog.text
        assert "Context: {'param1': 'value1'}" in caplog.text
    
    def test_create_flow_run_record(self):
        """Test flow run record creation."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time.replace(second=start_time.second + 30)
        
        record = create_flow_run_record(
            flow_name="test_flow",
            status="completed",
            start_time=start_time,
            end_time=end_time,
            error_message=None
        )
        
        assert record['flow_name'] == "test_flow"
        assert record['status'] == "completed"
        assert record['start_time'] == start_time
        assert record['end_time'] == end_time
        assert record['error_message'] is None
        assert 'created_at' in record
    
    def test_create_flow_run_record_with_error(self):
        """Test flow run record creation with error."""
        start_time = datetime.now(timezone.utc)
        
        record = create_flow_run_record(
            flow_name="test_flow",
            status="failed",
            start_time=start_time,
            error_message="Test error"
        )
        
        assert record['flow_name'] == "test_flow"
        assert record['status'] == "failed"
        assert record['error_message'] == "Test error"
        assert record['end_time'] is None
    
    @patch.dict('os.environ', {
        'FLASK_ENV': 'development',
        'DATABASE_URL': 'sqlite:///test.db',
        'SECRET_KEY': 'test_key'
    })
    def test_get_environment_info(self):
        """Test environment information retrieval."""
        info = get_environment_info()
        
        assert 'python_version' in info
        assert 'prefect_version' in info
        assert info['environment'] == 'development'
        assert info['database_url'] == 'sqlite:///test.db'
        assert 'salesforce_configured' in info
    
    def test_validate_workflow_parameters_success(self):
        """Test successful parameter validation."""
        parameters = {"param1": "value1", "param2": "value2"}
        required_params = ["param1", "param2"]
        
        result = validate_workflow_parameters(parameters, required_params)
        assert result is True
    
    def test_validate_workflow_parameters_missing(self):
        """Test parameter validation with missing parameters."""
        parameters = {"param1": "value1"}
        required_params = ["param1", "param2"]
        
        with pytest.raises(ValueError, match="Missing required parameters: \['param2'\]"):
            validate_workflow_parameters(parameters, required_params)
    
    def test_validate_workflow_parameters_empty(self):
        """Test parameter validation with empty required list."""
        parameters = {"param1": "value1"}
        required_params = []
        
        result = validate_workflow_parameters(parameters, required_params)
        assert result is True
    
    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        assert format_duration(30.5) == "30.5s"
        assert format_duration(0.1) == "0.1s"
    
    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        assert format_duration(90) == "1.5m"
        assert format_duration(3600) == "1.0h"
    
    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        assert format_duration(7200) == "2.0h"
        assert format_duration(18000) == "5.0h"
    
    @patch('psutil.virtual_memory')
    def test_get_memory_usage_success(self, mock_virtual_memory):
        """Test memory usage retrieval with psutil available."""
        mock_memory = MagicMock()
        mock_memory.total = 8 * 1024**3  # 8GB
        mock_memory.available = 4 * 1024**3  # 4GB
        mock_memory.used = 4 * 1024**3  # 4GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        memory_info = get_memory_usage()
        
        assert memory_info['total_gb'] == 8.0
        assert memory_info['available_gb'] == 4.0
        assert memory_info['used_gb'] == 4.0
        assert memory_info['percent_used'] == 50.0
    
    @patch('psutil.virtual_memory', side_effect=ImportError)
    def test_get_memory_usage_no_psutil(self, mock_virtual_memory):
        """Test memory usage retrieval without psutil."""
        memory_info = get_memory_usage()
        
        assert memory_info['error'] == 'psutil not available'
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_success(self, mock_disk_usage):
        """Test disk space checking with psutil available."""
        mock_disk = MagicMock()
        mock_disk.total = 100 * 1024**3  # 100GB
        mock_disk.free = 60 * 1024**3  # 60GB
        mock_disk.used = 40 * 1024**3  # 40GB
        mock_disk_usage.return_value = mock_disk
        
        disk_info = check_disk_space()
        
        assert disk_info['total_gb'] == 100.0
        assert disk_info['free_gb'] == 60.0
        assert disk_info['used_gb'] == 40.0
        assert disk_info['percent_used'] == 40.0
    
    @patch('psutil.disk_usage', side_effect=ImportError)
    def test_check_disk_space_no_psutil(self, mock_disk_usage):
        """Test disk space checking without psutil."""
        disk_info = check_disk_space()
        
        assert disk_info['error'] == 'psutil not available'
    
    def test_check_disk_space_custom_path(self):
        """Test disk space checking with custom path."""
        with patch('psutil.disk_usage') as mock_disk_usage:
            mock_disk = MagicMock()
            mock_disk.total = 100 * 1024**3
            mock_disk.free = 60 * 1024**3
            mock_disk.used = 40 * 1024**3
            mock_disk_usage.return_value = mock_disk
            
            disk_info = check_disk_space("/custom/path")
            
            mock_disk_usage.assert_called_once_with("/custom/path")
            assert disk_info['total_gb'] == 100.0 
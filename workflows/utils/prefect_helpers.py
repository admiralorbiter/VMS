"""
Prefect Helper Utilities
=======================

Utility functions and helpers for Prefect workflows in the VMS application.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from prefect import get_run_logger
from prefect.client import get_client
from prefect.utilities.annotations import quote


def get_workflow_logger(name: str = None) -> logging.Logger:
    """
    Get a logger configured for Prefect workflows.
    
    Args:
        name: Logger name (defaults to calling module name)
        
    Returns:
        Configured logger instance
    """
    if name is None:
        name = __name__
    
    logger = logging.getLogger(name)
    
    # Configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def log_workflow_start(flow_name: str, parameters: Dict[str, Any] = None):
    """
    Log the start of a workflow with parameters.
    
    Args:
        flow_name: Name of the workflow
        parameters: Optional parameters for the workflow
    """
    logger = get_workflow_logger()
    logger.info(f"Starting workflow: {flow_name}")
    
    if parameters:
        logger.info(f"Parameters: {parameters}")


def log_workflow_completion(flow_name: str, result: Any = None, duration: float = None):
    """
    Log the completion of a workflow.
    
    Args:
        flow_name: Name of the workflow
        result: Optional result from the workflow
        duration: Optional duration in seconds
    """
    logger = get_workflow_logger()
    logger.info(f"Completed workflow: {flow_name}")
    
    if duration:
        logger.info(f"Duration: {duration:.2f} seconds")
    
    if result:
        logger.info(f"Result: {result}")


def log_workflow_error(flow_name: str, error: Exception, context: Dict[str, Any] = None):
    """
    Log an error that occurred during workflow execution.
    
    Args:
        flow_name: Name of the workflow
        error: The exception that occurred
        context: Optional context information
    """
    logger = get_workflow_logger()
    logger.error(f"Error in workflow {flow_name}: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")


def create_flow_run_record(flow_name: str, status: str, start_time: datetime = None, 
                          end_time: datetime = None, error_message: str = None) -> Dict[str, Any]:
    """
    Create a flow run record for tracking in VMS database.
    
    Args:
        flow_name: Name of the workflow
        status: Current status of the workflow
        start_time: When the workflow started
        end_time: When the workflow ended
        error_message: Error message if workflow failed
        
    Returns:
        Dictionary with flow run information
    """
    return {
        'flow_name': flow_name,
        'status': status,
        'start_time': start_time or datetime.now(timezone.utc),
        'end_time': end_time,
        'error_message': error_message,
        'created_at': datetime.now(timezone.utc)
    }


def get_environment_info() -> Dict[str, str]:
    """
    Get information about the current environment.
    
    Returns:
        Dictionary with environment information
    """
    return {
        'python_version': os.sys.version,
        'prefect_version': '2.10.0',  # Update as needed
        'environment': os.getenv('FLASK_ENV', 'development'),
        'database_url': os.getenv('DATABASE_URL', 'sqlite:///vms.db'),
        'salesforce_configured': bool(os.getenv('SF_USERNAME')),
    }


def validate_workflow_parameters(parameters: Dict[str, Any], required_params: list) -> bool:
    """
    Validate that required parameters are present.
    
    Args:
        parameters: Parameters to validate
        required_params: List of required parameter names
        
    Returns:
        True if all required parameters are present
        
    Raises:
        ValueError: If required parameters are missing
    """
    missing_params = [param for param in required_params if param not in parameters]
    
    if missing_params:
        raise ValueError(f"Missing required parameters: {missing_params}")
    
    return True


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage information.
    
    Returns:
        Dictionary with memory usage statistics
    """
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'percent_used': memory.percent
        }
    except ImportError:
        return {'error': 'psutil not available'}


def check_disk_space(path: str = '.') -> Dict[str, float]:
    """
    Check available disk space.
    
    Args:
        path: Path to check disk space for
        
    Returns:
        Dictionary with disk space information
    """
    try:
        import psutil
        disk = psutil.disk_usage(path)
        return {
            'total_gb': disk.total / (1024**3),
            'free_gb': disk.free / (1024**3),
            'used_gb': disk.used / (1024**3),
            'percent_used': (disk.used / disk.total) * 100
        }
    except ImportError:
        return {'error': 'psutil not available'} 
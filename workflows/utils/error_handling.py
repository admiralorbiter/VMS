"""
Prefect Error Handling Utilities
===============================

Error handling, retry logic, and error classification for Prefect workflows.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from prefect import task
from prefect.utilities.annotations import quote
from workflows.utils.prefect_helpers import get_workflow_logger


class PrefectErrorHandler:
    """Handle different types of errors in Prefect workflows"""
    
    ERROR_TYPES = {
        'AUTHENTICATION_ERROR': 'Authentication or authorization errors',
        'RATE_LIMIT_ERROR': 'API rate limit exceeded',
        'NETWORK_ERROR': 'Network connectivity issues',
        'DATABASE_ERROR': 'Database connection or query errors',
        'VALIDATION_ERROR': 'Data validation errors',
        'TIMEOUT_ERROR': 'Operation timeout',
        'UNKNOWN_ERROR': 'Unknown or unclassified errors'
    }
    
    @staticmethod
    def classify_error(error: Exception) -> str:
        """
        Classify an error based on its type and message.
        
        Args:
            error: The exception to classify
            
        Returns:
            Error classification string
        """
        error_str = str(error).lower()
        
        # Authentication errors
        if any(term in error_str for term in ['auth', 'login', 'password', 'token', 'unauthorized']):
            return "AUTHENTICATION_ERROR"
        
        # Rate limit errors
        elif any(term in error_str for term in ['rate limit', 'throttle', 'too many requests', '429']):
            return "RATE_LIMIT_ERROR"
        
        # Network errors
        elif any(term in error_str for term in ['connection', 'timeout', 'network', 'dns', 'socket']):
            return "NETWORK_ERROR"
        
        # Database errors
        elif any(term in error_str for term in ['database', 'sql', 'constraint', 'foreign key']):
            return "DATABASE_ERROR"
        
        # Validation errors
        elif any(term in error_str for term in ['validation', 'invalid', 'required', 'missing']):
            return "VALIDATION_ERROR"
        
        # Timeout errors
        elif any(term in error_str for term in ['timeout', 'timed out']):
            return "TIMEOUT_ERROR"
        
        else:
            return "UNKNOWN_ERROR"
    
    @staticmethod
    def get_error_description(error_type: str) -> str:
        """
        Get a human-readable description of an error type.
        
        Args:
            error_type: The error type to describe
            
        Returns:
            Description of the error type
        """
        return PrefectErrorHandler.ERROR_TYPES.get(error_type, 'Unknown error type')
    
    @staticmethod
    def should_retry(error_type: str) -> bool:
        """
        Determine if an error type should trigger a retry.
        
        Args:
            error_type: The error type to check
            
        Returns:
            True if the error should trigger a retry
        """
        retryable_errors = [
            'RATE_LIMIT_ERROR',
            'NETWORK_ERROR',
            'TIMEOUT_ERROR'
        ]
        
        return error_type in retryable_errors
    
    @staticmethod
    def get_retry_delay(error_type: str, attempt: int) -> int:
        """
        Calculate retry delay based on error type and attempt number.
        
        Args:
            error_type: The error type
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds before next retry
        """
        base_delays = {
            'RATE_LIMIT_ERROR': 60,  # 1 minute
            'NETWORK_ERROR': 30,      # 30 seconds
            'TIMEOUT_ERROR': 15       # 15 seconds
        }
        
        base_delay = base_delays.get(error_type, 30)
        
        # Exponential backoff with jitter
        delay = base_delay * (2 ** (attempt - 1))
        
        # Add jitter (±20%)
        import random
        jitter = delay * 0.2 * random.uniform(-1, 1)
        delay += jitter
        
        return max(1, int(delay))


def resilient_task(func: Callable = None, 
                  retries: int = 3, 
                  retry_delay_seconds: int = 60,
                  retry_jitter_factor: float = 0.1):
    """
    Decorator to create a resilient task with retry logic.
    
    Args:
        func: The function to wrap
        retries: Number of retries
        retry_delay_seconds: Base delay between retries
        retry_jitter_factor: Jitter factor for retry delays
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @task(
            retries=retries,
            retry_delay_seconds=retry_delay_seconds
        )
        def wrapper(*args, **kwargs):
            logger = get_workflow_logger()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_type = PrefectErrorHandler.classify_error(e)
                logger.error(f"Error in {func.__name__}: {error_type} - {str(e)}")
                
                if PrefectErrorHandler.should_retry(error_type):
                    logger.info(f"Retrying {func.__name__} due to {error_type}")
                    raise  # Let Prefect handle the retry
                else:
                    logger.error(f"Not retrying {func.__name__} due to {error_type}")
                    raise
        
        return wrapper
    
    if func:
        return decorator(func)
    return decorator


def handle_salesforce_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Handle Salesforce-specific errors with appropriate logging and classification.
    
    Args:
        error: The Salesforce error
        context: Optional context information
        
    Returns:
        Dictionary with error handling information
    """
    logger = get_workflow_logger()
    
    error_type = PrefectErrorHandler.classify_error(error)
    error_description = PrefectErrorHandler.get_error_description(error_type)
    
    error_info = {
        'error_type': error_type,
        'error_description': error_description,
        'error_message': str(error),
        'should_retry': PrefectErrorHandler.should_retry(error_type),
        'context': context or {}
    }
    
    logger.error(f"Salesforce error: {error_type} - {error_description}")
    logger.error(f"Error message: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")
    
    return error_info


def handle_database_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Handle database-specific errors with appropriate logging and classification.
    
    Args:
        error: The database error
        context: Optional context information
        
    Returns:
        Dictionary with error handling information
    """
    logger = get_workflow_logger()
    
    error_type = PrefectErrorHandler.classify_error(error)
    error_description = PrefectErrorHandler.get_error_description(error_type)
    
    error_info = {
        'error_type': error_type,
        'error_description': error_description,
        'error_message': str(error),
        'should_retry': PrefectErrorHandler.should_retry(error_type),
        'context': context or {}
    }
    
    logger.error(f"Database error: {error_type} - {error_description}")
    logger.error(f"Error message: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")
    
    return error_info


def validate_workflow_result(result: Any, expected_type: type = None, 
                           required_keys: list = None) -> bool:
    """
    Validate the result of a workflow task.
    
    Args:
        result: The result to validate
        expected_type: Expected type of the result
        required_keys: Required keys if result is a dictionary
        
    Returns:
        True if validation passes
        
    Raises:
        ValueError: If validation fails
    """
    if result is None:
        raise ValueError("Result cannot be None")
    
    if expected_type and not isinstance(result, expected_type):
        raise ValueError(f"Expected {expected_type}, got {type(result)}")
    
    if required_keys and isinstance(result, dict):
        missing_keys = [key for key in required_keys if key not in result]
        if missing_keys:
            raise ValueError(f"Missing required keys: {missing_keys}")
    
    return True


def log_error_with_context(error: Exception, workflow_name: str, 
                          task_name: str = None, context: Dict[str, Any] = None):
    """
    Log an error with comprehensive context information.
    
    Args:
        error: The exception that occurred
        workflow_name: Name of the workflow
        task_name: Name of the specific task (optional)
        context: Additional context information
    """
    logger = get_workflow_logger()
    
    error_type = PrefectErrorHandler.classify_error(error)
    
    log_message = f"Error in {workflow_name}"
    if task_name:
        log_message += f" (task: {task_name})"
    log_message += f": {error_type} - {str(error)}"
    
    logger.error(log_message)
    
    if context:
        logger.error(f"Context: {context}")
    
    # Log stack trace for debugging
    import traceback
    logger.debug(f"Stack trace: {traceback.format_exc()}")


def create_error_summary(errors: list) -> Dict[str, Any]:
    """
    Create a summary of multiple errors.
    
    Args:
        errors: List of error dictionaries
        
    Returns:
        Summary of errors with counts and types
    """
    if not errors:
        return {'total_errors': 0, 'error_types': {}, 'sample_errors': []}
    
    error_types = {}
    sample_errors = []
    
    for error in errors:
        error_type = error.get('error_type', 'UNKNOWN_ERROR')
        error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if len(sample_errors) < 5:  # Keep first 5 errors as samples
            sample_errors.append(error)
    
    return {
        'total_errors': len(errors),
        'error_types': error_types,
        'sample_errors': sample_errors
    } 
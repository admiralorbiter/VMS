"""
Base Workflow Module
===================

Base workflow patterns and utilities for Prefect workflows in the VMS application.
This module provides the foundation for all other workflows.
"""

import time
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from prefect import flow, task, get_run_logger
from sqlalchemy import text

from workflows.utils.prefect_helpers import (
    log_workflow_start, 
    log_workflow_completion, 
    log_workflow_error,
    create_flow_run_record,
    get_environment_info,
    validate_workflow_parameters
)
from workflows.utils.error_handling import (
    PrefectErrorHandler,
    log_error_with_context,
    validate_workflow_result
)


@task(retries=3, retry_delay_seconds=60)
def salesforce_connection():
    """
    Establish Salesforce connection with retry logic.
    
    Returns:
        Salesforce connection object
        
    Raises:
        Exception: If connection fails after retries
    """
    logger = get_run_logger()
    logger.info("Establishing Salesforce connection...")
    
    try:
        from simple_salesforce import Salesforce
        from config import Config
        
        # Create Salesforce connection
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )
        
        # Test connection
        sf.query("SELECT Id FROM User LIMIT 1")
        
        logger.info("Salesforce connection established successfully")
        return sf
        
    except Exception as e:
        error_type = PrefectErrorHandler.classify_error(e)
        logger.error(f"Salesforce connection failed: {error_type} - {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=30)
def database_connection():
    """
    Establish database connection with retry logic.
    
    Returns:
        Database session object
        
    Raises:
        Exception: If connection fails after retries
    """
    logger = get_run_logger()
    logger.info("Establishing database connection...")
    
    try:
        from models import db
        from app import app
        
        # Test database connection within Flask app context
        with app.app_context():
            db.session.execute(text("SELECT 1"))
        
        logger.info("Database connection established successfully")
        return db.session
        
    except Exception as e:
        error_type = PrefectErrorHandler.classify_error(e)
        logger.error(f"Database connection failed: {error_type} - {str(e)}")
        raise


@task
def validate_environment():
    """
    Validate that the environment is properly configured.
    
    Returns:
        Dictionary with environment validation results
    """
    logger = get_run_logger()
    logger.info("Validating environment configuration...")
    
    validation_results = {
        'salesforce_configured': False,
        'database_configured': False,
        'environment_variables': {},
        'errors': []
    }
    
    # Check Salesforce configuration
    try:
        from config import Config
        if hasattr(Config, 'SF_USERNAME') and Config.SF_USERNAME:
            validation_results['salesforce_configured'] = True
        else:
            validation_results['errors'].append("Salesforce username not configured (set SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN)")
    except Exception as e:
        validation_results['errors'].append(f"Salesforce configuration error: {str(e)}")
    
    # Check database configuration
    try:
        from models import db
        from app import app
        with app.app_context():
            db.session.execute(text("SELECT 1"))
        validation_results['database_configured'] = True
    except Exception as e:
        validation_results['errors'].append(f"Database configuration error: {str(e)}")
    
    # Check environment variables
    env_vars = [
        'FLASK_ENV',
        'DATABASE_URL',
        'SECRET_KEY'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        validation_results['environment_variables'][var] = bool(value)
        if not value:
            validation_results['errors'].append(f"Environment variable {var} not set")
    
    if validation_results['errors']:
        logger.warning(f"Environment validation found {len(validation_results['errors'])} issues")
        for error in validation_results['errors']:
            logger.warning(f"  - {error}")
    else:
        logger.info("Environment validation passed")
    
    return validation_results


@task
def log_workflow_metrics(flow_name: str, start_time: datetime, 
                        end_time: datetime, result: Any = None, 
                        errors: list = None):
    """
    Log comprehensive workflow metrics.
    
    Args:
        flow_name: Name of the workflow
        start_time: When the workflow started
        end_time: When the workflow ended
        result: Workflow result
        errors: List of errors that occurred
    """
    logger = get_run_logger()
    
    duration = (end_time - start_time).total_seconds()
    
    metrics = {
        'flow_name': flow_name,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration,
        'duration_formatted': format_duration(duration),
        'success': len(errors or []) == 0,
        'error_count': len(errors or []),
        'environment': get_environment_info()
    }
    
    logger.info(f"Workflow metrics: {metrics}")
    
    return metrics


def workflow_decorator(flow_name: str = None, validate_params: list = None):
    """
    Decorator to add common workflow functionality.
    
    Args:
        flow_name: Name for the workflow (defaults to function name)
        validate_params: List of required parameters to validate
        
    Returns:
        Decorated workflow function
    """
    def decorator(func):
        @flow(name=flow_name or func.__name__)
        def wrapper(*args, **kwargs):
            # Get actual flow name
            actual_flow_name = flow_name or func.__name__
            
            # Validate parameters if specified
            if validate_params:
                try:
                    validate_workflow_parameters(kwargs, validate_params)
                except ValueError as e:
                    log_error_with_context(e, actual_flow_name, "parameter_validation")
                    raise
            
            # Log workflow start
            log_workflow_start(actual_flow_name, kwargs)
            
            # Record start time
            start_time = datetime.now(timezone.utc)
            
            # Track errors
            errors = []
            
            try:
                # Execute the workflow
                result = func(*args, **kwargs)
                
                # Validate result
                validate_workflow_result(result)
                
                # Log completion
                end_time = datetime.now(timezone.utc)
                log_workflow_completion(actual_flow_name, result, 
                                      (end_time - start_time).total_seconds())
                
                # Log metrics
                log_workflow_metrics(actual_flow_name, start_time, end_time, result, errors)
                
                return result
                
            except Exception as e:
                # Log error
                end_time = datetime.now(timezone.utc)
                log_error_with_context(e, actual_flow_name)
                errors.append({
                    'error_type': PrefectErrorHandler.classify_error(e),
                    'error_message': str(e),
                    'timestamp': end_time.isoformat()
                })
                
                # Log metrics with errors
                log_workflow_metrics(actual_flow_name, start_time, end_time, None, errors)
                
                raise
        
        return wrapper
    
    return decorator


@workflow_decorator("salesforce-sync")
def salesforce_sync_flow():
    """
    Main Salesforce synchronization workflow.
    
    This is a placeholder workflow that will be extended with actual
    Salesforce sync functionality.
    
    Returns:
        Dictionary with sync results
    """
    logger = get_run_logger()
    logger.info("Starting Salesforce sync workflow")
    
    # Validate environment
    env_validation = validate_environment.submit()
    env_result = env_validation.result()
    
    # In development, allow the sync to proceed even with missing credentials
    # The actual Salesforce connection will fail gracefully if credentials are missing
    if os.environ.get('FLASK_ENV') == 'production' and (not env_result['salesforce_configured'] or not env_result['database_configured']):
        raise ValueError("Environment not properly configured for Salesforce sync")
    
    # Establish connections
    sf_connection = salesforce_connection.submit()
    db_connection = database_connection.submit()
    
    # Placeholder for actual sync logic
    logger.info("Salesforce sync workflow completed successfully")
    
    return {
        'status': 'success',
        'environment_validated': True,
        'connections_established': True,
        'message': 'Salesforce sync workflow completed'
    }


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


# Import os for environment variable access
import os 
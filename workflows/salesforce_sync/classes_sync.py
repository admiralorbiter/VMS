"""
Classes Sync Workflow Module
===========================

This module provides Prefect workflows for synchronizing class data
from Salesforce to the local VMS database.

Key Features:
- Class data synchronization from Salesforce Class__c objects
- Comprehensive error handling and retry logic
- Chunked processing for large datasets
- Detailed logging and metrics tracking

Workflows:
- classes_sync_flow: Main workflow for class synchronization
- process_classes_batch: Task for processing class batches

Dependencies:
- Salesforce API integration
- Class model
- Prefect workflow utilities
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from prefect import flow, task, get_run_logger
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.class_model import Class

from workflows.base_workflow import (
    salesforce_connection,
    database_connection,
    validate_environment,
    log_workflow_metrics
)
from workflows.utils.error_handling import (
    handle_salesforce_error,
    handle_database_error,
    PrefectErrorHandler
)
from workflows.utils.prefect_helpers import (
    log_workflow_start,
    log_workflow_completion,
    format_duration
)


@task(retries=3, retry_delay_seconds=60)
def query_classes(sf_connection) -> Dict[str, Any]:
    """
    Query classes from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying classes from Salesforce...")
    
    try:
        # Query classes from Salesforce
        classes_query = """
        SELECT Id, Name, School__c, Class_Year_Number__c
        FROM Class__c
        """
        
        result = sf_connection.query_all(classes_query)
        classes = result.get('records', [])
        
        logger.info(f"Retrieved {len(classes)} classes from Salesforce")
        
        return {
            'classes': classes,
            'total_count': len(classes),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_classes'})
        logger.error(f"Failed to query classes: {error_info['error_message']}")
        raise


@task(retries=2, retry_delay_seconds=30)
def process_classes_batch(classes_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of classes from Salesforce.
    
    Args:
        classes_data: Dictionary containing classes and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    classes = classes_data['classes']
    
    logger.info(f"Processing {len(classes)} classes...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in classes:
        try:
            # Check if class already exists
            existing_class = Class.query.filter_by(salesforce_id=row['Id']).first()
            
            if existing_class:
                # Update existing class
                existing_class.name = row['Name']
                existing_class.school_salesforce_id = row['School__c']
                existing_class.class_year = int(row['Class_Year_Number__c']) if row.get('Class_Year_Number__c') else None
                logger.debug(f"Updated existing class: {row['Name']}")
            else:
                # Create new class
                new_class = Class(
                    salesforce_id=row['Id'],
                    name=row['Name'],
                    school_salesforce_id=row['School__c'],
                    class_year=int(row['Class_Year_Number__c']) if row.get('Class_Year_Number__c') else None
                )
                db_session.add(new_class)
                logger.debug(f"Created new class: {row['Name']}")
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing class {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} classes successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@flow(name="classes-sync")
def classes_sync_flow() -> Dict[str, Any]:
    """
    Main workflow for synchronizing classes from Salesforce.
    
    This workflow:
    1. Connects to Salesforce and database
    2. Queries classes from Salesforce
    3. Processes classes in batches
    4. Commits all changes to database
    5. Returns comprehensive results
    
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    
    # Log workflow start
    start_time = datetime.now(timezone.utc)
    log_workflow_start("classes_sync_flow", {})
    
    try:
        # Validate environment
        validate_environment()
        
        # Get connections
        sf_connection = salesforce_connection()
        db_session = database_connection()
        
        # Query data from Salesforce
        classes_data = query_classes(sf_connection)
        
        # Process classes
        classes_result = process_classes_batch(classes_data, db_session)
        
        # Commit all changes
        db_session.commit()
        
        # Prepare results
        total_success = classes_result['success_count']
        total_errors = classes_result['error_count']
        all_errors = classes_result['errors']
        
        # Create error summary if there are errors
        error_summary = None
        if all_errors:
            error_summary = create_error_summary(all_errors)
        
        # Log workflow completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        log_workflow_completion("classes_sync_flow", {
            'total_success': total_success,
            'total_errors': total_errors,
            'duration_seconds': duration.total_seconds()
        })
        
        logger.info(f"Classes sync completed: {total_success} successes, {total_errors} errors")
        
        return {
            'success': True,
            'message': f'Successfully processed {total_success} records with {total_errors} errors',
            'classes_success': classes_result['success_count'],
            'classes_errors': classes_result['error_count'],
            'errors': all_errors[:10],  # Limit error display
            'error_summary': error_summary,
            'duration': format_duration(duration)
        }
        
    except Exception as e:
        # Log workflow failure
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        error_context = create_error_context(e, {
            'workflow': 'classes_sync_flow',
            'start_time': start_time,
            'duration': duration
        })
        
        logger.error(f"Classes sync failed: {error_context['error_message']}")
        
        return {
            'success': False,
            'error': error_context['error_message'],
            'error_type': error_context['error_type'],
            'duration': format_duration(duration)
        } 
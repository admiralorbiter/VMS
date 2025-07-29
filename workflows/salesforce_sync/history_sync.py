"""
History Sync Workflow Module
===========================

This module provides Prefect workflows for synchronizing historical activity data
from Salesforce to the local VMS database.

Key Features:
- Historical activity data synchronization from Salesforce
- Comprehensive error handling and retry logic
- Chunked processing for large datasets
- Detailed logging and metrics tracking

Workflows:
- history_sync_flow: Main workflow for history synchronization
- process_history_batch: Task for processing history batches

Dependencies:
- Salesforce API integration
- History model
- Prefect workflow utilities
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from prefect import flow, task, get_run_logger
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.history import History
from models.contact import Contact
from models.event import Event

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
def query_history(sf_connection) -> Dict[str, Any]:
    """
    Query historical activity data from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying historical activity data from Salesforce...")
    
    try:
        # Query historical activity from Salesforce
        # This query should be adapted based on the specific Salesforce objects
        # that contain historical activity data
        history_query = """
        SELECT Id, Name, Contact__c, Event__c, Activity_Date__c, 
               Activity_Type__c, Description__c, Hours__c, Status__c
        FROM Activity__c
        WHERE Activity_Type__c IN ('Volunteer Session', 'Training', 'Meeting')
        ORDER BY Activity_Date__c DESC
        """
        
        result = sf_connection.query_all(history_query)
        history_records = result.get('records', [])
        
        logger.info(f"Retrieved {len(history_records)} history records from Salesforce")
        
        return {
            'history_records': history_records,
            'total_count': len(history_records),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_history'})
        logger.error(f"Failed to query history: {error_info['error_message']}")
        raise


@task(retries=2, retry_delay_seconds=30)
def process_history_batch(history_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of history records from Salesforce.
    
    Args:
        history_data: Dictionary containing history records and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    history_records = history_data['history_records']
    
    logger.info(f"Processing {len(history_records)} history records...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in history_records:
        try:
            # Check if history record already exists
            existing_history = History.query.filter_by(salesforce_id=row['Id']).first()
            
            if existing_history:
                # Update existing history record
                history = existing_history
                logger.debug(f"Updating existing history record: {row['Name']}")
            else:
                # Create new history record
                history = History()
                history.salesforce_id = row['Id']
                db_session.add(history)
                logger.debug(f"Creating new history record: {row['Name']}")
            
            # Update history fields
            history.name = row.get('Name', '')
            history.activity_type = row.get('Activity_Type__c', '')
            history.description = row.get('Description__c', '')
            history.status = row.get('Status__c', '')
            
            # Handle numeric fields
            def safe_convert_to_float(value, default=0.0):
                if value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            history.hours = safe_convert_to_float(row.get('Hours__c'))
            
            # Handle date fields
            if row.get('Activity_Date__c'):
                try:
                    from routes.utils import parse_date
                    history.activity_date = parse_date(row['Activity_Date__c'])
                except Exception as e:
                    logger.warning(f"Could not parse activity date for {row['Name']}: {str(e)}")
            
            # Handle relationships
            contact_id = row.get('Contact__c')
            if contact_id:
                contact = Contact.query.filter_by(salesforce_individual_id=contact_id).first()
                if contact:
                    history.contact_id = contact.id
            
            event_id = row.get('Event__c')
            if event_id:
                event = Event.query.filter_by(salesforce_id=event_id).first()
                if event:
                    history.event_id = event.id
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing history record {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} history records successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@flow(name="history-sync")
def history_sync_flow() -> Dict[str, Any]:
    """
    Main workflow for synchronizing historical activity data from Salesforce.
    
    This workflow:
    1. Connects to Salesforce and database
    2. Queries historical activity data from Salesforce
    3. Processes history records in batches
    4. Commits all changes to database
    5. Returns comprehensive results
    
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    
    # Log workflow start
    start_time = datetime.now(timezone.utc)
    log_workflow_start("history_sync_flow", {})
    
    try:
        # Validate environment
        validate_environment()
        
        # Get connections
        sf_connection = salesforce_connection()
        db_session = database_connection()
        
        # Query data from Salesforce
        history_data = query_history(sf_connection)
        
        # Process history records
        history_result = process_history_batch(history_data, db_session)
        
        # Commit all changes
        db_session.commit()
        
        # Prepare results
        total_success = history_result['success_count']
        total_errors = history_result['error_count']
        all_errors = history_result['errors']
        
        # Create error summary if there are errors
        error_summary = None
        if all_errors:
            error_summary = create_error_summary(all_errors)
        
        # Log workflow completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        log_workflow_completion("history_sync_flow", {
            'total_success': total_success,
            'total_errors': total_errors,
            'duration_seconds': duration.total_seconds()
        })
        
        logger.info(f"History sync completed: {total_success} successes, {total_errors} errors")
        
        return {
            'success': True,
            'message': f'Successfully processed {total_success} records with {total_errors} errors',
            'history_success': history_result['success_count'],
            'history_errors': history_result['error_count'],
            'errors': all_errors[:10],  # Limit error display
            'error_summary': error_summary,
            'duration': format_duration(duration)
        }
        
    except Exception as e:
        # Log workflow failure
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        error_context = create_error_context(e, {
            'workflow': 'history_sync_flow',
            'start_time': start_time,
            'duration': duration
        })
        
        logger.error(f"History sync failed: {error_context['error_message']}")
        
        return {
            'success': False,
            'error': error_context['error_message'],
            'error_type': error_context['error_type'],
            'duration': format_duration(duration)
        } 
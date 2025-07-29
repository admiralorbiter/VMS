"""
Pathways Sync Workflow Module
============================

This module provides Prefect workflows for synchronizing pathways and pathway participants
from Salesforce to the local VMS database.

Key Features:
- Pathway data synchronization from Salesforce Pathway__c objects
- Pathway participant synchronization from Pathway_Participant__c objects
- Pathway-session relationship synchronization from Pathway_Session__c objects
- Comprehensive error handling and retry logic
- Detailed logging and metrics tracking

Workflows:
- pathways_sync_flow: Main workflow for pathway synchronization
- process_pathways_batch: Task for processing pathway batches
- process_pathway_participants_batch: Task for processing participant batches
- process_pathway_sessions_batch: Task for processing session relationships

Dependencies:
- Salesforce API integration
- Pathway, Event, and Contact models
- Prefect workflow utilities
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from prefect import flow, task, get_run_logger
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.pathways import Pathway
from models.event import Event
from models.contact import Contact

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
def query_pathways(sf_connection) -> Dict[str, Any]:
    """
    Query pathways from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying pathways from Salesforce...")
    
    try:
        # Query pathways from Salesforce
        pathways_query = """
        SELECT Id, Name
        FROM Pathway__c
        """
        
        result = sf_connection.query_all(pathways_query)
        pathways = result.get('records', [])
        
        logger.info(f"Retrieved {len(pathways)} pathways from Salesforce")
        
        return {
            'pathways': pathways,
            'total_count': len(pathways),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_pathways'})
        logger.error(f"Failed to query pathways: {error_info['error_message']}")
        raise


@task(retries=3, retry_delay_seconds=60)
def query_pathway_participants(sf_connection) -> Dict[str, Any]:
    """
    Query pathway participants from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying pathway participants from Salesforce...")
    
    try:
        # Query pathway participants from Salesforce
        participants_query = """
        SELECT Contact__c, Pathway__c
        FROM Pathway_Participant__c
        """
        
        result = sf_connection.query_all(participants_query)
        participants = result.get('records', [])
        
        logger.info(f"Retrieved {len(participants)} pathway participants from Salesforce")
        
        return {
            'participants': participants,
            'total_count': len(participants),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_pathway_participants'})
        logger.error(f"Failed to query pathway participants: {error_info['error_message']}")
        raise


@task(retries=3, retry_delay_seconds=60)
def query_pathway_sessions(sf_connection) -> Dict[str, Any]:
    """
    Query pathway-session relationships from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying pathway-session relationships from Salesforce...")
    
    try:
        # Query pathway-session relationships from Salesforce
        sessions_query = """
        SELECT Session__c, Pathway__c
        FROM Pathway_Session__c
        """
        
        result = sf_connection.query_all(sessions_query)
        sessions = result.get('records', [])
        
        logger.info(f"Retrieved {len(sessions)} pathway-session relationships from Salesforce")
        
        return {
            'sessions': sessions,
            'total_count': len(sessions),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_pathway_sessions'})
        logger.error(f"Failed to query pathway-session relationships: {error_info['error_message']}")
        raise


@task(retries=2, retry_delay_seconds=30)
def process_pathways_batch(pathways_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of pathways from Salesforce.
    
    Args:
        pathways_data: Dictionary containing pathways and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    pathways = pathways_data['pathways']
    
    logger.info(f"Processing {len(pathways)} pathways...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in pathways:
        try:
            # Check if pathway already exists
            existing_pathway = Pathway.query.filter_by(salesforce_id=row['Id']).first()
            
            if existing_pathway:
                # Update existing pathway
                existing_pathway.name = row['Name']
                logger.debug(f"Updated existing pathway: {row['Name']}")
            else:
                # Create new pathway
                new_pathway = Pathway(
                    salesforce_id=row['Id'],
                    name=row['Name']
                )
                db_session.add(new_pathway)
                logger.debug(f"Created new pathway: {row['Name']}")
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing pathway {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} pathways successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@task(retries=2, retry_delay_seconds=30)
def process_pathway_participants_batch(participants_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of pathway participants from Salesforce.
    
    Args:
        participants_data: Dictionary containing participants and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    participants = participants_data['participants']
    
    logger.info(f"Processing {len(participants)} pathway participants...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in participants:
        try:
            # Find the pathway
            pathway = Pathway.query.filter_by(salesforce_id=row['Pathway__c']).first()
            if not pathway:
                error_count += 1
                errors.append(f"Pathway not found for participant: {row['Pathway__c']}")
                continue
            
            # Find the contact
            contact = Contact.query.filter_by(salesforce_individual_id=row['Contact__c']).first()
            if not contact:
                error_count += 1
                errors.append(f"Contact not found for participant: {row['Contact__c']}")
                continue
            
            # Add contact to pathway's contacts if not already present
            if contact not in pathway.contacts:
                pathway.contacts.append(contact)
                success_count += 1
                logger.debug(f"Added participant {contact.first_name} {contact.last_name} to pathway {pathway.name}")
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing pathway-participant relationship: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} pathway participants successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@task(retries=2, retry_delay_seconds=30)
def process_pathway_sessions_batch(sessions_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of pathway-session relationships from Salesforce.
    
    Args:
        sessions_data: Dictionary containing sessions and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    sessions = sessions_data['sessions']
    
    logger.info(f"Processing {len(sessions)} pathway-session relationships...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in sessions:
        try:
            # Find the pathway
            pathway = Pathway.query.filter_by(salesforce_id=row['Pathway__c']).first()
            if not pathway:
                error_count += 1
                errors.append(f"Pathway not found for session relationship: {row['Pathway__c']}")
                continue
            
            # Find the event
            event = Event.query.filter_by(salesforce_id=row['Session__c']).first()
            if not event:
                error_count += 1
                errors.append(f"Event not found for session relationship: {row['Session__c']}")
                continue
            
            # Add event to pathway's events if not already present
            if event not in pathway.events:
                pathway.events.append(event)
                success_count += 1
                logger.debug(f"Added event {event.title} to pathway {pathway.name}")
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing pathway-session relationship: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} pathway-session relationships successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@flow(name="pathways-sync")
def pathways_sync_flow() -> Dict[str, Any]:
    """
    Main workflow for synchronizing pathways and participants from Salesforce.
    
    This workflow:
    1. Connects to Salesforce and database
    2. Queries pathways, participants, and session relationships from Salesforce
    3. Processes pathways in batches
    4. Processes participants in batches
    5. Processes session relationships in batches
    6. Commits all changes to database
    7. Returns comprehensive results
    
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    
    # Log workflow start
    start_time = datetime.now(timezone.utc)
    log_workflow_start("pathways_sync_flow", {})
    
    try:
        # Validate environment
        validate_environment()
        
        # Get connections
        sf_connection = salesforce_connection()
        db_session = database_connection()
        
        # Query data from Salesforce
        pathways_data = query_pathways(sf_connection)
        participants_data = query_pathway_participants(sf_connection)
        sessions_data = query_pathway_sessions(sf_connection)
        
        # Process pathways
        pathways_result = process_pathways_batch(pathways_data, db_session)
        
        # Process participants
        participants_result = process_pathway_participants_batch(participants_data, db_session)
        
        # Process session relationships
        sessions_result = process_pathway_sessions_batch(sessions_data, db_session)
        
        # Commit all changes
        db_session.commit()
        
        # Prepare results
        total_success = (
            pathways_result['success_count'] + 
            participants_result['success_count'] + 
            sessions_result['success_count']
        )
        total_errors = (
            pathways_result['error_count'] + 
            participants_result['error_count'] + 
            sessions_result['error_count']
        )
        all_errors = (
            pathways_result['errors'] + 
            participants_result['errors'] + 
            sessions_result['errors']
        )
        
        # Create error summary if there are errors
        error_summary = None
        if all_errors:
            error_summary = create_error_summary(all_errors)
        
        # Log workflow completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        log_workflow_completion("pathways_sync_flow", {
            'total_success': total_success,
            'total_errors': total_errors,
            'pathways_success': pathways_result['success_count'],
            'pathways_errors': pathways_result['error_count'],
            'participants_success': participants_result['success_count'],
            'participants_errors': participants_result['error_count'],
            'sessions_success': sessions_result['success_count'],
            'sessions_errors': sessions_result['error_count'],
            'duration_seconds': duration.total_seconds()
        })
        
        logger.info(f"Pathways sync completed: {total_success} successes, {total_errors} errors")
        
        return {
            'success': True,
            'message': f'Successfully processed {total_success} records with {total_errors} errors',
            'pathways_success': pathways_result['success_count'],
            'pathways_errors': pathways_result['error_count'],
            'participants_success': participants_result['success_count'],
            'participants_errors': participants_result['error_count'],
            'sessions_success': sessions_result['success_count'],
            'sessions_errors': sessions_result['error_count'],
            'errors': all_errors[:10],  # Limit error display
            'error_summary': error_summary,
            'duration': format_duration(duration)
        }
        
    except Exception as e:
        # Log workflow failure
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        error_context = create_error_context(e, {
            'workflow': 'pathways_sync_flow',
            'start_time': start_time,
            'duration': duration
        })
        
        logger.error(f"Pathways sync failed: {error_context['error_message']}")
        
        return {
            'success': False,
            'error': error_context['error_message'],
            'error_type': error_context['error_type'],
            'duration': format_duration(duration)
        } 
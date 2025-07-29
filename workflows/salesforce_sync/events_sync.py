"""
Events Sync Workflow Module
==========================

This module provides Prefect workflows for synchronizing events and participants
from Salesforce to the local VMS database.

Key Features:
- Event data synchronization from Salesforce Session__c objects
- Participant data synchronization from Session_Participant__c objects
- Comprehensive error handling and retry logic
- Chunked processing for large datasets
- Detailed logging and metrics tracking

Workflows:
- events_sync_flow: Main workflow for event synchronization
- process_events_batch: Task for processing event batches
- process_participants_batch: Task for processing participant batches

Dependencies:
- Salesforce API integration
- Event and Contact models
- District and School models
- Prefect workflow utilities
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from prefect import flow, task, get_run_logger
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.event import Event, EventType, EventStatus, EventFormat
from models.contact import Contact
from models.district_model import District
from models.school_model import School
from routes.utils import DISTRICT_MAPPINGS, map_cancellation_reason, map_event_format, map_session_type, parse_date, parse_event_skills

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
def query_events(sf_connection) -> Dict[str, Any]:
    """
    Query events from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying events from Salesforce...")
    
    try:
        # Query events from Salesforce
        events_query = """
        SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c, 
            End_Date_and_Time__c, Session_Status__c, Location_Information__c, 
            Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c, 
            District__c, School__c, Legacy_Skill_Covered_for_the_Session__c, 
            Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
            Total_Requested_Volunteer_Jobs__c, Available_Slots__c, Parent_Account__c,
            Session_Host__c
        FROM Session__c
        WHERE Session_Status__c != 'Draft' AND Session_Type__c != 'Connector Session'
        ORDER BY Start_Date_and_Time__c DESC
        """
        
        result = sf_connection.query_all(events_query)
        events = result.get('records', [])
        
        logger.info(f"Retrieved {len(events)} events from Salesforce")
        
        return {
            'events': events,
            'total_count': len(events),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_events'})
        logger.error(f"Failed to query events: {error_info['error_message']}")
        raise


@task(retries=3, retry_delay_seconds=60)
def query_participants(sf_connection) -> Dict[str, Any]:
    """
    Query participants from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying participants from Salesforce...")
    
    try:
        # Query participants from Salesforce
        participants_query = """
        SELECT
            Id,
            Name,
            Contact__c,
            Session__c,
            Status__c,
            Delivery_Hours__c,
            Age_Group__c,
            Email__c,
            Title__c
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Student'
        ORDER BY Session__c, Name
        """
        
        result = sf_connection.query_all(participants_query)
        participants = result.get('records', [])
        
        logger.info(f"Retrieved {len(participants)} participants from Salesforce")
        
        return {
            'participants': participants,
            'total_count': len(participants),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_participants'})
        logger.error(f"Failed to query participants: {error_info['error_message']}")
        raise


@task(retries=2, retry_delay_seconds=30)
def process_events_batch(events_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of events from Salesforce.
    
    Args:
        events_data: Dictionary containing events and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    events = events_data['events']
    
    logger.info(f"Processing {len(events)} events...")
    
    success_count = 0
    error_count = 0
    errors = []
    status_counts = {}
    
    for row in events:
        try:
            # Check if event already exists
            existing_event = Event.query.filter_by(salesforce_id=row['Id']).first()
            
            if existing_event:
                # Update existing event
                event = existing_event
                logger.debug(f"Updating existing event: {row['Name']}")
            else:
                # Create new event
                event = Event()
                event.salesforce_id = row['Id']
                db_session.add(event)
                logger.debug(f"Creating new event: {row['Name']}")
            
            # Update event fields
            event.title = row.get('Name', '')
            event.session_type = map_session_type(row.get('Session_Type__c'))
            event.format = map_event_format(row.get('Format__c'))
            
            # Handle dates
            if row.get('Start_Date_and_Time__c'):
                event.start_time = parse_date(row['Start_Date_and_Time__c'])
            if row.get('End_Date_and_Time__c'):
                event.end_time = parse_date(row['End_Date_and_Time__c'])
            
            # Handle status
            status = row.get('Session_Status__c', '').lower()
            if status == 'completed':
                event.status = EventStatus.COMPLETED
            elif status == 'cancelled':
                event.status = EventStatus.CANCELLED
            elif status == 'scheduled':
                event.status = EventStatus.SCHEDULED
            else:
                event.status = EventStatus.SCHEDULED
            
            # Handle location and description
            event.location = row.get('Location_Information__c', '')
            event.description = row.get('Description__c', '')
            event.cancellation_reason = map_cancellation_reason(row.get('Cancellation_Reason__c'))
            
            # Handle numeric fields
            def safe_convert_to_int(value, default=0):
                if value is None:
                    return default
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return default
            
            event.participant_count = safe_convert_to_int(row.get('Non_Scheduled_Students_Count__c'))
            event.total_requested_volunteer_jobs = safe_convert_to_int(row.get('Total_Requested_Volunteer_Jobs__c'))
            event.available_slots = safe_convert_to_int(row.get('Available_Slots__c'))
            
            # Handle additional information
            event.additional_information = row.get('Additional_Information__c', '')
            event.session_host = row.get('Session_Host__c', '')
            
            # Handle skills
            skills_covered = row.get('Legacy_Skill_Covered_for_the_Session__c', '')
            skills_needed = row.get('Legacy_Skills_Needed__c', '')
            requested_skills = row.get('Requested_Skills__c', '')
            
            if skills_covered or skills_needed or requested_skills:
                event.skills = parse_event_skills(skills_covered, skills_needed, requested_skills)
            
            # Handle School relationship
            school_id = row.get('School__c')
            if school_id:
                school = School.query.get(school_id)
                if school:
                    event.school = school_id
                    school_district = school.district
                else:
                    school_district = None
            else:
                school_district = None
            
            # Handle District relationship
            district_name = row.get('District__c')
            parent_account = row.get('Parent_Account__c')
            
            # If District__c is empty, use Parent_Account__c instead
            if not district_name and parent_account:
                district_name = parent_account
            
            # Try to get the district
            district = None
            if district_name and district_name in DISTRICT_MAPPINGS:
                mapped_name = DISTRICT_MAPPINGS[district_name]
                district = District.query.filter_by(name=mapped_name).first()
            
            # Clear and reassign districts if we have a valid district to assign
            if district or school_district:
                event.districts = []  # Clear existing districts
                if school_district:
                    event.districts.append(school_district)
                if district and district not in event.districts:
                    event.districts.append(district)
            
            # Track status counts
            status = event.status.value if event.status else 'unknown'
            status_counts[status] = status_counts.get(status, 0) + 1
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing event {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} events successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors,
        'status_counts': status_counts
    }


@task(retries=2, retry_delay_seconds=30)
def process_participants_batch(participants_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of participants from Salesforce.
    
    Args:
        participants_data: Dictionary containing participants and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    participants = participants_data['participants']
    
    logger.info(f"Processing {len(participants)} participants...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in participants:
        try:
            # Find the event
            event = Event.query.filter_by(salesforce_id=row['Session__c']).first()
            if not event:
                error_count += 1
                errors.append(f"Event not found for participant {row.get('Name', 'Unknown')}: {row['Session__c']}")
                continue
            
            # Find the contact
            contact = Contact.query.filter_by(salesforce_individual_id=row['Contact__c']).first()
            if not contact:
                error_count += 1
                errors.append(f"Contact not found for participant {row.get('Name', 'Unknown')}: {row['Contact__c']}")
                continue
            
            # Check if participation already exists
            existing_participation = next(
                (p for p in event.participants if p.contact_id == contact.id),
                None
            )
            
            if not existing_participation:
                # Add contact to event participants
                event.participants.append(contact)
                success_count += 1
                logger.debug(f"Added participant {contact.first_name} {contact.last_name} to event {event.title}")
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing participant {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} participants successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@flow(name="events-sync")
def events_sync_flow() -> Dict[str, Any]:
    """
    Main workflow for synchronizing events and participants from Salesforce.
    
    This workflow:
    1. Connects to Salesforce and database
    2. Queries events and participants from Salesforce
    3. Processes events in batches
    4. Processes participants in batches
    5. Commits all changes to database
    6. Returns comprehensive results
    
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    
    # Log workflow start
    start_time = datetime.now(timezone.utc)
    log_workflow_start("events_sync_flow", {})
    
    try:
        # Validate environment
        validate_environment()
        
        # Get connections
        sf_connection = salesforce_connection()
        db_session = database_connection()
        
        # Query data from Salesforce
        events_data = query_events(sf_connection)
        participants_data = query_participants(sf_connection)
        
        # Process events
        events_result = process_events_batch(events_data, db_session)
        
        # Process participants
        participants_result = process_participants_batch(participants_data, db_session)
        
        # Commit all changes
        db_session.commit()
        
        # Prepare results
        total_success = events_result['success_count'] + participants_result['success_count']
        total_errors = events_result['error_count'] + participants_result['error_count']
        all_errors = events_result['errors'] + participants_result['errors']
        
        # Create error summary if there are errors
        error_summary = None
        if all_errors:
            error_summary = create_error_summary(all_errors)
        
        # Log workflow completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        log_workflow_completion("events_sync_flow", {
            'total_success': total_success,
            'total_errors': total_errors,
            'events_success': events_result['success_count'],
            'events_errors': events_result['error_count'],
            'participants_success': participants_result['success_count'],
            'participants_errors': participants_result['error_count'],
            'status_counts': events_result['status_counts'],
            'duration_seconds': duration.total_seconds()
        })
        
        logger.info(f"Events sync completed: {total_success} successes, {total_errors} errors")
        
        return {
            'success': True,
            'message': f'Successfully processed {total_success} records with {total_errors} errors',
            'events_success': events_result['success_count'],
            'events_errors': events_result['error_count'],
            'participants_success': participants_result['success_count'],
            'participants_errors': participants_result['error_count'],
            'status_counts': events_result['status_counts'],
            'errors': all_errors[:10],  # Limit error display
            'error_summary': error_summary,
            'duration': format_duration(duration)
        }
        
    except Exception as e:
        # Log workflow failure
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        error_context = create_error_context(e, {
            'workflow': 'events_sync_flow',
            'start_time': start_time,
            'duration': duration
        })
        
        logger.error(f"Events sync failed: {error_context['error_message']}")
        
        return {
            'success': False,
            'error': error_context['error_message'],
            'error_type': error_context['error_type'],
            'duration': format_duration(duration)
        } 
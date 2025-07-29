"""
Volunteers Sync Workflow
========================

Prefect workflow for synchronizing volunteer data from Salesforce.
This workflow handles large datasets with chunked processing and comprehensive
error handling.

Features:
- Chunked processing for large volunteer datasets
- Comprehensive volunteer data mapping
- Education and skill mapping
- Address and contact information handling
- Connector data integration
- Detailed progress tracking and reporting
"""

import time
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from prefect import flow, task, get_run_logger
from sqlalchemy.orm import Session

from workflows.base_workflow import (
    salesforce_connection, 
    database_connection, 
    validate_environment,
    workflow_decorator
)
from workflows.utils.prefect_helpers import (
    log_workflow_start,
    log_workflow_completion,
    format_duration,
    get_memory_usage
)
from workflows.utils.error_handling import (
    PrefectErrorHandler,
    handle_salesforce_error,
    handle_database_error,
    log_error_with_context,
    create_error_summary
)


@task(retries=3, retry_delay_seconds=60)
def get_volunteer_count(sf_connection) -> int:
    """
    Get total count of volunteers in Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Total number of volunteers
    """
    logger = get_run_logger()
    logger.info("Getting volunteer count from Salesforce...")
    
    try:
        count_query = """
        SELECT COUNT(Id) total
        FROM Contact 
        WHERE Contact_Type__c = 'Volunteer' or Contact_Type__c=''
        """
        
        result = sf_connection.query(count_query)
        if not result or 'records' not in result or not result['records']:
            raise ValueError("Failed to get volunteer count from Salesforce")
        
        total_count = result['records'][0]['total']
        logger.info(f"Total volunteers in Salesforce: {total_count}")
        
        return total_count
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'get_volunteer_count'})
        logger.error(f"Failed to get volunteer count: {error_info}")
        raise


@task(retries=3, retry_delay_seconds=60)
def query_volunteers_chunk(sf_connection, chunk_size: int = 2000, last_id: str = None) -> Dict[str, Any]:
    """
    Query a chunk of volunteers from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        chunk_size: Number of records to retrieve
        last_id: ID of last processed record for pagination
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info(f"Querying volunteers chunk (size: {chunk_size}, last_id: {last_id})...")
    
    try:
        # Build query with pagination
        base_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email,
               npe01__AlternateEmail__c, npe01__HomeEmail__c, 
               npe01__WorkEmail__c, npe01__Preferred_Email__c,
               HomePhone, MobilePhone, npe01__WorkPhone__c, Phone,
               npe01__PreferredPhone__c,
               npsp__Primary_Affiliation__c, Title, Department, Gender__c, 
               Birthdate, Last_Mailchimp_Email_Date__c, Last_Volunteer_Date__c, 
               Last_Email_Message__c, Volunteer_Recruitment_Notes__c, 
               Volunteer_Skills__c, Volunteer_Skills_Text__c,
               Volunteer_Interests__c,
               Number_of_Attended_Volunteer_Sessions__c,
               Racial_Ethnic_Background__c,
               Last_Activity_Date__c,
               First_Volunteer_Date__c,
               Last_Non_Internal_Email_Activity__c,
               Description, Highest_Level_of_Educational__c, Age_Group__c,
               DoNotCall, npsp__Do_Not_Contact__c, HasOptedOutOfEmail,
               EmailBouncedDate,
               MailingAddress, npe01__Home_Address__c, npe01__Work_Address__c,
               npe01__Other_Address__c, npe01__Primary_Address_Type__c,
               npe01__Secondary_Address_Type__c,
               Connector_Active_Subscription__c,
               Connector_Active_Subscription_Name__c,
               Connector_Affiliations__c,
               Connector_Industry__c,
               Connector_Joining_Date__c,
               Connector_Last_Login_Date_Time__c,
               Connector_Last_Update_Date__c,
               Connector_Profile_Link__c,
               Connector_Role__c,
               Connector_SignUp_Role__c,
               Connector_User_ID__c
        FROM Contact
        WHERE Contact_Type__c = 'Volunteer' or Contact_Type__c=''
        """
        
        if last_id:
            base_query += f" AND Id > '{last_id}'"
        
        base_query += f" ORDER BY Id ASC LIMIT {chunk_size}"
        
        result = sf_connection.query_all(base_query)
        volunteers = result.get('records', [])
        
        logger.info(f"Retrieved {len(volunteers)} volunteers from Salesforce")
        
        return {
            'volunteers': volunteers,
            'chunk_size': len(volunteers),
            'last_id': volunteers[-1]['Id'] if volunteers else last_id,
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {
            'operation': 'query_volunteers_chunk',
            'chunk_size': chunk_size,
            'last_id': last_id
        })
        logger.error(f"Failed to query volunteers chunk: {error_info}")
        raise


@task
def process_volunteers_chunk(volunteer_data: Dict[str, Any], db_session: Session) -> Dict[str, Any]:
    """
    Process a chunk of volunteers and import into database.
    
    Args:
        volunteer_data: Volunteer data from Salesforce
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    logger.info("Processing volunteers chunk...")
    
    from models.volunteer import Volunteer, ConnectorData
    from models.contact import Contact, ContactTypeEnum
    from routes.utils import parse_date
    
    volunteers = volunteer_data['volunteers']
    success_count = 0
    error_count = 0
    created_count = 0
    updated_count = 0
    errors = []
    
    # Education mapping
    education_mapping = {
        'BACHELORS': 'BACHELORS_DEGREE',
        'MASTERS': 'MASTERS',
        'DOCTORATE': 'DOCTORATE',
        'BACHELOR': 'BACHELORS_DEGREE',
        'BACHELOR\'S': 'BACHELORS_DEGREE',
        'BACHELORS DEGREE': 'BACHELORS_DEGREE',
        'MASTER': 'MASTERS',
        'MASTER\'S': 'MASTERS',
        'MASTERS DEGREE': 'MASTERS',
        'PHD': 'DOCTORATE',
        'PH.D': 'DOCTORATE',
        'PH.D.': 'DOCTORATE',
        'DOCTORAL': 'DOCTORATE',
        'HIGH SCHOOL DIPLOMA OR GED': 'HIGH_SCHOOL',
        'ADVANCED PROFESSIONAL DEGREE': 'PROFESSIONAL',
        'PREFER NOT TO ANSWER': 'UNKNOWN',
        'CERTIFICATE': 'OTHER',
        'CERTIFICATION': 'OTHER',
        'ASSOCIATE': 'ASSOCIATES',
        'ASSOCIATES': 'ASSOCIATES',
        'ASSOCIATE\'S': 'ASSOCIATES',
        'HIGH SCHOOL': 'HIGH_SCHOOL',
        'GED': 'HIGH_SCHOOL',
        'SOME COLLEGE': 'SOME_COLLEGE',
        'PROFESSIONAL': 'PROFESSIONAL',
        'PROFESSIONAL DEGREE': 'PROFESSIONAL'
    }
    
    for volunteer_row in volunteers:
        try:
            # Check if volunteer exists
            volunteer = Volunteer.query.filter_by(salesforce_individual_id=volunteer_row['Id']).first()
            is_new = False
            updates = []
            
            if not volunteer:
                volunteer = Volunteer()
                volunteer.salesforce_individual_id = volunteer_row['Id']
                db_session.add(volunteer)
                is_new = True
                updates.append('Created new volunteer')
            
            # Update volunteer fields
            if volunteer.salesforce_account_id != volunteer_row['AccountId']:
                volunteer.salesforce_account_id = volunteer_row['AccountId']
                updates.append('account_id')
            
            new_first_name = (volunteer_row.get('FirstName') or '').strip()
            if volunteer.first_name != new_first_name:
                volunteer.first_name = new_first_name
                updates.append('first_name')
            
            new_last_name = (volunteer_row.get('LastName') or '').strip()
            if volunteer.last_name != new_last_name:
                volunteer.last_name = new_last_name
                updates.append('last_name')
            
            new_middle_name = (volunteer_row.get('MiddleName') or '').strip()
            if volunteer.middle_name != new_middle_name:
                volunteer.middle_name = new_middle_name
                updates.append('middle_name')
            
            new_org_name = (volunteer_row.get('npsp__Primary_Affiliation__c') or '').strip()
            if volunteer.organization_name != new_org_name:
                volunteer.organization_name = new_org_name
                updates.append('organization')
            
            new_title = (volunteer_row.get('Title') or '').strip()
            if volunteer.title != new_title:
                volunteer.title = new_title
                updates.append('title')
            
            new_department = (volunteer_row.get('Department') or '').strip()
            if volunteer.department != new_department:
                volunteer.department = new_department
                updates.append('department')
            
            # Handle education level mapping
            sf_education = (volunteer_row.get('Highest_Level_of_Educational__c') or '').strip().upper()
            if sf_education:
                mapped_education = education_mapping.get(sf_education, 'UNKNOWN')
                if volunteer.education_level != mapped_education:
                    volunteer.education_level = mapped_education
                    updates.append('education_level')
            
            # Handle dates
            if volunteer_row.get('Birthdate'):
                birthdate = parse_date(volunteer_row['Birthdate'])
                if volunteer.birthdate != birthdate:
                    volunteer.birthdate = birthdate
                    updates.append('birthdate')
            
            if volunteer_row.get('Last_Volunteer_Date__c'):
                last_volunteer_date = parse_date(volunteer_row['Last_Volunteer_Date__c'])
                if volunteer.last_volunteer_date != last_volunteer_date:
                    volunteer.last_volunteer_date = last_volunteer_date
                    updates.append('last_volunteer_date')
            
            if volunteer_row.get('First_Volunteer_Date__c'):
                first_volunteer_date = parse_date(volunteer_row['First_Volunteer_Date__c'])
                if volunteer.first_volunteer_date != first_volunteer_date:
                    volunteer.first_volunteer_date = first_volunteer_date
                    updates.append('first_volunteer_date')
            
            # Handle contact information
            new_email = (volunteer_row.get('Email') or '').strip()
            if volunteer.email != new_email:
                volunteer.email = new_email
                updates.append('email')
            
            new_phone = (volunteer_row.get('Phone') or '').strip()
            if volunteer.phone != new_phone:
                volunteer.phone = new_phone
                updates.append('phone')
            
            # Handle skills and interests
            new_skills = (volunteer_row.get('Volunteer_Skills__c') or '').strip()
            if volunteer.skills != new_skills:
                volunteer.skills = new_skills
                updates.append('skills')
            
            new_interests = (volunteer_row.get('Volunteer_Interests__c') or '').strip()
            if volunteer.interests != new_interests:
                volunteer.interests = new_interests
                updates.append('interests')
            
            # Handle connector data
            connector_data = {
                'active_subscription': (volunteer_row.get('Connector_Active_Subscription__c') or '').strip().upper() or 'NONE',
                'active_subscription_name': (volunteer_row.get('Connector_Active_Subscription_Name__c') or '').strip(),
                'affiliations': (volunteer_row.get('Connector_Affiliations__c') or '').strip(),
                'industry': (volunteer_row.get('Connector_Industry__c') or '').strip(),
                'joining_date': (volunteer_row.get('Connector_Joining_Date__c') or '').strip(),
                'last_login_datetime': (volunteer_row.get('Connector_Last_Login_Date_Time__c') or '').strip(),
                'last_update_date': parse_date(volunteer_row.get('Connector_Last_Update_Date__c')),
                'profile_link': (volunteer_row.get('Connector_Profile_Link__c') or '').strip(),
                'role': (volunteer_row.get('Connector_Role__c') or '').strip(),
                'signup_role': (volunteer_row.get('Connector_SignUp_Role__c') or '').strip(),
                'user_auth_id': (volunteer_row.get('Connector_User_ID__c') or '').strip()
            }
            
            # Create or update connector data
            if not volunteer.connector:
                volunteer.connector = ConnectorData(volunteer_id=volunteer.id)
                updates.append('connector_created')
            
            # Update connector fields
            for key, value in connector_data.items():
                if hasattr(volunteer.connector, key) and getattr(volunteer.connector, key) != value:
                    setattr(volunteer.connector, key, value)
                    updates.append(f'connector_{key}')
            
            if is_new:
                created_count += 1
            elif updates:
                updated_count += 1
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing volunteer {volunteer_row.get('FirstName', '')} {volunteer_row.get('LastName', '')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    # Commit all changes
    try:
        db_session.commit()
        logger.info(f"Successfully processed {success_count} volunteers (created: {created_count}, updated: {updated_count})")
    except Exception as e:
        db_session.rollback()
        error_info = handle_database_error(e, {'operation': 'commit_volunteers'})
        logger.error(f"Failed to commit volunteers: {error_info}")
        raise
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'created_count': created_count,
        'updated_count': updated_count,
        'errors': errors,
        'total_processed': len(volunteers)
    }


@workflow_decorator("volunteers-sync")
def volunteers_sync_flow(chunk_size: int = 2000) -> Dict[str, Any]:
    """
    Main volunteers synchronization workflow.
    
    This workflow synchronizes volunteer data from Salesforce with chunked
    processing for large datasets and comprehensive error handling.
    
    Args:
        chunk_size: Number of records to process per chunk (default: 2000)
        
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    start_time = datetime.now(timezone.utc)
    
    logger.info(f"Starting volunteers sync workflow (chunk_size: {chunk_size})")
    
    # Track overall results
    total_success = 0
    total_errors = 0
    total_created = 0
    total_updated = 0
    all_errors = []
    chunks_processed = 0
    
    try:
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
        
        # Get total count for progress tracking
        total_count = get_volunteer_count.submit(sf_connection)
        total_volunteers = total_count.result()
        
        logger.info(f"Total volunteers to process: {total_volunteers}")
        
        # Process in chunks
        last_id = None
        while True:
            # Query chunk
            chunk_data = query_volunteers_chunk.submit(sf_connection, chunk_size, last_id)
            chunk_result = chunk_data.result()
            
            if not chunk_result['volunteers']:
                logger.info("No more volunteers to process")
                break
            
            # Process chunk
            chunk_processing = process_volunteers_chunk.submit(chunk_result, db_connection)
            processing_result = chunk_processing.result()
            
            # Update totals
            total_success += processing_result['success_count']
            total_errors += processing_result['error_count']
            total_created += processing_result['created_count']
            total_updated += processing_result['updated_count']
            all_errors.extend(processing_result['errors'])
            chunks_processed += 1
            
            # Update last_id for next iteration
            last_id = chunk_result['last_id']
            
            # Log progress
            progress = (total_success / total_volunteers) * 100 if total_volunteers > 0 else 0
            logger.info(f"Progress: {progress:.1f}% ({total_success}/{total_volunteers}) - Chunk {chunks_processed}")
            
            # Check if we've processed all records
            if len(chunk_result['volunteers']) < chunk_size:
                logger.info("Reached end of volunteer data")
                break
        
        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Get memory usage
        memory_info = get_memory_usage()
        
        # Create result summary
        result = {
            'status': 'success',
            'total_success': total_success,
            'total_errors': total_errors,
            'total_created': total_created,
            'total_updated': total_updated,
            'chunks_processed': chunks_processed,
            'duration_seconds': duration,
            'duration_formatted': format_duration(duration),
            'memory_usage': memory_info,
            'chunk_size': chunk_size,
            'error_summary': create_error_summary(all_errors),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        log_workflow_completion("volunteers-sync", result, duration)
        logger.info(f"Volunteers sync completed successfully: {total_success} successes, {total_errors} errors")
        
        return result
        
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        log_error_with_context(e, "volunteers-sync", context={
            'chunk_size': chunk_size,
            'total_success': total_success,
            'total_errors': total_errors,
            'chunks_processed': chunks_processed
        })
        
        return {
            'status': 'error',
            'error_message': str(e),
            'error_type': PrefectErrorHandler.classify_error(e),
            'total_success': total_success,
            'total_errors': total_errors,
            'total_created': total_created,
            'total_updated': total_updated,
            'chunks_processed': chunks_processed,
            'duration_seconds': duration,
            'duration_formatted': format_duration(duration),
            'chunk_size': chunk_size,
            'error_summary': create_error_summary(all_errors),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        } 
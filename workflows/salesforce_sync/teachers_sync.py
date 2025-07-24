"""
Teachers sync workflow for Salesforce data synchronization.

This module implements the Prefect workflow for synchronizing teacher data
from Salesforce to the local VMS database. It handles large datasets using
chunked processing and includes comprehensive error handling and logging.
"""

from prefect import task, flow
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from workflows.base_workflow import (
    salesforce_connection,
    database_connection,
    validate_environment,
    log_workflow_metrics,
    workflow_decorator
)
from workflows.utils.prefect_helpers import get_workflow_logger
from workflows.utils.error_handling import resilient_task, PrefectErrorHandler
from models.teacher import Teacher, TeacherStatus
from models.school import School
from models.contact import Contact, Email, Phone, ContactTypeEnum


@task
@resilient_task
def get_teacher_count() -> int:
    """
    Get the total number of teacher records from Salesforce.
    
    Returns:
        int: Total number of teacher records
    """
    logger = get_workflow_logger()
    logger.info("Retrieving total teacher count from Salesforce")
    
    sf = salesforce_connection()
    
    # Query for teachers (Contact records with Teacher__c = true)
    query = """
        SELECT COUNT() 
        FROM Contact 
        WHERE Teacher__c = true
    """
    
    result = sf.query(query)
    count = result['totalSize']
    
    logger.info(f"Found {count} teacher records in Salesforce")
    return count


@task
@resilient_task
def query_teachers_chunk(offset: int, limit: int) -> List[Dict[str, Any]]:
    """
    Query a chunk of teacher data from Salesforce.
    
    Args:
        offset (int): Offset for pagination
        limit (int): Number of records to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of teacher records
    """
    logger = get_workflow_logger()
    logger.info(f"Querying teachers chunk: offset={offset}, limit={limit}")
    
    sf = salesforce_connection()
    
    # Query for teachers with all relevant fields
    query = f"""
        SELECT Id, FirstName, LastName, Email, Phone,
               MailingStreet, MailingCity, MailingState, MailingPostalCode,
               Gender__c, Department, npsp__Primary_Affiliation__c,
               School__r.Name, School__r.Id,
               Connector_Role__c, Connector_Active__c,
               Connector_Start_Date__c, Connector_End_Date__c,
               Last_Email_Message__c, Last_Mailchimp_Email_Date__c,
               CreatedDate, LastModifiedDate
        FROM Contact 
        WHERE Teacher__c = true
        ORDER BY Id
        LIMIT {limit} 
        OFFSET {offset}
    """
    
    result = sf.query(query)
    records = result.get('records', [])
    
    logger.info(f"Retrieved {len(records)} teacher records")
    return records


@task
@resilient_task
def process_teachers_chunk(teachers_data: List[Dict[str, Any]], chunk_number: int) -> Dict[str, Any]:
    """
    Process a chunk of teacher data and import into the database.
    
    Args:
        teachers_data (List[Dict[str, Any]]): List of teacher records from Salesforce
        chunk_number (int): Chunk number for logging purposes
        
    Returns:
        Dict[str, Any]: Processing statistics
    """
    logger = get_workflow_logger()
    logger.info(f"Processing teachers chunk {chunk_number} with {len(teachers_data)} records")
    
    session = database_connection()
    
    stats = {
        'processed': 0,
        'created': 0,
        'updated': 0,
        'errors': 0,
        'errors_detail': []
    }
    
    try:
        for teacher_record in teachers_data:
            try:
                # Check if teacher already exists
                existing_teacher = session.query(Teacher).filter(
                    Teacher.salesforce_contact_id == teacher_record['Id']
                ).first()
                
                # Get or create associated school
                school = None
                if teacher_record.get('npsp__Primary_Affiliation__c'):
                    school = session.query(School).filter(
                        School.salesforce_id == teacher_record['npsp__Primary_Affiliation__c']
                    ).first()
                
                # Parse connector dates
                connector_start_date = None
                connector_end_date = None
                
                if teacher_record.get('Connector_Start_Date__c'):
                    try:
                        connector_start_date = datetime.fromisoformat(
                            teacher_record['Connector_Start_Date__c'].split('T')[0]
                        ).date()
                    except (ValueError, AttributeError):
                        pass
                
                if teacher_record.get('Connector_End_Date__c'):
                    try:
                        connector_end_date = datetime.fromisoformat(
                            teacher_record['Connector_End_Date__c'].split('T')[0]
                        ).date()
                    except (ValueError, AttributeError):
                        pass
                
                # Parse email tracking dates
                last_email_message = None
                last_mailchimp_date = None
                
                if teacher_record.get('Last_Email_Message__c'):
                    try:
                        last_email_message = datetime.fromisoformat(
                            teacher_record['Last_Email_Message__c'].split('T')[0]
                        ).date()
                    except (ValueError, AttributeError):
                        pass
                
                if teacher_record.get('Last_Mailchimp_Email_Date__c'):
                    try:
                        last_mailchimp_date = datetime.fromisoformat(
                            teacher_record['Last_Mailchimp_Email_Date__c'].split('T')[0]
                        ).date()
                    except (ValueError, AttributeError):
                        pass
                
                if existing_teacher:
                    # Update existing teacher
                    existing_teacher.first_name = teacher_record.get('FirstName', '')
                    existing_teacher.last_name = teacher_record.get('LastName', '')
                    existing_teacher.department = teacher_record.get('Department')
                    existing_teacher.school_id = school.id if school else None
                    existing_teacher.connector_role = teacher_record.get('Connector_Role__c')
                    existing_teacher.connector_active = teacher_record.get('Connector_Active__c', False)
                    existing_teacher.connector_start_date = connector_start_date
                    existing_teacher.connector_end_date = connector_end_date
                    existing_teacher.last_email_message = last_email_message
                    existing_teacher.last_mailchimp_date = last_mailchimp_date
                    existing_teacher.updated_at = datetime.fromisoformat(
                        teacher_record['LastModifiedDate'].replace('Z', '+00:00')
                    )
                    
                    stats['updated'] += 1
                else:
                    # Create new teacher
                    new_teacher = Teacher(
                        salesforce_contact_id=teacher_record['Id'],
                        first_name=teacher_record.get('FirstName', ''),
                        last_name=teacher_record.get('LastName', ''),
                        department=teacher_record.get('Department'),
                        school_id=school.id if school else None,
                        connector_role=teacher_record.get('Connector_Role__c'),
                        connector_active=teacher_record.get('Connector_Active__c', False),
                        connector_start_date=connector_start_date,
                        connector_end_date=connector_end_date,
                        last_email_message=last_email_message,
                        last_mailchimp_date=last_mailchimp_date,
                        status=TeacherStatus.ACTIVE,
                        created_at=datetime.fromisoformat(
                            teacher_record['CreatedDate'].replace('Z', '+00:00')
                        ),
                        updated_at=datetime.fromisoformat(
                            teacher_record['LastModifiedDate'].replace('Z', '+00:00')
                        )
                    )
                    session.add(new_teacher)
                    stats['created'] += 1
                
                # Handle email and phone contact information
                if teacher_record.get('Email'):
                    # Check if email already exists
                    existing_email = session.query(Email).filter(
                        Email.contact_id == (existing_teacher.id if existing_teacher else new_teacher.id),
                        Email.email == teacher_record['Email'],
                        Email.primary == True
                    ).first()
                    
                    if not existing_email:
                        email = Email(
                            contact_id=existing_teacher.id if existing_teacher else new_teacher.id,
                            email=teacher_record['Email'],
                            type=ContactTypeEnum.professional,
                            primary=True
                        )
                        session.add(email)
                
                if teacher_record.get('Phone'):
                    # Check if phone already exists
                    existing_phone = session.query(Phone).filter(
                        Phone.contact_id == (existing_teacher.id if existing_teacher else new_teacher.id),
                        Phone.number == teacher_record['Phone'],
                        Phone.primary == True
                    ).first()
                    
                    if not existing_phone:
                        phone = Phone(
                            contact_id=existing_teacher.id if existing_teacher else new_teacher.id,
                            number=teacher_record['Phone'],
                            type=ContactTypeEnum.professional,
                            primary=True
                        )
                        session.add(phone)
                
                stats['processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing teacher {teacher_record.get('Id', 'Unknown')}: {str(e)}"
                logger.error(error_msg)
                stats['errors'] += 1
                stats['errors_detail'].append(error_msg)
                continue
        
        session.commit()
        logger.info(f"Chunk {chunk_number} completed: {stats['processed']} processed, "
                   f"{stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Database error in chunk {chunk_number}: {str(e)}")
        raise
    
    return stats


@workflow_decorator
def teachers_sync_flow(chunk_size: int = 100) -> Dict[str, Any]:
    """
    Main workflow for synchronizing teacher data from Salesforce.
    
    This workflow handles large teacher datasets by processing them in chunks.
    It includes comprehensive error handling, progress tracking, and detailed logging.
    
    Args:
        chunk_size (int): Number of records to process in each chunk
        
    Returns:
        Dict[str, Any]: Summary of the synchronization process
    """
    logger = get_workflow_logger()
    logger.info("Starting teachers synchronization workflow")
    
    # Validate environment
    validate_environment()
    
    # Get total teacher count
    total_teachers = get_teacher_count()
    
    if total_teachers == 0:
        logger.info("No teachers found in Salesforce")
        return {
            'total_teachers': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'chunks_processed': 0
        }
    
    # Calculate number of chunks
    num_chunks = (total_teachers + chunk_size - 1) // chunk_size
    logger.info(f"Processing {total_teachers} teachers in {num_chunks} chunks of {chunk_size}")
    
    # Process chunks
    total_processed = 0
    total_created = 0
    total_updated = 0
    total_errors = 0
    chunks_processed = 0
    
    for chunk_num in range(num_chunks):
        offset = chunk_num * chunk_size
        
        try:
            # Query chunk
            teachers_chunk = query_teachers_chunk(offset, chunk_size)
            
            if not teachers_chunk:
                logger.info(f"Chunk {chunk_num + 1} is empty, stopping")
                break
            
            # Process chunk
            chunk_stats = process_teachers_chunk(teachers_chunk, chunk_num + 1)
            
            # Update totals
            total_processed += chunk_stats['processed']
            total_created += chunk_stats['created']
            total_updated += chunk_stats['updated']
            total_errors += chunk_stats['errors']
            chunks_processed += 1
            
            # Log progress
            progress = (chunk_num + 1) / num_chunks * 100
            logger.info(f"Progress: {progress:.1f}% ({chunk_num + 1}/{num_chunks} chunks)")
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_num + 1}: {str(e)}")
            total_errors += len(teachers_chunk) if 'teachers_chunk' in locals() else 1
            continue
    
    # Log final results
    logger.info(f"Teachers sync completed: {total_processed} processed, "
               f"{total_created} created, {total_updated} updated, {total_errors} errors")
    
    result = {
        'total_teachers': total_teachers,
        'total_processed': total_processed,
        'total_created': total_created,
        'total_updated': total_updated,
        'total_errors': total_errors,
        'chunks_processed': chunks_processed
    }
    
    # Log workflow metrics
    log_workflow_metrics('teachers_sync', result)
    
    return result


if __name__ == '__main__':
    # For testing purposes
    result = teachers_sync_flow()
    print(f"Teachers sync result: {result}") 
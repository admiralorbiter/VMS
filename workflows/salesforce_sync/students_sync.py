"""
Students sync workflow for Salesforce data synchronization.

This module implements the Prefect workflow for synchronizing student data
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
from models.student import Student
from models.school_model import School
from models.contact import Contact


@task
@resilient_task
def get_student_count() -> int:
    """
    Get the total number of student records from Salesforce.
    
    Returns:
        int: Total number of student records
    """
    logger = get_workflow_logger()
    logger.info("Retrieving total student count from Salesforce")
    
    sf = salesforce_connection()
    
    # Query for students (Contact records with Student__c = true)
    query = """
        SELECT COUNT() 
        FROM Contact 
        WHERE Student__c = true
    """
    
    result = sf.query(query)
    count = result['totalSize']
    
    logger.info(f"Found {count} student records in Salesforce")
    return count


@task
@resilient_task
def query_students_chunk(offset: int, limit: int) -> List[Dict[str, Any]]:
    """
    Query a chunk of student data from Salesforce.
    
    Args:
        offset (int): Offset for pagination
        limit (int): Number of records to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of student records
    """
    logger = get_workflow_logger()
    logger.info(f"Querying students chunk: offset={offset}, limit={limit}")
    
    sf = salesforce_connection()
    
    # Query for students with all relevant fields
    query = f"""
        SELECT Id, FirstName, LastName, Email, Phone,
               MailingStreet, MailingCity, MailingState, MailingPostalCode,
               Birthdate, Grade_Level__c, School__c, School__r.Name,
               Parent_Email__c, Parent_Phone__c, Parent_Name__c,
               Interests__c, Skills__c, Goals__c,
               CreatedDate, LastModifiedDate
        FROM Contact 
        WHERE Student__c = true
        ORDER BY Id
        LIMIT {limit} 
        OFFSET {offset}
    """
    
    result = sf.query(query)
    records = result.get('records', [])
    
    logger.info(f"Retrieved {len(records)} student records")
    return records


@task
@resilient_task
def process_students_chunk(students_data: List[Dict[str, Any]], chunk_number: int) -> Dict[str, Any]:
    """
    Process a chunk of student data and import into the database.
    
    Args:
        students_data (List[Dict[str, Any]]): List of student records from Salesforce
        chunk_number (int): Chunk number for logging purposes
        
    Returns:
        Dict[str, Any]: Processing statistics
    """
    logger = get_workflow_logger()
    logger.info(f"Processing students chunk {chunk_number} with {len(students_data)} records")
    
    session = database_connection()
    
    stats = {
        'processed': 0,
        'created': 0,
        'updated': 0,
        'errors': 0,
        'errors_detail': []
    }
    
    try:
        for student_record in students_data:
            try:
                # Check if student already exists
                existing_student = session.query(Student).filter(
                    Student.salesforce_id == student_record['Id']
                ).first()
                
                # Get or create associated school
                school = None
                if student_record.get('School__c'):
                    school = session.query(School).filter(
                        School.salesforce_id == student_record['School__c']
                    ).first()
                
                # Get or create parent contact
                parent_contact = None
                if student_record.get('Parent_Email__c'):
                    parent_contact = session.query(Contact).filter(
                        Contact.email == student_record['Parent_Email__c']
                    ).first()
                    
                    if not parent_contact:
                        parent_contact = Contact(
                            first_name=student_record.get('Parent_Name__c', '').split()[0] if student_record.get('Parent_Name__c') else '',
                            last_name=student_record.get('Parent_Name__c', '').split()[-1] if student_record.get('Parent_Name__c') else '',
                            email=student_record.get('Parent_Email__c'),
                            phone=student_record.get('Parent_Phone__c'),
                            contact_type='parent'
                        )
                        session.add(parent_contact)
                        session.flush()  # Get the ID
                
                if existing_student:
                    # Update existing student
                    existing_student.first_name = student_record.get('FirstName', '')
                    existing_student.last_name = student_record.get('LastName', '')
                    existing_student.email = student_record.get('Email')
                    existing_student.phone = student_record.get('Phone')
                    existing_student.birthdate = student_record.get('Birthdate')
                    existing_student.grade_level = student_record.get('Grade_Level__c')
                    existing_student.school_id = school.id if school else None
                    existing_student.parent_id = parent_contact.id if parent_contact else None
                    existing_student.interests = student_record.get('Interests__c')
                    existing_student.skills = student_record.get('Skills__c')
                    existing_student.goals = student_record.get('Goals__c')
                    existing_student.last_modified = datetime.fromisoformat(
                        student_record['LastModifiedDate'].replace('Z', '+00:00')
                    )
                    
                    stats['updated'] += 1
                else:
                    # Create new student
                    new_student = Student(
                        salesforce_id=student_record['Id'],
                        first_name=student_record.get('FirstName', ''),
                        last_name=student_record.get('LastName', ''),
                        email=student_record.get('Email'),
                        phone=student_record.get('Phone'),
                        birthdate=student_record.get('Birthdate'),
                        grade_level=student_record.get('Grade_Level__c'),
                        school_id=school.id if school else None,
                        parent_id=parent_contact.id if parent_contact else None,
                        interests=student_record.get('Interests__c'),
                        skills=student_record.get('Skills__c'),
                        goals=student_record.get('Goals__c'),
                        created_date=datetime.fromisoformat(
                            student_record['CreatedDate'].replace('Z', '+00:00')
                        ),
                        last_modified=datetime.fromisoformat(
                            student_record['LastModifiedDate'].replace('Z', '+00:00')
                        )
                    )
                    session.add(new_student)
                    stats['created'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing student {student_record.get('Id', 'Unknown')}: {str(e)}"
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
def students_sync_flow(chunk_size: int = 100) -> Dict[str, Any]:
    """
    Main workflow for synchronizing student data from Salesforce.
    
    This workflow handles large student datasets by processing them in chunks.
    It includes comprehensive error handling, progress tracking, and detailed logging.
    
    Args:
        chunk_size (int): Number of records to process in each chunk
        
    Returns:
        Dict[str, Any]: Summary of the synchronization process
    """
    logger = get_workflow_logger()
    logger.info("Starting students synchronization workflow")
    
    # Validate environment
    validate_environment()
    
    # Get total student count
    total_students = get_student_count()
    
    if total_students == 0:
        logger.info("No students found in Salesforce")
        return {
            'total_students': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'chunks_processed': 0
        }
    
    # Calculate number of chunks
    num_chunks = (total_students + chunk_size - 1) // chunk_size
    logger.info(f"Processing {total_students} students in {num_chunks} chunks of {chunk_size}")
    
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
            students_chunk = query_students_chunk(offset, chunk_size)
            
            if not students_chunk:
                logger.info(f"Chunk {chunk_num + 1} is empty, stopping")
                break
            
            # Process chunk
            chunk_stats = process_students_chunk(students_chunk, chunk_num + 1)
            
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
            total_errors += len(students_chunk) if 'students_chunk' in locals() else 1
            continue
    
    # Log final results
    logger.info(f"Students sync completed: {total_processed} processed, "
               f"{total_created} created, {total_updated} updated, {total_errors} errors")
    
    result = {
        'total_students': total_students,
        'total_processed': total_processed,
        'total_created': total_created,
        'total_updated': total_updated,
        'total_errors': total_errors,
        'chunks_processed': chunks_processed
    }
    
    # Log workflow metrics
    log_workflow_metrics('students_sync', result)
    
    return result


if __name__ == '__main__':
    # For testing purposes
    result = students_sync_flow()
    print(f"Students sync result: {result}") 
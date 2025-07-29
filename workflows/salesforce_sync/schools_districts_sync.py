"""
Schools and Districts Sync Workflow Module
=========================================

This module provides Prefect workflows for synchronizing schools and districts
from Salesforce to the local VMS database.

Key Features:
- District data synchronization from Salesforce Account objects
- School data synchronization from Salesforce Account objects
- Comprehensive error handling and retry logic
- Chunked processing for large datasets
- Detailed logging and metrics tracking

Workflows:
- schools_districts_sync_flow: Main workflow for schools and districts synchronization
- process_districts_batch: Task for processing district batches
- process_schools_batch: Task for processing school batches

Dependencies:
- Salesforce API integration
- School and District models
- Prefect workflow utilities
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from prefect import flow, task, get_run_logger
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.school_model import School
from models.district_model import District

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
def query_districts(sf_connection) -> Dict[str, Any]:
    """
    Query districts from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying districts from Salesforce...")
    
    try:
        # Query districts from Salesforce
        district_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account 
        WHERE Type = 'School District'
        """
        
        result = sf_connection.query_all(district_query)
        districts = result.get('records', [])
        
        logger.info(f"Retrieved {len(districts)} districts from Salesforce")
        
        return {
            'districts': districts,
            'total_count': len(districts),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_districts'})
        logger.error(f"Failed to query districts: {error_info['error_message']}")
        raise


@task(retries=3, retry_delay_seconds=60)
def query_schools(sf_connection) -> Dict[str, Any]:
    """
    Query schools from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying schools from Salesforce...")
    
    try:
        # Query schools from Salesforce
        school_query = """
        SELECT Id, Name, ParentId, Connector_Account_Name__c, School_Code_External_ID__c
        FROM Account 
        WHERE Type = 'School'
        """
        
        result = sf_connection.query_all(school_query)
        schools = result.get('records', [])
        
        logger.info(f"Retrieved {len(schools)} schools from Salesforce")
        
        return {
            'schools': schools,
            'total_count': len(schools),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_schools'})
        logger.error(f"Failed to query schools: {error_info['error_message']}")
        raise


@task(retries=2, retry_delay_seconds=30)
def process_districts_batch(districts_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of districts from Salesforce.
    
    Args:
        districts_data: Dictionary containing districts and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    districts = districts_data['districts']
    
    logger.info(f"Processing {len(districts)} districts...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in districts:
        try:
            # Check if district already exists
            existing_district = District.query.filter_by(salesforce_id=row['Id']).first()
            
            if existing_district:
                # Update existing district
                existing_district.name = row['Name']
                existing_district.district_code = row['School_Code_External_ID__c']
                logger.debug(f"Updated existing district: {row['Name']}")
            else:
                # Create new district
                new_district = District(
                    salesforce_id=row['Id'],
                    name=row['Name'],
                    district_code=row['School_Code_External_ID__c']
                )
                db_session.add(new_district)
                logger.debug(f"Created new district: {row['Name']}")
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing district {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} districts successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@task(retries=2, retry_delay_seconds=30)
def process_schools_batch(schools_data: Dict[str, Any], db_session) -> Dict[str, Any]:
    """
    Process a batch of schools from Salesforce.
    
    Args:
        schools_data: Dictionary containing schools and metadata
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    schools = schools_data['schools']
    
    logger.info(f"Processing {len(schools)} schools...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for row in schools:
        try:
            # Check if school already exists
            existing_school = School.query.filter_by(id=row['Id']).first()
            
            # Find the district using salesforce_id
            district = District.query.filter_by(salesforce_id=row['ParentId']).first()
            
            if existing_school:
                # Update existing school
                existing_school.name = row['Name']
                existing_school.district_id = district.id if district else None
                existing_school.salesforce_district_id = row['ParentId']
                existing_school.normalized_name = row['Connector_Account_Name__c']
                existing_school.school_code = row['School_Code_External_ID__c']
                logger.debug(f"Updated existing school: {row['Name']}")
            else:
                # Create new school
                new_school = School(
                    id=row['Id'],
                    name=row['Name'],
                    district_id=district.id if district else None,
                    salesforce_district_id=row['ParentId'],
                    normalized_name=row['Connector_Account_Name__c'],
                    school_code=row['School_Code_External_ID__c']
                )
                db_session.add(new_school)
                logger.debug(f"Created new school: {row['Name']}")
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing school {row.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"Processed {success_count} schools successfully, {error_count} errors")
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


@task(retries=2, retry_delay_seconds=30)
def update_school_levels(db_session) -> Dict[str, Any]:
    """
    Update school levels based on school names and patterns.
    
    Args:
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    logger.info("Updating school levels...")
    
    try:
        # Get all schools
        schools = School.query.all()
        
        updated_count = 0
        error_count = 0
        errors = []
        
        for school in schools:
            try:
                school_name_lower = school.name.lower()
                
                # Determine school level based on name patterns
                if any(keyword in school_name_lower for keyword in ['elementary', 'primary', 'grade school']):
                    school.level = 'Elementary'
                elif any(keyword in school_name_lower for keyword in ['middle', 'junior high']):
                    school.level = 'Middle'
                elif any(keyword in school_name_lower for keyword in ['high', 'senior']):
                    school.level = 'High'
                else:
                    school.level = 'Other'
                
                updated_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = f"Error updating school level for {school.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        logger.info(f"Updated {updated_count} school levels successfully, {error_count} errors")
        
        return {
            'success_count': updated_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Failed to update school levels: {str(e)}")
        return {
            'success_count': 0,
            'error_count': 1,
            'errors': [f"Failed to update school levels: {str(e)}"]
        }


@flow(name="schools-districts-sync")
def schools_districts_sync_flow() -> Dict[str, Any]:
    """
    Main workflow for synchronizing schools and districts from Salesforce.
    
    This workflow:
    1. Connects to Salesforce and database
    2. Queries districts and schools from Salesforce
    3. Processes districts in batches
    4. Processes schools in batches
    5. Updates school levels
    6. Commits all changes to database
    7. Returns comprehensive results
    
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    
    # Log workflow start
    start_time = datetime.now(timezone.utc)
    log_workflow_start("schools_districts_sync_flow", {})
    
    try:
        # Validate environment
        validate_environment()
        
        # Get connections
        sf_connection = salesforce_connection()
        db_session = database_connection()
        
        # Query data from Salesforce
        districts_data = query_districts(sf_connection)
        schools_data = query_schools(sf_connection)
        
        # Process districts first (schools depend on districts)
        districts_result = process_districts_batch(districts_data, db_session)
        
        # Commit district changes
        db_session.commit()
        
        # Process schools
        schools_result = process_schools_batch(schools_data, db_session)
        
        # Update school levels
        levels_result = update_school_levels(db_session)
        
        # Commit all changes
        db_session.commit()
        
        # Prepare results
        total_success = (
            districts_result['success_count'] + 
            schools_result['success_count'] + 
            levels_result['success_count']
        )
        total_errors = (
            districts_result['error_count'] + 
            schools_result['error_count'] + 
            levels_result['error_count']
        )
        all_errors = (
            districts_result['errors'] + 
            schools_result['errors'] + 
            levels_result['errors']
        )
        
        # Create error summary if there are errors
        error_summary = None
        if all_errors:
            error_summary = create_error_summary(all_errors)
        
        # Log workflow completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        log_workflow_completion("schools_districts_sync_flow", {
            'total_success': total_success,
            'total_errors': total_errors,
            'districts_success': districts_result['success_count'],
            'districts_errors': districts_result['error_count'],
            'schools_success': schools_result['success_count'],
            'schools_errors': schools_result['error_count'],
            'levels_success': levels_result['success_count'],
            'levels_errors': levels_result['error_count'],
            'duration_seconds': duration.total_seconds()
        })
        
        logger.info(f"Schools and districts sync completed: {total_success} successes, {total_errors} errors")
        
        return {
            'success': True,
            'message': f'Successfully processed {total_success} records with {total_errors} errors',
            'districts_success': districts_result['success_count'],
            'districts_errors': districts_result['error_count'],
            'schools_success': schools_result['success_count'],
            'schools_errors': schools_result['error_count'],
            'levels_success': levels_result['success_count'],
            'levels_errors': levels_result['error_count'],
            'errors': all_errors[:10],  # Limit error display
            'error_summary': error_summary,
            'duration': format_duration(duration)
        }
        
    except Exception as e:
        # Log workflow failure
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        error_context = create_error_context(e, {
            'workflow': 'schools_districts_sync_flow',
            'start_time': start_time,
            'duration': duration
        })
        
        logger.error(f"Schools and districts sync failed: {error_context['error_message']}")
        
        return {
            'success': False,
            'error': error_context['error_message'],
            'error_type': error_context['error_type'],
            'duration': format_duration(duration)
        } 
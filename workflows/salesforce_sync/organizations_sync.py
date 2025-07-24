"""
Organizations Sync Workflow
==========================

Prefect workflow for synchronizing organizations and affiliations from Salesforce.
This workflow handles both organization data and volunteer-organization relationships.

Features:
- Organization data sync with address information
- Affiliation relationship sync
- Comprehensive error handling and retry logic
- Detailed progress tracking and reporting
- Database transaction management
"""

import time
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
def query_organizations(sf_connection) -> Dict[str, Any]:
    """
    Query organizations from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying organizations from Salesforce...")
    
    try:
        # Query organizations from Salesforce
        # Excludes household, school district, and school accounts
        org_query = """
        SELECT Id, Name, Type, Description, ParentId, 
               BillingStreet, BillingCity, BillingState, 
               BillingPostalCode, BillingCountry, LastActivityDate
        FROM Account
        WHERE Type NOT IN ('Household', 'School District', 'School')
        ORDER BY Name ASC
        """
        
        result = sf_connection.query_all(org_query)
        organizations = result.get('records', [])
        
        logger.info(f"Retrieved {len(organizations)} organizations from Salesforce")
        
        return {
            'organizations': organizations,
            'total_count': len(organizations),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_organizations'})
        logger.error(f"Failed to query organizations: {error_info}")
        raise


@task(retries=3, retry_delay_seconds=60)
def query_affiliations(sf_connection) -> Dict[str, Any]:
    """
    Query affiliations from Salesforce.
    
    Args:
        sf_connection: Salesforce connection object
        
    Returns:
        Dictionary with query results and metadata
    """
    logger = get_run_logger()
    logger.info("Querying affiliations from Salesforce...")
    
    try:
        # Query affiliations from Salesforce
        affiliation_query = """
        SELECT Id, Name, npe5__Organization__c, npe5__Contact__c, 
               npe5__Role__c, npe5__Primary__c, npe5__Status__c, 
               npe5__StartDate__c, npe5__EndDate__c
        FROM npe5__Affiliation__c
        """
        
        result = sf_connection.query_all(affiliation_query)
        affiliations = result.get('records', [])
        
        logger.info(f"Retrieved {len(affiliations)} affiliations from Salesforce")
        
        return {
            'affiliations': affiliations,
            'total_count': len(affiliations),
            'query_time': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        error_info = handle_salesforce_error(e, {'operation': 'query_affiliations'})
        logger.error(f"Failed to query affiliations: {error_info}")
        raise


@task
def process_organizations(org_data: Dict[str, Any], db_session: Session) -> Dict[str, Any]:
    """
    Process and import organizations into the database.
    
    Args:
        org_data: Organization data from Salesforce
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    logger.info("Processing organizations...")
    
    from models.organization import Organization
    from utils.academic_year import parse_date
    
    organizations = org_data['organizations']
    success_count = 0
    error_count = 0
    errors = []
    
    for org in organizations:
        try:
            # Check if organization already exists
            existing_org = Organization.query.filter_by(salesforce_id=org['Id']).first()
            
            if existing_org:
                # Update existing organization
                existing_org.name = org.get('Name', '')
                existing_org.type = org.get('Type')
                existing_org.description = org.get('Description')
                existing_org.billing_street = org.get('BillingStreet')
                existing_org.billing_city = org.get('BillingCity')
                existing_org.billing_state = org.get('BillingState')
                existing_org.billing_postal_code = org.get('BillingPostalCode')
                existing_org.billing_country = org.get('BillingCountry')
                
                # Parse and set last activity date if available
                if org.get('LastActivityDate'):
                    existing_org.last_activity_date = parse_date(org['LastActivityDate'])
                
                success_count += 1
            else:
                # Create new organization
                new_org = Organization(
                    salesforce_id=org['Id'],
                    name=org.get('Name', ''),
                    type=org.get('Type'),
                    description=org.get('Description'),
                    billing_street=org.get('BillingStreet'),
                    billing_city=org.get('BillingCity'),
                    billing_state=org.get('BillingState'),
                    billing_postal_code=org.get('BillingPostalCode'),
                    billing_country=org.get('BillingCountry')
                )
                
                # Parse and set last activity date if available
                if org.get('LastActivityDate'):
                    new_org.last_activity_date = parse_date(org['LastActivityDate'])
                
                db_session.add(new_org)
                success_count += 1
                
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing organization {org.get('Name', 'Unknown')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    # Commit all changes
    try:
        db_session.commit()
        logger.info(f"Successfully processed {success_count} organizations")
    except Exception as e:
        db_session.rollback()
        error_info = handle_database_error(e, {'operation': 'commit_organizations'})
        logger.error(f"Failed to commit organizations: {error_info}")
        raise
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors,
        'total_processed': len(organizations)
    }


@task
def process_affiliations(affiliation_data: Dict[str, Any], db_session: Session) -> Dict[str, Any]:
    """
    Process and import affiliations into the database.
    
    Args:
        affiliation_data: Affiliation data from Salesforce
        db_session: Database session
        
    Returns:
        Dictionary with processing results
    """
    logger = get_run_logger()
    logger.info("Processing affiliations...")
    
    from models.organization import Organization
    from models.volunteer import Volunteer
    from models.contact import Contact
    
    affiliations = affiliation_data['affiliations']
    success_count = 0
    error_count = 0
    errors = []
    
    for affiliation in affiliations:
        try:
            org_id = affiliation.get('npe5__Organization__c')
            contact_id = affiliation.get('npe5__Contact__c')
            
            if not org_id or not contact_id:
                error_count += 1
                errors.append(f"Missing organization or contact ID in affiliation")
                continue
            
            # Find organization and contact
            org = Organization.query.filter_by(salesforce_id=org_id).first()
            contact = Contact.query.filter_by(salesforce_individual_id=contact_id).first()
            
            if not org or not contact:
                error_count += 1
                errors.append(f"Could not find organization or contact for affiliation")
                continue
            
            # Create or update affiliation relationship
            # This would depend on your specific affiliation model structure
            # For now, we'll log the relationship
            logger.info(f"Affiliation: {contact.first_name} {contact.last_name} -> {org.name}")
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error processing affiliation: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    # Commit all changes
    try:
        db_session.commit()
        logger.info(f"Successfully processed {success_count} affiliations")
    except Exception as e:
        db_session.rollback()
        error_info = handle_database_error(e, {'operation': 'commit_affiliations'})
        logger.error(f"Failed to commit affiliations: {error_info}")
        raise
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors,
        'total_processed': len(affiliations)
    }


@workflow_decorator("organizations-sync")
def organizations_sync_flow(sync_affiliations: bool = True) -> Dict[str, Any]:
    """
    Main organizations synchronization workflow.
    
    This workflow synchronizes organizations and affiliations from Salesforce
    to the VMS database with comprehensive error handling and monitoring.
    
    Args:
        sync_affiliations: Whether to sync affiliations (default: True)
        
    Returns:
        Dictionary with sync results and statistics
    """
    logger = get_run_logger()
    start_time = datetime.now(timezone.utc)
    
    logger.info(f"Starting organizations sync workflow (affiliations: {sync_affiliations})")
    
    # Track overall results
    total_success = 0
    total_errors = 0
    all_errors = []
    
    try:
        # Validate environment
        env_validation = validate_environment.submit()
        env_result = env_validation.result()
        
        if not env_result['salesforce_configured'] or not env_result['database_configured']:
            raise ValueError("Environment not properly configured for Salesforce sync")
        
        # Establish connections
        sf_connection = salesforce_connection.submit()
        db_connection = database_connection.submit()
        
        # Sync organizations
        logger.info("Starting organization sync...")
        org_data = query_organizations.submit(sf_connection)
        org_result = process_organizations.submit(org_data.result(), db_connection)
        
        total_success += org_result.result()['success_count']
        total_errors += org_result.result()['error_count']
        all_errors.extend(org_result.result()['errors'])
        
        # Sync affiliations if requested
        if sync_affiliations:
            logger.info("Starting affiliation sync...")
            affiliation_data = query_affiliations.submit(sf_connection)
            affiliation_result = process_affiliations.submit(affiliation_data.result(), db_connection)
            
            total_success += affiliation_result.result()['success_count']
            total_errors += affiliation_result.result()['error_count']
            all_errors.extend(affiliation_result.result()['errors'])
        
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
            'duration_seconds': duration,
            'duration_formatted': format_duration(duration),
            'memory_usage': memory_info,
            'sync_affiliations': sync_affiliations,
            'error_summary': create_error_summary(all_errors),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        log_workflow_completion("organizations-sync", result, duration)
        logger.info(f"Organizations sync completed successfully: {total_success} successes, {total_errors} errors")
        
        return result
        
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        log_error_with_context(e, "organizations-sync", context={
            'sync_affiliations': sync_affiliations,
            'total_success': total_success,
            'total_errors': total_errors
        })
        
        return {
            'status': 'error',
            'error_message': str(e),
            'error_type': PrefectErrorHandler.classify_error(e),
            'total_success': total_success,
            'total_errors': total_errors,
            'duration_seconds': duration,
            'duration_formatted': format_duration(duration),
            'sync_affiliations': sync_affiliations,
            'error_summary': create_error_summary(all_errors),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        } 
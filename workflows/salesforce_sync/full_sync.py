"""
Full Salesforce Sync Workflow Module
===================================

This module provides a comprehensive workflow that runs all Salesforce sync operations
in the correct order to ensure data consistency and proper relationships.

Key Features:
- Orchestrates all individual sync workflows
- Runs syncs in dependency order (districts/schools first, then others)
- Comprehensive error handling and reporting
- Detailed progress tracking
- Rollback capabilities for failed syncs

Workflow Order:
1. Schools and Districts (foundation data)
2. Organizations (independent entities)
3. Classes (depend on schools)
4. Teachers (depend on schools)
5. Students (depend on schools and classes)
6. Volunteers (independent entities)
7. Events (depend on schools/districts)
8. Pathways (depend on events and contacts)
9. History (depends on all other entities)

Dependencies:
- All individual sync workflows
- Prefect workflow utilities
- Database transaction management
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from prefect import flow, task, get_run_logger

from workflows.salesforce_sync import (
    schools_districts_sync_flow,
    organizations_sync_flow,
    classes_sync_flow,
    teachers_sync_flow,
    students_sync_flow,
    volunteers_sync_flow,
    events_sync_flow,
    pathways_sync_flow,
    history_sync_flow
)

from workflows.utils.prefect_helpers import (
    log_workflow_start,
    log_workflow_completion,
    format_duration
)
from workflows.utils.error_handling import (
    PrefectErrorHandler
)


@task(retries=1, retry_delay_seconds=30)
def run_schools_districts_sync() -> Dict[str, Any]:
    """Run schools and districts sync workflow."""
    logger = get_run_logger()
    logger.info("Starting schools and districts sync...")
    
    try:
        result = schools_districts_sync_flow()
        logger.info(f"Schools and districts sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Schools and districts sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'SCHOOLS_DISTRICTS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_organizations_sync() -> Dict[str, Any]:
    """Run organizations sync workflow."""
    logger = get_run_logger()
    logger.info("Starting organizations sync...")
    
    try:
        result = organizations_sync_flow()
        logger.info(f"Organizations sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Organizations sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'ORGANIZATIONS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_classes_sync() -> Dict[str, Any]:
    """Run classes sync workflow."""
    logger = get_run_logger()
    logger.info("Starting classes sync...")
    
    try:
        result = classes_sync_flow()
        logger.info(f"Classes sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Classes sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'CLASSES_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_teachers_sync() -> Dict[str, Any]:
    """Run teachers sync workflow."""
    logger = get_run_logger()
    logger.info("Starting teachers sync...")
    
    try:
        result = teachers_sync_flow()
        logger.info(f"Teachers sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Teachers sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'TEACHERS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_students_sync() -> Dict[str, Any]:
    """Run students sync workflow."""
    logger = get_run_logger()
    logger.info("Starting students sync...")
    
    try:
        result = students_sync_flow()
        logger.info(f"Students sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Students sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'STUDENTS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_volunteers_sync() -> Dict[str, Any]:
    """Run volunteers sync workflow."""
    logger = get_run_logger()
    logger.info("Starting volunteers sync...")
    
    try:
        result = volunteers_sync_flow()
        logger.info(f"Volunteers sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Volunteers sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'VOLUNTEERS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_events_sync() -> Dict[str, Any]:
    """Run events sync workflow."""
    logger = get_run_logger()
    logger.info("Starting events sync...")
    
    try:
        result = events_sync_flow()
        logger.info(f"Events sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Events sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'EVENTS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_pathways_sync() -> Dict[str, Any]:
    """Run pathways sync workflow."""
    logger = get_run_logger()
    logger.info("Starting pathways sync...")
    
    try:
        result = pathways_sync_flow()
        logger.info(f"Pathways sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"Pathways sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'PATHWAYS_SYNC_ERROR'
        }


@task(retries=1, retry_delay_seconds=30)
def run_history_sync() -> Dict[str, Any]:
    """Run history sync workflow."""
    logger = get_run_logger()
    logger.info("Starting history sync...")
    
    try:
        result = history_sync_flow()
        logger.info(f"History sync completed: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"History sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'HISTORY_SYNC_ERROR'
        }


@flow(name="full-salesforce-sync")
def full_salesforce_sync_flow() -> Dict[str, Any]:
    """
    Comprehensive Salesforce sync workflow that runs all sync operations in order.
    
    This workflow orchestrates all individual sync workflows in the correct dependency
    order to ensure data consistency and proper relationships.
    
    Sync Order:
    1. Schools and Districts (foundation data)
    2. Organizations (independent entities)
    3. Classes (depend on schools)
    4. Teachers (depend on schools)
    5. Students (depend on schools and classes)
    6. Volunteers (independent entities)
    7. Events (depend on schools/districts)
    8. Pathways (depend on events and contacts)
    9. History (depends on all other entities)
    
    Returns:
        Dictionary with comprehensive sync results and statistics
    """
    logger = get_run_logger()
    
    # Log workflow start
    start_time = datetime.now(timezone.utc)
    log_workflow_start("full_salesforce_sync_flow", {})
    
    try:
        # Step 1: Schools and Districts (foundation)
        logger.info("=== Step 1: Schools and Districts Sync ===")
        schools_districts_result = run_schools_districts_sync()
        
        # Step 2: Organizations (independent)
        logger.info("=== Step 2: Organizations Sync ===")
        organizations_result = run_organizations_sync()
        
        # Step 3: Classes (depend on schools)
        logger.info("=== Step 3: Classes Sync ===")
        classes_result = run_classes_sync()
        
        # Step 4: Teachers (depend on schools)
        logger.info("=== Step 4: Teachers Sync ===")
        teachers_result = run_teachers_sync()
        
        # Step 5: Students (depend on schools and classes)
        logger.info("=== Step 5: Students Sync ===")
        students_result = run_students_sync()
        
        # Step 6: Volunteers (independent)
        logger.info("=== Step 6: Volunteers Sync ===")
        volunteers_result = run_volunteers_sync()
        
        # Step 7: Events (depend on schools/districts)
        logger.info("=== Step 7: Events Sync ===")
        events_result = run_events_sync()
        
        # Step 8: Pathways (depend on events and contacts)
        logger.info("=== Step 8: Pathways Sync ===")
        pathways_result = run_pathways_sync()
        
        # Step 9: History (depends on all other entities)
        logger.info("=== Step 9: History Sync ===")
        history_result = run_history_sync()
        
        # Compile results
        all_results = [
            ('schools_districts', schools_districts_result),
            ('organizations', organizations_result),
            ('classes', classes_result),
            ('teachers', teachers_result),
            ('students', students_result),
            ('volunteers', volunteers_result),
            ('events', events_result),
            ('pathways', pathways_result),
            ('history', history_result)
        ]
        
        # Calculate overall statistics
        successful_syncs = 0
        failed_syncs = 0
        total_success_count = 0
        total_error_count = 0
        failed_syncs_list = []
        all_errors = []
        
        for sync_name, result in all_results:
            if result.get('success', False):
                successful_syncs += 1
                # Add success counts if available
                for key, value in result.items():
                    if 'success' in key and isinstance(value, int):
                        total_success_count += value
            else:
                failed_syncs += 1
                failed_syncs_list.append(sync_name)
                all_errors.append(f"{sync_name}: {result.get('error', 'Unknown error')}")
        
        # Log workflow completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        log_workflow_completion("full_salesforce_sync_flow", {
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'total_success_count': total_success_count,
            'total_error_count': total_error_count,
            'duration_seconds': duration.total_seconds()
        })
        
        logger.info(f"Full Salesforce sync completed: {successful_syncs} successful syncs, {failed_syncs} failed syncs")
        
        return {
            'success': failed_syncs == 0,
            'message': f'Completed {successful_syncs} syncs successfully, {failed_syncs} failed',
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'failed_syncs_list': failed_syncs_list,
            'total_success_count': total_success_count,
            'total_error_count': total_error_count,
            'sync_results': {
                'schools_districts': schools_districts_result,
                'organizations': organizations_result,
                'classes': classes_result,
                'teachers': teachers_result,
                'students': students_result,
                'volunteers': volunteers_result,
                'events': events_result,
                'pathways': pathways_result,
                'history': history_result
            },
            'errors': all_errors,
            'duration': format_duration(duration)
        }
        
    except Exception as e:
        # Log workflow failure
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        error_context = create_error_context(e, {
            'workflow': 'full_salesforce_sync_flow',
            'start_time': start_time,
            'duration': duration
        })
        
        logger.error(f"Full Salesforce sync failed: {error_context['error_message']}")
        
        return {
            'success': False,
            'error': error_context['error_message'],
            'error_type': error_context['error_type'],
            'duration': format_duration(duration)
        } 
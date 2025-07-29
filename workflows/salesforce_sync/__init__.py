"""
Salesforce Sync Workflows Package
================================

This package contains all Prefect workflows for synchronizing data from Salesforce
to the local VMS database.

Available Workflows:
- organizations_sync_flow: Synchronize organizations and affiliations
- volunteers_sync_flow: Synchronize volunteer data with chunked processing
- students_sync_flow: Synchronize student data with parent relationships
- teachers_sync_flow: Synchronize teacher data with school relationships
- events_sync_flow: Synchronize events and participants
- pathways_sync_flow: Synchronize pathways and participants
- history_sync_flow: Synchronize historical activity data
- schools_districts_sync_flow: Synchronize schools and districts
- classes_sync_flow: Synchronize class data
- full_salesforce_sync_flow: Run all sync workflows in correct order

Each workflow includes:
- Comprehensive error handling and retry logic
- Detailed logging and metrics tracking
- Chunked processing for large datasets
- Database transaction management
- Performance monitoring

Usage:
    from workflows.salesforce_sync import organizations_sync_flow
    result = organizations_sync_flow()
    
    # Or run all syncs at once:
    from workflows.salesforce_sync import full_salesforce_sync_flow
    result = full_salesforce_sync_flow()
"""

from .organizations_sync import organizations_sync_flow
from .volunteers_sync import volunteers_sync_flow
from .students_sync import students_sync_flow
from .teachers_sync import teachers_sync_flow
from .events_sync import events_sync_flow
from .pathways_sync import pathways_sync_flow
from .history_sync import history_sync_flow
from .schools_districts_sync import schools_districts_sync_flow
from .classes_sync import classes_sync_flow
from .full_sync import full_salesforce_sync_flow

__all__ = [
    'organizations_sync_flow',
    'volunteers_sync_flow', 
    'students_sync_flow',
    'teachers_sync_flow',
    'events_sync_flow',
    'pathways_sync_flow',
    'history_sync_flow',
    'schools_districts_sync_flow',
    'classes_sync_flow',
    'full_salesforce_sync_flow'
] 
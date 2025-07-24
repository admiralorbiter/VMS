"""
Salesforce Sync Workflows
========================

Prefect workflows for synchronizing data between Salesforce and VMS.
This module provides comprehensive data synchronization with error handling,
retry logic, and detailed monitoring.

Workflows:
- organizations_sync: Sync organizations and affiliations
- volunteers_sync: Sync volunteer data with chunked processing
- students_sync: Sync student data with large dataset handling
- teachers_sync: Sync teacher data
- events_sync: Sync events and sessions
- pathways_sync: Sync pathways and participants
- classes_sync: Sync class data
- schools_sync: Sync schools and districts
- history_sync: Sync historical activity data

Features:
- Chunked processing for large datasets
- Comprehensive error handling and retry logic
- Detailed progress tracking and reporting
- Database transaction management
- Performance monitoring and metrics
"""

from .organizations_sync import organizations_sync_flow
from .volunteers_sync import volunteers_sync_flow
from .students_sync import students_sync_flow
from .teachers_sync import teachers_sync_flow
from .events_sync import events_sync_flow
from .pathways_sync import pathways_sync_flow
from .classes_sync import classes_sync_flow
from .schools_sync import schools_sync_flow
from .history_sync import history_sync_flow

__all__ = [
    'organizations_sync_flow',
    'volunteers_sync_flow', 
    'students_sync_flow',
    'teachers_sync_flow',
    'events_sync_flow',
    'pathways_sync_flow',
    'classes_sync_flow',
    'schools_sync_flow',
    'history_sync_flow'
] 
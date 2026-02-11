"""
Salesforce Row Processors
=========================

This subpackage contains the business logic for processing individual
Salesforce records during import operations. By extracting this logic
from route files, we achieve:

1. Cleaner route files that only handle HTTP request/response
2. Reusable processing logic that can be tested in isolation
3. Consistent patterns across all import types

Usage:
    from services.salesforce.processors.event import process_event_row

    for row in salesforce_records:
        success, error = process_event_row(row, caches)
"""

# Import processors for convenient access
from services.salesforce.processors.event import (
    fix_missing_participation_records,
    process_event_row,
    process_participation_row,
    process_student_participation_row,
)

__all__ = [
    "process_event_row",
    "process_participation_row",
    "process_student_participation_row",
    "fix_missing_participation_records",
]

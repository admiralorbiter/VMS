"""
Delta Sync Service
==================

This module provides utilities for implementing delta/incremental sync
with Salesforce. Delta sync only fetches records modified since the last
successful sync, significantly reducing import time for routine syncs.

Key Features:
- Watermark-based delta tracking using Salesforce LastModifiedDate
- Automatic fallback to full sync if no previous watermark exists
- Integration with SyncLog for tracking sync history
- Helper functions for building SOQL queries with date filters

Usage:
    from services.salesforce import DeltaSyncHelper

    # In your import route:
    helper = DeltaSyncHelper('events_and_participants')

    # Check if delta mode requested
    if request.args.get('delta', 'false').lower() == 'true':
        watermark = helper.get_watermark()
        if watermark:
            query += helper.build_date_filter(watermark)

    # After successful sync:
    helper.record_watermark(sync_log, datetime.now(timezone.utc))
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from models.sync_log import SyncLog, SyncStatus

logger = logging.getLogger(__name__)


class DeltaSyncHelper:
    """Helper class for implementing delta sync in Salesforce imports."""

    # Default lookback buffer (1 hour) to account for clock drift and in-flight changes
    DEFAULT_BUFFER_HOURS = 1

    def __init__(self, sync_type: str, buffer_hours: int = None):
        """
        Initialize the delta sync helper for a specific sync type.

        Args:
            sync_type: The type of sync (e.g., 'volunteers', 'events_and_participants')
            buffer_hours: Hours to subtract from watermark for safety (default: 1)
        """
        self.sync_type = sync_type
        self.buffer_hours = (
            buffer_hours if buffer_hours is not None else self.DEFAULT_BUFFER_HOURS
        )

    # Wider buffer applied after a failed sync to catch records that fell in the gap
    FAILED_SYNC_BUFFER_HOURS = 48

    def get_watermark(self) -> Optional[datetime]:
        """
        Get the watermark timestamp for delta sync with appropriate lookback buffer.

        Uses recovery_buffer_hours from the most recent SyncLog entry to determine
        how far back to look. Normal runs: 1 hour. Post-failure: 48 hours. (TD-055)
        """
        watermark, buffer_hours = SyncLog.get_watermark_with_buffer(self.sync_type)
        if not watermark:
            return None

        if buffer_hours != self.DEFAULT_BUFFER_HOURS:
            logger.warning(
                "Recovery mode: applying %d-hour lookback buffer for %s delta sync",
                buffer_hours,
                self.sync_type,
            )

        return watermark - timedelta(hours=buffer_hours)

    def format_watermark_for_soql(self, watermark: datetime) -> str:
        """
        Format a datetime as a Salesforce SOQL-compatible datetime string.

        Args:
            watermark: The datetime to format

        Returns:
            str: ISO format datetime string for SOQL (e.g., '2024-01-15T10:30:00Z')
        """
        # Salesforce expects UTC in ISO format
        if watermark.tzinfo is None:
            # Assume UTC if no timezone
            watermark = watermark.replace(tzinfo=timezone.utc)
        return watermark.strftime("%Y-%m-%dT%H:%M:%SZ")

    def build_date_filter(
        self, watermark: datetime, field: str = "LastModifiedDate"
    ) -> str:
        """
        Build a SOQL WHERE clause fragment for delta sync.

        Args:
            watermark: The datetime to filter from
            field: The Salesforce field to filter on (default: LastModifiedDate)

        Returns:
            str: A SOQL fragment like " AND LastModifiedDate > 2024-01-15T10:30:00Z"
        """
        formatted = self.format_watermark_for_soql(watermark)
        return f" AND {field} > {formatted}"

    def should_use_delta(self, request_args: dict) -> bool:
        """
        Determine if delta sync should be used based on request parameters.

        Args:
            request_args: The Flask request.args dict

        Returns:
            bool: True if delta sync should be used
        """
        delta_param = request_args.get("delta", "false").lower()
        return delta_param in ("true", "1", "yes")

    def get_delta_info(self, request_args: dict) -> dict:
        """
        Get comprehensive delta sync information for logging and response.

        Args:
            request_args: The Flask request.args dict

        Returns:
            dict: Delta sync information including mode, watermark, etc.
        """
        is_delta = self.should_use_delta(request_args)
        watermark = self.get_watermark() if is_delta else None

        # If delta requested but no watermark, fall back to full sync
        actual_delta = is_delta and watermark is not None

        return {
            "requested_delta": is_delta,
            "actual_delta": actual_delta,
            "watermark": watermark,
            "watermark_formatted": (
                self.format_watermark_for_soql(watermark) if watermark else None
            ),
            "fallback_to_full": is_delta and not watermark,
        }


def add_delta_filter_to_query(
    base_query: str,
    sync_type: str,
    request_args: dict,
    date_field: str = "LastModifiedDate",
) -> tuple[str, dict]:
    """
    Convenience function to add delta filtering to a SOQL query.

    This is a simpler interface for routes that want minimal changes.

    Args:
        base_query: The base SOQL query string
        sync_type: The sync type (e.g., 'volunteers')
        request_args: The Flask request.args dict
        date_field: The field to filter on (default: LastModifiedDate)

    Returns:
        tuple: (modified_query, delta_info_dict)

    Example:
        query = "SELECT Id, Name FROM Contact WHERE Type = 'Volunteer'"
        query, delta_info = add_delta_filter_to_query(query, 'volunteers', request.args)
        # query now includes LastModifiedDate filter if delta mode
    """
    helper = DeltaSyncHelper(sync_type)
    delta_info = helper.get_delta_info(request_args)

    modified_query = base_query
    if delta_info["actual_delta"] and delta_info["watermark"]:
        # Determine where to insert the filter
        # If query has ORDER BY, insert before it
        query_upper = base_query.upper()
        if "ORDER BY" in query_upper:
            order_idx = query_upper.index("ORDER BY")
            modified_query = (
                base_query[:order_idx]
                + helper.build_date_filter(delta_info["watermark"], date_field)
                + " "
                + base_query[order_idx:]
            )
        else:
            # Just append to the end
            modified_query = base_query + helper.build_date_filter(
                delta_info["watermark"], date_field
            )

    return modified_query, delta_info


def create_sync_log_with_watermark(
    sync_type: str,
    started_at: datetime,
    status: str,
    records_processed: int = 0,
    records_failed: int = 0,
    records_skipped: int = 0,
    error_message: str = None,
    error_details: str = None,
    is_delta: bool = False,
) -> SyncLog:
    """
    Create a SyncLog entry with watermark for future delta syncs.

    This convenience function creates a sync log and automatically sets
    the watermark to the current time for use in future delta syncs.

    Args:
        sync_type: The type of sync
        started_at: When the sync started
        status: The sync status ('success', 'failed', 'partial')
        records_processed: Number of records processed successfully
        records_failed: Number of records that failed
        records_skipped: Number of records skipped
        error_message: Optional error message
        error_details: Optional JSON error details
        is_delta: Whether this was a delta sync

    Returns:
        SyncLog: The created sync log (not yet committed to DB)
    """
    from models import db

    sync_log = SyncLog(
        sync_type=sync_type,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        status=status,
        records_processed=records_processed,
        records_failed=records_failed,
        records_skipped=records_skipped,
        error_message=error_message,
        error_details=error_details,
        is_delta_sync=is_delta,
        # Always advance watermark — failed runs get wide recovery buffer (TD-055)
        last_sync_watermark=datetime.now(timezone.utc),
        recovery_buffer_hours=48 if status == SyncStatus.FAILED.value else 1,
    )

    return sync_log

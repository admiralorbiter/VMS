"""
Salesforce Import Dashboard Routes
==================================

Provides a dedicated dashboard for managing all Salesforce data imports,
separated from the main admin page for better organization.

Routes:
- GET /admin/salesforce - Main import dashboard
- GET /admin/salesforce/sync-history - Return sync log history (JSON)
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from models import db
from models.sync_log import SyncLog
from routes.utils import admin_required

sf_dashboard_bp = Blueprint("sf_dashboard", __name__, url_prefix="/admin/salesforce")


@sf_dashboard_bp.route("/")
@login_required
@admin_required
def import_dashboard():
    """
    Render the Salesforce import dashboard.

    Displays all available import types organized by frequency,
    with delta sync controls and progress tracking.
    """
    # Get last sync info for each import type
    sync_types = [
        "organizations",
        "volunteers",
        "affiliations",
        "events",
        "history",
        "schools",
        "classes",
        "teachers",
        "students",
        "student_participations",
        "unaffiliated_events",
    ]

    last_syncs = {}
    for sync_type in sync_types:
        last_sync = (
            SyncLog.query.filter_by(sync_type=sync_type)
            .order_by(SyncLog.completed_at.desc())
            .first()
        )
        last_syncs[sync_type] = last_sync

    return render_template("salesforce/import_dashboard.html", last_syncs=last_syncs)


@sf_dashboard_bp.route("/sync-history")
@login_required
@admin_required
def sync_history():
    """
    Return recent sync log history as JSON.

    Returns the 50 most recent sync operations across all types.
    """
    logs = SyncLog.query.order_by(SyncLog.completed_at.desc()).limit(50).all()

    return jsonify(
        {
            "success": True,
            "logs": [
                {
                    "id": log.id,
                    "sync_type": log.sync_type,
                    "started_at": (
                        log.started_at.isoformat() if log.started_at else None
                    ),
                    "completed_at": (
                        log.completed_at.isoformat() if log.completed_at else None
                    ),
                    "status": log.status,
                    "records_processed": log.records_processed,
                    "records_failed": log.records_failed,
                    "is_delta_sync": log.is_delta_sync,
                }
                for log in logs
            ],
        }
    )


@sf_dashboard_bp.route("/health-metrics")
@login_required
@admin_required
def health_metrics():
    """
    Return health metrics for the Salesforce sync dashboard.

    Provides:
    - 7-day error rate trend by sync type
    - Average duration by sync type
    - Stale sync warnings (no sync in 24+ hours)
    """
    from datetime import timedelta

    # Get date range for 7 days (use utcnow for consistency with naive DB timestamps)
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    sync_types = [
        "organizations",
        "volunteers",
        "affiliations",
        "events",
        "history",
        "schools",
        "teachers",
        "students",
    ]

    # Calculate metrics for each sync type
    metrics = {}
    stale_syncs = []

    for sync_type in sync_types:
        # Get logs for this sync type in the last 7 days
        logs = (
            SyncLog.query.filter(
                SyncLog.sync_type == sync_type,
                SyncLog.completed_at >= seven_days_ago,
            )
            .order_by(SyncLog.completed_at.asc())
            .all()
        )

        total_runs = len(logs)
        failed_runs = sum(1 for log in logs if log.status == "failed")
        partial_runs = sum(1 for log in logs if log.status == "partial")

        # Calculate average duration
        durations = [log.duration_seconds for log in logs if log.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else None

        # Calculate total records processed and failed
        total_processed = sum(log.records_processed or 0 for log in logs)
        total_failed = sum(log.records_failed or 0 for log in logs)

        # Error rate
        error_rate = (failed_runs / total_runs * 100) if total_runs > 0 else None
        record_error_rate = (
            (total_failed / (total_processed + total_failed) * 100)
            if (total_processed + total_failed) > 0
            else None
        )

        metrics[sync_type] = {
            "total_runs": total_runs,
            "failed_runs": failed_runs,
            "partial_runs": partial_runs,
            "error_rate": round(error_rate, 1) if error_rate is not None else None,
            "record_error_rate": (
                round(record_error_rate, 2) if record_error_rate is not None else None
            ),
            "avg_duration_seconds": (
                round(avg_duration, 1) if avg_duration is not None else None
            ),
            "total_processed": total_processed,
            "total_failed": total_failed,
        }

        # Check for stale syncs (no successful sync in 24 hours)
        last_sync = (
            SyncLog.query.filter(
                SyncLog.sync_type == sync_type,
                SyncLog.status.in_(["success", "partial"]),
            )
            .order_by(SyncLog.completed_at.desc())
            .first()
        )

        if last_sync and last_sync.completed_at:
            # Handle both timezone-aware and naive datetimes
            completed_at = last_sync.completed_at
            if completed_at.tzinfo is not None:
                completed_at = completed_at.replace(tzinfo=None)
            hours_since = (now - completed_at).total_seconds() / 3600
            if hours_since > 24:
                stale_syncs.append(
                    {
                        "sync_type": sync_type,
                        "hours_since": round(hours_since, 1),
                        "last_sync": last_sync.completed_at.isoformat(),
                    }
                )
        else:
            # Never synced
            stale_syncs.append(
                {
                    "sync_type": sync_type,
                    "hours_since": None,
                    "last_sync": None,
                }
            )

    # Calculate daily trend for chart (aggregate across all types)
    daily_trend = []
    for i in range(7):
        day_start = now - timedelta(days=6 - i)
        day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_logs = SyncLog.query.filter(
            SyncLog.completed_at >= day_start,
            SyncLog.completed_at < day_end,
        ).all()

        day_total = len(day_logs)
        day_failed = sum(1 for log in day_logs if log.status == "failed")

        daily_trend.append(
            {
                "date": day_start.strftime("%Y-%m-%d"),
                "day_name": day_start.strftime("%a"),
                "total_runs": day_total,
                "failed_runs": day_failed,
                "success_rate": (
                    round((day_total - day_failed) / day_total * 100, 1)
                    if day_total > 0
                    else 100
                ),
            }
        )

    return jsonify(
        {
            "success": True,
            "metrics": metrics,
            "stale_syncs": stale_syncs,
            "daily_trend": daily_trend,
        }
    )

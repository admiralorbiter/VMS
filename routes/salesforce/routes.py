"""
Salesforce Import Dashboard Routes
==================================

Provides a dedicated dashboard for managing all Salesforce data imports,
separated from the main admin page for better organization.

Routes:
- GET /admin/salesforce - Main import dashboard
- GET /admin/salesforce/sync-history - Return sync log history (JSON)
"""

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

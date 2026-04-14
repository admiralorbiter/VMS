"""
Cache Management Routes
======================

This module provides web-based cache management functionality for administrators.
It allows manual cache refresh, status monitoring, and scheduler control through
the web interface.

Key Features:
- Manual cache refresh for all or specific cache types
- Real-time cache status monitoring
- Scheduler start/stop controls
- Cache statistics and health monitoring
- Admin-only access controls

Routes:
- /management/cache/status - View cache status and statistics
- /management/cache/refresh - Manual cache refresh
- /management/cache/scheduler/start - Start the scheduler
- /management/cache/scheduler/stop - Stop the scheduler
"""

from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from routes.decorators import admin_required, handle_route_errors
from utils.cache_refresh_scheduler import (
    get_cache_status,
    refresh_all_caches,
    refresh_specific_cache,
    start_cache_refresh_scheduler,
    stop_cache_refresh_scheduler,
)

# Create blueprint
cache_management_bp = Blueprint("cache_management", __name__)


@cache_management_bp.route("/management/cache/status")
@login_required
@admin_required
def cache_status():
    """Display cache status and statistics."""
    status = get_cache_status()

    # Format the status data for display
    formatted_status = {
        "is_running": status["is_running"],
        "refresh_interval_hours": status["refresh_interval_hours"],
        "last_refresh": status["last_refresh"],
        "stats": status["stats"],
    }

    return render_template(
        "management/cache_status.html", status=formatted_status, title="Cache Status"
    )


@cache_management_bp.route("/management/cache/refresh", methods=["GET", "POST"])
@login_required
@admin_required
@handle_route_errors
def cache_refresh():
    """Manual cache refresh interface."""
    if request.method == "POST":
        cache_type = request.form.get("cache_type", "all")

        if cache_type == "all":
            refresh_all_caches()
            flash("All caches refreshed successfully!", "success")
        else:
            refresh_specific_cache(cache_type)
            flash(f"{cache_type.title()} caches refreshed successfully!", "success")

        return redirect(url_for("cache_management.cache_status"))

    # GET request - show refresh form
    cache_types = [
        ("all", "All Caches"),
        ("district", "District Reports"),
        ("organization", "Organization Reports"),
        ("virtual_session", "Virtual Session Reports"),
        ("volunteer", "Volunteer Reports"),
        ("recruitment", "Recruitment Reports"),
    ]

    return render_template(
        "management/cache_refresh.html", cache_types=cache_types, title="Refresh Caches"
    )


@cache_management_bp.route("/management/cache/scheduler/start", methods=["POST"])
@login_required
@admin_required
@handle_route_errors
def start_scheduler():
    """Start the cache refresh scheduler."""
    start_cache_refresh_scheduler()
    return jsonify(
        {"success": True, "message": "Cache refresh scheduler started successfully"}
    )


@cache_management_bp.route("/management/cache/scheduler/stop", methods=["POST"])
@login_required
@admin_required
@handle_route_errors
def stop_scheduler():
    """Stop the cache refresh scheduler."""
    stop_cache_refresh_scheduler()
    return jsonify(
        {"success": True, "message": "Cache refresh scheduler stopped successfully"}
    )


@cache_management_bp.route("/management/cache/api/status")
@login_required
@admin_required
@handle_route_errors
def api_cache_status():
    """API endpoint for cache status (for AJAX updates)."""
    status = get_cache_status()
    return jsonify({"success": True, "data": status})


@cache_management_bp.route("/management/cache/api/refresh", methods=["POST"])
@login_required
@admin_required
@handle_route_errors
def api_cache_refresh():
    """API endpoint for cache refresh (for AJAX requests)."""
    data = request.get_json()
    cache_type = data.get("cache_type", "all")

    if cache_type == "all":
        refresh_all_caches()
        message = "All caches refreshed successfully"
    else:
        refresh_specific_cache(cache_type)
        message = f"{cache_type.title()} caches refreshed successfully"

    return jsonify({"success": True, "message": message})


def load_routes(bp):
    """Load cache management routes into the provided blueprint."""
    # Register routes with the main blueprint
    bp.add_url_rule("/management/cache/status", "cache_status", cache_status)
    bp.add_url_rule(
        "/management/cache/refresh",
        "cache_refresh",
        cache_refresh,
        methods=["GET", "POST"],
    )
    bp.add_url_rule(
        "/management/cache/scheduler/start",
        "start_scheduler",
        start_scheduler,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/management/cache/scheduler/stop",
        "stop_scheduler",
        stop_scheduler,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/management/cache/api/status", "api_cache_status", api_cache_status
    )
    bp.add_url_rule(
        "/management/cache/api/refresh",
        "api_cache_refresh",
        api_cache_refresh,
        methods=["POST"],
    )

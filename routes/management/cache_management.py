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

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps

from utils.cache_refresh_scheduler import (
    refresh_all_caches,
    refresh_specific_cache,
    get_cache_status,
    start_cache_refresh_scheduler,
    stop_cache_refresh_scheduler,
)

# Create blueprint
cache_management_bp = Blueprint("cache_management", __name__)


def admin_required(f):
    """Decorator to require admin privileges for cache management."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash("Admin privileges required for cache management.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@cache_management_bp.route("/management/cache/status")
@login_required
@admin_required
def cache_status():
    """Display cache status and statistics."""
    status = get_cache_status()
    
    # Format the status data for display
    formatted_status = {
        'is_running': status['is_running'],
        'refresh_interval_hours': status['refresh_interval_hours'],
        'last_refresh': status['last_refresh'],
        'stats': status['stats'],
    }
    
    return render_template(
        "management/cache_status.html",
        status=formatted_status,
        title="Cache Status"
    )


@cache_management_bp.route("/management/cache/refresh", methods=["GET", "POST"])
@login_required
@admin_required
def cache_refresh():
    """Manual cache refresh interface."""
    if request.method == "POST":
        cache_type = request.form.get("cache_type", "all")
        
        try:
            if cache_type == "all":
                refresh_all_caches()
                flash("All caches refreshed successfully!", "success")
            else:
                refresh_specific_cache(cache_type)
                flash(f"{cache_type.title()} caches refreshed successfully!", "success")
            
            return redirect(url_for("cache_management.cache_status"))
            
        except Exception as e:
            flash(f"Cache refresh failed: {str(e)}", "error")
            return redirect(url_for("cache_management.cache_refresh"))
    
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
        "management/cache_refresh.html",
        cache_types=cache_types,
        title="Refresh Caches"
    )


@cache_management_bp.route("/management/cache/scheduler/start", methods=["POST"])
@login_required
@admin_required
def start_scheduler():
    """Start the cache refresh scheduler."""
    try:
        start_cache_refresh_scheduler()
        return jsonify({
            "success": True,
            "message": "Cache refresh scheduler started successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@cache_management_bp.route("/management/cache/scheduler/stop", methods=["POST"])
@login_required
@admin_required
def stop_scheduler():
    """Stop the cache refresh scheduler."""
    try:
        stop_cache_refresh_scheduler()
        return jsonify({
            "success": True,
            "message": "Cache refresh scheduler stopped successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@cache_management_bp.route("/management/cache/api/status")
@login_required
@admin_required
def api_cache_status():
    """API endpoint for cache status (for AJAX updates)."""
    try:
        status = get_cache_status()
        return jsonify({
            "success": True,
            "data": status
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@cache_management_bp.route("/management/cache/api/refresh", methods=["POST"])
@login_required
@admin_required
def api_cache_refresh():
    """API endpoint for cache refresh (for AJAX requests)."""
    data = request.get_json()
    cache_type = data.get("cache_type", "all")
    
    try:
        if cache_type == "all":
            refresh_all_caches()
            message = "All caches refreshed successfully"
        else:
            refresh_specific_cache(cache_type)
            message = f"{cache_type.title()} caches refreshed successfully"
        
        return jsonify({
            "success": True,
            "message": message
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def load_routes(bp):
    """Load cache management routes into the provided blueprint."""
    # Register routes with the main blueprint
    bp.add_url_rule("/management/cache/status", "cache_status", cache_status)
    bp.add_url_rule("/management/cache/refresh", "cache_refresh", cache_refresh, methods=["GET", "POST"])
    bp.add_url_rule("/management/cache/scheduler/start", "start_scheduler", start_scheduler, methods=["POST"])
    bp.add_url_rule("/management/cache/scheduler/stop", "stop_scheduler", stop_scheduler, methods=["POST"])
    bp.add_url_rule("/management/cache/api/status", "api_cache_status", api_cache_status)
    bp.add_url_rule("/management/cache/api/refresh", "api_cache_refresh", api_cache_refresh, methods=["POST"])

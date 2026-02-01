"""
District Virtual Sessions Route
===============================

Provides virtual session views for Virtual Admin users.
Sessions are automatically filtered by the tenant's linked district.

Requirements:
- Virtual Admin users see sessions for their district
- Sessions come from Pathful import (EventType.VIRTUAL_SESSION)
- Read-only access (no import capabilities)
"""

from datetime import datetime

from flask import render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from models import db
from models.event import Event, EventStatus, EventType
from models.tenant import Tenant
from routes.district import district_bp


def get_tenant_district_name():
    """Get the district name for the current user's tenant."""
    if not current_user.tenant_id:
        return None

    # Query the tenant
    tenant = Tenant.query.get(current_user.tenant_id)
    if not tenant:
        return None

    # Check if tenant has a linked district via FK
    if tenant.district:
        return tenant.district.name

    # Fallback: check settings for linked_district_name (legacy)
    return tenant.get_setting("linked_district_name")


@district_bp.route("/virtual-sessions")
@login_required
def virtual_sessions():
    """
    Virtual Sessions view for district users.

    Shows all Pathful-imported virtual sessions filtered by the tenant's
    linked district. Accessible to Virtual Admin (and higher) roles.
    """
    # Get the district name for this tenant
    district_name = get_tenant_district_name()

    if not district_name:
        return render_template(
            "district/virtual_sessions.html",
            sessions=None,
            error="No district linked to this tenant. Please contact an administrator.",
            district_name=None,
            total_sessions=0,
            total_students=0,
            filters={},
            career_clusters=[],
        )

    # Get filter parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Date range (default: current academic year Aug-Jul)
    today = datetime.now()
    if today.month >= 8:
        default_start = datetime(today.year, 8, 1)
        default_end = datetime(today.year + 1, 7, 31, 23, 59, 59)
    else:
        default_start = datetime(today.year - 1, 8, 1)
        default_end = datetime(today.year, 7, 31, 23, 59, 59)

    date_from_str = request.args.get("date_from")
    date_to_str = request.args.get("date_to")

    try:
        date_from = (
            datetime.strptime(date_from_str, "%Y-%m-%d")
            if date_from_str
            else default_start
        )
    except ValueError:
        date_from = default_start

    try:
        date_to = (
            datetime.strptime(date_to_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            if date_to_str
            else default_end
        )
    except ValueError:
        date_to = default_end

    # Other filters
    career_cluster = request.args.get("career_cluster", "")
    status = request.args.get("status", "")
    search = request.args.get("search", "")

    # Base query - virtual sessions for this district
    query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.district_partner == district_name,  # Auto-filter by tenant's district
        Event.start_date >= date_from,
        Event.start_date <= date_to,
    )

    # Apply additional filters
    if career_cluster:
        query = query.filter(Event.career_cluster == career_cluster)

    if status:
        try:
            status_enum = EventStatus(status)
            query = query.filter(Event.status == status_enum)
        except ValueError:
            pass

    if search:
        query = query.filter(
            db.or_(
                Event.title.ilike(f"%{search}%"),
                Event.career_cluster.ilike(f"%{search}%"),
                Event.location.ilike(f"%{search}%"),
                Event.educators.ilike(f"%{search}%"),
                Event.professionals.ilike(f"%{search}%"),
            )
        )

    # Order and paginate with eager loading
    query = query.options(
        joinedload(Event.school_obj),
        joinedload(Event.volunteers),
        joinedload(Event.teachers),
    ).order_by(Event.start_date.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get unique career clusters for filter dropdown (within this district)
    career_clusters = (
        db.session.query(Event.career_cluster)
        .filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.district_partner == district_name,
            Event.career_cluster.isnot(None),
            Event.career_cluster != "",
        )
        .distinct()
        .order_by(Event.career_cluster)
        .all()
    )
    career_clusters = [c[0] for c in career_clusters]

    # Get summary stats for this district
    total_sessions = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.district_partner == district_name,
        Event.start_date >= date_from,
        Event.start_date <= date_to,
    ).count()

    total_students = (
        db.session.query(func.sum(Event.registered_student_count))
        .filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.district_partner == district_name,
            Event.start_date >= date_from,
            Event.start_date <= date_to,
        )
        .scalar()
        or 0
    )

    return render_template(
        "district/virtual_sessions.html",
        sessions=pagination,
        district_name=district_name,
        career_clusters=career_clusters,
        total_sessions=total_sessions,
        total_students=total_students,
        filters={
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
            "career_cluster": career_cluster,
            "status": status,
            "search": search,
        },
    )

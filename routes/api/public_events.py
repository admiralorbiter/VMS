"""
Public District Event API Routes

Public API for districts to embed event listings on their websites.

Requirements:
- FR-API-101: GET /api/v1/district/{tenant}/events - List published events
- FR-API-102: GET /api/v1/district/{tenant}/events/{slug} - Event details
- FR-API-103: API key authentication via X-API-Key header
- FR-API-104: Rate limiting (60/min, 1000/hr, 10000/day) via Flask-Limiter
- FR-API-105: CORS support for district websites
- FR-API-106: API key rotation (via tenant settings)
- FR-API-107: JSON envelope with success, data, pagination
- FR-API-108: Event objects with required fields

Usage:
    GET /api/v1/district/kansas-city-usd/events
    Headers: X-API-Key: your-tenant-api-key
"""

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, g, jsonify, request
from flask_cors import cross_origin

from models.event import Event, EventStatus
from models.tenant import Tenant
from utils.rate_limiter import get_api_key_or_ip, limiter

# Create public API blueprint
public_api_bp = Blueprint("public_api", __name__, url_prefix="/api/v1/district")


def require_api_key(f):
    """
    Decorator to require valid API key (FR-API-103).

    Validates X-API-Key header against tenant's stored key hash.
    Sets g.tenant for the request.
    """

    @wraps(f)
    def decorated_function(tenant_slug, *args, **kwargs):
        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "MISSING_API_KEY",
                            "message": "X-API-Key header is required",
                        },
                    }
                ),
                401,
            )

        # Find tenant by slug
        tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()

        if not tenant:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "TENANT_NOT_FOUND",
                            "message": f"Tenant '{tenant_slug}' not found",
                        },
                    }
                ),
                404,
            )

        # Validate API key
        if not tenant.validate_api_key(api_key):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_API_KEY",
                            "message": "Invalid API key",
                        },
                    }
                ),
                401,
            )

        # Set tenant in g for use in route
        g.api_tenant = tenant

        return f(tenant_slug, *args, **kwargs)

    return decorated_function


def get_cors_origins(tenant):
    """Get CORS origins for a tenant."""
    origins = tenant.get_allowed_origins_list()
    return origins if origins else ["*"]


def build_event_response(event):
    """
    Build event object for API response (FR-API-108).

    Includes: id, title, description, event_type, date, times,
    location, volunteers_needed, signup_url
    """
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": event.type.value if event.type else None,
        "format": event.format.value if event.format else None,
        "date": event.start_date.strftime("%Y-%m-%d") if event.start_date else None,
        "start_time": event.start_date.strftime("%H:%M") if event.start_date else None,
        "end_time": event.end_date.strftime("%H:%M") if event.end_date else None,
        "start_datetime": event.start_date.isoformat() if event.start_date else None,
        "end_datetime": event.end_date.isoformat() if event.end_date else None,
        "location": event.location,
        "volunteers_needed": event.volunteers_needed or 0,
        "volunteers_registered": event.volunteer_count or 0,
        "slots_available": max(
            0, (event.volunteers_needed or 0) - (event.volunteer_count or 0)
        ),
        "signup_url": event.registration_link,
        "status": event.status.value if event.status else None,
    }


@public_api_bp.route("/<tenant_slug>/events", methods=["GET", "OPTIONS"])
@limiter.limit(
    "60 per minute; 1000 per hour; 10000 per day", key_func=get_api_key_or_ip
)
@cross_origin()  # FR-API-105: CORS support
@require_api_key
def list_events(tenant_slug):
    """
    List published events for a tenant (FR-API-101).

    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        from_date: Filter events from this date (YYYY-MM-DD)
        to_date: Filter events to this date (YYYY-MM-DD)
        event_type: Filter by event type

    Returns:
        JSON with success, data, and pagination (FR-API-107)
    """
    tenant = g.api_tenant

    # Pagination params
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    # Date filters
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    event_type = request.args.get("event_type")

    # Base query - only published events for this tenant
    query = Event.query.filter(
        Event.tenant_id == tenant.id, Event.status == EventStatus.PUBLISHED
    )

    # Apply date filters
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            query = query.filter(Event.start_date >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            query = query.filter(Event.start_date <= to_dt)
        except ValueError:
            pass

    # Apply event type filter
    if event_type:
        query = query.filter(Event.type == event_type)

    # Order by date
    query = query.order_by(Event.start_date.asc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Build response (FR-API-107)
    return jsonify(
        {
            "success": True,
            "data": [build_event_response(event) for event in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
            "meta": {
                "tenant": tenant.slug,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    )


@public_api_bp.route("/<tenant_slug>/events/<event_id>", methods=["GET", "OPTIONS"])
@limiter.limit(
    "60 per minute; 1000 per hour; 10000 per day", key_func=get_api_key_or_ip
)
@cross_origin()  # FR-API-105: CORS support
@require_api_key
def get_event(tenant_slug, event_id):
    """
    Get single event details (FR-API-102).

    Returns:
        JSON with event details including signup URL (FR-API-108)
    """
    tenant = g.api_tenant

    # Find event - must be published and belong to tenant
    event = Event.query.filter(
        Event.id == event_id,
        Event.tenant_id == tenant.id,
        Event.status == EventStatus.PUBLISHED,
    ).first()

    if not event:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "EVENT_NOT_FOUND",
                        "message": f"Event '{event_id}' not found",
                    },
                }
            ),
            404,
        )

    return jsonify(
        {
            "success": True,
            "data": build_event_response(event),
            "meta": {
                "tenant": tenant.slug,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    )


@public_api_bp.route("/<tenant_slug>/events/upcoming", methods=["GET", "OPTIONS"])
@limiter.limit(
    "60 per minute; 1000 per hour; 10000 per day", key_func=get_api_key_or_ip
)
@cross_origin()
@require_api_key
def list_upcoming_events(tenant_slug):
    """
    List upcoming published events (convenience endpoint).

    Returns only future events, ordered by date.
    """
    tenant = g.api_tenant

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    # Query upcoming published events
    now = datetime.now(timezone.utc)
    query = Event.query.filter(
        Event.tenant_id == tenant.id,
        Event.status == EventStatus.PUBLISHED,
        Event.start_date >= now,
    ).order_by(Event.start_date.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "success": True,
            "data": [build_event_response(event) for event in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
            "meta": {
                "tenant": tenant.slug,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    )

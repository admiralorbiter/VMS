"""
Scoping Service Module
======================

Provides centralized helpers for tenant-based access control and event scoping.
Used by virtual session routes to enforce district admin access restrictions.

Phase D-3: District Admin Access (DEC-009)

Key Concepts:
- Tenant users are scoped to events in their linked district
- Staff/admin users (no tenant_id) have global access
- District scoping uses Event.district_partner field

Usage:
    from services.scoping import scope_events_query, can_edit_event

    # Scope a query based on user's access
    query = scope_events_query(Event.query, current_user)

    # Check if user can edit an event
    if not can_edit_event(current_user, event):
        abort(403)
"""

from models.tenant import Tenant
from models.user import TenantRole


def get_user_district_name(user):
    """
    Get the district name for a tenant user.

    Args:
        user: User object (must have tenant_id and tenant relationship)

    Returns:
        str: District name if user is tenant-scoped, None otherwise

    Examples:
        >>> get_user_district_name(staff_user)  # No tenant_id
        None
        >>> get_user_district_name(kck_admin)  # Tenant linked to KCK
        'Kansas City, Kansas Public Schools'
    """
    if not user or not user.tenant_id:
        return None

    # Get the tenant
    tenant = Tenant.query.get(user.tenant_id)
    if not tenant:
        return None

    # Check if tenant has a linked district via FK
    if tenant.district:
        return tenant.district.name

    # Fallback: check settings for linked_district_name (legacy)
    return tenant.get_setting("linked_district_name")


def is_tenant_user(user):
    """
    Check if user is a tenant (district) user.

    Args:
        user: User object

    Returns:
        bool: True if user has a tenant_id set
    """
    return user and user.tenant_id is not None


def is_staff_user(user):
    """
    Check if user is a PrepKC staff member (not tenant-scoped).

    Args:
        user: User object

    Returns:
        bool: True if user has no tenant_id (full access)
    """
    return user and user.tenant_id is None


def can_view_event(user, event):
    """
    Check if user can view an event.

    Staff users can view all events.
    Tenant users can only view events in their district.

    Args:
        user: User object
        event: Event object

    Returns:
        bool: True if user can view the event
    """
    if not user or not event:
        return False

    # Staff/admin can view all events
    if is_staff_user(user):
        return True

    # Tenant users can only view their district's events
    user_district = get_user_district_name(user)
    if not user_district:
        return False

    return event.district_partner == user_district


def can_edit_event(user, event):
    """
    Check if user can edit an event (with potential restrictions).

    Staff users can edit all events.
    Tenant admins can edit events in their district (with field restrictions).
    Other tenant users cannot edit events.

    Args:
        user: User object
        event: Event object

    Returns:
        bool: True if user can edit the event (may have field restrictions)
    """
    if not user or not event:
        return False

    # Staff/admin can edit all events
    if is_staff_user(user):
        return True

    # Check if user is in the event's district
    user_district = get_user_district_name(user)
    if not user_district or event.district_partner != user_district:
        return False

    # Only tenant admin, coordinator, and virtual_admin can edit
    return user.tenant_role in [
        TenantRole.ADMIN,
        TenantRole.COORDINATOR,
        TenantRole.VIRTUAL_ADMIN,
    ]


def get_editable_fields(user, event):
    """
    Get the list of fields a user can edit for an event.

    Staff users can edit all fields.
    Tenant admins/coordinators can edit limited fields:
      - cancellation_reason, cancellation_notes
      - educators (teacher tagging)
      - professionals (presenter tagging)
      - status (only Draft -> Cancelled)

    Args:
        user: User object
        event: Event object

    Returns:
        list: List of field names the user can edit, or ['all'] for full access
    """
    if not user or not event:
        return []

    # Staff/admin can edit all fields
    if is_staff_user(user):
        return ["all"]

    # Check if user can edit this event at all
    if not can_edit_event(user, event):
        return []

    # Tenant admin/coordinator restricted fields
    return [
        "cancellation_reason",
        "cancellation_notes",
        "educators",
        "professionals",
        "status",  # Limited: only Draft -> Cancelled
    ]


def scope_events_query(query, user):
    """
    Apply tenant scoping to an event query.

    Staff users see all events (no filter applied).
    Tenant users see only events in their district.

    Args:
        query: SQLAlchemy query on Event model
        user: User object

    Returns:
        SQLAlchemy query with district filter applied (if needed)

    Example:
        query = Event.query.filter(Event.type == EventType.VIRTUAL_SESSION)
        query = scope_events_query(query, current_user)
    """
    from models.event import Event

    if not user:
        # No user = no results (safety)
        return query.filter(Event.id == -1)

    # Staff/admin see all events
    if is_staff_user(user):
        return query

    # Tenant users see only their district
    user_district = get_user_district_name(user)
    if not user_district:
        # User has tenant but no linked district = no results
        return query.filter(Event.id == -1)

    return query.filter(Event.district_partner == user_district)


def scope_flags_query(query, user):
    """
    Apply tenant scoping to a flag query.

    Staff users see all flags (no filter applied).
    Tenant users see only flags for events in their district.

    Args:
        query: SQLAlchemy query on EventFlag model (must have Event joined)
        user: User object

    Returns:
        SQLAlchemy query with district filter applied (if needed)
    """
    from models.event import Event
    from models.event_flag import EventFlag

    if not user:
        return query.filter(EventFlag.id == -1)

    # Staff/admin see all flags
    if is_staff_user(user):
        return query

    # Tenant users see only their district's flags
    user_district = get_user_district_name(user)
    if not user_district:
        return query.filter(EventFlag.id == -1)

    # Join to Event if not already joined, then filter
    return query.join(Event, EventFlag.event_id == Event.id).filter(
        Event.district_partner == user_district
    )

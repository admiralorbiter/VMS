"""
Virtual Session Audit Service
=============================

Provides specialized audit logging for virtual session changes.
This is a thin wrapper around the core log_audit_action() function
that adds domain-specific context for virtual session events.

Phase D-4: Audit Logging (DEC-009)

Usage:
    from services.audit_service import log_virtual_session_change, VirtualSessionAction

    # Log a teacher being tagged
    log_virtual_session_change(
        event=session,
        action=VirtualSessionAction.TEACHER_TAGGED,
        user=current_user,
        field_name="educators",
        old_value=None,
        new_value="John Smith"
    )
"""

from enum import Enum

from flask_login import current_user

from routes.utils import log_audit_action


class VirtualSessionAction(str, Enum):
    """
    Enumeration of auditable actions for virtual sessions.

    Action naming follows: pol.virtual.session.{action}
    per documentation/content/audit_requirements.md
    """

    # Teacher/Presenter tagging
    TEACHER_TAGGED = "teacher_tagged"
    TEACHER_UNTAGGED = "teacher_untagged"
    PRESENTER_TAGGED = "presenter_tagged"
    PRESENTER_UNTAGGED = "presenter_untagged"

    # Status changes
    STATUS_CHANGED = "status_changed"
    CANCELLATION_SET = "cancellation_set"

    # Flag management
    FLAG_RESOLVED = "flag_resolved"
    FLAG_CREATED = "flag_created"

    # Import operations
    IMPORTED = "imported"
    UPDATED_VIA_IMPORT = "updated_via_import"

    # Field edits (generic)
    FIELD_UPDATED = "field_updated"


def log_virtual_session_change(
    event,
    action: VirtualSessionAction,
    user=None,
    field_name: str = None,
    old_value=None,
    new_value=None,
    source: str = "manual",
    notes: str = None,
):
    """
    Log a change to a virtual session event.

    This function provides a specialized interface for logging virtual session
    changes, enriching the audit log with session-specific metadata including
    user role and district context.

    Args:
        event: Event object being modified
        action: VirtualSessionAction enum value
        user: User making the change (defaults to current_user, None for system)
        field_name: Name of the field being changed (optional)
        old_value: Previous value (will be stringified)
        new_value: New value (will be stringified)
        source: Source of change - "manual", "pathful_import", "api"
        notes: Optional context about the change

    Examples:
        # Log teacher being tagged
        log_virtual_session_change(
            event=session,
            action=VirtualSessionAction.TEACHER_TAGGED,
            field_name="educators",
            new_value="Jane Doe"
        )

        # Log import update
        log_virtual_session_change(
            event=session,
            action=VirtualSessionAction.UPDATED_VIA_IMPORT,
            user=None,  # System action
            source="pathful_import",
            notes="Weekly sync"
        )
    """
    # Use current_user if no user specified and we're in request context
    if user is None:
        try:
            user = current_user if current_user.is_authenticated else None
        except RuntimeError:
            # Outside of request context
            user = None

    # Build action name following naming convention
    action_name = f"pol.virtual.session.{action.value}"

    # Build metadata with rich context
    metadata = {
        "session_title": getattr(event, "title", None),
        "pathful_session_id": getattr(event, "pathful_session_id", None),
        "district": getattr(event, "district_partner", None),
        "source": source,
    }

    # Add field change details if provided
    if field_name:
        metadata["field_name"] = field_name
    if old_value is not None:
        metadata["old_value"] = str(old_value)[:500]  # Truncate long values
    if new_value is not None:
        metadata["new_value"] = str(new_value)[:500]

    # Add user context
    if user:
        metadata["actor_role"] = _get_user_role(user)
        metadata["actor_district"] = _get_user_district(user)
    else:
        metadata["actor_role"] = "system"

    # Add notes if provided
    if notes:
        metadata["notes"] = notes

    # Call the core audit logging function
    log_audit_action(
        action=action_name,
        resource_type="virtual_session",
        resource_id=event.id if event else None,
        metadata=metadata,
    )


def _get_user_role(user) -> str:
    """Get a human-readable role string for the user."""
    if not user:
        return "system"

    # Check for staff/admin
    if getattr(user, "is_admin", False):
        return "admin"

    # Check for tenant role (may be string or enum)
    tenant_role = getattr(user, "tenant_role", None)
    if tenant_role:
        role_value = (
            tenant_role.value if hasattr(tenant_role, "value") else str(tenant_role)
        )
        return f"tenant_{role_value}"

    # Default
    return "user"


def _get_user_district(user) -> str:
    """Get the district name for a tenant user, if applicable."""
    if not user:
        return None

    # Import here to avoid circular imports
    from services.scoping import get_user_district_name

    return get_user_district_name(user)


# Convenience functions for common actions


def log_teacher_tagged(event, teacher_name: str, user=None):
    """Log a teacher being tagged to a session."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.TEACHER_TAGGED,
        user=user,
        field_name="educators",
        new_value=teacher_name,
    )


def log_teacher_untagged(event, teacher_name: str, user=None):
    """Log a teacher being untagged from a session."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.TEACHER_UNTAGGED,
        user=user,
        field_name="educators",
        old_value=teacher_name,
    )


def log_presenter_tagged(event, presenter_name: str, user=None):
    """Log a presenter being tagged to a session."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.PRESENTER_TAGGED,
        user=user,
        field_name="professionals",
        new_value=presenter_name,
    )


def log_presenter_untagged(event, presenter_name: str, user=None):
    """Log a presenter being untagged from a session."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.PRESENTER_UNTAGGED,
        user=user,
        field_name="professionals",
        old_value=presenter_name,
    )


def log_status_changed(event, old_status: str, new_status: str, user=None):
    """Log a status change on a session."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.STATUS_CHANGED,
        user=user,
        field_name="status",
        old_value=old_status,
        new_value=new_status,
    )


def log_cancellation_set(event, reason: str, notes: str = None, user=None):
    """Log cancellation reason being set."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.CANCELLATION_SET,
        user=user,
        field_name="cancellation_reason",
        new_value=reason,
        notes=notes,
    )


def log_flag_resolved(event, flag_type: str, resolution_notes: str = None, user=None):
    """Log a flag being resolved."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.FLAG_RESOLVED,
        user=user,
        field_name="flag",
        old_value=flag_type,
        new_value="resolved",
        notes=resolution_notes,
    )


def log_session_imported(event, source: str = "pathful_import"):
    """Log a new session being created via import."""
    log_virtual_session_change(
        event=event, action=VirtualSessionAction.IMPORTED, user=None, source=source
    )


def log_session_updated_via_import(
    event, changed_fields: list, source: str = "pathful_import"
):
    """Log an existing session being updated via import."""
    log_virtual_session_change(
        event=event,
        action=VirtualSessionAction.UPDATED_VIA_IMPORT,
        user=None,
        source=source,
        notes=(
            f"Fields updated: {', '.join(changed_fields)}" if changed_fields else None
        ),
    )

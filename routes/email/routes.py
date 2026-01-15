"""
Email Management Routes Module
==============================

This module provides administrative functionality for email management in the VMS system.
It handles email templates, outbox management, delivery attempts, and settings.

Key Features:
- Email template management
- Outbox message viewing and management
- Delivery attempt tracking
- Email settings and safety configuration
- Test email sending
- Quality check viewing

Main Endpoints:
- /management/email: Email overview dashboard
- /management/email/templates: Template management
- /management/email/outbox: Message outbox
- /management/email/attempts: Delivery attempts
- /management/email/settings: Email settings

Security Features:
- Admin-only access for all operations
- Role-based permission checking
- Input validation and sanitization
- Error handling with user feedback
"""

import os
from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from models import db
from models.email import (
    DeliveryAttemptStatus,
    EmailDeliveryAttempt,
    EmailMessage,
    EmailMessageStatus,
    EmailTemplate,
)
from routes.decorators import security_level_required
from routes.utils import log_audit_action
from utils.email import (
    create_delivery_attempt,
    create_email_message,
    get_email_allowlist,
    is_email_delivery_enabled,
    is_production_environment,
    queue_message_for_delivery,
    run_quality_checks,
)

email_bp = Blueprint("email", __name__)


@email_bp.route("/management/email")
@login_required
@security_level_required(3)  # ADMIN only
def email_overview():
    """
    Display email overview dashboard.

    Shows quick health metrics, queue status, and recent failures.
    """
    # Get queue stats
    queued_count = EmailMessage.query.filter_by(
        status=EmailMessageStatus.QUEUED
    ).count()
    failed_count = EmailMessage.query.filter_by(
        status=EmailMessageStatus.FAILED
    ).count()
    sent_today = EmailMessage.query.filter(
        EmailMessage.status == EmailMessageStatus.SENT,
        EmailMessage.sent_at >= datetime.now(timezone.utc) - timedelta(days=1),
    ).count()

    # Recent failures (last 24h)
    recent_failures = (
        EmailDeliveryAttempt.query.filter(
            EmailDeliveryAttempt.status == DeliveryAttemptStatus.FAILED,
            EmailDeliveryAttempt.attempted_at
            >= datetime.now(timezone.utc) - timedelta(days=1),
        )
        .limit(10)
        .all()
    )

    # Delivery enabled status
    delivery_enabled = is_email_delivery_enabled()
    allowlist_active = (
        len(get_email_allowlist()) > 0 and not is_production_environment()
    )

    return render_template(
        "email/overview.html",
        queued_count=queued_count,
        failed_count=failed_count,
        sent_today=sent_today,
        recent_failures=recent_failures,
        delivery_enabled=delivery_enabled,
        allowlist_active=allowlist_active,
        is_production=is_production_environment(),
    )


@email_bp.route("/management/email/templates")
@login_required
@security_level_required(3)  # ADMIN only
def email_templates():
    """
    Display email templates list.

    Shows all templates with version information and active status.
    """
    templates = EmailTemplate.query.order_by(
        EmailTemplate.purpose_key, EmailTemplate.version.desc()
    ).all()

    # Group by purpose_key
    template_groups = {}
    for template in templates:
        if template.purpose_key not in template_groups:
            template_groups[template.purpose_key] = []
        template_groups[template.purpose_key].append(template)

    return render_template("email/templates.html", template_groups=template_groups)


@email_bp.route("/management/email/templates/<int:template_id>")
@login_required
@security_level_required(3)  # ADMIN only
def email_template_detail(template_id):
    """
    Display email template detail with preview.

    Shows template content, version info, and allows preview with sample context.
    """
    template = EmailTemplate.query.get_or_404(template_id)

    # Sample context for preview
    sample_context = {
        "user_name": "John Doe",
        "district_name": "Example District",
        "teacher_name": "Jane Smith",
        "bug_report_id": "123",
        "magic_url": "https://example.com/sign-in?token=abc123",
    }

    return render_template(
        "email/template_detail.html", template=template, sample_context=sample_context
    )


@email_bp.route("/management/email/outbox")
@login_required
@security_level_required(3)  # ADMIN only
def email_outbox():
    """
    Display email outbox (messages list).

    Shows all email messages with filtering and search capabilities.
    """
    # Get filter parameters
    status_filter = request.args.get("status", "all")
    template_filter = request.args.get("template", "")
    search_query = request.args.get("search", "").strip()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    # Start with base query
    query = EmailMessage.query

    # Apply status filter
    if status_filter != "all":
        try:
            status_enum = EmailMessageStatus[status_filter.upper()]
            query = query.filter(EmailMessage.status == status_enum)
        except KeyError:
            pass

    # Apply template filter
    if template_filter:
        query = query.join(EmailTemplate).filter(
            EmailTemplate.purpose_key == template_filter
        )

    # Apply search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                EmailMessage.subject.ilike(search_term),
                EmailMessage.recipients.contains([search_query]),
            )
        )

    # Order by newest first
    query = query.order_by(EmailMessage.created_at.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    messages = pagination.items

    # Get template list for filter dropdown
    templates = EmailTemplate.query.distinct(EmailTemplate.purpose_key).all()

    return render_template(
        "email/outbox.html",
        messages=messages,
        pagination=pagination,
        status_filter=status_filter,
        template_filter=template_filter,
        search_query=search_query,
        templates=templates,
        EmailMessageStatus=EmailMessageStatus,
    )


@email_bp.route("/management/email/outbox/<int:message_id>")
@login_required
@security_level_required(3)  # ADMIN only
def email_message_detail(message_id):
    """
    Display email message detail.

    Shows full message content, recipients, quality checks, and delivery attempts.
    """
    message = EmailMessage.query.get_or_404(message_id)
    attempts = (
        EmailDeliveryAttempt.query.filter_by(message_id=message_id)
        .order_by(EmailDeliveryAttempt.attempted_at.desc())
        .all()
    )

    return render_template(
        "email/message_detail.html",
        message=message,
        attempts=attempts,
        EmailMessageStatus=EmailMessageStatus,
        DeliveryAttemptStatus=DeliveryAttemptStatus,
    )


@email_bp.route("/management/email/outbox/<int:message_id>/queue", methods=["POST"])
@login_required
@security_level_required(3)  # ADMIN only
def queue_message(message_id):
    """
    Queue an email message for delivery.

    Changes message status from DRAFT to QUEUED.
    """
    try:
        message = queue_message_for_delivery(message_id)
        log_audit_action(
            action="queue_email",
            resource_type="email_message",
            resource_id=str(message_id),
        )
        flash("Message queued for delivery", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(f"Error queueing message: {str(e)}", "error")

    return redirect(url_for("email.email_message_detail", message_id=message_id))


@email_bp.route("/management/email/outbox/<int:message_id>/send", methods=["POST"])
@login_required
@security_level_required(3)  # ADMIN only
def send_message(message_id):
    """
    Send an email message immediately.

    Creates a delivery attempt and sends via Mailjet.
    """
    message = EmailMessage.query.get_or_404(message_id)

    if message.status != EmailMessageStatus.QUEUED:
        flash(
            f"Message must be QUEUED to send (current: {EmailMessageStatus(message.status).name})",
            "error",
        )
        return redirect(url_for("email.email_message_detail", message_id=message_id))

    try:
        is_dry_run = request.form.get("dry_run", "false").lower() == "true"
        attempt = create_delivery_attempt(message, is_dry_run=is_dry_run)
        log_audit_action(
            action="send_email",
            resource_type="email_message",
            resource_id=str(message_id),
            metadata={"attempt_id": attempt.id, "dry_run": is_dry_run},
        )
        if is_dry_run:
            flash("Dry-run completed (no actual delivery)", "info")
        else:
            flash("Message sent successfully", "success")
    except Exception as e:
        flash(f"Error sending message: {str(e)}", "error")

    return redirect(url_for("email.email_message_detail", message_id=message_id))


@email_bp.route("/management/email/outbox/<int:message_id>/cancel", methods=["POST"])
@login_required
@security_level_required(3)  # ADMIN only
def cancel_message(message_id):
    """
    Cancel an email message.

    Changes message status to CANCELLED if in DRAFT or QUEUED status.
    """
    message = EmailMessage.query.get_or_404(message_id)

    if message.status not in [EmailMessageStatus.DRAFT, EmailMessageStatus.QUEUED]:
        flash(
            f"Cannot cancel message in {EmailMessageStatus(message.status).name} status",
            "error",
        )
        return redirect(url_for("email.email_message_detail", message_id=message_id))

    message.status = EmailMessageStatus.CANCELLED
    message.status_updated_at = datetime.now(timezone.utc)
    db.session.commit()

    log_audit_action(
        action="cancel_email",
        resource_type="email_message",
        resource_id=str(message_id),
    )
    flash("Message cancelled", "success")
    return redirect(url_for("email.email_message_detail", message_id=message_id))


@email_bp.route("/management/email/attempts")
@login_required
@security_level_required(3)  # ADMIN only
def email_attempts():
    """
    Display delivery attempts list.

    Shows all delivery attempts with filtering and search.
    """
    # Get filter parameters
    status_filter = request.args.get("status", "all")
    message_id_filter = request.args.get("message_id", type=int)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    # Start with base query
    query = EmailDeliveryAttempt.query

    # Apply status filter
    if status_filter != "all":
        try:
            status_enum = DeliveryAttemptStatus[status_filter.upper()]
            query = query.filter(EmailDeliveryAttempt.status == status_enum)
        except KeyError:
            pass

    # Apply message_id filter
    if message_id_filter:
        query = query.filter(EmailDeliveryAttempt.message_id == message_id_filter)

    # Order by newest first
    query = query.order_by(EmailDeliveryAttempt.attempted_at.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    attempts = pagination.items

    return render_template(
        "email/attempts.html",
        attempts=attempts,
        pagination=pagination,
        status_filter=status_filter,
        message_id_filter=message_id_filter,
        DeliveryAttemptStatus=DeliveryAttemptStatus,
    )


@email_bp.route("/management/email/settings")
@login_required
@security_level_required(3)  # ADMIN only
def email_settings():
    """
    Display email settings and safety configuration.

    Shows current settings (read-only, driven by environment variables).
    """
    delivery_enabled = is_email_delivery_enabled()
    allowlist = get_email_allowlist()
    is_prod = is_production_environment()
    mail_from = os.environ.get("MAIL_FROM", "Not configured")
    mail_from_name = os.environ.get("MAIL_FROM_NAME", "Not configured")

    # Check if Mailjet is configured
    from utils.email import get_mailjet_client

    mailjet_configured = get_mailjet_client() is not None

    # Get templates for test send dropdown
    templates = (
        EmailTemplate.query.filter_by(is_active=True)
        .order_by(EmailTemplate.purpose_key)
        .all()
    )

    # Determine test email recipient - prefer allowlist in non-production
    test_email_recipient = current_user.email
    if not is_prod and allowlist:
        test_email_recipient = allowlist[0]

    return render_template(
        "email/settings.html",
        delivery_enabled=delivery_enabled,
        allowlist=allowlist,
        is_production=is_prod,
        mail_from=mail_from,
        mail_from_name=mail_from_name,
        mailjet_configured=mailjet_configured,
        templates=templates,
        test_email_recipient=test_email_recipient,
    )


@email_bp.route("/management/email/test-send", methods=["POST"])
@login_required
@security_level_required(3)  # ADMIN only
def test_send():
    """
    Send a test email to the current user.

    Only works if user's email is in allowlist (non-prod) or delivery is enabled (prod).
    """
    import os

    from utils.email import EmailQualityError, create_email_message, get_mailjet_client

    # Get template
    template_id = request.form.get("template_id", type=int)
    if not template_id:
        flash("Template ID is required", "error")
        return redirect(url_for("email.email_settings"))

    template = EmailTemplate.query.get_or_404(template_id)

    # Get recipient - prefer allowlist email in non-production, fall back to current user's email
    recipient_email = None
    if not is_production_environment():
        allowlist = get_email_allowlist()
        if allowlist:
            # Use first email from allowlist in non-production
            # Normalize by stripping whitespace and lowercasing
            recipient_email = allowlist[0].strip().lower()

    # Fall back to current user's email if no allowlist email found
    if not recipient_email:
        recipient_email = current_user.email
        if recipient_email:
            recipient_email = recipient_email.strip().lower()

    if not recipient_email:
        flash(
            "Your user account does not have an email address and no allowlist is configured",
            "error",
        )
        return redirect(url_for("email.email_settings"))

    # Check if dry-run
    is_dry_run = request.form.get("dry_run", "false").lower() == "true"

    try:
        # Build context with all required and optional placeholders
        # Start with required placeholders
        context = {
            "user_name": current_user.username or "Test User",
            "test_mode": "DRY-RUN" if is_dry_run else "LIVE",
        }

        # Add all required placeholders with default test values
        if template.required_placeholders:
            for placeholder in template.required_placeholders:
                if placeholder not in context:
                    # Provide sensible defaults for common placeholders
                    if placeholder == "district_name":
                        context["district_name"] = "Test District"
                    elif placeholder == "school_name":
                        context["school_name"] = "Test School"
                    elif placeholder == "organization_name":
                        context["organization_name"] = "Test Organization"
                    else:
                        # Generic default for any other required placeholder
                        context[placeholder] = (
                            f"Test {placeholder.replace('_', ' ').title()}"
                        )

        # Add optional placeholders with defaults if they exist in the template
        if template.optional_placeholders:
            for placeholder in template.optional_placeholders:
                if placeholder not in context:
                    if placeholder == "district_name":
                        context["district_name"] = "Test District"
                    elif placeholder == "school_name":
                        context["school_name"] = "Test School"
                    elif placeholder == "organization_name":
                        context["organization_name"] = "Test Organization"
                    else:
                        context[placeholder] = (
                            f"Test {placeholder.replace('_', ' ').title()}"
                        )

        message = create_email_message(
            template=template,
            recipients=[recipient_email],
            context=context,
            created_by_id=current_user.id,
            status=(
                EmailMessageStatus.QUEUED
                if not is_dry_run
                else EmailMessageStatus.DRAFT
            ),
        )

        # Ensure message is committed to database before attempting delivery
        # This way it will appear in outbox even if delivery fails
        db.session.commit()

        # Send immediately
        attempt = create_delivery_attempt(message, is_dry_run=is_dry_run)

        log_audit_action(
            action="test_send_email",
            resource_type="email_message",
            resource_id=str(message.id),
            metadata={"dry_run": is_dry_run},
        )

        if is_dry_run:
            flash(
                f"Test email dry-run completed (no actual delivery). Message #{message.id} saved to outbox.",
                "info",
            )
        else:
            # Check if delivery actually succeeded
            if attempt.status == DeliveryAttemptStatus.SUCCESS:
                flash(
                    f"Test email sent successfully to {recipient_email}! Message #{message.id} is in the outbox.",
                    "success",
                )
            elif attempt.status == DeliveryAttemptStatus.FAILED:
                flash(
                    f"Test email created (Message #{message.id}) but delivery failed: {attempt.error_message or 'Unknown error'}. Check Delivery Attempts and Outbox for details.",
                    "warning",
                )
            else:
                flash(
                    f"Test email created (Message #{message.id}). Status: {DeliveryAttemptStatus(attempt.status).name}. Check Outbox for details.",
                    "info",
                )

    except EmailQualityError as e:
        db.session.rollback()
        flash(f"Quality check failed: {str(e)}", "error")
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        flash(f"Error sending test email: {error_msg}", "error")
        # Also log to help user understand what went wrong
        if "Mailjet" in error_msg or "mailjet" in error_msg.lower():
            flash(
                "Check that Mailjet API keys are configured (MJ_APIKEY_PUBLIC and MJ_APIKEY_PRIVATE)",
                "warning",
            )
        elif "allowlist" in error_msg.lower() or "blocked" in error_msg.lower():
            flash(
                "Email was blocked by allowlist. Check EMAIL_ALLOWLIST environment variable.",
                "warning",
            )

    return redirect(url_for("email.email_settings"))

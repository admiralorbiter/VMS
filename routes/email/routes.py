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
from sqlalchemy import or_

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
    get_email_allowlist,
    is_email_delivery_enabled,
    is_production_environment,
    queue_message_for_delivery,
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

    Shows template content, version info, version history, and allows preview
    with sample context.
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

    # Version history for this purpose_key
    version_history = (
        EmailTemplate.query.filter_by(purpose_key=template.purpose_key)
        .order_by(EmailTemplate.version.desc())
        .all()
    )

    # Check if this template has messages (affects delete eligibility)
    message_count = EmailMessage.query.filter_by(template_id=template_id).count()

    return render_template(
        "email/template_detail.html",
        template=template,
        sample_context=sample_context,
        version_history=version_history,
        message_count=message_count,
    )


import re


def _auto_generate_template_content(html_template, text_template):
    """Auto-generate the missing template format from the provided one.

    If only HTML is provided, strip tags to create plain text.
    If only plain text is provided, wrap in <p> tags to create HTML.
    """
    if html_template and not text_template:
        # Strip HTML tags to generate plain text
        text = re.sub(r"<br\s*/?>", "\n", html_template)
        text = re.sub(r"</p>\s*<p[^>]*>", "\n\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text_template = text.strip()
    elif text_template and not html_template:
        # Wrap plain text lines in <p> tags
        lines = text_template.split("\n")
        html_parts = []
        for line in lines:
            line = line.strip()
            if line:
                html_parts.append(f"<p>{line}</p>")
            else:
                html_parts.append("")
        html_template = "\n".join(html_parts).strip()
    return html_template, text_template


@email_bp.route("/management/email/templates/new", methods=["GET", "POST"])
@login_required
@security_level_required(3)  # ADMIN only
def create_template():
    """
    Create a new email template.

    GET: Display empty template form.
    POST: Validate and create template with version 1.
    """
    if request.method == "GET":
        return render_template(
            "email/template_form.html", template=None, edit_mode=False
        )

    # POST: Create template
    name = request.form.get("name", "").strip()
    purpose_key = request.form.get("purpose_key", "").strip()
    description = request.form.get("description", "").strip()
    subject_template = request.form.get("subject_template", "").strip()
    html_template = request.form.get("html_template", "").strip()
    text_template = request.form.get("text_template", "").strip()
    required_placeholders_raw = request.form.get("required_placeholders", "").strip()
    optional_placeholders_raw = request.form.get("optional_placeholders", "").strip()

    # Validate required fields
    errors = []
    if not name:
        errors.append("Name is required.")
    if not purpose_key:
        errors.append("Purpose key is required.")
    if not subject_template:
        errors.append("Subject template is required.")
    if not html_template and not text_template:
        errors.append(
            "At least one of HTML template or plain-text template is required."
        )

    # Check purpose_key uniqueness
    if purpose_key:
        existing = EmailTemplate.query.filter_by(purpose_key=purpose_key).first()
        if existing:
            errors.append(
                f'Purpose key "{purpose_key}" already exists. '
                f'Use the existing template\'s "Create New Version" action instead.'
            )

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "email/template_form.html",
            template=None,
            edit_mode=False,
            form_data=request.form,
        )

    # Parse placeholders
    required_placeholders = (
        [p.strip() for p in required_placeholders_raw.split(",") if p.strip()]
        if required_placeholders_raw
        else None
    )
    optional_placeholders = (
        [p.strip() for p in optional_placeholders_raw.split(",") if p.strip()]
        if optional_placeholders_raw
        else None
    )

    # Auto-generate missing format
    html_template, text_template = _auto_generate_template_content(
        html_template, text_template
    )

    template = EmailTemplate(
        purpose_key=purpose_key,
        version=1,
        name=name,
        description=description or None,
        subject_template=subject_template,
        html_template=html_template,
        text_template=text_template,
        required_placeholders=required_placeholders,
        optional_placeholders=optional_placeholders,
        is_active=True,
        created_by_id=current_user.id,
    )
    db.session.add(template)
    db.session.commit()

    log_audit_action(
        action="create_email_template",
        resource_type="email_template",
        resource_id=str(template.id),
        metadata={"purpose_key": purpose_key, "version": 1},
    )
    flash(f'Template "{name}" created successfully.', "success")
    return redirect(url_for("email.email_template_detail", template_id=template.id))


@email_bp.route(
    "/management/email/templates/<int:template_id>/edit", methods=["GET", "POST"]
)
@login_required
@security_level_required(3)  # ADMIN only
def edit_template(template_id):
    """
    Edit an existing email template.

    GET: Display pre-filled form (purpose_key is read-only).
    POST: Validate and update template fields.
    """
    template = EmailTemplate.query.get_or_404(template_id)

    if request.method == "GET":
        return render_template(
            "email/template_form.html", template=template, edit_mode=True
        )

    # POST: Update template
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    subject_template = request.form.get("subject_template", "").strip()
    html_template = request.form.get("html_template", "").strip()
    text_template = request.form.get("text_template", "").strip()
    required_placeholders_raw = request.form.get("required_placeholders", "").strip()
    optional_placeholders_raw = request.form.get("optional_placeholders", "").strip()

    # Validate required fields
    errors = []
    if not name:
        errors.append("Name is required.")
    if not subject_template:
        errors.append("Subject template is required.")
    if not html_template and not text_template:
        errors.append(
            "At least one of HTML template or plain-text template is required."
        )

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "email/template_form.html",
            template=template,
            edit_mode=True,
            form_data=request.form,
        )

    # Parse placeholders
    required_placeholders = (
        [p.strip() for p in required_placeholders_raw.split(",") if p.strip()]
        if required_placeholders_raw
        else None
    )
    optional_placeholders = (
        [p.strip() for p in optional_placeholders_raw.split(",") if p.strip()]
        if optional_placeholders_raw
        else None
    )

    # Auto-generate missing format
    html_template, text_template = _auto_generate_template_content(
        html_template, text_template
    )

    template.name = name
    template.description = description or None
    template.subject_template = subject_template
    template.html_template = html_template
    template.text_template = text_template
    template.required_placeholders = required_placeholders
    template.optional_placeholders = optional_placeholders
    db.session.commit()

    log_audit_action(
        action="edit_email_template",
        resource_type="email_template",
        resource_id=str(template.id),
        metadata={"purpose_key": template.purpose_key, "version": template.version},
    )
    flash(f'Template "{template.name}" updated successfully.', "success")
    return redirect(url_for("email.email_template_detail", template_id=template.id))


@email_bp.route(
    "/management/email/templates/<int:template_id>/new-version", methods=["POST"]
)
@login_required
@security_level_required(3)  # ADMIN only
def create_template_version(template_id):
    """
    Create a new version of a template.

    Copies the current template content into a new record with version incremented.
    Deactivates all other versions for the same purpose_key.
    """
    source = EmailTemplate.query.get_or_404(template_id)

    # Get the highest version number for this purpose_key
    max_version = (
        db.session.query(db.func.max(EmailTemplate.version))
        .filter_by(purpose_key=source.purpose_key)
        .scalar()
        or 0
    )
    new_version = max_version + 1

    # Deactivate all existing versions for this purpose_key
    EmailTemplate.query.filter_by(purpose_key=source.purpose_key).update(
        {"is_active": False}
    )

    # Create new version
    new_template = EmailTemplate(
        purpose_key=source.purpose_key,
        version=new_version,
        name=source.name,
        description=source.description,
        subject_template=source.subject_template,
        html_template=source.html_template,
        text_template=source.text_template,
        required_placeholders=source.required_placeholders,
        optional_placeholders=source.optional_placeholders,
        is_active=True,
        created_by_id=current_user.id,
    )
    db.session.add(new_template)
    db.session.commit()

    log_audit_action(
        action="create_email_template_version",
        resource_type="email_template",
        resource_id=str(new_template.id),
        metadata={
            "purpose_key": source.purpose_key,
            "from_version": source.version,
            "new_version": new_version,
        },
    )
    flash(
        f'New version {new_version} of "{source.purpose_key}" created successfully.',
        "success",
    )
    return redirect(url_for("email.email_template_detail", template_id=new_template.id))


@email_bp.route(
    "/management/email/templates/<int:template_id>/activate", methods=["POST"]
)
@login_required
@security_level_required(3)  # ADMIN only
def activate_template(template_id):
    """
    Activate a template version.

    Deactivates all other versions with the same purpose_key and activates this one.
    """
    template = EmailTemplate.query.get_or_404(template_id)

    # Deactivate all versions for this purpose_key
    EmailTemplate.query.filter_by(purpose_key=template.purpose_key).update(
        {"is_active": False}
    )

    # Activate this version
    template.is_active = True
    db.session.commit()

    log_audit_action(
        action="activate_email_template",
        resource_type="email_template",
        resource_id=str(template.id),
        metadata={"purpose_key": template.purpose_key, "version": template.version},
    )
    flash(
        f'Version {template.version} of "{template.purpose_key}" is now active.',
        "success",
    )
    return redirect(url_for("email.email_template_detail", template_id=template.id))


@email_bp.route(
    "/management/email/templates/<int:template_id>/delete", methods=["POST"]
)
@login_required
@security_level_required(3)  # ADMIN only
def delete_template(template_id):
    """
    Delete a template version.

    Only allowed if the template has no associated EmailMessage records.
    """
    template = EmailTemplate.query.get_or_404(template_id)

    # Check for associated messages
    message_count = EmailMessage.query.filter_by(template_id=template_id).count()
    if message_count > 0:
        flash(
            f"Cannot delete this template — it has {message_count} associated message(s). "
            f"You can deactivate it instead.",
            "error",
        )
        return redirect(url_for("email.email_template_detail", template_id=template_id))

    purpose_key = template.purpose_key
    version = template.version
    db.session.delete(template)
    db.session.commit()

    log_audit_action(
        action="delete_email_template",
        resource_type="email_template",
        resource_id=str(template_id),
        metadata={"purpose_key": purpose_key, "version": version},
    )
    flash(f'Template "{purpose_key}" v{version} deleted.', "success")
    return redirect(url_for("email.email_templates"))


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

    from utils.email import EmailQualityError, create_email_message

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


@email_bp.route("/management/email/templates/<int:template_id>/placeholders")
@login_required
@security_level_required(3)
def template_placeholders(template_id):
    """
    Return template placeholder info as JSON.

    Used by the compose page to dynamically render placeholder input fields.
    """
    template = EmailTemplate.query.get_or_404(template_id)
    return jsonify(
        {
            "required": template.required_placeholders or [],
            "optional": template.optional_placeholders or [],
            "subject": template.subject_template or "",
            "purpose_key": template.purpose_key,
        }
    )


@email_bp.route("/management/email/compose", methods=["GET", "POST"])
@login_required
@security_level_required(3)  # ADMIN only
def compose():
    """
    Compose and send an email to arbitrary recipients.

    GET: Display compose form with template selection, recipient input,
         and dynamic placeholder fields.
    POST: Validate inputs, create email message, and optionally send.
    """
    from utils.email import EmailQualityError, create_email_message

    # Get active templates for dropdown
    templates = (
        EmailTemplate.query.filter_by(is_active=True)
        .order_by(EmailTemplate.purpose_key)
        .all()
    )

    is_prod = is_production_environment()
    allowlist = get_email_allowlist() if not is_prod else []

    if request.method == "GET":
        return render_template(
            "email/compose.html",
            templates=templates,
            is_production=is_prod,
            allowlist=allowlist,
        )

    # --- POST handling ---
    template_id = request.form.get("template_id", type=int)
    if not template_id:
        flash("Please select a template", "error")
        return render_template(
            "email/compose.html",
            templates=templates,
            is_production=is_prod,
            allowlist=allowlist,
        )

    template = EmailTemplate.query.get_or_404(template_id)

    # Parse recipients from textarea (one per line or comma-separated)
    raw_recipients = request.form.get("recipients", "").strip()
    if not raw_recipients:
        flash("Please enter at least one recipient email address", "error")
        return render_template(
            "email/compose.html",
            templates=templates,
            is_production=is_prod,
            allowlist=allowlist,
        )

    # Split by newlines and commas, strip whitespace, remove empties
    recipients = []
    for line in raw_recipients.replace(",", "\n").split("\n"):
        email = line.strip()
        if email:
            recipients.append(email)

    if not recipients:
        flash("No valid recipient addresses found", "error")
        return render_template(
            "email/compose.html",
            templates=templates,
            is_production=is_prod,
            allowlist=allowlist,
        )

    # Build context from placeholder form fields
    context = {}
    if template.required_placeholders:
        for placeholder in template.required_placeholders:
            value = request.form.get(f"placeholder_{placeholder}", "").strip()
            if not value:
                flash(
                    f"Required placeholder '{placeholder}' is missing a value", "error"
                )
                return render_template(
                    "email/compose.html",
                    templates=templates,
                    is_production=is_prod,
                    allowlist=allowlist,
                )
            context[placeholder] = value

    if template.optional_placeholders:
        for placeholder in template.optional_placeholders:
            value = request.form.get(f"placeholder_{placeholder}", "").strip()
            if value:
                context[placeholder] = value
            else:
                # Provide a sensible default for optional placeholders
                context[placeholder] = f"[{placeholder.replace('_', ' ').title()}]"

    # Determine action
    is_dry_run = request.form.get("dry_run", "false").lower() == "true"
    action = request.form.get("action", "draft")  # "draft" or "send"

    initial_status = EmailMessageStatus.DRAFT
    if action == "send":
        initial_status = EmailMessageStatus.QUEUED

    try:
        message = create_email_message(
            template=template,
            recipients=recipients,
            context=context,
            created_by_id=current_user.id,
            status=initial_status,
        )
        db.session.commit()

        log_audit_action(
            action="compose_email",
            resource_type="email_message",
            resource_id=str(message.id),
            metadata={
                "recipient_count": len(recipients),
                "template": template.purpose_key,
                "action": action,
                "dry_run": is_dry_run,
            },
        )

        if action == "send":
            # Send immediately
            attempt = create_delivery_attempt(message, is_dry_run=is_dry_run)

            if is_dry_run:
                flash(
                    f"Dry-run completed for {message.recipient_count} recipient(s). "
                    f"Message #{message.id} saved to outbox.",
                    "info",
                )
            elif attempt.status == DeliveryAttemptStatus.SUCCESS:
                flash(
                    f"Email sent to {message.recipient_count} recipient(s)! "
                    f"Message #{message.id} is in the outbox.",
                    "success",
                )
            else:
                flash(
                    f"Delivery failed: {attempt.error_message or 'Unknown error'}. "
                    f"Message #{message.id} saved to outbox.",
                    "error",
                )
        else:
            flash(
                f"Email saved as draft with {message.recipient_count} recipient(s). "
                f"Message #{message.id} — review and send from the outbox.",
                "success",
            )

        return redirect(url_for("email.email_message_detail", message_id=message.id))

    except EmailQualityError as e:
        db.session.rollback()
        flash(f"Quality check failed: {str(e)}", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Error composing email: {str(e)}", "error")

    return render_template(
        "email/compose.html",
        templates=templates,
        is_production=is_prod,
        allowlist=allowlist,
    )

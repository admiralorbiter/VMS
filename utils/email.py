"""
Email Utility Functions
=======================

This module provides utility functions for email management including:
- Safety gates (allowlist, environment checks)
- Quality checks (recipient validation, template validation)
- Mailjet integration
- Template rendering
- Error handling and alerting

Key Features:
- Safe-by-default email sending
- Recipient allowlist enforcement
- Quality validation
- Dry-run mode support
- Error tracking and alerting
"""

import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from flask import current_app
from mailjet_rest import Client

from models import db
from models.bug_report import BugReport, BugReportType
from models.email import (
    DeliveryAttemptStatus,
    EmailDeliveryAttempt,
    EmailMessage,
    EmailMessageStatus,
    EmailTemplate,
)


class EmailSafetyError(Exception):
    """Raised when email send is blocked by safety gates."""

    pass


class EmailQualityError(Exception):
    """Raised when email fails quality checks."""

    pass


def get_mailjet_client() -> Optional[Client]:
    """
    Get Mailjet client instance if credentials are configured.

    Returns:
        Client instance or None if not configured
    """
    api_key_public = os.environ.get("MJ_APIKEY_PUBLIC")
    api_key_private = os.environ.get("MJ_APIKEY_PRIVATE")

    if not api_key_public or not api_key_private:
        return None

    return Client(auth=(api_key_public, api_key_private), version="v3.1")


def is_email_delivery_enabled() -> bool:
    """
    Check if email delivery is enabled via environment variable.

    Returns:
        True if EMAIL_DELIVERY_ENABLED is set to 'true', False otherwise
    """
    return os.environ.get("EMAIL_DELIVERY_ENABLED", "").lower() == "true"


def get_email_allowlist() -> List[str]:
    """
    Get email allowlist from environment variable.

    Format: comma-separated list of email addresses or domains (e.g., @example.com)

    Returns:
        List of allowed email addresses/domains
    """
    allowlist_str = os.environ.get("EMAIL_ALLOWLIST", "")
    if not allowlist_str:
        return []
    return [addr.strip() for addr in allowlist_str.split(",") if addr.strip()]


def is_production_environment() -> bool:
    """
    Check if running in production environment.

    Returns:
        True if FLASK_ENV is 'production', False otherwise
    """
    return os.environ.get("FLASK_ENV", "").lower() == "production"


def check_recipient_allowlist(
    email: str, allowlist: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    Check if email address is in allowlist.

    Args:
        email: Email address to check
        allowlist: List of allowed emails/domains

    Returns:
        Tuple of (is_allowed, reason_if_blocked)
    """
    if not allowlist:
        return True, None

    email_lower = email.lower().strip()

    for allowed in allowlist:
        allowed_lower = allowed.lower().strip()
        # Exact match
        if email_lower == allowed_lower:
            return True, None
        # Domain match (starts with @)
        if allowed_lower.startswith("@") and email_lower.endswith(allowed_lower):
            return True, None

    return False, f"Email {email} not in allowlist"


def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "Email is required and must be a string"

    email = email.strip()
    if not email:
        return False, "Email cannot be empty"

    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, f"Invalid email format: {email}"

    return True, None


def validate_recipients(
    recipients: List[str],
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Validate and deduplicate recipient list.

    Args:
        recipients: List of email addresses

    Returns:
        Tuple of (valid_recipients, excluded_recipients_with_reasons)
    """
    valid = []
    excluded = []
    seen = set()

    for email in recipients:
        # Deduplicate
        email_lower = email.lower().strip()
        if email_lower in seen:
            excluded.append({"email": email, "reason": "Duplicate"})
            continue
        seen.add(email_lower)

        # Format validation
        is_valid, error = validate_email_format(email)
        if not is_valid:
            excluded.append({"email": email, "reason": error})
            continue

        valid.append(email)

    return valid, excluded


def check_safety_gates(
    recipients: List[str], is_dry_run: bool = False
) -> Tuple[bool, Optional[str], List[Dict[str, str]]]:
    """
    Check all safety gates before sending email.

    Args:
        recipients: List of recipient email addresses
        is_dry_run: Whether this is a dry-run (bypasses some checks)

    Returns:
        Tuple of (is_allowed, error_message, excluded_recipients)
    """
    excluded = []

    # Check if delivery is enabled (unless dry-run)
    if not is_dry_run and not is_email_delivery_enabled():
        return (
            False,
            "Email delivery is disabled (EMAIL_DELIVERY_ENABLED not set)",
            excluded,
        )

    # In non-production, enforce allowlist (unless dry-run)
    if not is_production_environment() and not is_dry_run:
        allowlist = get_email_allowlist()
        if allowlist:
            valid_recipients = []
            for email in recipients:
                is_allowed, reason = check_recipient_allowlist(email, allowlist)
                if is_allowed:
                    valid_recipients.append(email)
                else:
                    excluded.append(
                        {"email": email, "reason": reason or "Not in allowlist"}
                    )

            if not valid_recipients:
                return False, "All recipients blocked by allowlist", excluded
            recipients = valid_recipients

    # Rate/volume guards
    max_recipients = int(os.environ.get("EMAIL_MAX_RECIPIENTS", "100"))
    if len(recipients) > max_recipients:
        return (
            False,
            f"Recipient count ({len(recipients)}) exceeds maximum ({max_recipients})",
            excluded,
        )

    return True, None, excluded


def render_template(template: EmailTemplate, context: Dict) -> Tuple[str, str, str]:
    """
    Render email template with context.

    Args:
        template: EmailTemplate instance
        context: Dictionary of template variables

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    subject = template.subject_template
    html_body = template.html_template
    text_body = template.text_template

    # Simple placeholder replacement ({{key}})
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        value_str = str(value) if value is not None else ""
        subject = subject.replace(placeholder, value_str)
        html_body = html_body.replace(placeholder, value_str)
        text_body = text_body.replace(placeholder, value_str)

    return subject, html_body, text_body


def validate_template_rendering(
    template: EmailTemplate, context: Dict
) -> Tuple[bool, List[str]]:
    """
    Validate that template rendering has no missing placeholders.

    Args:
        template: EmailTemplate instance
        context: Dictionary of template variables

    Returns:
        Tuple of (is_valid, list_of_missing_placeholders)
    """
    subject, html_body, text_body = render_template(template, context)

    missing = []
    placeholder_pattern = r"\{\{(\w+)\}\}"

    for content, name in [
        (subject, "subject"),
        (html_body, "html_body"),
        (text_body, "text_body"),
    ]:
        matches = re.findall(placeholder_pattern, content)
        if matches:
            missing.extend([f"{name}:{match}" for match in matches])

    return len(missing) == 0, missing


def run_quality_checks(message: EmailMessage) -> Dict:
    """
    Run quality checks on email message.

    Args:
        message: EmailMessage instance

    Returns:
        Dictionary of quality check results
    """
    checks = {
        "recipient_count": message.recipient_count,
        "recipient_validation": {"passed": True, "issues": []},
        "template_validation": {"passed": True, "issues": []},
        "context_completeness": {"passed": True, "issues": []},
        "allowlist_compliance": {"passed": True, "issues": []},
    }

    # Recipient validation
    if message.recipient_count == 0:
        checks["recipient_validation"]["passed"] = False
        checks["recipient_validation"]["issues"].append("No recipients")

    # Excluded recipients check
    if message.excluded_recipients:
        checks["recipient_validation"]["passed"] = False
        checks["recipient_validation"]["issues"].extend(
            [f"{ex['email']}: {ex['reason']}" for ex in message.excluded_recipients]
        )

    # Template validation (check for missing placeholders)
    if message.template:
        # This would need the original context, so we'll just check if rendered content exists
        if not message.subject or not message.html_body or not message.text_body:
            checks["template_validation"]["passed"] = False
            checks["template_validation"]["issues"].append("Missing rendered content")

    # Context completeness (template-specific)
    if message.template and message.template.required_placeholders:
        context = message.context_metadata or {}
        missing_context = [
            key for key in message.template.required_placeholders if key not in context
        ]
        if missing_context:
            checks["context_completeness"]["passed"] = False
            checks["context_completeness"]["issues"].append(
                f"Missing context: {', '.join(missing_context)}"
            )

    # Allowlist compliance
    if not is_production_environment():
        allowlist = get_email_allowlist()
        if allowlist:
            for recipient in message.recipients:
                is_allowed, reason = check_recipient_allowlist(recipient, allowlist)
                if not is_allowed:
                    checks["allowlist_compliance"]["passed"] = False
                    checks["allowlist_compliance"]["issues"].append(
                        f"{recipient}: {reason}"
                    )

    # Calculate quality score (0-100)
    passed_checks = sum(
        1
        for check in checks.values()
        if isinstance(check, dict) and check.get("passed", False)
    )
    total_checks = sum(1 for check in checks.values() if isinstance(check, dict))
    quality_score = int((passed_checks / total_checks * 100)) if total_checks > 0 else 0

    checks["quality_score"] = quality_score
    return checks


def create_email_message(
    template: EmailTemplate,
    recipients: List[str],
    context: Dict,
    created_by_id: int,
    status: EmailMessageStatus = EmailMessageStatus.DRAFT,
) -> EmailMessage:
    """
    Create an email message with quality checks.

    Args:
        template: EmailTemplate instance
        recipients: List of recipient email addresses
        context: Template context dictionary
        created_by_id: User ID who created the message
        status: Initial status (default: DRAFT)

    Returns:
        EmailMessage instance

    Raises:
        EmailQualityError: If quality checks fail
    """
    # Validate and deduplicate recipients
    valid_recipients, excluded = validate_recipients(recipients)

    # Render template
    subject, html_body, text_body = render_template(template, context)

    # Validate template rendering
    is_valid, missing = validate_template_rendering(template, context)
    if not is_valid:
        raise EmailQualityError(
            f"Template has missing placeholders: {', '.join(missing)}"
        )

    # Create message
    message = EmailMessage(
        template_id=template.id,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        recipients=valid_recipients,
        recipient_count=len(valid_recipients),
        excluded_recipients=excluded if excluded else None,
        status=status,
        context_metadata=context,
        created_by_id=created_by_id,
    )

    # Run quality checks
    quality_checks = run_quality_checks(message)
    message.quality_checks = quality_checks
    message.quality_score = quality_checks.get("quality_score", 0)

    # If quality score is too low, set status to BLOCKED
    if message.quality_score < 50 and status == EmailMessageStatus.QUEUED:
        message.status = EmailMessageStatus.BLOCKED

    db.session.add(message)
    db.session.flush()  # Get message ID

    return message


def send_email_via_mailjet(
    message: EmailMessage, is_dry_run: bool = False
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Send email via Mailjet API.

    Args:
        message: EmailMessage instance
        is_dry_run: Whether this is a dry-run (no actual delivery)

    Returns:
        Tuple of (success, error_message, mailjet_response)
    """
    if is_dry_run:
        return (
            True,
            None,
            {"dry_run": True, "message": "Dry-run mode, no actual delivery"},
        )

    client = get_mailjet_client()
    if not client:
        return False, "Mailjet credentials not configured", None

    # Check safety gates
    is_allowed, error_msg, excluded = check_safety_gates(
        message.recipients, is_dry_run=is_dry_run
    )
    if not is_allowed:
        return False, error_msg, None

    # Prepare Mailjet payload
    mail_from = os.environ.get("MAIL_FROM", "noreply@example.com")
    mail_from_name = os.environ.get("MAIL_FROM_NAME", "VMS System")

    data = {
        "Messages": [
            {
                "From": {"Email": mail_from, "Name": mail_from_name},
                "To": [{"Email": email} for email in message.recipients],
                "Subject": message.subject,
                "TextPart": message.text_body,
                "HTMLPart": message.html_body,
            }
        ]
    }

    # Add SandboxMode if in non-production
    if not is_production_environment():
        data["Messages"][0]["SandboxMode"] = True

    try:
        result = client.send.create(data=data)
        response_json = result.json() if hasattr(result, "json") else {}

        if result.status_code == 200:
            # Extract Mailjet message ID
            mailjet_message_id = None
            if "Messages" in response_json and len(response_json["Messages"]) > 0:
                mailjet_message_id = (
                    response_json["Messages"][0].get("To", [{}])[0].get("MessageID")
                )

            return (
                True,
                None,
                {
                    "status_code": result.status_code,
                    "response": response_json,
                    "message_id": mailjet_message_id,
                },
            )
        else:
            error_msg = f"Mailjet API error: {result.status_code}"
            if "Messages" in response_json:
                error_details = response_json["Messages"][0].get("Errors", [])
                if error_details:
                    error_msg = f"{error_msg} - {error_details[0].get('ErrorMessage', 'Unknown error')}"
            return (
                False,
                error_msg,
                {"status_code": result.status_code, "response": response_json},
            )

    except Exception as e:
        return False, f"Mailjet API exception: {str(e)}", None


def create_delivery_attempt(
    message: EmailMessage, is_dry_run: bool = False
) -> EmailDeliveryAttempt:
    """
    Create and execute a delivery attempt for an email message.

    Args:
        message: EmailMessage instance
        is_dry_run: Whether this is a dry-run

    Returns:
        EmailDeliveryAttempt instance
    """
    attempt = EmailDeliveryAttempt(
        message_id=message.id,
        status=DeliveryAttemptStatus.PENDING,
        is_dry_run=is_dry_run,
    )

    db.session.add(attempt)
    db.session.flush()

    # Send via Mailjet
    success, error_message, mailjet_response = send_email_via_mailjet(
        message, is_dry_run=is_dry_run
    )

    # Update attempt status
    if success:
        attempt.status = (
            DeliveryAttemptStatus.DRY_RUN
            if is_dry_run
            else DeliveryAttemptStatus.SUCCESS
        )
        if mailjet_response and "message_id" in mailjet_response:
            attempt.mailjet_message_id = mailjet_response["message_id"]
    else:
        attempt.status = DeliveryAttemptStatus.FAILED
        attempt.error_message = error_message
        if mailjet_response:
            attempt.error_details = mailjet_response

    # Store provider payload summary (no secrets)
    attempt.provider_payload_summary = {
        "recipient_count": len(message.recipients),
        "subject": message.subject[:100],  # Truncate for storage
        "has_html": bool(message.html_body),
        "has_text": bool(message.text_body),
    }

    attempt.completed_at = datetime.now(timezone.utc)
    attempt.mailjet_response = mailjet_response

    # Update message status
    if success and not is_dry_run:
        message.status = EmailMessageStatus.SENT
        message.sent_at = datetime.now(timezone.utc)
    elif not success:
        message.status = EmailMessageStatus.FAILED
        # Create BugReport for delivery failure
        create_delivery_failure_bug_report(message, attempt)

    message.status_updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return attempt


def create_delivery_failure_bug_report(
    message: EmailMessage, attempt: EmailDeliveryAttempt
):
    """
    Create a BugReport entry for email delivery failure.

    Args:
        message: EmailMessage instance
        attempt: EmailDeliveryAttempt instance
    """
    # Find system user or use a default
    from models.user import User

    system_user = User.query.filter_by(email="system@vms.local").first()
    if not system_user:
        # Create a system user if it doesn't exist (or use first admin)
        system_user = User.query.filter_by(security_level=3).first()
        if not system_user:
            return  # Can't create bug report without a user

    description = f"""SYSTEM_ALERT: EMAIL_DELIVERY_FAILED

Email Message ID: {message.id}
Template: {message.template.purpose_key if message.template else 'Unknown'}
Recipients: {', '.join(message.recipients[:5])}{'...' if len(message.recipients) > 5 else ''}
Error: {attempt.error_message or 'Unknown error'}

Delivery Attempt ID: {attempt.id}
Attempted At: {attempt.attempted_at.isoformat() if attempt.attempted_at else 'N/A'}
"""

    bug_report = BugReport(
        type=BugReportType.OTHER,
        description=description,
        page_url="/management/email/outbox",
        page_title="Email Outbox",
        submitted_by_id=system_user.id,
    )

    db.session.add(bug_report)
    # Don't commit here - let the caller commit


def queue_message_for_delivery(message_id: int) -> EmailMessage:
    """
    Queue an email message for delivery.

    Args:
        message_id: EmailMessage ID

    Returns:
        EmailMessage instance
    """
    message = EmailMessage.query.get_or_404(message_id)

    if message.status != EmailMessageStatus.DRAFT:
        raise ValueError(
            f"Message {message_id} is not in DRAFT status (current: {EmailMessageStatus(message.status).name})"
        )

    message.status = EmailMessageStatus.QUEUED
    message.queued_at = datetime.now(timezone.utc)
    message.status_updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return message

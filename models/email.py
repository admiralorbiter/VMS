"""
Email Models Module
==================

This module defines models for managing email templates, messages, and delivery
attempts in the VMS system. It provides a safe-by-default email system with
comprehensive tracking and audit capabilities.

Key Features:
- Email template versioning and management
- Two-phase email sending (draft → queued → sent)
- Delivery attempt tracking with provider integration
- Quality checks and safety gates
- Recipient allowlist enforcement
- Comprehensive audit trails

Database Tables:
- email_templates: Versioned email templates (HTML + text)
- email_messages: Outbox records for email intents
- email_delivery_attempts: Individual delivery attempts to the provider

Email Lifecycle:
- DRAFT: Message created but not queued
- QUEUED: Message queued for delivery
- SENT: Successfully delivered
- FAILED: Delivery failed
- BLOCKED: Blocked by safety gates
- CANCELLED: Manually cancelled

Safety Features:
- Environment-based delivery gates
- Recipient allowlist enforcement
- Rate limiting and volume caps
- Quality validation before sending
"""

from datetime import datetime, timezone
from enum import IntEnum
from typing import Dict

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import db


class EmailMessageStatus(IntEnum):
    """Status enum for email message lifecycle."""

    DRAFT = 0  # Created but not queued
    QUEUED = 1  # Queued for delivery
    SENT = 2  # Successfully delivered
    FAILED = 3  # Delivery failed
    BLOCKED = 4  # Blocked by safety gates
    CANCELLED = 5  # Manually cancelled


class DeliveryAttemptStatus(IntEnum):
    """Status enum for individual delivery attempts."""

    PENDING = 0  # Attempt created but not sent
    SUCCESS = 1  # Successfully sent to provider
    FAILED = 2  # Provider rejected or error
    DRY_RUN = 3  # Dry-run mode (no actual delivery)


class EmailTemplate(db.Model):
    """
    Email template model for versioned email templates.

    Templates are versioned by purpose_key and version number, allowing
    multiple versions of the same template to exist for rollback capability.

    Database Table:
        email_templates - Stores email template definitions

    Key Features:
        - Versioned templates with purpose keys
        - HTML and text versions
        - Placeholder validation
        - Template preview capability
    """

    __tablename__ = "email_templates"

    id = db.Column(Integer, primary_key=True)
    purpose_key = db.Column(String(100), nullable=False, index=True)
    version = db.Column(Integer, nullable=False, default=1)
    name = db.Column(String(200), nullable=False)
    description = db.Column(Text)

    # Template content
    subject_template = db.Column(Text, nullable=False)
    html_template = db.Column(Text, nullable=False)
    text_template = db.Column(Text, nullable=False)

    # Template metadata
    required_placeholders = db.Column(
        JSON, nullable=True
    )  # List of required placeholder keys
    optional_placeholders = db.Column(
        JSON, nullable=True
    )  # List of optional placeholder keys

    # Versioning and lifecycle
    is_active = db.Column(Boolean, default=True, nullable=False)
    created_at = db.Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_by_id = db.Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Relationships
    messages = relationship("EmailMessage", back_populates="template", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.purpose_key} v{self.version}>"

    def to_dict(self) -> Dict:
        """Convert template to dictionary for API responses."""
        return {
            "id": self.id,
            "purpose_key": self.purpose_key,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by.username if self.created_by else None,
        }


class EmailMessage(db.Model):
    """
    Email message (outbox) model for tracking email intents.

    This model represents an immutable intent to send an email. All email
    sends go through this model, providing full auditability and safety.

    Database Table:
        email_messages - Stores email message intents and metadata

    Key Features:
        - Immutable message records
        - Template versioning tracking
        - Rendered content storage
        - Recipient tracking with exclusions
        - Quality check results
        - Context metadata (district, teacher, bug_report, etc.)
        - Status lifecycle management
    """

    __tablename__ = "email_messages"

    id = db.Column(Integer, primary_key=True)
    template_id = db.Column(Integer, ForeignKey("email_templates.id"), nullable=False)
    template = relationship("EmailTemplate", back_populates="messages")

    # Rendered content (immutable once set)
    subject = db.Column(Text, nullable=False)
    html_body = db.Column(Text, nullable=False)
    text_body = db.Column(Text, nullable=False)

    # Recipients
    recipients = db.Column(JSON, nullable=False)  # List of email addresses
    recipient_count = db.Column(Integer, nullable=False, default=0)
    excluded_recipients = db.Column(
        JSON, nullable=True
    )  # List of {email, reason} dicts

    # Status and lifecycle
    status = db.Column(
        Integer, default=EmailMessageStatus.DRAFT, nullable=False, index=True
    )
    status_updated_at = db.Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Quality check results
    quality_checks = db.Column(JSON, nullable=True)  # Dict of check results
    quality_score = db.Column(Integer, nullable=True)  # Overall quality score (0-100)

    # Context metadata (for linking to other resources)
    context_metadata = db.Column(
        JSON, nullable=True
    )  # Dict with district, teacher_id, bug_report_id, etc.

    # User tracking
    created_by_id = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Timestamps
    created_at = db.Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    queued_at = db.Column(DateTime(timezone=True), nullable=True)
    sent_at = db.Column(DateTime(timezone=True), nullable=True)

    # Relationships
    delivery_attempts = relationship(
        "EmailDeliveryAttempt",
        back_populates="message",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<EmailMessage {self.id} {EmailMessageStatus(self.status).name}>"

    def to_dict(self) -> Dict:
        """Convert message to dictionary for API responses."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "template_purpose_key": (
                self.template.purpose_key if self.template else None
            ),
            "subject": self.subject,
            "recipient_count": self.recipient_count,
            "status": EmailMessageStatus(self.status).name,
            "status_updated_at": (
                self.status_updated_at.isoformat() if self.status_updated_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by.username if self.created_by else None,
            "quality_score": self.quality_score,
        }


class EmailDeliveryAttempt(db.Model):
    """
    Email delivery attempt model for tracking individual provider API calls.

    Each attempt to send an email through the provider is recorded here, providing
    full traceability of delivery attempts, failures, and provider responses.

    Database Table:
        email_delivery_attempts - Stores individual delivery attempts

    Key Features:
        - Individual attempt tracking
        - Provider response ID storage
        - Error message and details
        - Status tracking
        - Provider payload summary (no secrets)
        - Timestamp tracking
    """

    __tablename__ = "email_delivery_attempts"

    id = db.Column(Integer, primary_key=True)
    message_id = db.Column(Integer, ForeignKey("email_messages.id"), nullable=False)
    message = relationship("EmailMessage", back_populates="delivery_attempts")

    # Status
    status = db.Column(
        Integer, default=DeliveryAttemptStatus.PENDING, nullable=False, index=True
    )

    # Provider response
    provider_message_id = db.Column(
        String(100), nullable=True, index=True
    )  # Provider's message ID
    provider_response = db.Column(JSON, nullable=True)  # Full API response (sanitized)

    # Error tracking
    error_message = db.Column(Text, nullable=True)
    error_details = db.Column(JSON, nullable=True)  # Structured error details

    # Provider payload summary (for debugging, no secrets)
    provider_payload_summary = db.Column(
        JSON, nullable=True
    )  # Summary of what was sent (no API keys)

    # Timestamps
    attempted_at = db.Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    completed_at = db.Column(DateTime(timezone=True), nullable=True)

    # Dry-run flag
    is_dry_run = db.Column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<EmailDeliveryAttempt {self.id} {DeliveryAttemptStatus(self.status).name}>"

    def to_dict(self) -> Dict:
        """Convert attempt to dictionary for API responses."""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "status": DeliveryAttemptStatus(self.status).name,
            "provider_message_id": self.provider_message_id,
            "error_message": self.error_message,
            "attempted_at": (
                self.attempted_at.isoformat() if self.attempted_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "is_dry_run": self.is_dry_run,
        }


class BatchEmailJobStatus(IntEnum):
    """Status enum for batch email job lifecycle.

    State machine:
        DRAFT → CANARY_SENT → CONFIRMED → COMPLETED
                    ↓              ↓
               CANCELLED      CANCELLED
                (timeout)      (manual)
    """

    DRAFT = 0  # Job created, under review
    CANARY_SENT = 1  # Canary email sent, cooldown timer started
    CONFIRMED = 2  # Confirmation code entered, batch sending in progress
    COMPLETED = 3  # All emails sent successfully
    CANCELLED = 4  # Cancelled (manual, timeout, or error)
    FAILED = 5  # Fatal error during batch send


class BatchEmailJob(db.Model):
    """
    Batch email job model for safe, multi-gate bulk email sending.

    Implements a 5-gate safety system:
        1. Create (DRAFT) — preview recipients + rendered email
        2. Review — explicit "Send Canary" click required
        3. Canary (CANARY_SENT) — ONE email to test address
        4. Cooldown — auto-cancel if no confirmation within deadline
        5. Confirm (CONFIRMED) — enter confirmation code to start batch

    Database Table:
        batch_email_jobs - Stores batch job state and progress

    Key Safety Features:
        - Dead man's switch (auto-cancel on timeout)
        - Random confirmation code prevents accidental clicks
        - Canary email for visual verification before batch
        - Full audit trail of every state transition
    """

    __tablename__ = "batch_email_jobs"

    id = db.Column(Integer, primary_key=True)
    template_id = db.Column(Integer, ForeignKey("email_templates.id"), nullable=False)
    template = relationship("EmailTemplate", foreign_keys=[template_id])

    # Job status
    status = db.Column(
        Integer, default=BatchEmailJobStatus.DRAFT, nullable=False, index=True
    )

    # Safety gates
    confirmation_code = db.Column(
        String(10), nullable=False
    )  # Random code (e.g., "A3X9K2")
    canary_email = db.Column(
        String(255), nullable=False
    )  # Test address for canary send
    cooldown_minutes = db.Column(
        Integer, nullable=False, default=10
    )  # Minutes before auto-cancel

    # Timing
    created_at = db.Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    canary_sent_at = db.Column(DateTime(timezone=True), nullable=True)
    expires_at = db.Column(
        DateTime(timezone=True), nullable=True
    )  # Auto-cancel deadline
    confirmed_at = db.Column(DateTime(timezone=True), nullable=True)
    completed_at = db.Column(DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(DateTime(timezone=True), nullable=True)
    cancel_reason = db.Column(String(50), nullable=True)  # "manual", "timeout", "error"

    # Batch context
    district_name = db.Column(
        String(255), nullable=False, default="Kansas City Kansas Public Schools"
    )
    tenant_id = db.Column(Integer, nullable=True)
    context_data = db.Column(JSON, nullable=True)  # Shared template context overrides

    # Progress tracking
    total_recipients = db.Column(Integer, nullable=False, default=0)
    sent_count = db.Column(Integer, nullable=False, default=0)
    skipped_count = db.Column(Integer, nullable=False, default=0)
    error_count = db.Column(Integer, nullable=False, default=0)

    # Audit
    created_by_id = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<BatchEmailJob {self.id} " f"{BatchEmailJobStatus(self.status).name}>"

    @property
    def is_expired(self) -> bool:
        """Check if the cooldown timer has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def seconds_remaining(self) -> int:
        """Seconds remaining before auto-cancel. Returns 0 if expired."""
        if self.expires_at is None:
            return 0
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

    def to_dict(self) -> Dict:
        """Convert job to dictionary for API responses."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "status": BatchEmailJobStatus(self.status).name,
            "confirmation_code": self.confirmation_code,
            "canary_email": self.canary_email,
            "cooldown_minutes": self.cooldown_minutes,
            "district_name": self.district_name,
            "total_recipients": self.total_recipients,
            "sent_count": self.sent_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "is_expired": self.is_expired,
            "seconds_remaining": self.seconds_remaining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "canary_sent_at": (
                self.canary_sent_at.isoformat() if self.canary_sent_at else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "confirmed_at": (
                self.confirmed_at.isoformat() if self.confirmed_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "cancelled_at": (
                self.cancelled_at.isoformat() if self.cancelled_at else None
            ),
            "cancel_reason": self.cancel_reason,
        }

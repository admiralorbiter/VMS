"""
Outreach Model for District Recruitment

Tracks recruitment outreach attempts to volunteers for events.
Supports FR-SELFSERV-403: District staff shall be able to log outreach
attempts and track outcomes.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text

from models import db


class OutreachAttempt(db.Model):
    """
    Log of recruitment outreach attempts (FR-SELFSERV-403).

    Tracks attempts to contact volunteers for event recruitment,
    including the method used, outcome, and any notes.
    """

    __tablename__ = "outreach_attempt"

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey("volunteer.id"), nullable=False)
    event_id = db.Column(Integer, ForeignKey("event.id"), nullable=False)
    tenant_id = db.Column(Integer, ForeignKey("tenant.id"), nullable=False)

    # Outreach details
    method = db.Column(String(20), nullable=False)  # email, phone, text, in_person
    outcome = db.Column(
        String(20), default="pending"
    )  # pending, no_response, interested, declined, confirmed
    notes = db.Column(Text)

    # Timestamps
    attempted_at = db.Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    followed_up_at = db.Column(DateTime(timezone=True))
    attempted_by_id = db.Column(Integer, ForeignKey("users.id"))

    # Relationships
    volunteer = db.relationship(
        "Volunteer",
        backref=db.backref("outreach_attempts", lazy="dynamic"),
    )
    event = db.relationship(
        "Event",
        backref=db.backref("outreach_attempts", lazy="dynamic"),
    )
    tenant = db.relationship(
        "Tenant",
        backref=db.backref("outreach_attempts", lazy="dynamic"),
    )
    attempted_by = db.relationship(
        "User",
        backref=db.backref("outreach_attempts", lazy="dynamic"),
        foreign_keys=[attempted_by_id],
    )

    # Method options
    METHOD_CHOICES = [
        ("email", "Email"),
        ("phone", "Phone Call"),
        ("text", "Text Message"),
        ("in_person", "In Person"),
    ]

    # Outcome options
    OUTCOME_CHOICES = [
        ("pending", "Pending"),
        ("no_response", "No Response"),
        ("interested", "Interested"),
        ("declined", "Declined"),
        ("confirmed", "Confirmed"),
    ]

    def __repr__(self):
        return f"<OutreachAttempt {self.id}: v{self.volunteer_id}→e{self.event_id} {self.method}:{self.outcome}>"

    @classmethod
    def log_attempt(
        cls,
        volunteer_id,
        event_id,
        tenant_id,
        method,
        outcome="pending",
        notes=None,
        attempted_by_id=None,
    ):
        """
        Create a new outreach attempt record.

        Args:
            volunteer_id: ID of the volunteer being contacted
            event_id: ID of the event for recruitment
            tenant_id: ID of the tenant
            method: Contact method (email, phone, text, in_person)
            outcome: Result of outreach (default: pending)
            notes: Optional notes about the attempt
            attempted_by_id: User ID who made the attempt

        Returns:
            OutreachAttempt instance
        """
        attempt = cls(
            volunteer_id=volunteer_id,
            event_id=event_id,
            tenant_id=tenant_id,
            method=method,
            outcome=outcome,
            notes=notes,
            attempted_by_id=attempted_by_id,
        )
        db.session.add(attempt)
        db.session.commit()
        return attempt

    def update_outcome(self, outcome, notes=None):
        """Update the outcome of an outreach attempt."""
        self.outcome = outcome
        if notes:
            self.notes = notes
        self.followed_up_at = datetime.now(timezone.utc)
        db.session.commit()

    @classmethod
    def get_history(cls, volunteer_id, event_id, tenant_id):
        """Get all outreach attempts for a volunteer/event pair."""
        return (
            cls.query.filter_by(
                volunteer_id=volunteer_id,
                event_id=event_id,
                tenant_id=tenant_id,
            )
            .order_by(cls.attempted_at.desc())
            .all()
        )

    @classmethod
    def get_event_outreach(cls, event_id, tenant_id):
        """Get all outreach attempts for an event."""
        return (
            cls.query.filter_by(
                event_id=event_id,
                tenant_id=tenant_id,
            )
            .order_by(cls.attempted_at.desc())
            .all()
        )

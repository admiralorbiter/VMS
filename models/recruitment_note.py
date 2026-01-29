"""
Recruitment Note Model for Volunteer Profiles

Tracks recruitment notes and outcomes per FR-RECRUIT-306 / US-403.
Enables staff to record recruitment-related notes with outcomes
and view them in chronological order.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text

from models import db


class RecruitmentOutcome(PyEnum):
    """Outcome choices for recruitment notes."""

    NO_OUTCOME = "no_outcome"
    INTERESTED = "interested"
    FOLLOW_UP = "follow_up"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class RecruitmentNote(db.Model):
    """
    Recruitment note associated with a volunteer (FR-RECRUIT-306).

    Tracks recruitment outreach notes and outcomes for a volunteer
    within a tenant context. Notes are displayed in chronological order
    on the volunteer profile.
    """

    __tablename__ = "recruitment_note"

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(
        Integer, ForeignKey("volunteer.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id = db.Column(
        Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=True
    )

    # Note content
    note = db.Column(Text, nullable=False)
    outcome = db.Column(
        String(20), default=RecruitmentOutcome.NO_OUTCOME.value, nullable=False
    )

    # Audit fields
    created_by = db.Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    volunteer = db.relationship(
        "Volunteer",
        backref=db.backref(
            "recruitment_notes", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    tenant = db.relationship(
        "Tenant",
        backref=db.backref(
            "recruitment_notes", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    created_by_user = db.relationship(
        "User",
        backref=db.backref("recruitment_notes_created", lazy="dynamic"),
        foreign_keys=[created_by],
    )

    # Outcome display choices
    OUTCOME_CHOICES = [
        (RecruitmentOutcome.NO_OUTCOME.value, "No Outcome"),
        (RecruitmentOutcome.INTERESTED.value, "Interested"),
        (RecruitmentOutcome.FOLLOW_UP.value, "Follow-up Needed"),
        (RecruitmentOutcome.ACCEPTED.value, "Accepted"),
        (RecruitmentOutcome.DECLINED.value, "Declined"),
    ]

    def __repr__(self):
        return f"<RecruitmentNote {self.id}: vol={self.volunteer_id} outcome={self.outcome}>"

    @property
    def outcome_label(self):
        """Get the display label for the outcome."""
        outcome_labels = {
            "general": "General Note",
            "no_outcome": "No Outcome",
            "interested": "Interested",
            "not_interested": "Not Interested",
            "callback": "Callback Requested",
            "no_answer": "No Answer",
            "left_message": "Left Message",
            "scheduled": "Scheduled",
            "follow_up": "Follow-up Needed",
            "accepted": "Accepted",
            "declined": "Declined",
        }
        return outcome_labels.get(
            self.outcome,
            self.outcome.replace("_", " ").title() if self.outcome else "Unknown",
        )

    @classmethod
    def create_note(cls, volunteer_id, tenant_id, note, outcome=None, created_by=None):
        """
        Create a new recruitment note.

        Args:
            volunteer_id: ID of the volunteer
            tenant_id: ID of the tenant/district
            note: Note text content
            outcome: Optional outcome value
            created_by: User ID of staff member

        Returns:
            RecruitmentNote instance
        """
        recruitment_note = cls(
            volunteer_id=volunteer_id,
            tenant_id=tenant_id,
            note=note,
            outcome=outcome or RecruitmentOutcome.NO_OUTCOME.value,
            created_by=created_by,
        )
        db.session.add(recruitment_note)
        db.session.commit()
        return recruitment_note

    @classmethod
    def get_for_volunteer(cls, volunteer_id, tenant_id):
        """
        Get all recruitment notes for a volunteer within a tenant.

        Returns notes in reverse chronological order.
        """
        return (
            cls.query.filter_by(volunteer_id=volunteer_id, tenant_id=tenant_id)
            .order_by(cls.created_at.desc())
            .all()
        )

    def to_dict(self):
        """Convert to dictionary for JSON responses."""
        created_by_display = None
        if self.created_by_user:
            if self.created_by_user.first_name or self.created_by_user.last_name:
                created_by_display = f"{self.created_by_user.first_name or ''} {self.created_by_user.last_name or ''}".strip()
            else:
                created_by_display = self.created_by_user.email

        return {
            "id": self.id,
            "note": self.note,
            "outcome": self.outcome,
            "outcome_label": dict(self.OUTCOME_CHOICES).get(self.outcome, "Unknown"),
            "created_by": created_by_display,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

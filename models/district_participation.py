"""
District Participation Model Module
===================================

This module defines the DistrictParticipation model for tracking volunteer
assignments to district events with status management.

Key Features:
- Tenant-scoped event participation tracking
- Status workflow (invited -> confirmed/declined -> attended)
- Participation type categorization
- Audit trail for invitation workflow

Database Table:
- district_participation: Event assignment and status tracking

Relationships:
- Many-to-one with Volunteer (the participant)
- Many-to-one with Event (the district event)
- Many-to-one with Tenant (ensures tenant isolation)
- Many-to-one with User (invited_by audit trail)

Usage Examples:
    # Invite volunteer to event
    dp = DistrictParticipation(
        volunteer_id=volunteer.id,
        event_id=event.id,
        tenant_id=tenant.id,
        invited_by=current_user.id,
        participation_type='volunteer'
    )
    db.session.add(dp)

    # Track confirmation
    dp.confirm()
    db.session.commit()
"""

from datetime import datetime, timezone

from models import db


class DistrictParticipation(db.Model):
    """
    Volunteer assignment to district events with status tracking.

    This model tracks the lifecycle of a volunteer's participation in a
    district event, from invitation through attendance confirmation.

    Database Table:
        district_participation - Event participation records

    Key Features:
        - Status workflow: invited -> confirmed/declined -> attended/no_show
        - Participation types: volunteer, speaker, mentor, etc.
        - Tenant isolation ensures districts only see their events
        - Audit trail tracks invitation and confirmation times

    Attributes:
        id: Primary key
        volunteer_id: FK to Volunteer
        event_id: FK to Event
        tenant_id: FK to Tenant (for isolation)
        status: Participation status
        participation_type: Role type (volunteer, speaker, mentor)
        invited_by: FK to User who invited
        invited_at: Invitation timestamp
        confirmed_at: Confirmation timestamp
        notes: Assignment notes
    """

    __tablename__ = "district_participation"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    volunteer_id = db.Column(
        db.Integer,
        db.ForeignKey("volunteer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the volunteer",
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the event",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to tenant for isolation",
    )

    # Status
    status = db.Column(
        db.String(20),
        default="invited",
        nullable=False,
        comment="Status: invited, confirmed, declined, attended, no_show",
    )

    # Participation type
    participation_type = db.Column(
        db.String(50),
        default="volunteer",
        nullable=True,
        comment="Role type: volunteer, speaker, mentor, facilitator",
    )

    # Audit fields
    invited_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who invited the volunteer",
    )
    invited_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    confirmed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        comment="When volunteer confirmed",
    )
    attended_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        comment="When attendance was recorded",
    )

    # Notes
    notes = db.Column(
        db.Text,
        nullable=True,
        comment="Assignment notes",
    )

    # Prevent duplicate volunteer-event assignments within tenant
    __table_args__ = (
        db.UniqueConstraint(
            "volunteer_id",
            "event_id",
            "tenant_id",
            name="uq_district_participation_vol_event_tenant",
        ),
    )

    # Relationships
    volunteer = db.relationship(
        "Volunteer",
        backref=db.backref(
            "district_participations", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    event = db.relationship(
        "Event",
        backref=db.backref(
            "district_participations", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    tenant = db.relationship(
        "Tenant",
        backref=db.backref(
            "district_participations", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    invited_by_user = db.relationship(
        "User",
        backref=db.backref("invited_participations", lazy="dynamic"),
        foreign_keys=[invited_by],
    )

    # Status constants
    STATUS_INVITED = "invited"
    STATUS_CONFIRMED = "confirmed"
    STATUS_DECLINED = "declined"
    STATUS_ATTENDED = "attended"
    STATUS_NO_SHOW = "no_show"

    # Participation type constants
    TYPE_VOLUNTEER = "volunteer"
    TYPE_SPEAKER = "speaker"
    TYPE_MENTOR = "mentor"
    TYPE_FACILITATOR = "facilitator"

    @classmethod
    def get_for_event(cls, event_id, tenant_id, status=None):
        """
        Get all participants for an event within a tenant.

        Args:
            event_id: Event ID to filter by
            tenant_id: Tenant ID for isolation
            status: Optional status filter

        Returns:
            Query object for participants
        """
        query = cls.query.filter_by(event_id=event_id, tenant_id=tenant_id)
        if status:
            query = query.filter_by(status=status)
        return query

    @classmethod
    def get_for_volunteer(cls, volunteer_id, tenant_id):
        """
        Get all participations for a volunteer within a tenant.

        Args:
            volunteer_id: Volunteer ID to filter by
            tenant_id: Tenant ID for isolation

        Returns:
            Query object for participations
        """
        return cls.query.filter_by(volunteer_id=volunteer_id, tenant_id=tenant_id)

    def confirm(self):
        """Mark participation as confirmed."""
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)

    def decline(self):
        """Mark participation as declined."""
        self.status = self.STATUS_DECLINED

    def mark_attended(self):
        """Mark volunteer as attended."""
        self.status = self.STATUS_ATTENDED
        self.attended_at = datetime.now(timezone.utc)

    def mark_no_show(self):
        """Mark volunteer as no-show."""
        self.status = self.STATUS_NO_SHOW

    def __repr__(self):
        """String representation for debugging."""
        return f"<DistrictParticipation vol={self.volunteer_id} event={self.event_id} status={self.status}>"

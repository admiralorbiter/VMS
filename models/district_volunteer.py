"""
District Volunteer Model Module
==============================

This module defines the DistrictVolunteer model for tracking volunteer
membership within specific tenant organizations.

Key Features:
- Many-to-many association between Volunteer and Tenant
- District-specific volunteer status tracking
- Audit trail for volunteer additions
- Duplicate prevention via unique constraint

Database Table:
- district_volunteer: Tenant-scoped volunteer membership

Relationships:
- Many-to-one with Volunteer (the actual volunteer record)
- Many-to-one with Tenant (the district organization)
- Many-to-one with User (added_by audit trail)

Usage Examples:
    # Add volunteer to district
    dv = DistrictVolunteer(
        volunteer_id=volunteer.id,
        tenant_id=tenant.id,
        added_by=current_user.id
    )
    db.session.add(dv)

    # Get all volunteers for a tenant
    volunteers = DistrictVolunteer.query.filter_by(
        tenant_id=tenant.id,
        status='active'
    ).all()
"""

from datetime import datetime, timezone

from models import db


class DistrictVolunteer(db.Model):
    """
    Association between Volunteer and Tenant for tenant-scoped management.

    This model enables district administrators to manage their own volunteer
    pool without modifying the core Volunteer model used by PrepKC.

    Database Table:
        district_volunteer - Stores tenant-volunteer associations

    Key Features:
        - Status tracking (active/inactive)
        - Audit trail (who added, when)
        - District-specific notes
        - Unique constraint prevents duplicates

    Attributes:
        id: Primary key
        volunteer_id: FK to Volunteer
        tenant_id: FK to Tenant
        status: Membership status (active, inactive)
        added_by: FK to User who added the volunteer
        added_at: When volunteer was added to district
        notes: District-specific notes
    """

    __tablename__ = "district_volunteer"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    volunteer_id = db.Column(
        db.Integer,
        db.ForeignKey("volunteer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the volunteer record",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the tenant/district",
    )

    # Status
    status = db.Column(
        db.String(20),
        default="active",
        nullable=False,
        comment="Membership status: active, inactive",
    )

    # Audit fields
    added_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who added volunteer to district",
    )
    added_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # District-specific data
    notes = db.Column(
        db.Text,
        nullable=True,
        comment="District-specific notes about the volunteer",
    )

    # Prevent duplicate volunteer-tenant associations
    __table_args__ = (
        db.UniqueConstraint(
            "volunteer_id", "tenant_id", name="uq_district_volunteer_volunteer_tenant"
        ),
    )

    # Relationships
    volunteer = db.relationship(
        "Volunteer",
        backref=db.backref(
            "district_memberships", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    tenant = db.relationship(
        "Tenant",
        backref=db.backref(
            "district_volunteers", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    added_by_user = db.relationship(
        "User",
        backref=db.backref("added_district_volunteers", lazy="dynamic"),
        foreign_keys=[added_by],
    )

    # Status constants
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"

    @classmethod
    def get_for_tenant(cls, tenant_id, status=None):
        """
        Get all district volunteers for a tenant.

        Args:
            tenant_id: Tenant ID to filter by
            status: Optional status filter (active/inactive)

        Returns:
            Query object for district volunteers
        """
        query = cls.query.filter_by(tenant_id=tenant_id)
        if status:
            query = query.filter_by(status=status)
        return query

    @classmethod
    def add_volunteer_to_tenant(
        cls, volunteer_id, tenant_id, added_by=None, notes=None
    ):
        """
        Add a volunteer to a tenant's pool.

        Args:
            volunteer_id: ID of volunteer to add
            tenant_id: ID of tenant to add to
            added_by: User ID who is adding (optional)
            notes: Initial notes (optional)

        Returns:
            DistrictVolunteer instance (new or existing)

        Note:
            If volunteer is already in tenant (inactive), reactivates them.
        """
        existing = cls.query.filter_by(
            volunteer_id=volunteer_id,
            tenant_id=tenant_id,
        ).first()

        if existing:
            # Reactivate if inactive
            if existing.status == cls.STATUS_INACTIVE:
                existing.status = cls.STATUS_ACTIVE
                existing.added_at = datetime.now(timezone.utc)
                existing.added_by = added_by
            if notes:
                existing.notes = notes
            return existing

        # Create new association
        return cls(
            volunteer_id=volunteer_id,
            tenant_id=tenant_id,
            added_by=added_by,
            notes=notes,
        )

    def deactivate(self):
        """Mark volunteer as inactive in this tenant."""
        self.status = self.STATUS_INACTIVE

    def activate(self):
        """Mark volunteer as active in this tenant."""
        self.status = self.STATUS_ACTIVE

    def __repr__(self):
        """String representation for debugging."""
        return f"<DistrictVolunteer volunteer_id={self.volunteer_id} tenant_id={self.tenant_id} status={self.status}>"

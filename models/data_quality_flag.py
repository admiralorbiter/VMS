"""
Data Quality Flag Model
=======================

General-purpose flagging system for Salesforce data quality issues
detected during imports. Allows staff to review and optionally fix
issues in both the local DB and Salesforce.

Issue Types:
- all_caps_name: Contact name is ALL UPPERCASE
- null_org_type: Organization has no type classification
- missing_address: Contact address is empty/skeleton
- truncated_skill: Skill name was truncated at column limit
- other: Freeform data quality issue

Statuses:
- open: Needs review
- dismissed: Reviewed and accepted as-is
- fixed_in_sf: Corrected in Salesforce (will resolve on next import)
- auto_fixed: Automatically corrected during import
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import db


class DataQualityIssueType:
    """Constants for data quality issue types."""

    ALL_CAPS_NAME = "all_caps_name"
    NULL_ORG_TYPE = "null_org_type"
    MISSING_ADDRESS = "missing_address"
    TRUNCATED_SKILL = "truncated_skill"
    OTHER = "other"

    @classmethod
    def all_types(cls):
        return [
            cls.ALL_CAPS_NAME,
            cls.NULL_ORG_TYPE,
            cls.MISSING_ADDRESS,
            cls.TRUNCATED_SKILL,
            cls.OTHER,
        ]

    @classmethod
    def display_name(cls, issue_type):
        names = {
            cls.ALL_CAPS_NAME: "ALL CAPS Name",
            cls.NULL_ORG_TYPE: "Missing Org Type",
            cls.MISSING_ADDRESS: "Empty Address",
            cls.TRUNCATED_SKILL: "Truncated Skill",
            cls.OTHER: "Other",
        }
        return names.get(issue_type, issue_type)


class DataQualityFlag(db.Model):
    """
    Flags for data quality issues detected during Salesforce imports.

    Database Table:
        data_quality_flag
    """

    __tablename__ = "data_quality_flag"

    id = Column(Integer, primary_key=True)

    # What entity has the issue
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # 'contact', 'organization', 'volunteer'
    entity_id = Column(Integer, nullable=False, index=True)

    # Issue details
    issue_type = Column(String(50), nullable=False, index=True)
    details = Column(Text)  # Human-readable description
    salesforce_id = Column(
        String(18), nullable=True, index=True
    )  # SF record ID for cross-reference

    # Status tracking
    status = Column(
        String(20), default="open", nullable=False, index=True
    )  # open, dismissed, fixed_in_sf, auto_fixed

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(Integer, ForeignKey("users.id"))

    resolution_notes = Column(Text)

    # Relationships
    resolver = relationship("User", foreign_keys=[resolved_by])

    # Prevent duplicate flags for the same entity+issue
    __table_args__ = (
        db.UniqueConstraint(
            "entity_type",
            "entity_id",
            "issue_type",
            name="uix_dqf_entity_issue",
        ),
    )

    def resolve(self, status="dismissed", notes=None, resolved_by=None):
        """Mark this flag as resolved."""
        self.status = status
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        self.resolution_notes = notes

    @property
    def issue_type_display(self):
        return DataQualityIssueType.display_name(self.issue_type)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "issue_type": self.issue_type,
            "issue_type_display": self.issue_type_display,
            "details": self.details,
            "salesforce_id": self.salesforce_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
        }

    def __repr__(self):
        return (
            f"<DataQualityFlag {self.id}: {self.issue_type} "
            f"({self.status}) for {self.entity_type}:{self.entity_id}>"
        )


def flag_data_quality_issue(
    entity_type, entity_id, issue_type, details=None, salesforce_id=None
):
    """
    Create or update a data quality flag (idempotent).

    If a flag already exists for this entity+issue, it's left as-is.
    Returns the flag (existing or new).
    """
    existing = DataQualityFlag.query.filter_by(
        entity_type=entity_type,
        entity_id=entity_id,
        issue_type=issue_type,
    ).first()

    if existing:
        return existing

    flag = DataQualityFlag(
        entity_type=entity_type,
        entity_id=entity_id,
        issue_type=issue_type,
        details=details,
        salesforce_id=salesforce_id,
    )
    db.session.add(flag)
    return flag

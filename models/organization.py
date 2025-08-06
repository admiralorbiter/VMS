"""
Organization Models Module
=========================

This module contains the SQLAlchemy models for managing organizations and their
relationships with volunteers in the VMS system.

Models:
- Organization: Core organization entity with address and Salesforce integration
- VolunteerOrganization: Junction table for volunteer-organization relationships

Key Features:
- Bi-directional Salesforce integration with ID tracking
- Address management with structured fields
- Many-to-many volunteer relationships with metadata
- Automatic timestamp tracking
- Cascade delete operations for data integrity
- Role and status tracking for relationships
- Primary organization designation
- Historical relationship tracking

Relationships:
- Organization <-> Volunteer (many-to-many through VolunteerOrganization)
- Organization -> VolunteerOrganization (one-to-many)
- Volunteer -> VolunteerOrganization (one-to-many)

Database Design:
- Uses composite primary keys for junction table
- Indexed fields for performance on common queries
- Foreign key constraints with CASCADE delete
- Optimized for bulk operations with confirm_deleted_rows=False

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- Account record linking via salesforce_id
- Volunteer-organization relationship tracking
- Direct URL generation for Salesforce records

Data Management:
- Address information for billing and contact
- Organization classification and description
- Relationship metadata (role, dates, status)
- Audit trail with timestamps
- Activity tracking for business intelligence

Performance Optimizations:
- Indexed foreign keys for fast joins
- Composite primary keys for efficient lookups
- Cascade delete for referential integrity
- Bulk operation optimizations

Usage Examples:
    # Create a new organization
    org = Organization(
        name="Tech Corp",
        type="Business",
        salesforce_id="0011234567890ABCD"
    )

    # Add volunteer to organization
    vol_org = VolunteerOrganization(
        volunteer_id=volunteer.id,
        organization_id=org.id,
        role="Software Engineer",
        is_primary=True
    )

    # Get organization's Salesforce URL
    sf_url = org.salesforce_url
"""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from models import db


class Organization(db.Model):
    """
    Organization model representing companies, schools, or other institutions.

    This model stores core information about organizations that volunteers are associated with.
    It supports bi-directional sync with Salesforce and includes address information.

    Database Table:
        organization - Stores organization information and addresses

    Key Features:
        - Salesforce integration for data synchronization
        - Address management for billing and contact information
        - Many-to-many relationships with volunteers
        - Automatic timestamp tracking for audit trails
        - Organization classification and description
        - Activity tracking for business intelligence

    Relationships:
        - volunteers: Many-to-many with Volunteer model through volunteer_organization table
        - volunteer_organizations: One-to-many with VolunteerOrganization model (association table)

    Salesforce Integration:
        - salesforce_id: Links to Salesforce Account record
        - volunteer_salesforce_id: Reference to volunteer record in Salesforce
        - salesforce_url property: Generates direct link to Salesforce record

    Address Management:
        - Structured address fields for billing information
        - Supports international addresses with country field
        - TODO: Consider refactoring into separate Address model

    Timestamps:
        - created_at: Set once when record is created
        - updated_at: Automatically updated whenever record is modified
        - last_activity_date: Manually set to track business-level activity

    Data Validation:
        - Name is required and indexed for search
        - Salesforce ID is unique when present
        - Address fields are optional but structured
    """

    __tablename__ = "organization"

    # Primary identifier and Salesforce integration fields
    id = db.Column(Integer, primary_key=True)
    # Salesforce Account ID (18 char) - indexed for sync operations
    salesforce_id = db.Column(String(18), unique=True, nullable=True, index=True)
    # Organization name - indexed for search operations
    name = db.Column(String(255), nullable=False, index=True)
    # Organization classification (e.g., "School", "Business", "Non-profit")
    type = db.Column(String(255), nullable=True)
    # Organization description for additional context
    description = db.Column(String(255), nullable=True)

    # Reference to volunteer record in Salesforce
    # This field may be used for specific volunteer-organization relationships
    volunteer_salesforce_id = db.Column(String(18), nullable=True, index=True)

    # Address fields for billing/contact information
    # TODO: Consider refactoring these into a separate Address model
    # that can be reused across different entities
    billing_street = db.Column(String(255), nullable=True)
    billing_city = db.Column(String(255), nullable=True)
    billing_state = db.Column(String(255), nullable=True)
    billing_postal_code = db.Column(String(255), nullable=True)
    billing_country = db.Column(String(255), nullable=True)

    # Automatic timestamp fields for audit trail
    # created_at: Set once when record is created
    # updated_at: Automatically updated whenever record is modified
    # last_activity_date: Manually set to track business-level activity
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity_date = db.Column(db.DateTime, nullable=True)

    # Relationship definitions for volunteer associations
    # volunteers: Many-to-many relationship allowing direct access to associated Volunteer records
    # overlaps: Tells SQLAlchemy that this relationship shares some foreign keys with volunteer_organizations
    volunteers = relationship(
        "Volunteer",
        secondary="volunteer_organization",
        back_populates="organizations",  # Match the name in Volunteer model
        overlaps="volunteer_organizations",  # Match the relationship name
    )

    # Direct access to the association records for detailed relationship management
    # cascade='all, delete-orphan': Automatically deletes association records when Organization is deleted
    # passive_deletes=True: Lets the database handle cascade deletes for better performance
    volunteer_organizations = relationship(
        "VolunteerOrganization", back_populates="organization", cascade="all, delete-orphan", passive_deletes=True, overlaps="volunteers"
    )

    @property
    def salesforce_url(self):
        """
        Generate Salesforce URL if ID exists.

        This property creates a direct link to the Salesforce record for easy access
        from the VMS interface. Only generates URL if salesforce_id is present.

        Returns:
            str: URL to Salesforce record, or None if no salesforce_id exists

        Usage:
            sf_url = organization.salesforce_url
            if sf_url:
                # Open Salesforce record in browser
        """
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_id}/view"
        return None

    @property
    def volunteer_count(self):
        """
        Returns the number of volunteers associated with this organization.
        """
        return len(self.volunteers)


class VolunteerOrganization(db.Model):
    """
    Association model connecting volunteers to organizations.

    This is a junction table that manages the many-to-many relationship between
    Volunteer and Organization models. It includes additional metadata about
    the relationship such as role, dates, and status.

    Database Table:
        volunteer_organization - Junction table for volunteer-organization relationships

    Key Features:
        - Composite primary key for efficient relationship management
        - Salesforce integration for bi-directional synchronization
        - Role and status tracking for relationship context
        - Date range support for historical tracking
        - Primary organization flag for volunteer's main affiliation
        - Automatic timestamp tracking for audit trails

    Design Features:
        - Composite primary key (volunteer_id + organization_id)
        - Salesforce integration for bi-directional sync
        - Role and status tracking for relationship context
        - Date range support for historical tracking
        - Primary organization flag for volunteer's main affiliation

    Performance Optimizations:
        - confirm_deleted_rows=False improves deletion performance for bulk operations
        - Indexed foreign keys for fast joins and lookups
        - CASCADE delete ensures referential integrity

    Primary Keys:
        - volunteer_id and organization_id form a composite primary key

    Relationship Metadata:
        - role: Position or role at the organization
        - start_date/end_date: Relationship duration tracking
        - is_primary: Flags the volunteer's main organization
        - status: Current relationship status (Current, Past, Pending)

    Note: confirm_deleted_rows=False improves deletion performance for bulk operations
    """

    __tablename__ = "volunteer_organization"

    # Performance optimization for bulk delete operations
    __mapper_args__ = {"confirm_deleted_rows": False}  # Performance optimization for deletions

    # Composite primary key columns for the junction table
    # ondelete='CASCADE': Automatically deletes records if parent is deleted
    # index=True: Speeds up joins and lookups
    volunteer_id = db.Column(Integer, ForeignKey("volunteer.id", ondelete="CASCADE"), primary_key=True, index=True)
    organization_id = db.Column(Integer, ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True, index=True)

    # Salesforce integration fields for bi-directional sync
    # These fields store the Salesforce IDs for sync operations
    salesforce_volunteer_id = db.Column(db.String(18), nullable=True, index=True)
    salesforce_org_id = db.Column(db.String(18), nullable=True, index=True)

    # Relationship metadata for context and tracking
    role = db.Column(String(255), nullable=True)  # Position/role at organization
    start_date = db.Column(db.DateTime, nullable=True)  # When relationship began
    end_date = db.Column(db.DateTime, nullable=True)  # When relationship ended
    is_primary = db.Column(Boolean, default=False)  # Indicates primary organization for volunteer
    status = db.Column(String(50), default="Current")  # e.g., 'Current', 'Past', 'Pending'

    # Automatic timestamps for audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship definitions for direct access to parent models
    # Fix the relationships - remove secondary and use direct relationships
    # overlaps: Tells SQLAlchemy about relationship sharing to avoid conflicts
    volunteer = relationship("Volunteer", back_populates="volunteer_organizations", overlaps="organizations,volunteers")  # Add both relationship names

    organization = relationship("Organization", back_populates="volunteer_organizations", overlaps="organizations,volunteers")  # Add both relationship names

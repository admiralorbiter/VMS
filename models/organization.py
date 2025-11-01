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

import warnings

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from models import db
from models.contact import FormEnum
from models.utils import validate_salesforce_id


class OrganizationTypeEnum(FormEnum):
    """
    Enum defining the possible types of organizations.

    Used to classify organizations for reporting, filtering, and business logic.
    Values match those defined in business rules (config/validation.py).

    Values:
    - SCHOOL: Educational institutions
    - BUSINESS: For-profit companies
    - NON_PROFIT: Non-profit organizations
    - GOVERNMENT: Government entities
    - OTHER: Other types not covered above
    """

    SCHOOL = "School"
    BUSINESS = "Business"
    NON_PROFIT = "Non-profit"
    GOVERNMENT = "Government"
    OTHER = "Other"


class VolunteerOrganizationStatusEnum(FormEnum):
    """
    Enum defining the possible statuses of a volunteer-organization relationship.

    Used to track the current state of the relationship between a volunteer
    and an organization.

    Values:
    - CURRENT: Currently active relationship
    - PAST: Relationship has ended
    - PENDING: Relationship pending activation or approval
    """

    CURRENT = "Current"
    PAST = "Past"
    PENDING = "Pending"


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
    type = db.Column(
        Enum(OrganizationTypeEnum), nullable=True, index=True
    )  # Indexed for filtering
    # Organization description for additional context
    description = db.Column(String(255), nullable=True)

    # Reference to volunteer record in Salesforce
    # Used for tracking specific volunteer-organization relationships in Salesforce.
    # This is typically populated during Salesforce sync operations when a
    # volunteer's organization relationship has a corresponding Salesforce record.
    volunteer_salesforce_id = db.Column(String(18), nullable=True, index=True)

    # Address fields for billing/contact information
    # TODO: Consider refactoring these into a separate Address model
    # that can be reused across different entities
    billing_street = db.Column(String(255), nullable=True)
    billing_city = db.Column(String(255), nullable=True)
    billing_state = db.Column(String(255), nullable=True)
    billing_postal_code = db.Column(String(255), nullable=True)
    billing_country = db.Column(String(255), nullable=True)

    # Automatic timestamp fields for audit trail (timezone-aware, database-side defaults)
    # last_activity_date: Manually set to track business-level activity
    created_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_activity_date = db.Column(db.DateTime, nullable=True)

    @validates("salesforce_id", "volunteer_salesforce_id")
    def validate_salesforce_id_field(self, key, value):
        """
        Validate Salesforce ID format using shared validator.

        Args:
            key: Field name being validated
            value: Salesforce ID to validate

        Returns:
            str: Validated Salesforce ID or None

        Raises:
            ValueError: If Salesforce ID format is invalid
        """
        return validate_salesforce_id(value)

    @validates("type")
    def validate_type(self, key, value):
        """
        Validates organization type to ensure it's a valid OrganizationTypeEnum value.

        Maps common Salesforce type variations to standard enum values for compatibility:
        - "Corporate" -> "Business"
        - "Post-Secondary" -> "School" (educational institutions)
        - "Nonprofit" -> "Non-profit" (spelling variation)
        - "Non-Profit" -> "Non-profit" (case/hyphen variation)
        - "Non Profit" -> "Non-profit" (space variation)

        Args:
            key: Field name being validated
            value: The type value to validate

        Returns:
            OrganizationTypeEnum: Valid type enum value or None

        Raises:
            ValueError: If type value is invalid

        Example:
            >>> org.validate_type("type", "Business")
            OrganizationTypeEnum.BUSINESS

            >>> org.validate_type("type", "Corporate")
            OrganizationTypeEnum.BUSINESS

            >>> org.validate_type("type", "Post-Secondary")
            OrganizationTypeEnum.SCHOOL
        """
        if value is None:
            return None
        if isinstance(value, OrganizationTypeEnum):
            return value
        if isinstance(value, str):
            normalized_value = value.strip()

            # Mapping dictionary for Salesforce type variations to standard enum values
            type_mappings = {
                # Business variations
                "corporate": OrganizationTypeEnum.BUSINESS,
                # School/Educational variations
                "post-secondary": OrganizationTypeEnum.SCHOOL,
                "postsecondary": OrganizationTypeEnum.SCHOOL,
                "post secondary": OrganizationTypeEnum.SCHOOL,
                # Non-profit variations
                "nonprofit": OrganizationTypeEnum.NON_PROFIT,
                "non-profit": OrganizationTypeEnum.NON_PROFIT,
                "non profit": OrganizationTypeEnum.NON_PROFIT,
                "nonprofit organization": OrganizationTypeEnum.NON_PROFIT,
                "non-profit organization": OrganizationTypeEnum.NON_PROFIT,
            }

            # Check mapping dictionary first (case-insensitive)
            mapped_value = type_mappings.get(normalized_value.lower())
            if mapped_value:
                return mapped_value

            # Try value-based lookup for exact matches
            for enum_member in OrganizationTypeEnum:
                if enum_member.value.lower() == normalized_value.lower():
                    return enum_member

            # Try name-based lookup (e.g., "Business" -> BUSINESS)
            try:
                return OrganizationTypeEnum[
                    normalized_value.upper().replace("-", "_").replace(" ", "_")
                ]
            except KeyError:
                raise ValueError(
                    f"Invalid organization type: {value}. "
                    f"Valid values: {[t.value for t in OrganizationTypeEnum]}"
                )
        raise ValueError(f"Type must be an OrganizationTypeEnum value or valid string")

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
        "VolunteerOrganization",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="volunteers",
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

        This property efficiently counts volunteers using the association table
        without loading the entire relationship collection. This avoids loading
        all VolunteerOrganization records into memory.

        Returns:
            int: Number of volunteers associated with this organization

        Performance Note:
            Executes a database query on each access. For bulk operations
            accessing this property multiple times, consider eager loading
            or calculating counts in a single query.
        """
        # Use association table count to avoid loading entire collection
        return (
            db.session.query(VolunteerOrganization)
            .filter(VolunteerOrganization.organization_id == self.id)
            .count()
        )

    @property
    def formatted_billing_address(self):
        """
        Returns formatted string representation of billing address.

        Returns:
            str or None: Multi-line formatted address string if address information
                         exists, None otherwise

        Format:
            Street Address
            City, State ZIP
            Country (if not USA)

        Example:
            >>> org.formatted_billing_address
            '123 Main St\nKansas City, MO 64111\nUSA'
        """
        if not self.has_address_info:
            return None

        parts = []
        if self.billing_street:
            parts.append(self.billing_street)
        if self.billing_city and self.billing_state:
            city_state = f"{self.billing_city}, {self.billing_state}"
            if self.billing_postal_code:
                city_state += f" {self.billing_postal_code}"
            parts.append(city_state)
        elif self.billing_city:
            parts.append(self.billing_city)
        elif self.billing_state:
            parts.append(self.billing_state)

        if self.billing_country and self.billing_country.upper() != "USA":
            parts.append(self.billing_country)

        return "\n".join(parts) if parts else None

    @property
    def has_address_info(self):
        """
        Check if organization has any address information populated.

        Returns:
            bool: True if any address field is populated, False otherwise
        """
        return any(
            [
                self.billing_street,
                self.billing_city,
                self.billing_state,
                self.billing_postal_code,
                self.billing_country,
            ]
        )

    @property
    def primary_volunteers(self):
        """
        Returns list of volunteers who have this organization as their primary.

        Returns:
            list: List of Volunteer objects where is_primary=True for this organization

        Performance Note:
            Executes a database query on each access. For bulk operations,
            consider eager loading the relationship.
        """
        return [
            vo.volunteer
            for vo in self.volunteer_organizations
            if vo.is_primary and vo.volunteer
        ]

    @classmethod
    def from_salesforce(cls, data):
        """
        Creates an Organization instance from Salesforce data with proper data cleaning.

        This class method handles the conversion of Salesforce data to Organization
        instances, ensuring that empty strings are converted to None values
        and data is properly formatted. Also maps "Corporate" type to "Business"
        for Salesforce compatibility.

        Args:
            data (dict): Dictionary containing Salesforce organization data

        Returns:
            Organization: New Organization instance with cleaned data

        Example:
            >>> sf_data = {
            ...     "name": "Tech Corp",
            ...     "type": "",
            ...     "billing_city": "Kansas City"
            ... }
            >>> org = Organization.from_salesforce(sf_data)
            >>> org.type is None
            True

            >>> sf_data = {"name": "Tech Corp", "type": "Corporate"}
            >>> org = Organization.from_salesforce(sf_data)
            >>> org.type == OrganizationTypeEnum.BUSINESS
            True
        """
        # Convert empty strings to None
        cleaned = {k: (None if v == "" else v) for k, v in data.items()}

        # Map common Salesforce type variations to standard values before validation
        # The validate_type method will handle the actual enum conversion
        if "type" in cleaned and cleaned["type"]:
            type_value = cleaned["type"].strip()
            type_lower = type_value.lower()

            # Mapping for common variations (maps to enum values, not enum names)
            type_mappings = {
                "corporate": "Business",
                "post-secondary": "School",
                "postsecondary": "School",
                "post secondary": "School",
                "nonprofit": "Non-profit",
                "non-profit": "Non-profit",  # Already correct, but ensure consistency
                "non profit": "Non-profit",
            }

            # Apply mapping if found
            if type_lower in type_mappings:
                cleaned["type"] = type_mappings[type_lower]

        return cls(**cleaned)

    @validates("billing_city", "billing_state", "billing_postal_code")
    def validate_address_fields(self, key, value):
        """
        Validates address fields for consistency.

        This validator provides warnings for address inconsistencies but doesn't
        block saves, allowing partial address data during imports.

        Args:
            key: Field name being validated
            value: Address field value to validate

        Returns:
            str or None: Validated address value or None

        Note:
            Uses warnings for non-critical validation, similar to Volunteer.validate_dates()
        """
        if not value:
            return None

        # If we have a city, recommend having state as well
        if key == "billing_city" and value and not self.billing_state:
            warnings.warn(
                f"Organization {self.id}: City provided without state. "
                "Consider providing both for complete address.",
                UserWarning,
            )
        # If we have a state, recommend having postal code
        if key == "billing_state" and value and not self.billing_postal_code:
            warnings.warn(
                f"Organization {self.id}: State provided without postal code. "
                "Consider providing postal code for complete address.",
                UserWarning,
            )

        return value

    def __repr__(self):
        """
        Developer-friendly string representation of the Organization model.

        Returns:
            str: Debug representation showing organization ID and name
        """
        name = self.name[:50] if self.name else "Unknown"
        return f"<Organization {self.id}: {name}>"

    def __str__(self):
        """
        Human-readable string representation of the Organization model.

        Returns:
            str: Organization name, or "Unknown" if name is not set
        """
        return self.name if self.name else "Unknown"


class VolunteerOrganization(db.Model):
    """
    Association model connecting volunteers to organizations.

    This is a junction table that manages the many-to-many relationship between
    Volunteer and Organization models. It includes additional metadata about
    the relationship such as role, dates, and status.

    Database Table:
        volunteer_organization - Junction table for volunteer-organization relationships

    Key Features:
        - Composite primary key (volunteer_id + organization_id) for efficient relationship management
        - Salesforce integration for bi-directional synchronization
        - Role and status tracking for relationship context
        - Date range support for historical tracking (start_date/end_date)
        - Primary organization flag for volunteer's main affiliation
        - Automatic timestamp tracking for audit trails

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
    __mapper_args__ = {
        "confirm_deleted_rows": False  # Performance optimization for deletions
    }

    # Composite primary key columns for the junction table
    # ondelete='CASCADE': Automatically deletes records if parent is deleted
    # index=True: Speeds up joins and lookups
    volunteer_id = db.Column(
        Integer,
        ForeignKey("volunteer.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    organization_id = db.Column(
        Integer,
        ForeignKey("organization.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    # Salesforce integration fields for bi-directional sync
    # These fields store the Salesforce IDs for sync operations
    salesforce_volunteer_id = db.Column(db.String(18), nullable=True, index=True)
    salesforce_org_id = db.Column(db.String(18), nullable=True, index=True)

    @validates("salesforce_volunteer_id", "salesforce_org_id")
    def validate_salesforce_id_field(self, key, value):
        """
        Validate Salesforce ID format using shared validator.

        Args:
            key: Field name being validated
            value: Salesforce ID to validate

        Returns:
            str: Validated Salesforce ID or None

        Raises:
            ValueError: If Salesforce ID format is invalid
        """
        return validate_salesforce_id(value)

    @validates("status")
    def validate_status(self, key, value):
        """
        Validates relationship status to ensure it's a valid VolunteerOrganizationStatusEnum value.

        Args:
            key: Field name being validated
            value: The status value to validate

        Returns:
            VolunteerOrganizationStatusEnum: Valid status enum value

        Raises:
            ValueError: If status value is invalid

        Example:
            >>> vol_org.validate_status("status", "Current")
            VolunteerOrganizationStatusEnum.CURRENT
        """
        if value is None:
            return VolunteerOrganizationStatusEnum.CURRENT  # Default to CURRENT
        if isinstance(value, VolunteerOrganizationStatusEnum):
            return value
        if isinstance(value, str):
            # Try value-based lookup
            for enum_member in VolunteerOrganizationStatusEnum:
                if enum_member.value.lower() == value.lower():
                    return enum_member
            # Try name-based lookup
            try:
                return VolunteerOrganizationStatusEnum[value.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid status: {value}. "
                    f"Valid values: {[s.value for s in VolunteerOrganizationStatusEnum]}"
                )
        raise ValueError(f"Status must be a VolunteerOrganizationStatusEnum enum value")

    # Relationship metadata for context and tracking
    role = db.Column(String(255), nullable=True)  # Position/role at organization
    start_date = db.Column(db.DateTime, nullable=True)  # When relationship began
    end_date = db.Column(db.DateTime, nullable=True)  # When relationship ended
    is_primary = db.Column(
        Boolean, default=False
    )  # Indicates primary organization for volunteer
    status = db.Column(
        Enum(VolunteerOrganizationStatusEnum),
        default=VolunteerOrganizationStatusEnum.CURRENT,
        nullable=True,
    )

    # Automatic timestamps for audit trail (timezone-aware, database-side defaults)
    created_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship definitions for direct access to parent models
    # overlaps: Tells SQLAlchemy about relationship sharing to avoid conflicts
    volunteer = relationship(
        "Volunteer",
        back_populates="volunteer_organizations",
        overlaps="organizations,volunteers",  # Add both relationship names
    )

    organization = relationship(
        "Organization",
        back_populates="volunteer_organizations",
        overlaps="organizations,volunteers",  # Add both relationship names
    )

    def __repr__(self):
        """
        Developer-friendly string representation of the VolunteerOrganization model.

        Returns:
            str: Debug representation showing volunteer and organization IDs
        """
        return f"<VolunteerOrganization volunteer_id={self.volunteer_id} organization_id={self.organization_id}>"

    def __str__(self):
        """
        Human-readable string representation of the VolunteerOrganization model.

        Returns:
            str: String showing volunteer and organization relationship
        """
        org_name = (
            self.organization.name[:30]
            if self.organization and self.organization.name
            else "Unknown Org"
        )
        role_str = f" as {self.role}" if self.role else ""
        status_str = f" ({self.status.value})" if self.status else ""
        return f"Volunteer {self.volunteer_id} -> {org_name}{role_str}{status_str}"

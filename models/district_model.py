"""
District Model Module
====================

This module defines the District model for managing school districts in the VMS system.
It provides core district information storage and Salesforce integration capabilities.

Key Features:
- School district information management
- Salesforce integration for data synchronization
- One-to-many relationship with schools
- District code and name tracking
- Unique Salesforce ID mapping
- Indexed fields for performance optimization

Database Table:
- district: Stores school district information

District Management:
- District name and identification
- District code for external references
- Salesforce record synchronization
- School relationship management
- Data integrity and validation

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- District record mapping and tracking
- Unique ID constraints for data consistency
- Indexed fields for fast lookups

Relationships:
- One-to-many with School model (defined in school_model.py)
- Many-to-many with Event model through event_districts
- One-to-many with DistrictYearEndReport model
- One-to-many with DistrictEngagementReport model

Performance Features:
- Indexed salesforce_id for fast lookups
- Auto-incrementing primary key
- Optimized query patterns
- Efficient relationship management

Usage Examples:
    # Create a new district
    district = District(
        name="Kansas City Public Schools",
        district_code="KCPS",
        salesforce_id="0011234567890ABCD"
    )

    # Find district by Salesforce ID
    district = District.query.filter_by(salesforce_id="0011234567890ABCD").first()

    # Get district's schools (relationship defined in School model)
    schools = district.schools
"""

from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from models import db
from models.utils import validate_salesforce_id


class District(db.Model):
    """
    District model representing school districts in the system.

    This model stores core information about school districts and maintains
    a one-to-many relationship with schools. Each district can have multiple
    schools associated with it.

    Database Table:
        district - Stores school district information

    Key Features:
        - School district information management
        - Salesforce integration for data synchronization
        - One-to-many relationship with schools
        - District code and name tracking
        - Unique Salesforce ID mapping
        - Indexed fields for performance optimization

    District Management:
        - District name and identification
        - District code for external references
        - Salesforce record synchronization
        - School relationship management
        - Data integrity and validation

    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - District record mapping and tracking
        - Unique ID constraints for data consistency
        - Indexed fields for fast lookups

    Relationships:
        - One-to-many with School model (defined in school_model.py)
        - Many-to-many with Event model through event_districts
        - One-to-many with DistrictYearEndReport model
        - One-to-many with DistrictEngagementReport model

    Performance Features:
        - Indexed salesforce_id for fast lookups
        - Auto-incrementing primary key
        - Optimized query patterns
        - Efficient relationship management

    Data Validation:
        - District name is required
        - Salesforce ID is unique when present and validated for format
        - District code is optional but indexed
        - Auto-incrementing ID for internal references

    Helper Methods:
        - salesforce_url: Generate Salesforce URL for district record
        - school_count: Get count of schools in district
        - to_dict(): Convert district to dictionary for API responses

    Note: The relationship with schools is defined in the School model to avoid
    circular references. See models/school_model.py for the relationship definition.
    """

    __tablename__ = "district"

    # Primary key - Auto-incrementing integer for internal references
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Salesforce integration field - Used to sync with Salesforce records
    # indexed=True improves query performance when looking up by salesforce_id
    salesforce_id = db.Column(db.String(18), unique=True, nullable=True, index=True)

    # Core district information
    name = db.Column(
        db.String(255), nullable=False
    )  # Required field - District's official name
    district_code = db.Column(
        db.String(20), nullable=True
    )  # Optional external reference code

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

    @validates("salesforce_id")
    def validate_salesforce_id_field(self, key, value):
        """
        Validates Salesforce ID format using shared validator.

        Args:
            key (str): The name of the field being validated
            value: Salesforce ID to validate

        Returns:
            str: Validated Salesforce ID or None

        Raises:
            ValueError: If Salesforce ID format is invalid

        Example:
            >>> district.validate_salesforce_id_field("salesforce_id", "0011234567890ABCD")
            '0011234567890ABCD'
        """
        return validate_salesforce_id(value)

    @property
    def salesforce_url(self):
        """
        Generate Salesforce URL for this district.

        Returns:
            str: URL to Salesforce District record, or None if no salesforce_id
        """
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_id}/view"
        return None

    @property
    def school_count(self):
        """
        Returns the count of schools in this district.

        Returns:
            int: Number of schools in this district
        """
        return self.schools.count()

    def to_dict(self):
        """
        Convert district to dictionary for API responses.

        Returns:
            dict: Dictionary representation of the district with metadata
        """
        return {
            "id": self.id,
            "salesforce_id": self.salesforce_id,
            "name": self.name,
            "district_code": self.district_code,
            "school_count": self.school_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        """
        String representation of the district for debugging and logging.

        Returns:
            str: Debug representation showing district name
        """
        return f"<District {self.name}>"

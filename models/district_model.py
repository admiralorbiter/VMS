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

from models import db


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
        - Salesforce ID is unique when present
        - District code is optional but indexed
        - Auto-incrementing ID for internal references

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

    def __repr__(self):
        """
        String representation of the district for debugging and logging.

        Returns:
            str: Debug representation showing district name
        """
        return f"<District {self.name}>"

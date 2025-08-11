"""
School Model Module
==================

This module defines the School model for managing individual schools in the VMS system.
It provides school information storage, district relationships, and Salesforce integration.

Key Features:
- School information management and storage
- District relationship management
- Salesforce integration for data synchronization
- School level categorization (Elementary, Middle, High)
- Normalized name support for consistent searching
- School code tracking for external references
- Bi-directional district relationships

Database Table:
- school: Stores individual school information

School Management:
- School name and identification
- School level categorization
- District assignment and relationships
- Normalized name for search consistency
- School code for external references
- Salesforce ID mapping

District Relationships:
- Many-to-one relationship with District model
- Bi-directional navigation (school.district, district.schools)
- Cascade delete for data integrity
- Dynamic loading for performance optimization

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- School record mapping and tracking
- District relationship synchronization
- Unique ID constraints for data consistency

School Levels:
- Elementary: K-5 schools
- Middle: 6-8 schools
- High: 9-12 schools
- Other: Specialized or alternative schools

Performance Features:
- Dynamic relationship loading
- Cascade delete for data integrity
- Optimized query patterns
- Efficient district navigation

Usage Examples:
    # Create a new school
    school = School(
        id="0015f00000JVZsFAAX",
        name="Lincoln High School",
        district_id=district.id,
        level="High",
        school_code="LHS"
    )

    # Get school's district
    district = school.district

    # Get district's schools
    schools = district.schools.all()

    # Find schools by level
    high_schools = School.query.filter_by(level="High").all()
"""

from models import db


class School(db.Model):
    """
    School model representing individual schools in the system.

    This model maintains the relationship between schools and their districts,
    storing both internal and Salesforce-related identifiers. The model supports
    bi-directional relationships, allowing navigation from schools to districts
    and vice versa.

    Database Table:
        school - Stores individual school information

    Key Features:
        - School information management and storage
        - District relationship management
        - Salesforce integration for data synchronization
        - School level categorization (Elementary, Middle, High)
        - Normalized name support for consistent searching
        - School code tracking for external references
        - Bi-directional district relationships

    School Management:
        - School name and identification
        - School level categorization
        - District assignment and relationships
        - Normalized name for search consistency
        - School code for external references
        - Salesforce ID mapping

    District Relationships:
        - Many-to-one relationship with District model
        - Bi-directional navigation (school.district, district.schools)
        - Cascade delete for data integrity
        - Dynamic loading for performance optimization

    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - School record mapping and tracking
        - District relationship synchronization
        - Unique ID constraints for data consistency

    School Levels:
        - Elementary: K-5 schools
        - Middle: 6-8 schools
        - High: 9-12 schools
        - Other: Specialized or alternative schools

    Performance Features:
        - Dynamic relationship loading
        - Cascade delete for data integrity
        - Optimized query patterns
        - Efficient district navigation

    Data Validation:
        - School name is required
        - Salesforce ID format for primary key
        - District relationship for organization
        - Level categorization for filtering
        - Normalized name for search consistency

    Key Relationships:
        - district: Many-to-one relationship with District model
        - events: One-to-many relationship with Event model
    """

    __tablename__ = "school"

    # Primary key - Using Salesforce ID format for direct mapping
    id = db.Column(
        db.String(255), primary_key=True
    )  # Salesforce ID format (e.g., '0015f00000JVZsFAAX')

    # Core school information
    name = db.Column(
        db.String(255), nullable=False
    )  # Required field - School's official name

    # District relationship fields
    district_id = db.Column(
        db.Integer, db.ForeignKey("district.id")
    )  # Internal district reference
    salesforce_district_id = db.Column(db.String(255))  # External district reference

    # Additional school information
    normalized_name = db.Column(
        db.String(255)
    )  # Standardized name for consistent searching
    school_code = db.Column(db.String(255))  # External reference code

    # Add the new level field
    level = db.Column(
        db.String(50)
    )  # Can store values like 'High', 'Elementary', 'Middle', etc.

    # Relationship definition for both models
    # - backref creates a 'schools' property on District model
    # - lazy='dynamic' makes district.schools return a query object instead of a list
    #   allowing for further filtering and efficient counting
    district = db.relationship(
        "District",
        backref=db.backref("schools", lazy="dynamic", cascade="all, delete-orphan"),
        cascade="all, delete",
    )

    def __repr__(self):
        """
        String representation of the school for debugging and logging.

        Returns:
            str: Debug representation showing school name
        """
        return f"<School {self.name}>"

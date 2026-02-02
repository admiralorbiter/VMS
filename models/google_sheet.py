"""
Google Sheet Models Module
=========================

This module defines the GoogleSheet model for managing Google Sheets integration
in the VMS system. It provides simple storage for Google Sheet IDs with academic
year and purpose-based organization.

Key Features:
- Simple storage of Google Sheet IDs (plain text, no encryption)
- Academic year and purpose-based organization
- User tracking for sheet creation
- Automatic timestamp tracking
- API-friendly dictionary conversion

Database Table:
- google_sheets: Stores Google Sheet configurations

Academic Year Management:
- Academic year organization (e.g., "2023-2024")
- Purpose-based categorization (e.g., "virtual_sessions", "district_reports")
- Unique academic year + purpose constraints
- Year-based sheet identification
- Temporal data organization

User Tracking:
- Creator identification and tracking
- User relationship management
- Audit trail for sheet creation
- Creator name resolution

Integration Features:
- Google Sheets API integration support
- Simple credential storage
- Academic year alignment
- User permission tracking

Usage Examples:
    # Create a new Google Sheet configuration for district reports
    sheet = GoogleSheet(
        academic_year="2024-2025",
        purpose="district_reports",
        sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        sheet_name="District Year-End Report 2024-2025",
        created_by=user.id
    )

    # Create a virtual sessions sheet
    virtual_sheet = GoogleSheet(
        academic_year="2024-2025",
        purpose="virtual_sessions",
        sheet_id="1CxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        sheet_name="Virtual Sessions 2024-2025",
        created_by=user.id
    )

    # Get sheet ID (plain text)
    sheet_id = sheet.decrypted_sheet_id

    # Update sheet ID
    sheet.update_sheet_id("new_sheet_id_here")

    # Convert to dictionary for API
    sheet_dict = sheet.to_dict()
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from models import db


class GoogleSheet(db.Model):
    """
    Model for managing Google Sheets integration.

    This model provides simple storage and management of Google Sheet IDs
    with academic year and purpose organization. It organizes sheets by academic year
    and purpose, allowing multiple sheets per academic year for different uses.

    Database Table:
        google_sheets - Stores Google Sheet configurations

    Key Features:
        - Simple storage of Google Sheet IDs (plain text)
        - Academic year and purpose-based organization
        - User tracking for sheet creation and management
        - Automatic timestamp tracking for audit trails
        - API-friendly dictionary conversion

    Academic Year Management:
        - Academic year organization (e.g., "2023-2024")
        - Purpose-based categorization (e.g., "virtual_sessions", "district_reports")
        - Unique academic year + purpose constraints
        - Year-based sheet identification
        - Temporal data organization

    User Tracking:
        - Creator identification and tracking
        - User relationship management
        - Audit trail for sheet creation
        - Creator name resolution for display

    Integration Features:
        - Google Sheets API integration support
        - Simple credential storage
        - Academic year alignment
        - User permission tracking

    Data Management:
        - Plain text sheet ID storage
        - Academic year and purpose organization
        - User creation tracking
        - Timestamp tracking for changes
    """

    __tablename__ = "google_sheets"

    id = Column(Integer, primary_key=True)
    academic_year = Column(String(10), nullable=False)  # e.g., "2023-2024"
    purpose = Column(
        String(50), nullable=False, default="district_reports"
    )  # e.g., "district_reports", "virtual_sessions"
    sheet_id = Column(
        Text, nullable=True
    )  # Google Sheet ID (nullable for test compatibility)
    sheet_name = Column(String(255), nullable=True)  # Display name for the sheet
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(Integer, db.ForeignKey("users.id"))
    district_name = Column(
        String(200), nullable=True
    )  # For scoping sheets to districts

    # Note: Unique constraint is handled at database level with partial index
    # Virtual sessions: Only one sheet per academic year (enforced by partial unique index)
    # District reports: Multiple sheets per academic year allowed (no constraint)

    # Relationship to user who created it
    creator = db.relationship("User", backref="created_sheets")

    def __init__(
        self,
        academic_year,
        sheet_id,
        created_by=None,
        purpose="district_reports",
        sheet_name=None,
        district_name=None,
    ):
        """
        Initialize a new Google Sheet configuration.

        Args:
            academic_year: Academic year (e.g., "2023-2024")
            sheet_id: Google Sheet ID to store (plain text)
            created_by: User ID who created this configuration
            purpose: Purpose of the sheet (e.g., "district_reports", "virtual_sessions")
            sheet_name: Display name for the sheet
        """
        self.academic_year = academic_year
        self.purpose = purpose
        self.sheet_id = sheet_id  # Store as plain text
        self.sheet_name = sheet_name
        self.sheet_name = sheet_name
        self.created_by = created_by
        self.district_name = district_name

    @property
    def decrypted_sheet_id(self):
        """
        Get the Google Sheet ID (plain text).

        Note: This property name is kept for backward compatibility.
        The sheet ID is now stored as plain text, not encrypted.

        Returns:
            str: Google Sheet ID, or None if not set
        """
        return self.sheet_id

    def update_sheet_id(self, new_sheet_id):
        """
        Update the sheet ID.

        Args:
            new_sheet_id: New Google Sheet ID to store
        """
        self.sheet_id = new_sheet_id

    def to_dict(self):
        """
        Convert to dictionary for API responses.

        Returns:
            dict: Dictionary representation with decrypted sheet ID and metadata
        """
        return {
            "id": self.id,
            "academic_year": self.academic_year,
            "purpose": self.purpose,
            "sheet_id": self.decrypted_sheet_id,
            "sheet_name": self.sheet_name,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
            "created_by": self.created_by,
            "created_by": self.created_by,
            "creator_name": self.creator.username if self.creator else None,
            "district_name": self.district_name,
        }

    def __repr__(self):
        """
        String representation for debugging.

        Returns:
            str: Debug representation showing academic year and purpose
        """
        return f"<GoogleSheet {self.academic_year} - {self.purpose}>"

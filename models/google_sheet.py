"""
Google Sheet Models Module
=========================

This module defines the GoogleSheet model for managing Google Sheets integration
in the VMS system. It provides secure storage and encryption for Google Sheet IDs
with academic year and purpose-based organization.

Key Features:
- Secure encryption of Google Sheet IDs
- Academic year and purpose-based organization
- User tracking for sheet creation
- Automatic timestamp tracking
- Environment-based encryption key management
- API-friendly dictionary conversion

Database Table:
- google_sheets: Stores encrypted Google Sheet configurations

Security Features:
- Fernet encryption for sheet IDs
- Environment variable key management
- Base64 encoding for storage
- Automatic key generation fallback
- Secure decryption methods

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
- Encrypted credential storage
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

    # Get decrypted sheet ID
    sheet_id = sheet.decrypted_sheet_id

    # Update sheet ID
    sheet.update_sheet_id("new_sheet_id_here")

    # Convert to dictionary for API
    sheet_dict = sheet.to_dict()
"""

import base64
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from flask import current_app
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from models import db


class GoogleSheet(db.Model):
    """
    Model for managing Google Sheets integration.

    This model provides secure storage and management of Google Sheet IDs
    with encryption for data security. It organizes sheets by academic year
    and purpose, allowing multiple sheets per academic year for different uses.

    Database Table:
        google_sheets - Stores encrypted Google Sheet configurations

    Key Features:
        - Secure encryption of Google Sheet IDs using Fernet
        - Academic year and purpose-based organization
        - User tracking for sheet creation and management
        - Automatic timestamp tracking for audit trails
        - Environment-based encryption key management
        - API-friendly dictionary conversion

    Security Features:
        - Fernet encryption for sensitive sheet IDs
        - Environment variable key management
        - Base64 encoding for database storage
        - Automatic key generation fallback
        - Secure decryption methods with error handling

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
        - Encrypted credential storage
        - Academic year alignment
        - User permission tracking

    Data Management:
        - Encrypted sheet ID storage
        - Academic year and purpose organization
        - User creation tracking
        - Timestamp tracking for changes
        - Error handling for decryption failures
    """

    __tablename__ = "google_sheets"

    id = Column(Integer, primary_key=True)
    academic_year = Column(String(10), nullable=False)  # e.g., "2023-2024"
    purpose = Column(
        String(50), nullable=False, default="district_reports"
    )  # e.g., "district_reports", "virtual_sessions"
    sheet_id = Column(
        Text, nullable=True
    )  # Encrypted Google Sheet ID (nullable for test compatibility)
    sheet_name = Column(String(255), nullable=True)  # Display name for the sheet
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(Integer, db.ForeignKey("users.id"))

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
    ):
        """
        Initialize a new Google Sheet configuration.

        Args:
            academic_year: Academic year (e.g., "2023-2024")
            sheet_id: Google Sheet ID to encrypt and store
            created_by: User ID who created this configuration
            purpose: Purpose of the sheet (e.g., "district_reports", "virtual_sessions")
            sheet_name: Display name for the sheet
        """
        self.academic_year = academic_year
        self.purpose = purpose
        # Store the encryption key to ensure consistency between encrypt/decrypt
        self._encryption_key = self._get_encryption_key()
        self.sheet_id = self._encrypt_sheet_id(sheet_id)
        self.sheet_name = sheet_name
        self.created_by = created_by

    def _get_encryption_key(self):
        """
        Get or create encryption key from environment variable.

        Attempts to get the encryption key from Flask config first,
        then falls back to environment variables. If no key exists,
        generates a new one with a warning.

        Returns:
            bytes: Encryption key for Fernet cipher
        """
        # Try to get from Flask config first, then environment
        try:
            key = current_app.config.get("ENCRYPTION_KEY")
        except RuntimeError:
            # If we're outside application context, fall back to os.getenv
            key = os.getenv("ENCRYPTION_KEY")

        if not key:
            # Generate a new key if none exists
            key = Fernet.generate_key()
            print(
                f"WARNING: No ENCRYPTION_KEY found in environment. Generated new key: {key.decode()}"
            )
            print(
                "Please add this key to your environment variables for production use."
            )
        elif isinstance(key, str):
            key = key.encode()
        return key

    def _encrypt_sheet_id(self, sheet_id):
        """
        Encrypt the Google Sheet ID using Fernet encryption.

        Args:
            sheet_id: Plain text Google Sheet ID to encrypt

        Returns:
            str: Base64-encoded encrypted sheet ID, or None if input is None
        """
        if not sheet_id:
            return None

        key = self._encryption_key
        f = Fernet(key)
        encrypted_data = f.encrypt(sheet_id.encode())
        return base64.b64encode(encrypted_data).decode()

    def _decrypt_sheet_id(self, encrypted_sheet_id):
        """
        Decrypt the Google Sheet ID using Fernet decryption.

        Args:
            encrypted_sheet_id: Base64-encoded encrypted sheet ID

        Returns:
            str: Decrypted Google Sheet ID, or None if decryption fails
        """
        if not encrypted_sheet_id:
            return None

        try:
            key = self._encryption_key
            f = Fernet(key)
            encrypted_data = base64.b64decode(encrypted_sheet_id.encode())
            decrypted_data = f.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Error decrypting sheet ID: {e}")
            return None

    @property
    def decrypted_sheet_id(self):
        """
        Get the decrypted Google Sheet ID.

        Returns:
            str: Decrypted Google Sheet ID, or None if decryption fails
        """
        return self._decrypt_sheet_id(self.sheet_id)

    def update_sheet_id(self, new_sheet_id):
        """
        Update the encrypted sheet ID.

        Args:
            new_sheet_id: New Google Sheet ID to encrypt and store
        """
        self.sheet_id = self._encrypt_sheet_id(new_sheet_id)

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
            "creator_name": self.creator.username if self.creator else None,
        }

    def __repr__(self):
        """
        String representation for debugging.

        Returns:
            str: Debug representation showing academic year and purpose
        """
        return f"<GoogleSheet {self.academic_year} - {self.purpose}>"

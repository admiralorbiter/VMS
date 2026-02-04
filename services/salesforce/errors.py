"""
Salesforce Import Error Types
=============================

Provides standardized error codes and structured error objects for
Salesforce import operations. Enables machine-parseable error responses
in API endpoints.

Usage:
    from services.salesforce.errors import ImportErrorCode, create_import_error

    error = create_import_error(
        code=ImportErrorCode.FK_NOT_FOUND,
        row=salesforce_row,
        message="School not found",
        field="school_id"
    )
    errors.append(error.to_dict())
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ImportErrorCode(Enum):
    """Standardized error codes for Salesforce import failures.

    Codes are organized by category:
    - Data validation: MISSING_*, INVALID_*
    - Relationships: FK_*, DUPLICATE_*
    - Processing: DB_*, CONTACT_*
    - Generic: UNKNOWN
    """

    # Data validation errors
    MISSING_SF_ID = "MISSING_SF_ID"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_DATE = "INVALID_DATE"
    INVALID_ENUM = "INVALID_ENUM"
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_PHONE = "INVALID_PHONE"

    # Relationship errors
    FK_NOT_FOUND = "FK_NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    PARENT_NOT_FOUND = "PARENT_NOT_FOUND"

    # Processing errors
    CONTACT_INFO_FAILED = "CONTACT_INFO_FAILED"
    DB_CONSTRAINT = "DB_CONSTRAINT"
    DB_INTEGRITY = "DB_INTEGRITY"

    # Generic fallback
    UNKNOWN = "UNKNOWN"


@dataclass
class ImportError:
    """Structured error for import failures.

    Attributes:
        code: Machine-parseable error code from ImportErrorCode enum
        record_id: Salesforce ID of the failed record
        record_name: Human-readable identifier (e.g., "John Doe")
        field: Optional field name that caused the error
        message: Human-readable error description
    """

    code: ImportErrorCode
    record_id: Optional[str]
    record_name: Optional[str]
    field: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code.value,
            "record_id": self.record_id,
            "record_name": self.record_name,
            "field": self.field,
            "message": self.message,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        parts = [f"[{self.code.value}]"]
        if self.record_name:
            parts.append(self.record_name)
        if self.record_id:
            parts.append(f"(SF ID: {self.record_id})")
        if self.field:
            parts.append(f"field={self.field}")
        parts.append(f"- {self.message}")
        return " ".join(parts)


def create_import_error(
    code: ImportErrorCode,
    row: dict,
    message: str,
    field: Optional[str] = None,
    name_fields: tuple = ("FirstName", "LastName"),
) -> ImportError:
    """Create an ImportError from a Salesforce row.

    Args:
        code: Error code from ImportErrorCode enum
        row: Salesforce record dict containing Id and name fields
        message: Human-readable error message
        field: Optional field name that caused the error
        name_fields: Tuple of field names to combine for record_name

    Returns:
        ImportError instance ready for serialization

    Example:
        error = create_import_error(
            code=ImportErrorCode.INVALID_DATE,
            row={"Id": "003ABC", "FirstName": "John", "LastName": "Doe"},
            message="Invalid date format",
            field="birthdate"
        )
    """
    # Build name from specified fields
    name_parts = [str(row.get(f, "")).strip() for f in name_fields]
    name = " ".join(filter(None, name_parts)) or "Unknown"

    return ImportError(
        code=code,
        record_id=row.get("Id"),
        record_name=name,
        field=field,
        message=message,
    )


def classify_exception(e: Exception) -> ImportErrorCode:
    """Attempt to classify an exception into an ImportErrorCode.

    Args:
        e: The exception to classify

    Returns:
        Best-matching ImportErrorCode, or UNKNOWN if unclassifiable
    """
    error_str = str(e).lower()

    # Check for common patterns
    if "foreign key" in error_str or "fk constraint" in error_str:
        return ImportErrorCode.FK_NOT_FOUND
    if "duplicate" in error_str or "unique constraint" in error_str:
        return ImportErrorCode.DUPLICATE_RECORD
    if "integrity" in error_str:
        return ImportErrorCode.DB_INTEGRITY
    if "not null" in error_str or "required" in error_str:
        return ImportErrorCode.MISSING_REQUIRED_FIELD
    if "date" in error_str or "datetime" in error_str:
        return ImportErrorCode.INVALID_DATE
    if "email" in error_str:
        return ImportErrorCode.INVALID_EMAIL

    return ImportErrorCode.UNKNOWN

"""
Teacher Import Service
=====================

Service layer for importing teacher rosters from Google Sheets URLs and CSV files.
Provides a unified interface for tenant-scoped teacher imports.

Key Features:
- Parse Google Sheet URLs to extract sheet IDs
- Handle CSV file uploads with encoding detection
- Validate column names and data integrity
- Delegate to roster_import utility for actual imports
"""

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

from models.teacher_progress import TeacherProgress
from utils.roster_import import import_roster, validate_import_data


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    row_count: int = 0
    preview_data: List[dict] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of an import operation."""

    success: bool
    records_added: int = 0
    records_updated: int = 0
    records_deactivated: int = 0
    records_skipped: int = 0
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class TeacherImportService:
    """
    Service for importing teacher rosters from various sources.

    Supports:
    - Google Sheets (via URL or sheet ID)
    - CSV file uploads

    All imports are scoped to a tenant and academic year.
    """

    # Regex patterns for extracting Google Sheet ID
    SHEET_ID_PATTERNS = [
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",  # Standard URL
        r"^([a-zA-Z0-9-_]{20,})$",  # Raw sheet ID
    ]

    REQUIRED_COLUMNS = ["Building", "Name", "Email"]
    OPTIONAL_COLUMNS = ["Grade"]

    @classmethod
    def extract_sheet_id(cls, url_or_id: str) -> Optional[str]:
        """
        Extract Google Sheet ID from various URL formats.

        Args:
            url_or_id: Google Sheet URL or raw sheet ID

        Returns:
            Sheet ID string or None if not found
        """
        if not url_or_id:
            return None

        url_or_id = url_or_id.strip()

        for pattern in cls.SHEET_ID_PATTERNS:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        return None

    @classmethod
    def read_google_sheet(
        cls, sheet_id: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Read data from a Google Sheet.

        Args:
            sheet_id: Google Sheet ID

        Returns:
            Tuple of (DataFrame, error_message)
        """
        from flask import current_app

        current_app.logger.info(f"Attempting to read Google Sheet: {sheet_id}")

        # Try multiple URL formats
        urls = [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv",
        ]

        last_error = None
        for url in urls:
            try:
                current_app.logger.info(f"Trying URL: {url}")
                df = pd.read_csv(url)
                current_app.logger.info(
                    f"Successfully read {len(df)} rows from Google Sheet"
                )
                current_app.logger.info(f"Columns: {list(df.columns)}")
                return df, None
            except Exception as e:
                last_error = str(e)
                current_app.logger.warning(f"Failed with URL {url}: {last_error}")
                continue

        return (
            None,
            f"Could not read Google Sheet. Make sure the sheet is publicly accessible or shared with 'Anyone with the link'. Error: {last_error}",
        )

    @classmethod
    def read_csv_file(
        cls, file_content: bytes, filename: str = "upload.csv"
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Read data from a CSV file with encoding detection.

        Args:
            file_content: Raw bytes of the CSV file
            filename: Original filename for error messages

        Returns:
            Tuple of (DataFrame, error_message)
        """
        # Try different encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                return df, None
            except UnicodeDecodeError:
                continue
            except Exception as e:
                return None, f"Error parsing CSV file: {str(e)}"

        return None, "Could not decode CSV file. Please ensure it's saved as UTF-8."

    @classmethod
    def validate_dataframe(
        cls, df: pd.DataFrame, max_preview: int = 10
    ) -> ValidationResult:
        """
        Validate a DataFrame for teacher import.

        Args:
            df: DataFrame to validate
            max_preview: Maximum rows to include in preview

        Returns:
            ValidationResult with validation status and preview data
        """
        result = ValidationResult(is_valid=True)

        if df is None or df.empty:
            result.is_valid = False
            result.errors.append("No data found in the file.")
            return result

        # Check for required columns (case-insensitive)
        df_columns_lower = [col.lower().strip() for col in df.columns]
        column_mapping = {}

        for req_col in cls.REQUIRED_COLUMNS:
            found = False
            for i, col in enumerate(df_columns_lower):
                if col == req_col.lower():
                    column_mapping[req_col] = df.columns[i]
                    found = True
                    break
            if not found:
                result.is_valid = False
                result.errors.append(f"Missing required column: '{req_col}'")

        # Check for optional columns
        for opt_col in cls.OPTIONAL_COLUMNS:
            for i, col in enumerate(df_columns_lower):
                if col == opt_col.lower():
                    column_mapping[opt_col] = df.columns[i]
                    break

        if not result.is_valid:
            return result

        # Rename columns to standard names
        rename_map = {v: k for k, v in column_mapping.items()}
        df = df.rename(columns=rename_map)

        # Use existing validation logic
        validated_data, errors, warnings = validate_import_data(df)

        # Add warnings to result
        result.warnings.extend(warnings)

        if errors:
            result.is_valid = False
            result.errors.extend(errors)
            return result

        result.row_count = len(validated_data)
        result.preview_data = validated_data[:max_preview]

        if result.row_count == 0:
            result.is_valid = False
            result.errors.append("No valid data rows found after validation.")

        return result

    @classmethod
    def import_from_google_sheet(
        cls,
        sheet_url: str,
        tenant_id: int,
        academic_year: str,
        user_id: int,
        district_name: str,
    ) -> ImportResult:
        """
        Import teacher data from a Google Sheet URL.

        Args:
            sheet_url: Google Sheet URL or ID
            tenant_id: Tenant ID for scoping
            academic_year: Academic year (e.g., "2024-2025")
            user_id: User performing the import
            district_name: District name for the records

        Returns:
            ImportResult with success status and counts
        """
        # Extract sheet ID
        sheet_id = cls.extract_sheet_id(sheet_url)
        if not sheet_id:
            return ImportResult(
                success=False,
                error_message="Could not extract Google Sheet ID from the provided URL.",
            )

        # Read data
        df, error = cls.read_google_sheet(sheet_id)
        if error:
            return ImportResult(success=False, error_message=error)

        return cls._import_dataframe(
            df, tenant_id, academic_year, user_id, district_name, sheet_id
        )

    @classmethod
    def import_from_csv(
        cls,
        file_content: bytes,
        tenant_id: int,
        academic_year: str,
        user_id: int,
        district_name: str,
    ) -> ImportResult:
        """
        Import teacher data from a CSV file.

        Args:
            file_content: Raw bytes of CSV file
            tenant_id: Tenant ID for scoping
            academic_year: Academic year (e.g., "2024-2025")
            user_id: User performing the import
            district_name: District name for the records

        Returns:
            ImportResult with success status and counts
        """
        # Read CSV
        df, error = cls.read_csv_file(file_content)
        if error:
            return ImportResult(success=False, error_message=error)

        return cls._import_dataframe(
            df, tenant_id, academic_year, user_id, district_name
        )

    @classmethod
    def _import_dataframe(
        cls,
        df: pd.DataFrame,
        tenant_id: int,
        academic_year: str,
        user_id: int,
        district_name: str,
        sheet_id: Optional[str] = None,
    ) -> ImportResult:
        """
        Internal method to import a validated DataFrame.
        """
        # Validate
        validation = cls.validate_dataframe(df)
        if not validation.is_valid:
            return ImportResult(
                success=False, error_message="; ".join(validation.errors)
            )

        # Normalize column names for import
        df_columns_lower = {col.lower().strip(): col for col in df.columns}
        rename_map = {}
        for std_col in cls.REQUIRED_COLUMNS + cls.OPTIONAL_COLUMNS:
            if std_col.lower() in df_columns_lower:
                rename_map[df_columns_lower[std_col.lower()]] = std_col
        df = df.rename(columns=rename_map)

        # Re-validate with standard names
        validated_data, errors, warnings = validate_import_data(df)
        if errors:
            return ImportResult(success=False, error_message="; ".join(errors))

        # Log warnings
        if warnings:
            from flask import current_app

            for warning in warnings:
                current_app.logger.warning(f"Import warning: {warning}")

        try:
            # Use existing import logic
            import_log = import_roster(
                district_name=district_name,
                academic_year=academic_year,
                teacher_data=validated_data,
                user_id=user_id,
                sheet_id=sheet_id,
                tenant_id=tenant_id,
            )

            return ImportResult(
                success=True,
                records_added=import_log.records_added,
                records_updated=import_log.records_updated,
                records_deactivated=import_log.records_deactivated,
                records_skipped=len(warnings),
                warnings=warnings,
            )
        except Exception as e:
            return ImportResult(success=False, error_message=f"Import failed: {str(e)}")

    @classmethod
    def get_import_history(cls, tenant_id: int, limit: int = 20) -> List[dict]:
        """
        Get import history for a tenant.

        Note: This requires RosterImportLog to be fully functional.
        For now, returns an empty list as the log table isn't being used.
        """
        # TODO: Implement when RosterImportLog is enabled
        return []

    @classmethod
    def get_teacher_count(cls, tenant_id: int, academic_year: str) -> dict:
        """
        Get teacher counts for a tenant/year.

        Returns:
            Dict with active and total counts
        """
        active = TeacherProgress.query.filter_by(
            tenant_id=tenant_id, academic_year=academic_year, is_active=True
        ).count()

        total = TeacherProgress.query.filter_by(
            tenant_id=tenant_id, academic_year=academic_year
        ).count()

        return {"active": active, "total": total, "inactive": total - active}

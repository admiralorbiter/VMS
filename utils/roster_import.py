"""
Roster Import Utility
====================

Handles the logic for safely importing teacher rosters from Google Sheets.
Implements merge/upsert strategy instead of destructive replacement.
"""

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import func

from models import db
from models.roster_import_log import RosterImportLog
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress


def validate_import_data(df):
    """
    Validate the import dataframe.

    Returns:
        tuple: (validated_data, errors, warnings)
        - validated_data: List of valid teacher dictionaries
        - errors: List of critical errors that prevent import
        - warnings: List of warnings (like skipped duplicates)
    """
    required_columns = ["Building", "Name", "Email"]
    errors = []
    warnings = []

    # Check needed columns
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return None, [f"Missing required columns: {', '.join(missing_cols)}"], []

    validated_rows = []
    emails_seen = {}  # email -> first row number

    for index, row in df.iterrows():
        row_num = index + 2  # 1-indexed + header

        building = str(row.get("Building", "")).strip()
        name = str(row.get("Name", "")).strip()
        email = str(row.get("Email", "")).strip()
        grade = str(row.get("Grade", "")).strip()

        # Skip empty rows
        if not building and not name and not email:
            continue

        # Basic validation
        if not building or not name or not email:
            errors.append(
                f"Row {row_num}: Missing required fields (Building, Name, or Email)"
            )
            continue

        # Handle duplicates as warnings, not errors - skip the duplicate row
        email_lower = email.lower()
        if email_lower in emails_seen:
            first_row = emails_seen[email_lower]
            warnings.append(
                f"Row {row_num}: Skipped duplicate email '{email}' (first seen on row {first_row})"
            )
            continue

        emails_seen[email_lower] = row_num

        validated_rows.append(
            {
                "building": building,
                "name": name,
                "email": email,
                "grade": grade,
                "is_active": True,
            }
        )

    return validated_rows, errors, warnings


def import_roster(
    district_name, academic_year, teacher_data, user_id, sheet_id=None, tenant_id=None
):
    """
    Import roster using merge/upsert strategy.

    Args:
        district_name (str): Name of the district
        academic_year (str): Academic year (e.g. "2025-2026")
        teacher_data (list): List of validated teacher dictionaries
        user_id (int): ID of the user performing import
        sheet_id (str): Optional Google Sheet ID source
        tenant_id (int): Optional tenant ID for multi-tenant support

    Returns:
        RosterImportLog: The log entry for this import
    """
    # Temporary workaround: Skipping DB logging due to SQLite RETURNING issue
    # import_log = RosterImportLog(...)
    # db.session.add(import_log)
    # db.session.commit()

    # Mock log object for return compatibility
    class MockLog:
        def __init__(self):
            self.id = 0
            self.records_added = 0
            self.records_updated = 0
            self.records_deactivated = 0
            self.status = "success"

    import_log = MockLog()

    try:
        # 2. Get existing records for this district/year
        existing_records = TeacherProgress.query.filter_by(
            academic_year=academic_year, district_name=district_name
        ).all()

        # Map email -> record for quick lookup
        existing_map = {r.email.lower(): r for r in existing_records}

        records_added = 0
        records_updated = 0
        records_deactivated = 0

        # 3. Process Import Data (Upsert)
        processed_emails = set()

        for row in teacher_data:
            email_key = row["email"].lower()
            processed_emails.add(email_key)

            if email_key in existing_map:
                # Update existing - Using Core Update
                from sqlalchemy import update

                stmt = (
                    update(TeacherProgress)
                    .where(TeacherProgress.id == existing_map[email_key].id)
                    .values(
                        building=row["building"],
                        name=row["name"],
                        grade=row["grade"],
                        is_active=True,
                        updated_at=datetime.now(timezone.utc),
                    )
                )

                db.session.execute(stmt)
                db.session.commit()

                records_updated += 1
            else:
                # Simple ORM add with expunge to safe-guard against refresh
                new_record = TeacherProgress(
                    academic_year=academic_year,
                    virtual_year=academic_year,
                    building=row["building"],
                    name=row["name"],
                    email=row["email"],
                    grade=row["grade"],
                    target_sessions=1,
                    created_by=user_id,
                    teacher_id=None,
                )
                new_record.district_name = district_name
                new_record.is_active = True
                new_record.tenant_id = tenant_id  # Multi-tenant support
                new_record.created_at = datetime.now(timezone.utc)
                new_record.updated_at = datetime.now(timezone.utc)

                db.session.add(new_record)
                db.session.commit()
                db.session.expunge(new_record)

                records_added += 1

        # 4. Handle Removals (Soft Delete)

        # 4. Handle Removals (Soft Delete) - Using Core Update
        for email, record in existing_map.items():
            if email not in processed_emails and record.is_active:
                from sqlalchemy import update

                stmt = (
                    update(TeacherProgress)
                    .where(TeacherProgress.id == record.id)
                    .values(is_active=False, updated_at=datetime.now(timezone.utc))
                )

                db.session.execute(stmt)
                db.session.commit()

                records_deactivated += 1

        # 5. Commit & Update Log
        import_log.records_added = records_added
        import_log.records_updated = records_updated
        import_log.records_deactivated = records_deactivated
        import_log.status = "success"

        db.session.commit()
        return import_log

    except Exception as e:
        db.session.rollback()
        # import_log.status = "failed"
        # import_log.error_message = str(e)
        # db.session.commit()
        raise e

"""
Roster Import Utility
====================

Handles the logic for safely importing teacher rosters from Google Sheets.
Implements merge/upsert strategy instead of destructive replacement.
"""

import json
from datetime import datetime, timezone

import pandas as pd
from flask import current_app
from sqlalchemy import func

from models import db
from models.data_quality_flag import DataQualityIssueType, flag_data_quality_issue
from models.roster_import_log import RosterImportLog
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import DeactivationSource, TeacherProgress


def _find_school_by_building_name(building_name, district_id=None):
    """
    Fuzzy-match a building short name (e.g. 'TA Edison') to a School record.

    When district_id is provided, searches within that district first to avoid
    cross-district false matches.  Falls back to global search only if no
    district-scoped match is found.

    Matching strategy (applied district-scoped first, then global):
     1. Exact case-insensitive match
     2. Substring match (building name contained in school name)
     3. Word-by-word match (each word with len>2 searched individually)

    Returns:
        School object or None
    """
    if not building_name or not building_name.strip():
        return None

    b = building_name.strip()

    def _search(base_query):
        """Run the 3-tier match against a base query."""
        # 1. Exact match
        school = base_query.filter(func.upper(School.name) == b.upper()).first()
        if school:
            return school

        # 2. Substring match (building name IN school name)
        school = base_query.filter(School.name.ilike(f"%{b}%")).first()
        if school:
            return school

        # 3. Word-by-word fallback — search the longest word (skip abbreviations)
        words = [w for w in b.split() if len(w) > 2]
        if words:
            words.sort(key=len, reverse=True)
            for word in words:
                school = base_query.filter(School.name.ilike(f"%{word}%")).first()
                if school:
                    return school

        return None

    # District-scoped search first (prevents cross-district false matches)
    if district_id:
        result = _search(School.query.filter(School.district_id == district_id))
        if result:
            return result

    # Global fallback
    return _search(School.query)


def _link_progress_to_teachers(tenant_id, academic_year):
    """
    Link TeacherProgress records to existing Teacher records.

    Match priority (Sprint 1 — consolidated matching):
      1. Email match: TeacherProgress.email → Teacher.cached_email (exact, case-insensitive)
      2. Email match: TeacherProgress.email → Email model (fallback)
      3. Name match: normalized first+last name comparison

    For each match found:
      - Set TeacherProgress.teacher_id
      - Set Teacher.school_id from building name (if currently None)
      - Cache the email on Teacher.cached_email (if not already set)
    """
    from models.tenant import Tenant
    from services.teacher_matching_service import normalize_name

    # Resolve district_id for district-scoped school matching
    district_id = None
    if tenant_id:
        tenant = Tenant.query.get(tenant_id)
        if tenant and tenant.district_id:
            district_id = tenant.district_id

    if tenant_id:
        progress_records = TeacherProgress.query.filter_by(
            academic_year=academic_year, tenant_id=tenant_id
        ).all()
    else:
        progress_records = TeacherProgress.query.filter_by(
            academic_year=academic_year
        ).all()

    linked_count = 0
    school_set_count = 0

    for tp in progress_records:
        # Skip if already linked
        if tp.teacher_id:
            continue

        teacher = None

        # Priority 1: Match by email (highest confidence)
        if tp.email:
            email_lower = tp.email.strip().lower()

            # 1a: Check Teacher.cached_email (fast, indexed)
            teacher = Teacher.query.filter(
                func.lower(Teacher.cached_email) == email_lower
            ).first()

            # 1b: Check Email model (slower fallback)
            if not teacher:
                from models.contact import Email

                email_record = (
                    Email.query.filter(func.lower(Email.email) == email_lower)
                    .join(Teacher, Email.contact_id == Teacher.id)
                    .first()
                )
                if email_record:
                    teacher = Teacher.query.get(email_record.contact_id)

        # Priority 2: Match by normalized name (lower confidence)
        if not teacher and tp.name:
            name_parts = tp.name.strip().split(" ", 1)
            if len(name_parts) >= 2:
                normalized_first = normalize_name(name_parts[0])
                normalized_last = normalize_name(name_parts[1])

                # Query candidates and compare normalized names
                candidates = Teacher.query.filter(Teacher.active == True).all()
                for candidate in candidates:
                    if (
                        normalize_name(candidate.first_name or "") == normalized_first
                        and normalize_name(candidate.last_name or "") == normalized_last
                    ):
                        teacher = candidate
                        break

        if not teacher:
            continue

        # Link TeacherProgress → Teacher
        tp.teacher_id = teacher.id
        linked_count += 1

        # Cache email on teacher for faster future matching
        if tp.email and not teacher.cached_email:
            teacher.cached_email = tp.email.strip().lower()

        # Set school_id on Teacher if not already set
        if not teacher.school_id and tp.building:
            school = _find_school_by_building_name(tp.building, district_id=district_id)
            if school:
                teacher.school_id = school.id
                school_set_count += 1

    if linked_count > 0 or school_set_count > 0:
        db.session.commit()

    try:
        current_app.logger.info(
            f"Teacher linking: {linked_count} TeacherProgress records linked, "
            f"{school_set_count} Teacher school_ids set"
        )
    except RuntimeError:
        # Outside app context (e.g. testing)
        pass

    return linked_count, school_set_count


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
    # 1. Create audit log entry (ORM add + flush — no RETURNING clause needed)
    import_log = RosterImportLog(
        district_name=district_name,
        academic_year=academic_year,
        imported_by=user_id,
        source_sheet_id=sheet_id,
        status="pending",
    )
    db.session.add(import_log)
    db.session.flush()  # Assigns import_log.id via SQLite-compatible SELECT

    try:
        # 2. Get existing records for this district/year
        # Use tenant_id when available (preferred); fall back to district_name
        # for legacy non-tenant imports.
        if tenant_id:
            existing_records = TeacherProgress.query.filter_by(
                academic_year=academic_year, tenant_id=tenant_id
            ).all()
        else:
            existing_records = TeacherProgress.query.filter_by(
                academic_year=academic_year, district_name=district_name
            ).all()

        # Map email -> record for quick lookup
        existing_map = {r.email.lower(): r for r in existing_records}

        records_added = 0
        records_updated = 0
        records_deactivated = 0
        records_flagged = 0
        flagged_details_list = []

        # 3. Process Import Data (Upsert)
        processed_emails = set()

        for row in teacher_data:
            email_key = row["email"].lower()
            processed_emails.add(email_key)

            if email_key in existing_map:
                existing_record = existing_map[email_key]

                # Check for Intentional Removal protection
                target_is_active = True
                if (
                    getattr(existing_record, "deactivation_source", None)
                    == DeactivationSource.MANUAL_ADMIN
                    and not existing_record.is_active
                ):
                    target_is_active = False
                    records_flagged += 1

                    reason = (
                        existing_record.deactivation_reason
                        or "Intentional Admin Removal"
                    )
                    flagged_details_list.append(
                        {
                            "email": existing_record.email,
                            "name": existing_record.name,
                            "reason": reason,
                            "date": (
                                existing_record.deactivated_at.isoformat()
                                if existing_record.deactivated_at
                                else None
                            ),
                        }
                    )

                    flag_data_quality_issue(
                        entity_type="teacher",
                        entity_id=existing_record.id,
                        issue_type=DataQualityIssueType.PROTECTED_TEACHER_SKIPPED,
                        details=json.dumps(
                            {
                                "email": existing_record.email,
                                "reason": reason,
                                "last_challenged_at": datetime.now(
                                    timezone.utc
                                ).isoformat(),
                            }
                        ),
                        source="roster_import",
                    )

                # Update existing - Using Core Update
                from sqlalchemy import update

                stmt = (
                    update(TeacherProgress)
                    .where(TeacherProgress.id == existing_record.id)
                    .values(
                        building=row["building"],
                        name=row["name"],
                        grade=row["grade"],
                        is_active=target_is_active,
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

        # 4. Handle Removals (Soft Delete) - Using Core Update
        for email, record in existing_map.items():
            if email not in processed_emails and record.is_active:
                from sqlalchemy import update

                stmt = (
                    update(TeacherProgress)
                    .where(TeacherProgress.id == record.id)
                    .values(
                        is_active=False,
                        deactivation_source=DeactivationSource.IMPORT_DIFF,
                        updated_at=datetime.now(timezone.utc),
                    )
                )

                db.session.execute(stmt)
                db.session.commit()

                records_deactivated += 1

        # 5. Link TeacherProgress records to Teacher entities
        _link_progress_to_teachers(tenant_id, academic_year)

        # 6. Update audit log with results
        import_log.records_added = records_added
        import_log.records_updated = records_updated
        import_log.records_deactivated = records_deactivated
        import_log.records_flagged = records_flagged
        import_log.flagged_details = (
            json.dumps(flagged_details_list) if flagged_details_list else None
        )
        import_log.status = "success"

        db.session.commit()
        return import_log

    except Exception as e:
        db.session.rollback()
        # Log the failure in a new transaction
        try:
            import_log_fail = RosterImportLog(
                district_name=district_name,
                academic_year=academic_year,
                imported_by=user_id,
                source_sheet_id=sheet_id,
                status="failed",
                error_message=str(e),
            )
            db.session.add(import_log_fail)
            db.session.commit()
        except Exception:
            pass  # Don't mask the original error
        raise e

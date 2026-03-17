"""
Row processing functions for Pathful imports.

Handles processing individual rows from Pathful Session Reports, including
role-based routing to teacher/volunteer matching and event linking.
"""

from datetime import datetime, timezone

import pandas as pd
from flask import current_app
from sqlalchemy import func

from models import db
from models.event import EventStatus
from models.school_model import School

from .matching import (
    match_or_create_event,
    match_teacher,
    match_volunteer,
    upsert_district,
)
from .parsing import (
    PARTNER_FILTER,
    parse_name,
    parse_pathful_date,
    safe_int,
    safe_str,
    serialize_row_for_json,
)


def _parse_pathful_count(value):
    """Parse Pathful count columns (e.g. Attended Educator Count).

    Returns int if the value is a valid number, None for 'n/a', NaN, empty, etc.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return int(value)
    s = str(value).strip().lower()
    if s in ("n/a", "na", "nan", "none", "nat", ""):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _reverse_link_teacher_progress(teacher_id):
    """Link an unlinked TeacherProgress to a Teacher when match_teacher failed.

    Delegates to the centralized ``resolve_teacher_for_tp`` in
    ``teacher_matching_service`` for consistent matching across the system.

    This closes the ordering-dependency gap where session data is imported
    before user-profile data.
    """
    from models.teacher import Teacher
    from models.teacher_progress import TeacherProgress
    from services.teacher_matching_service import normalize_name

    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        return

    # Find unlinked TPs that could match this teacher by email or name
    candidates = TeacherProgress.query.filter(
        TeacherProgress.teacher_id.is_(None),
    ).all()

    # Build Teacher's normalized name and first+last name
    teacher_full = f"{teacher.first_name or ''} {teacher.last_name or ''}"
    teacher_normalized = normalize_name(teacher_full)
    teacher_email = (teacher.cached_email or "").strip().lower()
    # For first+last matching (ignores middle names in TP)
    teacher_first_last = normalize_name(
        f"{teacher.first_name or ''} {teacher.last_name or ''}"
    )

    for tp in candidates:
        # Match by email
        if teacher_email and tp.email and tp.email.strip().lower() == teacher_email:
            tp.teacher_id = teacher_id
            return
        # Match by normalized full name
        if tp.name and normalize_name(tp.name) == teacher_normalized:
            tp.teacher_id = teacher_id
            return
        # Match by first+last (skip middle names)
        if tp.name:
            parts = tp.name.strip().split()
            if len(parts) >= 2:
                tp_first_last = normalize_name(f"{parts[0]} {parts[-1]}")
                if tp_first_last == teacher_first_last:
                    tp.teacher_id = teacher_id
                    return


def process_session_report_row(
    row, row_index, import_log, processed_events, caches=None
):
    """
    Process a single row from the Pathful Session Report.

    Args:
        row: DataFrame row
        row_index: Row index (1-based)
        import_log: PathfulImportLog instance
        processed_events: Dict to track processed events by session_id

    Returns:
        bool: True if row was processed successfully
    """
    try:
        # Extract key fields
        partner = safe_str(row.get("Partner", ""))
        signup_role = safe_str(row.get("SignUp Role", "")).lower()

        # Filter: Only PREP-KC partner
        if partner.upper() != PARTNER_FILTER:
            import_log.skipped_rows += 1
            return True

        # Filter: Skip students and parents
        if signup_role in ["student", "parent"]:
            import_log.skipped_rows += 1
            return True

        # Extract session data
        session_id = row.get("Session ID")
        title = safe_str(row.get("Title"))
        date_value = row.get("Date")
        status = safe_str(row.get("Status"))
        duration = row.get("Duration")
        career_cluster = safe_str(row.get("Career Cluster"))

        # Parse date
        session_date = parse_pathful_date(date_value)
        if not session_date:
            # Only warn for genuinely unparseable dates, not empty/NaT values
            date_str = str(date_value).strip().lower() if date_value is not None else ""
            if date_str and date_str not in ("nat", "nan", "none", ""):
                current_app.logger.warning(
                    f"Row {row_index}: Could not parse date '{date_value}'"
                )
            import_log.skipped_rows += 1
            return True

        if not title:
            current_app.logger.warning("Row %s: Missing title", row_index)
            import_log.error_count += 1
            return False

        # Get or create event (idempotent)
        session_id_str = (
            str(session_id)
            if session_id and not pd.isna(session_id)
            else f"{title}_{session_date.date()}"
        )

        if session_id_str in processed_events:
            event = processed_events[session_id_str]
            match_type = "cached"
        else:
            event, match_type = match_or_create_event(
                session_id,
                title,
                session_date,
                status,
                duration,
                career_cluster,
                import_log,
                caches=caches,
            )
            processed_events[session_id_str] = event

            if (
                match_type == "matched_by_session_id"
                or match_type == "matched_by_title_date"
            ):
                import_log.updated_events += 1

        # Update student counts on event
        registered_students = safe_int(row.get("Registered Student Count"))
        attended_students = safe_int(row.get("Attended Student Count"))

        if registered_students > 0:
            event.registered_student_count = max(
                event.registered_student_count or 0, registered_students
            )
        if attended_students > 0:
            event.attended_student_count = max(
                event.attended_student_count or 0, attended_students
            )

        # Update educator attendance count on event (for auditing)
        att_edu_raw = _parse_pathful_count(row.get("Attended Educator Count"))
        if att_edu_raw is not None and att_edu_raw > 0:
            event.attended_educator_count = max(
                event.attended_educator_count or 0, att_edu_raw
            )

        # Extract participant data
        name = safe_str(row.get("Name"))
        user_auth_id = row.get("User Auth Id")
        school = safe_str(row.get("School"))
        district_or_company = safe_str(row.get("District or Company"))

        # Convert row to dict for unmatched record storage
        raw_data = serialize_row_for_json(row)

        # Process based on role
        if signup_role == "educator":
            # Match teacher via TeacherProgress
            teacher_progress = match_teacher(
                name=name,
                email="",  # Session report doesn't have email, only User Auth Id
                school_name=school,
                pathful_user_id=user_auth_id,
                import_log=import_log,
                row_number=row_index,
                raw_data=raw_data,
                caches=caches,
            )

            # Link teacher to event via EventTeacher FK (cache-first)
            from models.event import EventTeacher as _ET
            from services.teacher_matching_service import normalize_name as _norm

            teacher_id_to_link = None
            if teacher_progress and teacher_progress.teacher_id:
                teacher_id_to_link = teacher_progress.teacher_id
            elif name:
                # Try cache-first Teacher resolution before DB
                first_name, last_name = parse_name(name)
                if first_name or last_name:
                    norm_key = f"{_norm(first_name)} {_norm(last_name)}".strip()
                    cached_teacher = None
                    if caches:
                        cached_teacher = caches["teacher_record_by_name"].get(norm_key)
                    if cached_teacher:
                        teacher_id_to_link = cached_teacher.id
                    else:
                        from services.teacher_service import find_or_create_teacher

                        teacher_record, is_new, _match_info = find_or_create_teacher(
                            first_name=first_name,
                            last_name=last_name,
                            import_source="pathful",
                        )
                        teacher_id_to_link = teacher_record.id
                        # Update cache for subsequent rows
                        if caches and norm_key:
                            caches["teacher_record_by_name"][norm_key] = teacher_record

                    # Backfill teacher_id onto TeacherProgress so future
                    # counting can use the EventTeacher FK path (prevents drift)
                    if (
                        teacher_id_to_link
                        and teacher_progress
                        and not teacher_progress.teacher_id
                    ):
                        teacher_progress.teacher_id = teacher_id_to_link

                    # ── Option C: Reverse backfill ─────────────────────────
                    # When match_teacher() returned None (no TeacherProgress
                    # found), but we resolved a Teacher record, try to find
                    # an unlinked TeacherProgress by the Teacher's email and
                    # link them.  This closes the gap when session data is
                    # imported before user data.
                    if teacher_id_to_link and not teacher_progress:
                        _reverse_link_teacher_progress(teacher_id_to_link)

            # Derive teacher attendance status from Attended Educator Count
            # and the event status.  Attended Educator Count is the primary
            # signal for completed events:
            #   1 (or any positive int) → teacher attended
            #   n/a / None              → teacher registered but never showed
            mapped_event_status = EventStatus.map_status(status)
            att_edu = _parse_pathful_count(row.get("Attended Educator Count"))

            if mapped_event_status == EventStatus.COMPLETED:
                if att_edu is not None and att_edu >= 1:
                    et_status = "attended"
                else:
                    et_status = "no_show"
            elif mapped_event_status in (
                EventStatus.CANCELLED,
                EventStatus.NO_SHOW,
            ):
                et_status = "no_show"
            else:
                et_status = "registered"

            # Create or update EventTeacher (cache-first, DB-fallback)
            if teacher_id_to_link:
                et_key = (event.id, teacher_id_to_link)
                et_set = caches["event_teacher_set"] if caches else set()
                if et_key not in et_set:
                    # Key not in this import's cache — check DB for records
                    # created in prior imports or via other paths (manual,
                    # Salesforce, session edit, etc.)
                    existing_et = _ET.query.filter_by(
                        event_id=event.id, teacher_id=teacher_id_to_link
                    ).first()
                    if existing_et:
                        # Update stale status (e.g. "registered" on a now-
                        # completed event).  Respect admin overrides (notes).
                        if (
                            not existing_et.notes
                            and existing_et.status != et_status
                            and et_status in ("attended", "no_show")
                        ):
                            existing_et.status = et_status
                            existing_et.attendance_confirmed_at = (
                                datetime.now(timezone.utc)
                                if et_status == "attended"
                                else None
                            )
                    else:
                        et = _ET(
                            event_id=event.id,
                            teacher_id=teacher_id_to_link,
                            status=et_status,
                            attendance_confirmed_at=(
                                datetime.now(timezone.utc)
                                if et_status == "attended"
                                else None
                            ),
                        )
                        db.session.add(et)
                    if caches:
                        caches["event_teacher_set"].add(et_key)
                else:
                    # Key already processed in this import run — update if
                    # status has changed (e.g. row with different att count).
                    # Respect admin overrides: skip records where notes is set.
                    if et_status in ("attended", "no_show"):
                        existing_et = _ET.query.filter_by(
                            event_id=event.id, teacher_id=teacher_id_to_link
                        ).first()
                        if existing_et and existing_et.status != et_status:
                            if not existing_et.notes:
                                existing_et.status = et_status
                                existing_et.attendance_confirmed_at = (
                                    datetime.now(timezone.utc)
                                    if et_status == "attended"
                                    else None
                                )

            # Text cache (Event.educators) is regenerated post-import
            # by sync_event_participant_fields — no manual accumulation needed

            # ONLY store district from Educator rows (Professional rows have company, not district)
            if district_or_company and not event.district_partner:
                event.district_partner = district_or_company
                # Also upsert and link to District model for proper FK relationship
                district_record = upsert_district(district_or_company, caches=caches)
                if district_record and district_record not in event.districts:
                    event.districts.append(district_record)

            # Store school info from Educator rows
            if school and school.upper() != "PREP-KC":  # Skip "PREP-KC" as school name
                if not event.school:
                    # Try to match school to existing School record (cache first)
                    if caches:
                        school_record = caches["school_by_name"].get(school.lower())
                    else:
                        school_record = School.query.filter(
                            func.lower(School.name) == func.lower(school)
                        ).first()
                    if school_record:
                        event.school = school_record.id
                # Always store school name in location as fallback display
                if not event.location:
                    event.location = school

        elif signup_role == "professional":
            # Match volunteer
            volunteer = match_volunteer(
                name=name,
                email="",  # Session report doesn't have email
                organization_name=district_or_company,  # This is their company/employer
                pathful_user_id=user_auth_id,
                import_log=import_log,
                row_number=row_index,
                raw_data=raw_data,
                caches=caches,
            )
            # If matched, link volunteer to event
            if volunteer and volunteer not in event.volunteers:
                event.volunteers.append(volunteer)

            # Store professional name on event (accumulate if multiple)
            if name:
                current_professionals = set(
                    filter(None, (event.professionals or "").split("; "))
                )
                current_professionals.add(name)
                event.professionals = "; ".join(sorted(current_professionals))

        import_log.processed_rows += 1
        return True

    except Exception as e:
        current_app.logger.error("Row %s: Error processing - %s", row_index, str(e))
        import_log.error_count += 1
        return False

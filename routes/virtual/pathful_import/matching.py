"""
Entity matching and creation functions for Pathful imports.

Provides cache-based matching for teachers, volunteers, events, and districts.
"""

from datetime import timedelta

import pandas as pd
from flask import current_app
from sqlalchemy import func

from models import db
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventType
from models.pathful_import import PathfulUnmatchedRecord, UnmatchedType
from models.school_model import School
from models.teacher_progress import TeacherProgress
from models.volunteer import Volunteer

from .parsing import parse_name, safe_int, safe_str


def build_import_caches():
    """
    Pre-load all lookup data into dicts to avoid per-row DB queries.

    Returns:
        dict of caches keyed by name
    """
    from models.contact import Email as ContactEmail

    print("Building import caches...")

    # Teacher caches (TeacherProgress)
    all_teachers = TeacherProgress.query.all()
    teacher_by_pathful_id = {}
    teacher_by_email = {}
    teacher_by_name = {}
    for t in all_teachers:
        if t.pathful_user_id:
            teacher_by_pathful_id[t.pathful_user_id] = t
        if t.email:
            teacher_by_email[t.email.lower()] = t
        if t.name:
            teacher_by_name[t.name.lower()] = t
    print(
        f"  Teachers: {len(all_teachers)} ({len(teacher_by_pathful_id)} by pathful_id, {len(teacher_by_email)} by email)"
    )

    # Volunteer caches
    all_volunteers = Volunteer.query.all()
    volunteer_by_pathful_id = {}
    volunteer_by_name = {}
    for v in all_volunteers:
        if v.pathful_user_id:
            volunteer_by_pathful_id[v.pathful_user_id] = v
        if v.first_name and v.last_name:
            volunteer_by_name[(v.first_name.lower(), v.last_name.lower())] = v

    # Volunteer email cache (requires joining Email table)
    volunteer_by_email = {}
    volunteer_emails = (
        db.session.query(ContactEmail.email, ContactEmail.contact_id)
        .join(Volunteer, Volunteer.id == ContactEmail.contact_id)
        .all()
    )
    vol_id_map = {v.id: v for v in all_volunteers}
    for email_addr, contact_id in volunteer_emails:
        if email_addr and contact_id in vol_id_map:
            volunteer_by_email[email_addr.lower()] = vol_id_map[contact_id]
    print(
        f"  Volunteers: {len(all_volunteers)} ({len(volunteer_by_pathful_id)} by pathful_id, {len(volunteer_by_email)} by email)"
    )

    # School cache
    all_schools = School.query.all()
    school_by_name = {s.name.lower(): s for s in all_schools if s.name}
    print(f"  Schools: {len(all_schools)}")

    # District cache (includes aliases for Pathful name resolution)
    from models.district_model import DistrictAlias

    all_districts = District.query.all()
    district_by_name = {d.name.lower(): d for d in all_districts if d.name}
    # Also index all aliases so cache lookup resolves different spellings
    all_aliases = DistrictAlias.query.all()
    for alias in all_aliases:
        district_by_name[alias.alias.lower()] = alias.district
    print(f"  Districts: {len(all_districts)} ({len(all_aliases)} aliases)")

    # Event caches
    all_events = Event.query.filter(Event.type == EventType.VIRTUAL_SESSION).all()
    event_by_session_id = {}
    event_by_title_date = {}
    for e in all_events:
        if e.pathful_session_id:
            event_by_session_id[e.pathful_session_id] = e
        if e.title and e.start_date:
            event_by_title_date[(e.title.lower().strip(), e.start_date.date())] = e
    print(f"  Events: {len(all_events)} ({len(event_by_session_id)} by session_id)")

    # EventTeacher existence cache — avoids per-row SELECT in ensure_event_teacher
    from models.event import EventTeacher

    all_et = EventTeacher.query.all()
    event_teacher_set = {(et.event_id, et.teacher_id) for et in all_et}
    print(f"  EventTeacher links: {len(event_teacher_set)}")

    # Teacher model caches — avoids loading ALL teachers in find_or_create_teacher
    from models.teacher import Teacher
    from services.teacher_matching_service import normalize_name

    all_teacher_records = Teacher.query.filter(Teacher.active == True).all()
    teacher_record_by_email = {}
    teacher_record_by_name = {}
    for t in all_teacher_records:
        if t.cached_email:
            teacher_record_by_email[t.cached_email.lower()] = t
        norm_first = normalize_name(t.first_name or "")
        norm_last = normalize_name(t.last_name or "")
        norm_name = f"{norm_first} {norm_last}".strip()
        if norm_name:
            teacher_record_by_name[norm_name] = t
        # Also index by first-word + first-word-of-last for multi-part surname
        # matching (e.g., "catalina velarde" for Teacher "Catalina Velarde Duarte")
        if norm_first and norm_last and " " in norm_last:
            first_word_of_last = norm_last.split()[0]
            short_key = f"{norm_first} {first_word_of_last}"
            # Only set if not already claimed by another teacher (avoid collisions)
            teacher_record_by_name.setdefault(short_key, t)
    print(
        f"  Teacher records: {len(all_teacher_records)} ({len(teacher_record_by_email)} by email, {len(teacher_record_by_name)} by name)"
    )

    # Organization cache (includes aliases for Epic 19 resolution)
    from models.organization import Organization, OrganizationAlias

    all_orgs = Organization.query.all()
    organization_by_name = {o.name.lower(): o for o in all_orgs if o.name}
    all_org_aliases = OrganizationAlias.query.all()
    for alias in all_org_aliases:
        organization_by_name[alias.name.lower()] = alias.organization
    print(f"  Organizations: {len(all_orgs)} ({len(all_org_aliases)} aliases)")

    print("Caches built.\n")

    return {
        "teacher_by_pathful_id": teacher_by_pathful_id,
        "teacher_by_email": teacher_by_email,
        "teacher_by_name": teacher_by_name,
        "volunteer_by_pathful_id": volunteer_by_pathful_id,
        "volunteer_by_email": volunteer_by_email,
        "volunteer_by_name": volunteer_by_name,
        "school_by_name": school_by_name,
        "district_by_name": district_by_name,
        "event_by_session_id": event_by_session_id,
        "event_by_title_date": event_by_title_date,
        "event_teacher_set": event_teacher_set,
        "teacher_record_by_email": teacher_record_by_email,
        "teacher_record_by_name": teacher_record_by_name,
        "organization_by_name": organization_by_name,
    }


def upsert_district(district_name, caches=None):
    """
    Find or create a District record by name.

    Uses resolve_district() for alias-aware matching, preventing duplicate
    Districts when Pathful sends a different spelling (e.g. "Kansas City,
    KS (KCKPS) Public Schools" vs the canonical "Kansas City Kansas School
    District").

    When an existing district is found by alias but the incoming name is NOT
    yet registered as an alias, it is automatically added to DistrictAlias
    so the teacher progress dashboard can find events using that string.

    Args:
        district_name: Name of the district from Pathful data
        caches: Pre-built import caches (optional)

    Returns:
        District: Found or created District instance
    """
    if not district_name:
        return None

    from models.district_model import DistrictAlias
    from services.district_service import resolve_district

    # 1. Cache lookup (fast, avoids DB round-trip for repeated rows)
    if caches:
        cached = caches["district_by_name"].get(district_name.lower())
        if cached:
            return cached

    # 2. Alias-aware resolution (canonical name → alias → case-insensitive)
    district = resolve_district(district_name)

    if district:
        # Auto-register the Pathful string as an alias if it differs from
        # the canonical name and isn't already registered.
        if district_name != district.name:
            existing_alias = DistrictAlias.query.filter_by(alias=district_name).first()
            if not existing_alias:
                new_alias = DistrictAlias(alias=district_name, district_id=district.id)
                db.session.add(new_alias)
                db.session.flush()
                current_app.logger.info(
                    f"Auto-registered DistrictAlias: "
                    f"'{district_name}' -> '{district.name}'"
                )

        # Update cache
        if caches:
            caches["district_by_name"][district_name.lower()] = district
        return district

    # 3. No match — create a new District record
    import re

    # Generate district code from name
    acronym_match = re.search(r"\(([A-Z]+)\)", district_name)
    if acronym_match:
        code = acronym_match.group(1)
    else:
        simplified = re.sub(
            r"\s*(School District|Public Schools|Schools)$",
            "",
            district_name,
            flags=re.IGNORECASE,
        )
        first_part = simplified.split(",")[0].strip()
        code = re.sub(r"[^A-Z0-9-]", "", first_part.upper().replace(" ", "-"))[:20]

    # Ensure code uniqueness
    base_code = code
    suffix = 1
    while District.query.filter(District.district_code == code).first():
        code = f"{base_code}-{suffix}"
        suffix += 1

    district = District(
        name=district_name,
        district_code=code,
        salesforce_id=None,
    )
    db.session.add(district)
    db.session.flush()

    # Add to cache
    if caches:
        caches["district_by_name"][district_name.lower()] = district

    current_app.logger.info("Created new District: %s (code=%s)", district_name, code)
    return district


def match_or_create_event(
    session_id,
    title,
    session_date,
    status_str,
    duration,
    career_cluster,
    import_log,
    caches=None,
):
    """
    Find existing event or create new one (idempotent).

    Matching priority:
    1. pathful_session_id (exact match)
    2. title + date (flexible match)

    When matched, the event status is updated if the incoming status
    represents a forward progression in the lifecycle:
        DRAFT -> REQUESTED -> CONFIRMED -> PUBLISHED -> COMPLETED
    Cancelled/No-Show are treated as terminal and always accepted.

    Args:
        session_id: Pathful Session ID
        title: Session title
        session_date: Session date
        status_str: Status string
        duration: Duration in minutes
        career_cluster: Career cluster category
        import_log: PathfulImportLog instance for tracking

    Returns:
        tuple: (Event, match_type) where match_type is 'matched' or 'created'
    """
    # Status progression order (higher index = further along in lifecycle)
    STATUS_ORDER = {
        EventStatus.DRAFT: 0,
        EventStatus.REQUESTED: 1,
        EventStatus.CONFIRMED: 2,
        EventStatus.PUBLISHED: 3,
        EventStatus.COMPLETED: 4,
    }

    def _should_update_status(current_status, new_status):
        """Return True if new_status is a forward progression from current_status."""
        # Terminal statuses (Cancelled, No Show, etc.) always accepted
        if new_status in (
            EventStatus.CANCELLED,
            EventStatus.NO_SHOW,
            EventStatus.SIMULCAST,
        ):
            return True
        cur_order = STATUS_ORDER.get(current_status, -1)
        new_order = STATUS_ORDER.get(new_status, -1)
        return new_order > cur_order

    def _update_matched_event(event, status_str, career_cluster):
        """Update fields on a matched event that may have changed since last import."""
        if career_cluster and not event.career_cluster:
            event.career_cluster = career_cluster

        # Update status if it has progressed
        if status_str:
            new_status = EventStatus.map_status(status_str)
            if _should_update_status(event.status, new_status):
                event.status = new_status
                event.original_status_string = status_str

    session_id_str = str(session_id) if session_id and not pd.isna(session_id) else None

    # Priority 1: Match by pathful_session_id
    if session_id_str:
        event = (
            caches["event_by_session_id"].get(session_id_str)
            if caches
            else Event.query.filter(Event.pathful_session_id == session_id_str).first()
        )
        if event:
            _update_matched_event(event, status_str, career_cluster)
            return event, "matched_by_session_id"

    # Priority 2: Match by title + date
    if title and session_date:
        cache_key = (title.lower().strip(), session_date.date())
        event = (
            caches["event_by_title_date"].get(cache_key)
            if caches
            else Event.query.filter(
                func.lower(Event.title) == func.lower(title.strip()),
                func.date(Event.start_date) == session_date.date(),
                Event.type == EventType.VIRTUAL_SESSION,
            ).first()
        )

        if event:
            # Update pathful_session_id if not set
            if session_id_str and not event.pathful_session_id:
                event.pathful_session_id = session_id_str
            _update_matched_event(event, status_str, career_cluster)
            return event, "matched_by_title_date"

    # No match: Create new event
    mapped_status = EventStatus.map_status(status_str)

    event = Event(
        title=title,
        start_date=session_date,
        end_date=session_date,  # Will be updated if duration is known
        duration=safe_int(duration, 60),
        type=EventType.VIRTUAL_SESSION,
        format=EventFormat.VIRTUAL,
        status=mapped_status,
        original_status_string=status_str,
        pathful_session_id=session_id_str,
        career_cluster=career_cluster,
        import_source="pathful_direct",
        session_host="PREPKC",
    )

    # Calculate end_date from duration
    if duration and session_date:
        event.end_date = session_date + timedelta(minutes=safe_int(duration, 60))

    db.session.add(event)
    db.session.flush()  # Get the event.id

    # Add to caches for subsequent rows
    if caches:
        if session_id_str:
            caches["event_by_session_id"][session_id_str] = event
        if title and session_date:
            caches["event_by_title_date"][
                (title.lower().strip(), session_date.date())
            ] = event

    import_log.created_events += 1
    return event, "created"


def _try_resolve_teacher_school(
    teacher,
    school_name: str,
    import_log,
    row_number: int,
    raw_data: dict,
    caches=None,
) -> bool:
    """Resolve a school name from Pathful to a Teacher.salesforce_school_id FK.

    Only sets the school if:
      1. school_name is non-empty
      2. teacher.salesforce_school_id is currently None
         (i.e. not already assigned by Google Sheets roster or Salesforce sync,
         which are authoritative sources and must not be overwritten here)

    Tries three lookups in order:
      1. Exact case-insensitive match on School.name
      2. Case-insensitive match on School.normalized_name (handles ALL CAPS variants)
      3. Strip trailing " School" word and retry 1+2
         (Pathful appends "Elementary School", "High School", etc.
          while the DB stores "Frances Willard Elementary", "Dobbs Elementary", etc.)

    Args:
        teacher: Teacher model instance to update
        school_name: Raw school name string from Pathful CSV
        import_log: PathfulImportLog instance for unmatched tracking
        row_number: Original CSV row number for unmatched tracking
        raw_data: Original CSV row dict for unmatched tracking
        caches: Shared dict for cross-row memoization and deduplication

    Returns:
        True if the school was resolved and the FK was set, False otherwise.
    """
    import re

    if not school_name or not school_name.strip():
        return False
    if teacher.salesforce_school_id:
        # Already set by an authoritative source — do not overwrite.
        return False

    def _lookup(name_str):
        """Try exact then normalized match for a single name string."""
        n = name_str.strip().lower()
        hit = School.query.filter(func.lower(School.name) == n).first()
        if not hit:
            hit = School.query.filter(func.lower(School.normalized_name) == n).first()
        return hit

    school = _lookup(school_name)

    if not school:
        # Pass 3: strip trailing " School" (Pathful adds it, DB usually omits it)
        stripped = re.sub(
            r"\s+School\s*$", "", school_name.strip(), flags=re.IGNORECASE
        ).strip()
        if stripped and stripped.lower() != school_name.strip().lower():
            school = _lookup(stripped)

    if not school and stripped:
        # Pass 4: convert common expansions to match normalized_name abbreviations in DB
        # e.g., "M E Pearson Elementary" -> "M E Pearson Elem"
        # e.g., "Sumner Academy of Arts and Science" -> "Sumner Academy of Arts & Science"
        abbreviated = (
            stripped.lower().replace(" elementary", " elem").replace(" and ", " & ")
        )
        if abbreviated != stripped.lower():
            # Only check normalized_name for this highly-mangled variant
            school = School.query.filter(
                func.lower(School.normalized_name) == abbreviated
            ).first()

    if school:
        teacher.salesforce_school_id = school.id
        current_app.logger.debug(
            "Pathful school resolved: %r -> School %s (%s)",
            school_name,
            school.id,
            school.name,
        )
        return True

    current_app.logger.debug(
        "Pathful school not resolved in DB: %r (teacher %s)",
        school_name,
        teacher.id,
    )

    # ── Create Unmatched Record ──────────────────────────────
    # Avoid spamming the DB by deduplicating using caches if available.
    # We only want one notification per unique school name per import.
    dedup_key = school_name.strip().lower()

    if caches is not None:
        if "unresolved_schools" not in caches:
            caches["unresolved_schools"] = set()

        if dedup_key in caches["unresolved_schools"]:
            return False

        caches["unresolved_schools"].add(dedup_key)

    unmatched = PathfulUnmatchedRecord(
        import_log_id=import_log.id,
        row_number=row_number,
        raw_data=raw_data,
        unmatched_type=UnmatchedType.SCHOOL_UNRESOLVED,
        attempted_match_name=f"{teacher.first_name} {teacher.last_name}".strip(),
        attempted_match_school=school_name,
    )
    # Link the teacher so admin can go straight to the record
    unmatched.resolved_teacher_id = teacher.id

    db.session.add(unmatched)
    import_log.unmatched_count += 1

    return False


def match_teacher(
    name,
    email,
    school_name,
    pathful_user_id,
    import_log,
    row_number,
    raw_data,
    caches=None,
):
    """
    Match a teacher from Pathful data to existing TeacherProgress records.

    Matching priority:
    1. pathful_user_id (exact match)
    2. email (normalized, case-insensitive)
    3. name + school (fuzzy match)

    Args:
        name: Teacher name
        email: Teacher email (may be empty)
        school_name: School name
        pathful_user_id: Pathful User Auth Id
        import_log: PathfulImportLog instance
        row_number: Row number for unmatched tracking
        raw_data: Full row data for unmatched record

    Returns:
        TeacherProgress or None
    """
    pathful_id_str = safe_str(pathful_user_id)
    email_normalized = safe_str(email).lower()
    name_str = safe_str(name)

    # Priority 1: Match by pathful_user_id
    if pathful_id_str:
        teacher_progress = (
            caches["teacher_by_pathful_id"].get(pathful_id_str)
            if caches
            else TeacherProgress.query.filter(
                TeacherProgress.pathful_user_id == pathful_id_str
            ).first()
        )
        if teacher_progress:
            import_log.matched_teachers += 1
            return teacher_progress

    # Priority 2: Match by email
    if email_normalized:
        teacher_progress = (
            caches["teacher_by_email"].get(email_normalized)
            if caches
            else TeacherProgress.query.filter(
                func.lower(TeacherProgress.email) == email_normalized
            ).first()
        )
        if teacher_progress:
            # Update pathful_user_id if not set
            if pathful_id_str and not teacher_progress.pathful_user_id:
                teacher_progress.pathful_user_id = pathful_id_str
            import_log.matched_teachers += 1
            return teacher_progress

    # Priority 3: Match by name (case-insensitive)
    if name_str:
        teacher_progress = (
            caches["teacher_by_name"].get(name_str.lower())
            if caches
            else TeacherProgress.query.filter(
                func.lower(TeacherProgress.name) == func.lower(name_str)
            ).first()
        )
        if teacher_progress:
            if pathful_id_str and not teacher_progress.pathful_user_id:
                teacher_progress.pathful_user_id = pathful_id_str
            import_log.matched_teachers += 1
            return teacher_progress

    # No match - create unmatched record
    unmatched = PathfulUnmatchedRecord(
        import_log_id=import_log.id,
        row_number=row_number,
        raw_data=raw_data,
        unmatched_type=UnmatchedType.TEACHER,
        attempted_match_name=name_str,
        attempted_match_email=email_normalized,
        attempted_match_school=school_name,
    )
    if pathful_id_str:
        unmatched.attempted_match_session_id = pathful_id_str

    db.session.add(unmatched)
    import_log.unmatched_count += 1

    return None


def match_volunteer(
    name,
    email,
    organization_name,
    pathful_user_id,
    import_log,
    row_number,
    raw_data,
    caches=None,
):
    """
    Match a volunteer/professional from Pathful data.

    Matching priority:
    1. pathful_user_id (exact match)
    2. email (normalized, case-insensitive)
    3. name (fuzzy match by first + last)

    Args:
        name: Professional name
        email: Professional email (may be empty)
        organization_name: Organization/company name
        pathful_user_id: Pathful User Auth Id
        import_log: PathfulImportLog instance
        row_number: Row number for unmatched tracking
        raw_data: Full row data for unmatched record

    Returns:
        Volunteer or None
    """
    pathful_id_str = safe_str(pathful_user_id)
    email_normalized = safe_str(email).lower()
    name_str = safe_str(name)
    first_name, last_name = parse_name(name_str)

    # Priority 1: Match by pathful_user_id
    if pathful_id_str:
        volunteer = (
            caches["volunteer_by_pathful_id"].get(pathful_id_str)
            if caches
            else Volunteer.query.filter(
                Volunteer.pathful_user_id == pathful_id_str
            ).first()
        )
        if volunteer:
            import_log.matched_volunteers += 1
            return volunteer

    # Priority 2: Match by email (using Email model)
    if email_normalized:
        if caches:
            volunteer = caches["volunteer_by_email"].get(email_normalized)
        else:
            from models.contact import Email

            email_record = Email.query.filter(
                func.lower(Email.email) == email_normalized
            ).first()
            volunteer = None
            if email_record and email_record.contact:
                volunteer = Volunteer.query.filter(
                    Volunteer.id == email_record.contact_id
                ).first()
        if volunteer:
            # Update pathful_user_id if not set
            if pathful_id_str and not volunteer.pathful_user_id:
                volunteer.pathful_user_id = pathful_id_str
            import_log.matched_volunteers += 1
            return volunteer

    # Priority 3: Match by name
    if first_name and last_name:
        name_key = (first_name.lower(), last_name.lower())
        volunteer = (
            caches["volunteer_by_name"].get(name_key)
            if caches
            else Volunteer.query.filter(
                func.lower(Volunteer.first_name) == func.lower(first_name),
                func.lower(Volunteer.last_name) == func.lower(last_name),
            ).first()
        )
        if volunteer:
            if pathful_id_str and not volunteer.pathful_user_id:
                volunteer.pathful_user_id = pathful_id_str
            import_log.matched_volunteers += 1
            return volunteer

    # No existing match found.
    # Create the Volunteer record now so they are linked to the event and
    # appear in org reports.  We still write an unmatched record so admins
    # can review and optionally merge with an existing contact later.
    if first_name and last_name:
        volunteer = Volunteer(
            first_name=first_name,
            last_name=last_name,
            pathful_user_id=pathful_id_str if pathful_id_str else None,
        )
        db.session.add(volunteer)
        db.session.flush()  # get volunteer.id

        # Link to organization if company name is provided
        if organization_name:
            volunteer.organization_name = organization_name

            from models.organization import VolunteerOrganization
            from services.organization_service import resolve_organization

            org = resolve_organization(organization_name, caches=caches)
            if org:
                # Check no duplicate org link
                exists = VolunteerOrganization.query.filter_by(
                    volunteer_id=volunteer.id, organization_id=org.id
                ).first()
                if not exists:
                    has_primary = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, is_primary=True
                    ).first()
                    vol_org = VolunteerOrganization(
                        volunteer_id=volunteer.id,
                        organization_id=org.id,
                        is_primary=not has_primary,
                    )
                    db.session.add(vol_org)

        # Update caches so duplicate rows in this import reuse this volunteer
        if caches and first_name and last_name:
            caches["volunteer_by_name"][
                (first_name.lower(), last_name.lower())
            ] = volunteer
            if pathful_id_str:
                caches["volunteer_by_pathful_id"][pathful_id_str] = volunteer

        # Still create an unmatched record for admin review / potential merging
        unmatched = PathfulUnmatchedRecord(
            import_log_id=import_log.id,
            row_number=row_number,
            raw_data=raw_data,
            unmatched_type=UnmatchedType.VOLUNTEER,
            attempted_match_name=name_str,
            attempted_match_email=email_normalized,
            attempted_match_organization=organization_name,
        )
        unmatched.resolved_volunteer_id = volunteer.id
        if pathful_id_str:
            unmatched.attempted_match_session_id = pathful_id_str
        db.session.add(unmatched)
        import_log.unmatched_count += 1

        import_log.matched_volunteers += 1
        return volunteer

    # Cannot create without at least a first and last name — give up
    unmatched = PathfulUnmatchedRecord(
        import_log_id=import_log.id,
        row_number=row_number,
        raw_data=raw_data,
        unmatched_type=UnmatchedType.VOLUNTEER,
        attempted_match_name=name_str,
        attempted_match_email=email_normalized,
        attempted_match_organization=organization_name,
    )
    if pathful_id_str:
        unmatched.attempted_match_session_id = pathful_id_str

    db.session.add(unmatched)
    import_log.unmatched_count += 1

    return None

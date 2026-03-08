"""
Teacher Matching Service
========================

Centralized identity resolution for teacher records. All teacher matching
and linking should go through this service to ensure consistent behavior.

The service provides:
- Name normalization (case, punctuation, hyphens)
- Teacher identity resolution (TeacherProgress → Teacher linking)
- PathfulUserProfile matching (profile → TeacherProgress linking)
- Session counting via educator name matching

Used by: tenant_teacher_usage, pathful_import processing, pathful_import routes
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison by removing punctuation and lowercasing.

    Args:
        name: The name to normalize

    Returns:
        Normalized lowercase name with punctuation removed
    """
    if not name:
        return ""
    return (
        name.lower()
        .strip()
        .replace("-", " ")
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
    )


def build_teacher_alias_map(
    teachers: List[Any],
) -> tuple[Dict[int, int], Dict[str, int]]:
    """
    Build maps for teacher matching.

    Creates a progress counter map and an alias map that maps various
    name variations to teacher IDs for flexible matching.

    Args:
        teachers: List of teacher objects with id, name attributes

    Returns:
        tuple: (progress_map, alias_map)
            - progress_map: Dict[teacher_id, session_count] initialized to 0
            - alias_map: Dict[normalized_name, teacher_id]
    """
    teacher_progress_map = {}  # teacher_id -> completed_count
    teacher_alias_map = {}  # normalized_name -> teacher_id

    for teacher in teachers:
        teacher_progress_map[teacher.id] = 0

        # Create name variations for matching
        base_name = teacher.name.lower().strip()
        normalized = normalize_name(teacher.name)

        name_variations = [
            base_name,
            normalized,
        ]

        # Add first + last name variation if different from stored name
        parts = teacher.name.split()
        if len(parts) > 1:
            first_last = f"{parts[0]} {parts[-1]}".lower()
            name_variations.append(first_last)
            name_variations.append(normalize_name(first_last))

        # Store aliases pointing to teacher id
        for name_var in name_variations:
            if name_var:
                teacher_alias_map[name_var] = teacher.id

    return teacher_progress_map, teacher_alias_map


def match_educator_to_teacher(
    educator_name: str, alias_map: Dict[str, int], min_name_length: int = 3
) -> Optional[int]:
    """
    Match an educator name string to a teacher ID using flexible matching.

    Tries exact match first, then falls back to partial/fuzzy matching.

    Args:
        educator_name: The educator name from the session
        alias_map: Map of normalized names to teacher IDs
        min_name_length: Minimum name length for partial matching

    Returns:
        teacher_id if matched, None otherwise
    """
    if not educator_name:
        return None

    educator_key = educator_name.lower().strip()
    educator_normalized = normalize_name(educator_name)

    # Try exact match first
    teacher_id = alias_map.get(educator_key) or alias_map.get(educator_normalized)

    if teacher_id:
        return teacher_id

    # Try flexible matching - look for partial matches
    if len(educator_key) > min_name_length:
        for name_key, alias_teacher_id in alias_map.items():
            name_key_normalized = normalize_name(name_key)

            # Check if either version matches (partial match)
            if (
                educator_key in name_key
                or name_key in educator_key
                or educator_normalized in name_key_normalized
                or name_key_normalized in educator_normalized
            ):
                return alias_teacher_id

    return None


def count_sessions_for_teachers(
    events: List[Any], alias_map: Dict[str, int], progress_map: Dict[int, int]
) -> Dict[int, int]:
    """
    Count completed sessions for each teacher based on Event.educators field.

    Parses the semicolon-separated educators field from each event and
    matches names to teachers using the alias map.

    Args:
        events: List of Event objects with educators attribute
        alias_map: Map of normalized names to teacher IDs
        progress_map: Map of teacher IDs to session counts (will be modified)

    Returns:
        Updated progress_map with session counts
    """
    for event in events:
        if not event.educators:
            continue

        # Parse semicolon-separated educator names
        educator_names = [
            name.strip() for name in event.educators.split(";") if name.strip()
        ]

        for educator_name in educator_names:
            teacher_id = match_educator_to_teacher(educator_name, alias_map)

            if teacher_id and teacher_id in progress_map:
                progress_map[teacher_id] += 1

    return progress_map


# ---------------------------------------------------------------------------
# Centralized Identity Resolution
# ---------------------------------------------------------------------------


def resolve_teacher_for_tp(tp):
    """Resolve a Teacher record for a TeacherProgress with teacher_id=None.

    This is the SINGLE canonical path for linking TeacherProgress → Teacher.
    All callers (backfills, imports, reconciliation) should use this function
    instead of implementing their own matching logic.

    Matching priority:
    1. Email match — TP.email vs Teacher.cached_email (most reliable)
    2. Profile bridge — TP.email → PathfulUserProfile → Teacher via profile data
    3. Normalized name — normalize_name(TP.name) vs Teacher names
    4. Create new Teacher — if no match found but we have sufficient identity data

    Side effects:
    - Sets tp.teacher_id if a match is found or a Teacher is created
    - Sets Teacher.cached_email if it was NULL (self-healing)
    - Does NOT commit — caller is responsible for db.session.commit()

    Returns:
        Teacher instance if resolved, None otherwise
    """
    from sqlalchemy import func as sqla_func

    from models import db
    from models.teacher import Teacher, TeacherStatus

    if tp.teacher_id is not None:
        return db.session.get(Teacher, tp.teacher_id)

    teacher = None

    # --- Priority 1: Email match ---
    if tp.email:
        teacher = Teacher.query.filter(
            sqla_func.lower(Teacher.cached_email) == tp.email.strip().lower()
        ).first()

    # --- Priority 2: Profile bridge ---
    if not teacher and tp.email:
        from models.pathful_import import PathfulUserProfile

        profile = PathfulUserProfile.query.filter(
            sqla_func.lower(PathfulUserProfile.login_email) == tp.email.strip().lower(),
            PathfulUserProfile.signup_role == "Educator",
        ).first()
        if profile and profile.teacher_progress_id:
            # Profile is linked to another TP — check if that TP has a teacher_id
            from models.teacher_progress import TeacherProgress

            linked_tp = db.session.get(TeacherProgress, profile.teacher_progress_id)
            if linked_tp and linked_tp.teacher_id:
                teacher = db.session.get(Teacher, linked_tp.teacher_id)

    # --- Priority 3: Normalized name match ---
    if not teacher and tp.name:
        tp_normalized = normalize_name(tp.name)
        if tp_normalized:
            parts = tp.name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                # Also build first+last for middle-name tolerance
                tp_first_last = normalize_name(f"{parts[0]} {parts[-1]}")

                candidates = Teacher.query.filter(
                    sqla_func.lower(Teacher.first_name) == first_name.lower()
                ).all()
                # Collect all name-matched teachers
                name_matches = []
                for t in candidates:
                    t_full = f"{t.first_name or ''} {t.last_name or ''}"
                    t_normalized = normalize_name(t_full)
                    # Full normalized match OR first+last match
                    if t_normalized == tp_normalized or t_normalized == tp_first_last:
                        name_matches.append(t)

                if len(name_matches) == 1:
                    teacher = name_matches[0]
                elif len(name_matches) > 1:
                    # Multiple matches — prefer the one with EventTeacher records
                    from models.event import EventTeacher

                    for t in name_matches:
                        if EventTeacher.query.filter_by(teacher_id=t.id).first():
                            teacher = t
                            break
                    if not teacher:
                        # None have ETs — fall back to first match
                        teacher = name_matches[0]

    # --- Priority 4: Create new Teacher ---
    if not teacher and tp.email and tp.name:
        parts = tp.name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = " ".join(parts[1:])  # Preserve multi-part last names

            teacher = Teacher(
                first_name=first_name,
                last_name=last_name,
                cached_email=tp.email.strip().lower(),
                import_source="reconciliation",
                status=TeacherStatus.ACTIVE,
            )
            db.session.add(teacher)
            db.session.flush()  # Get the ID assigned
            logger.info(
                "Created Teacher id=%s for TP id=%s (%s)",
                teacher.id,
                tp.id,
                tp.name,
            )

    # --- Link and self-heal ---
    if teacher:
        tp.teacher_id = teacher.id
        # Self-healing: ensure Teacher always has cached_email
        if not teacher.cached_email and tp.email:
            teacher.cached_email = tp.email.strip().lower()
            logger.info(
                "Self-healed cached_email for Teacher id=%s → %s",
                teacher.id,
                teacher.cached_email,
            )

    return teacher


def match_tp_to_profile(tp):
    """Link a TeacherProgress to its PathfulUserProfile.

    This is the canonical path for linking TeacherProgress → PathfulUserProfile.
    Used by the user report import auto-linking and the reconciliation script.

    Matching priority:
    1. pathful_user_id — exact match (existing Pathful key)
    2. Email — TP.email vs PathfulUserProfile.login_email
    3. Normalized name — normalize_name(TP.name) vs PathfulUserProfile.name

    Side effects:
    - Sets profile.teacher_progress_id if matched
    - Sets tp.pathful_user_id from profile if not already set
    - Does NOT commit — caller is responsible for db.session.commit()

    Returns:
        PathfulUserProfile instance if matched, None otherwise
    """
    from sqlalchemy import func as sqla_func

    from models.pathful_import import PathfulUserProfile

    profile = None

    # --- Priority 1: pathful_user_id ---
    if tp.pathful_user_id:
        profile = PathfulUserProfile.query.filter_by(
            pathful_user_id=tp.pathful_user_id
        ).first()

    # --- Priority 2: Email ---
    if not profile and tp.email:
        profile = PathfulUserProfile.query.filter(
            sqla_func.lower(PathfulUserProfile.login_email) == tp.email.strip().lower(),
            PathfulUserProfile.signup_role == "Educator",
            PathfulUserProfile.teacher_progress_id.is_(None),
        ).first()

    # --- Priority 3: Normalized name ---
    if not profile and tp.name:
        tp_normalized = normalize_name(tp.name)
        if tp_normalized:
            # Get candidate profiles with no TP link
            candidates = PathfulUserProfile.query.filter(
                PathfulUserProfile.signup_role == "Educator",
                PathfulUserProfile.teacher_progress_id.is_(None),
                PathfulUserProfile.name.isnot(None),
            ).all()
            for p in candidates:
                if normalize_name(p.name) == tp_normalized:
                    profile = p
                    break

    # --- Link ---
    if profile:
        if not profile.teacher_progress_id:
            profile.link_to_teacher_progress(tp.id)
        if not tp.pathful_user_id and profile.pathful_user_id:
            tp.pathful_user_id = profile.pathful_user_id

    return profile

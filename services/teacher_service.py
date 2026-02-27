"""
Teacher Service Module (Sprint 1)
=================================

Centralized service for all Teacher record operations.
This is the SINGLE entry point for finding or creating Teacher records,
replacing the scattered inline logic across routes.

Match Priority Chain:
    1. salesforce_individual_id (exact, unique)
    2. cached_email (exact, case-insensitive)
    3. Normalized name (fuzzy, with confidence scoring)

Usage:
    from services.teacher_service import find_or_create_teacher

    teacher, is_new, match_info = find_or_create_teacher(
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@school.org",
        import_source="pathful",
    )
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from sqlalchemy import func

from models import db
from models.contact import Email
from models.teacher import Teacher, TeacherStatus
from services.teacher_matching_service import normalize_name

logger = logging.getLogger(__name__)


@dataclass
class MatchInfo:
    """Details about how a teacher was matched or created."""

    method: str  # 'salesforce_id', 'email', 'name', 'created'
    confidence: float  # 0.0 - 1.0
    matched_value: Optional[str] = None  # The value that caused the match

    def __repr__(self):
        return f"MatchInfo(method='{self.method}', confidence={self.confidence})"


def find_or_create_teacher(
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    salesforce_id: Optional[str] = None,
    school_id: Optional[str] = None,
    import_source: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> Tuple[Teacher, bool, MatchInfo]:
    """
    Find an existing teacher or create a new one.

    This is the SINGLE entry point for all teacher record resolution.
    It uses a prioritized matching strategy to prevent duplicates.

    Match Priority:
        1. salesforce_individual_id (exact match, highest confidence)
        2. cached_email / Email model (case-insensitive, high confidence)
        3. Normalized name match (fuzzy, lower confidence)

    Args:
        first_name: Teacher's first name (required)
        last_name: Teacher's last name (required)
        email: Teacher's email address (optional, used for matching)
        salesforce_id: Salesforce Individual ID (optional)
        school_id: School ID to assign (optional)
        import_source: Where this record comes from (e.g., 'salesforce', 'pathful', 'manual')
        tenant_id: Tenant ID for future multi-tenant filtering (optional, reserved)

    Returns:
        Tuple of (teacher, is_new, match_info):
            - teacher: The found or created Teacher object
            - is_new: True if a new record was created
            - match_info: Details about the match method and confidence
    """
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not first_name and not last_name:
        raise ValueError("At least one of first_name or last_name is required")

    # --- Priority 1: Salesforce ID match ---
    if salesforce_id:
        teacher = Teacher.query.filter_by(
            salesforce_individual_id=salesforce_id
        ).first()
        if teacher:
            _update_teacher_if_needed(teacher, email, school_id, import_source)
            logger.debug(
                f"Teacher matched by Salesforce ID: {salesforce_id} → {teacher.full_name}"
            )
            return (
                teacher,
                False,
                MatchInfo(
                    method="salesforce_id",
                    confidence=1.0,
                    matched_value=salesforce_id,
                ),
            )

    # --- Priority 2: Email match ---
    if email:
        email_lower = email.strip().lower()

        # 2a: Check Teacher.cached_email (fast, indexed)
        teacher = Teacher.query.filter(
            func.lower(Teacher.cached_email) == email_lower
        ).first()

        if teacher:
            _update_teacher_if_needed(teacher, email, school_id, import_source)
            logger.debug(
                f"Teacher matched by cached_email: {email_lower} → {teacher.full_name}"
            )
            return (
                teacher,
                False,
                MatchInfo(
                    method="email",
                    confidence=0.95,
                    matched_value=email_lower,
                ),
            )

        # 2b: Check Email model (slower, but catches all email records)
        email_record = (
            Email.query.filter(func.lower(Email.email) == email_lower)
            .join(Teacher, Email.contact_id == Teacher.id)
            .first()
        )
        if email_record:
            teacher = Teacher.query.get(email_record.contact_id)
            if teacher:
                # Cache the email on the teacher for faster future matches
                if not teacher.cached_email:
                    teacher.cached_email = email_lower
                _update_teacher_if_needed(teacher, email, school_id, import_source)
                logger.debug(
                    f"Teacher matched by Email model: {email_lower} → {teacher.full_name}"
                )
                return (
                    teacher,
                    False,
                    MatchInfo(
                        method="email",
                        confidence=0.90,
                        matched_value=email_lower,
                    ),
                )

    # --- Priority 3: Name match (fuzzy) ---
    normalized_first = normalize_name(first_name)
    normalized_last = normalize_name(last_name)
    full_normalized = f"{normalized_first} {normalized_last}".strip()

    if full_normalized:
        # Query all teachers and check normalized names
        # This is O(n) but teacher count is manageable (~10K)
        candidates = Teacher.query.filter(Teacher.active == True).all()

        for candidate in candidates:
            candidate_normalized = normalize_name(candidate.full_name)
            candidate_first = normalize_name(candidate.first_name or "")
            candidate_last = normalize_name(candidate.last_name or "")

            # Exact normalized match
            if candidate_normalized == full_normalized:
                _update_teacher_if_needed(candidate, email, school_id, import_source)
                logger.debug(
                    f"Teacher matched by exact name: '{full_normalized}' → {candidate.full_name}"
                )
                return (
                    candidate,
                    False,
                    MatchInfo(
                        method="name",
                        confidence=0.80,
                        matched_value=full_normalized,
                    ),
                )

            # First + Last match (handles middle name differences)
            if (
                candidate_first
                and candidate_last
                and candidate_first == normalized_first
                and candidate_last == normalized_last
            ):
                _update_teacher_if_needed(candidate, email, school_id, import_source)
                logger.debug(
                    f"Teacher matched by first+last: '{first_name} {last_name}' → {candidate.full_name}"
                )
                return (
                    candidate,
                    False,
                    MatchInfo(
                        method="name",
                        confidence=0.75,
                        matched_value=f"{normalized_first} {normalized_last}",
                    ),
                )

    # --- No match: Create new teacher ---
    teacher = Teacher(
        first_name=first_name,
        last_name=last_name,
        status=TeacherStatus.ACTIVE,
        active=True,
        import_source=import_source,
    )

    if email:
        teacher.cached_email = email.strip().lower()

    if school_id:
        teacher.school_id = school_id

    if salesforce_id:
        teacher.salesforce_individual_id = salesforce_id

    db.session.add(teacher)
    db.session.flush()  # Get the ID assigned

    # Also create an Email record for the teacher
    if email:
        email_record = Email(
            contact_id=teacher.id,
            email=email.strip().lower(),
            primary=True,
        )
        db.session.add(email_record)

    logger.info(
        f"Created new Teacher: {first_name} {last_name} "
        f"(id={teacher.id}, source={import_source})"
    )

    return (
        teacher,
        True,
        MatchInfo(
            method="created",
            confidence=1.0,
            matched_value=None,
        ),
    )


def _update_teacher_if_needed(
    teacher: Teacher,
    email: Optional[str],
    school_id: Optional[str],
    import_source: Optional[str],
) -> None:
    """
    Update an existing teacher with new information if fields are missing.

    Only fills in blanks — never overwrites existing data.

    Args:
        teacher: The existing teacher to update
        email: New email to set if teacher has no cached_email
        school_id: New school_id to set if teacher has none
        import_source: New import_source to set if teacher has none
    """
    if email and not teacher.cached_email:
        teacher.cached_email = email.strip().lower()

    if school_id and not teacher.school_id:
        teacher.school_id = school_id

    if import_source and not teacher.import_source:
        teacher.import_source = import_source


def backfill_primary_emails() -> dict:
    """
    Backfill primary_email on Teacher records from the Email model.

    For teachers that have Email records but no primary_email set,
    copies the primary email address to Teacher.cached_email for
    faster matching.

    Returns:
        dict with stats: {'updated': int, 'skipped': int, 'total': int}
    """
    teachers = Teacher.query.filter(Teacher.cached_email.is_(None)).all()
    updated = 0
    skipped = 0

    for teacher in teachers:
        # Find primary email
        primary = Email.query.filter_by(contact_id=teacher.id, primary=True).first()
        if not primary:
            # Fall back to any email
            primary = Email.query.filter_by(contact_id=teacher.id).first()

        if primary and primary.email:
            teacher.cached_email = primary.email.strip().lower()
            updated += 1
        else:
            skipped += 1

    if updated > 0:
        db.session.flush()

    logger.info(
        f"Backfill cached_email: {updated} updated, {skipped} skipped, "
        f"{len(teachers)} total without cached_email"
    )

    return {"updated": updated, "skipped": skipped, "total": len(teachers)}

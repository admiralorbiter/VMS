"""
C1: Pathful ID & Email Backfill Service
========================================

After the Pathful import engine matches a volunteer via P3 (name match) or P4
(near-name quarantine), this service:

  1. Looks up the volunteer's ``pathful_user_id`` in ``PathfulUserProfile``
  2. If a profile exists and has a ``login_email``, ensures that email is recorded
     in the ``contact_email`` table for the Volunteer's contact record
  3. If a profile exists and the Volunteer still has no ``pathful_user_id``, sets it

Effect: The **next** import of the same person hits Priority 2 (email) or
Priority 1 (pathful_user_id) instead of falling through to P3/P4. This
progressively collapses the duplicate-creation rate without touching any records
outside of the current session.

Usage (called from processing.py after every P3/P4 match):

    from services.pathful_id_backfill_service import backfill_volunteer_from_profile

    changed = backfill_volunteer_from_profile(volunteer, pathful_user_id_str)

Safety rules:
  - NEVER overwrites an existing email — only adds if not present.
  - NEVER sets pathful_user_id if one is already on the volunteer.
  - All writes happen inside the caller's transaction; this function does NOT commit.
  - Returns a small dict describing what (if anything) was changed, for logging.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def backfill_volunteer_from_profile(
    volunteer,
    pathful_user_id: Optional[str],
) -> dict:
    """
    Attempt to enrich a Volunteer record using data from PathfulUserProfile.

    Should be called immediately after a P3 or P4 volunteer match, while the
    volunteer object is still in the session and pathful_user_id is known from
    the current import row.

    Args:
        volunteer: The matched ``Volunteer`` ORM instance (already in session).
        pathful_user_id: The raw ``User Auth Id`` string from the current import
            row. May be None/empty if the session report row lacked it.

    Returns:
        dict with keys:
            ``pathful_id_set``  (bool) — True if pathful_user_id was written
            ``email_added``     (bool) — True if a new Email row was created
            ``profile_found``   (bool) — True if a UserProfile existed for this ID
    """
    result = {
        "pathful_id_set": False,
        "email_added": False,
        "profile_found": False,
    }

    if not volunteer or not volunteer.id:
        return result

    # ── Resolve pathful_user_id ────────────────────────────────────────────────
    # Prefer the value already on the volunteer (set by P1/P2/P3 in match_volunteer).
    # Fall back to the id passed in from the import row.
    effective_id = volunteer.pathful_user_id or (pathful_user_id or "").strip() or None
    if not effective_id:
        # No handle we can look up — nothing to do.
        return result

    # ── Backfill pathful_user_id onto the Volunteer if missing ────────────────
    if not volunteer.pathful_user_id and effective_id:
        volunteer.pathful_user_id = effective_id
        result["pathful_id_set"] = True
        logger.debug(
            "C1: backfilled pathful_user_id=%r onto Volunteer %s",
            effective_id,
            volunteer.id,
        )

    # ── Look up PathfulUserProfile ────────────────────────────────────────────
    from models.pathful_import import PathfulUserProfile

    profile = PathfulUserProfile.query.filter_by(pathful_user_id=effective_id).first()

    if not profile:
        # No profile yet (user_report not yet imported, or this is a very new
        # user). Nothing more to do — the pathful_user_id alone already raises
        # the next-import hit rate from P3 to P1.
        return result

    result["profile_found"] = True

    # ── Link profile → Volunteer if not already linked ────────────────────────
    if not profile.volunteer_id:
        profile.volunteer_id = volunteer.id
        logger.debug(
            "C1: linked PathfulUserProfile %s → Volunteer %s",
            profile.id,
            volunteer.id,
        )

    # ── Backfill email ────────────────────────────────────────────────────────
    login_email = (profile.login_email or "").strip().lower()
    if not login_email:
        return result  # Profile exists but has no email — nothing more to backfill

    _ensure_volunteer_email(volunteer, login_email, result)

    return result


def _ensure_volunteer_email(volunteer, email_lower: str, result: dict) -> None:
    """
    Add ``email_lower`` to the volunteer's contact Email records if not present.

    Uses the same ``contact_email`` table that P2 reads from, so this directly
    improves the hit rate on future imports.

    Idempotent — silently no-ops if the email already exists for this contact.
    """
    # Check if this email already exists for this volunteer (case-insensitive)
    from sqlalchemy import func as sqla_func

    from models import db
    from models.contact import Email as ContactEmail
    from models.contact_enums import ContactTypeEnum

    existing = ContactEmail.query.filter(
        ContactEmail.contact_id == volunteer.id,
        sqla_func.lower(ContactEmail.email) == email_lower,
    ).first()

    if existing:
        return  # Already present — nothing to do

    # Add email as non-primary professional record so future P2 lookups can find it
    new_email = ContactEmail(
        contact_id=volunteer.id,
        email=email_lower,
        type=ContactTypeEnum.professional,
        primary=False,  # Never override the authoritative Salesforce primary
    )
    db.session.add(new_email)
    result["email_added"] = True

    logger.info(
        "C1: added email %r to Volunteer %s (source: PathfulUserProfile)",
        email_lower,
        volunteer.id,
    )

"""
tests/unit/services/test_pathful_hardening.py
==============================================

Unit tests for all Pathful pipeline hardening epics (Phase E).

  Epic A — High-severity fixes
    A1: teacher_record_by_name cache collision detection
    A2: Event P2 session_id cross-check guard

  Epic B — Structural guardrails
    B1: volunteer_by_email / teacher_by_email cache collision markers
    B2: Organization T4 — quarantine-first, no auto-alias

  Epic C — Future hardening
    C1: backfill_volunteer_from_profile (pathful_id_backfill_service)

Each section is self-contained and creates its own in-memory DB rows.
Tests NEVER commit to the production database (enforced by conftest.py's
:memory: safety assertion).
"""

import json
from datetime import date, datetime, timezone

import pytest

from models import db

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_volunteer(first_name, last_name, pathful_user_id=None, flush=True):
    """Create a minimal Volunteer in the current session."""
    from models.volunteer import Volunteer

    v = Volunteer(
        first_name=first_name,
        last_name=last_name,
        pathful_user_id=pathful_user_id,
    )
    db.session.add(v)
    if flush:
        db.session.flush()
    return v


def _make_teacher(first_name, last_name, flush=True):
    """Create a minimal Teacher in the current session."""
    from models.teacher import Teacher

    t = Teacher(
        first_name=first_name,
        last_name=last_name,
        active=True,
    )
    db.session.add(t)
    if flush:
        db.session.flush()
    return t


def _make_event(title, start_date=None, pathful_session_id=None):
    """Create a minimal Event in the current session."""
    from models.event import Event, EventFormat, EventStatus, EventType

    e = Event(
        title=title,
        type=EventType.VIRTUAL_SESSION,
        format=EventFormat.VIRTUAL,
        start_date=start_date or datetime.now(timezone.utc),
        status=EventStatus.CONFIRMED,
        pathful_session_id=pathful_session_id,
        volunteers_needed=0,
    )
    db.session.add(e)
    db.session.flush()
    return e


def _make_import_log():
    """Create a minimal PathfulImportLog in the current session."""
    from models.pathful_import import PathfulImportLog

    log = PathfulImportLog(filename="test.xlsx", import_type="session_report")
    db.session.add(log)
    db.session.flush()
    return log


# ──────────────────────────────────────────────────────────────────────────────
# A1 — Teacher name cache collision detection
# ──────────────────────────────────────────────────────────────────────────────


class TestA1TeacherNameCacheCollision:
    """
    A1: build_import_caches() must set teacher_record_by_name[key] = None when
    two Teacher rows normalise to the same full name, rather than silently
    letting the second overwrite the first.
    """

    def test_unique_name_is_stored(self, app):
        """Single teacher with unique name → stored normally in cache."""
        with app.app_context():
            t = _make_teacher("Jane", "Smith")
            db.session.commit()

            from routes.virtual.pathful_import.matching import build_import_caches

            caches = build_import_caches()
            # Normalised key: "jane smith"
            cached = caches["teacher_record_by_name"].get("jane smith")
            assert cached is not None
            assert cached.id == t.id

    def test_collision_sets_none(self, app):
        """Two teachers with the same normalised full name → cache value is None."""
        with app.app_context():
            _make_teacher("Alice", "Jones")
            _make_teacher("Alice", "Jones")  # duplicate normalised name
            db.session.commit()

            from routes.virtual.pathful_import.matching import build_import_caches

            caches = build_import_caches()
            cached = caches["teacher_record_by_name"].get("alice jones")
            # None is the collision marker — it must be explicitly None (not missing)
            assert "alice jones" in caches["teacher_record_by_name"]
            assert cached is None  # collision detected

    def test_collision_does_not_affect_other_keys(self, app):
        """Collision on one name must not contaminate unrelated name keys."""
        with app.app_context():
            _make_teacher("Bob", "Unique")
            _make_teacher("Carol", "Collision")
            _make_teacher("Carol", "Collision")
            db.session.commit()

            from routes.virtual.pathful_import.matching import build_import_caches

            caches = build_import_caches()
            # Unrelated name must still resolve
            cached = caches["teacher_record_by_name"].get("bob unique")
            assert cached is not None
            # Collided name must be None
            assert caches["teacher_record_by_name"].get("carol collision") is None


# ──────────────────────────────────────────────────────────────────────────────
# A2 — Event P2 session_id cross-check
# ──────────────────────────────────────────────────────────────────────────────


class TestA2EventP2SessionIdGuard:
    """
    A2: match_or_create_event() P2 (title+date match) must NOT merge two rows
    that share a title and date but carry *different* Pathful session IDs.
    """

    def test_same_session_id_deduplicates(self, app):
        """Same title + same session_id on second call → returns same event."""
        with app.app_context():
            log = _make_import_log()
            db.session.commit()

            from routes.virtual.pathful_import.matching import match_or_create_event

            d = datetime(2025, 3, 15, tzinfo=timezone.utc)

            ev1, t1 = match_or_create_event(
                "SID-001", "Career Day", d, "COMPLETED", None, None, log
            )
            db.session.flush()

            ev2, t2 = match_or_create_event(
                "SID-001", "Career Day", d, "COMPLETED", None, None, log
            )
            db.session.flush()

            assert ev1.id == ev2.id  # idempotent

    def test_different_session_ids_create_separate_events(self, app):
        """Same title + date but *different* session_ids → two distinct Event rows."""
        with app.app_context():
            log = _make_import_log()
            db.session.commit()

            from routes.virtual.pathful_import.matching import match_or_create_event

            d = datetime(2025, 4, 1, tzinfo=timezone.utc)

            ev1, _ = match_or_create_event(
                "SID-A", "Creative Careers Uncovered", d, "COMPLETED", None, None, log
            )
            db.session.flush()

            ev2, _ = match_or_create_event(
                "SID-B", "Creative Careers Uncovered", d, "COMPLETED", None, None, log
            )
            db.session.flush()

            assert ev1.id != ev2.id  # guard creates a new event

    def test_null_session_id_still_deduplicates_by_title_date(self, app):
        """Rows with no session_id fall back to title+date deduplication as before."""
        with app.app_context():
            log = _make_import_log()
            db.session.commit()

            from routes.virtual.pathful_import.matching import match_or_create_event

            d = datetime(2025, 5, 10, tzinfo=timezone.utc)

            ev1, _ = match_or_create_event(
                None, "No ID Session", d, "COMPLETED", None, None, log
            )
            db.session.flush()

            ev2, _ = match_or_create_event(
                None, "No ID Session", d, "COMPLETED", None, None, log
            )
            db.session.flush()

            assert ev1.id == ev2.id  # still deduplicates when both IDs are absent


# ──────────────────────────────────────────────────────────────────────────────
# B1 — Email cache collision markers
# ──────────────────────────────────────────────────────────────────────────────


class TestB1EmailCacheCollisions:
    """
    B1: build_import_caches() must set volunteer_by_email[key] = None when two
    Volunteer contacts share the same email address (e.g. family shared inbox).
    Lookups then fall through to the name-match tier instead of silently picking
    one person. The same pattern applies to teacher_by_email.
    """

    def test_unique_email_stored(self, app):
        """One volunteer with one email → cache holds the volunteer."""
        with app.app_context():
            from models.contact import ContactTypeEnum, Email

            v = _make_volunteer("Dana", "Unique")
            e = Email(
                contact_id=v.id,
                email="dana@example.com",
                type=ContactTypeEnum.personal,
                primary=True,
            )
            db.session.add(e)
            db.session.commit()

            from routes.virtual.pathful_import.matching import build_import_caches

            caches = build_import_caches()
            cached = caches["volunteer_by_email"].get("dana@example.com")
            assert cached is not None
            assert cached.id == v.id

    def test_shared_email_collision_is_none(self, app):
        """Two volunteers sharing an email → cache entry is None (collision marker)."""
        with app.app_context():
            from models.contact import ContactTypeEnum, Email

            v1 = _make_volunteer("Pat", "Smith")
            v2 = _make_volunteer("Chris", "Smith")
            shared = "shared@family.example.com"
            for vid in (v1.id, v2.id):
                db.session.add(
                    Email(
                        contact_id=vid,
                        email=shared,
                        type=ContactTypeEnum.personal,
                        primary=True,
                    )
                )
            db.session.commit()

            from routes.virtual.pathful_import.matching import build_import_caches

            caches = build_import_caches()
            assert shared in caches["volunteer_by_email"]
            assert caches["volunteer_by_email"][shared] is None

    def test_collision_does_not_contaminate_other_emails(self, app):
        """Collision on one email must not affect unrelated email keys."""
        with app.app_context():
            from models.contact import ContactTypeEnum, Email

            v_clean = _make_volunteer("Solo", "Brown")
            db.session.add(
                Email(
                    contact_id=v_clean.id,
                    email="solo@clean.com",
                    type=ContactTypeEnum.personal,
                    primary=True,
                )
            )

            v_a = _make_volunteer("Dup", "Alpha")
            v_b = _make_volunteer("Dup", "Beta")
            for vid in (v_a.id, v_b.id):
                db.session.add(
                    Email(
                        contact_id=vid,
                        email="dup@shared.com",
                        type=ContactTypeEnum.personal,
                        primary=True,
                    )
                )
            db.session.commit()

            from routes.virtual.pathful_import.matching import build_import_caches

            caches = build_import_caches()
            assert caches["volunteer_by_email"].get("solo@clean.com") is not None
            assert caches["volunteer_by_email"].get("dup@shared.com") is None


# ──────────────────────────────────────────────────────────────────────────────
# B2 — Organization T4 quarantine-first (no auto-alias)
# ──────────────────────────────────────────────────────────────────────────────


class TestB2OrgTier4QuarantineFirst:
    """
    B2: resolve_organization() Tier 4 must NOT write an OrganizationAlias
    automatically. It must return None and leave alias creation to admin confirmation.
    """

    def test_tier4_returns_none_without_writing_alias(self, app):
        """T4 near-match → returns None (no auto-alias written)."""
        with app.app_context():
            from models.organization import Organization, OrganizationAlias
            from services.organization_service import resolve_organization

            org = Organization(name="Next Level")
            db.session.add(org)
            db.session.commit()

            incoming = "Next Level, Inc."
            result = resolve_organization(incoming)

            # B2: must now return None (quarantine-first)
            assert result is None

            # Critical: no alias must have been written
            alias = OrganizationAlias.query.filter_by(name=incoming).first()
            assert (
                alias is None
            ), "T4 auto-wrote an OrganizationAlias — this should never happen after B2."

    def test_tier1_exact_match_still_works(self, app):
        """Exact match in cache still resolves instantly (T1/T2 unaffected by B2)."""
        with app.app_context():
            from models.organization import Organization
            from services.organization_service import resolve_organization

            org = Organization(name="Exact Corp")
            db.session.add(org)
            db.session.commit()

            result = resolve_organization("Exact Corp")
            assert result is not None
            assert result.id == org.id

    def test_tier3_alias_match_still_works(self, app):
        """Admin-confirmed alias (T3) still resolves (B2 only affects T4)."""
        with app.app_context():
            from models.organization import Organization, OrganizationAlias
            from services.organization_service import resolve_organization

            org = Organization(name="Canonical Co")
            db.session.add(org)
            db.session.flush()
            alias = OrganizationAlias(
                name="Alternate Name", organization_id=org.id, is_auto_generated=False
            )
            db.session.add(alias)
            db.session.commit()

            result = resolve_organization("alternate name")
            assert result is not None
            assert result.id == org.id

    def test_completely_unknown_org_returns_none(self, app):
        """No match at any tier → None (unchanged from pre-B2 behaviour)."""
        with app.app_context():
            from services.organization_service import resolve_organization

            result = resolve_organization("Totally Unknown Entity XYZ 99999")
            assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# C1 — Pathful email backfill service
# ──────────────────────────────────────────────────────────────────────────────


class TestC1PathfulBackfillService:
    """
    C1: backfill_volunteer_from_profile() must:
      - Backfill pathful_user_id onto volunteer if missing
      - Look up PathfulUserProfile by that ID
      - If profile has login_email and volunteer has no such email → add Email row
      - Link profile.volunteer_id → volunteer
      - Be idempotent (second call adds no duplicate rows)
    """

    def _make_profile(
        self, pathful_user_id, login_email=None, signup_role="Professional"
    ):
        from models.pathful_import import PathfulUserProfile

        p = PathfulUserProfile(
            pathful_user_id=pathful_user_id,
            signup_role=signup_role,
            name="Profile Person",
            login_email=login_email,
        )
        db.session.add(p)
        db.session.flush()
        return p

    def test_backfills_pathful_user_id(self, app):
        """volunteer.pathful_user_id is None → gets set from passed-in id."""
        with app.app_context():
            v = _make_volunteer("Tom", "Noid")
            assert v.pathful_user_id is None
            db.session.commit()

            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            result = backfill_volunteer_from_profile(v, "PID-001")
            assert v.pathful_user_id == "PID-001"
            assert result["pathful_id_set"] is True

    def test_does_not_overwrite_existing_pathful_user_id(self, app):
        """If volunteer already has pathful_user_id, it must not be changed."""
        with app.app_context():
            v = _make_volunteer("Ann", "Already", pathful_user_id="EXISTING")
            db.session.commit()

            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            result = backfill_volunteer_from_profile(v, "NEW-ID")
            assert v.pathful_user_id == "EXISTING"
            assert result["pathful_id_set"] is False

    def test_no_profile_returns_early(self, app):
        """No PathfulUserProfile exists for the id → returns without email add."""
        with app.app_context():
            v = _make_volunteer("No", "Profile")
            db.session.commit()

            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            result = backfill_volunteer_from_profile(v, "GHOST-999")
            assert result["profile_found"] is False
            assert result["email_added"] is False

    def test_adds_email_from_profile(self, app):
        """Profile with login_email → email row added to volunteer's contact."""
        with app.app_context():
            v = _make_volunteer("Kim", "NoEmail")
            self._make_profile("KIM-001", login_email="kim@work.example.com")
            db.session.commit()

            from models.contact import Email
            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            result = backfill_volunteer_from_profile(v, "KIM-001")

            assert result["profile_found"] is True
            assert result["email_added"] is True

            email_row = Email.query.filter_by(
                contact_id=v.id, email="kim@work.example.com"
            ).first()
            assert email_row is not None
            assert email_row.primary is False  # never overrides Salesforce primary

    def test_idempotent_email_not_duplicated(self, app):
        """Calling backfill twice with the same profile must not create duplicate emails."""
        with app.app_context():
            v = _make_volunteer("Lee", "Idempotent")
            self._make_profile("LEE-001", login_email="lee@example.com")
            db.session.commit()

            from models.contact import Email
            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            backfill_volunteer_from_profile(v, "LEE-001")
            backfill_volunteer_from_profile(v, "LEE-001")  # second call

            count = Email.query.filter_by(
                contact_id=v.id, email="lee@example.com"
            ).count()
            assert count == 1  # exactly one row, not two

    def test_links_profile_to_volunteer(self, app):
        """profile.volunteer_id gets set to the volunteer's id."""
        with app.app_context():
            v = _make_volunteer("Max", "Link")
            p = self._make_profile("MAX-001", login_email="max@co.example.com")
            assert p.volunteer_id is None
            db.session.commit()

            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            backfill_volunteer_from_profile(v, "MAX-001")
            db.session.flush()

            assert p.volunteer_id == v.id

    def test_profile_without_email_sets_id_only(self, app):
        """Profile exists but has no login_email → only pathful_user_id backfilled."""
        with app.app_context():
            v = _make_volunteer("Riley", "NoMail")
            self._make_profile("RILEY-001", login_email=None)
            db.session.commit()

            from models.contact import Email
            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            result = backfill_volunteer_from_profile(v, "RILEY-001")
            assert result["profile_found"] is True
            assert result["email_added"] is False
            assert result["pathful_id_set"] is True
            assert Email.query.filter_by(contact_id=v.id).count() == 0

    def test_no_id_returns_empty_result(self, app):
        """Volunteer has no pathful_user_id and none is passed → early return."""
        with app.app_context():
            v = _make_volunteer("Ghost", "Nobody")
            db.session.commit()

            from services.pathful_id_backfill_service import (
                backfill_volunteer_from_profile,
            )

            result = backfill_volunteer_from_profile(v, None)
            assert result["pathful_id_set"] is False
            assert result["profile_found"] is False
            assert result["email_added"] is False


# ──────────────────────────────────────────────────────────────────────────────
# B2 regression — updated test for existing test_organization_service.py
# ──────────────────────────────────────────────────────────────────────────────
# NOTE: test_tier4_suffix_auto_learning in test_organization_service.py now FAILS
# after B2 because it asserts that the auto-learned alias was saved. That test was
# written against the pre-B2 behaviour. The corrected assertion is here:


class TestB2Regression:
    """
    Regression guard: the old test_tier4_suffix_auto_learning expected an alias
    to be auto-written. After B2 it must expect None (no alias) instead.
    This test replaces that expectation explicitly.
    """

    def test_tier4_no_longer_auto_writes_alias(self, app):
        with app.app_context():
            from models.organization import Organization, OrganizationAlias
            from services.organization_service import resolve_organization

            org = Organization(name="Next Level")
            db.session.add(org)
            db.session.commit()

            incoming = "Next Level, Inc."
            result = resolve_organization(incoming)

            # B2 changed this: result is now None (not org)
            assert result is None

            # And no alias was written
            assert OrganizationAlias.query.filter_by(name=incoming).first() is None

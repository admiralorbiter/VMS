"""
One-Time Teacher Linking Reconciliation Script
===============================================

Resolves unlinked TeacherProgress records by using the centralized matching
service.  The script:

1. Links unlinked PathfulUserProfiles to TeacherProgress (via match_tp_to_profile)
2. Resolves teacher_id for unlinked TPs (via resolve_teacher_for_tp)
3. Prints a report of changes made and unresolved records

Usage:
    # Dry run (default — no database changes)
    python scripts/reconcile_teacher_links.py

    # Apply changes
    python scripts/reconcile_teacher_links.py --commit
"""

import argparse
import sys

# Ensure project root is on the path
sys.path.insert(0, ".")

from app import create_app  # noqa: E402


def reconcile(commit: bool = False):
    app = create_app()
    with app.app_context():
        from models import db
        from models.pathful_import import PathfulUserProfile
        from models.teacher_progress import TeacherProgress
        from services.teacher_matching_service import (
            match_tp_to_profile,
            resolve_teacher_for_tp,
        )

        # --- Step 1: Link PathfulUserProfiles to TeacherProgress ---
        print("=" * 60)
        print("Step 1: Linking PathfulUserProfiles → TeacherProgress")
        print("=" * 60)

        unlinked_profiles = PathfulUserProfile.query.filter(
            PathfulUserProfile.signup_role == "Educator",
            PathfulUserProfile.teacher_progress_id.is_(None),
        ).count()
        print(f"  Unlinked educator profiles: {unlinked_profiles}")

        # We match TP → Profile (not the other way around) because
        # we care about the TPs that are in the active roster
        tps = TeacherProgress.query.filter_by(
            tenant_id=1, academic_year="2025-2026", is_active=True
        ).all()

        profile_linked = 0
        for tp in tps:
            if tp.pathful_user_id:
                # Already has a pathful_user_id, check if profile exists
                existing = PathfulUserProfile.query.filter_by(
                    pathful_user_id=tp.pathful_user_id,
                ).first()
                if existing and not existing.teacher_progress_id:
                    existing.link_to_teacher_progress(tp.id)
                    profile_linked += 1
                    print(f"  LINKED (pathful_id): TP {tp.id} [{tp.name}]")
                continue

            profile = match_tp_to_profile(tp)
            if profile:
                profile_linked += 1
                print(f"  LINKED: TP {tp.id} [{tp.name}] → Profile [{profile.name}]")

        print(f"\n  Profiles linked: {profile_linked}")

        # --- Step 2: Resolve teacher_id for unlinked TPs ---
        print("\n" + "=" * 60)
        print("Step 2: Resolving TeacherProgress → Teacher")
        print("=" * 60)

        orphans = [t for t in tps if t.teacher_id is None]
        print(f"  Unlinked TPs: {len(orphans)}")

        teachers_resolved = 0
        teachers_created = 0
        unresolved = []

        for tp in orphans:
            had_teacher = tp.teacher_id is not None
            teacher = resolve_teacher_for_tp(tp)
            if teacher:
                teachers_resolved += 1
                if teacher.import_source == "reconciliation":
                    teachers_created += 1
                    print(
                        f"  CREATED: TP {tp.id} [{tp.name}] → "
                        f"NEW Teacher {teacher.id}"
                    )
                else:
                    print(
                        f"  MATCHED: TP {tp.id} [{tp.name}] → "
                        f"Teacher {teacher.id} [{teacher.first_name} {teacher.last_name}]"
                    )
            else:
                unresolved.append(tp)
                print(f"  UNRESOLVED: TP {tp.id} [{tp.name}] email=[{tp.email}]")

        print(f"\n  Teachers resolved: {teachers_resolved}")
        print(f"  Teachers created: {teachers_created}")
        print(f"  Unresolved: {len(unresolved)}")

        # --- Summary ---
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Profiles linked: {profile_linked}")
        print(f"  Teachers resolved: {teachers_resolved} (created: {teachers_created})")
        print(f"  Unresolved TPs: {len(unresolved)}")

        if unresolved:
            print("\n  Unresolved teachers (requires manual review):")
            for tp in unresolved:
                print(f"    - TP {tp.id}: {tp.name} ({tp.email})")

        if commit:
            db.session.commit()
            print("\n  ✓ Changes committed to database.")
        else:
            db.session.rollback()
            print("\n  ⚠ DRY RUN — no changes saved. Use --commit to apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile unlinked teacher records")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply changes to the database (default is dry-run)",
    )
    args = parser.parse_args()
    reconcile(commit=args.commit)

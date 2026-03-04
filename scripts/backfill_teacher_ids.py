"""
One-time script to backfill TeacherProgress.teacher_id for records that
are missing it. Matches by name against the Teacher table.

Usage: python scripts/backfill_teacher_ids.py [--dry-run]
"""
import sys
import argparse

sys.path.insert(0, ".")

from app import create_app

app = create_app()


def backfill_teacher_ids(dry_run=True):
    with app.app_context():
        from models import db
        from models.teacher import Teacher
        from models.teacher_progress import TeacherProgress
        from services.teacher_matching_service import normalize_name

        # Find all TeacherProgress records with no teacher_id
        unlinked = TeacherProgress.query.filter(
            TeacherProgress.teacher_id.is_(None),
            TeacherProgress.is_active == True,
        ).all()

        print(f"Found {len(unlinked)} TeacherProgress records with teacher_id=NULL")

        if not unlinked:
            print("Nothing to do.")
            return

        # Build a lookup of normalized name -> Teacher
        all_teachers = Teacher.query.filter_by(active=True).all()
        teacher_by_name = {}
        for t in all_teachers:
            key = f"{normalize_name(t.first_name)} {normalize_name(t.last_name)}".strip()
            if key:
                teacher_by_name[key] = t

        print(f"Built lookup with {len(teacher_by_name)} active teachers")

        matched = 0
        unmatched = []

        for tp in unlinked:
            # Parse TeacherProgress name into first/last
            parts = tp.name.strip().split() if tp.name else []
            if len(parts) >= 2:
                first = parts[0]
                last = " ".join(parts[1:])
            elif len(parts) == 1:
                first = parts[0]
                last = ""
            else:
                unmatched.append(tp)
                continue

            key = f"{normalize_name(first)} {normalize_name(last)}".strip()
            teacher = teacher_by_name.get(key)

            if teacher:
                if not dry_run:
                    tp.teacher_id = teacher.id
                matched += 1
                print(f"  MATCH: {tp.name} -> Teacher #{teacher.id} ({teacher.first_name} {teacher.last_name})")
            else:
                unmatched.append(tp)

        print(f"\nMatched: {matched}")
        print(f"Unmatched: {len(unmatched)}")

        if unmatched:
            print("\nUnmatched teachers (no Teacher record found):")
            for tp in unmatched[:20]:
                print(f"  SKIP: {tp.name} ({tp.building})")
            if len(unmatched) > 20:
                print(f"  ... and {len(unmatched) - 20} more")

        if not dry_run and matched > 0:
            db.session.commit()
            print(f"\n✓ Committed {matched} teacher_id updates.")
        elif dry_run and matched > 0:
            print(f"\n[DRY RUN] Would update {matched} records. Run with --commit to apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit", action="store_true",
        help="Actually commit changes (default is dry-run)"
    )
    args = parser.parse_args()
    backfill_teacher_ids(dry_run=not args.commit)

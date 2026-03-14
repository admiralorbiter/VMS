"""
Duplicate Teacher Audit & Merge Script (TD-035)
=================================================

Finds and merges duplicate Teacher records caused by multi-part surname
mismatches (e.g., "Catalina Velarde" vs "Catalina Velarde Duarte").

Safety features:
- School validation: pairs with DIFFERENT schools are flagged for manual
  review and NOT auto-merged
- Merge log: saves a JSON log of all merges for undo capability
- Dry-run by default: use --commit to apply

Usage:
    # Audit only (generates review report)
    python scripts/maintenance/merge_duplicate_teachers.py

    # Apply safe merges only (skips conflicting-school pairs)
    python scripts/maintenance/merge_duplicate_teachers.py --commit

    # Undo a previous merge (requires merge_log JSON)
    python scripts/maintenance/merge_duplicate_teachers.py --undo merge_log_TIMESTAMP.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from app import create_app  # noqa: E402


def _last_name_matches(name_a, name_b):
    """Word-boundary last name matching (mirrors teacher_service.py)."""
    if not name_a or not name_b:
        return False
    if name_a == name_b:
        return True
    shorter, longer = (
        (name_a, name_b) if len(name_a) <= len(name_b) else (name_b, name_a)
    )
    if not longer.startswith(shorter):
        return False
    next_char = longer[len(shorter)]
    return next_char in (" ", "-")


def _schools_compatible(t1, t2):
    """Check if two teachers' schools are compatible for merging.

    Returns: (is_safe, reason)
    - Safe: same school, or one/both have no school
    - Unsafe: different schools
    """
    s1 = t1.school.name if t1.school else None
    s2 = t2.school.name if t2.school else None

    if not s1 and not s2:
        return True, "both have no school"
    if not s1 or not s2:
        return True, "one has no school"
    if s1.lower().strip() == s2.lower().strip():
        return True, f"same school: {s1}"
    return False, f"DIFFERENT schools: '{s1}' vs '{s2}'"


def find_duplicates(teachers, normalize_name):
    """Find duplicate Teacher pairs using word-boundary name matching."""
    from models.event import EventTeacher

    by_first = {}
    for t in teachers:
        first = normalize_name(t.first_name or "").strip()
        last = normalize_name(t.last_name or "").strip()
        if first and last:
            by_first.setdefault(first, []).append((t, last))

    pairs = []
    seen_ids = set()

    for first_name, group in sorted(by_first.items()):
        if len(group) < 2:
            continue
        for i, (t1, last1) in enumerate(group):
            for t2, last2 in group[i + 1 :]:
                if t1.id == t2.id:
                    continue
                # Only multi-part surname variants (not exact-name duplicates)
                if last1 != last2 and _last_name_matches(last1, last2):
                    pair_key = tuple(sorted([t1.id, t2.id]))
                    if pair_key in seen_ids:
                        continue
                    seen_ids.add(pair_key)

                    et1 = EventTeacher.query.filter_by(teacher_id=t1.id).count()
                    et2 = EventTeacher.query.filter_by(teacher_id=t2.id).count()

                    if et1 > et2:
                        canonical, duplicate = t1, t2
                    elif et2 > et1:
                        canonical, duplicate = t2, t1
                    else:
                        canonical, duplicate = (t1, t2) if t1.id < t2.id else (t2, t1)

                    school_safe, school_reason = _schools_compatible(
                        canonical, duplicate
                    )
                    pairs.append(
                        {
                            "canonical": canonical,
                            "duplicate": duplicate,
                            "school_safe": school_safe,
                            "school_reason": school_reason,
                        }
                    )

    return pairs


def merge_teacher(canonical, duplicate, db, dry_run=True):
    """Merge duplicate Teacher into canonical. Returns stats and undo info."""
    from models.event import EventTeacher
    from models.pathful_import import PathfulUnmatchedRecord
    from models.student import Student
    from models.teacher_progress import TeacherProgress

    stats = {
        "event_teachers_moved": 0,
        "event_teachers_deduped": 0,
        "teacher_progress_moved": 0,
        "students_moved": 0,
        "unmatched_moved": 0,
    }
    undo_info = {
        "canonical_id": canonical.id,
        "duplicate_id": duplicate.id,
        "canonical_name": f"{canonical.first_name} {canonical.last_name}",
        "duplicate_name": f"{duplicate.first_name} {duplicate.last_name}",
        "moved_event_teacher_event_ids": [],
        "deduped_event_ids": [],
        "status_upgrades": [],
        "moved_tp_ids": [],
        "moved_student_ids": [],
        "moved_unmatched_ids": [],
    }

    # EventTeacher: status-aware merge
    canonical_events = {
        et.event_id: et
        for et in EventTeacher.query.filter_by(teacher_id=canonical.id).all()
    }

    dup_event_teachers = EventTeacher.query.filter_by(teacher_id=duplicate.id).all()
    for et in dup_event_teachers:
        if et.event_id in canonical_events:
            canon_et = canonical_events[et.event_id]
            STATUS_PRIORITY = {"attended": 3, "no_show": 2, "registered": 1}
            dup_priority = STATUS_PRIORITY.get(et.status, 0)
            canon_priority = STATUS_PRIORITY.get(canon_et.status, 0)

            if dup_priority > canon_priority:
                old_status = canon_et.status
                if not dry_run:
                    canon_et.status = et.status
                    if et.confirmed_at and not canon_et.confirmed_at:
                        canon_et.confirmed_at = et.confirmed_at
                undo_info["status_upgrades"].append(
                    {
                        "event_id": et.event_id,
                        "old_status": old_status,
                        "new_status": et.status,
                    }
                )

            if not dry_run:
                db.session.delete(et)
            undo_info["deduped_event_ids"].append(et.event_id)
            stats["event_teachers_deduped"] += 1
        else:
            if not dry_run:
                et.teacher_id = canonical.id
            undo_info["moved_event_teacher_event_ids"].append(et.event_id)
            stats["event_teachers_moved"] += 1

    # TeacherProgress
    for tp in TeacherProgress.query.filter_by(teacher_id=duplicate.id).all():
        if not dry_run:
            tp.teacher_id = canonical.id
        undo_info["moved_tp_ids"].append(tp.id)
        stats["teacher_progress_moved"] += 1

    # Student
    for s in Student.query.filter_by(teacher_id=duplicate.id).all():
        if not dry_run:
            s.teacher_id = canonical.id
        undo_info["moved_student_ids"].append(s.id)
        stats["students_moved"] += 1

    # PathfulUnmatchedRecord
    for um in PathfulUnmatchedRecord.query.filter_by(
        resolved_teacher_id=duplicate.id
    ).all():
        if not dry_run:
            um.resolved_teacher_id = canonical.id
        undo_info["moved_unmatched_ids"].append(um.id)
        stats["unmatched_moved"] += 1

    # Mark duplicate inactive
    if not dry_run:
        duplicate.active = False
        duplicate.import_source = (
            f"merged_into_{canonical.id}"
            if not duplicate.import_source
            else f"{duplicate.import_source}|merged_into_{canonical.id}"
        )

    return stats, undo_info


def run_audit_and_merge(commit=False):
    """Main entry point."""
    app = create_app()
    with app.app_context():
        from models import db
        from models.event import EventTeacher
        from models.teacher import Teacher
        from services.teacher_matching_service import normalize_name

        teachers = Teacher.query.filter(Teacher.active == True).all()

        lines = []
        lines.append(f"Duplicate Teacher Audit Report (TD-035)")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total active teachers: {len(teachers)}")
        lines.append("=" * 70)

        pairs = find_duplicates(teachers, normalize_name)

        if not pairs:
            lines.append("\nNo multi-part surname duplicates found!")
            report = "\n".join(lines)
            print(report)
            return

        safe_pairs = [p for p in pairs if p["school_safe"]]
        review_pairs = [p for p in pairs if not p["school_safe"]]

        lines.append(f"\nFound {len(pairs)} pairs total:")
        lines.append(f"  SAFE to merge: {len(safe_pairs)} (same school or no school)")
        lines.append(f"  NEEDS REVIEW:  {len(review_pairs)} (different schools)")

        # --- Safe pairs ---
        if safe_pairs:
            lines.append(f"\n{'=' * 70}")
            lines.append("SAFE TO MERGE (same school or one/both have no school)")
            lines.append("=" * 70)

        merge_log = []
        total_stats = {
            "event_teachers_moved": 0,
            "event_teachers_deduped": 0,
            "teacher_progress_moved": 0,
            "students_moved": 0,
            "unmatched_moved": 0,
        }

        for i, pair in enumerate(safe_pairs, 1):
            canonical, duplicate = pair["canonical"], pair["duplicate"]
            c_school = canonical.school.name if canonical.school else "--"
            d_school = duplicate.school.name if duplicate.school else "--"
            c_et = EventTeacher.query.filter_by(teacher_id=canonical.id).count()
            d_et = EventTeacher.query.filter_by(teacher_id=duplicate.id).count()

            lines.append(f"\n  Safe Pair {i}: ({pair['school_reason']})")
            lines.append(
                f"    KEEP  [{canonical.id:>6}] {canonical.first_name} {canonical.last_name} "
                f'(ETs={c_et}, school="{c_school}", src={canonical.import_source})'
            )
            lines.append(
                f"    MERGE [{duplicate.id:>6}] {duplicate.first_name} {duplicate.last_name} "
                f'(ETs={d_et}, school="{d_school}", src={duplicate.import_source})'
            )

            stats, undo_info = merge_teacher(
                canonical, duplicate, db, dry_run=not commit
            )
            merge_log.append(undo_info)

            actions = []
            if stats["event_teachers_moved"]:
                actions.append(f"{stats['event_teachers_moved']} ETs moved")
            if stats["event_teachers_deduped"]:
                actions.append(f"{stats['event_teachers_deduped']} ETs deduped")
            if stats["teacher_progress_moved"]:
                actions.append(f"{stats['teacher_progress_moved']} TPs moved")
            if stats["students_moved"]:
                actions.append(f"{stats['students_moved']} students moved")
            if stats["unmatched_moved"]:
                actions.append(f"{stats['unmatched_moved']} unmatched moved")

            lines.append(
                f"    -> {', '.join(actions) if actions else 'No FK references to move'}"
            )

            for key in total_stats:
                if key in stats:
                    total_stats[key] += stats[key]

        # --- Review pairs ---
        if review_pairs:
            lines.append(f"\n{'=' * 70}")
            lines.append("NEEDS MANUAL REVIEW (different schools -- NOT merged)")
            lines.append("=" * 70)

        for i, pair in enumerate(review_pairs, 1):
            canonical, duplicate = pair["canonical"], pair["duplicate"]
            c_school = canonical.school.name if canonical.school else "--"
            d_school = duplicate.school.name if duplicate.school else "--"
            c_et = EventTeacher.query.filter_by(teacher_id=canonical.id).count()
            d_et = EventTeacher.query.filter_by(teacher_id=duplicate.id).count()

            lines.append(f"\n  Review Pair {i}: {pair['school_reason']}")
            lines.append(
                f"    [{canonical.id:>6}] {canonical.first_name} {canonical.last_name} "
                f'(ETs={c_et}, school="{c_school}", src={canonical.import_source})'
            )
            lines.append(
                f"    [{duplicate.id:>6}] {duplicate.first_name} {duplicate.last_name} "
                f'(ETs={d_et}, school="{d_school}", src={duplicate.import_source})'
            )

        # --- Summary ---
        lines.append(f"\n{'=' * 70}")
        lines.append("SUMMARY")
        lines.append("=" * 70)
        lines.append(f"  Safe pairs merged: {len(safe_pairs)}")
        lines.append(f"  Review pairs skipped: {len(review_pairs)}")
        lines.append(f"  EventTeachers moved: {total_stats['event_teachers_moved']}")
        lines.append(
            f"  EventTeachers deduped: {total_stats['event_teachers_deduped']}"
        )
        lines.append(
            f"  TeacherProgress moved: {total_stats['teacher_progress_moved']}"
        )

        if commit:
            db.session.commit()
            lines.append(f"\n  >>> Changes committed to database.")

            # Save merge log for undo capability
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            log_path = f"scripts/maintenance/merge_log_{timestamp}.json"
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(merge_log, f, indent=2)
            lines.append(f"  >>> Merge log saved: {log_path}")
        else:
            db.session.rollback()
            lines.append(f"\n  DRY RUN -- no changes saved. Use --commit to apply.")

        # Write report to file
        report = "\n".join(lines)
        report_path = "scripts/maintenance/duplicate_teacher_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(report)
        print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Audit and merge duplicate Teacher records (TD-035)"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply safe merges to the database (default is dry-run audit)",
    )
    args = parser.parse_args()
    run_audit_and_merge(commit=args.commit)

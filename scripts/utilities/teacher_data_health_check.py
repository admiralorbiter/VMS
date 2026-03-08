"""
Teacher Data Health Check
========================

Diagnostic script that reports data integrity issues in the teacher data system.
Run manually as an audit tool.

Usage:
    python scripts/utilities/teacher_data_health_check.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import create_app
from models import db
from models.event import Event, EventTeacher, EventType
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress


def run_health_check():
    """Run all health checks and print a summary."""
    app = create_app()
    with app.app_context():
        issues = []

        # Check 1: Teachers without cached_email
        no_email = Teacher.query.filter(
            Teacher.cached_email.is_(None),
            Teacher.active.is_(True),
        ).count()
        if no_email > 0:
            issues.append(f"  ⚠ {no_email} active teachers without cached_email")

        # Check 2: Unlinked TeacherProgress records (no teacher_id)
        unlinked = TeacherProgress.query.filter(
            TeacherProgress.teacher_id.is_(None),
            TeacherProgress.is_active.is_(True),
        ).count()
        if unlinked > 0:
            issues.append(
                f"  ⚠ {unlinked} active TeacherProgress without teacher_id (unlinked)"
            )

        # Check 3: event.educators entries without matching EventTeacher
        events_with_educators = Event.query.filter(
            Event.educators.isnot(None),
            Event.educators != "",
            Event.type == EventType.VIRTUAL_SESSION,
        ).all()

        orphan_text_count = 0
        for event in events_with_educators:
            et_count = EventTeacher.query.filter_by(event_id=event.id).count()
            if et_count == 0:
                orphan_text_count += 1

        if orphan_text_count > 0:
            issues.append(
                f"  ⚠ {orphan_text_count} events have educators text but no EventTeacher records"
            )

        # Check 4: Duplicate Teacher records (same name + same school)
        from sqlalchemy import func

        dupes = (
            db.session.query(
                func.lower(Teacher.first_name),
                func.lower(Teacher.last_name),
                Teacher.school_id,
                func.count(Teacher.id).label("cnt"),
            )
            .group_by(
                func.lower(Teacher.first_name),
                func.lower(Teacher.last_name),
                Teacher.school_id,
            )
            .having(func.count(Teacher.id) > 1)
            .all()
        )
        if dupes:
            issues.append(
                f"  ⚠ {len(dupes)} duplicate teacher groups (same name + school)"
            )

        # Check 5: Teachers without tenant_id (skip if column doesn't exist yet)
        try:
            no_tenant = Teacher.query.filter(
                Teacher.tenant_id.is_(None),
                Teacher.active.is_(True),
            ).count()
            if no_tenant > 0:
                issues.append(f"  ℹ {no_tenant} active teachers without tenant_id")
        except Exception:
            issues.append("  ℹ tenant_id column not yet in database (run migration)")

        # Summary
        total_teachers = Teacher.query.count()
        active_teachers = Teacher.query.filter_by(active=True).count()
        total_tp = TeacherProgress.query.count()
        total_et = EventTeacher.query.count()

        print("=== Teacher Data Health Check ===")
        print(f"  Teachers: {total_teachers} total, {active_teachers} active")
        print(f"  TeacherProgress: {total_tp}")
        print(f"  EventTeacher: {total_et}")
        print()

        if issues:
            print(f"Issues found ({len(issues)}):")
            for issue in issues:
                print(issue)
        else:
            print("✅ No issues found!")

        return len(issues)


if __name__ == "__main__":
    exit_code = run_health_check()
    sys.exit(1 if exit_code > 0 else 0)

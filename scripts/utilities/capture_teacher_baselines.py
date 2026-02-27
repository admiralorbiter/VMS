"""
Sprint 0: Capture Dashboard Baselines
======================================

Captures current teacher data metrics before the refactor starts.
These numbers will be compared after the refactor to verify data integrity.

Usage:
    python scripts/utilities/capture_teacher_baselines.py
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import func

from app import create_app
from models import db
from models.event import Event, EventTeacher
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress


def capture_baselines():
    """Capture and print current teacher data metrics."""
    print("=" * 60)
    print(f"TEACHER DATA BASELINES — {datetime.now().isoformat()}")
    print("=" * 60)

    # --- Teacher records ---
    total_teachers = Teacher.query.count()
    teachers_with_school = Teacher.query.filter(Teacher.school_id.isnot(None)).count()
    teachers_without_school = total_teachers - teachers_with_school
    teachers_active = Teacher.query.filter_by(active=True).count()

    print(f"\n--- Teacher Records ---")
    print(f"  Total:             {total_teachers}")
    print(f"  Active:            {teachers_active}")
    print(f"  With school_id:    {teachers_with_school}")
    print(f"  Without school_id: {teachers_without_school}")

    # --- TeacherProgress records ---
    total_tp = TeacherProgress.query.count()
    tp_active = TeacherProgress.query.filter_by(is_active=True).count()
    tp_linked = TeacherProgress.query.filter(
        TeacherProgress.teacher_id.isnot(None)
    ).count()
    tp_unlinked = total_tp - tp_linked

    print(f"\n--- TeacherProgress Records ---")
    print(f"  Total:      {total_tp}")
    print(f"  Active:     {tp_active}")
    print(
        f"  Linked:     {tp_linked} ({tp_linked/total_tp*100:.1f}%)"
        if total_tp > 0
        else "  Linked:     0"
    )
    print(f"  Unlinked:   {tp_unlinked}")

    # --- TeacherProgress duplicates ---
    duplicates = (
        db.session.query(
            TeacherProgress.tenant_id,
            TeacherProgress.academic_year,
            func.lower(TeacherProgress.email).label("email_lower"),
            func.count(TeacherProgress.id).label("cnt"),
        )
        .group_by(
            TeacherProgress.tenant_id,
            TeacherProgress.academic_year,
            func.lower(TeacherProgress.email),
        )
        .having(func.count(TeacherProgress.id) > 1)
        .all()
    )
    print(f"  Duplicate groups: {len(duplicates)}")

    # --- EventTeacher records ---
    total_et = EventTeacher.query.count()
    print(f"\n--- EventTeacher Records ---")
    print(f"  Total:      {total_et}")

    # --- Events with educators text ---
    events_with_educators = Event.query.filter(
        Event.educators.isnot(None), Event.educators != ""
    ).count()
    events_total = Event.query.count()

    print(f"\n--- Event Records ---")
    print(f"  Total events:            {events_total}")
    print(f"  With educators text:     {events_with_educators}")

    # --- Events with professionals text ---
    events_with_professionals = Event.query.filter(
        Event.professionals.isnot(None), Event.professionals != ""
    ).count()
    print(f"  With professionals text: {events_with_professionals}")

    # --- Consistency check: EventTeacher vs event.educators ---
    # Count events that have EventTeacher records
    events_with_et = db.session.query(
        func.count(func.distinct(EventTeacher.event_id))
    ).scalar()
    print(f"\n--- Consistency ---")
    print(f"  Events with EventTeacher FK links:   {events_with_et}")
    print(f"  Events with educators text field:     {events_with_educators}")

    # --- Schools ---
    total_schools = School.query.count()
    print(f"\n--- Schools ---")
    print(f"  Total: {total_schools}")

    # --- By tenant ---
    tp_by_tenant = (
        db.session.query(
            TeacherProgress.tenant_id,
            func.count(TeacherProgress.id),
        )
        .group_by(TeacherProgress.tenant_id)
        .all()
    )
    print(f"\n--- TeacherProgress by Tenant ---")
    for tenant_id, count in tp_by_tenant:
        print(f"  Tenant {tenant_id}: {count} records")

    # --- By academic year ---
    tp_by_year = (
        db.session.query(
            TeacherProgress.academic_year,
            func.count(TeacherProgress.id),
        )
        .group_by(TeacherProgress.academic_year)
        .all()
    )
    print(f"\n--- TeacherProgress by Academic Year ---")
    for year, count in tp_by_year:
        print(f"  {year}: {count} records")

    print(f"\n{'=' * 60}")
    print("Save this output for post-refactor comparison.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        capture_baselines()

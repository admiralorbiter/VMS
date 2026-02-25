"""
Fix Duplicate TeacherProgress Records
======================================

One-time script to remove duplicate TeacherProgress records caused by
import_roster() matching on district_name instead of tenant_id.

For each (tenant_id, academic_year, email) group with multiple records,
keeps the oldest record (lowest id) and deletes the rest.

Usage:
    python scripts/utilities/fix_duplicate_teachers.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import func

from app import create_app
from models import db
from models.teacher_progress import TeacherProgress


def fix_duplicates():
    """Find and remove duplicate TeacherProgress records."""
    # Find groups with duplicates: same tenant_id, academic_year, email (case-insensitive)
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

    if not duplicates:
        print("No duplicate TeacherProgress records found.")
        return

    print(f"Found {len(duplicates)} groups of duplicates.\n")

    total_deleted = 0

    for dup in duplicates:
        tenant_id = dup.tenant_id
        academic_year = dup.academic_year
        email_lower = dup.email_lower

        # Get all records in this group, ordered by id
        records = (
            TeacherProgress.query.filter(
                TeacherProgress.tenant_id == tenant_id,
                TeacherProgress.academic_year == academic_year,
                func.lower(TeacherProgress.email) == email_lower,
            )
            .order_by(TeacherProgress.id)
            .all()
        )

        # Keep the first (oldest), delete the rest
        keeper = records[0]
        to_delete = records[1:]

        print(
            f"  {keeper.name} ({email_lower}) tenant={tenant_id} year={academic_year}: "
            f"keeping id={keeper.id}, deleting ids={[r.id for r in to_delete]}"
        )

        for record in to_delete:
            db.session.delete(record)
            total_deleted += 1

    db.session.commit()
    print(f"\n✅ Done. Deleted {total_deleted} duplicate records.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        fix_duplicates()

"""
Script to match TeacherProgress entries to Teacher records.
This can be run from the command line or imported as a module.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import app
from routes.virtual.usage import (
    get_current_virtual_year,
    match_teacher_progress_to_teachers,
)

if __name__ == "__main__":
    with app.app_context():
        virtual_year = sys.argv[1] if len(sys.argv) > 1 else get_current_virtual_year()
        print(f"Matching teachers for virtual year: {virtual_year}")
        print("=" * 60)

        stats = match_teacher_progress_to_teachers(virtual_year=virtual_year)

        print(f"\nMatching Results:")
        print(f"  Total processed: {stats['total_processed']}")
        print(f"  Matched by email: {stats['matched_by_email']}")
        print(f"  Matched by name: {stats['matched_by_name']}")
        print(f"  Unmatched: {stats['unmatched']}")

        if stats["errors"]:
            print(f"\nErrors ({len(stats['errors'])}):")
            for error in stats["errors"]:
                print(f"  - {error}")

        print("\n" + "=" * 60)
        print("Matching complete!")

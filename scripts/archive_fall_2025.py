"""
Script to manually archive Fall 2025 semester stats for KCKPS.
Run this script to populate the archive with data from the completed Fall 2025 semester.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from routes.virtual.usage import snapshot_semester_progress

app = create_app()


def run_archive():
    with app.app_context():
        print("Starting manual archive for Fall 2025...")

        district_name = "Kansas City Kansas Public Schools"
        virtual_year = "2025-2026"
        semester_name = "Fall 2025"

        # Fall 2025 Dates: July 1, 2025 - Dec 31, 2025
        # (Using the dates defined in our new get_semester_dates helper logic)
        date_from = datetime(2025, 7, 1, 0, 0, 0)
        date_to = datetime(2025, 12, 31, 23, 59, 59)

        success, count = snapshot_semester_progress(
            district_name, virtual_year, semester_name, date_from, date_to
        )

        if success:
            print(
                f"SUCCESS: Archived {count} teacher progress records for {semester_name}."
            )
        else:
            print("FAILURE: Could not archive records. Check logs.")


if __name__ == "__main__":
    run_archive()

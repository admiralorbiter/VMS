#!/usr/bin/env python3
"""
Script to mark volunteers as excluded from reports
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.volunteer import Volunteer


def mark_excluded_volunteers():
    """Mark specific volunteers as excluded from reports"""
    with app.app_context():
        # List of volunteers to exclude from reports
        excluded_names = [
            ("Christopher", "Hamman"),
            # Add more names as needed
        ]

        for first_name, last_name in excluded_names:
            print(f"Looking for volunteer: {first_name} {last_name}")

            volunteer = Volunteer.query.filter(Volunteer.first_name.ilike(f"%{first_name}%"), Volunteer.last_name.ilike(f"%{last_name}%")).first()

            if volunteer:
                print(f"Found volunteer: {volunteer.first_name} {volunteer.last_name} (ID: {volunteer.id})")
                print(f"Current exclude_from_reports: {volunteer.exclude_from_reports}")
                volunteer.exclude_from_reports = True
                print(f"Marked {volunteer.first_name} {volunteer.last_name} as excluded from reports")
            else:
                print(f"Volunteer {first_name} {last_name} not found")

        # Commit changes
        db.session.commit()
        print("Changes committed successfully")


if __name__ == "__main__":
    mark_excluded_volunteers()

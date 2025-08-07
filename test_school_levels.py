#!/usr/bin/env python3
"""
Test script to update school levels from Google Sheet
"""

import os

import pandas as pd

from app import app
from models import db
from models.school_model import School


def test_school_levels():
    """Test updating school levels from Google Sheet"""
    with app.app_context():
        print("=== Before School Level Update ===")
        schools_with_levels = School.query.filter(School.level.isnot(None)).count()
        schools_without_levels = School.query.filter(School.level.is_(None)).count()
        print(f"Schools with levels: {schools_with_levels}")
        print(f"Schools without levels: {schools_without_levels}")

        # Show some sample schools before update
        schools = School.query.limit(5).all()
        print("\nSample schools before update:")
        for school in schools:
            print(f"  {school.id} - {school.name} (Level: {school.level})")

        print("\n=== Updating School Levels ===")
        try:
            sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
            print(f"DEBUG: SCHOOL_MAPPING_GOOGLE_SHEET = {sheet_id}")

            if not sheet_id:
                raise ValueError("School mapping Google Sheet ID not configured")

            # Try primary URL format
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
            print(f"DEBUG: Trying CSV URL: {csv_url}")

            try:
                df = pd.read_csv(csv_url)
                print(f"DEBUG: Successfully read CSV with {len(df)} rows")
                print(f"DEBUG: CSV columns: {list(df.columns)}")
            except Exception as e:
                print(f"DEBUG: Failed to read CSV with primary URL: {str(e)}")

                # Try alternative URL format
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                print(f"DEBUG: Trying alternative CSV URL: {csv_url}")
                df = pd.read_csv(csv_url)
                print(f"DEBUG: Successfully read CSV with alternative URL, {len(df)} rows")

            success_count = 0
            error_count = 0
            errors = []

            # Process each row
            for index, row in df.iterrows():
                try:
                    # Skip rows without an ID or Level
                    if pd.isna(row["Id"]) or pd.isna(row["Level"]):
                        print(f"DEBUG: Skipping row {index} - missing Id or Level")
                        continue

                    print(f"DEBUG: Processing row {index} - Id: {row['Id']}, Level: {row['Level']}")

                    # Find the school by Salesforce ID
                    school = School.query.get(row["Id"])
                    if school:
                        school.level = row["Level"].strip()
                        success_count += 1
                        print(f"DEBUG: Updated school {school.name} to level {school.level}")
                    else:
                        error_count += 1
                        error_msg = f"School not found with ID: {row['Id']}"
                        errors.append(error_msg)
                        print(f"DEBUG: {error_msg}")

                except Exception as e:
                    error_count += 1
                    error_msg = f"Error processing school {row.get('Id')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"DEBUG: {error_msg}")

            db.session.commit()
            print(f"DEBUG: Final result - {success_count} successes, {error_count} errors")

            print("\n=== After School Level Update ===")
            schools_with_levels = School.query.filter(School.level.isnot(None)).count()
            schools_without_levels = School.query.filter(School.level.is_(None)).count()
            print(f"Schools with levels: {schools_with_levels}")
            print(f"Schools without levels: {schools_without_levels}")

            # Show some sample schools after update
            schools = School.query.limit(5).all()
            print("\nSample schools after update:")
            for school in schools:
                print(f"  {school.id} - {school.name} (Level: {school.level})")

        except Exception as e:
            print(f"Error during school level update: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_school_levels()

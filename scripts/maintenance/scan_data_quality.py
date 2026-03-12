"""
Data Quality Scanner
====================

Scans existing database records for data quality issues and populates
the DataQualityFlag table. Detection-only — does NOT modify source data.

Usage:
    python scripts/maintenance/scan_data_quality.py              # Run all detectors
    python scripts/maintenance/scan_data_quality.py --check names # Run only name detector
    python scripts/maintenance/scan_data_quality.py --check orgs  # Run only org detector
    python scripts/maintenance/scan_data_quality.py --check students  # Run only student detector
    python scripts/maintenance/scan_data_quality.py --dry-run     # Preview without writing flags

Detectors:
    names     - ALL CAPS contact names (first, last, middle)
    orgs      - Organizations missing a type classification
    students  - Student records with literal 'None' email/phone (TD-033)

Adding new detectors:
    1. Create a function: detect_<name>(dry_run=False) -> dict with 'found' and 'flagged' keys
    2. Register it in DETECTORS dict at the bottom of this file
    3. Add a DataQualityIssueType constant if needed

This script is idempotent — running it multiple times won't create duplicate flags
thanks to the unique constraint on (entity_type, entity_id, issue_type).
"""

import argparse
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app import app, db  # noqa: E402


def detect_all_caps_names(dry_run=False):
    """Detect contacts (volunteers) with ALL CAPS first or last names."""
    from models.volunteer import Volunteer
    from routes.name_utils import is_all_caps_name

    stats = {"found": 0, "flagged": 0, "skipped_existing": 0}

    volunteers = Volunteer.query.all()
    total = len(volunteers)
    print(f"  Scanning {total} volunteers for ALL CAPS names...")

    batch_size = 500
    for i, vol in enumerate(volunteers):
        # Check first and last name
        names_to_check = [
            ("first_name", vol.first_name),
            ("last_name", vol.last_name),
            ("middle_name", vol.middle_name),
        ]

        for field, name in names_to_check:
            if is_all_caps_name(name):
                stats["found"] += 1

                if not dry_run:
                    from models.data_quality_flag import flag_data_quality_issue

                    flag = flag_data_quality_issue(
                        entity_type="contact",
                        entity_id=vol.id,
                        issue_type="all_caps_name",
                        details=f"Original: {vol.first_name} {vol.last_name}",
                        salesforce_id=vol.salesforce_individual_id,
                    )
                    if flag.id is None:  # New flag (not yet flushed)
                        stats["flagged"] += 1
                    else:
                        stats["skipped_existing"] += 1
                break  # One flag per volunteer, not per field

        # Commit in batches
        if not dry_run and (i + 1) % batch_size == 0:
            db.session.commit()
            print(f"    → Committed batch ({i + 1}/{total})")

    if not dry_run:
        db.session.commit()

    return stats


def detect_missing_org_type(dry_run=False):
    """Detect organizations with NULL or empty org_type."""
    from models.organization import Organization

    stats = {"found": 0, "flagged": 0, "skipped_existing": 0}

    orgs = Organization.query.filter(
        db.or_(
            Organization.type.is_(None),
            Organization.type == "",
        )
    ).all()

    stats["found"] = len(orgs)
    print(f"  Found {stats['found']} organizations with missing type...")

    for org in orgs:
        if not dry_run:
            from models.data_quality_flag import flag_data_quality_issue

            flag = flag_data_quality_issue(
                entity_type="organization",
                entity_id=org.id,
                issue_type="null_org_type",
                details=f"Organization: {org.name}",
                salesforce_id=org.salesforce_id,
            )
            if flag.id is None:
                stats["flagged"] += 1
            else:
                stats["skipped_existing"] += 1

    if not dry_run:
        db.session.commit()

    return stats


def detect_student_none_strings(dry_run=False):
    """Detect student records with literal string 'None' in email/phone (TD-033)."""
    from models.contact import Email, Phone
    from models.student import Student

    stats = {"found": 0, "flagged": 0, "skipped_existing": 0, "detail": {}}

    # Check emails with literal 'None'
    none_emails = (
        db.session.query(Email)
        .join(Student, Email.contact_id == Student.id)
        .filter(Email.email == "None")
        .count()
    )
    stats["detail"]["none_emails"] = none_emails
    stats["found"] += none_emails

    # Check phones with literal 'None'
    none_phones = (
        db.session.query(Phone)
        .join(Student, Phone.contact_id == Student.id)
        .filter(Phone.number == "None")
        .count()
    )
    stats["detail"]["none_phones"] = none_phones
    stats["found"] += none_phones

    print(f"  Found {none_emails} email='None' and {none_phones} phone='None' records")

    # Flag at the student level (one flag per affected student)
    if none_emails > 0 or none_phones > 0:
        affected_student_ids = set()

        email_students = (
            db.session.query(Email.contact_id)
            .join(Student, Email.contact_id == Student.id)
            .filter(Email.email == "None")
            .all()
        )
        affected_student_ids.update(row[0] for row in email_students)

        phone_students = (
            db.session.query(Phone.contact_id)
            .join(Student, Phone.contact_id == Student.id)
            .filter(Phone.number == "None")
            .all()
        )
        affected_student_ids.update(row[0] for row in phone_students)

        print(f"  Affected students: {len(affected_student_ids)}")

        batch_size = 500
        for i, student_id in enumerate(affected_student_ids):
            if not dry_run:
                from models.data_quality_flag import flag_data_quality_issue

                flag = flag_data_quality_issue(
                    entity_type="student",
                    entity_id=student_id,
                    issue_type="other",
                    details="TD-033: email or phone contains literal string 'None'",
                )
                if flag.id is None:
                    stats["flagged"] += 1
                else:
                    stats["skipped_existing"] += 1

            if not dry_run and (i + 1) % batch_size == 0:
                db.session.commit()
                print(f"    → Committed batch ({i + 1}/{len(affected_student_ids)})")

        if not dry_run:
            db.session.commit()

    return stats


# ────────────────────────────────────────────────────────
# Registry of detectors — add new ones here
# ────────────────────────────────────────────────────────
DETECTORS = {
    "names": ("ALL CAPS Contact Names", detect_all_caps_names),
    "orgs": ("Missing Organization Type", detect_missing_org_type),
    "students": ("Student str(None) Data (TD-033)", detect_student_none_strings),
}


def main():
    parser = argparse.ArgumentParser(
        description="Scan database for data quality issues and populate flags."
    )
    parser.add_argument(
        "--check",
        choices=list(DETECTORS.keys()),
        help="Run only a specific detector (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview issues without writing flags to the database",
    )
    args = parser.parse_args()

    detectors_to_run = {args.check: DETECTORS[args.check]} if args.check else DETECTORS

    with app.app_context():
        print("=" * 60)
        print("DATA QUALITY SCAN")
        print(
            f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE (writing flags)'}"
        )
        print(f"Detectors: {', '.join(detectors_to_run.keys())}")
        print("=" * 60)

        total_found = 0
        total_flagged = 0

        for key, (label, detector_fn) in detectors_to_run.items():
            print(f"\n[{key.upper()}] {label}")
            print("-" * 40)

            stats = detector_fn(dry_run=args.dry_run)

            total_found += stats["found"]
            total_flagged += stats.get("flagged", 0)

            print(f"  Results: {stats['found']} issues found", end="")
            if not args.dry_run:
                print(
                    f", {stats['flagged']} new flags created"
                    f", {stats.get('skipped_existing', 0)} already flagged"
                )
            else:
                print(" (dry run — no flags created)")

            if "detail" in stats:
                for k, v in stats["detail"].items():
                    print(f"    {k}: {v}")

        print(f"\n{'=' * 60}")
        print(f"SUMMARY: {total_found} total issues found", end="")
        if not args.dry_run:
            print(f", {total_flagged} new flags created")
            print("View results at: /admin/data-quality")
        else:
            print(" (dry run)")
        print("=" * 60)


if __name__ == "__main__":
    main()

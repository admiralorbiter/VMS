#!/usr/bin/env python3
"""
Standalone Virtual Import Script for 2025-2026 Academic Year
============================================================

This script runs the virtual session import for the 2025-2026 academic year
as a standalone script without requiring the Flask app to be running.

Usage:
    python scripts/run_virtual_import_2025_26_standalone.py

Features:
- Imports virtual session data from Google Sheets
- Works standalone without Flask app running
- Provides detailed progress reporting
- Handles errors gracefully with rollback
- Processes teachers, presenters, and events
- Creates or updates districts and schools

Requirements:
- Valid Google Sheet configuration for 2025-2026 academic year
- Database connection and models
- All required dependencies installed

Example Output:
    === Virtual Import Script for 2025-2026 Academic Year ===
    Started at: 2025-01-27 15:30:00 UTC

    [SUCCESS] Found Google Sheet configuration for 2025-2026
       Sheet ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
       Sheet Name: Virtual Sessions 2025-2026

    [INFO] Starting import process...
    ==================================================
    === Starting Import: 150 rows ===
    ...
    ==================================================
    [SUCCESS] IMPORT COMPLETED SUCCESSFULLY!
       Events processed: 45
       Warnings: 12
       Errors: 3
    [INFO] Note: Import updates existing events with latest data - no purge needed!
    Completed at: 2025-01-27 15:32:15 UTC
"""

import os
import sys
from datetime import datetime, timezone

# Ensure repository root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pandas as pd
import requests

from app import app
from models import db
from models.email import EmailTemplate
from models.google_sheet import GoogleSheet
from models.user import SecurityLevel, User
from utils.email import create_delivery_attempt, create_email_message


def ensure_email_template():
    """Ensure the virtual import summary email template exists."""
    template_key = "virtual_import_summary"
    template = EmailTemplate.query.filter_by(purpose_key=template_key).first()

    # Delete old template to force update with new styling
    if template:
        db.session.delete(template)
        db.session.commit()
        template = None

    if not template:
        print(f"[INFO] Creating email template: {template_key}")
        subject = "Virtual Import Report - {{date}} - {{status}}"

        html_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Virtual Import Report</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">{{date}}</p>
    </div>

    <div style="background: #f9f9f9; padding: 25px; border: 1px solid #eee; border-top: none;">
        <div style="display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-bottom: 20px; {{status_style}}">
            {{status}}
        </div>

        <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h2 style="margin: 0 0 15px 0; font-size: 18px; color: #555;">Summary</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                        <span style="color: #888;">Duration</span>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">
                        {{duration}}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                        <span style="color: #888;">Events Processed</span>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold; color: #28a745;">
                        {{success_count}}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">
                        <span style="color: #888;">Warnings</span>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold; color: #ffc107;">
                        {{warning_count}}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0;">
                        <span style="color: #888;">Errors</span>
                    </td>
                    <td style="padding: 10px 0; text-align: right; font-weight: bold; color: #dc3545;">
                        {{error_count}}
                    </td>
                </tr>
            </table>
        </div>

        {{error_details}}
    </div>

    <div style="background: #f0f0f0; padding: 15px; border-radius: 0 0 10px 10px; text-align: center; font-size: 12px; color: #888;">
        Generated by VMS Virtual Import Script
    </div>
</body>
</html>
        """

        text_body = """
Virtual Import Execution Report
===============================
Date: {{date}}
Status: {{status}}
Duration: {{duration}}

Summary
-------
Events Processed: {{success_count}}
Warnings: {{warning_count}}
Errors: {{error_count}}

{{error_details_text}}

Generated by VMS Virtual Import Script
        """

        template = EmailTemplate(
            purpose_key=template_key,
            name="Virtual Import Summary",
            subject_template=subject,
            html_template=html_body,
            text_template=text_body,
            description="Summary report for virtual session import",
            required_placeholders=[
                "date",
                "status",
                "duration",
                "success_count",
                "warning_count",
                "error_count",
                "status_style",
                "error_details",
                "error_details_text",
            ],
            version=2,
            is_active=True,
        )
        db.session.add(template)
        db.session.commit()

    return template


def send_virtual_import_email(success: bool, start_time: datetime, result: dict = None):
    """Send summary email for virtual import."""
    try:
        recipient = os.environ.get("DAILY_IMPORT_RECIPIENT")
        if not recipient:
            recipient = os.environ.get("MAIL_FROM")

        if not recipient:
            # Try to find admin user
            admin = User.query.filter_by(username="admin").first()
            if admin:
                recipient = admin.email

        if not recipient:
            print("[WARNING] No recipient found for summary email. Skipping.")
            return

        template = ensure_email_template()

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        duration_str = f"{duration:.2f} seconds"

        status = "SUCCESS" if success else "FAILED"

        success_count = 0
        warning_count = 0
        error_count = 0
        errors = []

        if result:
            success_count = result.get("success_count", 0)
            warning_count = result.get("warning_count", 0)
            error_count = result.get("error_count", 0)
            errors = result.get("errors", [])[:10]  # First 10 errors

        # Pre-render error details for HTML
        error_details_html = ""
        error_details_text = ""
        if errors:
            error_details_html = """
            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h2 style="margin: 0 0 15px 0; font-size: 18px; color: #dc3545;">Error Details (First 10)</h2>
                <ul style="margin: 0; padding-left: 20px; color: #555;">
            """
            for err in errors:
                error_details_html += f'<li style="margin-bottom: 8px;">{err}</li>'
            error_details_html += "</ul></div>"

            error_details_text = "Error Details:\n" + "-" * 14 + "\n"
            for err in errors:
                error_details_text += f"- {err}\n"

        # Status styling
        if success:
            status_style = "background-color: #d4edda; color: #155724;"
        else:
            status_style = "background-color: #f8d7da; color: #721c24;"

        context = {
            "date": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "status": status,
            "status_style": status_style,
            "duration": duration_str,
            "success_count": success_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "error_details": error_details_html,
            "error_details_text": error_details_text,
        }

        print(f"[INFO] Sending summary email to {recipient}...")

        # Get system user ID
        admin = User.query.filter_by(username="admin").first()
        sender_id = admin.id if admin else 1

        message = create_email_message(
            template=template,
            recipients=[recipient],
            context=context,
            created_by_id=sender_id,
        )

        db.session.commit()
        create_delivery_attempt(message)
        print("[SUCCESS] Summary email sent.")

    except Exception as e:
        print(f"[ERROR] Failed to send summary email: {e}")
        import traceback

        traceback.print_exc()


def run_virtual_import_2025_26():
    """Run the virtual import for 2025-2026 academic year"""

    # Use the existing Flask app (like other scripts)
    with app.app_context():
        print("=== Virtual Import Script for 2025-2026 Academic Year ===")
        start_time = datetime.now(timezone.utc)
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print()

        try:
            # Get the Google Sheet configuration for 2025-2026
            academic_year = "2025-2026"
            sheet_record = GoogleSheet.query.filter_by(
                academic_year=academic_year, purpose="virtual_sessions"
            ).first()

            if not sheet_record:
                print(
                    f"[ERROR] No Google Sheet configured for academic year {academic_year}"
                )
                print("Please configure the Google Sheet in the admin panel first.")
                return False

            sheet_id = sheet_record.decrypted_sheet_id
            if not sheet_id:
                print(
                    f"[ERROR] Google Sheet ID for {academic_year} could not be decrypted or is missing."
                )
                return False

            print(f"[SUCCESS] Found Google Sheet configuration for {academic_year}")
            print(f"   Sheet ID: {sheet_id}")
            print(f"   Sheet Name: {sheet_record.sheet_name}")
            print()

            # Build CSV URL and download data
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            )
            print(f"[INFO] Downloading data from: {csv_url}")

            # Download CSV data
            response = requests.get(csv_url, stream=True)
            response.raise_for_status()

            # Read the CSV in chunks
            chunks = []
            chunk_size = 8192  # 8KB chunks

            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    chunks.append(chunk)

            # Combine chunks and read as CSV
            content = b"".join(chunks)
            df = pd.read_csv(
                pd.io.common.BytesIO(content), skiprows=3, dtype={"School Name": str}
            )

            print(f"[SUCCESS] Downloaded {len(df)} rows of data")
            print()

            # Run the import logic directly
            print("[INFO] Starting import process...")
            print("=" * 50)

            # Call the import logic directly
            result = run_import_logic_direct(df, academic_year)

            if result["success"]:
                print("=" * 50)
                print("[SUCCESS] IMPORT COMPLETED SUCCESSFULLY!")
                print(f"   Events processed: {result.get('success_count', 0)}")
                print(f"   Warnings: {result.get('warning_count', 0)}")
                print(f"   Errors: {result.get('error_count', 0)}")

                errors = result.get("errors", [])
                if errors:
                    print(f"\n[WARNING] Error Details ({len(errors)} total):")
                    for i, error in enumerate(errors[:10], 1):  # Show first 10 errors
                        print(f"   {i}. {error}")
                    if len(errors) > 10:
                        print(f"   ... and {len(errors) - 10} more errors")

                print(
                    f"\n[INFO] Note: Import updates existing events with latest data - no purge needed!"
                )
                print(
                    f"Completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
                send_virtual_import_email(True, start_time, result)
                return True
            else:
                print("=" * 50)
                print("[ERROR] IMPORT FAILED!")
                print(f"Error: {result.get('error', 'Unknown error')}")
                send_virtual_import_email(False, start_time, result)
                return False

        except Exception as e:
            print("=" * 50)
            print(f"[CRITICAL ERROR] {str(e)}")
            import traceback

            traceback.print_exc()
            send_virtual_import_email(False, start_time)
            return False


def run_import_logic_direct(df, academic_year):
    """Run the import logic directly without Flask request context"""
    try:
        print(f"\n=== Starting Import: {len(df)} rows ===")

        # Import required modules
        from datetime import timedelta

        from sqlalchemy import func

        from models.contact import (
            Contact,
            ContactTypeEnum,
            LocalStatusEnum,
            RaceEthnicityEnum,
        )
        from models.district_model import District
        from models.event import (
            Event,
            EventFormat,
            EventStatus,
            EventTeacher,
            EventType,
        )
        from models.history import History
        from models.organization import Organization, VolunteerOrganization
        from models.school_model import School
        from models.teacher import Teacher
        from models.volunteer import EventParticipation, Volunteer
        from routes.reports.common import DISTRICT_MAPPING
        from routes.reports.virtual_session import invalidate_virtual_session_caches

        # Import helper functions from the routes module
        from routes.virtual.routes import (
            add_district_to_event,
            clean_status,
            clean_string_value,
            clean_time_string,
            extract_session_id,
            find_existing_event,
            get_status_priority,
            map_people_of_color,
            parse_datetime,
            process_presenter,
            process_teacher_data,
            process_teacher_for_event,
            safe_str,
            should_update_status,
            split_teacher_names,
            standardize_organization,
            update_legacy_fields,
            validate_csv_row,
        )
        from routes.virtual.utils import (
            generate_school_id,
            get_or_create_district,
            get_or_create_school,
        )

        # First pass: Calculate session datetimes
        session_datetimes = {}
        for index, row in df.iterrows():
            title = clean_string_value(row.get("Session Title"))
            date_str = row.get("Date")
            time_str = row.get("Time")

            if title and not pd.isna(date_str):
                event_datetime = parse_datetime(date_str, time_str)
                if event_datetime:
                    date_key = event_datetime.date().isoformat()
                    datetime_key = event_datetime.isoformat()
                    if title not in session_datetimes:
                        session_datetimes[title] = {}
                    if date_key not in session_datetimes[title]:
                        session_datetimes[title][date_key] = []
                    if datetime_key not in [
                        d["datetime_iso"] for d in session_datetimes[title][date_key]
                    ]:
                        session_datetimes[title][date_key].append(
                            {"datetime": event_datetime, "datetime_iso": datetime_key}
                        )

        success_count = warning_count = error_count = 0
        errors = []
        processed_event_ids = {}
        all_rows_for_lookup = df.to_dict("records")
        primary_logic_already_run = {}

        # Second pass: Process each row
        for row_index, row_data in enumerate(all_rows_for_lookup):
            event_processed_in_this_row = False
            try:
                # Validate CSV row data
                is_valid, row_errors, row_warnings = validate_csv_row(
                    row_data, row_index
                )
                if not is_valid:
                    for error in row_errors:
                        errors.append(error)
                        error_count += 1
                    continue

                # Log warnings
                for warning in row_warnings:
                    print(f"WARNING - {warning}")
                    warning_count += 1

                # Extract key fields
                status_str = safe_str(row_data.get("Status", "")).lower().strip()
                is_simulcast = status_str == "simulcast"
                title = clean_string_value(row_data.get("Session Title"))

                if not title:
                    print(f"ERROR - Row {row_index + 1}: No Session Title")
                    warning_count += 1
                    errors.append(f"Skipped row {row_index + 1}: Missing Session Title")
                    continue

                # Determine event context (datetime) for this row
                current_datetime = None
                date_str = row_data.get("Date")
                time_str = row_data.get("Time")

                # Try parsing date/time from the current row
                if not pd.isna(date_str):
                    parsed_dt = parse_datetime(date_str, time_str)
                    if parsed_dt:
                        current_datetime = parsed_dt
                    else:
                        # Fallback logic for missing time
                        date_parts = str(date_str).strip().split("/")
                        if len(date_parts) >= 2:
                            try:
                                month = int(date_parts[0])
                                day = int(date_parts[1])
                                if len(date_parts) >= 3:
                                    year = int(date_parts[2])
                                else:
                                    current_year = 2024 if month >= 7 else 2025
                                    year = current_year

                                target_date = datetime(year, month, day).date()
                                existing_event = Event.query.filter(
                                    func.lower(Event.title)
                                    == func.lower(title.strip()),
                                    func.date(Event.start_date) == target_date,
                                    Event.type == EventType.VIRTUAL_SESSION,
                                ).first()

                                if existing_event:
                                    current_datetime = existing_event.start_date
                                else:
                                    current_datetime = datetime(year, month, day, 9, 0)
                                    print(
                                        f"INFO - Row {row_index + 1} ('{title}'): No time specified, using default 9:00 AM"
                                    )

                            except (ValueError, IndexError):
                                pass

                # If we can't determine event context, process teacher data only
                if not current_datetime:
                    if row_data.get("Teacher Name") and not pd.isna(
                        row_data.get("Teacher Name")
                    ):
                        print(
                            f"WARNING - Row {row_index + 1} ('{title}'): No valid event datetime found. Processing TEACHER ONLY."
                        )
                        process_teacher_data(row_data, is_simulcast)
                    else:
                        print(
                            f"ERROR - Row {row_index + 1} ('{title}'): Cannot determine event datetime and no teacher name."
                        )
                        warning_count += 1
                        errors.append(
                            f"Skipped row {row_index + 1} ('{title}'): Cannot determine event datetime."
                        )
                    continue

                # Event Handling
                event_key = (title, current_datetime.isoformat())
                event = None
                event_id = processed_event_ids.get(event_key)

                is_primary_row_status = status_str not in ["simulcast"]

                if event_id:
                    event = db.session.get(Event, event_id)

                if not event:
                    # Use flexible matching to prevent duplicates
                    event = find_existing_event(
                        title, current_datetime, processed_event_ids
                    )

                    if event:
                        processed_event_ids[event_key] = event.id
                        print(
                            f"INFO: Found existing event {event.id} for '{title}' at {current_datetime.isoformat()}"
                        )

                        # Update status immediately if this is a primary row with higher priority status
                        if is_primary_row_status:
                            new_status = EventStatus.map_status(status_str)
                            if should_update_status(event.status, new_status):
                                old_status = event.status
                                event.status = new_status
                                event.original_status_string = status_str
                                print(
                                    f"INFO - Row {row_index + 1}: Updated existing event {event.id} status to '{new_status}' (was '{old_status}')"
                                )

                        if not event.session_host or event.session_host != "PREPKC":
                            event.session_host = "PREPKC"
                    else:
                        can_create_event_statuses = [
                            "teacher no-show",
                            "teacher cancelation",
                            "local professional no-show",
                            "pathful professional no-show",
                            "technical difficulties",
                            "count",
                        ]

                        can_create_incomplete_event = (
                            status_str in can_create_event_statuses
                        )

                        if is_primary_row_status or can_create_incomplete_event:
                            event = Event(
                                title=title,
                                start_date=current_datetime,
                                end_date=(
                                    current_datetime.replace(
                                        hour=current_datetime.hour + 1
                                    )
                                    if current_datetime
                                    else None
                                ),
                                duration=60,
                                type=EventType.VIRTUAL_SESSION,
                                format=EventFormat.VIRTUAL,
                                status=EventStatus.map_status(status_str),
                                original_status_string=status_str,
                                session_id=extract_session_id(
                                    row_data.get("Session Link")
                                ),
                                session_host="PREPKC",
                            )
                            db.session.add(event)
                            db.session.flush()
                            processed_event_ids[event_key] = event.id
                        else:
                            print(
                                f"WARNING - Row {row_index + 1} ('{title}'): Secondary status '{status_str}' but no existing event found for datetime {current_datetime.isoformat()}. Processing TEACHER ONLY."
                            )
                            if row_data.get("Teacher Name") and not pd.isna(
                                row_data.get("Teacher Name")
                            ):
                                process_teacher_data(row_data, is_simulcast)
                            continue

                if not event:
                    print(
                        f"ERROR - Row {row_index + 1} ('{title}'): Could not find or create event for datetime {current_datetime.isoformat()}."
                    )
                    warning_count += 1
                    errors.append(
                        f"Skipped row {row_index + 1} ('{title}'): Could not find or create event for {current_datetime.isoformat()}."
                    )
                    continue

                # District Handling
                if row_data.get("District") and not pd.isna(row_data.get("District")):
                    district_name = safe_str(row_data.get("District"))
                    if district_name:
                        existing_district = next(
                            (d for d in event.districts if d.name == district_name),
                            None,
                        )
                        if not existing_district:
                            add_district_to_event(event, district_name)

                # --- Status Update (runs for ALL primary rows, not just first) ---
                # Always update status from primary rows to ensure we capture the highest status
                if is_primary_row_status and event:
                    new_status = EventStatus.map_status(status_str)
                    if should_update_status(event.status, new_status):
                        old_status = event.status
                        event.status = new_status
                        event.original_status_string = status_str
                        print(
                            f"INFO - Row {row_index + 1}: Updated event status to '{new_status}' (was '{old_status}') for '{title}' at {current_datetime.isoformat()}"
                        )
                    elif status_str and status_str != "":
                        # Log when we have a status but it's not higher priority (for debugging)
                        if (
                            event.status == EventStatus.DRAFT
                            and new_status != EventStatus.DRAFT
                        ):
                            print(
                                f"DEBUG - Row {row_index + 1}: Status '{status_str}' -> '{new_status}' not higher than current '{event.status}' for '{title}'"
                            )

                # Primary Logic Block
                primary_logic_run_key = (title, current_datetime.isoformat())
                if is_primary_row_status and not primary_logic_already_run.get(
                    primary_logic_run_key, False
                ):
                    event_processed_in_this_row = True
                    current_date_key = current_datetime.date().isoformat()
                    primary_logic_already_run[primary_logic_run_key] = True

                    # Participant Count Calculation
                    qualifying_teacher_rows_count = 0
                    event.participant_count = 0

                    for lookup_row_index_pc, lookup_row_data_pc in enumerate(
                        all_rows_for_lookup
                    ):
                        lookup_title_pc = clean_string_value(
                            lookup_row_data_pc.get("Session Title")
                        )
                        if lookup_title_pc != title:
                            continue

                        lookup_date_str_pc = lookup_row_data_pc.get("Date")
                        lookup_date_key_pc = None
                        if not pd.isna(lookup_date_str_pc):
                            try:
                                date_str_cleaned_pc = str(lookup_date_str_pc).strip()
                                if "/" in date_str_cleaned_pc:
                                    parts_pc = date_str_cleaned_pc.split("/")
                                    if len(parts_pc) >= 3:
                                        month_str_pc, day_str_pc, year_str_pc = (
                                            parts_pc[0],
                                            parts_pc[1],
                                            parts_pc[2],
                                        )
                                        if (
                                            month_str_pc.isdigit()
                                            and day_str_pc.isdigit()
                                            and year_str_pc.isdigit()
                                        ):
                                            month_pc = int(month_str_pc)
                                            day_pc = int(day_str_pc)
                                            year_pc = int(year_str_pc)
                                    elif len(parts_pc) >= 2:
                                        month_str_pc, day_str_pc = (
                                            parts_pc[0],
                                            parts_pc[1],
                                        )
                                        if (
                                            month_str_pc.isdigit()
                                            and day_str_pc.isdigit()
                                        ):
                                            month_pc = int(month_str_pc)
                                            day_pc = int(day_str_pc)
                                            current_dt_utc_pc = datetime.now(
                                                timezone.utc
                                            )
                                            if current_dt_utc_pc.month >= 7:
                                                year_pc = current_dt_utc_pc.year
                                            else:
                                                year_pc = current_dt_utc_pc.year - 1

                                    if (
                                        "month_pc" in locals()
                                        and "day_pc" in locals()
                                        and "year_pc" in locals()
                                    ):
                                        lookup_date_key_pc = (
                                            datetime(year_pc, month_pc, day_pc)
                                            .date()
                                            .isoformat()
                                        )
                            except (ValueError, IndexError):
                                pass

                        if lookup_date_key_pc == current_date_key:
                            school_name_pc = lookup_row_data_pc.get("School Name")
                            if school_name_pc and not pd.isna(school_name_pc):
                                qualifying_teacher_rows_count += 1

                    event.participant_count = qualifying_teacher_rows_count

                    # Update event fields
                    # Note: Status is already updated above for all primary rows
                    # Here we just ensure original_status_string is set if not already
                    if not event.original_status_string and status_str:
                        event.original_status_string = status_str
                    event.description = row_data.get("Description")
                    event.additional_information = row_data.get("Session Type")
                    event.registration_link = row_data.get("Session Link")

                    if current_datetime and current_datetime != event.start_date:
                        event.start_date = current_datetime
                        event.end_date = current_datetime + timedelta(hours=1)

                    if not event.session_host:
                        event.session_host = "PREPKC"

                    # School Handling
                    primary_school_name = row_data.get("School Name")
                    if primary_school_name and not pd.isna(primary_school_name):
                        school_district = None
                        if event.district_partner:
                            school_district = get_or_create_district(
                                event.district_partner
                            )

                        school = get_or_create_school(
                            primary_school_name, school_district
                        )
                        if school:
                            event.school = school.id

                    # Update Metrics
                    if event.status == EventStatus.COMPLETED:
                        event.registered_count = event.registered_count or 0
                        event.attended_count = event.attended_count or 0
                        event.volunteers_needed = event.volunteers_needed or 1
                        if not event.duration:
                            event.duration = 60

                # Teacher Processing
                if row_data.get("Teacher Name") and not pd.isna(
                    row_data.get("Teacher Name")
                ):
                    process_teacher_for_event(row_data, event, is_simulcast)

                # Presenter Processing
                presenter_name = row_data.get("Presenter")
                if presenter_name and not pd.isna(presenter_name):
                    process_presenter(row_data, event, is_simulcast)

                # Commit changes
                db.session.commit()
                if event_processed_in_this_row:
                    success_count += 1

            except Exception as e:
                db.session.rollback()
                error_count += 1
                title_for_error = clean_string_value(
                    row_data.get("Session Title", "Unknown")
                )
                dt_str = (
                    current_datetime.isoformat()
                    if "current_datetime" in locals() and current_datetime
                    else "Unknown Time"
                )
                error_msg = f"ERROR - Row {row_index + 1} for '{title_for_error}' at {dt_str}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                current_datetime = None

        # Summary of results
        print(f"\n=== Import Complete ===")
        print(f"Success: {success_count} events processed (new + updated)")
        print(f"Warnings: {warning_count}")
        print(f"Errors: {error_count}")
        if errors:
            print(f"Error details: {len(errors)} total issues")
        print(
            "Note: Import updates existing events with latest data - no purge needed!"
        )
        print("========================")

        # Invalidate virtual session caches
        try:
            invalidate_virtual_session_caches()
            print("Virtual session caches invalidated - reports will show fresh data")
        except Exception as e:
            print(f"Warning: Could not invalidate caches: {str(e)}")

        return {
            "success": True,
            "success_count": success_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "errors": errors,
        }

    except Exception as e:
        db.session.rollback()
        error_msg = f"Overall import failed: {str(e)}"
        print(f"CRITICAL ERROR: {error_msg}")
        return {"success": False, "error": error_msg}


if __name__ == "__main__":
    success = run_virtual_import_2025_26()
    sys.exit(0 if success else 1)

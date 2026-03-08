#!/usr/bin/env python3
"""
Test Email Templates Script
============================

Sends example import report emails for preview/testing purposes.
This allows you to see the email styling without running actual imports.

Templates are auto-synced from email_templates/*.yaml on app startup.
This script simply loads them from the database and sends test emails.

Usage:
    python scripts/daily_imports/test_email_templates.py

Requirements:
    - Mailjet API keys configured (MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE)
    - DAILY_IMPORT_RECIPIENT or MAIL_FROM set in environment
    - EMAIL_DELIVERY_ENABLED=true
"""

import os
import sys
from datetime import datetime, timezone

# Ensure repository root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app import app
from models import db
from models.email import EmailTemplate
from models.user import User
from utils.email import create_delivery_attempt, create_email_message


def get_recipient():
    """Get the recipient email address."""
    recipient = os.environ.get("DAILY_IMPORT_RECIPIENT")
    if not recipient:
        recipient = os.environ.get("MAIL_FROM")
    return recipient


def _get_template(purpose_key: str) -> EmailTemplate:
    """Load an active template from the database by purpose_key.

    Templates are auto-synced from email_templates/*.yaml on app startup.
    """
    template = EmailTemplate.query.filter_by(
        purpose_key=purpose_key, is_active=True
    ).first()
    if not template:
        print(f"[ERROR] Template '{purpose_key}' not found in database.")
        print("Templates are auto-synced from email_templates/*.yaml on app startup.")
        print("Make sure the app has been started at least once.")
        sys.exit(1)
    return template


def send_test_virtual_import_email(recipient: str):
    """Send a test virtual import email with sample data."""
    print("\n=== Sending Test Virtual Import Email ===")

    template = _get_template("virtual_import_summary")

    # Sample data
    start_time = datetime.now(timezone.utc)
    status = "SUCCESS"
    status_style = "background-color: #d4edda; color: #155724;"

    # Sample errors for demonstration
    sample_errors = [
        "Row 45: Missing teacher email for 'Johnson Elementary'",
        "Row 78: Invalid date format '2026-13-45'",
        "Row 123: Duplicate event ID 'EVT-2025-001'",
    ]

    # Pre-render error details
    error_details_html = """
    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <h2 style="margin: 0 0 15px 0; font-size: 18px; color: #dc3545;">Error Details (First 10)</h2>
        <ul style="margin: 0; padding-left: 20px; color: #555;">
    """
    for err in sample_errors:
        error_details_html += f'<li style="margin-bottom: 8px;">{err}</li>'
    error_details_html += "</ul></div>"

    error_details_text = "Error Details:\n--------------\n"
    for err in sample_errors:
        error_details_text += f"- {err}\n"

    context = {
        "date": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": status,
        "status_style": status_style,
        "duration": "185.42 seconds",
        "success_count": 261,
        "warning_count": 45,
        "error_count": len(sample_errors),
        "error_details": error_details_html,
        "error_details_text": error_details_text,
    }

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
    print(f"[SUCCESS] Virtual Import test email sent to {recipient}")


def send_test_daily_import_email(recipient: str):
    """Send a test daily import email with sample data."""
    print("\n=== Sending Test Daily Import Email ===")

    template = _get_template("daily_import_summary")

    # Sample data
    start_time = datetime.now(timezone.utc)
    status = "SUCCESS"
    status_style = "background-color: #d4edda; color: #155724;"

    # Sample steps data
    sample_steps = [
        ("organizations", "Success", 127, "4.52s"),
        ("volunteers", "Success", 892, "58.21s"),
        ("affiliations", "Success", 1523, "520.15s"),
        ("events", "Success", 45, "21.88s"),
        ("history", "Success", 160, "62.45s"),
    ]

    # Build HTML rows
    steps_rows = ""
    steps_text_list = ""
    for name, status_text, records, duration in sample_steps:
        if status_text == "Success":
            status_color = "#28a745"
        elif status_text == "FAILED":
            status_color = "#dc3545"
        else:
            status_color = "#6c757d"

        steps_rows += f"""
        <tr>
            <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">{name}</td>
            <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: center; color: {status_color}; font-weight: bold;">{status_text}</td>
            <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: right;">{records}</td>
            <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: right;">{duration}</td>
        </tr>
        """
        steps_text_list += f"- {name}: {status_text} ({duration}) - {records} records\n"

    context = {
        "date": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": status,
        "status_style": status_style,
        "duration": "667.21 seconds",
        "steps_rows": steps_rows,
        "steps_text_list": steps_text_list,
    }

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
    print(f"[SUCCESS] Daily Import test email sent to {recipient}")


def send_test_teacher_reminder_email(recipient: str):
    """Send a test teacher session reminder email with sample data."""
    print("\n=== Sending Test Teacher Session Reminder Email ===")

    template = _get_template("teacher_session_reminder")

    # Sample session list HTML (mimics what email_reminders.py will produce)
    session_list_html = """
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
        <thead>
            <tr style="background-color: #003366;">
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Date</th>
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Time</th>
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Title</th>
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Career Cluster</th>
                <th style="padding: 10px 8px; text-align: center; color: white; border-bottom: 2px solid #c8a415;">Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Mar 15, 2026</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">10:00 AM</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Healthcare Careers Exploration</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Health Sciences</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: center;">
                    <span style="background: #d4edda; color: #155724; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">Confirmed</span>
                </td>
            </tr>
            <tr>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Mar 22, 2026</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">1:30 PM</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Engineering &amp; Technology Panel</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">STEM</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: center;">
                    <span style="background: #fff3cd; color: #856404; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">Requested</span>
                </td>
            </tr>
            <tr>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Apr 5, 2026</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">9:00 AM</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Business &amp; Finance Industry Chat</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">Business Management</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: center;">
                    <span style="background: #d4edda; color: #155724; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">Confirmed</span>
                </td>
            </tr>
        </tbody>
    </table>
    """

    session_list_text = (
        "- Mar 15, 2026 10:00 AM | Healthcare Careers Exploration | "
        "Health Sciences | Confirmed\n"
        "- Mar 22, 2026  1:30 PM | Engineering & Technology Panel | "
        "STEM | Requested\n"
        "- Apr 5, 2026   9:00 AM | Business & Finance Industry Chat | "
        "Business Management | Confirmed\n"
    )

    context = {
        "teacher_name": "Tahra Arnold",
        "building_name": "Banneker Elementary",
        "district_name": "Kansas City Kansas Public Schools",
        "session_list": session_list_html,
        "session_list_text": session_list_text,
        "login_url": "http://localhost:5050/login",
        "contact_email": "support@example.com",
    }

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
    print(f"[SUCCESS] Teacher Session Reminder test email sent to {recipient}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Test Email Templates Script")
    print("=" * 60)

    with app.app_context():
        recipient = get_recipient()

        if not recipient:
            print("[ERROR] No recipient configured!")
            print("Set DAILY_IMPORT_RECIPIENT or MAIL_FROM in your .env file.")
            return 1

        print(f"\nRecipient: {recipient}")
        print(
            f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        try:
            # Send all test emails
            send_test_virtual_import_email(recipient)
            send_test_daily_import_email(recipient)
            send_test_teacher_reminder_email(recipient)

            print("\n" + "=" * 60)
            print("[SUCCESS] All test emails sent!")
            print("Check your inbox to preview the email styles.")
            print("=" * 60)
            return 0

        except Exception as e:
            print(f"\n[ERROR] Failed to send test emails: {e}")
            import traceback

            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())

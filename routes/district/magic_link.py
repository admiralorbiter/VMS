"""
Magic Link Routes Module
========================

This module provides routes for teacher magic link authentication in the
District Data Tracker. Teachers can request a magic link via email
to securely access their progress data without creating an account.

Key Features:
- Email-based magic link request (FR-DISTRICT-505)
- Secure token validation (FR-DISTRICT-523)
- Single-teacher data scope (FR-DISTRICT-506)
- Data correction flag submission (FR-DISTRICT-507)

Main Endpoints:
- GET  /district/<slug>/teacher/request-link: Show request form
- POST /district/<slug>/teacher/request-link: Process request, send email
- GET  /district/<slug>/teacher/verify/<token>: Validate token, show dashboard
- POST /district/<slug>/teacher/flag-issue: Submit data correction flag

Security Considerations:
- Generic responses prevent email enumeration (TC-021)
- Tokens are cryptographically secure (TC-024)
- Each token is scoped to single teacher identity (TC-003)
"""

import os
from datetime import datetime, timezone

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func

from models import db
from models.bug_report import BugReport, BugReportType
from models.magic_link import MagicLink
from models.teacher_progress import TeacherProgress
from routes.district import district_bp
from routes.district.portal import RESERVED_SLUGS, get_district_portal


def get_teacher_progress_sessions(teacher_progress):
    """
    Get session data for a teacher based on their TeacherProgress record.

    This queries the actual Event/EventTeacher relationships if the
    teacher_progress is linked to a Teacher record.

    Args:
        teacher_progress: TeacherProgress instance

    Returns:
        Tuple of (past_sessions, upcoming_sessions, completed_count, planned_count)
    """
    from models.event import Event, EventStatus, EventTeacher, EventType

    past_sessions = []
    upcoming_sessions = []

    if not teacher_progress.teacher_id:
        # No linked Teacher record - return empty lists
        return [], [], 0, 0

    now = datetime.now(timezone.utc)

    # Query all virtual sessions for this teacher
    teacher_registrations = (
        EventTeacher.query.filter_by(teacher_id=teacher_progress.teacher_id)
        .join(Event)
        .filter(Event.type == EventType.VIRTUAL_SESSION)
        .options(db.joinedload(EventTeacher.event))
        .order_by(Event.start_date.desc())
        .all()
    )

    for reg in teacher_registrations:
        event = reg.event
        if not event:
            continue

        # Ensure start_date is timezone-aware for comparison
        start_date = event.start_date
        if start_date:
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

        session_data = {
            "id": event.id,
            "title": event.title or "Virtual Session",
            "date": start_date.date() if start_date else None,
            "time": start_date.time() if start_date else None,
            "datetime": start_date,
            "status": event.status.value if event.status else "unknown",
            "topic_theme": event.series or "",
        }

        if start_date and start_date < now:
            past_sessions.append(session_data)
        elif start_date and start_date >= now:
            if event.status in [
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.REQUESTED,
            ]:
                upcoming_sessions.append(session_data)

    # Sort sessions
    past_sessions.sort(key=lambda x: x["datetime"] or datetime.min, reverse=True)
    upcoming_sessions.sort(key=lambda x: x["datetime"] or datetime.max)

    return past_sessions, upcoming_sessions, len(past_sessions), len(upcoming_sessions)


@district_bp.route("/<slug>/teacher/request-link", methods=["GET"])
def magic_link_request_form(slug: str):
    """
    Display the magic link request form.

    Args:
        slug: District slug from URL

    Returns:
        Rendered request form template
    """
    if slug.lower() in RESERVED_SLUGS:
        return redirect(url_for("virtual.virtual_usage"))

    try:
        portal_config = get_district_portal(slug)
    except KeyError:
        flash("District not found.", "error")
        return redirect(url_for("main.index"))

    return render_template(
        "district/magic_link/request_link.html",
        district=portal_config,
        district_slug=slug,
    )


@district_bp.route("/<slug>/teacher/request-link", methods=["POST"])
def magic_link_request_submit(slug: str):
    """
    Process magic link request and send email.

    Security: Always shows generic success message (TC-021 compliance)
    to prevent email enumeration attacks.

    Args:
        slug: District slug from URL

    Returns:
        Redirect to confirmation page
    """
    if slug.lower() in RESERVED_SLUGS:
        return redirect(url_for("virtual.virtual_usage"))

    try:
        portal_config = get_district_portal(slug)
    except KeyError:
        flash("District not found.", "error")
        return redirect(url_for("main.index"))

    email = request.form.get("email", "").lower().strip()

    if not email:
        flash("Please enter your email address.", "error")
        return redirect(url_for("district.magic_link_request_form", slug=slug))

    # Always redirect to confirmation regardless of whether email exists
    # This prevents email enumeration (TC-021)

    # Check if email exists in TeacherProgress roster
    teacher_progress = TeacherProgress.query.filter(
        func.lower(TeacherProgress.email) == email,
        TeacherProgress.is_active == True,
    ).first()

    if teacher_progress:
        try:
            # Deactivate any existing links for this email
            MagicLink.deactivate_for_email(email, slug)

            # Create new magic link
            magic_link = MagicLink.create_for_teacher(
                teacher_progress_id=teacher_progress.id,
                email=email,
                district_slug=slug,
            )
            db.session.commit()

            # Send email
            _send_magic_link_email(
                email=email,
                teacher_name=teacher_progress.name,
                magic_link=magic_link,
                district_name=portal_config.get("display_name", slug.upper()),
            )

            current_app.logger.info(
                f"Magic link created for {email} in district {slug}"
            )
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating magic link: {e}", exc_info=True)
    else:
        # Log that email was not found (but don't reveal to user)
        current_app.logger.info(
            f"Magic link requested for unknown email {email} in {slug}"
        )

    return redirect(url_for("district.magic_link_sent", slug=slug))


@district_bp.route("/<slug>/teacher/link-sent")
def magic_link_sent(slug: str):
    """
    Display confirmation page after magic link request.

    Shows generic message regardless of whether email was found.

    Args:
        slug: District slug from URL

    Returns:
        Rendered confirmation template
    """
    if slug.lower() in RESERVED_SLUGS:
        return redirect(url_for("virtual.virtual_usage"))

    try:
        portal_config = get_district_portal(slug)
    except KeyError:
        portal_config = {"display_name": slug.upper()}

    return render_template(
        "district/magic_link/link_sent.html",
        district=portal_config,
        district_slug=slug,
    )


@district_bp.route("/<slug>/teacher/verify/<token>")
def magic_link_verify(slug: str, token: str):
    """
    Validate magic link token and display teacher dashboard.

    Security: Token is validated, expired tokens rejected (TC-024 compliance).
    Only shows data for the specific teacher (TC-022, FR-DISTRICT-506).

    Args:
        slug: District slug from URL
        token: Magic link token

    Returns:
        Rendered teacher dashboard or redirect to request form
    """
    if slug.lower() in RESERVED_SLUGS:
        return redirect(url_for("virtual.virtual_usage"))

    try:
        portal_config = get_district_portal(slug)
    except KeyError:
        flash("District not found.", "error")
        return redirect(url_for("main.index"))

    # Validate token
    magic_link = MagicLink.validate_token(token)

    if not magic_link:
        flash(
            "This link has expired or is invalid. Please request a new one.",
            "error",
        )
        return redirect(url_for("district.magic_link_request_form", slug=slug))

    # Verify district matches
    if magic_link.district_slug and magic_link.district_slug != slug:
        flash("Invalid link for this district.", "error")
        return redirect(url_for("district.magic_link_request_form", slug=slug))

    # Get teacher progress data
    teacher_progress = magic_link.teacher_progress
    if not teacher_progress:
        flash("Teacher record not found.", "error")
        return redirect(url_for("district.magic_link_request_form", slug=slug))

    # Get session data
    past_sessions, upcoming_sessions, completed_count, planned_count = (
        get_teacher_progress_sessions(teacher_progress)
    )

    # Calculate progress status
    progress_status = teacher_progress.get_progress_status(
        completed_sessions=completed_count,
        planned_sessions=planned_count,
    )

    return render_template(
        "district/magic_link/teacher_view.html",
        district=portal_config,
        district_slug=slug,
        teacher=teacher_progress,
        past_sessions=past_sessions,
        upcoming_sessions=upcoming_sessions,
        progress_status=progress_status,
        magic_link_token=token,
    )


@district_bp.route("/<slug>/teacher/flag-issue", methods=["POST"])
def magic_link_flag_issue(slug: str):
    """
    Handle data correction flag submission from magic link session.

    Requires valid magic link token for authentication.
    Creates BugReport for staff follow-up (FR-DISTRICT-507, TC-023).

    Args:
        slug: District slug from URL

    Returns:
        JSON response with success status
    """
    try:
        data = request.get_json() or request.form
        token = data.get("token")
        issue_type = data.get("issue_type")
        issue_category = data.get("issue_category")
        description = data.get("description", "")

        # Validate token
        magic_link = MagicLink.validate_token(token)
        if not magic_link:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Session expired. Please request a new link.",
                    }
                ),
                401,
            )

        # Validate required fields
        if not issue_type or not issue_category:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Please select an issue type and category.",
                    }
                ),
                400,
            )

        teacher_progress = magic_link.teacher_progress
        if not teacher_progress:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Teacher record not found.",
                    }
                ),
                404,
            )

        # Log the issue
        current_app.logger.info(
            f"Data flag submitted by teacher {teacher_progress.email}: "
            f"Type={issue_type}, Category={issue_category}, Desc={description}"
        )

        # Create BugReport
        try:
            bug_report = BugReport(
                type=(
                    BugReportType.DATA_ERROR
                    if issue_category == "incorrect"
                    else BugReportType.OTHER
                ),
                description=(
                    f"📧 Submitted via Teacher Magic Link\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"District: {slug.upper()}\n"
                    f"Teacher: {teacher_progress.name}\n"
                    f"Email: {teacher_progress.email}\n"
                    f"Building: {teacher_progress.building}\n"
                    f"Issue Type: {issue_type}\n"
                    f"Category: {issue_category}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Description:\n{description}"
                ),
                page_url=f"/district/{slug}/teacher/verify/{token[:20]}...",
                page_title="Teacher Progress Dashboard (Magic Link)",
                submitted_by_id=None,  # No authenticated user
            )
            db.session.add(bug_report)
            db.session.commit()

            current_app.logger.info(
                f"BugReport {bug_report.id} created for teacher data flag"
            )
        except Exception as e:
            current_app.logger.warning(f"Could not create bug report: {e}")
            db.session.rollback()

        return jsonify(
            {
                "success": True,
                "message": (
                    "Thank you! Your feedback has been submitted. "
                    "Our team will review it shortly."
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting flag: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred. Please try again.",
                }
            ),
            500,
        )


def _send_magic_link_email(
    email: str,
    teacher_name: str,
    magic_link: MagicLink,
    district_name: str,
):
    """
    Send magic link email to teacher.

    Uses Mailjet if configured, otherwise logs to console.

    Args:
        email: Teacher email address
        teacher_name: Teacher's name
        magic_link: MagicLink instance
        district_name: Display name of district
    """
    from flask import current_app

    # Generate the full URL
    base_url = current_app.config.get("BASE_URL", request.host_url.rstrip("/"))
    link_url = magic_link.get_url(base_url)

    current_app.logger.info(f"Magic link URL for {email}: {link_url}")

    # Try to send via Mailjet
    try:
        from utils.email import (
            check_recipient_allowlist,
            get_email_allowlist,
            get_mailjet_client,
            is_email_delivery_enabled,
        )

        mailjet = get_mailjet_client()

        if not mailjet:
            current_app.logger.warning(
                "Mailjet not configured. Magic link logged to console only."
            )
            return

        if not is_email_delivery_enabled():
            current_app.logger.warning(
                "Email delivery disabled. Magic link logged to console only."
            )
            return

        # Check allowlist in non-production
        allowlist = get_email_allowlist()
        if allowlist:
            is_allowed, reason = check_recipient_allowlist(email, allowlist)
            if not is_allowed:
                current_app.logger.warning(
                    f"Email blocked by allowlist: {email}. Reason: {reason}"
                )
                return

        # Send email via Mailjet
        data = {
            "Messages": [
                {
                    "From": {
                        "Email": os.environ.get("MAIL_FROM", "noreply@prepkc.org"),
                        "Name": "PrepKC Virtual Sessions",
                    },
                    "To": [{"Email": email, "Name": teacher_name}],
                    "Subject": f"Access Your Virtual Session Progress - {district_name}",
                    "HTMLPart": f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 30px; text-align: center;">
                            <h1 style="color: white; margin: 0;">Virtual Session Progress</h1>
                        </div>
                        <div style="padding: 30px; background: #f8f9fa;">
                            <h2 style="color: #1e3a5f;">Hello {teacher_name},</h2>
                            <p style="font-size: 16px; color: #333;">
                                Click the button below to view your virtual session progress for {district_name}.
                            </p>
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{link_url}"
                                   style="background: #2d5a87; color: white; padding: 15px 30px;
                                          text-decoration: none; border-radius: 5px; font-size: 18px;
                                          display: inline-block;">
                                    View My Progress
                                </a>
                            </div>
                            <p style="font-size: 14px; color: #666;">
                                This link will expire in {magic_link.hours_until_expiry} hours.
                            </p>
                            <p style="font-size: 14px; color: #666;">
                                If you didn't request this link, you can safely ignore this email.
                            </p>
                        </div>
                        <div style="background: #1e3a5f; padding: 20px; text-align: center;">
                            <p style="color: #ccc; font-size: 12px; margin: 0;">
                                PrepKC - Preparing Kansas City Youth for Success
                            </p>
                        </div>
                    </div>
                    """,
                    "TextPart": f"""
Hello {teacher_name},

Click the link below to view your virtual session progress for {district_name}:

{link_url}

This link will expire in {magic_link.hours_until_expiry} hours.

If you didn't request this link, you can safely ignore this email.

---
PrepKC - Preparing Kansas City Youth for Success
                    """,
                }
            ]
        }

        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            current_app.logger.info(f"Magic link email sent to {email}")
        else:
            current_app.logger.error(
                f"Mailjet error: {result.status_code} - {result.json()}"
            )

    except Exception as e:
        current_app.logger.error(f"Error sending magic link email: {e}", exc_info=True)

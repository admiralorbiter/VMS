"""
District Public Signup Routes

Public-facing routes for volunteer event signup without authentication.
Enables volunteers to sign up for district events via a simple form.

FR-SELFSERV-404: Public signup forms that create volunteer records
FR-SELFSERV-405: Confirmation emails with calendar invites
"""

from datetime import datetime, timezone

from flask import abort, current_app, flash, redirect, render_template, request, url_for

from models import db
from models.district_participation import DistrictParticipation
from models.district_volunteer import DistrictVolunteer
from models.event import Event, EventStatus
from models.tenant import Tenant
from models.volunteer import Volunteer
from routes.district import district_bp
from utils.calendar_utils import generate_event_ics_from_model


def resolve_tenant_by_slug(slug: str) -> Tenant:
    """Resolve tenant from URL slug."""
    tenant = Tenant.query.filter_by(slug=slug, is_active=True).first()
    if not tenant:
        abort(404)
    return tenant


@district_bp.route("/<slug>/event/<int:event_id>/signup", methods=["GET"])
def public_signup_form(slug, event_id):
    """
    Display public signup form for a district event.

    FR-SELFSERV-404: Public signup form for district events.
    """
    tenant = resolve_tenant_by_slug(slug)

    # Get event and verify it's published and accepting signups
    event = Event.query.filter_by(id=event_id, tenant_id=tenant.id).first_or_404()

    if event.status not in [EventStatus.PUBLISHED, EventStatus.CONFIRMED]:
        flash("This event is not currently accepting signups.", "warning")
        return redirect(url_for("index"))

    # Check if event is in the past (handle both naive and aware datetimes)
    if event.start_date:
        now = datetime.now(timezone.utc)
        event_date = event.start_date
        # If event date is naive, assume it's in UTC for comparison
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        if event_date < now:
            flash("This event has already occurred.", "warning")
            return redirect(url_for("index"))

    # Check if event is full
    confirmed_count = DistrictParticipation.query.filter_by(
        event_id=event_id,
        tenant_id=tenant.id,
        status="confirmed",
    ).count()

    spots_remaining = None
    is_full = False
    if event.volunteers_needed and event.volunteers_needed > 0:
        spots_remaining = max(0, event.volunteers_needed - confirmed_count)
        is_full = spots_remaining == 0

    return render_template(
        "district/signup/form.html",
        event=event,
        tenant=tenant,
        spots_remaining=spots_remaining,
        is_full=is_full,
        page_title=f"Sign Up: {event.title}",
    )


@district_bp.route("/<slug>/event/<int:event_id>/signup", methods=["POST"])
def public_signup_submit(slug, event_id):
    """
    Process public signup form submission.

    FR-SELFSERV-404: Create volunteer record and participation.
    FR-SELFSERV-405: Send confirmation email with calendar invite.
    """
    tenant = resolve_tenant_by_slug(slug)

    # Verify event is valid for signup
    event = Event.query.filter_by(id=event_id, tenant_id=tenant.id).first_or_404()

    if event.status not in [EventStatus.PUBLISHED, EventStatus.CONFIRMED]:
        flash("This event is not currently accepting signups.", "error")
        return redirect(
            url_for("district.public_signup_form", slug=slug, event_id=event_id)
        )

    # Check if event is in the past (handle both naive and aware datetimes)
    if event.start_date:
        now = datetime.now(timezone.utc)
        event_date = event.start_date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        if event_date < now:
            flash("This event has already occurred.", "error")
            return redirect(
                url_for("district.public_signup_form", slug=slug, event_id=event_id)
            )

    # Get form data
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip() or None
    organization = request.form.get("organization", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    # Validate required fields
    if not all([first_name, last_name, email]):
        flash("Please fill in all required fields.", "error")
        return redirect(
            url_for("district.public_signup_form", slug=slug, event_id=event_id)
        )

    # Basic email validation
    if "@" not in email or "." not in email:
        flash("Please enter a valid email address.", "error")
        return redirect(
            url_for("district.public_signup_form", slug=slug, event_id=event_id)
        )

    try:
        from models.contact import Contact, Email

        # Check if volunteer already exists (by email)
        email_record = (
            Email.query.join(Contact, Email.contact_id == Contact.id)
            .join(Volunteer, Volunteer.id == Contact.id)
            .filter(db.func.lower(Email.email) == email.lower())
            .first()
        )

        volunteer = None
        if email_record:
            volunteer = Volunteer.query.get(email_record.contact_id)

        if volunteer:
            # Update volunteer info if needed
            if not volunteer.first_name:
                volunteer.first_name = first_name
            if not volunteer.last_name:
                volunteer.last_name = last_name
        else:
            # Create new volunteer
            volunteer = Volunteer(
                first_name=first_name,
                last_name=last_name,
            )
            db.session.add(volunteer)
            db.session.flush()  # Get volunteer ID

            # Add email using Email model directly
            new_email = Email(
                contact_id=volunteer.id,
                email=email,
                primary=True,
            )
            db.session.add(new_email)

        # Ensure volunteer is linked to this tenant's pool
        district_vol = DistrictVolunteer.query.filter_by(
            volunteer_id=volunteer.id,
            tenant_id=tenant.id,
        ).first()

        if not district_vol:
            district_vol = DistrictVolunteer(
                volunteer_id=volunteer.id,
                tenant_id=tenant.id,
                status="active",
            )
            db.session.add(district_vol)

        # Check if already signed up for this event
        existing_participation = DistrictParticipation.query.filter_by(
            volunteer_id=volunteer.id,
            event_id=event_id,
            tenant_id=tenant.id,
        ).first()

        if existing_participation:
            flash("You're already signed up for this event!", "info")
            return redirect(
                url_for("district.public_signup_success", slug=slug, event_id=event_id)
            )

        # Create participation record
        participation = DistrictParticipation(
            volunteer_id=volunteer.id,
            event_id=event_id,
            tenant_id=tenant.id,
            status="confirmed",
            participation_type="volunteer",
            confirmed_at=datetime.now(timezone.utc),
            notes=notes,
        )
        db.session.add(participation)
        db.session.commit()

        # Send confirmation email with calendar invite
        _send_signup_confirmation_email(volunteer, event, tenant)

        current_app.logger.info(
            f"Public signup: {email} signed up for event {event_id} (tenant: {tenant.slug})"
        )

        return redirect(
            url_for("district.public_signup_success", slug=slug, event_id=event_id)
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing signup: {e}")
        flash("An error occurred. Please try again.", "error")
        return redirect(
            url_for("district.public_signup_form", slug=slug, event_id=event_id)
        )


@district_bp.route("/<slug>/event/<int:event_id>/signup/success")
def public_signup_success(slug, event_id):
    """
    Display signup success/confirmation page.
    """
    tenant = resolve_tenant_by_slug(slug)
    event = Event.query.filter_by(id=event_id, tenant_id=tenant.id).first_or_404()

    return render_template(
        "district/signup/success.html",
        event=event,
        tenant=tenant,
        page_title="Signup Confirmed!",
    )


def _send_signup_confirmation_email(volunteer: Volunteer, event: Event, tenant: Tenant):
    """
    Send signup confirmation email with calendar invite attachment.

    FR-SELFSERV-405: Confirmation emails with calendar invites.
    """
    try:
        from utils.email import get_mailjet_client, is_email_delivery_enabled

        # Check if email delivery is enabled
        if not is_email_delivery_enabled():
            current_app.logger.info(
                f"Email delivery disabled - skipping confirmation to {volunteer.primary_email}"
            )
            return

        client = get_mailjet_client()
        if not client:
            current_app.logger.warning("Mailjet client not configured")
            return

        # Generate calendar invite
        ics_content = generate_event_ics_from_model(event)

        # Format event date
        event_date_str = (
            event.start_date.strftime("%B %d, %Y at %I:%M %p")
            if event.start_date
            else "TBD"
        )

        # Build email
        data = {
            "Messages": [
                {
                    "From": {
                        "Email": "events@prepkc.org",
                        "Name": tenant.name or "PrepKC",
                    },
                    "To": [
                        {
                            "Email": volunteer.primary_email,
                            "Name": f"{volunteer.first_name} {volunteer.last_name}",
                        }
                    ],
                    "Subject": f"You're signed up for {event.title}!",
                    "TextPart": f"""
Hi {volunteer.first_name},

Thank you for signing up for {event.title}!

Event Details:
- Date: {event_date_str}
- Location: {event.location or 'TBD'}

{event.description or ''}

We look forward to seeing you there!

Best regards,
{tenant.name or 'PrepKC'}
""",
                    "HTMLPart": f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">You're signed up! ✓</h2>
        <p>Hi {volunteer.first_name},</p>
        <p>Thank you for signing up for <strong>{event.title}</strong>!</p>

        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #495057;">Event Details</h3>
            <p><strong>📅 Date:</strong> {event_date_str}</p>
            <p><strong>📍 Location:</strong> {event.location or 'TBD'}</p>
            {f'<p>{event.description}</p>' if event.description else ''}
        </div>

        <p>A calendar invite is attached to this email for your convenience.</p>

        <p>We look forward to seeing you there!</p>

        <p>Best regards,<br>{tenant.name or 'PrepKC'}</p>
    </div>
</body>
</html>
""",
                    "Attachments": [
                        {
                            "ContentType": "text/calendar",
                            "Filename": f"{event.title.replace(' ', '_')}.ics",
                            "Base64Content": __import__("base64")
                            .b64encode(ics_content.encode())
                            .decode(),
                        }
                    ],
                }
            ]
        }

        result = client.send.create(data=data)
        if result.status_code == 200:
            current_app.logger.info(
                f"Confirmation email sent to {volunteer.primary_email} for event {event.id}"
            )
        else:
            current_app.logger.error(
                f"Failed to send confirmation email: {result.status_code} - {result.json()}"
            )

    except Exception as e:
        current_app.logger.error(f"Error sending confirmation email: {e}")
        # Don't fail the signup if email fails

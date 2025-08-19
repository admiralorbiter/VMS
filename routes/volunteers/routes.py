"""
Volunteer Management System - Routes

This module contains all the Flask routes for the volunteer management system.
It handles volunteer listing, creation, editing, viewing, and data import operations.

Key Features:
- Volunteer listing with filtering and pagination
- Individual volunteer view with detailed information
- Volunteer creation and editing forms
- Salesforce data import functionality
- Local status calculation and updates
- Volunteer deletion and purging operations

Routes:
- /volunteers: Main volunteer listing page
- /volunteers/add: Add new volunteer form
- /volunteers/view/<id>: View individual volunteer details
- /volunteers/edit/<id>: Edit volunteer information
- /volunteers/import-from-salesforce: Import volunteer data from Salesforce
- /volunteers/update-local-statuses: Bulk update local status calculations

Author: VMS Development Team
Last Updated: 2024
"""

import csv
import io
import json
import os
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import and_, or_

from config import Config
from forms import VolunteerForm
from models import db
from models.contact import (
    Address,
    AgeGroupEnum,
    Contact,
    ContactTypeEnum,
    EducationEnum,
    Email,
    GenderEnum,
    LocalStatusEnum,
    Phone,
    RaceEthnicityEnum,
)
from models.event import Event
from models.history import History
from models.organization import Organization, VolunteerOrganization
from models.volunteer import (
    ConnectorData,
    ConnectorSubscriptionEnum,
    Engagement,
    EventParticipation,
    Skill,
    Volunteer,
    VolunteerSkill,
)
from routes.utils import (
    admin_required,
    get_email_addresses,
    get_phone_numbers,
    log_audit_action,
    parse_date,
    parse_skills,
)

# Create Flask Blueprint for volunteer routes
volunteers_bp = Blueprint("volunteers", __name__)


def process_volunteer_row(row, success_count, error_count, errors):
    """
    Process a single volunteer row from CSV data.

    This function handles the conversion of CSV data to Volunteer model instances,
    including proper data validation and relationship management.

    Args:
        row (dict): Dictionary containing volunteer data from CSV
        success_count (int): Current count of successful processing operations
        error_count (int): Current count of processing errors
        errors (list): List to collect error messages

    Returns:
        tuple: Updated (success_count, error_count)

    Note:
        This function is used primarily for CSV import operations and handles
        both new volunteer creation and existing volunteer updates.
    """
    try:
        # Check if volunteer exists by salesforce_id
        volunteer = None
        if row.get("Id"):
            volunteer = Volunteer.query.filter_by(
                salesforce_individual_id=row["Id"]
            ).first()

        # If volunteer doesn't exist, create new one
        if not volunteer:
            volunteer = Volunteer()
            db.session.add(volunteer)

        # Update volunteer fields (handles both new and existing volunteers)
        volunteer.salesforce_individual_id = row.get("Id", "").strip()
        volunteer.salesforce_account_id = row.get("AccountId", "").strip()
        volunteer.first_name = row.get("FirstName", "").strip()
        volunteer.last_name = row.get("LastName", "").strip()
        volunteer.middle_name = row.get("MiddleName", "").strip()
        volunteer.organization_name = row.get("Primary Affiliation", "").strip()
        volunteer.title = row.get("Title", "").strip()
        volunteer.department = row.get("Department", "").strip()
        volunteer.industry = row.get("Industry", "").strip()

        # Handle gender enum
        gender_str = row.get("Gender", "").lower().replace(" ", "_").strip()
        if gender_str in [e.name for e in GenderEnum]:
            volunteer.gender = GenderEnum[gender_str]

        # Handle dates
        volunteer.birthdate = parse_date(row.get("Birthdate", ""))
        volunteer.first_volunteer_date = parse_date(
            row.get("First_Volunteer_Date__c", "")
        )
        volunteer.last_mailchimp_activity_date = parse_date(
            row.get("Last_Mailchimp_Email_Date__c", "")
        )
        volunteer.last_volunteer_date = parse_date(
            row.get("Last_Volunteer_Date__c", "")
        )
        volunteer.last_email_date = parse_date(row.get("Last_Email_Message__c", ""))
        volunteer.last_non_internal_email_date = parse_date(
            row.get("Last_Non_Internal_Email_Activity__c", "")
        )
        volunteer.notes = row.get("Notes", "").strip()

        # Handle emails
        new_emails = get_email_addresses(row)
        if new_emails:
            # Clear existing emails and add new ones
            volunteer.emails = new_emails

        # Handle phones
        new_phones = get_phone_numbers(row)
        if new_phones:
            # Clear existing phones and add new ones
            volunteer.phones = new_phones

        # Handle skills
        if row.get("Volunteer_Skills_Text__c") or row.get("Volunteer_Skills__c"):
            skills = parse_skills(
                row.get("Volunteer_Skills_Text__c", ""),
                row.get("Volunteer_Skills__c", ""),
            )

            # Update skills
            for skill_name in skills:
                skill = Skill.query.filter_by(name=skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.session.add(skill)
                if skill not in volunteer.skills:
                    volunteer.skills.append(skill)

        # Add this new section to handle times_volunteered
        if row.get("Number_of_Attended_Volunteer_Sessions__c"):
            try:
                volunteer.times_volunteered = int(
                    float(row["Number_of_Attended_Volunteer_Sessions__c"])
                )
            except (ValueError, TypeError):
                volunteer.times_volunteered = 0

        # Handle Connector data
        connector_data = {
            "active_subscription": (row.get("Connector_Active_Subscription__c") or "")
            .strip()
            .upper()
            or "NONE",
            "active_subscription_name": (
                row.get("Connector_Active_Subscription_Name__c") or ""
            ).strip(),
            "affiliations": (row.get("Connector_Affiliations__c") or "").strip(),
            "industry": (row.get("Connector_Industry__c") or "").strip(),
            "joining_date": (row.get("Connector_Joining_Date__c") or "").strip(),
            "last_login_datetime": (
                row.get("Connector_Last_Login_Date_Time__c") or ""
            ).strip(),
            "last_update_date": parse_date(row.get("Connector_Last_Update_Date__c")),
            "profile_link": (row.get("Connector_Profile_Link__c") or "").strip(),
            "role": (row.get("Connector_Role__c") or "").strip(),
            "signup_role": (row.get("Connector_SignUp_Role__c") or "").strip(),
            "user_auth_id": (row.get("Connector_User_ID__c") or "").strip(),
        }

        # Create or update connector data
        if not volunteer.connector:
            volunteer.connector = ConnectorData(volunteer_id=volunteer.id)

        # Update connector fields if they exist in Salesforce data
        if connector_data["active_subscription"] in [
            e.name for e in ConnectorSubscriptionEnum
        ]:
            if (
                volunteer.connector.active_subscription
                != ConnectorSubscriptionEnum[connector_data["active_subscription"]]
            ):
                volunteer.connector.active_subscription = ConnectorSubscriptionEnum[
                    connector_data["active_subscription"]
                ]

        for field, value in connector_data.items():
            if (
                field != "active_subscription" and value
            ):  # Skip active_subscription as it's handled above
                current_value = getattr(volunteer.connector, field)
                if current_value != value:
                    setattr(volunteer.connector, field, value)

        return success_count + 1, error_count

    except Exception as e:
        db.session.rollback()
        errors.append(f"Error processing row: {str(e)}")
        return success_count, error_count + 1


@volunteers_bp.route("/volunteers")
@login_required
def volunteers():
    """
    Main volunteer listing page with filtering, sorting, and pagination.

    This route handles the primary volunteer management interface, providing:
    - Comprehensive filtering by name, organization, email, skills, and local status
    - Sorting by various fields with configurable direction
    - Pagination for large datasets
    - Real-time volunteer count calculations

    Query Parameters:
    - page: Current page number for pagination
    - per_page: Number of volunteers per page
    - search_name: Filter by volunteer name (supports multi-term search)
    - org_search: Filter by organization name, title, or department
    - email_search: Filter by email address
    - skill_search: Filter by volunteer skills
    - local_status: Filter by local status (local, partial, non_local, unknown)
    - sort_by: Field to sort by (name, times_volunteered, last_volunteer_date)
    - sort_direction: Sort direction (asc, desc)

    Returns:
        rendered template: volunteers/volunteers.html with volunteer data and filters
    """
    # Get pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    # Create a dict of current filters, including pagination params
    current_filters = {
        "search_name": request.args.get("search_name", "").strip(),
        "org_search": request.args.get("org_search", "").strip(),
        "email_search": request.args.get("email_search", "").strip(),
        "skill_search": request.args.get("skill_search", "").strip(),
        "local_status": request.args.get("local_status", ""),
        "connector_only": request.args.get("connector_only", type=bool),
        "per_page": per_page,
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Get sort parameters
    sort_by = request.args.get("sort_by", "last_volunteer_date")  # default sort field
    sort_direction = request.args.get("sort_direction", "desc")  # default direction

    # Add sort parameters to current_filters
    current_filters.update({"sort_by": sort_by, "sort_direction": sort_direction})

    # Start with a subquery to get the attended count
    # This calculates the actual number of events each volunteer has attended
    # by counting EventParticipation records with valid attendance statuses
    attended_count_subq = (
        db.session.query(
            EventParticipation.volunteer_id,
            db.func.count(EventParticipation.id).label("attended_count"),
        )
        .filter(
            or_(
                EventParticipation.status == "Attended",
                EventParticipation.status == "Completed",
                EventParticipation.status == "Successfully Completed",
            )
        )
        .group_by(EventParticipation.volunteer_id)
        .subquery()
    )

    # Build main query with joins for filtering and organization data
    # This complex query allows for efficient filtering across multiple related tables
    query = (
        db.session.query(
            Volunteer,
            db.func.coalesce(attended_count_subq.c.attended_count, 0).label(
                "attended_count"
            ),
        )
        .outerjoin(
            attended_count_subq, Volunteer.id == attended_count_subq.c.volunteer_id
        )
        .outerjoin(VolunteerOrganization)
        .outerjoin(
            Organization, VolunteerOrganization.organization_id == Organization.id
        )
    )

    # Apply filters
    if current_filters.get("search_name"):
        # Split search terms and remove empty strings
        search_terms = [
            term.strip()
            for term in current_filters["search_name"].split()
            if term.strip()
        ]

        # Build dynamic search condition
        name_conditions = []
        for term in search_terms:
            search_pattern = f"%{term}%"
            name_conditions.append(
                or_(
                    Volunteer.first_name.ilike(search_pattern),
                    Volunteer.middle_name.ilike(search_pattern),
                    Volunteer.last_name.ilike(search_pattern),
                    # Concatenated name search using SQLite's || operator
                    (
                        Volunteer.first_name
                        + " "
                        + db.func.coalesce(Volunteer.middle_name, "")
                        + " "
                        + Volunteer.last_name
                    ).ilike(search_pattern),
                )
            )
        # Combine all conditions with AND (each term must match somewhere)
        if name_conditions:
            query = query.filter(and_(*name_conditions))

    if current_filters.get("org_search"):
        search_term = f"%{current_filters['org_search']}%"
        # The joins are already established in the main query, so we can directly filter
        query = query.filter(
            or_(
                # Search direct volunteer fields
                Volunteer.organization_name.ilike(search_term),
                Volunteer.title.ilike(search_term),
                Volunteer.department.ilike(search_term),
                # Search related organization fields
                Organization.name.ilike(search_term),
                VolunteerOrganization.role.ilike(search_term),
            )
        )

    if current_filters.get("email_search"):
        search_term = f"%{current_filters['email_search']}%"
        query = query.join(Email).filter(Email.email.ilike(search_term))

    if current_filters.get("skill_search"):
        search_term = f"%{current_filters['skill_search']}%"
        query = query.join(Volunteer.skills).filter(Skill.name.ilike(search_term))

    if current_filters.get("local_status"):
        query = query.filter(Volunteer.local_status == current_filters["local_status"])

    if current_filters.get("connector_only"):
        query = query.filter(
            Volunteer.connector.has(ConnectorData.user_auth_id.isnot(None))
        )

    # Apply sorting based on parameters
    if sort_by:
        sort_column = None
        if sort_by == "name":
            sort_column = (
                Volunteer.first_name
                + " "
                + db.func.coalesce(Volunteer.middle_name, "")
                + " "
                + Volunteer.last_name
            )
        elif sort_by == "times_volunteered":
            sort_column = (
                Volunteer.times_volunteered
                + db.func.coalesce(attended_count_subq.c.attended_count, 0)
                + Volunteer.additional_volunteer_count
            )

        if sort_column is not None:
            if sort_direction == "desc":
                query = query.order_by(sort_column.desc(), Volunteer.last_name.asc())
            else:
                query = query.order_by(sort_column.asc(), Volunteer.last_name.asc())
        else:
            # Default sort
            query = query.order_by(Volunteer.last_volunteer_date.desc())

    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Transform the results to include the attended count and organization info
    volunteers_with_counts = []
    for result in pagination.items:
        volunteer_data = {
            "volunteer": result[0],
            "attended_count": result[1] or 0,
            "organizations": [],
            "organizations_json": [],  # JSON-serializable version
        }

        # Get organization info with roles
        for vol_org in result[0].volunteer_organizations:
            org_info = {
                "organization": vol_org.organization,
                "role": vol_org.role,
                "status": vol_org.status,
                "is_primary": vol_org.is_primary,
            }
            volunteer_data["organizations"].append(org_info)

            # Create JSON-serializable version
            org_json = {
                "organization": {
                    "id": vol_org.organization.id,
                    "name": vol_org.organization.name,
                },
                "role": vol_org.role,
                "status": vol_org.status,
                "is_primary": vol_org.is_primary,
            }
            volunteer_data["organizations_json"].append(org_json)

        # Ensure organizations_json is always a list, even if empty
        if volunteer_data["organizations_json"] is None:
            volunteer_data["organizations_json"] = []

        # Debug: Print the organizations_json for the first few volunteers
        if len(volunteers_with_counts) < 3:
            print(
                f"Volunteer {result[0].id}: {len(volunteer_data['organizations_json'])} organizations"
            )
            print(f"Organizations JSON: {volunteer_data['organizations_json']}")

        volunteers_with_counts.append(volunteer_data)

    return render_template(
        "volunteers/volunteers.html",
        volunteers=volunteers_with_counts,
        pagination=pagination,
        current_filters=current_filters,
    )


@volunteers_bp.route("/volunteers/add", methods=["GET", "POST"])
@login_required
def add_volunteer():
    form = VolunteerForm()

    if form.validate_on_submit():
        try:
            # Create and add volunteer first
            volunteer = Volunteer(
                salutation=form.salutation.data if form.salutation.data else None,
                first_name=form.first_name.data,
                middle_name=form.middle_name.data,
                last_name=form.last_name.data,
                suffix=form.suffix.data if form.suffix.data else None,
                organization_name=form.organization_name.data,
                title=form.title.data,
                department=form.department.data,
                industry=form.industry.data,
                notes=form.notes.data,
            )

            # Handle enums properly
            if form.gender.data:
                volunteer.gender = GenderEnum[form.gender.data]
            if form.local_status.data:
                volunteer.local_status = LocalStatusEnum[form.local_status.data]
            if form.race_ethnicity.data:
                volunteer.race_ethnicity = RaceEthnicityEnum[form.race_ethnicity.data]
            if form.education.data:
                volunteer.education = EducationEnum[form.education.data]

            db.session.add(volunteer)
            db.session.flush()  # This ensures volunteer has an ID before adding relationships

            # Add skills
            if form.skills.data:
                # Parse skills from textarea (assume comma-separated)
                skill_names = [
                    skill.strip()
                    for skill in form.skills.data.split(",")
                    if skill.strip()
                ]
                for skill_name in set(skill_names):
                    skill = Skill.query.filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.session.add(skill)
                        db.session.flush()
                    volunteer.skills.append(skill)

            # Add email
            if form.email.data:
                email_type = (
                    ContactTypeEnum.personal
                    if form.email_type.data == "personal"
                    else ContactTypeEnum.professional
                )
                email = Email(
                    email=form.email.data,
                    type=email_type,
                    primary=True,
                    contact_id=volunteer.id,
                )
                db.session.add(email)

            # Add phone
            if form.phone.data:
                phone_type = (
                    ContactTypeEnum.personal
                    if form.phone_type.data == "personal"
                    else ContactTypeEnum.professional
                )
                phone = Phone(
                    number=form.phone.data,
                    type=phone_type,
                    primary=True,
                    contact_id=volunteer.id,
                )
                db.session.add(phone)

            # Link to organization if provided
            if form.organization_name.data:
                vol_org = VolunteerOrganization.link_volunteer_to_org(
                    volunteer=volunteer,
                    org_name=form.organization_name.data,
                    role=form.title.data,  # Use title as role for now
                    is_primary=True,
                )
                db.session.flush()

            db.session.commit()
            flash("Volunteer added successfully!", "success")
            return redirect(url_for("volunteers.volunteers"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error adding volunteer: {str(e)}", "error")

    return render_template("volunteers/add_volunteer.html", form=form)


@volunteers_bp.route("/volunteers/view/<int:id>")
@login_required
def view_volunteer(id):
    volunteer = db.session.get(Volunteer, id)
    if not volunteer:
        abort(404)

    # Get all participations for this volunteer, including virtual events
    participations = (
        EventParticipation.query.filter_by(volunteer_id=id)
        .join(Event, EventParticipation.event_id == Event.id)
        .all()
    )

    # Define status mapping for various event types and status values
    status_mapping = {
        # Standard statuses
        "Attended": "Attended",
        "Completed": "Attended",
        "No-Show": "No-Show",
        "No Show": "No-Show",
        "Cancelled": "Cancelled",
        "Canceled": "Cancelled",
        # Virtual-specific statuses
        "successfully completed": "Attended",
        "simulcast": "Attended",
        "technical difficulties": "No-Show",
        "local professional no-show": "No-Show",
        "pathful professional no-show": "No-Show",
        "teacher no-show": "No-Show",
        "teacher cancelation": "Cancelled",
        "Confirmed": "Attended",  # Could be pending or attended depending on your business logic
    }

    # Initialize participation stats with empty lists
    participation_stats = {"Attended": [], "No-Show": [], "Cancelled": []}

    # Process each participation record
    for participation in participations:
        # Get status from participation record, fall back to event status
        status = participation.status

        # If status isn't directly usable, try mapping it
        if status not in participation_stats:
            # Try using the mapping, default to 'Attended' if not found
            mapped_status = status_mapping.get(status, "Attended")

            # If still not valid, try lowercased version (handle case sensitivity)
            if mapped_status not in participation_stats and status:
                mapped_status = status_mapping.get(status.lower(), "Attended")
        else:
            mapped_status = status

        # Get the event date, handling virtual events that might store date differently
        event_date = None
        if participation.event.start_date:
            event_date = participation.event.start_date
        elif hasattr(participation.event, "date") and participation.event.date:
            event_date = participation.event.date
        else:
            # If no date available, create a default date to avoid errors
            event_date = datetime.now()

        # Add to appropriate category
        if mapped_status in participation_stats:
            participation_stats[mapped_status].append(
                {
                    "event": participation.event,
                    "delivery_hours": participation.delivery_hours,
                    "date": event_date,
                }
            )

    # Sort each list by date
    for status in participation_stats:
        participation_stats[status].sort(key=lambda x: x["date"], reverse=True)

    # Get history records for the volunteer
    histories = (
        History.query.filter_by(volunteer_id=id, is_deleted=False)
        .order_by(History.activity_date.desc())
        .all()
    )

    # Create a dictionary of organization relationships for easy access in template
    org_relationships = {}
    for vol_org in volunteer.volunteer_organizations:
        org_relationships[vol_org.organization_id] = vol_org

    return render_template(
        "volunteers/view.html",
        volunteer=volunteer,
        emails=sorted(volunteer.emails, key=lambda x: x.primary, reverse=True),
        phones=sorted(volunteer.phones, key=lambda x: x.primary, reverse=True),
        participation_stats=participation_stats,
        histories=histories,
        org_relationships=org_relationships,
        now=datetime.now(),
    )


@volunteers_bp.route("/volunteers/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_volunteer(id):
    volunteer = db.session.get(Volunteer, id)
    if not volunteer:
        abort(404)

    form = VolunteerForm(obj=volunteer)

    # Populate form with existing data
    if request.method == "GET":
        # Handle enums properly
        if volunteer.gender:
            form.gender.data = volunteer.gender.name
        if volunteer.local_status:
            form.local_status.data = volunteer.local_status.name
        if volunteer.race_ethnicity:
            form.race_ethnicity.data = volunteer.race_ethnicity.name
        if volunteer.education:
            form.education.data = volunteer.education.name

        # Handle skills as comma-separated string
        if volunteer.skills:
            form.skills.data = ", ".join([skill.name for skill in volunteer.skills])

        # Handle email and phone safely
        try:
            emails_list = list(volunteer.emails) if volunteer.emails else []
            if emails_list:
                primary_email = next(
                    (email for email in emails_list if email.primary), None
                )
                if not primary_email:
                    primary_email = emails_list[0]
                if primary_email:
                    form.email.data = primary_email.email
                    form.email_type.data = primary_email.type.name
        except Exception as e:
            print(f"Error loading emails: {e}")

        try:
            phones_list = list(volunteer.phones) if volunteer.phones else []
            if phones_list:
                primary_phone = next(
                    (phone for phone in phones_list if phone.primary), None
                )
                if not primary_phone:
                    primary_phone = phones_list[0]
                if primary_phone:
                    form.phone.data = primary_phone.number
                    form.phone_type.data = primary_phone.type.name
        except Exception as e:
            print(f"Error loading phones: {e}")

    if form.validate_on_submit():
        try:
            print(f"Form data: {form.data}")  # Debug form data

            # Update basic fields
            volunteer.salutation = (
                form.salutation.data if form.salutation.data else None
            )
            volunteer.first_name = form.first_name.data
            volunteer.middle_name = form.middle_name.data
            volunteer.last_name = form.last_name.data
            volunteer.suffix = form.suffix.data if form.suffix.data else None
            volunteer.organization_name = form.organization_name.data
            volunteer.title = form.title.data
            volunteer.department = form.department.data
            volunteer.industry = form.industry.data
            volunteer.notes = form.notes.data

            print(f"Basic fields updated")  # Debug checkpoint

            # Handle enums with proper error checking
            try:
                if form.gender.data and form.gender.data != "":
                    volunteer.gender = GenderEnum[form.gender.data]
                else:
                    volunteer.gender = None

                if form.local_status.data and form.local_status.data != "":
                    volunteer.local_status = LocalStatusEnum[form.local_status.data]
                else:
                    volunteer.local_status = None

                if form.race_ethnicity.data and form.race_ethnicity.data != "":
                    volunteer.race_ethnicity = RaceEthnicityEnum[
                        form.race_ethnicity.data
                    ]
                else:
                    volunteer.race_ethnicity = None

                if form.education.data and form.education.data != "":
                    volunteer.education = EducationEnum[form.education.data]
                else:
                    volunteer.education = None

                print(f"Enums updated")  # Debug checkpoint
            except KeyError as e:
                print(f"Enum error: {e}")
                flash(f"Invalid enum value: {str(e)}", "error")
                return redirect(url_for("volunteers.edit_volunteer", id=id))

            # Handle skills
            if (
                form.skills.data
                and form.skills.data.strip()
                and form.skills.data != "[]"
            ):
                try:
                    # Clear existing skills
                    volunteer.skills = []
                    db.session.flush()

                    # Add new skills
                    skill_names = [
                        skill.strip()
                        for skill in form.skills.data.split(",")
                        if skill.strip() and skill.strip() != "[]"
                    ]
                    for skill_name in set(skill_names):
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                            db.session.add(skill)
                            db.session.flush()
                        volunteer.skills.append(skill)
                    print(f"Skills updated: {skill_names}")  # Debug checkpoint
                except Exception as e:
                    print(f"Skills error: {e}")
                    flash(f"Error updating skills: {str(e)}", "error")
                    return redirect(url_for("volunteers.edit_volunteer", id=id))
            else:
                # Clear skills if empty
                volunteer.skills = []
                print("Skills cleared (empty input)")  # Debug checkpoint

            # Handle email with transaction safety
            if form.email.data:
                try:
                    Email.query.filter_by(contact_id=volunteer.id).delete()
                    email_type = (
                        ContactTypeEnum.personal
                        if form.email_type.data == "personal"
                        else ContactTypeEnum.professional
                    )
                    email = Email(
                        contact_id=volunteer.id,
                        email=form.email.data,
                        type=email_type,
                        primary=True,
                    )
                    db.session.add(email)
                    print(f"Email updated: {form.email.data}")  # Debug checkpoint
                except Exception as e:
                    print(f"Email error: {e}")
                    flash(f"Error updating email: {str(e)}", "error")
                    return redirect(url_for("volunteers.edit_volunteer", id=id))

            # Handle phone with transaction safety
            if form.phone.data:
                try:
                    Phone.query.filter_by(contact_id=volunteer.id).delete()
                    phone_type = (
                        ContactTypeEnum.personal
                        if form.phone_type.data == "personal"
                        else ContactTypeEnum.professional
                    )
                    phone = Phone(
                        contact_id=volunteer.id,
                        number=form.phone.data,
                        type=phone_type,
                        primary=True,
                    )
                    db.session.add(phone)
                    print(f"Phone updated: {form.phone.data}")  # Debug checkpoint
                except Exception as e:
                    print(f"Phone error: {e}")
                    flash(f"Error updating phone: {str(e)}", "error")
                    return redirect(url_for("volunteers.edit_volunteer", id=id))

            print("About to commit to database")  # Debug checkpoint
            db.session.commit()
            print(f"Database committed successfully")  # Debug checkpoint
            flash("Volunteer updated successfully", "success")
            redirect_url = url_for("volunteers.view_volunteer", id=volunteer.id)
            print(f"Redirecting to: {redirect_url}")  # Debug redirect URL
            return redirect(redirect_url)

        except Exception as e:
            db.session.rollback()
            print(f"General error in edit_volunteer: {str(e)}")  # Debug error
            flash(f"Error updating volunteer: {str(e)}", "error")
    else:
        # Form validation failed
        print(
            f"Form validation failed. Errors: {form.errors}"
        )  # Debug validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template(
        "volunteers/edit.html",
        form=form,
        volunteer=volunteer,
        GenderEnum=GenderEnum,
        RaceEthnicityEnum=RaceEthnicityEnum,
        LocalStatusEnum=LocalStatusEnum,
        EducationEnum=EducationEnum,
    )


@volunteers_bp.route("/volunteers/purge", methods=["POST"])
@login_required
@admin_required
def purge_volunteers():

    try:
        # Get all volunteer IDs first
        volunteer_ids = db.session.query(Volunteer.id).all()
        volunteer_ids = [v[0] for v in volunteer_ids]

        # Delete all related data for volunteers
        Email.query.filter(Email.contact_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        Phone.query.filter(Phone.contact_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        Address.query.filter(Address.contact_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        VolunteerSkill.query.filter(
            VolunteerSkill.volunteer_id.in_(volunteer_ids)
        ).delete(synchronize_session=False)
        Engagement.query.filter(Engagement.volunteer_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        EventParticipation.query.filter(
            EventParticipation.volunteer_id.in_(volunteer_ids)
        ).delete(synchronize_session=False)
        History.query.filter(History.volunteer_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        VolunteerOrganization.query.filter(
            VolunteerOrganization.volunteer_id.in_(volunteer_ids)
        ).delete(synchronize_session=False)
        # Before deleting volunteers:
        Volunteer.query.delete()  # This should trigger cascades
        # Also clean up:
        Email.query.filter(
            Email.contact_id.notin_(Contact.query.with_entities(Contact.id))
        ).delete()
        Phone.query.filter(
            Phone.contact_id.notin_(Contact.query.with_entities(Contact.id))
        ).delete()
        db.session.commit()
        # Clean up related records first
        EventParticipation.query.filter(
            EventParticipation.volunteer_id.in_(volunteer_ids)
        ).delete(synchronize_session=False)
        History.query.filter(History.volunteer_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        VolunteerOrganization.query.filter(
            VolunteerOrganization.volunteer_id.in_(volunteer_ids)
        ).delete(synchronize_session=False)

        # Clean up orphaned email and phone records
        Email.query.filter(Email.contact_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        Phone.query.filter(Phone.contact_id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )

        # Delete volunteers and their contact records
        Volunteer.query.filter(Volunteer.id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )
        Contact.query.filter(Contact.id.in_(volunteer_ids)).delete(
            synchronize_session=False
        )

        db.session.commit()
        log_audit_action(
            action="purge",
            resource_type="volunteer",
            resource_id=None,
            metadata={"count": len(volunteer_ids)},
        )
        return jsonify(
            {
                "success": True,
                "message": f"Successfully deleted {len(volunteer_ids)} volunteers and associated records",
            }
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {"success": False, "message": f"Error deleting volunteers: {str(e)}"}
            ),
            500,
        )


@volunteers_bp.route("/volunteers/delete/<int:id>", methods=["DELETE"])
@login_required
@admin_required
def delete_volunteer(id):

    try:
        volunteer = db.session.get(Volunteer, id)
        if not volunteer:
            abort(404)

        # Delete all related records first (in correct order due to foreign key constraints)
        Email.query.filter_by(contact_id=id).delete()
        Phone.query.filter_by(contact_id=id).delete()
        Address.query.filter_by(contact_id=id).delete()
        VolunteerSkill.query.filter_by(volunteer_id=id).delete()
        History.query.filter_by(volunteer_id=id).delete()
        EventParticipation.query.filter_by(volunteer_id=id).delete()
        VolunteerOrganization.query.filter_by(volunteer_id=id).delete()

        # Delete the volunteer
        db.session.delete(volunteer)
        db.session.commit()
        log_audit_action(
            action="delete",
            resource_type="volunteer",
            resource_id=id,
        )

        return jsonify({"success": True, "message": "Volunteer deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@volunteers_bp.route("/volunteers/import-from-salesforce", methods=["POST"])
@login_required
def import_from_salesforce():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        print("Starting volunteer import from Salesforce...")

        # Define Salesforce query
        salesforce_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email,
               npe01__AlternateEmail__c, npe01__HomeEmail__c,
               npe01__WorkEmail__c, npe01__Preferred_Email__c,
               HomePhone, MobilePhone, npe01__WorkPhone__c, Phone,
               npe01__PreferredPhone__c,
               npsp__Primary_Affiliation__c, Title, Department, Gender__c,
               Birthdate, Last_Mailchimp_Email_Date__c, Last_Volunteer_Date__c,
               Last_Email_Message__c, Volunteer_Recruitment_Notes__c,
               Volunteer_Skills__c, Volunteer_Skills_Text__c,
               Volunteer_Interests__c,
               Number_of_Attended_Volunteer_Sessions__c,
               Racial_Ethnic_Background__c,
               Last_Activity_Date__c,
               First_Volunteer_Date__c,
               Last_Non_Internal_Email_Activity__c,
               Description, Highest_Level_of_Educational__c, Age_Group__c,
               DoNotCall, npsp__Do_Not_Contact__c, HasOptedOutOfEmail,
               EmailBouncedDate,
               MailingAddress, npe01__Home_Address__c, npe01__Work_Address__c,
               npe01__Other_Address__c, npe01__Primary_Address_Type__c,
               npe01__Secondary_Address_Type__c,
               Connector_Active_Subscription__c,
               Connector_Active_Subscription_Name__c,
               Connector_Affiliations__c,
               Connector_Industry__c,
               Connector_Joining_Date__c,
               Connector_Last_Login_Date_Time__c,
               Connector_Last_Update_Date__c,
               Connector_Profile_Link__c,
               Connector_Role__c,
               Connector_SignUp_Role__c,
               Connector_User_ID__c
        FROM Contact
        WHERE Contact_Type__c = 'Volunteer' or Contact_Type__c=''
        """

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        # Execute the query
        result = sf.query_all(salesforce_query)
        sf_rows = result.get("records", [])
        total_records = len(sf_rows)

        print(f"Found {total_records} records to process")

        success_count = 0
        error_count = 0
        created_count = 0
        updated_count = 0
        errors = []

        # Progress tracking
        progress_interval = max(1, total_records // 20)  # Show progress every 5%
        last_progress = 0

        # Add comprehensive education mapping
        education_mapping = {
            # Exact matches
            "BACHELORS": "BACHELORS_DEGREE",
            "MASTERS": "MASTERS",
            "DOCTORATE": "DOCTORATE",
            # Common variations
            "BACHELOR": "BACHELORS_DEGREE",
            "BACHELOR'S": "BACHELORS_DEGREE",
            "BACHELORS DEGREE": "BACHELORS_DEGREE",
            "MASTER": "MASTERS",
            "MASTER'S": "MASTERS",
            "MASTERS DEGREE": "MASTERS",
            "PHD": "DOCTORATE",
            "PH.D": "DOCTORATE",
            "PH.D.": "DOCTORATE",
            "DOCTORAL": "DOCTORATE",
            # New Salesforce specific values
            "HIGH SCHOOL DIPLOMA OR GED": "HIGH_SCHOOL",
            "ADVANCED PROFESSIONAL DEGREE": "PROFESSIONAL",
            "PREFER NOT TO ANSWER": "UNKNOWN",
            # Other credentials
            "CERTIFICATE": "OTHER",
            "CERTIFICATION": "OTHER",
            "ASSOCIATE": "ASSOCIATES",
            "ASSOCIATES": "ASSOCIATES",
            "ASSOCIATE'S": "ASSOCIATES",
            "HIGH SCHOOL": "HIGH_SCHOOL",
            "GED": "HIGH_SCHOOL",
            "SOME COLLEGE": "SOME_COLLEGE",
            "PROFESSIONAL": "PROFESSIONAL",
            "PROFESSIONAL DEGREE": "PROFESSIONAL",
        }

        # Process each row from Salesforce
        for i, row in enumerate(sf_rows):
            try:
                # Progress indicator
                if i >= last_progress + progress_interval:
                    progress = (i / total_records) * 100
                    print(
                        f"Progress: {progress:.1f}% ({i}/{total_records}) - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}"
                    )
                    last_progress = i

                # Check if volunteer exists
                volunteer = Volunteer.query.filter_by(
                    salesforce_individual_id=row["Id"]
                ).first()
                is_new = False
                updates = []

                if not volunteer:
                    volunteer = Volunteer()
                    volunteer.salesforce_individual_id = row["Id"]
                    db.session.add(volunteer)
                    is_new = True
                    updates.append("new")

                # Update volunteer fields only if they've changed
                if volunteer.salesforce_account_id != row["AccountId"]:
                    volunteer.salesforce_account_id = row["AccountId"]
                    updates.append("acc")

                new_first_name = (row.get("FirstName") or "").strip()
                if volunteer.first_name != new_first_name:
                    volunteer.first_name = new_first_name
                    updates.append("fn")

                new_last_name = (row.get("LastName") or "").strip()
                if volunteer.last_name != new_last_name:
                    volunteer.last_name = new_last_name
                    updates.append("ln")

                new_middle_name = (row.get("MiddleName") or "").strip()
                if volunteer.middle_name != new_middle_name:
                    volunteer.middle_name = new_middle_name
                    updates.append("mn")

                new_org_name = (row.get("npsp__Primary_Affiliation__c") or "").strip()
                if volunteer.organization_name != new_org_name:
                    volunteer.organization_name = new_org_name
                    updates.append("org")

                new_title = (row.get("Title") or "").strip()
                if volunteer.title != new_title:
                    volunteer.title = new_title
                    updates.append("title")

                new_department = (row.get("Department") or "").strip()
                if volunteer.department != new_department:
                    volunteer.department = new_department
                    updates.append("dept")

                # Handle gender enum
                gender_str = (
                    (row.get("Gender__c") or "").lower().replace(" ", "_").strip()
                )
                if gender_str and gender_str in [e.name for e in GenderEnum]:
                    if not volunteer.gender or volunteer.gender.name != gender_str:
                        volunteer.gender = GenderEnum[gender_str]
                        updates.append("gen")

                # Handle race/ethnicity
                race_ethnicity_map = {
                    "Bi-racial/Multi-racial/Multicultural": "bi_multi_racial",
                    "Black": "black_african",
                    "Black/African American": "black",
                    "Prefer not to answer": "prefer_not_to_say",
                    "Native American/Alaska Native/First Nation": "native_american",
                    "White/Caucasian/European American": "white_caucasian",
                    "Hispanic American/Latino": "hispanic_american",
                    "Other POC": "other_poc",
                    "Asian American/Pacific Islander": "asian_pacific_islander",
                }

                # Set default mappings for common cases
                default_mapping = {
                    "Other POC": "other",
                    "White/Caucasian/European American": "white",
                    "Black": "black",
                    "Bi-racial/Multi-racial/Multicultural": "multi_racial",
                }

                race_ethnicity_str = row.get("Racial_Ethnic_Background__c")

                if race_ethnicity_str and race_ethnicity_str != "None":
                    # Clean the string for comparison
                    cleaned_str = race_ethnicity_str.strip()
                    if "AggregateResult" in cleaned_str:
                        cleaned_str = cleaned_str.replace("AggregateResult", "").strip()

                    # Try primary mapping first
                    enum_value = race_ethnicity_map.get(cleaned_str)

                    if enum_value and enum_value in [e.name for e in RaceEthnicityEnum]:
                        if (
                            not volunteer.race_ethnicity
                            or volunteer.race_ethnicity.name != enum_value
                        ):
                            volunteer.race_ethnicity = RaceEthnicityEnum[enum_value]
                            updates.append("race")
                    else:
                        # Try default mapping if primary fails
                        default_value = default_mapping.get(cleaned_str)
                        if default_value and default_value in [
                            e.name for e in RaceEthnicityEnum
                        ]:
                            if (
                                not volunteer.race_ethnicity
                                or volunteer.race_ethnicity.name != default_value
                            ):
                                volunteer.race_ethnicity = RaceEthnicityEnum[
                                    default_value
                                ]
                                updates.append("race")
                elif volunteer.race_ethnicity != RaceEthnicityEnum.unknown:
                    volunteer.race_ethnicity = RaceEthnicityEnum.unknown
                    updates.append("race")

                # Handle dates
                new_birthdate = parse_date(row.get("Birthdate"))
                if volunteer.birthdate != new_birthdate:
                    volunteer.birthdate = new_birthdate
                    updates.append("bd")

                new_first_volunteer_date = parse_date(
                    row.get("First_Volunteer_Date__c")
                )
                if volunteer.first_volunteer_date != new_first_volunteer_date:
                    volunteer.first_volunteer_date = new_first_volunteer_date
                    updates.append("fvd")

                new_mailchimp_date = parse_date(row.get("Last_Mailchimp_Email_Date__c"))
                if volunteer.last_mailchimp_activity_date != new_mailchimp_date:
                    volunteer.last_mailchimp_activity_date = new_mailchimp_date
                    updates.append("mcd")

                new_volunteer_date = parse_date(row.get("Last_Volunteer_Date__c"))
                if volunteer.last_volunteer_date != new_volunteer_date:
                    volunteer.last_volunteer_date = new_volunteer_date
                    updates.append("lvd")

                new_activity_date = parse_date(row.get("Last_Activity_Date__c"))
                if volunteer.last_activity_date != new_activity_date:
                    volunteer.last_activity_date = new_activity_date
                    updates.append("lad")

                new_email_date = parse_date(row.get("Last_Email_Message__c"))
                if volunteer.last_email_date != new_email_date:
                    volunteer.last_email_date = new_email_date
                    updates.append("led")

                new_non_internal_email_date = parse_date(
                    row.get("Last_Non_Internal_Email_Activity__c")
                )
                if (
                    volunteer.last_non_internal_email_date
                    != new_non_internal_email_date
                ):
                    volunteer.last_non_internal_email_date = new_non_internal_email_date
                    updates.append("nied")

                new_notes = (row.get("Volunteer_Recruitment_Notes__c") or "").strip()
                if volunteer.notes != new_notes:
                    volunteer.notes = new_notes
                    updates.append("notes")

                # Handle description
                new_description = (row.get("Description") or "").strip()
                if volunteer.description != new_description:
                    volunteer.description = new_description
                    updates.append("desc")

                # Handle education level with robust mapping
                education_str = (
                    row.get("Highest_Level_of_Educational__c") or ""
                ).strip()
                if education_str:
                    try:
                        # Normalize the string (uppercase, remove special chars)
                        normalized_education = (
                            education_str.upper().replace(".", "").replace("-", " ")
                        )

                        # Try direct mapping first
                        enum_value = education_mapping.get(normalized_education)

                        if enum_value and enum_value in [e.name for e in EducationEnum]:
                            if (
                                not volunteer.education
                                or volunteer.education.name != enum_value
                            ):
                                volunteer.education = EducationEnum[enum_value]
                                updates.append("edu")
                        else:
                            # Log unmatched values for future mapping updates
                            volunteer.education = EducationEnum.UNKNOWN
                            updates.append("edu")

                    except (ValueError, KeyError) as e:
                        # Set to UNKNOWN if mapping fails
                        volunteer.education = EducationEnum.UNKNOWN
                        updates.append("edu")

                # Handle age group
                age_str = (row.get("Age_Group__c") or "").strip()
                if age_str:
                    # Map Salesforce age groups to our enum
                    age_map = {
                        "Under 18": AgeGroupEnum.UNDER_18,
                        "18-24": AgeGroupEnum.AGE_18_24,
                        "25-34": AgeGroupEnum.AGE_25_34,
                        "35-44": AgeGroupEnum.AGE_35_44,
                        "45-54": AgeGroupEnum.AGE_45_54,
                        "55-64": AgeGroupEnum.AGE_55_64,
                        "65+": AgeGroupEnum.AGE_65_PLUS,
                    }
                    new_age_group = age_map.get(age_str, AgeGroupEnum.UNKNOWN)
                    if volunteer.age_group != new_age_group:
                        volunteer.age_group = new_age_group
                        updates.append("age")

                # Handle interests
                interests_str = row.get("Volunteer_Interests__c")
                if (
                    interests_str is not None
                ):  # Only update if field exists in Salesforce data
                    interests_str = interests_str.strip()
                    if volunteer.interests != interests_str:
                        volunteer.interests = interests_str
                        updates.append("int")

                # Handle skills - only update if there are changes
                if row.get("Volunteer_Skills__c") or row.get(
                    "Volunteer_Skills_Text__c"
                ):
                    new_skills = parse_skills(
                        row.get("Volunteer_Skills_Text__c", ""),
                        row.get("Volunteer_Skills__c", ""),
                    )
                    current_skills = {skill.name for skill in volunteer.skills}
                    if set(new_skills) != current_skills:
                        # Clear existing skills
                        volunteer.skills = []
                        # Add new skills
                        for skill_name in new_skills:
                            skill = Skill.query.filter_by(name=skill_name).first()
                            if not skill:
                                skill = Skill(name=skill_name)
                                db.session.add(skill)
                            if skill not in volunteer.skills:
                                volunteer.skills.append(skill)
                        updates.append("skills")

                # Handle times_volunteered
                if row.get("Number_of_Attended_Volunteer_Sessions__c"):
                    try:
                        new_times = int(
                            float(row["Number_of_Attended_Volunteer_Sessions__c"])
                        )
                        if volunteer.times_volunteered != new_times:
                            volunteer.times_volunteered = new_times
                            updates.append("tv")
                    except (ValueError, TypeError):
                        if volunteer.times_volunteered != 0:
                            volunteer.times_volunteered = 0
                            updates.append("tv")

                # Handle contact preferences
                new_do_not_call = bool(row.get("DoNotCall"))
                if volunteer.do_not_call != new_do_not_call:
                    volunteer.do_not_call = new_do_not_call
                    updates.append("dnc")

                new_do_not_contact = bool(row.get("npsp__Do_Not_Contact__c"))
                if volunteer.do_not_contact != new_do_not_contact:
                    volunteer.do_not_contact = new_do_not_contact
                    updates.append("dnt")

                new_email_opt_out = bool(row.get("HasOptedOutOfEmail"))
                if volunteer.email_opt_out != new_email_opt_out:
                    volunteer.email_opt_out = new_email_opt_out
                    updates.append("eoo")

                # Handle email bounce date
                new_bounce_date = parse_date(row.get("EmailBouncedDate"))
                if volunteer.email_bounced_date != new_bounce_date:
                    volunteer.email_bounced_date = new_bounce_date
                    updates.append("ebd")

                # Handle emails
                email_fields = {
                    "npe01__WorkEmail__c": ContactTypeEnum.professional,
                    "Email": ContactTypeEnum.personal,
                    "npe01__HomeEmail__c": ContactTypeEnum.personal,
                    "npe01__AlternateEmail__c": ContactTypeEnum.personal,
                }

                # Get preferred email type
                preferred_email = row.get("npe01__Preferred_Email__c", "").lower()
                email_changes = False

                # Process each email field
                for email_field, email_type in email_fields.items():
                    email_value = row.get(email_field)
                    if not email_value:
                        continue

                    # Check if this should be the primary email based on preference
                    is_primary = False
                    if preferred_email:
                        if (
                            (
                                preferred_email == "work"
                                and email_field == "npe01__WorkEmail__c"
                            )
                            or (
                                preferred_email == "personal"
                                and email_field in ["npe01__HomeEmail__c", "Email"]
                            )
                            or (
                                preferred_email == "alternate"
                                and email_field == "npe01__AlternateEmail__c"
                            )
                        ):
                            is_primary = True
                    elif (
                        email_field == "Email"
                    ):  # Default to standard Email field as primary if no preference
                        is_primary = True

                    # Check if email already exists
                    email = Email.query.filter_by(
                        contact_id=volunteer.id, email=email_value
                    ).first()

                    if not email:
                        email = Email(
                            contact_id=volunteer.id,
                            email=email_value,
                            type=email_type,
                            primary=is_primary,
                        )
                        db.session.add(email)
                        email_changes = True
                    else:
                        # Update existing email type and primary status if changed
                        if email.type != email_type:
                            email.type = email_type
                            email_changes = True
                        if is_primary and not email.primary:
                            # Set all other emails to non-primary
                            Email.query.filter_by(
                                contact_id=volunteer.id, primary=True
                            ).update({"primary": False})
                            email.primary = True
                            email_changes = True

                if email_changes:
                    updates.append("emails")

                # Handle phone numbers
                phone_fields = {
                    "npe01__WorkPhone__c": ContactTypeEnum.professional,
                    "Phone": ContactTypeEnum.professional,  # Business Phone
                    "HomePhone": ContactTypeEnum.personal,
                    "MobilePhone": ContactTypeEnum.personal,
                }

                # Get preferred phone type
                preferred_phone = row.get("npe01__PreferredPhone__c", "").lower()
                phone_changes = False

                # Process each phone field
                for phone_field, phone_type in phone_fields.items():
                    phone_value = row.get(phone_field)
                    if not phone_value:
                        continue

                    # Check if this should be the primary phone based on preference
                    is_primary = False
                    if preferred_phone:
                        if (
                            (
                                preferred_phone == "work"
                                and phone_field in ["npe01__WorkPhone__c", "Phone"]
                            )
                            or (
                                preferred_phone == "home" and phone_field == "HomePhone"
                            )
                            or (
                                preferred_phone == "mobile"
                                and phone_field == "MobilePhone"
                            )
                        ):
                            is_primary = True
                    elif (
                        phone_field == "Phone"
                    ):  # Default to business Phone as primary if no preference
                        is_primary = True

                    # Check if phone already exists
                    phone = Phone.query.filter_by(
                        contact_id=volunteer.id, number=phone_value
                    ).first()

                    if not phone:
                        phone = Phone(
                            contact_id=volunteer.id,
                            number=phone_value,
                            type=phone_type,
                            primary=is_primary,
                        )
                        db.session.add(phone)
                        phone_changes = True
                    else:
                        # Update existing phone type and primary status if changed
                        if phone.type != phone_type:
                            phone.type = phone_type
                            phone_changes = True
                        if is_primary and not phone.primary:
                            # Set all other phones to non-primary
                            Phone.query.filter_by(
                                contact_id=volunteer.id, primary=True
                            ).update({"primary": False})
                            phone.primary = True
                            phone_changes = True

                if phone_changes:
                    updates.append("phones")

                # Handle addresses
                mailing_address = row.get("MailingAddress", {})
                if isinstance(mailing_address, dict):
                    # Find or create mailing address
                    mailing = next(
                        (
                            addr
                            for addr in volunteer.addresses
                            if addr.type == ContactTypeEnum.personal and addr.primary
                        ),
                        None,
                    )
                    if not mailing:
                        mailing = Address(
                            contact_id=volunteer.id,
                            type=ContactTypeEnum.personal,
                            primary=True,
                        )
                        volunteer.addresses.append(mailing)
                        updates.append("ma")

                    # Update mailing address fields
                    if mailing.address_line1 != mailing_address.get("street", ""):
                        mailing.address_line1 = mailing_address.get("street", "")
                        updates.append("ms")
                    if mailing.city != mailing_address.get("city", ""):
                        mailing.city = mailing_address.get("city", "")
                        updates.append("mc")
                    if mailing.state != mailing_address.get("state", ""):
                        mailing.state = mailing_address.get("state", "")
                        updates.append("mst")
                    if mailing.zip_code != mailing_address.get("postalCode", ""):
                        mailing.zip_code = mailing_address.get("postalCode", "")
                        updates.append("mz")
                    if mailing.country != mailing_address.get("country", ""):
                        mailing.country = mailing_address.get("country", "")
                        updates.append("mco")

                # Handle work address if present
                work_address = row.get("npe01__Work_Address__c", "")
                if work_address:
                    work = next(
                        (
                            addr
                            for addr in volunteer.addresses
                            if addr.type == ContactTypeEnum.professional
                        ),
                        None,
                    )
                    if not work:
                        work = Address(
                            contact_id=volunteer.id, type=ContactTypeEnum.professional
                        )
                        volunteer.addresses.append(work)
                        updates.append("wa")

                    # Parse work address string
                    try:
                        parts = work_address.split(",")
                        if len(parts) >= 1:
                            work.address_line1 = parts[0].strip()
                        if len(parts) >= 2:
                            work.city = parts[1].strip()
                        if len(parts) >= 3:
                            state_zip = parts[2].strip().split()
                            if len(state_zip) >= 1:
                                work.state = state_zip[0]
                            if len(state_zip) >= 2:
                                work.zip_code = state_zip[1]
                        updates.append("wu")
                    except Exception as e:
                        print(
                            f"Error parsing work address for {volunteer.first_name} {volunteer.last_name}: {str(e)}"
                        )

                # Set address types based on primary/secondary preferences
                primary_type = (row.get("npe01__Primary_Address_Type__c") or "").lower()
                secondary_type = (
                    row.get("npe01__Secondary_Address_Type__c") or ""
                ).lower()

                for addr in volunteer.addresses:
                    is_home = addr.type == ContactTypeEnum.personal
                    is_work = addr.type == ContactTypeEnum.professional

                    # Set primary based on preference
                    if (primary_type == "home" and is_home) or (
                        primary_type == "work" and is_work
                    ):
                        addr.primary = True
                    elif (secondary_type == "home" and is_home) or (
                        secondary_type == "work" and is_work
                    ):
                        addr.primary = False

                # Handle Connector data
                connector_data = {
                    "active_subscription": (
                        row.get("Connector_Active_Subscription__c") or ""
                    )
                    .strip()
                    .upper()
                    or "NONE",
                    "active_subscription_name": (
                        row.get("Connector_Active_Subscription_Name__c") or ""
                    ).strip(),
                    "affiliations": (
                        row.get("Connector_Affiliations__c") or ""
                    ).strip(),
                    "industry": (row.get("Connector_Industry__c") or "").strip(),
                    "joining_date": (
                        row.get("Connector_Joining_Date__c") or ""
                    ).strip(),
                    "last_login_datetime": (
                        row.get("Connector_Last_Login_Date_Time__c") or ""
                    ).strip(),
                    "last_update_date": parse_date(
                        row.get("Connector_Last_Update_Date__c")
                    ),
                    "profile_link": (
                        row.get("Connector_Profile_Link__c") or ""
                    ).strip(),
                    "role": (row.get("Connector_Role__c") or "").strip(),
                    "signup_role": (row.get("Connector_SignUp_Role__c") or "").strip(),
                    "user_auth_id": (row.get("Connector_User_ID__c") or "").strip(),
                }

                # Create or update connector data
                if not volunteer.connector:
                    volunteer.connector = ConnectorData(volunteer_id=volunteer.id)
                    updates.append("con")

                # Update connector fields if they exist in Salesforce data
                if connector_data["active_subscription"] in [
                    e.name for e in ConnectorSubscriptionEnum
                ]:
                    if (
                        volunteer.connector.active_subscription
                        != ConnectorSubscriptionEnum[
                            connector_data["active_subscription"]
                        ]
                    ):
                        volunteer.connector.active_subscription = (
                            ConnectorSubscriptionEnum[
                                connector_data["active_subscription"]
                            ]
                        )
                        updates.append("cs")

                for field, value in connector_data.items():
                    if (
                        field != "active_subscription" and value
                    ):  # Skip active_subscription as it's handled above
                        current_value = getattr(volunteer.connector, field)
                        if current_value != value:
                            setattr(volunteer.connector, field, value)
                            updates.append(f"c{field[:2]}")

                success_count += 1
                created_count = created_count + 1 if is_new else created_count
                updated_count = (
                    updated_count + 1 if not is_new and updates else updated_count
                )

                # Compact status output for each record
                if i < 10 or i % 100 == 0:  # Show first 10 and every 100th
                    status = (
                        "NEW"
                        if is_new
                        else f"UPD({','.join(updates)})" if updates else "OK"
                    )
                    print(
                        f"[{i+1:4d}] {status}: {volunteer.first_name} {volunteer.last_name}"
                    )

            except Exception as e:
                error_count += 1
                error_detail = {
                    "name": f"{row.get('FirstName', '')} {row.get('LastName', '')}",
                    "salesforce_id": row.get("Id", ""),
                    "error": str(e),
                }
                errors.append(error_detail)
                print(
                    f"[{i+1:4d}] ERROR: {error_detail['name']} (ID: {error_detail['salesforce_id']}) - {str(e)[:100]}"
                )
                db.session.rollback()

        # Final summary
        print(f"\n{'='*60}")
        print(f"IMPORT COMPLETE")
        print(f"{'='*60}")
        print(f"Total Records: {total_records}")
        print(f"Successful:    {success_count}")
        print(f"Created:       {created_count}")
        print(f"Updated:       {updated_count}")
        print(f"Errors:        {error_count}")
        print(f"{'='*60}")

        if errors:
            print(f"\nERROR SUMMARY (showing first 10):")
            for i, error in enumerate(errors[:10]):
                print(f"  {i+1:2d}. {error['name']} (ID: {error['salesforce_id']})")
                print(f"      {error['error'][:80]}...")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        # Commit all successful changes
        try:
            db.session.commit()
            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {success_count} volunteers (Created: {created_count}, Updated: {updated_count}) with {error_count} errors",
                }
            )
        except Exception as e:
            db.session.rollback()
            return (
                jsonify(
                    {"success": False, "message": f"Database commit error: {str(e)}"}
                ),
                500,
            )

    except SalesforceAuthenticationFailed:
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/toggle-exclude-reports/<int:id>", methods=["POST"])
@login_required
def toggle_exclude_reports(id):
    """Toggle the exclude_from_reports field for a volunteer - Admin only"""
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin access required"}), 403

    try:
        volunteer = db.session.get(Volunteer, id)
        if not volunteer:
            return jsonify({"success": False, "message": "Volunteer not found"}), 404

        # Get the new value from the request
        data = request.get_json()
        exclude_from_reports = data.get("exclude_from_reports", False)

        # Update the field
        volunteer.exclude_from_reports = exclude_from_reports
        db.session.commit()

        status = "excluded from" if exclude_from_reports else "included in"
        return jsonify(
            {"success": True, "message": f"Volunteer {status} reports successfully"}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/update-local-statuses", methods=["POST"])
@login_required
def update_local_statuses():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        print("Starting local status update for all volunteers...")
        updated_count = 0
        error_count = 0

        # Get all volunteers
        volunteers = Volunteer.query.all()
        total_volunteers = len(volunteers)
        print(f"Found {total_volunteers} volunteers to process")

        # Progress tracking
        progress_interval = max(1, total_volunteers // 20)  # Show progress every 5%
        last_progress = 0

        for i, volunteer in enumerate(volunteers):
            try:
                # Progress indicator
                if i >= last_progress + progress_interval:
                    progress = (i / total_volunteers) * 100
                    print(
                        f"Progress: {progress:.1f}% ({i}/{total_volunteers}) - Updated: {updated_count}, Errors: {error_count}"
                    )
                    last_progress = i

                new_status = volunteer.calculate_local_status()
                if volunteer.local_status != new_status:
                    volunteer.local_status = new_status
                    volunteer.local_status_last_updated = datetime.utcnow()
                    updated_count += 1

                    # Show status changes for first 10 and every 100th
                    if updated_count <= 10 or updated_count % 100 == 0:
                        print(
                            f"[{i+1:4d}] STATUS: {volunteer.first_name} {volunteer.last_name} -> {new_status.name}"
                        )

            except Exception as e:
                error_count += 1
                print(
                    f"[{i+1:4d}] ERROR: {volunteer.first_name} {volunteer.last_name} - {str(e)[:80]}"
                )

        # Final summary
        print(f"\n{'='*50}")
        print(f"LOCAL STATUS UPDATE COMPLETE")
        print(f"{'='*50}")
        print(f"Total Volunteers: {total_volunteers}")
        print(f"Updated:         {updated_count}")
        print(f"Errors:          {error_count}")
        print(f"{'='*50}")

        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": f"Updated {updated_count} volunteer statuses with {error_count} errors",
            }
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Error updating local statuses: {str(e)}",
                }
            ),
            500,
        )


@volunteers_bp.route("/volunteers/<int:volunteer_id>/organizations")
@login_required
def get_organizations_json(volunteer_id):
    """Get organizations data for a specific volunteer as JSON"""
    try:
        from models import eagerload_volunteer_bundle

        volunteer = eagerload_volunteer_bundle(Volunteer.query).get_or_404(volunteer_id)
        organizations_data = []

        for vol_org in volunteer.volunteer_organizations:
            org_data = {
                "organization": {
                    "id": vol_org.organization.id,
                    "name": vol_org.organization.name,
                },
                "role": vol_org.role,
                "status": vol_org.status,
                "is_primary": vol_org.is_primary,
            }
            organizations_data.append(org_data)

        return jsonify(organizations_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

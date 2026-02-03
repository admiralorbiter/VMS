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
from models.recruitment_note import RecruitmentNote
from models.volunteer import (
    ConnectorData,
    ConnectorSubscriptionEnum,
    Engagement,
    EventParticipation,
    Skill,
    Volunteer,
    VolunteerSkill,
)
from routes.decorators import global_users_only
from routes.utils import (
    admin_required,
    get_email_addresses,
    get_phone_numbers,
    log_audit_action,
    parse_date,
    parse_skills,
)
from services.salesforce_mappers import (
    map_age_group,
    map_education_level,
    map_race_ethnicity,
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

            # Update skills - use no_autoflush to prevent identity map warnings
            with db.session.no_autoflush:
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
@global_users_only
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
                Volunteer.industry.ilike(search_term),
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
        status_val = current_filters["local_status"]
        # Map frontend values to Enum keys
        if status_val == "true":
            status_val = "local"
        elif status_val == "false":
            status_val = "non_local"

        try:
            status_enum = LocalStatusEnum[status_val]
            query = query.filter(Volunteer.local_status == status_enum)
        except KeyError:
            # If invalid status provided, return no results (or ignore)
            # Returning no results is safer for filtering
            query = query.filter(db.false())

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
            # Match the display calculation: attended_count + additional_volunteer_count
            # Exclude times_volunteered to avoid double counting (it may contain outdated Salesforce data)
            sort_column = (
                db.func.coalesce(attended_count_subq.c.attended_count, 0)
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
@global_users_only
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
@global_users_only
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
        "NoShow": "No-Show",
        "Cancelled": "Cancelled",
        "Canceled": "Cancelled",
        "canceled": "Cancelled",  # Handle lowercase version
        "cancelled": "Cancelled",  # Handle lowercase version
        "CANCELLED": "Cancelled",  # Handle uppercase version
        "CANCELED": "Cancelled",  # Handle uppercase version
        "Scheduled": "Scheduled",  # Keep scheduled for future events
        "scheduled": "Scheduled",  # Handle lowercase
        # Virtual-specific statuses
        "successfully completed": "Attended",
        "simulcast": "Attended",
        "technical difficulties": "No-Show",
        "local professional no-show": "No-Show",
        "pathful professional no-show": "No-Show",
        "teacher no-show": "No-Show",
        "teacher cancelation": "Cancelled",
        "teacher cancellation": "Cancelled",
        "Confirmed": "Attended",  # Could be pending or attended depending on your business logic
        # Additional variations
        "Present": "Attended",
        "Absent": "No-Show",
        "Did Not Attend": "No-Show",
        "DID NOT ATTEND": "No-Show",
        "Event Cancelled": "Cancelled",
        "Event Canceled": "Cancelled",
        "EVENT CANCELLED": "Cancelled",
        "EVENT CANCELED": "Cancelled",
    }

    # Initialize participation stats with empty lists
    participation_stats = {
        "Attended": [],
        "No-Show": [],
        "Cancelled": [],
        "Scheduled": [],
        "Unknown": [],
    }

    # Process each participation record
    for participation in participations:
        # Get status from participation record, fall back to event status
        status = participation.status

        # Debug: Print the original status for troubleshooting
        print(
            f"Processing participation: Event='{participation.event.title}', Status='{status}'"
        )

        # Get the event date first, handling virtual events that might store date differently
        event_date = None
        if participation.event.start_date:
            event_date = participation.event.start_date
        elif hasattr(participation.event, "date") and participation.event.date:
            event_date = participation.event.date
        else:
            # If no date available, create a default date to avoid errors
            event_date = datetime.now()

        # Determine if event is in the future
        is_future_event = event_date > datetime.now()

        # Handle "Scheduled" status with date-awareness BEFORE other mappings
        if status and status.lower() == "scheduled":
            # For past events with "Scheduled", mark as "Unknown" since status wasn't updated
            mapped_status = "Unknown" if not is_future_event else "Scheduled"
            print(
                f"Processing 'Scheduled' status for event '{participation.event.title}': "
                f"{'Future' if is_future_event else 'Past'} -> {mapped_status}"
            )
        # If status isn't directly usable, try mapping it
        elif status not in participation_stats:
            # Try using the mapping first
            mapped_status = status_mapping.get(status, None)

            # If not found, try lowercased version (handle case sensitivity)
            if mapped_status is None and status:
                mapped_status = status_mapping.get(status.lower(), None)

            # If still not found, try to infer from event title or other clues
            if mapped_status is None:
                event_title_lower = participation.event.title.lower()

                # Check for cancelled/canceled in title (common pattern: "canceled - Event Name")
                if any(
                    word in event_title_lower
                    for word in [
                        "canceled -",
                        "cancelled -",
                        "cancel -",
                        "cancelled:",
                        "canceled:",
                    ]
                ):
                    mapped_status = "Cancelled"
                    print(
                        f"Detected cancelled event from title: '{participation.event.title}'"
                    )
                elif any(
                    word in event_title_lower
                    for word in ["no-show", "no show", "noshow", "no-show:", "no show:"]
                ):
                    mapped_status = "No-Show"
                    print(
                        f"Detected no-show event from title: '{participation.event.title}'"
                    )
                elif any(
                    word in event_title_lower
                    for word in ["canceled", "cancelled", "cancel"]
                ):
                    mapped_status = "Cancelled"
                    print(
                        f"Detected cancelled event from title (partial match): '{participation.event.title}'"
                    )
                else:
                    # Only default to Unknown now (not Attended)
                    mapped_status = "Unknown"
                    print(
                        f"WARNING: Unknown status '{status}' for event '{participation.event.title}' - using Unknown"
                    )
        else:
            mapped_status = status

        print(f"Final mapped status: '{mapped_status}'")

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
        History.query.filter_by(contact_id=id, is_deleted=False)
        .order_by(History.activity_date.desc())
        .all()
    )

    # Debug: Print history count
    print(f"Found {len(histories)} history records for volunteer {id}")
    if histories:
        print(
            f"First history record: {histories[0].activity_type} - {histories[0].summary}"
        )

    # Create a dictionary of organization relationships for easy access in template
    org_relationships = {}
    for vol_org in volunteer.volunteer_organizations:
        org_relationships[vol_org.organization_id] = vol_org

    # Get recruitment notes for this volunteer
    recruitment_notes = (
        RecruitmentNote.query.filter_by(volunteer_id=id)
        .order_by(RecruitmentNote.created_at.desc())
        .all()
    )

    return render_template(
        "volunteers/view.html",
        volunteer=volunteer,
        emails=sorted(volunteer.emails, key=lambda x: x.primary, reverse=True),
        phones=sorted(volunteer.phones, key=lambda x: x.primary, reverse=True),
        participation_stats=participation_stats,
        histories=histories,
        org_relationships=org_relationships,
        recruitment_notes=recruitment_notes,
        now=datetime.now(),
    )


@volunteers_bp.route("/volunteers/edit/<int:id>", methods=["GET", "POST"])
@login_required
@global_users_only
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


@volunteers_bp.route("/volunteers/toggle-exclude-reports/<int:id>", methods=["POST"])
@login_required
@global_users_only
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


@volunteers_bp.route("/volunteers/update-local-status/<int:id>", methods=["POST"])
@login_required
@global_users_only
def update_local_status(id):
    """Update the local status for a volunteer - Available to all global users"""

    try:
        volunteer = db.session.get(Volunteer, id)
        if not volunteer:
            return jsonify({"success": False, "message": "Volunteer not found"}), 404

        # Get the new status from the request
        data = request.get_json()
        new_status = data.get("local_status", None)

        # Validate the status
        if new_status not in [e.name for e in LocalStatusEnum]:
            return jsonify({"success": False, "message": "Invalid local status"}), 400

        # Update the field
        old_status = volunteer.local_status.name if volunteer.local_status else "None"
        volunteer.local_status = LocalStatusEnum[new_status]
        volunteer.local_status_last_updated = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Local status updated from {old_status} to {new_status}",
                "new_status": new_status,
                "new_status_display": (
                    volunteer.local_status.value
                    if volunteer.local_status
                    else "Unknown"
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/update-local-statuses", methods=["POST"])
@login_required
@global_users_only
def update_local_statuses():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        from models.student import Student
        from models.teacher import Teacher

        print("Starting enhanced local status update for all contacts...")

        # Track statistics for each contact type
        stats = {
            "volunteers": {"total": 0, "updated": 0, "errors": 0},
            "teachers": {"total": 0, "updated": 0, "errors": 0},
            "students": {"total": 0, "updated": 0, "errors": 0},
        }

        # Process Volunteers with enhanced logic
        print("\n=== Processing Volunteers ===")
        volunteers = Volunteer.query.all()
        stats["volunteers"]["total"] = len(volunteers)
        print(f"Found {len(volunteers)} volunteers to process")

        for i, volunteer in enumerate(volunteers):
            try:
                new_status = volunteer.calculate_local_status()
                if volunteer.local_status != new_status:
                    old_status = (
                        volunteer.local_status.name
                        if volunteer.local_status
                        else "None"
                    )
                    volunteer.local_status = new_status
                    volunteer.local_status_last_updated = datetime.utcnow()
                    stats["volunteers"]["updated"] += 1

                    # Show status changes for first 10 and every 100th
                    if (
                        stats["volunteers"]["updated"] <= 10
                        or stats["volunteers"]["updated"] % 100 == 0
                    ):
                        print(
                            f"[{i+1:4d}] VOLUNTEER: {volunteer.first_name} {volunteer.last_name} -> {old_status} to {new_status.name}"
                        )

            except Exception as e:
                stats["volunteers"]["errors"] += 1
                print(
                    f"[{i+1:4d}] ERROR (Volunteer): {volunteer.first_name} {volunteer.last_name} - {str(e)[:80]}"
                )

        # Process Teachers with local assumptions
        print("\n=== Processing Teachers ===")
        teachers = Teacher.query.all()
        stats["teachers"]["total"] = len(teachers)
        print(f"Found {len(teachers)} teachers to process")

        for i, teacher in enumerate(teachers):
            try:
                new_status = teacher.calculate_local_status()
                if (
                    not hasattr(teacher, "local_status")
                    or teacher.local_status != new_status
                ):
                    old_status = getattr(teacher, "local_status", None)
                    old_status_name = old_status.name if old_status else "None"
                    teacher.local_status = new_status
                    teacher.local_status_last_updated = datetime.utcnow()
                    stats["teachers"]["updated"] += 1

                    # Show status changes for first 10 and every 100th
                    if (
                        stats["teachers"]["updated"] <= 10
                        or stats["teachers"]["updated"] % 100 == 0
                    ):
                        print(
                            f"[{i+1:4d}] TEACHER: {teacher.first_name} {teacher.last_name} -> {old_status_name} to {new_status.name}"
                        )

            except Exception as e:
                stats["teachers"]["errors"] += 1
                print(
                    f"[{i+1:4d}] ERROR (Teacher): {teacher.first_name} {teacher.last_name} - {str(e)[:80]}"
                )

        # Process Students with local assumptions
        print("\n=== Processing Students ===")
        students = Student.query.all()
        stats["students"]["total"] = len(students)
        print(f"Found {len(students)} students to process")

        for i, student in enumerate(students):
            try:
                new_status = student.calculate_local_status()
                if (
                    not hasattr(student, "local_status")
                    or student.local_status != new_status
                ):
                    old_status = getattr(student, "local_status", None)
                    old_status_name = old_status.name if old_status else "None"
                    student.local_status = new_status
                    student.local_status_last_updated = datetime.utcnow()
                    stats["students"]["updated"] += 1

                    # Show status changes for first 10 and every 100th
                    if (
                        stats["students"]["updated"] <= 10
                        or stats["students"]["updated"] % 100 == 0
                    ):
                        print(
                            f"[{i+1:4d}] STUDENT: {student.first_name} {student.last_name} -> {old_status_name} to {new_status.name}"
                        )

            except Exception as e:
                stats["students"]["errors"] += 1
                print(
                    f"[{i+1:4d}] ERROR (Student): {student.first_name} {student.last_name} - {str(e)[:80]}"
                )

        # Calculate totals
        total_contacts = sum(stat["total"] for stat in stats.values())
        total_updated = sum(stat["updated"] for stat in stats.values())
        total_errors = sum(stat["errors"] for stat in stats.values())

        # Final summary
        print(f"\n{'='*60}")
        print(f"ENHANCED LOCAL STATUS UPDATE COMPLETE")
        print(f"{'='*60}")
        print(
            f"Volunteers: {stats['volunteers']['total']:,} total, {stats['volunteers']['updated']:,} updated, {stats['volunteers']['errors']} errors"
        )
        print(
            f"Teachers:   {stats['teachers']['total']:,} total, {stats['teachers']['updated']:,} updated, {stats['teachers']['errors']} errors"
        )
        print(
            f"Students:   {stats['students']['total']:,} total, {stats['students']['updated']:,} updated, {stats['students']['errors']} errors"
        )
        print(f"{'='*60}")
        print(
            f"TOTALS:     {total_contacts:,} total, {total_updated:,} updated, {total_errors} errors"
        )
        print(f"{'='*60}")

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Enhanced local status update complete: {total_updated:,} contacts updated ({stats['volunteers']['updated']:,} volunteers, {stats['teachers']['updated']:,} teachers, {stats['students']['updated']:,} students) with {total_errors} errors",
                "stats": stats,
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
@global_users_only
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


# =============================================================================
# Recruitment Notes Routes (Global Volunteer Notes)
# =============================================================================


@volunteers_bp.route("/volunteers/<int:volunteer_id>/notes", methods=["POST"])
@login_required
@global_users_only
def add_volunteer_note(volunteer_id):
    """Add a recruitment note to a volunteer."""
    volunteer = db.session.get(Volunteer, volunteer_id)
    if not volunteer:
        abort(404)

    note_text = request.form.get("note", "").strip()
    outcome = request.form.get("outcome", "general")

    if not note_text:
        flash("Note text is required.", "error")
        return redirect(url_for("volunteers.view_volunteer", id=volunteer_id))

    try:
        note = RecruitmentNote(
            volunteer_id=volunteer_id,
            note=note_text,
            outcome=outcome,
            created_by=current_user.id,
        )
        db.session.add(note)
        db.session.commit()
        flash("Note added successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding note: {str(e)}", "error")

    return redirect(url_for("volunteers.view_volunteer", id=volunteer_id))


@volunteers_bp.route(
    "/volunteers/<int:volunteer_id>/notes/<int:note_id>", methods=["DELETE"]
)
@login_required
@global_users_only
def delete_volunteer_note(volunteer_id, note_id):
    """Delete a recruitment note."""
    note = db.session.get(RecruitmentNote, note_id)
    if not note or note.volunteer_id != volunteer_id:
        return jsonify({"success": False, "message": "Note not found"}), 404

    try:
        db.session.delete(note)
        db.session.commit()
        return jsonify({"success": True, "message": "Note deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

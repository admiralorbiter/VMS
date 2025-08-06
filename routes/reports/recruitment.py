from flask import Blueprint, render_template, request
from flask_login import login_required

from models import db

# from models.upcoming_events import UpcomingEvent  # Moved to microservice
from models.event import Event
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation, Skill, Volunteer, VolunteerSkill

# Create blueprint
recruitment_bp = Blueprint("recruitment", __name__)


def load_routes(bp):
    @bp.route("/reports/recruitment")
    @login_required
    def recruitment_tools():
        recruitment_tools = [
            {
                "title": "Quick Recruitment Tool",
                "description": "View upcoming unfilled events and search volunteers by skills and availability.",
                "icon": "fa-solid fa-bolt",
                "url": "/reports/recruitment/quick",
                "category": "Recruitment",
            },
            {
                "title": "Advanced Volunteer Search",
                "description": "Search volunteers using multiple filters including skills, past events, and volunteer history.",
                "icon": "fa-solid fa-search",
                "url": "/reports/recruitment/search",
                "category": "Recruitment",
            },
        ]

        return render_template("reports/recruitment_tools.html", tools=recruitment_tools)

    # Quick recruitment tool
    @bp.route("/reports/recruitment/quick")
    @login_required
    def quick_recruitment():
        # Upcoming events functionality moved to microservice
        upcoming_events = []

        # Get the search query from the request
        search_query = request.args.get("search", "").strip().lower()
        page = request.args.get("page", 1, type=int)
        per_page = 20  # Number of volunteers per page

        # Get the event type filter
        event_type_filter = request.args.get("event_type", "").strip()

        # Fix: Handle exclude_dia value from both checkbox and hidden input
        exclude_dia = request.args.get("exclude_dia")
        exclude_dia = exclude_dia == "1" or exclude_dia == "true" or exclude_dia == "True"

        # Initialize volunteers_data and pagination as None
        volunteers_data = []
        pagination = None

        # Only query volunteers if there is a search query
        if search_query:
            # Split search query into words
            search_terms = search_query.split()

            volunteers_query = (
                Volunteer.query.outerjoin(Volunteer.volunteer_organizations)
                .outerjoin(VolunteerOrganization.organization)
                .outerjoin(EventParticipation, EventParticipation.volunteer_id == Volunteer.id)
                .filter(
                    db.or_(
                        db.and_(*[db.or_(Volunteer.first_name.ilike(f"%{term}%"), Volunteer.last_name.ilike(f"%{term}%")) for term in search_terms]),
                        Volunteer.title.ilike(f"%{search_query}%"),
                        Organization.name.ilike(f"%{search_query}%"),
                        Volunteer.skills.any(Skill.name.ilike(f"%{search_query}%")),
                    )
                )
            )

            # Add pagination to the volunteers query
            paginated_volunteers = (
                volunteers_query.add_columns(
                    db.func.count(EventParticipation.id).label("participation_count"), db.func.max(EventParticipation.event_id).label("last_event")
                )
                .group_by(Volunteer.id)
                .paginate(page=page, per_page=per_page, error_out=False)
            )

            # Store pagination object for template
            pagination = paginated_volunteers

            # Populate volunteers_data based on the paginated results
            for volunteer, participation_count, last_event in paginated_volunteers.items:
                volunteers_data.append(
                    {
                        "id": volunteer.id,
                        "name": f"{volunteer.first_name} {volunteer.last_name}",
                        "email": volunteer.primary_email,
                        "title": volunteer.title,
                        "organization": {
                            "name": volunteer.volunteer_organizations[0].organization.name if volunteer.volunteer_organizations else None,
                            "id": volunteer.volunteer_organizations[0].organization.id if volunteer.volunteer_organizations else None,
                        },
                        "participation_count": participation_count,
                        "skills": [skill.name for skill in volunteer.skills],
                        "industry": volunteer.industry,
                        "last_mailchimp_date": volunteer.last_mailchimp_activity_date,
                        "last_volunteer_date": volunteer.last_volunteer_date,
                        "last_email_date": volunteer.last_email_date,
                        "salesforce_contact_url": volunteer.salesforce_contact_url,
                    }
                )

        # Prepare events_data based on UpcomingEvent model
        events_data = []
        for event in upcoming_events:
            # Extract the URL from the HTML anchor tag if it exists
            registration_link = None
            if event.registration_link and "href=" in event.registration_link:
                start = event.registration_link.find('href="') + 6
                end = event.registration_link.find('"', start)
                if start > 5 and end > start:  # ensure we found both quotes
                    registration_link = event.registration_link[start:end]

            events_data.append(
                {
                    "title": event.name,
                    "description": event.event_type,
                    "start_date": event.start_date,
                    "type": event.event_type,
                    "location": event.registration_link,
                    "total_slots": event.available_slots,
                    "filled_slots": event.filled_volunteer_jobs,
                    "remaining_slots": event.available_slots - event.filled_volunteer_jobs,
                    "skills_needed": [],
                    "status": "Upcoming",
                    "registration_link": registration_link,
                }
            )

        return render_template(
            "reports/recruitment_report.html",
            events=events_data,
            volunteers=volunteers_data,
            search_query=search_query,
            event_types=[],  # Upcoming events moved to microservice
            exclude_dia=exclude_dia,
            event_type_filter=event_type_filter,
            pagination=pagination,
            page=page,
        )

    # Advanced volunteer search
    @bp.route("/reports/recruitment/search")
    @login_required
    def recruitment_search():
        # Get search query, pagination, and sorting parameters
        search_query = request.args.get("search", "").strip()
        page = request.args.get("page", 1, type=int)
        per_page = 20
        sort_by = request.args.get("sort", "name")
        order = request.args.get("order", "asc")
        search_mode = request.args.get("search_mode", "wide")  # Default to wide search

        # Base query joining necessary tables
        query = (
            Volunteer.query.outerjoin(VolunteerOrganization)
            .outerjoin(Organization)
            .outerjoin(VolunteerSkill)
            .outerjoin(Skill)
            .outerjoin(EventParticipation)
            .outerjoin(Event)
        )

        # Apply search if provided
        if search_query:
            # Split search query into terms and remove empty strings
            search_terms = [term.strip() for term in search_query.split() if term.strip()]

            if search_mode == "wide":
                # OR mode: Match any term across all fields
                search_conditions = []
                for term in search_terms:
                    search_conditions.append(
                        db.or_(
                            Volunteer.first_name.ilike(f"%{term}%"),
                            Volunteer.last_name.ilike(f"%{term}%"),
                            Organization.name.ilike(f"%{term}%"),
                            Skill.name.ilike(f"%{term}%"),
                            Event.title.ilike(f"%{term}%"),
                        )
                    )
                query = query.filter(db.or_(*search_conditions))
            else:
                # Narrow mode: Must match all terms
                for term in search_terms:
                    query = query.filter(
                        db.or_(
                            Volunteer.first_name.ilike(f"%{term}%"),
                            Volunteer.last_name.ilike(f"%{term}%"),
                            Organization.name.ilike(f"%{term}%"),
                            Skill.name.ilike(f"%{term}%"),
                            Event.title.ilike(f"%{term}%"),
                        )
                    )

        # Apply sorting
        if sort_by == "name":
            if order == "asc":
                query = query.order_by(Volunteer.first_name, Volunteer.last_name)
            else:
                query = query.order_by(db.desc(Volunteer.first_name), db.desc(Volunteer.last_name))
        elif sort_by == "organization":
            if order == "asc":
                query = query.order_by(Organization.name)
            else:
                query = query.order_by(db.desc(Organization.name))
        elif sort_by == "last_email":
            if order == "asc":
                query = query.order_by(Volunteer.last_non_internal_email_date)
            else:
                query = query.order_by(db.desc(Volunteer.last_non_internal_email_date))
        elif sort_by == "last_volunteer":
            if order == "asc":
                query = query.order_by(Volunteer.last_volunteer_date)
            else:
                query = query.order_by(db.desc(Volunteer.last_volunteer_date))
        elif sort_by == "times_volunteered":
            subquery = (
                db.session.query(EventParticipation.volunteer_id, db.func.count(EventParticipation.id).label("volunteer_count"))
                .group_by(EventParticipation.volunteer_id)
                .subquery()
            )

            query = query.outerjoin(subquery, Volunteer.id == subquery.c.volunteer_id).order_by(
                db.desc(subquery.c.volunteer_count) if order == "desc" else subquery.c.volunteer_count
            )

        # Add pagination
        pagination = query.distinct().paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            "reports/recruitment_search.html",
            volunteers=pagination.items,
            search_query=search_query,
            pagination=pagination,
            sort_by=sort_by,
            order=order,
            search_mode=search_mode,  # Pass the search mode to the template
        )

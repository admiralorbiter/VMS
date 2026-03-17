import csv
import io
from datetime import datetime, timezone

from flask import Blueprint, Response, render_template, request
from flask_login import login_required

from models import db, eagerload_volunteer_bundle
from models.contact import LocalStatusEnum

# from models.upcoming_events import UpcomingEvent  # Moved to microservice
from models.event import Event, EventType
from models.organization import Organization, VolunteerOrganization
from models.reports import RecruitmentCandidatesCache
from models.volunteer import EventParticipation, Skill, Volunteer, VolunteerSkill
from services.recruitment_scoring_service import (
    derive_keywords,
    derive_type_keywords,
    local_boost,
    recency_boost,
)

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
            {
                "title": "Event Candidate Matches",
                "description": "Ranked volunteer recommendations by event with explainable reasons.",
                "icon": "fa-solid fa-user-check",
                "url": "/reports/recruitment/candidates",
                "category": "Recruitment",
            },
        ]

        return render_template(
            "reports/recruitment/recruitment_tools.html", tools=recruitment_tools
        )

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
        exclude_dia = (
            exclude_dia == "1" or exclude_dia == "true" or exclude_dia == "True"
        )

        # Initialize volunteers_data and pagination as None
        volunteers_data = []
        pagination = None

        # Only query volunteers if there is a search query
        if search_query:
            # Split search query into words
            search_terms = search_query.split()

            volunteers_query = (
                eagerload_volunteer_bundle(Volunteer.query)
                .outerjoin(Volunteer.volunteer_organizations)
                .outerjoin(VolunteerOrganization.organization)
                .outerjoin(
                    EventParticipation, EventParticipation.volunteer_id == Volunteer.id
                )
                .filter(
                    db.or_(
                        db.and_(
                            *[
                                db.or_(
                                    Volunteer.first_name.ilike(f"%{term}%"),
                                    Volunteer.last_name.ilike(f"%{term}%"),
                                )
                                for term in search_terms
                            ]
                        ),
                        Volunteer.title.ilike(f"%{search_query}%"),
                        Organization.name.ilike(f"%{search_query}%"),
                        Volunteer.skills.any(Skill.name.ilike(f"%{search_query}%")),
                    )
                )
            )

            # Add pagination to the volunteers query
            paginated_volunteers = (
                volunteers_query.add_columns(
                    db.func.count(EventParticipation.id).label("participation_count"),
                    db.func.max(EventParticipation.event_id).label("last_event"),
                )
                .group_by(Volunteer.id)
                .paginate(page=page, per_page=per_page, error_out=False)
            )

            # Store pagination object for template
            pagination = paginated_volunteers

            # Populate volunteers_data based on the paginated results
            for (
                volunteer,
                participation_count,
                last_event,
            ) in paginated_volunteers.items:
                volunteers_data.append(
                    {
                        "id": volunteer.id,
                        "name": f"{volunteer.first_name} {volunteer.last_name}",
                        "email": volunteer.primary_email,
                        "title": volunteer.title,
                        "organization": {
                            "name": (
                                volunteer.volunteer_organizations[0].organization.name
                                if volunteer.volunteer_organizations
                                else None
                            ),
                            "id": (
                                volunteer.volunteer_organizations[0].organization.id
                                if volunteer.volunteer_organizations
                                else None
                            ),
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
            if event.registration_link:
                from services.salesforce.utils import extract_href_from_html

                registration_link = extract_href_from_html(event.registration_link)

            events_data.append(
                {
                    "title": event.name,
                    "description": event.event_type,
                    "start_date": event.start_date,
                    "type": event.event_type,
                    "location": event.registration_link,
                    "total_slots": event.available_slots,
                    "filled_slots": event.filled_volunteer_jobs,
                    "remaining_slots": event.available_slots
                    - event.filled_volunteer_jobs,
                    "skills_needed": [],
                    "status": "Upcoming",
                    "registration_link": registration_link,
                }
            )

        return render_template(
            "reports/recruitment/recruitment_report.html",
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
        connector_only = request.args.get(
            "connector_only", type=bool
        )  # Filter for connector profiles only

        # Base query joining necessary tables
        query = (
            eagerload_volunteer_bundle(Volunteer.query)
            .outerjoin(VolunteerOrganization)
            .outerjoin(Organization)
            .outerjoin(VolunteerSkill)
            .outerjoin(Skill)
            .outerjoin(EventParticipation)
            .outerjoin(Event)
        )

        # Apply search if provided
        if search_query:
            # Split search query into terms and remove empty strings
            search_terms = [
                term.strip() for term in search_query.split() if term.strip()
            ]

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
                            # Enhanced search fields
                            Volunteer.title.ilike(f"%{term}%"),
                            Volunteer.industry.ilike(f"%{term}%"),
                            db.cast(Volunteer.local_status, db.String).ilike(
                                f"%{term}%"
                            ),
                            db.cast(Event.type, db.String).ilike(f"%{term}%"),
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
                            # Enhanced search fields
                            Volunteer.title.ilike(f"%{term}%"),
                            Volunteer.industry.ilike(f"%{term}%"),
                            db.cast(Volunteer.local_status, db.String).ilike(
                                f"%{term}%"
                            ),
                            db.cast(Event.type, db.String).ilike(f"%{term}%"),
                        )
                    )

        # Apply connector filter if requested
        if connector_only:
            from models.pathful_import import PathfulUserProfile

            query = query.filter(
                Volunteer.pathful_profile.has(
                    PathfulUserProfile.pathful_user_id.isnot(None)
                )
            )

        # Apply sorting
        if sort_by == "name":
            if order == "asc":
                query = query.order_by(Volunteer.first_name, Volunteer.last_name)
            else:
                query = query.order_by(
                    db.desc(Volunteer.first_name), db.desc(Volunteer.last_name)
                )
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
                db.session.query(
                    EventParticipation.volunteer_id,
                    db.func.count(EventParticipation.id).label("volunteer_count"),
                )
                .filter(
                    EventParticipation.status.in_(
                        ["Attended", "Completed", "Successfully Completed"]
                    )
                )
                .group_by(EventParticipation.volunteer_id)
                .subquery()
            )

            query = query.outerjoin(
                subquery, Volunteer.id == subquery.c.volunteer_id
            ).order_by(
                db.desc(subquery.c.volunteer_count)
                if order == "desc"
                else subquery.c.volunteer_count
            )

        # Add pagination
        pagination = query.distinct().paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template(
            "reports/recruitment/recruitment_search.html",
            volunteers=pagination.items,
            search_query=search_query,
            pagination=pagination,
            sort_by=sort_by,
            order=order,
            search_mode=search_mode,  # Pass the search mode to the template
            connector_only=connector_only,  # Pass the connector filter state
        )

    @bp.route("/reports/recruitment/search.csv")
    @login_required
    def recruitment_search_csv():
        """CSV export of advanced search results (FR-RECRUIT-307).

        Accepts the same query params as recruitment_search() but returns
        all matching volunteers as a downloadable CSV file with additional
        columns (email, activity dates) for outreach purposes.
        """
        search_query = request.args.get("search", "").strip()
        sort_by = request.args.get("sort", "name")
        order = request.args.get("order", "asc")
        search_mode = request.args.get("search_mode", "wide")
        connector_only = request.args.get("connector_only", type=bool)

        # Build the same query as the HTML search route
        query = (
            eagerload_volunteer_bundle(Volunteer.query)
            .outerjoin(VolunteerOrganization)
            .outerjoin(Organization)
            .outerjoin(VolunteerSkill)
            .outerjoin(Skill)
            .outerjoin(EventParticipation)
            .outerjoin(Event)
        )

        if search_query:
            search_terms = [
                term.strip() for term in search_query.split() if term.strip()
            ]

            if search_mode == "wide":
                search_conditions = []
                for term in search_terms:
                    search_conditions.append(
                        db.or_(
                            Volunteer.first_name.ilike(f"%{term}%"),
                            Volunteer.last_name.ilike(f"%{term}%"),
                            Organization.name.ilike(f"%{term}%"),
                            Skill.name.ilike(f"%{term}%"),
                            Event.title.ilike(f"%{term}%"),
                            Volunteer.title.ilike(f"%{term}%"),
                            Volunteer.industry.ilike(f"%{term}%"),
                            db.cast(Volunteer.local_status, db.String).ilike(
                                f"%{term}%"
                            ),
                            db.cast(Event.type, db.String).ilike(f"%{term}%"),
                        )
                    )
                query = query.filter(db.or_(*search_conditions))
            else:
                for term in search_terms:
                    query = query.filter(
                        db.or_(
                            Volunteer.first_name.ilike(f"%{term}%"),
                            Volunteer.last_name.ilike(f"%{term}%"),
                            Organization.name.ilike(f"%{term}%"),
                            Skill.name.ilike(f"%{term}%"),
                            Event.title.ilike(f"%{term}%"),
                            Volunteer.title.ilike(f"%{term}%"),
                            Volunteer.industry.ilike(f"%{term}%"),
                            db.cast(Volunteer.local_status, db.String).ilike(
                                f"%{term}%"
                            ),
                            db.cast(Event.type, db.String).ilike(f"%{term}%"),
                        )
                    )

        if connector_only:
            from models.pathful_import import PathfulUserProfile

            query = query.filter(
                Volunteer.pathful_profile.has(
                    PathfulUserProfile.pathful_user_id.isnot(None)
                )
            )

        # Apply sorting (same as HTML route)
        if sort_by == "name":
            if order == "asc":
                query = query.order_by(Volunteer.first_name, Volunteer.last_name)
            else:
                query = query.order_by(
                    db.desc(Volunteer.first_name), db.desc(Volunteer.last_name)
                )
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

        # Fetch all results (no pagination for CSV export)
        volunteers = query.distinct().all()

        # Build CSV output
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Name",
                "Email",
                "Title",
                "Organization",
                "Skills",
                "Last Non-Internal Email Date",
                "Last Volunteer Date",
                "Times Volunteered",
            ]
        )

        for v in volunteers:
            writer.writerow(
                [
                    v.full_name,
                    v.primary_email or "",
                    v.title or "",
                    (
                        ", ".join(org.name for org in v.organizations)
                        if v.organizations
                        else ""
                    ),
                    "; ".join(skill.name for skill in v.skills) if v.skills else "",
                    (
                        v.last_non_internal_email_date.strftime("%Y-%m-%d")
                        if v.last_non_internal_email_date
                        else ""
                    ),
                    (
                        v.last_volunteer_date.strftime("%Y-%m-%d")
                        if v.last_volunteer_date
                        else ""
                    ),
                    v.total_times_volunteered,
                ]
            )

        csv_data = output.getvalue()

        # Build descriptive filename
        if search_query:
            clean_query = "".join(c for c in search_query if c.isalnum() or c in " -_")[
                :30
            ].strip()
            filename = f"volunteer_search_{clean_query}.csv"
        else:
            filename = "volunteer_search_export.csv"

        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={filename}",
        }
        return Response(csv_data, headers=headers)

    @bp.route("/reports/recruitment/candidates")
    @login_required
    def recruitment_candidates():
        """Event-based candidate list with enhanced keyword matching and transparent scoring.

        Query params:
            - event_id: int (optional). If missing, show an event selector.
            - limit: int (optional, default 100)
            - min_score: float (optional, default None)
            - custom_keywords: str (optional, comma-separated custom keywords)
        """
        from sqlalchemy import and_, or_

        event_id = request.args.get("event_id", type=int)
        limit = request.args.get("limit", 100, type=int)
        min_score = request.args.get("min_score", type=float)
        custom_keywords = request.args.get("custom_keywords", "").strip()

        # If no event chosen, show simple selector of upcoming/recent events
        if not event_id:
            # Upcoming (next 180 days) or recent past (last 30 days) for convenience
            now = datetime.now(timezone.utc)
            upcoming = (
                Event.query.filter(Event.start_date >= now)
                .order_by(Event.start_date.asc())
                .limit(50)
                .all()
            )
            recent = (
                Event.query.filter(Event.start_date < now)
                .order_by(Event.start_date.desc())
                .limit(50)
                .all()
            )
            return render_template(
                "reports/recruitment/recruitment_candidates.html",
                event=None,
                candidates=[],
                upcoming_events=upcoming,
                recent_events=recent,
                limit=limit,
                min_score=min_score,
            )

        event = Event.query.get(event_id)
        if not event:
            return (
                render_template(
                    "reports/recruitment/recruitment_candidates.html",
                    event=None,
                    candidates=[],
                    error=f"Event {event_id} not found",
                    upcoming_events=[],
                    recent_events=[],
                    limit=limit,
                    min_score=min_score,
                ),
                404,
            )

        # Keyword derivation functions imported from services.recruitment_scoring_service

        # Try cache first unless refresh requested
        refresh_requested = request.args.get("refresh", "0") == "1"

        cached_row = None
        if not refresh_requested:
            try:
                cached_row = RecruitmentCandidatesCache.query.filter_by(
                    event_id=event_id
                ).first()
            except Exception:
                cached_row = None

        # Initialize keyword variables
        kw_data = {}
        kw_explanations = {}
        kw = set()

        if cached_row:
            all_candidates = cached_row.candidates_data or []
            # For cached results, we need to reconstruct keywords for display
            try:
                kw_data, kw_explanations = derive_keywords(event, custom_keywords)
                for category, words in kw_data.items():
                    kw.update(words)
            except Exception as e:
                # Fallback to basic keywords if derivation fails
                kw_data = {
                    "type": (
                        derive_type_keywords(event.type)
                        if hasattr(event, "type")
                        else []
                    )
                }
                # Add custom keywords to fallback if present
                if custom_keywords:
                    custom_kw_list = [
                        kw.strip().lower()
                        for kw in custom_keywords.split(",")
                        if kw.strip()
                    ]
                    if custom_kw_list:
                        kw_data["custom"] = custom_kw_list
                        kw_explanations = {
                            "type": {
                                "explanation": f'Event type: {event.type.value.replace("_", " ").title()}',
                                "keywords": kw_data["type"],
                            },
                            "custom": {
                                "explanation": f"User-specified custom keywords: '{custom_keywords}'",
                                "keywords": custom_kw_list,
                            },
                        }
                        kw = set(kw_data["type"] + custom_kw_list)
                    else:
                        kw_explanations = {
                            "type": {
                                "explanation": f'Event type: {event.type.value.replace("_", " ").title()}',
                                "keywords": kw_data["type"],
                            }
                        }
                        kw = set(kw_data["type"])
                else:
                    kw_explanations = {
                        "type": {
                            "explanation": f'Event type: {event.type.value.replace("_", " ").title()}',
                            "keywords": kw_data["type"],
                        }
                    }
                    kw = set(kw_data["type"])
        else:
            # Build keyword set from event title/description and type
            # Get enhanced keywords and explanations
            kw_data, kw_explanations = derive_keywords(event, custom_keywords)

            # Flatten keywords for the existing logic
            kw = set()
            for category, words in kw_data.items():
                kw.update(words)

        # Governance filters: exclude do-not-contact and email opt-outs
        base_query = Volunteer.query

        # Build a prefilter when keywords exist to reduce candidate pool size
        if kw:
            ors = []
            for term in kw:
                like = f"%{term}%"
                ors.append(
                    or_(
                        Volunteer.title.ilike(like),
                        Volunteer.department.ilike(like),
                        Volunteer.industry.ilike(like),
                        Volunteer.skills.any(Skill.name.ilike(like)),
                    )
                )
            base_query = base_query.filter(or_(*ors))

        # Apply governance and status filters
        try:
            base_query = base_query.filter(
                and_(
                    or_(Volunteer.status == None, Volunteer.status != "inactive"),
                    or_(
                        Volunteer.do_not_contact == False,
                        Volunteer.do_not_contact.is_(False),
                    ),
                    or_(
                        Volunteer.email_opt_out == False,
                        Volunteer.email_opt_out.is_(False),
                    ),
                    or_(
                        Volunteer.exclude_from_reports == False,
                        Volunteer.exclude_from_reports.is_(False),
                    ),
                )
            )
        except Exception:
            # Fallback if inherited contact fields are not directly mapped on Volunteer in this ORM context
            pass

        volunteers = eagerload_volunteer_bundle(base_query).limit(2000).all()

        # Precompute past participation by event type for scoring
        same_type_counts = {
            row[0]: row[1]
            for row in (
                db.session.query(
                    EventParticipation.volunteer_id,
                    db.func.count(EventParticipation.id),
                )
                .join(Event, Event.id == EventParticipation.event_id)
                .filter(Event.type == event.type)
                .group_by(EventParticipation.volunteer_id)
                .all()
            )
        }

        # Precompute overall participation frequency for all events
        total_participation_counts = {
            row[0]: row[1]
            for row in (
                db.session.query(
                    EventParticipation.volunteer_id,
                    db.func.count(EventParticipation.id),
                )
                .group_by(EventParticipation.volunteer_id)
                .all()
            )
        }

        def score_and_reasons(v: Volunteer) -> tuple[float, list[str], str]:
            score = 0.0
            reasons: list[str] = []
            breakdown_lines: list[str] = []

            # Same event type participation
            stc = same_type_counts.get(v.id, 0)
            if stc > 0:
                comp = 1.0
                score += comp
                et = str(event.type).split(".")[-1].replace("_", " ").title()
                reasons.append(f"Past {et} event ({stc}x)")
                breakdown_lines.append(f"Past {et} events: +{comp:.2f} (count {stc})")

            # Title/department keyword match
            title_text = f"{(v.title or '').lower()} {(v.department or '').lower()} {(v.industry or '').lower()}"
            if kw and any(k in title_text for k in kw):
                comp = 0.6
                score += comp
                hits = [k for k in kw if k in title_text]
                if hits:
                    reasons.append(f"Title/industry match: {', '.join(hits[:3])}")
                    breakdown_lines.append(
                        f"Title/industry keyword ({', '.join(hits[:3])}): +{comp:.2f}"
                    )
                else:
                    breakdown_lines.append(f"Title/industry keyword: +{comp:.2f}")

            # Skill match
            skill_names = {
                s.name.lower()
                for s in getattr(v, "skills", [])
                if getattr(s, "name", None)
            }
            skill_overlap = kw.intersection(skill_names) if kw else set()
            if skill_overlap:
                comp = 0.8
                score += comp
                skills_txt = ", ".join(sorted(skill_overlap))
                reasons.append(f"Skills: {skills_txt}")
                breakdown_lines.append(f"Skill overlap ({skills_txt}): +{comp:.2f}")

            # Connector profile boost (for all events - connector profiles indicate established volunteers)
            if hasattr(v, "connector") and v.connector and v.connector.user_auth_id:
                comp = 0.4
                score += comp
                reasons.append("Has connector profile")
                breakdown_lines.append(f"Connector profile: +{comp:.2f}")

            # Recency boost
            rb = recency_boost(getattr(v, "last_volunteer_date", None))
            if rb > 0:
                score += rb
                reasons.append("Recent activity")
                breakdown_lines.append(f"Recency: +{rb:.2f}")

            # Locality
            lb = local_boost(getattr(v, "local_status", None))
            if lb > 0:
                score += lb
                reasons.append("Local/nearby")
                breakdown_lines.append(f"Locality: +{lb:.2f}")

            # Frequency boost with diminishing returns
            freq = total_participation_counts.get(v.id, 0)
            if freq >= 10:
                comp = 0.3
                score += comp
                reasons.append(f"Frequent volunteer ({freq} events)")
                breakdown_lines.append(f"Frequency ({freq}): +{comp:.2f}")
            elif freq >= 5:
                comp = 0.2
                score += comp
                reasons.append(f"Frequent volunteer ({freq} events)")
                breakdown_lines.append(f"Frequency ({freq}): +{comp:.2f}")
            elif freq >= 2:
                comp = 0.1
                score += comp
                reasons.append(f"Volunteer history ({freq} events)")
                breakdown_lines.append(f"Frequency ({freq}): +{comp:.2f}")

            breakdown = "\n".join(breakdown_lines)
            return round(score, 3), reasons, breakdown

        candidates = []
        for v in volunteers:
            score, reasons, breakdown = score_and_reasons(v)
            # Derive organization display
            org_name = getattr(v, "organization_name", None)
            if not org_name:
                try:
                    if getattr(v, "volunteer_organizations", None):
                        org_name = v.volunteer_organizations[0].organization.name
                except Exception:
                    org_name = None

            candidates.append(
                {
                    "id": v.id,
                    "name": f"{getattr(v, 'first_name', '')} {getattr(v, 'last_name', '')}".strip(),
                    "email": getattr(v, "primary_email", None),
                    "title": v.title,
                    "organization": org_name,
                    "skills": sorted(
                        [
                            s.name
                            for s in getattr(v, "skills", [])
                            if getattr(s, "name", None)
                        ]
                    )[:8],
                    "score": score,
                    "reasons": reasons,
                    "breakdown": breakdown,
                    # Add connector profile information
                    "connector_profile_url": (
                        getattr(v.connector, "connector_profile_url", None)
                        if hasattr(v, "connector") and v.connector
                        else None
                    ),
                    "has_connector_profile": bool(
                        getattr(v, "connector", None)
                        and getattr(v.connector, "user_auth_id", None)
                    ),
                }
            )

        # Sort and persist full list (unfiltered by min_score/limit)
        candidates.sort(key=lambda c: c["score"], reverse=True)
        try:
            existing = RecruitmentCandidatesCache.query.filter_by(
                event_id=event_id
            ).first()
            if existing:
                existing.candidates_data = candidates
                existing.last_updated = datetime.now(timezone.utc)
            else:
                db.session.add(
                    RecruitmentCandidatesCache(
                        event_id=event_id, candidates_data=candidates
                    )
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
        all_candidates = candidates

        # Apply runtime filters
        candidates = [
            c for c in all_candidates if (min_score is None or c["score"] >= min_score)
        ][: limit or 100]

        # Add keyword criteria to event object for template display
        event.keyword_criteria = kw_explanations
        event.debug_keywords = list(kw)  # For debug display

        return render_template(
            "reports/recruitment/recruitment_candidates.html",
            event=event,
            candidates=candidates,
            upcoming_events=[],
            recent_events=[],
            limit=limit,
            min_score=min_score,
            last_refreshed=(
                cached_row.last_updated if cached_row else datetime.now(timezone.utc)
            ),
            is_cached=bool(cached_row),
        )

    @bp.route("/reports/recruitment/candidates.csv")
    @login_required
    def recruitment_candidates_csv():
        """CSV export of event-based candidates using the same scoring heuristics."""

        event_id = request.args.get("event_id", type=int)
        limit = request.args.get("limit", 100, type=int)
        min_score = request.args.get("min_score", type=float)
        custom_keywords = request.args.get("custom_keywords", "").strip()

        event = Event.query.get(event_id) if event_id else None
        if not event:
            return Response("event_id is required", status=400)

        # Use same cache as HTML route
        refresh_requested = request.args.get("refresh", "0") == "1"
        cached_row = None
        if not refresh_requested:
            cached_row = RecruitmentCandidatesCache.query.filter_by(
                event_id=event_id
            ).first()

        if cached_row:
            all_candidates = cached_row.candidates_data or []
        else:
            # For CSV, we'll use a simplified approach
            all_candidates = []

        # Apply runtime filters
        candidates = [
            c for c in all_candidates if (min_score is None or c["score"] >= min_score)
        ][: limit or 100]

        rows = [
            [
                c["id"],
                c["name"],
                c.get("email"),
                c.get("title"),
                c.get("organization"),
                "; ".join(c.get("skills", [])[:12]),
                f"{c['score']:.3f}",
                " | ".join(c.get("reasons", [])),
            ]
            for c in candidates
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Volunteer ID",
                "Name",
                "Email",
                "Title",
                "Organization",
                "Skills",
                "Score",
                "Reasons",
            ]
        )
        writer.writerows(rows)
        csv_data = output.getvalue()

        # Create filename with custom keywords if present
        if custom_keywords:
            # Clean custom keywords for filename (remove special chars, limit length)
            clean_keywords = "".join(
                c for c in custom_keywords if c.isalnum() or c in " -_"
            )[:30]
            filename = f"event_{event.id}_custom_{clean_keywords}_candidates.csv"
        else:
            filename = f"event_{event.id}_candidates.csv"

        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={filename}",
        }
        return Response(csv_data, headers=headers)

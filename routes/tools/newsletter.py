"""
Newsletter Formatter Tool
=========================

Provides a UI for generating formatted newsletter text from upcoming Pathful
virtual sessions **and** in-person career exploration events.  Users select
which sessions to include, the tool groups them appropriately, and produces
copy-paste-ready text.

Endpoints:
    GET  /tools/newsletter-formatter                         → Render the formatter page
    GET  /tools/newsletter-formatter/sessions                → JSON API — upcoming virtual sessions
    GET  /tools/newsletter-formatter/in-person-sessions      → JSON API — upcoming in-person events
    GET  /tools/newsletter-formatter/search-virtual-sessions → JSON API — search virtual sessions
"""

import re
from datetime import datetime, timezone

from flask import current_app, jsonify, render_template, request
from flask_login import login_required

from models.event import Event, EventStatus, EventType, db
from routes.tools import tools_bp
from services.salesforce.utils import extract_href_from_html

# Base URL for constructing per-session Nepris links
NEPRIS_SESSION_BASE_URL = "https://prepkc.nepris.com/app/sessions/"

# ---------------------------------------------------------------------------
# Grade-level parsing (virtual sessions)
# ---------------------------------------------------------------------------

# Ordered list of (regex_pattern, list_of_grade_keys) pairs.
# First match wins.  Grade keys map to display headers.
_GRADE_PATTERNS = [
    # Multi-grade spans first (more specific)
    (r"^K-2:", ["Kindergarten", "First Grade", "Second Grade"]),
    (r"^K-1:", ["Kindergarten", "First Grade"]),
    (r"^2-5:", ["Second Grade", "Third Grade", "Fourth Grade", "Fifth Grade"]),
    (r"^2-3:", ["Second Grade", "Third Grade"]),
    (r"^4-5\s*Grade", ["Fourth Grade", "Fifth Grade"]),
    # Single grades
    (r"^K:", ["Kindergarten"]),
    (r"^1st\s*Grade:", ["First Grade"]),
    (r"^2nd\s*Grade:", ["Second Grade"]),
    (r"^3rd\s*Grade:", ["Third Grade"]),
    (r"^4th\s*Grade:", ["Fourth Grade"]),
    (r"^5th\s*Grade:", ["Fifth Grade"]),
]

# Canonical display order
GRADE_ORDER = [
    "Kindergarten",
    "First Grade",
    "Second Grade",
    "Third Grade",
    "Fourth Grade",
    "Fifth Grade",
    "General / KC Series",
]


def parse_grade_levels(title: str) -> list[str]:
    """Return a list of grade-level keys extracted from a session title.

    Falls back to ``["General / KC Series"]`` when no known prefix matches.
    """
    if not title:
        return ["General / KC Series"]

    stripped = title.strip()
    for pattern, grades in _GRADE_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return grades

    return ["General / KC Series"]


# ---------------------------------------------------------------------------
# In-person event section mapping
# ---------------------------------------------------------------------------

# Section grouping for in-person events.
# Primary sections default ON; "Other" defaults OFF (mirrors virtual General).
_IN_PERSON_SECTION_MAP = {
    EventType.CAREER_JUMPING: "Career Jumping",
    EventType.CAREER_SPEAKER: "Career Speakers",
    EventType.CAREER_FAIR: "Career Fair",
    EventType.CLASSROOM_SPEAKER: "Other Events",
    EventType.WORKPLACE_VISIT: "Other Events",
}

IN_PERSON_SECTION_ORDER = [
    "Career Jumping",
    "Career Speakers",
    "Career Fair",
    "Other Events",
]

# All in-person event types we query for
_IN_PERSON_EVENT_TYPES = list(_IN_PERSON_SECTION_MAP.keys())


def _ordinal(n: int) -> str:
    """Return the ordinal suffix for an integer (1→'1st', 2→'2nd', etc.)."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{('th','st','nd','rd','th','th','th','th','th','th')[n % 10]}"


def _format_time_short(dt: datetime) -> str:
    """Format a datetime's time as '8:30 AM' (no leading zero)."""
    return dt.strftime("%I:%M %p").lstrip("0")


def _format_in_person_datetime(start_dt: datetime, end_dt: datetime | None) -> str:
    """Build the newsletter-style datetime string.

    Example: ``Thursday, April 2nd from 8:30-10:30 AM``
    If both times share AM/PM, collapse to ``8:30-10:30 AM``.
    Otherwise use ``8:30 AM to 10:30 PM``.
    """
    day_name = start_dt.strftime("%A")  # e.g. "Thursday"
    month_name = start_dt.strftime("%B")  # e.g. "April"
    day_ord = _ordinal(start_dt.day)  # e.g. "2nd"

    date_part = f"{day_name}, {month_name} {day_ord}"

    start_time = _format_time_short(start_dt)
    if not end_dt:
        return f"{date_part}, {start_time}"

    end_time = _format_time_short(end_dt)
    # Collapse shared AM/PM: "8:30-10:30 AM"
    start_ampm = start_dt.strftime("%p")
    end_ampm = end_dt.strftime("%p")
    if start_ampm == end_ampm:
        start_no_ampm = start_time.replace(f" {start_ampm}", "")
        time_range = f"{start_no_ampm}-{end_time}"
    else:
        time_range = f"{start_time} to {end_time}"

    return f"{date_part}, from {time_range}"


def _section_for_event_type(event_type: EventType) -> str:
    """Map an EventType to its in-person section name."""
    return _IN_PERSON_SECTION_MAP.get(event_type, "Other Events")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@tools_bp.route("/newsletter-formatter")
@login_required
def newsletter_formatter():
    """Render the Newsletter Formatter page."""
    return render_template("tools/newsletter_formatter.html")


@tools_bp.route("/newsletter-formatter/sessions")
@login_required
def newsletter_formatter_sessions():
    """Return upcoming virtual sessions as JSON, annotated with grade levels."""
    try:
        now = datetime.now(timezone.utc)

        sessions = (
            Event.query.filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.status.in_([EventStatus.CONFIRMED, EventStatus.PUBLISHED]),
                Event.start_date > now,
            )
            .order_by(Event.start_date.asc())
            .all()
        )

        results = []
        for s in sessions:
            local_dt = s.local_start_date or s.start_date
            # Manual formatting for cross-platform compatibility (Windows %-m unsupported)
            date_str = f"{local_dt.month}/{local_dt.day}/{local_dt.strftime('%y')}"
            time_str = local_dt.strftime("%I:%M %p").lstrip("0").lower()
            formatted_datetime = f"{date_str} at {time_str}"

            grade_levels = parse_grade_levels(s.title)

            results.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "date": date_str,
                    "time": time_str,
                    "formatted_datetime": formatted_datetime,
                    "grade_levels": grade_levels,
                    "status": s.status.value if s.status else "Unknown",
                }
            )

        return jsonify({"success": True, "sessions": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@tools_bp.route("/newsletter-formatter/in-person-sessions")
@login_required
def newsletter_formatter_in_person_sessions():
    """Return upcoming in-person career events as JSON, grouped by section."""
    try:
        now = datetime.now(timezone.utc)

        events = (
            Event.query.filter(
                Event.type.in_(_IN_PERSON_EVENT_TYPES),
                Event.status.in_([EventStatus.CONFIRMED, EventStatus.PUBLISHED]),
                Event.start_date > now,
            )
            .order_by(Event.start_date.asc())
            .all()
        )

        results = []
        for e in events:
            local_start = e.local_start_date or e.start_date

            # Compute local end date (same timezone conversion as start)
            local_end = None
            if e.end_date:
                import pytz

                end = e.end_date
                if not end.tzinfo:
                    end = end.replace(tzinfo=timezone.utc)
                tz_name = current_app.config.get("TIMEZONE", "America/Chicago")
                tz = pytz.timezone(tz_name)
                local_end = end.astimezone(tz)

            formatted_dt = _format_in_person_datetime(local_start, local_end)
            section = _section_for_event_type(e.type)

            # Derive school name from relationship or title
            school_name = ""
            if e.school_obj:
                school_name = e.school_obj.name

            results.append(
                {
                    "id": e.id,
                    "title": e.title,
                    "formatted_datetime": formatted_dt,
                    "section": section,
                    "school_name": school_name,
                    "district": e.district_partner or "",
                    "link": extract_href_from_html(e.registration_link) or "",
                    "status": e.status.value if e.status else "Unknown",
                }
            )

        return jsonify(
            {
                "success": True,
                "sessions": results,
                "section_order": IN_PERSON_SECTION_ORDER,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@tools_bp.route("/newsletter-formatter/search-virtual-sessions")
@login_required
def newsletter_formatter_search_virtual_sessions():
    """Search upcoming virtual sessions by title keyword.

    Query params:
        q     (str, required)  – search term (case-insensitive title match)
        limit (int, optional)  – max results (default 20)

    Returns JSON with matching sessions including per-session Nepris links.
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"success": True, "sessions": []})

    try:
        limit = min(int(request.args.get("limit", 20)), 50)
    except (ValueError, TypeError):
        limit = 20

    try:
        now = datetime.now(timezone.utc)

        events = (
            Event.query.filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.status.in_([EventStatus.CONFIRMED, EventStatus.PUBLISHED]),
                Event.start_date > now,
                Event.title.ilike(f"%{q}%"),
            )
            .order_by(Event.start_date.asc())
            .limit(limit)
            .all()
        )

        results = []
        for e in events:
            local_start = e.local_start_date or e.start_date

            # Compute local end date
            local_end = None
            if e.end_date:
                import pytz

                end = e.end_date
                if not end.tzinfo:
                    end = end.replace(tzinfo=timezone.utc)
                tz_name = current_app.config.get("TIMEZONE", "America/Chicago")
                tz = pytz.timezone(tz_name)
                local_end = end.astimezone(tz)

            formatted_dt = _format_in_person_datetime(local_start, local_end)

            # Build Nepris link from pathful_session_id
            link = ""
            if e.pathful_session_id:
                link = f"{NEPRIS_SESSION_BASE_URL}{e.pathful_session_id}"

            results.append(
                {
                    "id": e.id,
                    "title": e.title,
                    "formatted_datetime": formatted_dt,
                    "link": link,
                    "status": e.status.value if e.status else "Unknown",
                }
            )

        return jsonify({"success": True, "sessions": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

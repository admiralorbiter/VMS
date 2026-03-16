"""
Newsletter Formatter Tool
=========================

Provides a UI for generating formatted newsletter text from upcoming Pathful
virtual sessions.  Users select which sessions to include, the tool groups
them by grade level, and produces copy-paste-ready text.

Endpoints:
    GET  /tools/newsletter-formatter            → Render the formatter page
    GET  /tools/newsletter-formatter/sessions    → JSON API returning upcoming sessions
"""

import re
from datetime import datetime, timezone

from flask import jsonify, render_template
from flask_login import login_required

from models.event import Event, EventStatus, EventType, db
from routes.tools import tools_bp

# ---------------------------------------------------------------------------
# Grade-level parsing
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

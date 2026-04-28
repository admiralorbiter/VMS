"""
org_membership_filter.py
========================
Date-scoped volunteer-organization membership filter.

Policy:
  Verified mode (default):
    - Current + no dates        → always include (open-ended active member)
    - Past + end_date set       → include only if overlaps report window
    - Past + no end_date        → exclude (departure date unknown)
    - Pending + no end_date     → exclude (not yet active)
    - start_date set            → used as lower bound regardless of status

  Full History mode:
    → no filter applied; returns None; include everyone ever linked

NOTE on timezones: volunteer_organization.start_date / end_date are stored as
naive DateTime. Strip timezone from report boundary datetimes before comparing:
    report_start = start_date.replace(tzinfo=None)
"""

from sqlalchemy import and_, or_

from models.organization import VolunteerOrganization


def membership_date_filter(report_start, report_end, mode="verified"):
    """
    Returns a SQLAlchemy filter clause or None.

    Args:
        report_start: School year start datetime (naive)
        report_end:   School year end datetime (naive)
        mode:         'verified' (conservative default) or 'full' (no filter)

    Usage:
        mode = request.args.get('mode', 'verified')
        if mode not in ('verified', 'full'):   # whitelist — never trust raw input
            mode = 'verified'
        f = membership_date_filter(start, end, mode=mode)
        if f is not None:
            query = query.filter(f)
    """
    if mode == "full":
        return None  # Full History: bypass filter entirely; also bypass cache

    if report_start is None and report_end is None:
        return None  # All-time query with no boundaries — nothing to scope

    # Strip timezone from boundaries to match naive DB columns
    if report_start and getattr(report_start, "tzinfo", None):
        report_start = report_start.replace(tzinfo=None)
    if report_end and getattr(report_end, "tzinfo", None):
        report_end = report_end.replace(tzinfo=None)

    VO = VolunteerOrganization

    # Rule 1: Membership must have started before the report window ended
    started_in_time = or_(
        VO.start_date == None,  # noqa: E711 — SQLAlchemy IS NULL
        VO.start_date <= report_end,
    )

    # Rule 2: Membership must still have been active during the window
    # Pending + no end_date → excluded (not yet active)
    # Past + no end_date   → excluded (unknown departure = conservative)
    still_active = or_(
        # Active current member with no known end
        and_(VO.status == "Current", VO.end_date == None),  # noqa: E711
        # Any member whose recorded end overlaps the window
        and_(VO.end_date != None, VO.end_date >= report_start),  # noqa: E711
    )

    return and_(started_in_time, still_active)

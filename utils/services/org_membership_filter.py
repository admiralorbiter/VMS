"""
org_membership_filter.py
========================
Date-scoped volunteer-organization membership filter.

Two filters are provided:

1. membership_date_filter(report_start, report_end, mode)
   -------------------------------------------------------
   Applied to the VolunteerOrganization (VO) join.
   Controls WHICH VOLUNTEERS count as members of an org for a given window.

   Policy (Verified mode):
     - Current + no dates     -> always include (open-ended active member)
     - Past + end_date set    -> include only if the tenure overlaps the report
                                  window (or any time, for all-time queries)
     - Past + no end_date     -> ALWAYS exclude (departure unknown)
     - Pending + no end_date  -> exclude (not yet active)

   Full History mode: no filter (returns None).

2. event_tenure_filter(mode)
   --------------------------
   Applied to the Event join, IN ADDITION TO membership_date_filter.
   Controls WHICH EVENTS are credited to a volunteer at this org.

   Problem it solves: a volunteer who moved from Org A to Org B still has a VO
   row for Org B (Current). Without this filter, ALL their historical events
   (including ones done while at Org A) appear on Org B's detail report.

   Policy (Verified mode):
     - event.start_date >= VO.start_date  (if start_date is set)
     - event.start_date <= VO.end_date    (if end_date is set)
     - If only one bound is set, the other is open-ended.

   Full History mode: no filter (returns None).

NOTE on timezones: volunteer_organization.start_date / end_date are stored as
naive DateTime. Strip timezone from report boundary datetimes before comparing.
"""

from sqlalchemy import and_, or_

from models.organization import VolunteerOrganization


def membership_date_filter(report_start, report_end, mode="verified"):
    """
    Returns a SQLAlchemy filter clause (applied to VolunteerOrganization) or None.

    Args:
        report_start: School year start datetime (naive), or None for all-time
        report_end:   School year end datetime (naive), or None for all-time
        mode:         'verified' (conservative default) or 'full' (no filter)
    """
    if mode == "full":
        return None  # Full History: bypass filter entirely; also bypass cache

    VO = VolunteerOrganization

    # All-time: no date window, but still enforce membership quality.
    if report_start is None and report_end is None:
        return or_(
            and_(VO.status == "Current", VO.end_date == None),  # noqa: E711
            VO.end_date != None,  # noqa: E711 -- Past/Pending with known end date
        )

    # Strip timezone from boundaries to match naive DB columns
    if report_start and getattr(report_start, "tzinfo", None):
        report_start = report_start.replace(tzinfo=None)
    if report_end and getattr(report_end, "tzinfo", None):
        report_end = report_end.replace(tzinfo=None)

    # Rule 1: Membership must have started before the report window ended
    started_in_time = or_(
        VO.start_date == None,  # noqa: E711 -- SQLAlchemy IS NULL
        VO.start_date <= report_end,
    )

    # Rule 2: Membership must still have been active during the window
    # Past + no end_date -> excluded (unknown departure = conservative)
    still_active = or_(
        and_(VO.status == "Current", VO.end_date == None),  # noqa: E711
        and_(VO.end_date != None, VO.end_date >= report_start),  # noqa: E711
    )

    return and_(started_in_time, still_active)


def event_tenure_filter(mode="verified"):
    """
    Returns a SQLAlchemy filter clause (applied to Event.start_date vs VO dates) or None.

    Prevents events from appearing on an org's report when they occurred outside
    the volunteer's known tenure at that org.

    Example: Lauren moved from UMKC -> Lockton in Aug 2025.
      - Her 2024 events should appear on UMKC's report, NOT Lockton's.
      - This filter ensures event.start_date falls within VO.start_date..VO.end_date.

    Must be used AFTER the Event and VolunteerOrganization models are joined.
    Requires: Event (from models.event) to be in scope in the calling query.

    Args:
        mode: 'verified' (apply tenure bounds) or 'full' (no filter)
    """
    if mode == "full":
        return None

    from models.event import Event

    VO = VolunteerOrganization

    # Lower bound: event must be on or after the volunteer's start at this org
    after_start = or_(
        VO.start_date == None,  # noqa: E711 -- no start recorded, open lower bound
        Event.start_date >= VO.start_date,
    )

    # Upper bound: event must be on or before the volunteer's end at this org
    # If end_date is NULL and status is Current -> still there, no upper bound
    # If end_date is NULL and status is Past -> already excluded by membership_date_filter
    before_end = or_(
        and_(VO.status == "Current", VO.end_date == None),  # noqa: E711
        and_(VO.end_date != None, Event.start_date <= VO.end_date),  # noqa: E711
    )

    return and_(after_start, before_end)

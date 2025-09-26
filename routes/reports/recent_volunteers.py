import io
from datetime import datetime, timedelta, timezone
from time import perf_counter

import pandas as pd
from flask import Blueprint, current_app, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import and_, or_

from models import db, eagerload_volunteer_bundle
from models.event import Event, EventStatus, EventType
from models.organization import Organization, VolunteerOrganization
from models.reports import RecentVolunteersReportCache
from models.volunteer import EventParticipation, Volunteer
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Local blueprint (registered by parent package)
recent_volunteers_bp = Blueprint("recent_volunteers", __name__)


def _parse_date(value: str, default: datetime | None = None) -> datetime | None:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        return default


def _default_date_range():
    # Past 365 days by default
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    return start, end


def _event_type_choices():
    """Return all event types with friendly labels, sorted alphabetically."""

    def friendly_label(value: str) -> str:
        label = value.replace("_", " ").title()
        fixes = {
            "Fafsa": "FAFSA",
            "Dia": "DIA",
            "P2gd": "P2GD",
            "Sla": "SLA",
            "Bfi": "BFI",
        }
        return fixes.get(label, label)

    choices = [(et.value, friendly_label(et.value)) for et in EventType]
    choices.sort(key=lambda x: x[1].lower())
    return choices


def _normalize_selected_types(raw_types: list[str] | None) -> list[EventType]:
    if not raw_types:
        return [et for et in EventType]  # default: all types

    normalized: list[EventType] = []
    values = {et.value: et for et in EventType}
    names = {et.name.lower(): et for et in EventType}
    for t in raw_types:
        if not t:
            continue
        t_norm = t.strip().lower()
        if t_norm in values:
            normalized.append(values[t_norm])
        elif t_norm in names:
            normalized.append(names[t_norm])
    # dedupe preserving order
    seen: set[EventType] = set()
    unique: list[EventType] = []
    for et in normalized:
        if et not in seen:
            seen.add(et)
            unique.append(et)
    return unique or [et for et in EventType]


def _get_primary_org_name(volunteer: Volunteer) -> str | None:
    # Prefer explicit primary org from association table
    if getattr(volunteer, "volunteer_organizations", None):
        primary = next(
            (vo for vo in volunteer.volunteer_organizations if vo.is_primary), None
        )
        if primary and primary.organization and primary.organization.name:
            return primary.organization.name
        # fall back to first org if present
        first = (
            volunteer.volunteer_organizations[0].organization
            if volunteer.volunteer_organizations
            else None
        )
        if first and first.name:
            return first.name
    # Avoid showing raw Salesforce IDs stored in organization_name
    org_name = getattr(volunteer, "organization_name", None)
    if org_name and not (len(org_name) == 18 and org_name.isalnum()):
        return org_name
    return None


def _serialize_for_cache(
    active_volunteers: list[dict], first_time_in_range: list[dict]
) -> dict:
    def ser_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    active_serialized: list[dict] = []
    for rec in active_volunteers:
        new_rec = dict(rec)
        new_rec["last_event_date"] = ser_dt(rec.get("last_event_date"))
        events = []
        for e in rec.get("events", []) or []:
            e_new = dict(e)
            e_new["date"] = ser_dt(e.get("date"))
            events.append(e_new)
        new_rec["events"] = events
        active_serialized.append(new_rec)

    first_serialized: list[dict] = []
    for rec in first_time_in_range:
        new_rec = dict(rec)
        new_rec["first_volunteer_date"] = ser_dt(rec.get("first_volunteer_date"))
        events = []
        for e in rec.get("events", []) or []:
            e_new = dict(e)
            e_new["date"] = ser_dt(e.get("date"))
            events.append(e_new)
        new_rec["events"] = events
        first_serialized.append(new_rec)

    return {
        "active_volunteers": active_serialized,
        "first_time_in_range": first_serialized,
    }


def _deserialize_from_cache(payload: dict) -> tuple[list[dict], list[dict]]:
    def parse_dt(value):
        if not value:
            return None
        try:
            # If pure date like 'YYYY-MM-DD', coerce to midnight UTC
            if isinstance(value, str) and "T" not in value:
                return datetime.fromisoformat(value + "T00:00:00+00:00")
            return datetime.fromisoformat(value)
        except Exception:
            return None

    active_out: list[dict] = []
    for rec in payload.get("active_volunteers") or []:
        new_rec = dict(rec)
        new_rec["last_event_date"] = parse_dt(rec.get("last_event_date"))
        events = []
        for e in rec.get("events", []) or []:
            e_new = dict(e)
            e_new["date"] = parse_dt(e.get("date"))
            events.append(e_new)
        new_rec["events"] = events
        active_out.append(new_rec)

    first_out: list[dict] = []
    for rec in payload.get("first_time_in_range") or []:
        new_rec = dict(rec)
        new_rec["first_volunteer_date"] = parse_dt(rec.get("first_volunteer_date"))
        events = []
        for e in rec.get("events", []) or []:
            e_new = dict(e)
            e_new["date"] = parse_dt(e.get("date"))
            events.append(e_new)
        new_rec["events"] = events
        first_out.append(new_rec)

    return active_out, first_out


def _query_active_volunteers(
    start_date: datetime,
    end_date: datetime,
    selected_types: list[EventType],
    title_contains: str | None,
):
    # Base query joining volunteers to their participations and events
    query = (
        db.session.query(Volunteer, Event, EventParticipation)
        .join(EventParticipation, EventParticipation.volunteer_id == Volunteer.id)
        .join(Event, Event.id == EventParticipation.event_id)
        .filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            Event.type.in_(selected_types),
            EventParticipation.status.in_(
                ["Attended", "Completed", "Successfully Completed", "Simulcast"]
            ),
            Volunteer.exclude_from_reports == False,
        )
    )

    if title_contains:
        like = f"%{title_contains.strip()}%"
        query = query.filter(Event.title.ilike(like))

    rows = eagerload_volunteer_bundle(query).all()

    # Aggregate per volunteer
    aggregated: dict[int, dict] = {}
    for volunteer, event, participation in rows:
        rec = aggregated.get(volunteer.id)
        if not rec:
            rec = {
                "id": volunteer.id,
                "name": f"{volunteer.first_name} {volunteer.last_name}",
                "email": volunteer.primary_email,
                "organization": _get_primary_org_name(volunteer),
                "events": [],
                "event_count": 0,
                "total_hours": 0.0,
                "last_event_date": None,
                "last_event_type": None,
            }
            aggregated[volunteer.id] = rec

        rec["events"].append(
            {
                "id": event.id,
                "title": event.title,
                "date": event.start_date,
                "type": event.type.value if event.type else None,
                "hours": float(participation.delivery_hours or 0),
            }
        )
        rec["event_count"] += 1
        rec["total_hours"] += float(participation.delivery_hours or 0)
        if not rec["last_event_date"] or (
            event.start_date and event.start_date > rec["last_event_date"]
        ):
            rec["last_event_date"] = event.start_date
            rec["last_event_type"] = event.type.value if event.type else None

    # Convert to sorted list (default sort by name)
    result = list(aggregated.values())
    result.sort(key=lambda r: (r["name"] or "").lower())
    return result


def _query_active_volunteers_all(
    start_date: datetime,
    end_date: datetime,
    title_contains: str | None,
):
    """Same as _query_active_volunteers but without filtering by event types.
    Returns per-volunteer records with full event lists and hours for fast client-side filtering.
    """
    query = (
        db.session.query(Volunteer, Event, EventParticipation)
        .join(EventParticipation, EventParticipation.volunteer_id == Volunteer.id)
        .join(Event, Event.id == EventParticipation.event_id)
        .filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            EventParticipation.status.in_(
                ["Attended", "Completed", "Successfully Completed", "Simulcast"]
            ),
            Volunteer.exclude_from_reports == False,
        )
    )

    if title_contains:
        like = f"%{title_contains.strip()}%"
        query = query.filter(Event.title.ilike(like))

    rows = eagerload_volunteer_bundle(query).all()

    aggregated: dict[int, dict] = {}
    for volunteer, event, participation in rows:
        rec = aggregated.get(volunteer.id)
        if not rec:
            rec = {
                "id": volunteer.id,
                "name": f"{volunteer.first_name} {volunteer.last_name}",
                "email": volunteer.primary_email,
                "organization": _get_primary_org_name(volunteer),
                "events": [],
                "event_count": 0,
                "total_hours": 0.0,
                "last_event_date": None,
                "last_event_type": None,
            }
            aggregated[volunteer.id] = rec

        rec["events"].append(
            {
                "id": event.id,
                "title": event.title,
                "date": event.start_date,
                "type": event.type.value if event.type else None,
                "hours": float(participation.delivery_hours or 0),
            }
        )
        rec["event_count"] += 1
        rec["total_hours"] += float(participation.delivery_hours or 0)
        if not rec["last_event_date"] or (
            event.start_date and event.start_date > rec["last_event_date"]
        ):
            rec["last_event_date"] = event.start_date
            rec["last_event_type"] = event.type.value if event.type else None

    result = list(aggregated.values())
    result.sort(key=lambda r: (r["name"] or "").lower())
    return result


def _derive_filtered_from_base(
    active_base: list[dict], first_base: list[dict], selected_types: list[EventType]
) -> tuple[list[dict], list[dict]]:
    selected = {t.value for t in selected_types}

    # Active volunteers: filter events and recompute aggregates
    active_out: list[dict] = []
    for rec in active_base:
        events = rec.get("events") or []
        filtered = [e for e in events if e.get("type") in selected]
        if not filtered:
            continue
        new_rec = {
            "id": rec.get("id"),
            "name": rec.get("name"),
            "email": rec.get("email"),
            "organization": rec.get("organization"),
            "events": filtered,
        }
        new_rec["event_count"] = len(filtered)
        new_rec["total_hours"] = round(
            sum(float(e.get("hours") or 0) for e in filtered), 1
        )
        last = None
        last_type = None
        for e in filtered:
            d = e.get("date")
            if d and (last is None or d > last):
                last = d
                last_type = e.get("type")
        new_rec["last_event_date"] = last
        new_rec["last_event_type"] = last_type

        # Build display list
        titles = [e.get("title") for e in filtered if e.get("title")]
        uniq = []
        seen = set()
        for t in titles:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        new_rec["events_display"] = "; ".join(uniq[:5]) + (
            " …" if len(uniq) > 5 else ""
        )
        active_out.append(new_rec)

    # First-time volunteers: filter events and recompute totals/hours
    first_out: list[dict] = []
    for rec in first_base:
        events = rec.get("events") or []
        filtered = [e for e in events if e.get("type") in selected]
        new_rec = {
            "id": rec.get("id"),
            "name": rec.get("name"),
            "first_volunteer_date": rec.get("first_volunteer_date"),
            "organization": rec.get("organization"),
            "title": rec.get("title"),
            "events": filtered,
        }
        new_rec["total_events"] = len(filtered)
        new_rec["total_hours"] = round(
            sum(float(e.get("hours") or 0) for e in filtered), 1
        )
        first_out.append(new_rec)

    # Keep stable ordering by name
    active_out.sort(key=lambda r: (r.get("name") or "").lower())
    first_out.sort(key=lambda r: (r.get("name") or "").lower())
    return active_out, first_out


def _query_first_time_in_range(start_date: datetime, end_date: datetime):
    # Volunteers whose first_volunteer_date falls within the date range
    volunteers = (
        db.session.query(
            Volunteer,
            db.func.count(EventParticipation.id).label("total_events"),
            db.func.sum(EventParticipation.delivery_hours).label("total_hours"),
            Organization.name.label("organization_name"),
        )
        .outerjoin(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
        .outerjoin(
            Event,
            and_(
                EventParticipation.event_id == Event.id,
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                Event.status == EventStatus.COMPLETED,
            ),
        )
        .outerjoin(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        )
        .outerjoin(
            Organization, VolunteerOrganization.organization_id == Organization.id
        )
        .filter(
            Volunteer.first_volunteer_date >= start_date,
            Volunteer.first_volunteer_date <= end_date,
            Volunteer.exclude_from_reports == False,
        )
        .group_by(Volunteer.id, Organization.name)
        .order_by(Volunteer.first_volunteer_date.desc())
        .all()
    )

    # Build detailed list including events in range for each volunteer
    results: list[dict] = []
    for v, events_count, hours, org in volunteers:
        volunteer_events = (
            db.session.query(Event, EventParticipation.delivery_hours)
            .join(EventParticipation, Event.id == EventParticipation.event_id)
            .filter(
                EventParticipation.volunteer_id == v.id,
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                Event.status == EventStatus.COMPLETED,
                or_(
                    EventParticipation.status == "Attended",
                    EventParticipation.status == "Completed",
                    EventParticipation.status == "Successfully Completed",
                ),
            )
            .order_by(Event.start_date)
            .all()
        )
        events_list = [
            {
                "title": event.title,
                "date": event.start_date,
                "type": event.type.value if event.type else None,
                "hours": float(event_hours or 0),
            }
            for event, event_hours in volunteer_events
        ]

        results.append(
            {
                "id": v.id,
                "name": f"{v.first_name} {v.last_name}",
                "first_volunteer_date": v.first_volunteer_date,
                "total_events": int(events_count or 0),
                "total_hours": float(hours or 0.0),
                "organization": org or _get_primary_org_name(v) or "Independent",
                "events": events_list,
            }
        )

    return results


def _apply_sort(items: list[dict], sort: str, order: str) -> list[dict]:
    key_funcs = {
        "name": lambda r: (r.get("name") or "").lower(),
        "last_event_date": lambda r: r.get("last_event_date") or datetime.min,
        "first_volunteer_date": lambda r: r.get("first_volunteer_date") or datetime.min,
        "total_events": lambda r: int(
            r.get("event_count") or r.get("total_events") or 0
        ),
        "total_hours": lambda r: float(r.get("total_hours") or 0.0),
        "event_type": lambda r: (r.get("last_event_type") or "z").lower(),
        "organization": lambda r: (r.get("organization") or "").lower(),
    }
    key_fn = key_funcs.get(sort, key_funcs["name"])
    reverse = order != "asc"
    return sorted(items, key=key_fn, reverse=reverse)


def _paginate(items: list[dict], page: int, per_page: int):
    total = len(items)
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    page = max(1, min(page, total_pages)) if total_pages else 1
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    return items[start_idx:end_idx], total, total_pages


def load_routes(bp: Blueprint):
    def _is_cache_valid(cache_record, max_age_hours: int = 24) -> bool:
        if not cache_record or not getattr(cache_record, "last_updated", None):
            return False
        last_updated = cache_record.last_updated
        # Normalize to timezone-aware UTC
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - last_updated) < timedelta(hours=max_age_hours)

    @bp.route("/reports/volunteers/recent")
    @login_required
    def recent_volunteers():
        # Optional timing logs; enable with ?debug_timing=1
        debug_timing = request.args.get("debug_timing", "0") == "1"

        def log_info(message: str) -> None:
            if debug_timing:
                current_app.logger.info(f"[RecentVolunteers] {message}")

        route_start = perf_counter()
        # Params: event_types (multi), date_from, date_to, school_year, title, sort, order, page, per_page
        raw_types = request.args.getlist("event_types")
        if not raw_types:
            raw_types = (
                request.args.get("event_types", "").split(",")
                if request.args.get("event_types")
                else None
            )
        selected_types = _normalize_selected_types(raw_types)

        school_year = request.args.get("school_year")
        date_from_param = request.args.get("date_from")
        date_to_param = request.args.get("date_to")
        title_contains = request.args.get("title", "").strip() or None

        sort = request.args.get("sort", "last_event_date")
        order = request.args.get("order", "desc")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)

        # First-time table controls
        ft_sort = request.args.get("ft_sort", "first_volunteer_date")
        ft_order = request.args.get("ft_order", "desc")
        ft_page = request.args.get("ft_page", 1, type=int)
        ft_per_page = request.args.get("ft_per_page", 25, type=int)

        if school_year:
            start_date, end_date = get_school_year_date_range(school_year)
        else:
            start_date, end_date = _default_date_range()
            start_date = _parse_date(date_from_param, start_date)
            end_date = _parse_date(date_to_param, end_date)
        log_info(
            f"Filters parsed: school_year={school_year}, start={start_date}, end={end_date}, types={[t.value for t in selected_types]}, title={bool(title_contains)}"
        )

        # Try cache first. If no exact match or invalid, fall back to base (ALL types) cache
        all_type_values = {et.value for et in EventType}
        selected_values = {t.value for t in selected_types}
        is_all_types = selected_values == all_type_values
        event_types_key = (
            ",".join(sorted(selected_values)) if selected_values else "ALL"
        )
        base_key = "ALL"
        cache_check_start = perf_counter()
        cache = RecentVolunteersReportCache.query.filter_by(
            school_year=school_year or None,
            date_from=(start_date.date() if (start_date and not school_year) else None),
            date_to=(end_date.date() if (end_date and not school_year) else None),
            event_types=event_types_key,
            title_filter=title_contains or None,
        ).first()
        refresh = request.args.get("refresh", "0") == "1"
        log_info(
            f"Cache check: found={bool(cache)}, refresh={refresh}, valid={_is_cache_valid(cache) if cache else False}, took={(perf_counter()-cache_check_start)*1000:.1f} ms"
        )

        if cache and not refresh and _is_cache_valid(cache):
            payload = cache.report_data or {}
            active_volunteers, first_time_in_range = _deserialize_from_cache(payload)
            log_info(
                f"Using cache payload: active={len(active_volunteers)} first_time={len(first_time_in_range)}"
            )
        else:
            # Try base cache (ALL types) for this date window always
            base_cache = RecentVolunteersReportCache.query.filter_by(
                school_year=school_year or None,
                date_from=(
                    start_date.date() if (start_date and not school_year) else None
                ),
                date_to=(end_date.date() if (end_date and not school_year) else None),
                event_types=base_key,
                title_filter=title_contains or None,
            ).first()

            if base_cache and _is_cache_valid(base_cache):
                log_info("Using base cache and deriving filtered view in-memory")
                base_active, base_first = _deserialize_from_cache(
                    base_cache.report_data or {}
                )
                if is_all_types:
                    # All types selected: use base directly
                    active_volunteers, first_time_in_range = base_active, base_first
                else:
                    active_volunteers, first_time_in_range = _derive_filtered_from_base(
                        base_active, base_first, selected_types
                    )
                    # Optionally store typed derived cache to speed subsequent loads
                    cache_save_start = perf_counter()
                    typed_payload = _serialize_for_cache(
                        active_volunteers, first_time_in_range
                    )
                    try:
                        typed_cache = RecentVolunteersReportCache.query.filter_by(
                            school_year=school_year or None,
                            date_from=(
                                start_date.date()
                                if (start_date and not school_year)
                                else None
                            ),
                            date_to=(
                                end_date.date()
                                if (end_date and not school_year)
                                else None
                            ),
                            event_types=event_types_key,
                            title_filter=title_contains or None,
                        ).first()
                        if not typed_cache:
                            typed_cache = RecentVolunteersReportCache(
                                school_year=school_year or None,
                                date_from=(
                                    start_date.date()
                                    if (start_date and not school_year)
                                    else None
                                ),
                                date_to=(
                                    end_date.date()
                                    if (end_date and not school_year)
                                    else None
                                ),
                                event_types=event_types_key,
                                title_filter=title_contains or None,
                                report_data=typed_payload,
                            )
                            db.session.add(typed_cache)
                        else:
                            typed_cache.report_data = typed_payload
                            typed_cache.last_updated = datetime.now(timezone.utc)
                        db.session.commit()
                        log_info(
                            f"Derived typed cache saved in {(perf_counter()-cache_save_start)*1000:.1f} ms"
                        )
                    except Exception:
                        db.session.rollback()
                        log_info("Derived typed cache save failed; rolled back")
            else:
                # Compute fresh BASE (all event types) and save as base cache
                q1_start = perf_counter()
                base_active = _query_active_volunteers_all(
                    start_date, end_date, title_contains
                )
                log_info(
                    f"_query_active_volunteers_all: rows={len(base_active)} took={(perf_counter()-q1_start)*1000:.1f} ms"
                )

                q2_start = perf_counter()
                base_first = _query_first_time_in_range(start_date, end_date)
                log_info(
                    f"_query_first_time_in_range: rows={len(base_first)} took={(perf_counter()-q2_start)*1000:.1f} ms"
                )

                # Save BASE cache
                base_payload = _serialize_for_cache(base_active, base_first)
                cache_save_start = perf_counter()
                try:
                    existing_base = RecentVolunteersReportCache.query.filter_by(
                        school_year=school_year or None,
                        date_from=(
                            start_date.date()
                            if (start_date and not school_year)
                            else None
                        ),
                        date_to=(
                            end_date.date() if (end_date and not school_year) else None
                        ),
                        event_types=base_key,
                        title_filter=title_contains or None,
                    ).first()
                    if not existing_base:
                        existing_base = RecentVolunteersReportCache(
                            school_year=school_year or None,
                            date_from=(
                                start_date.date()
                                if (start_date and not school_year)
                                else None
                            ),
                            date_to=(
                                end_date.date()
                                if (end_date and not school_year)
                                else None
                            ),
                            event_types=base_key,
                            title_filter=title_contains or None,
                            report_data=base_payload,
                        )
                        db.session.add(existing_base)
                    else:
                        existing_base.report_data = base_payload
                        existing_base.last_updated = datetime.now(timezone.utc)
                    db.session.commit()
                    log_info(
                        f"Base cache saved in {(perf_counter()-cache_save_start)*1000:.1f} ms"
                    )
                except Exception:
                    db.session.rollback()
                    log_info("Base cache save failed; rolled back")

                # From base, either use directly (all types) or derive filtered
                if is_all_types:
                    active_volunteers, first_time_in_range = base_active, base_first
                else:
                    active_volunteers, first_time_in_range = _derive_filtered_from_base(
                        base_active, base_first, selected_types
                    )

        # Sorting + pagination for active list
        sp1_start = perf_counter()
        active_sorted = _apply_sort(active_volunteers, sort, order)
        active_page, active_total, active_pages = _paginate(
            active_sorted, page, per_page
        )
        log_info(
            f"Active sort+paginate: sort={sort}/{order} page={page}/{active_pages} total={active_total} took={(perf_counter()-sp1_start)*1000:.1f} ms"
        )

        # Sorting + pagination for first-time list
        sp2_start = perf_counter()
        ft_sorted = _apply_sort(first_time_in_range, ft_sort, ft_order)
        ft_page_items, ft_total, ft_pages = _paginate(ft_sorted, ft_page, ft_per_page)
        log_info(
            f"First-time sort+paginate: sort={ft_sort}/{ft_order} page={ft_page}/{ft_pages} total={ft_total} took={(perf_counter()-sp2_start)*1000:.1f} ms"
        )

        # Compute next orders for header toggles in template
        ft_sort_defaults = {
            "first_volunteer_date": "desc",
            "total_events": "desc",
            "total_hours": "desc",
            "name": "asc",
            "organization": "asc",
        }
        ft_next_orders = {}
        for key, default in ft_sort_defaults.items():
            if ft_sort == key:
                ft_next_orders[key] = "desc" if ft_order == "asc" else "asc"
            else:
                ft_next_orders[key] = default

        # Stats
        summary = {
            "active_volunteers": active_total,
            "active_total_events": sum(v["event_count"] for v in active_volunteers),
            "active_total_hours": round(
                sum(v["total_hours"] for v in active_volunteers), 1
            ),
            "first_time_count": ft_total,
        }

        type_choices = _event_type_choices()
        selected_type_values = [t.value for t in selected_types]

        rendered = render_template(
            "reports/volunteers/recent_volunteers.html",
            # Filters
            type_choices=type_choices,
            selected_types=selected_type_values,
            school_year=school_year or "",
            date_from=start_date.strftime("%Y-%m-%d") if start_date else "",
            date_to=end_date.strftime("%Y-%m-%d") if end_date else "",
            title_contains=title_contains or "",
            sort=sort,
            order=order,
            page=page,
            per_page=per_page,
            # Data
            active_volunteers=active_page,
            active_total=active_total,
            active_pages=active_pages,
            # First-time table data
            ft_volunteers=ft_page_items,
            ft_total=ft_total,
            ft_pages=ft_pages,
            ft_page=ft_page,
            ft_per_page=ft_per_page,
            ft_sort=ft_sort,
            ft_order=ft_order,
            ft_next_orders=ft_next_orders,
            first_time_payload_ts=(cache.last_updated if cache else None),
            summary=summary,
            now=datetime.now(),
        )
        log_info(f"Total route time {(perf_counter()-route_start)*1000:.1f} ms")
        return rendered

    @bp.route("/reports/volunteers/recent/excel")
    @login_required
    def recent_volunteers_excel():
        raw_types = request.args.getlist("event_types")
        if not raw_types:
            raw_types = (
                request.args.get("event_types", "").split(",")
                if request.args.get("event_types")
                else None
            )
        selected_types = _normalize_selected_types(raw_types)

        school_year = request.args.get("school_year")
        date_from_param = request.args.get("date_from")
        date_to_param = request.args.get("date_to")
        title_contains = request.args.get("title", "").strip() or None

        if school_year:
            start_date, end_date = get_school_year_date_range(school_year)
        else:
            start_date, end_date = _default_date_range()
            start_date = _parse_date(date_from_param, start_date)
            end_date = _parse_date(date_to_param, end_date)

        # Attempt to use cache first for export
        all_type_values = {et.value for et in EventType}
        selected_values = {t.value for t in selected_types}
        is_all_types = selected_values == all_type_values
        event_types_key = (
            ",".join(sorted(selected_values)) if selected_values else "ALL"
        )
        base_key = "ALL"

        cache = RecentVolunteersReportCache.query.filter_by(
            school_year=school_year or None,
            date_from=(start_date.date() if (start_date and not school_year) else None),
            date_to=(end_date.date() if (end_date and not school_year) else None),
            event_types=(base_key if is_all_types else event_types_key),
            title_filter=title_contains or None,
        ).first()

        if cache:
            base_active, base_first = _deserialize_from_cache(cache.report_data or {})
            if is_all_types:
                active_volunteers, first_time_in_range = base_active, base_first
            else:
                active_volunteers, first_time_in_range = _derive_filtered_from_base(
                    base_active, base_first, selected_types
                )
        else:
            active_volunteers = _query_active_volunteers(
                start_date, end_date, selected_types, title_contains
            )
            first_time_in_range = _query_first_time_in_range(start_date, end_date)

        # Build DataFrames
        active_rows = []
        for v in active_volunteers:
            last_date_str = (
                v["last_event_date"].strftime("%m/%d/%y")
                if v.get("last_event_date")
                else ""
            )
            titles = [e["title"] for e in v["events"] if e.get("title")]
            active_rows.append(
                {
                    "Name": v["name"],
                    "Email": v.get("email") or "",
                    "Organization": v.get("organization") or "",
                    "Events (Count)": v.get("event_count") or 0,
                    "Total Hours": round(float(v.get("total_hours") or 0.0), 1),
                    "Last Event": last_date_str,
                    "Last Event Type": v.get("last_event_type") or "",
                    "Event Titles": "; ".join(sorted(set(titles))),
                }
            )

        first_time_rows = []
        for r in first_time_in_range:
            first_str = (
                r["first_volunteer_date"].strftime("%m/%d/%y")
                if r.get("first_volunteer_date")
                else ""
            )
            titles = [e["title"] for e in r["events"] if e.get("title")]
            first_time_rows.append(
                {
                    "Name": r["name"],
                    "First Volunteer Date": first_str,
                    "Events Count": r.get("total_events") or 0,
                    "Total Hours": round(float(r.get("total_hours") or 0.0), 1),
                    "Organization": r.get("organization") or "",
                    "Event Titles": "; ".join(sorted(set(titles))),
                }
            )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            if active_rows:
                df_active = pd.DataFrame(active_rows)
                df_active.to_excel(writer, index=False, sheet_name="Active Volunteers")
                ws = writer.sheets["Active Volunteers"]
                ws.set_column("A:A", 28)
                ws.set_column("B:B", 34)
                ws.set_column("C:C", 28)
                ws.set_column("D:D", 14)
                ws.set_column("E:E", 14)
                ws.set_column("F:F", 14)
                ws.set_column("G:G", 18)
                ws.set_column("H:H", 60)

            if first_time_rows:
                df_first = pd.DataFrame(first_time_rows)
                df_first.to_excel(writer, index=False, sheet_name="First-Time In Range")
                ws2 = writer.sheets["First-Time In Range"]
                ws2.set_column("A:A", 28)
                ws2.set_column("B:B", 18)
                ws2.set_column("C:C", 14)
                ws2.set_column("D:D", 14)
                ws2.set_column("E:E", 28)
                ws2.set_column("F:F", 60)

        output.seek(0)

        # Attempt to use cache for export as well
        event_types_key = ",".join(sorted([t.value for t in selected_types]))
        cache = RecentVolunteersReportCache.query.filter_by(
            school_year=school_year or None,
            date_from=(start_date.date() if (start_date and not school_year) else None),
            date_to=(end_date.date() if (end_date and not school_year) else None),
            event_types=event_types_key,
            title_filter=title_contains or None,
        ).first()

        if cache and cache.report_data:
            payload = cache.report_data
            active_from_cache, first_from_cache = _deserialize_from_cache(payload)
            if active_from_cache:
                active_volunteers = active_from_cache
            if first_from_cache:
                first_time_in_range = first_from_cache

        if school_year:
            filename = f"Recent_Volunteers_{school_year[:2]}-{school_year[2:]}.xlsx"
        else:
            filename = f"Recent_Volunteers_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name=filename,
            as_attachment=True,
        )

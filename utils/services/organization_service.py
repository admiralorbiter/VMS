"""
Organization Service Module
==========================

This module provides a unified service layer for organization data retrieval,
eliminating code duplication between basic organization views and detailed reports.

Key Features:
- Comprehensive organization engagement metrics
- Year-based and all-time data retrieval
- Volunteer and event breakdowns
- Caching support for performance
- Unified data format for consistency

Usage:
    from utils.services.organization_service import OrganizationService

    service = OrganizationService()
    summary = service.get_organization_summary(org_id)
    detail = service.get_organization_detail(org_id, school_year='2425')
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import aliased

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventTeacher, EventType
from models.organization import Organization, VolunteerOrganization
from models.reports import OrganizationDetailCache, OrganizationSummaryCache
from models.school_model import School
from models.teacher import Teacher
from models.volunteer import EventParticipation, Volunteer
from routes.reports.common import get_current_school_year, get_school_year_date_range


class OrganizationService:
    """Unified service for organization data retrieval and analysis."""

    def __init__(self):
        self.current_school_year = get_current_school_year()

    def get_organization_summary(self, org_id: int) -> Dict:
        """
        Get basic organization information with summary engagement metrics (all-time).

        Args:
            org_id: Organization ID

        Returns:
            Dictionary with organization info and summary stats
        """
        organization = Organization.query.get_or_404(org_id)

        # Get all-time volunteer count
        volunteer_count = (
            db.session.query(func.count(VolunteerOrganization.volunteer_id))
            .filter(VolunteerOrganization.organization_id == org_id)
            .scalar()
            or 0
        )

        # Get all-time event participation summary
        event_summary = (
            db.session.query(
                func.count(func.distinct(Event.id)).label("total_sessions"),
                func.sum(EventParticipation.delivery_hours).label("total_hours"),
                func.count(func.distinct(Volunteer.id)).label("unique_volunteers"),
            )
            .join(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                VolunteerOrganization.organization_id == org_id,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
                Volunteer.exclude_from_reports == False,
            )
            .first()
        )

        return {
            "organization": organization,
            "volunteer_count": volunteer_count,
            "total_sessions": event_summary.total_sessions or 0,
            "total_hours": round(event_summary.total_hours or 0, 2),
            "unique_volunteers": event_summary.unique_volunteers or 0,
        }

    def get_organization_detail(
        self, org_id: int, school_year: Optional[str] = None
    ) -> Dict:
        """
        Get comprehensive organization detail data with engagement breakdowns.

        Args:
            org_id: Organization ID
            school_year: School year filter (e.g., '2425') or None for all-time

        Returns:
            Dictionary with comprehensive organization data
        """
        organization = Organization.query.get_or_404(org_id)

        # Use current school year if none specified
        if school_year is None:
            school_year = self.current_school_year

        # Check cache first (unless all-time requested)
        if school_year != "all_time":
            cache = OrganizationDetailCache.query.filter_by(
                organization_id=org_id, school_year=school_year
            ).first()
            if cache:
                return self._format_cached_data(organization, cache, school_year)

        # Get date range for the school year
        if school_year == "all_time":
            start_date = None
            end_date = None
        else:
            start_date, end_date = get_school_year_date_range(school_year)

        # Get comprehensive data
        volunteers_data = self._get_volunteers_data(org_id, start_date, end_date)
        in_person_events = self._get_in_person_events(org_id, start_date, end_date)
        virtual_events = self._get_virtual_events(org_id, start_date, end_date)
        cancelled_events = self._get_cancelled_events(org_id, start_date, end_date)

        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(
            volunteers_data, in_person_events, virtual_events, cancelled_events
        )

        # Cache the data if it's year-specific
        if school_year != "all_time":
            self._cache_organization_detail(
                org_id,
                school_year,
                organization.name,
                summary_stats,
                volunteers_data,
                in_person_events,
                virtual_events,
                cancelled_events,
            )

        return {
            "organization": organization,
            "school_year": school_year,
            "volunteers": volunteers_data,
            "in_person_events": in_person_events,
            "virtual_events": virtual_events,
            "cancelled_events": cancelled_events,
            "summary_stats": summary_stats,
        }

    def _get_volunteers_data(
        self, org_id: int, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> List[Dict]:
        """Get volunteer participation data for the organization."""
        query = (
            db.session.query(
                Volunteer,
                func.count(func.distinct(Event.id)).label("event_count"),
                func.sum(EventParticipation.delivery_hours).label("total_hours"),
            )
            .join(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                VolunteerOrganization.organization_id == org_id,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
                Volunteer.exclude_from_reports == False,
            )
        )

        if start_date:
            query = query.filter(Event.start_date >= start_date)
        if end_date:
            query = query.filter(Event.start_date <= end_date)

        volunteer_stats = query.group_by(Volunteer.id).all()

        return [
            {
                "id": v.id,
                "name": f"{v.first_name} {v.last_name}",
                "email": v.primary_email,
                "events": events,
                "hours": round(hours or 0, 2),
            }
            for v, events, hours in volunteer_stats
        ]

    def _get_in_person_events(
        self, org_id: int, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> List[Dict]:
        """Get in-person event data with volunteer details."""
        query = (
            db.session.query(
                Event,
                Volunteer,
                EventParticipation.status,
                EventParticipation.delivery_hours,
            )
            .join(EventParticipation, Event.id == EventParticipation.event_id)
            .join(Volunteer, EventParticipation.volunteer_id == Volunteer.id)
            .join(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .filter(
                VolunteerOrganization.organization_id == org_id,
                Event.type != EventType.VIRTUAL_SESSION,
                db.or_(
                    EventParticipation.status.in_(
                        ["Attended", "Completed", "Successfully Completed"]
                    ),
                    Event.status == EventStatus.CONFIRMED,
                ),
                Volunteer.exclude_from_reports == False,
            )
        )

        if start_date:
            query = query.filter(Event.start_date >= start_date)
        if end_date:
            query = query.filter(Event.start_date <= end_date)

        detailed_events = query.order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()

        # Group events by event with volunteer names
        events_by_event = {}
        for event, volunteer, status, hours in detailed_events:
            # For CONFIRMED events, include all volunteers; for completed events, only include those with hours
            if event.status == EventStatus.CONFIRMED:
                # For scheduled events, hours might be None, so set to 0 if None
                hours = hours or 0
            elif hours is None:
                # Skip events without hours for completed events
                continue
            event_key = f"{event.id}_{event.title}"
            if event_key not in events_by_event:
                events_by_event[event_key] = {
                    "event": event,
                    "volunteers": [],
                    "total_hours": 0,
                }
            events_by_event[event_key]["volunteers"].append(
                {
                    "name": f"{volunteer.first_name} {volunteer.last_name}",
                    "status": status,
                    "hours": hours or 0,
                }
            )
            events_by_event[event_key]["total_hours"] += hours or 0

        # Format events data
        events_data = []
        for event_key, event_data in events_by_event.items():
            event = event_data["event"]
            volunteer_names = [v["name"] for v in event_data["volunteers"]]

            # Calculate student count
            student_count = self._calculate_student_count(event)

            events_data.append(
                {
                    "id": event.id,
                    "date": event.start_date.strftime("%m/%d/%y"),
                    "date_sort": event.start_date,
                    "title": event.title,
                    "type": event.type.value if event.type else "Unknown",
                    "volunteers": volunteer_names,
                    "volunteer_count": len(volunteer_names),
                    "hours": round(event_data["total_hours"], 2),
                    "students": student_count["count"],
                    "students_per_volunteer": student_count["per_volunteer"],
                    "is_calculated": student_count["is_calculated"],
                }
            )

        return events_data

    def _get_virtual_events(
        self, org_id: int, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> List[Dict]:
        """Get virtual event data with classroom details."""
        TeacherAlias = aliased(Teacher, flat=True)
        SchoolAlias = aliased(School, flat=True)
        DistrictAlias = aliased(District, flat=True)

        query = (
            db.session.query(
                Event,
                Volunteer,
                EventParticipation.status,
                EventTeacher,
                TeacherAlias,
                SchoolAlias,
                DistrictAlias,
            )
            .join(EventParticipation, Event.id == EventParticipation.event_id)
            .join(Volunteer, EventParticipation.volunteer_id == Volunteer.id)
            .join(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .outerjoin(EventTeacher, Event.id == EventTeacher.event_id)
            .outerjoin(TeacherAlias, EventTeacher.teacher_id == TeacherAlias.id)
            .outerjoin(SchoolAlias, TeacherAlias.salesforce_school_id == SchoolAlias.id)
            .outerjoin(DistrictAlias, SchoolAlias.district_id == DistrictAlias.id)
            .filter(
                VolunteerOrganization.organization_id == org_id,
                Event.type == EventType.VIRTUAL_SESSION,
                db.or_(
                    EventParticipation.status.in_(
                        ["Attended", "Completed", "Successfully Completed", "Simulcast"]
                    ),
                    Event.status == EventStatus.CONFIRMED,
                ),
                Volunteer.exclude_from_reports == False,
                db.or_(
                    TeacherAlias.id == None, TeacherAlias.exclude_from_reports == False
                ),
            )
        )

        if start_date:
            query = query.filter(Event.start_date >= start_date)
        if end_date:
            query = query.filter(Event.start_date <= end_date)

        detailed_events = query.order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()

        # Group events by event with volunteer names and classroom details
        events_by_event = {}
        for (
            event,
            volunteer,
            status,
            event_teacher,
            teacher,
            school,
            district,
        ) in detailed_events:
            event_key = f"{event.id}_{event.title}"
            if event_key not in events_by_event:
                events_by_event[event_key] = {
                    "event": event,
                    "volunteers": [],
                    "classrooms": [],
                    "unique_classroom_count": 0,
                }

            events_by_event[event_key]["volunteers"].append(
                {
                    "name": f"{volunteer.first_name} {volunteer.last_name}",
                    "status": status,
                }
            )

            # Add teacher/classroom information if available
            if (
                teacher
                and event_teacher
                and event_teacher.status in ["simulcast", "successfully completed"]
            ):
                classroom_info = {
                    "teacher_id": teacher.id,
                    "teacher_name": f"{teacher.first_name} {teacher.last_name}",
                    "school_name": school.name if school else "Unknown School",
                    "district_name": district.name if district else "Unknown District",
                    "status": event_teacher.status,
                }
                events_by_event[event_key]["classrooms"].append(classroom_info)

        # Calculate unique classroom count for each event
        for event_key, event_data in events_by_event.items():
            unique_teachers = set()
            for classroom in event_data["classrooms"]:
                unique_teachers.add(classroom["teacher_name"])
            event_data["unique_classroom_count"] = len(unique_teachers)

        # Format events data
        events_data = []
        for event_key, event_data in events_by_event.items():
            event = event_data["event"]
            unique_volunteer_names = list(
                set([v["name"] for v in event_data["volunteers"]])
            )

            events_data.append(
                {
                    "id": event.id,
                    "date": event.start_date.strftime("%m/%d/%y"),
                    "time": (
                        event.start_date.strftime("%I:%M %p")
                        if event.start_date
                        else ""
                    ),
                    "date_sort": event.start_date,
                    "title": event.title,
                    "type": event.type.value if event.type else "Unknown",
                    "volunteers": unique_volunteer_names,
                    "volunteer_count": len(unique_volunteer_names),
                    "classrooms": event_data["unique_classroom_count"],
                    "classroom_details": event_data["classrooms"],
                }
            )

        return events_data

    def _get_cancelled_events(
        self, org_id: int, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> List[Dict]:
        """Get cancelled events data."""
        query = (
            db.session.query(
                Event,
                func.count(func.distinct(EventParticipation.volunteer_id)).label(
                    "volunteer_count"
                ),
            )
            .join(EventParticipation, Event.id == EventParticipation.event_id)
            .join(Volunteer, EventParticipation.volunteer_id == Volunteer.id)
            .join(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .filter(
                VolunteerOrganization.organization_id == org_id,
                db.or_(
                    Event.status == EventStatus.CANCELLED,
                    EventParticipation.status.in_(
                        [
                            "Cancelled",
                            "No Show",
                            "Did Not Attend",
                            "Teacher No-Show",
                            "Volunteer canceling due to snow",
                            "Weather Cancellation",
                            "School Closure",
                            "Emergency Cancellation",
                        ]
                    ),
                ),
                Volunteer.exclude_from_reports == False,
            )
        )

        if start_date:
            query = query.filter(Event.start_date >= start_date)
        if end_date:
            query = query.filter(Event.start_date <= end_date)

        cancelled_events = query.group_by(Event.id).all()

        return [
            {
                "date": event.start_date.strftime("%m/%d/%y"),
                "title": event.title,
                "type": event.type.value if event.type else "Unknown",
                "volunteers": vol_count,
                "status": "Cancelled/No Show",
            }
            for event, vol_count in cancelled_events
        ]

    def _calculate_student_count(self, event: Event) -> Dict:
        """Calculate student count for an event."""
        attendance_detail = event.attendance_detail
        student_count = event.participant_count or 0
        students_per_volunteer = None
        is_calculated = False

        # Calculate students per volunteer if attendance detail exists
        if (
            attendance_detail
            and attendance_detail.total_students
            and attendance_detail.num_classrooms
            and attendance_detail.rotations
        ):
            try:
                total_students = int(attendance_detail.total_students)
                num_classrooms = int(attendance_detail.num_classrooms)
                rotations = int(attendance_detail.rotations)

                if num_classrooms > 0 and rotations > 0:
                    students_per_volunteer = math.floor(
                        (total_students / num_classrooms) * rotations
                    )
                    student_count = total_students
                    is_calculated = True
            except (ValueError, TypeError):
                pass

        return {
            "count": student_count,
            "per_volunteer": students_per_volunteer,
            "is_calculated": is_calculated,
        }

    def _calculate_summary_stats(
        self,
        volunteers_data: List[Dict],
        in_person_events: List[Dict],
        virtual_events: List[Dict],
        cancelled_events: List[Dict],
    ) -> Dict:
        """Calculate summary statistics from event data."""
        total_inperson_sessions = len(in_person_events)
        total_virtual_sessions = len(virtual_events)
        total_sessions = total_inperson_sessions + total_virtual_sessions
        total_hours = sum(vol["hours"] for vol in volunteers_data)
        total_volunteers = len(volunteers_data)
        total_cancelled = len(cancelled_events)
        total_students_reached = sum(evt["students"] for evt in in_person_events)

        # Calculate total unique classrooms across all virtual events
        teacher_session_counts = {}
        for event_data in virtual_events:
            if "classroom_details" in event_data:
                for classroom in event_data["classroom_details"]:
                    teacher_name = classroom["teacher_name"]
                    if teacher_name not in teacher_session_counts:
                        teacher_session_counts[teacher_name] = 0
                    teacher_session_counts[teacher_name] += 1

        total_classrooms_reached = len(teacher_session_counts)

        return {
            "total_inperson_sessions": total_inperson_sessions,
            "total_virtual_sessions": total_virtual_sessions,
            "total_sessions": total_sessions,
            "total_hours": total_hours,
            "total_volunteers": total_volunteers,
            "total_cancelled": total_cancelled,
            "total_students_reached": total_students_reached,
            "total_classrooms_reached": total_classrooms_reached,
        }

    def _format_cached_data(
        self,
        organization: Organization,
        cache: OrganizationDetailCache,
        school_year: str,
    ) -> Dict:
        """Format cached data for consistent return structure."""
        return {
            "organization": organization,
            "school_year": school_year,
            "volunteers": cache.volunteers_data or [],
            "in_person_events": cache.in_person_events or [],
            "virtual_events": cache.virtual_events or [],
            "cancelled_events": cache.cancelled_events or [],
            "summary_stats": cache.summary_stats or {},
            "is_cached": True,
            "last_refreshed": cache.last_updated,
        }

    def _cache_organization_detail(
        self,
        org_id: int,
        school_year: str,
        org_name: str,
        summary_stats: Dict,
        volunteers_data: List[Dict],
        in_person_events: List[Dict],
        virtual_events: List[Dict],
        cancelled_events: List[Dict],
    ):
        """Cache organization detail data for performance."""
        try:
            detail_cache = OrganizationDetailCache.query.filter_by(
                organization_id=org_id, school_year=school_year
            ).first()

            if not detail_cache:
                detail_cache = OrganizationDetailCache(
                    organization_id=org_id,
                    school_year=school_year,
                    organization_name=org_name,
                    in_person_events=in_person_events,
                    virtual_events=virtual_events,
                    cancelled_events=cancelled_events,
                    volunteers_data=volunteers_data,
                    summary_stats=summary_stats,
                )
                db.session.add(detail_cache)
            else:
                detail_cache.organization_name = org_name
                detail_cache.in_person_events = in_person_events
                detail_cache.virtual_events = virtual_events
                detail_cache.cancelled_events = cancelled_events
                detail_cache.volunteers_data = volunteers_data
                detail_cache.summary_stats = summary_stats

            db.session.commit()
        except Exception:
            db.session.rollback()

    def get_school_years(self) -> List[str]:
        """Get list of available school years."""
        current_year = int(self.current_school_year[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first
        return school_years

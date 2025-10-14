"""
Reports Models Module
====================

This module defines models for caching and storing report data in the VMS system.
These models provide efficient data storage for complex reports that require
significant computation time, allowing for faster report generation and display.

Key Features:
- Report data caching for performance optimization
- District-level year-end and engagement reports
- Organization-level reports and summaries
- JSON data storage for flexible report structures
- School year-based data organization
- Automatic timestamp tracking for cache invalidation
- Unique constraints to prevent duplicate reports

Database Tables:
- district_year_end_reports: Cached year-end reports for districts
- district_engagement_reports: Cached engagement reports for districts
- organization_reports: Cached reports for organizations
- organization_summary_cache: Summary data for all organizations
- organization_detail_cache: Detailed data for individual organizations

Report Types:
- District Year-End Reports: Annual summary reports for districts
- District Engagement Reports: Engagement metrics and statistics
- Organization Reports: Organization-specific activity reports
- Summary Caches: Aggregated data across organizations
- Detail Caches: Detailed data for individual organizations

Data Storage:
- JSON fields for flexible data structures
- School year organization for academic calendar alignment
- Host filter support for multi-host environments
- Timestamp tracking for cache management

Performance Optimizations:
- Indexed fields for fast queries
- Unique constraints to prevent duplicates
- Composite indexes for common query patterns
- Cached data to reduce computation time

Usage Examples:
    # Create a district year-end report
    report = DistrictYearEndReport(
        district_id="0011234567890ABCD",
        school_year="2425",
        host_filter="all",
        report_data={"total_events": 150, "total_volunteers": 45}
    )

    # Cache organization summary data
    summary = OrganizationSummaryCache(
        school_year="2425",
        organizations_data={"total_organizations": 25, "active_volunteers": 120}
    )

    # Check if report is recent
    if (datetime.now() - report.last_updated).days < 7:
        print("Report is up to date")
"""

from datetime import datetime, timezone

from models import db  # Import db from models instead of creating new instance


class DistrictYearEndReport(db.Model):
    """
    Model for caching district year-end reports.

    This model stores pre-computed year-end reports for districts to improve
    performance when generating complex reports. Each report is tied to a
    specific district, school year, and host filter combination.

    Database Table:
        district_year_end_reports - Cached year-end reports for districts

    Key Features:
        - District-specific report caching
        - School year organization
        - Host filter support for multi-host environments
        - JSON data storage for flexible report structures
        - Automatic timestamp tracking for cache invalidation
        - Unique constraints to prevent duplicate reports

    Relationships:
        - Many-to-one with District model

    Data Organization:
        - district_id: Links to specific district
        - school_year: Academic year (e.g., "2425" for 2024-2025)
        - host_filter: Host environment filter ("all", "prep-kc", etc.)
        - report_data: Main report data as JSON
        - events_data: Event-specific data as JSON

    Performance Features:
        - Indexed school_year for fast filtering
        - Composite index on school_year and last_updated
        - Unique constraint prevents duplicate reports
        - Cached data reduces computation time
    """

    __tablename__ = "district_year_end_reports"

    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.String(18), db.ForeignKey("district.id"), nullable=False)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # Added index
    host_filter = db.Column(db.String(20), default="all", nullable=False, index=True)
    report_data = db.Column(db.JSON, nullable=False)
    events_data = db.Column(db.JSON, nullable=True)
    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    district = db.relationship("District", backref="year_end_reports")

    __table_args__ = (
        db.UniqueConstraint(
            "district_id",
            "school_year",
            "host_filter",
            name="uix_district_school_year_host_filter",
        ),
        db.Index(
            "idx_school_year_last_updated", "school_year", "last_updated"
        ),  # Added composite index
    )


class DistrictEngagementReport(db.Model):
    """
    Model for caching district engagement reports.

    This model stores pre-computed engagement reports for districts, including
    summary statistics, volunteer data, student data, and event breakdowns.

    Database Table:
        district_engagement_reports - Cached engagement reports for districts

    Key Features:
        - District-specific engagement metrics
        - School year organization
        - Comprehensive data caching (summary, volunteers, students, events)
        - Breakdown data for detailed analysis
        - Automatic timestamp tracking for cache invalidation

    Relationships:
        - Many-to-one with District model

    Data Structure:
        - summary_stats: High-level engagement metrics
        - volunteers_data: Volunteer participation data
        - students_data: Student participation data
        - events_data: Event-specific engagement data
        - breakdown_data: Detailed event-centric analysis

    Performance Features:
        - Indexed school_year for fast filtering
        - Composite index on school_year and last_updated
        - Unique constraint prevents duplicate reports
        - Cached data reduces computation time
    """

    __tablename__ = "district_engagement_reports"

    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.String(18), db.ForeignKey("district.id"), nullable=False)
    school_year = db.Column(db.String(4), nullable=False, index=True)

    # Cache for summary stats and detailed data
    summary_stats = db.Column(db.JSON, nullable=False)
    volunteers_data = db.Column(db.JSON, nullable=True)
    students_data = db.Column(db.JSON, nullable=True)
    events_data = db.Column(db.JSON, nullable=True)

    # Cache for full breakdown data (event-centric view)
    breakdown_data = db.Column(db.JSON, nullable=True)

    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    district = db.relationship("District", backref="engagement_reports")

    __table_args__ = (
        db.UniqueConstraint(
            "district_id", "school_year", name="uix_district_engagement_school_year"
        ),
        db.Index("idx_engagement_school_year_updated", "school_year", "last_updated"),
    )


class OrganizationReport(db.Model):
    """
    Model for caching organization-specific reports.

    This model stores pre-computed reports for individual organizations,
    including summary statistics and detailed event data categorized by type.

    Database Table:
        organization_reports - Cached reports for organizations

    Key Features:
        - Organization-specific report caching
        - School year organization
        - Event type categorization (in-person, virtual, cancelled)
        - Volunteer data caching
        - Summary statistics storage
        - Automatic timestamp tracking for cache invalidation

    Relationships:
        - Many-to-one with Organization model

    Data Structure:
        - summary_stats: High-level organization metrics
        - in_person_events_data: In-person event details
        - virtual_events_data: Virtual event details
        - cancelled_events_data: Cancelled event details
        - volunteers_data: Volunteer participation data

    Performance Features:
        - Indexed school_year for fast filtering
        - Composite index on school_year and last_updated
        - Unique constraint prevents duplicate reports
        - Cached data reduces computation time
    """

    __tablename__ = "organization_reports"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.String(18), db.ForeignKey("organization.id"), nullable=False
    )
    school_year = db.Column(db.String(4), nullable=False, index=True)

    # Cache for summary stats
    summary_stats = db.Column(db.JSON, nullable=False)

    # Cache for detailed event data
    in_person_events_data = db.Column(db.JSON, nullable=True)
    virtual_events_data = db.Column(db.JSON, nullable=True)
    cancelled_events_data = db.Column(db.JSON, nullable=True)
    volunteers_data = db.Column(db.JSON, nullable=True)

    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    organization = db.relationship("Organization", backref="cached_reports")

    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "school_year", name="uix_organization_school_year"
        ),
        db.Index("idx_organization_school_year_updated", "school_year", "last_updated"),
    )


class OrganizationSummaryCache(db.Model):
    """
    Model for caching organization summary data across all organizations.

    This model stores aggregated summary data for all organizations within
    a school year, providing quick access to organization-level statistics.

    Database Table:
        organization_summary_cache - Summary data for all organizations

    Key Features:
        - School year-based organization summaries
        - Aggregated data across all organizations
        - JSON storage for flexible data structures
        - Automatic timestamp tracking for cache invalidation
        - Quick access to organization-level statistics

    Data Structure:
        - school_year: Academic year (e.g., "2425")
        - organizations_data: Aggregated organization statistics
        - last_updated: Cache invalidation timestamp

    Performance Features:
        - Indexed school_year for fast filtering
        - Single record per school year for efficient access
        - Cached data reduces computation time
    """

    __tablename__ = "organization_summary_cache"

    id = db.Column(db.Integer, primary_key=True)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # e.g., '2425'
    organizations_data = db.Column(db.JSON)  # Cached organization summary data
    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<OrganizationSummaryCache {self.school_year}>"


class OrganizationDetailCache(db.Model):
    """
    Model for caching detailed organization data.

    This model stores detailed data for individual organizations within
    a school year, including event breakdowns and volunteer statistics.

    Database Table:
        organization_detail_cache - Detailed data for individual organizations

    Key Features:
        - Organization-specific detailed data caching
        - School year organization
        - Event type categorization (in-person, virtual, cancelled)
        - Volunteer data storage
        - Summary statistics caching
        - Automatic timestamp tracking for cache invalidation

    Data Structure:
        - organization_id: Links to specific organization
        - school_year: Academic year (e.g., "2425")
        - organization_name: Human-readable organization name
        - in_person_events: In-person event data as JSON
        - virtual_events: Virtual event data as JSON
        - cancelled_events: Cancelled event data as JSON
        - volunteers_data: Volunteer statistics as JSON
        - summary_stats: Summary statistics as JSON

    Performance Features:
        - Indexed organization_id and school_year for fast queries
        - Unique constraint prevents duplicate caches
        - Cached data reduces computation time
    """

    __tablename__ = "organization_detail_cache"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # e.g., '2425'
    organization_name = db.Column(db.String(255))  # For easier identification

    # Cached detailed data as JSON
    in_person_events = db.Column(db.JSON)  # List of in-person event data
    virtual_events = db.Column(db.JSON)  # List of virtual event data
    cancelled_events = db.Column(db.JSON)  # List of cancelled event data
    volunteers_data = db.Column(db.JSON)  # Volunteer summary data
    summary_stats = db.Column(db.JSON)  # Summary statistics

    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "school_year", name="uq_org_detail_cache"
        ),
    )

    def __repr__(self):
        return f"<OrganizationDetailCache {self.organization_name} {self.school_year}>"


class FirstTimeVolunteerReportCache(db.Model):
    """
    Model for caching first time volunteer report data per school year.
    """

    __tablename__ = "first_time_volunteer_report_cache"
    id = db.Column(db.Integer, primary_key=True)
    school_year = db.Column(db.String(4), nullable=False, index=True)
    report_data = db.Column(db.JSON, nullable=False)
    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    __table_args__ = (
        db.UniqueConstraint("school_year", name="uq_first_time_volunteer_report_cache"),
    )


class VirtualSessionReportCache(db.Model):
    """
    Model for caching virtual session usage report data.

    This model stores pre-computed virtual session usage reports to improve
    performance when generating complex reports with multiple filters and
    aggregations.

    Database Table:
        virtual_session_report_cache - Cached virtual session usage reports

    Key Features:
        - Virtual year-based report caching
        - Date range support for flexible filtering
        - JSON storage for session data, summaries, and filter options
        - Automatic timestamp tracking for cache invalidation
        - Unique constraints to prevent duplicate reports

    Data Structure:
        - virtual_year: Academic year for virtual sessions (e.g., "2024-2025")
        - date_from, date_to: Optional date range filters
        - session_data: Main session data as JSON
        - district_summaries: District-level summary statistics
        - overall_summary: Overall report statistics
        - filter_options: Available filter options (districts, schools, etc.)

    Performance Features:
        - Indexed virtual_year for fast filtering
        - Composite index on virtual_year and last_updated
        - Unique constraint prevents duplicate reports
        - Cached data reduces computation time
    """

    __tablename__ = "virtual_session_report_cache"

    id = db.Column(db.Integer, primary_key=True)
    virtual_year = db.Column(
        db.String(9), nullable=False, index=True
    )  # e.g., '2024-2025'
    date_from = db.Column(db.Date, nullable=True)
    date_to = db.Column(db.Date, nullable=True)

    # Cached report data as JSON
    session_data = db.Column(db.JSON, nullable=False)  # All session records
    district_summaries = db.Column(db.JSON, nullable=True)  # District breakdown
    overall_summary = db.Column(db.JSON, nullable=True)  # Overall statistics
    filter_options = db.Column(db.JSON, nullable=True)  # Available filter options

    last_updated = db.Column(
        db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "virtual_year",
            "date_from",
            "date_to",
            name="uq_virtual_session_report_cache",
        ),
        db.Index("idx_virtual_year_updated", "virtual_year", "last_updated"),
    )

    def __repr__(self):
        return f"<VirtualSessionReportCache {self.virtual_year}>"


class RecentVolunteersReportCache(db.Model):
    """
    Model for caching recent volunteers report data.

    Cache is parameterized by either a school_year (YYZZ) or a date range
    (date_from/date_to), plus event types and optional title filter.
    """

    __tablename__ = "recent_volunteers_report_cache"

    id = db.Column(db.Integer, primary_key=True)

    # Filter keys
    school_year = db.Column(db.String(4), nullable=True, index=True)
    date_from = db.Column(db.Date, nullable=True, index=True)
    date_to = db.Column(db.Date, nullable=True, index=True)
    event_types = db.Column(
        db.String(600), nullable=False, index=True
    )  # comma-joined, sorted
    title_filter = db.Column(db.String(255), nullable=True, index=True)

    # Cached JSON payload
    report_data = db.Column(db.JSON, nullable=False)

    last_updated = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "school_year",
            "date_from",
            "date_to",
            "event_types",
            "title_filter",
            name="uq_recent_volunteers_report_cache",
        ),
    )

    def __repr__(self):
        return f"<RecentVolunteersReportCache sy={self.school_year} from={self.date_from} to={self.date_to} types={self.event_types}>"


class VirtualSessionDistrictCache(db.Model):
    """
    Model for caching district-specific virtual session reports.

    This model stores pre-computed district-level virtual session reports
    including monthly breakdowns, school/teacher statistics, and session details.

    Database Table:
        virtual_session_district_cache - Cached district virtual session reports

    Key Features:
        - District-specific report caching
        - Virtual year organization
        - Monthly breakdown data
        - School and teacher statistics
        - Session-level details
        - Automatic timestamp tracking for cache invalidation

    Data Structure:
        - district_name: Name of the district
        - virtual_year: Academic year for virtual sessions
        - date_from, date_to: Optional date range filters
        - session_data: District session data as JSON
        - monthly_stats: Monthly breakdown statistics
        - school_breakdown: School-level statistics
        - teacher_breakdown: Teacher-level statistics
        - summary_stats: Overall district statistics

    Performance Features:
        - Indexed district_name and virtual_year for fast queries
        - Composite index on virtual_year and last_updated
        - Unique constraint prevents duplicate reports
        - Cached data reduces computation time
    """

    __tablename__ = "virtual_session_district_cache"

    id = db.Column(db.Integer, primary_key=True)
    district_name = db.Column(db.String(255), nullable=False, index=True)
    virtual_year = db.Column(
        db.String(9), nullable=False, index=True
    )  # e.g., '2024-2025'
    date_from = db.Column(db.Date, nullable=True)
    date_to = db.Column(db.Date, nullable=True)

    # Cached district report data as JSON
    session_data = db.Column(db.JSON, nullable=False)  # District session records
    monthly_stats = db.Column(db.JSON, nullable=True)  # Monthly breakdown
    school_breakdown = db.Column(db.JSON, nullable=True)  # School statistics
    teacher_breakdown = db.Column(db.JSON, nullable=True)  # Teacher statistics
    summary_stats = db.Column(db.JSON, nullable=True)  # Overall district stats

    last_updated = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "district_name",
            "virtual_year",
            "date_from",
            "date_to",
            name="uq_virtual_session_district_cache",
        ),
        db.Index(
            "idx_district_virtual_year_updated",
            "district_name",
            "virtual_year",
            "last_updated",
        ),
    )

    def __repr__(self):
        return f"<VirtualSessionDistrictCache {self.district_name} {self.virtual_year}>"


class RecruitmentCandidatesCache(db.Model):
    """
    Cache for recruitment candidate recommendations per event.

    Stores the unfiltered candidate list (with scores and reasons) for an
    event so that the UI can apply runtime filters like min_score and limit
    without recomputing heavy queries.
    """

    __tablename__ = "recruitment_candidates_cache"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, nullable=False, index=True, unique=True)

    # Cached JSON payload: list of candidate dicts
    candidates_data = db.Column(db.JSON, nullable=False)

    last_updated = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<RecruitmentCandidatesCache event_id={self.event_id}>"


class DIAEventsReportCache(db.Model):
    """
    Model for caching DIA events report data.

    This model stores pre-computed DIA events reports to improve performance
    when displaying upcoming DIA events with volunteer assignments.

    Database Table:
        dia_events_report_cache - Cached DIA events reports

    Key Features:
        - Caches filled and unfilled DIA events
        - Includes volunteer contact information
        - Automatic timestamp tracking for cache invalidation
        - Single cache entry (no complex filter parameters)

    Data Structure:
        - report_data: Main report data as JSON containing:
            - filled_events: Events with volunteers assigned
            - unfilled_events: Events without volunteers
            - Event details, volunteer info, and contact data

    Performance Features:
        - Single cache entry for fast access
        - Cached data reduces database queries
        - Automatic invalidation after 24 hours
    """

    __tablename__ = "dia_events_report_cache"

    id = db.Column(db.Integer, primary_key=True)

    # Cached JSON payload containing filled and unfilled events
    report_data = db.Column(db.JSON, nullable=False)

    last_updated = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<DIAEventsReportCache updated={self.last_updated}>"

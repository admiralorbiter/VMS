"""
Models Package Initialization
============================

This module initializes the SQLAlchemy database instance and imports all
database models for the Volunteer Management System (VMS). It provides
centralized access to the database and all model classes.

Key Features:
- SQLAlchemy database instance initialization
- Model import management
- Centralized database access
- Model availability exports

Database Configuration:
- Uses Flask-SQLAlchemy for database integration
- Provides single database instance for all models
- Enables model relationships and queries
- Supports database migrations and schema management

Available Models:
- User: User authentication and management
- Volunteer: Volunteer data and relationships
- GoogleSheet: Google Sheets configuration
- Event: Event management and scheduling
- Organization: Organization data and relationships
- Contact: Contact information and addresses
- District: District information and organization
- School: School data and district associations
- Teacher: Teacher information and relationships
- Student: Student data and associations
- History: Activity tracking and audit trails
- Attendance: Attendance tracking and records
- BugReport: Bug report management
- Class: Class data and school associations
- ClientProject: Client project management

- Reports: Report configuration and data
- Validation: Data validation and quality monitoring

Usage:
    from models import db, User, Volunteer, Event
    # Use db for database operations
    # Use model classes for data access
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .attendance import EventAttendanceDetail
from .audit_log import AuditLog
from .bug_report import BugReport
from .class_model import Class
from .client_project_model import ClientProject
from .contact import Contact
from .district_model import District
from .event import Event
from .google_sheet import GoogleSheet
from .history import History
from .organization import Organization
from .reports import DistrictEngagementReport, DistrictYearEndReport, OrganizationReport
from .school_model import School
from .student import Student
from .teacher import Teacher

# Import your models after db initialization
from .user import User

# Import validation models
from .validation import (
    ValidationHistory,
    ValidationMetric,
    ValidationResult,
    ValidationRun,
)
from .volunteer import Volunteer

# Export the things you want to make available when importing from models
__all__ = [
    "db",
    "User",
    "Volunteer",
    "GoogleSheet",
    "AuditLog",
    "Event",
    "Organization",
    "Contact",
    "District",
    "School",
    "Teacher",
    "Student",
    "History",
    "EventAttendanceDetail",
    "BugReport",
    "Class",
    "ClientProject",
    "DistrictYearEndReport",
    "DistrictEngagementReport",
    "OrganizationReport",
    "ValidationRun",
    "ValidationResult",
    "ValidationMetric",
    "ValidationHistory",
]

# Eager-loading helper options
from sqlalchemy.orm import joinedload, selectinload


def eagerload_event_bundle(query):
    """Apply a standard eager-loading bundle for Event-heavy views."""
    from .event import Event

    return query.options(
        selectinload(Event.teacher_registrations),
        selectinload(Event.volunteers),
        selectinload(Event.districts),
        selectinload(Event.skills),
    )


def eagerload_organization_bundle(query):
    """Apply standard eager loading for Organization detail pages."""
    from .organization import Organization

    return query.options(
        selectinload(Organization.volunteers),
        selectinload(Organization.volunteer_organizations),
    )


def eagerload_volunteer_bundle(query):
    """Apply standard eager loading for Volunteer detail pages."""
    from .volunteer import Volunteer

    return query.options(
        selectinload(Volunteer.organizations),
        selectinload(Volunteer.skills),
        selectinload(Volunteer.volunteer_organizations),
    )

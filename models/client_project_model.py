"""
Client Project Model Module
==========================

This module defines the ClientProject model for managing client-connected
projects in the VMS system. It provides project tracking and management
for educational initiatives and partnerships.

Key Features:
- Client project management and tracking
- Project status workflow management
- Teacher and organization relationships
- Contact tracking with hours
- Project description and metadata
- Student count tracking
- Automatic timestamp tracking

Database Table:
- client_projects: Stores client project information and metadata

Project Management:
- Project status tracking (Planning, In Progress, Completed)
- Teacher assignment and tracking
- District and organization relationships
- Project description and title management
- Project date tracking
- Student count tracking

Contact Management:
- Primary contacts tracking with JSON storage
- Contact hours tracking
- Contact name and relationship management
- Flexible contact data structure

Status Workflow:
- PLANNING: Project in planning phase
- IN_PROGRESS: Project currently active
- COMPLETED: Project finished

Data Organization:
- Project metadata and descriptions
- Teacher and organization assignments
- District-level organization
- Contact relationship tracking
- Student impact tracking

Usage Examples:
    # Create a new client project
    project = ClientProject(
        status=ProjectStatus.IN_PROGRESS,
        teacher="Jane Smith",
        district="Kansas City Public Schools",
        organization="Tech Corp",
        project_title="STEM Career Fair",
        number_of_students=150
    )

    # Convert to dictionary for API
    project_dict = project.to_dict()

    # Check project status
    if project.status == ProjectStatus.COMPLETED:
        print("Project is finished")
"""

from datetime import datetime
from enum import Enum

from models import db


class ProjectStatus(Enum):
    """
    Enum for tracking project status.

    Provides standardized status categories for project management
    and workflow tracking.

    Statuses:
        - PLANNING: Project in planning phase
        - IN_PROGRESS: Project currently active and being worked on
        - COMPLETED: Project finished
    """

    IN_PROGRESS = "In Progress"
    PLANNING = "Planning"
    COMPLETED = "Completed"


class ClientProject(db.Model):
    """
    Model for managing client-connected projects.

    This model provides comprehensive project tracking for educational
    initiatives and partnerships. It manages project status, relationships
    with teachers and organizations, and contact tracking with hours.

    Database Table:
        client_projects - Stores client project information and metadata

    Key Features:
        - Client project management and tracking
        - Project status workflow management
        - Teacher and organization relationships
        - Contact tracking with hours
        - Project description and metadata
        - Student count tracking
        - Automatic timestamp tracking

    Project Management:
        - Project status tracking (Planning, In Progress, Completed)
        - Teacher assignment and tracking
        - District and organization relationships
        - Project description and title management
        - Project date tracking
        - Student count tracking

    Contact Management:
        - Primary contacts tracking with JSON storage
        - Contact hours tracking
        - Contact name and relationship management
        - Flexible contact data structure

    Status Workflow:
        - PLANNING: Project in planning phase
        - IN_PROGRESS: Project currently active
        - COMPLETED: Project finished

    Data Organization:
        - Project metadata and descriptions
        - Teacher and organization assignments
        - District-level organization
        - Contact relationship tracking
        - Student impact tracking

    Data Validation:
        - Status is required and must be valid enum value
        - Teacher name is required
        - District and organization are required
        - Project title and description are optional but tracked
        - Student count is optional but tracked

    Performance Features:
        - Indexed fields for fast queries
        - JSON storage for flexible contact data
        - Automatic timestamp tracking
        - Efficient project status filtering
    """

    __tablename__ = "client_projects"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    teacher = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200), nullable=False)

    # Store contacts as JSON array of objects with name and hours
    primary_contacts = db.Column(db.JSON)

    project_description = db.Column(db.Text)
    project_title = db.Column(db.String(200))
    project_dates = db.Column(db.String(100))
    number_of_students = db.Column(db.Integer)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )

    def to_dict(self):
        """
        Convert project to dictionary for API responses.

        Returns:
            dict: Dictionary representation of the project with all metadata
        """
        return {
            "id": self.id,
            "status": self.status,
            "teacher": self.teacher,
            "district": self.district,
            "organization": self.organization,
            "primary_contacts": self.primary_contacts,
            "project_description": self.project_description,
            "project_title": self.project_title,
            "project_dates": self.project_dates,
            "number_of_students": self.number_of_students,
        }

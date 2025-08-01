"""
Virtual Routes Module
====================

This module provides comprehensive functionality for managing virtual sessions
and events in the Volunteer Management System (VMS). It handles virtual event
creation, data import from Google Sheets, and virtual session management.

Key Features:
- Virtual session management and tracking
- Google Sheets data import and processing
- Event creation and updating from CSV data
- Teacher and presenter data processing
- Multiple teacher handling (slash-separated names)
- District and organization association
- Simulcast session handling
- Data validation and error handling

Main Endpoints:
- GET /virtual: Main virtual sessions page
- POST /virtual/purge: Purge virtual session data
- GET /virtual/events: List virtual events
- GET /virtual/event/<id>: Get specific virtual event
- POST /virtual/import-sheet: Import virtual session data from Google Sheets

Virtual Session Processing:
- CSV data parsing and validation
- Event creation from session data
- Teacher and presenter association
- Multiple teacher name splitting and processing
- District and organization linking
- Status tracking and updates
- Simulcast session handling

Data Import Features:
- Google Sheets integration
- CSV data processing
- Batch import with error reporting
- Data validation and cleanup
- Duplicate detection and handling
- Progress tracking and statistics
- Multiple teacher name handling

Event Management:
- Virtual event creation and updates
- Session ID extraction and tracking
- Date/time parsing and validation
- Status mapping and updates
- District and organization associations
- Teacher and presenter relationships
- Multiple teacher event associations

Helper Functions:
- Data cleaning and standardization
- Name parsing and validation
- Teacher name splitting (slash-separated)
- Organization name mapping
- District and school creation
- Session ID extraction
- Status mapping and validation

Security Features:
- Login required for all operations
- Input validation and sanitization
- Error handling with detailed reporting
- Data integrity protection
- Transaction rollback on errors

Dependencies:
- Flask Blueprint for routing
- Google Sheets API integration
- CSV processing with pandas
- Database models for all entities
- Utility functions for data processing
- HTTP requests for external APIs

Models Used:
- Event: Virtual event data and metadata
- District: District information and associations
- Organization: Organization data and relationships
- School: School information and district links
- Teacher: Teacher data and event associations
- Volunteer: Volunteer data and participation
- History: Activity tracking and audit trails
- Contact: Contact information and relationships

Template Dependencies:
- virtual/virtual.html: Main virtual sessions page
- virtual/events.html: Virtual events listing
- virtual/event_detail.html: Individual event view

Teacher Name Processing:
- Supports multiple teachers separated by slashes (e.g., "James Brockway/Megan Gasser")
- Automatic splitting and individual teacher record creation
- Proper event association for each teacher
- School and district assignment for each teacher
- Status tracking per teacher
"""

import traceback
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime, timezone, timedelta
from flask import current_app
from models.district_model import District
from models.event import db, Event, EventType, EventStatus, EventFormat
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from models.teacher import Teacher
from models.volunteer import Volunteer, EventParticipation
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs
from os import getenv
from sqlalchemy import func
import re
from models.history import History
import hashlib
from models.contact import Contact, RaceEthnicityEnum
from models.event import EventTeacher
from models.contact import ContactTypeEnum
from sqlalchemy.orm import joinedload # Import for potential optimization if needed
from routes.reports.common import DISTRICT_MAPPING
from routes.reports.virtual_session import invalidate_virtual_session_caches
import requests
from requests.adapters import HTTPAdapter

virtual_bp = Blueprint('virtual', __name__, url_prefix='/virtual')

@virtual_bp.route('/virtual')
def virtual():
    """
    Display the main virtual sessions page.
    
    Provides the main interface for virtual session management
    and data import operations.
    
    Returns:
        Rendered virtual sessions template
    """
    return render_template('virtual/virtual.html')

def split_teacher_names(teacher_name):
    """
    Split teacher names that may contain multiple teachers separated by slashes.
    
    Args:
        teacher_name: String containing one or more teacher names
        
    Returns:
        list: List of individual teacher name strings
        
    Examples:
        "James Brockway/Megan Gasser" -> ["James Brockway", "Megan Gasser"]
        "John Smith" -> ["John Smith"]
        "Jane Doe / Bob Wilson" -> ["Jane Doe", "Bob Wilson"]
    """
    if not teacher_name or pd.isna(teacher_name):
        return []
    
    teacher_name = safe_str(teacher_name)
    if not teacher_name.strip():
        return []
    
    # Split by slash and clean up each name
    teacher_names = []
    for name in teacher_name.split('/'):
        cleaned_name = name.strip()
        if cleaned_name:
            teacher_names.append(cleaned_name)
    
    return teacher_names

def process_teacher_data(row, is_simulcast=False):
    """
    Helper function to process just teacher data for simulcast/dateless entries.
    
    Processes teacher information from CSV rows that don't have full event data,
    such as simulcast entries or entries without dates.
    
    Args:
        row: Dictionary containing CSV row data
        is_simulcast: Boolean indicating if this is a simulcast entry
        
    Processing:
        - Teacher name parsing and validation
        - Teacher record creation or updating
        - Organization association if available
        - Contact information handling
        - Multiple teacher handling (separated by slashes)
    """
    if not row.get('Teacher Name') or pd.isna(row.get('Teacher Name')):
        return
        
    teacher_names = split_teacher_names(row.get('Teacher Name'))
    
    for teacher_name in teacher_names:
        name_parts = teacher_name.split(' ', 1)
        if len(name_parts) >= 2:
            first_name, last_name = name_parts[0], name_parts[1]
            
            # Find or create teacher
            teacher = Teacher.query.filter(
                func.lower(Teacher.first_name) == func.lower(first_name),
                func.lower(Teacher.last_name) == func.lower(last_name)
            ).first()
            
            if not teacher:
                teacher = Teacher(
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=''
                )
                
                # Handle school association
                school_name = row.get('School Name')
                district_name = row.get('District')
                if school_name:
                    school = get_or_create_school(school_name, get_or_create_district(district_name))
                    teacher.school_id = school.id
                
                db.session.add(teacher)
                db.session.commit()

def process_presenter(row, event, is_simulcast):
    """Helper function to process presenter data"""
    volunteer_id = None
    presenter_name = row.get('Presenter')
    presenter_org = standardize_organization(row.get('Organization', ''))
    people_of_color = row.get('Presenter of Color?', '')
    
    if presenter_name and not pd.isna(presenter_name):
        presenter_name = safe_str(presenter_name)
        first_name, last_name = clean_name(presenter_name)
        
        # Only proceed if we have at least a first name
        if first_name:
            volunteer = find_or_create_volunteer(first_name, last_name, presenter_org, people_of_color)
            
            if volunteer:
                # Create or update participation record
                create_participation(event, volunteer, event.status)
                
                # Handle volunteer association
                update_volunteer_association(event, volunteer, is_simulcast)

def find_or_create_volunteer(first_name, last_name, organization=None, people_of_color=None):
    """Find an existing volunteer or create a new one"""
    # First try exact match on first and last name (case-insensitive)
    volunteer = Volunteer.query.filter(
        func.lower(Volunteer.first_name) == func.lower(first_name),
        func.lower(Volunteer.last_name) == func.lower(last_name)
    ).first()
    
    # If no exact match and we have a last name, try partial matching
    if not volunteer and last_name:
        volunteer = Volunteer.query.filter(
            Volunteer.first_name.ilike(f"{first_name}%"),
            Volunteer.last_name.ilike(f"{last_name}%")
        ).first()
    
    # Create new volunteer if not found
    if not volunteer:
        current_app.logger.info(f"Creating new volunteer: {first_name} {last_name}")
        volunteer = Volunteer(
            first_name=first_name,
            last_name=last_name,
            middle_name='',
            organization_name=organization if not pd.isna(organization) else None,
            is_people_of_color=map_people_of_color(people_of_color)
        )
        db.session.add(volunteer)
        db.session.flush()
    else:
        # Update existing volunteer's organization if it has changed
        if organization and not pd.isna(organization) and organization != volunteer.organization_name:
            volunteer.organization_name = organization
        
        # Update People of Color status only if explicitly "Yes"
        if people_of_color and not pd.isna(people_of_color) and str(people_of_color).strip().lower() == 'yes':
            if not volunteer.is_people_of_color:
                volunteer.is_people_of_color = True
    
    # Create or update organization link if organization is provided
    if organization and not pd.isna(organization):
        # Find or create the organization
        from models.organization import Organization, VolunteerOrganization
        org = Organization.query.filter_by(name=organization).first()
        if not org:
            org = Organization(name=organization)
            db.session.add(org)
            db.session.flush()
        
        # Check if VolunteerOrganization link already exists
        vol_org = VolunteerOrganization.query.filter_by(
            volunteer_id=volunteer.id,
            organization_id=org.id
        ).first()
        
        if not vol_org:
            # Create the missing link
            vol_org = VolunteerOrganization(
                volunteer_id=volunteer.id,
                organization_id=org.id,
                role='Professional',
                is_primary=True,
                status='Current'
            )
            db.session.add(vol_org)
    
    return volunteer

def create_participation(event, volunteer, status):
    """Create or update participation record"""
    participation = EventParticipation.query.filter_by(
        event_id=event.id,
        volunteer_id=volunteer.id
    ).first()
    
    if not participation:
        # Define participation data
        participation_data = {
            'event_id': event.id,
            'volunteer_id': volunteer.id,
            'participant_type': 'Presenter',
            'status': 'Completed' if status == EventStatus.COMPLETED else 'Confirmed'
        }
        
        # Try to set delivery_hours if that field exists
        try:
            participation = EventParticipation(**participation_data)
            if hasattr(EventParticipation, 'delivery_hours'):
                participation.delivery_hours = event.duration / 60 if event.duration else 1
        except Exception as e:
            current_app.logger.warning(f"Could not set hours on EventParticipation: {e}")
            participation = EventParticipation(**participation_data)
        
        db.session.add(participation)
    else:
        # Update existing participation record
        participation.status = 'Completed' if status == EventStatus.COMPLETED else 'Confirmed'
        participation.participant_type = 'Presenter'
        if hasattr(EventParticipation, 'delivery_hours'):
            participation.delivery_hours = event.duration / 60 if event.duration else 1

def update_volunteer_association(event, volunteer, is_simulcast):
    """Update volunteer associations for an event"""
    # Before adding new volunteer to event's volunteers list, clear existing ones
    if not is_simulcast:  # Only clear for non-simulcast events
        event.volunteers = []  # Clear existing volunteer associations
        if hasattr(event, 'professionals'):
            event.professionals = ''  # Clear text-based professionals field
        if hasattr(event, 'professional_ids'):
            event.professional_ids = ''  # Clear professional IDs field
    
    # Add volunteer to event's volunteers list if not already there
    if volunteer not in event.volunteers:
        event.volunteers.append(volunteer)
    
    # Also update text-based fields for backwards compatibility
    update_legacy_fields(event, volunteer)

def update_legacy_fields(event, volunteer):
    """Update legacy text-based fields for backward compatibility"""
    if hasattr(event, 'professionals'):
        current_profs = []
        if event.professionals:
            current_profs = [p.strip() for p in event.professionals.split(';') if p.strip()]
        prof_name = f"{volunteer.first_name} {volunteer.last_name}"
        if prof_name not in current_profs:
            current_profs.append(prof_name)
            event.professionals = '; '.join(current_profs)
    
    if hasattr(event, 'professional_ids'):
        current_ids = []
        if event.professional_ids:
            current_ids = [id.strip() for id in event.professional_ids.split(';') if id.strip()]
        if str(volunteer.id) not in current_ids:
            current_ids.append(str(volunteer.id))
            event.professional_ids = '; '.join(current_ids)

def process_teacher_for_event(row, event, is_simulcast):
    """Process teacher data for a specific event"""
    # Check if teacher name exists and is not a NaN value
    if not row.get('Teacher Name') or pd.isna(row.get('Teacher Name')):
        return
        
    teacher_names = split_teacher_names(row.get('Teacher Name'))
    
    for teacher_name in teacher_names:
        name_parts = teacher_name.split(' ', 1)
        if len(name_parts) >= 2:
            first_name, last_name = name_parts[0], name_parts[1]
            
            # Find or create teacher
            teacher = Teacher.query.filter(
                func.lower(Teacher.first_name) == func.lower(first_name),
                func.lower(Teacher.last_name) == func.lower(last_name)
            ).first()
            
            if not teacher:
                teacher = Teacher(
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=''
                )
                
                # Handle school association
                school_name = row.get('School Name')
                district_name = row.get('District')
                if school_name and not pd.isna(school_name):
                    district = get_or_create_district(district_name) if district_name else None
                    school = get_or_create_school(school_name, district)
                    if school:  # Only set school_id if school exists
                        teacher.school_id = school.id
                
                db.session.add(teacher)
                db.session.flush()
            else:
                # Update existing teacher's school association if it has changed
                school_name = row.get('School Name')
                district_name = row.get('District')
                if school_name and not pd.isna(school_name):
                    district = get_or_create_district(district_name) if district_name else None
                    school = get_or_create_school(school_name, district)
                    if school and school.id != teacher.school_id:
                        teacher.school_id = school.id

            # Create or update teacher participation record
            event_teacher = EventTeacher.query.filter_by(
                event_id=event.id,
                teacher_id=teacher.id
            ).first()
            
            if not event_teacher:
                event_teacher = EventTeacher(
                    event_id=event.id,
                    teacher_id=teacher.id,
                    status=row.get('Status'),
                    is_simulcast=is_simulcast,
                    attendance_confirmed_at=datetime.now(timezone.utc) if event.status == EventStatus.COMPLETED else None
                )
                db.session.add(event_teacher)
            else:
                # Update existing teacher participation record
                event_teacher.status = row.get('Status')
                event_teacher.is_simulcast = is_simulcast
                if event.status == EventStatus.COMPLETED and not event_teacher.attendance_confirmed_at:
                    event_teacher.attendance_confirmed_at = datetime.now(timezone.utc)
                elif event.status != EventStatus.COMPLETED:
                    event_teacher.attendance_confirmed_at = None

def add_district_to_event(event, district_name):
    """Gets or creates the district and adds it to the event's districts list if not already present."""
    district = get_or_create_district(district_name)
    if district:
        # print(f"DEBUG: Adding district '{district.name}' (ID: {district.id}, Type: {type(district.id)}) to event '{event.title}'")
        
        # Check if district is already associated by ID
        if not any(d.id == district.id for d in event.districts):
            event.districts.append(district)
            # print(f"DEBUG: Successfully added district '{district.name}' to event '{event.title}'")
    else:
        print(f"DEBUG: Failed to get/create district for name: '{district_name}'")

@virtual_bp.route('/purge', methods=['POST'])
@login_required
def purge_virtual():
    """Remove all virtual session records and related data"""
    try:
        # Get all virtual session event IDs first
        virtual_event_ids = db.session.query(Event.id).filter(
            Event.type == EventType.VIRTUAL_SESSION
        ).all()
        virtual_event_ids = [event_id[0] for event_id in virtual_event_ids]
        
        # Delete event-teacher associations for virtual sessions
        event_teacher_deleted = 0
        if virtual_event_ids:
            event_teacher_deleted = EventTeacher.query.filter(
                EventTeacher.event_id.in_(virtual_event_ids)
            ).delete(synchronize_session=False)
        
        # Delete event participations for virtual sessions (presenters/volunteers)
        event_participation_deleted = 0
        if virtual_event_ids:
            event_participation_deleted = EventParticipation.query.filter(
                EventParticipation.event_id.in_(virtual_event_ids)
            ).delete(synchronize_session=False)
        
        # Then delete the virtual session events
        deleted_count = Event.query.filter_by(
            type=EventType.VIRTUAL_SESSION
        ).delete(synchronize_session=False)
        
        # Clean up orphaned teachers that were only created for virtual sessions
        # Find teachers who have no remaining event associations
        orphaned_teachers = Teacher.query.filter(
            ~Teacher.event_registrations.any()
        ).all()
        
        teacher_deleted_count = 0
        for teacher in orphaned_teachers:
            # Only delete teachers who were likely created for virtual sessions
            # (teachers without schools or with minimal data)
            if not teacher.school_id or not teacher.department:
                db.session.delete(teacher)
                teacher_deleted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully purged {deleted_count} virtual sessions, {teacher_deleted_count} orphaned teachers, {event_teacher_deleted} teacher associations, and {event_participation_deleted} event participations',
            'count': deleted_count,
            'teachers_deleted': teacher_deleted_count,
            'event_teachers_deleted': event_teacher_deleted,
            'event_participations_deleted': event_participation_deleted
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Purge failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/events', methods=['GET'])
@login_required
def list_events():
    """List all virtual events with their associated teachers and presenters"""
    try:
        events = Event.query.filter_by(
            type=EventType.VIRTUAL_SESSION
        ).order_by(Event.start_date.desc()).all()
        
        events_data = []
        for event in events:
            # Get all teacher participants
            teacher_data = [{
                'id': et.teacher_id,
                'name': f"{et.teacher.first_name} {et.teacher.last_name}",
                'school': et.teacher.school.name if et.teacher.school else None,
                'status': et.status,
                'is_simulcast': et.is_simulcast
            } for et in event.teacher_registrations]
            
            events_data.append({
                'id': event.id,
                'title': event.title,
                'date': event.start_date.strftime('%Y-%m-%d') if event.start_date else None,
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else None,
                'status': event.status,
                'session_type': event.additional_information,
                'topic': event.series,
                'session_link': event.registration_link,
                'presenter_name': event.presenter_name,
                'presenter_organization': event.presenter_organization,
                'presenter_location_type': event.presenter_location_type,
                'teachers': teacher_data
            })
        
        return jsonify({
            'success': True,
            'events': events_data
        })
        
    except Exception as e:
        current_app.logger.error("Error fetching events", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/event/<int:event_id>', methods=['GET'])
@login_required
def get_event(event_id):
    """Get detailed information about a specific virtual event"""
    try:
        event = Event.query.filter_by(
            id=event_id,
            type=EventType.VIRTUAL_SESSION
        ).first_or_404()
        
        # Get teacher participation details
        teacher_data = [{
            'id': et.teacher_id,
            'name': f"{et.teacher.first_name} {et.teacher.last_name}",
            'school': et.teacher.school.name if et.teacher.school else None,
            'status': et.status,
            'is_simulcast': et.is_simulcast
        } for et in event.teacher_registrations]
        
        return jsonify({
            'success': True,
            'event': {
                'id': event.id,
                'title': event.title,
                'date': event.start_date.strftime('%Y-%m-%d') if event.start_date else None,
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else None,
                'status': event.status,
                'session_type': event.additional_information,
                'topic': event.series,
                'session_link': event.registration_link,
                'presenter_name': event.presenter_name,
                'presenter_organization': event.presenter_organization,
                'presenter_location_type': event.presenter_location_type,
                'teachers': teacher_data
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching event {event_id}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def clean_name(name):
    """More robust name cleaning function"""
    if not name or pd.isna(name):
        return '', ''
    
    name = str(name).strip()
    
    # Handle common prefixes
    prefixes = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.']
    for prefix in prefixes:
        if name.lower().startswith(prefix):
            name = name[len(prefix):].strip()
    
    # Split name into parts
    parts = [p for p in name.split() if p]
    
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return parts[0], ''
    else:
        # For simplicity in matching, use first part as first name
        # and last part as last name (helps match with database)
        return parts[0], parts[-1]

def standardize_organization(org_name):
    """Standardize organization names"""
    if not org_name or pd.isna(org_name):
        return None
    
    org_name = str(org_name).strip()
    # Add common replacements
    replacements = {
        "IBM CORPORATION": "IBM",
        "HILL'S PET NUTRITION INC": "Hill's Pet Nutrition",
        # Add more as needed
    }
    return replacements.get(org_name.upper(), org_name)

def parse_datetime(date_str, time_str):
    """Parse datetime with support for virtual session year (July 1st to July 1st)"""
    try:
        if pd.isna(date_str):
            return None
            
        # Clean and parse date
        date_str = str(date_str).strip()
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) >= 2:
                month = int(parts[0])
                day = int(parts[1])
                
                # For virtual sessions (July 1st to July 1st):
                # - If month is July (7) or later, use current year
                # - If month is before July, use next year
                current_year = 2024 if month >= 7 else 2025  # Changed from >= 6 to >= 7
                
                # Parse time
                time_obj = clean_time_string(time_str) if time_str and not pd.isna(time_str) and str(time_str).strip() else None
                
                if time_obj:
                    # We have both date and time
                    try:
                        return datetime(
                            current_year,
                            month,
                            day,
                            time_obj.hour,
                            time_obj.minute
                        )
                    except ValueError:
                        current_app.logger.warning(f"Invalid date components: {month}/{day}/{current_year}")
                        return None
                else:
                    # We only have date, return None - the calling code will handle finding the event
                    return None
                    
        return None
    except Exception as e:
        current_app.logger.warning(f"Error parsing datetime: {e}")
        return None

def clean_string_value(value):
    """Convert any value to string safely"""
    if pd.isna(value) or value is None:
        return ''
    # Handle float or numeric values
    if isinstance(value, (float, int)):
        return str(value)
    return str(value).strip()

def clean_status(status):
    """Clean status value"""
    if pd.isna(status) or status is None:
        return ''
    return str(status).strip()

def get_or_create_district(name):
    """
    Get or create district by name, attempting to match aliases and standard names
    from DISTRICT_MAPPING to avoid creating duplicates.
    """
    if pd.isna(name) or not name or str(name).strip() == '':
        effective_name = 'Unknown District'
        target_salesforce_id = None
    else:
        effective_name = str(name).strip()
        target_salesforce_id = None

        # --- Attempt to map the input name to a canonical Salesforce ID ---
        name_lower = effective_name.lower()
        for sf_id, mapping_info in DISTRICT_MAPPING.items():
            # Check exact canonical name
            if mapping_info['name'].lower() == name_lower:
                target_salesforce_id = sf_id
                effective_name = mapping_info['name'] # Use the canonical name
                # REMOVED: Success log - print(f"    Mapped input '{name}' to canonical name '{effective_name}' via exact match (SFID: {sf_id})")
                break
            # Check aliases
            if 'aliases' in mapping_info:
                for alias in mapping_info['aliases']:
                    if alias.lower() == name_lower:
                        target_salesforce_id = sf_id
                        effective_name = mapping_info['name'] # Use the canonical name
                        # REMOVED: Success log - print(f"    Mapped input '{name}' to canonical name '{effective_name}' via alias '{alias}' (SFID: {sf_id})")
                        break
            if target_salesforce_id: # Stop searching if mapped
                break
        # --- End Mapping Attempt ---

    district = None
    # If we mapped to a Salesforce ID, prioritize finding the district by that ID
    if target_salesforce_id:
        district = District.query.filter_by(salesforce_id=target_salesforce_id).first()
        if district:
            # REMOVED: Success log - print(f"    Found existing district by mapped Salesforce ID: '{district.name}' (ID: {district.id})")
            pass

    # If not found by Salesforce ID (or no mapping occurred), try finding by the effective name (case-insensitive)
    if not district:
        district = District.query.filter(func.lower(District.name) == func.lower(effective_name)).first()
        if district:
             # REMOVED: Success log - print(f"    Found existing district by name lookup: '{district.name}' (ID: {district.id})")
             pass

    # Only create a new district if absolutely not found and it's not 'Unknown District'
    if not district and effective_name != 'Unknown District':
        # Only log when creating new districts (this could be worth knowing about)
        print(f"INFO: Creating new district: '{effective_name}'")
        # We create it without a Salesforce ID because we couldn't map it
        district = District(name=effective_name)
        db.session.add(district)
        db.session.flush() # Flush to assign an ID

    # Handle 'Unknown District' case - find or create the specific 'Unknown' record
    elif not district and effective_name == 'Unknown District':
         district = District.query.filter(func.lower(District.name) == 'unknown district').first()
         if not district:
              # Only log when creating Unknown District for the first time
              print(f"INFO: Creating 'Unknown District'")
              district = District(name='Unknown District')
              db.session.add(district)
              db.session.flush()

    return district

def safe_str(value):
    """Safely convert a value to string, handling NaN and None"""
    if pd.isna(value) or value is None:
        return ''
    return str(value)

def map_people_of_color(value):
    """Map People of Color column value to boolean"""
    if pd.isna(value) or not value or str(value).strip() == '':
        return False
    
    value_str = str(value).strip().lower()
    
    # Map "Yes" to True, everything else to False
    return value_str == 'yes'

def map_status(status_str):
    """Enhanced status mapping"""
    status_str = safe_str(status_str).strip().lower()
    
    # Add mappings for additional status values
    status_mapping = {
        'simulcast': EventStatus.SIMULCAST,
        'technical difficulties': EventStatus.NO_SHOW,
        'count': EventStatus.COUNT,
        'local professional no-show': EventStatus.NO_SHOW,
        'pathful professional no-show': EventStatus.NO_SHOW,
        'teacher no-show': EventStatus.NO_SHOW,
        'teacher cancelation': EventStatus.CANCELLED,
        'successfully completed': EventStatus.COMPLETED
    }
    
    return status_mapping.get(status_str, EventStatus.DRAFT)

@virtual_bp.route('/import-sheet', methods=['POST'])
@login_required
def import_sheet():
    try:
        data = request.get_json() or {}
        academic_year = data.get('academic_year')
        if not academic_year:
            return jsonify({'success': False, 'error': 'Academic year is required.'}), 400
        from models.google_sheet import GoogleSheet
        sheet_record = GoogleSheet.query.filter_by(academic_year=academic_year, purpose='virtual_sessions').first()
        if not sheet_record:
            return jsonify({'success': False, 'error': f'No Google Sheet configured for academic year {academic_year}'}), 400
        sheet_id = sheet_record.decrypted_sheet_id
        if not sheet_id:
            return jsonify({'success': False, 'error': f'Google Sheet ID for {academic_year} could not be decrypted or is missing.'}), 400
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Use requests with streaming
        response = requests.get(csv_url, stream=True)
        response.raise_for_status()
        
        # Read the CSV in chunks
        chunks = []
        chunk_size = 8192  # 8KB chunks
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                chunks.append(chunk)
        
        # Combine chunks and read as CSV
        content = b''.join(chunks)
        df = pd.read_csv(
            pd.io.common.BytesIO(content),
            skiprows=3,
            dtype={'School Name': str}
        )
        
        # Only show summary, not detailed processing info
        print(f"\n=== Starting Import: {len(df)} rows ===")

        # session_datetimes is less critical now as we primarily rely on row's datetime
        # Keep it for potential logging or edge-case handling if needed, but the core logic
        # will rely on parsing datetime per row in the second pass.
        session_datetimes = {}
        # REMOVED: First pass detailed logging - only calculate datetimes
        for index, row in df.iterrows():
            title = clean_string_value(row.get('Session Title'))
            date_str = row.get('Date')
            time_str = row.get('Time')

            if title and not pd.isna(date_str):
                event_datetime = parse_datetime(date_str, time_str)
                if event_datetime:
                    date_key = event_datetime.date().isoformat()
                    datetime_key = event_datetime.isoformat() # Store full datetime key too
                    if title not in session_datetimes:
                        session_datetimes[title] = {}
                    if date_key not in session_datetimes[title]:
                         session_datetimes[title][date_key] = []
                    # Store all datetimes found for this title/date combination
                    if datetime_key not in [d['datetime_iso'] for d in session_datetimes[title][date_key]]:
                        session_datetimes[title][date_key].append({'datetime': event_datetime, 'datetime_iso': datetime_key})

        success_count = warning_count = error_count = 0
        errors = []
        # Use Event ID cache to handle multiple rows for the same event
        # Key format: (title, datetime_iso_string)
        processed_event_ids = {}
        # Convert DataFrame rows to a list of dictionaries for easier lookup
        all_rows_for_lookup = df.to_dict('records')

        # --- Second Pass: Process each row ---
        # REMOVED: "Processing Rows" header
        primary_logic_already_run = {}  # Track if primary logic has run for each event instance
        for row_index, row_data in enumerate(all_rows_for_lookup):
            event_processed_in_this_row = False # Flag to track if event logic ran
            try:
                # Extract key fields safely
                status_str = safe_str(row_data.get('Status', '')).lower().strip()
                is_simulcast = status_str == 'simulcast'
                title = clean_string_value(row_data.get('Session Title'))

                if not title:
                    print(f"ERROR - Row {row_index + 1}: No Session Title")
                    warning_count += 1
                    errors.append(f"Skipped row {row_index + 1}: Missing Session Title")
                    continue

                # Determine the event context (datetime) for this row
                current_datetime = None
                date_str = row_data.get('Date')
                time_str = row_data.get('Time')

                # Try parsing date/time from the current row
                if not pd.isna(date_str):
                    parsed_dt = parse_datetime(date_str, time_str)
                    if parsed_dt:
                        current_datetime = parsed_dt
                        # REMOVED: Successful parsing log
                    else:
                        # If parsing failed (likely due to missing time), try to find existing event
                        date_parts = str(date_str).strip().split('/')
                        if len(date_parts) >= 2:
                            try:
                                month = int(date_parts[0])
                                day = int(date_parts[1])
                                current_year = 2024 if month >= 7 else 2025
                                target_date = datetime(current_year, month, day).date()
                                
                                # Find existing event for this title and date
                                existing_event = Event.query.filter(
                                    func.lower(Event.title) == func.lower(title.strip()),
                                    func.date(Event.start_date) == target_date,
                                    Event.type == EventType.VIRTUAL_SESSION
                                ).first()
                                
                                if existing_event:
                                    # Use the existing event's datetime
                                    current_datetime = existing_event.start_date
                                    # REMOVED: Success log
                                    
                            except (ValueError, IndexError):
                                pass
                    
                # If we can't determine event context (datetime), we can only process teacher data standalone.
                if not current_datetime:
                    if row_data.get('Teacher Name') and not pd.isna(row_data.get('Teacher Name')):
                         print(f"WARNING - Row {row_index + 1} ('{title}'): No valid event datetime found. Processing TEACHER ONLY.")
                         process_teacher_data(row_data, is_simulcast)
                    else:
                         print(f"ERROR - Row {row_index + 1} ('{title}'): Cannot determine event datetime and no teacher name.")
                         warning_count += 1
                         errors.append(f"Skipped row {row_index + 1} ('{title}'): Cannot determine event datetime.")
                    continue


                # --- Event Handling ---
                # Use title and the full datetime ISO string as the unique key
                event_key = (title, current_datetime.isoformat())
                event = None
                event_id = processed_event_ids.get(event_key)

                if event_id:
                    # Fetch fresh event object from session/DB using cached ID
                    event = db.session.get(Event, event_id)
                    if event:
                         # REMOVED: Cache hit success log
                         pass
                    else:
                         print(f"WARNING - Row {row_index + 1}: Event ID {event_id} found in cache for '{title}' at {current_datetime.isoformat()}, but not in DB session. Querying DB.")
                         # Fall through to DB query if session.get fails unexpectedly

                if not event:
                    # Query DB if not found via cache or if session.get failed
                    # *** UPDATED QUERY: Filter by exact start_date (datetime) ***
                    # REMOVED: DB query log
                    event = Event.query.filter(
                        func.lower(Event.title) == func.lower(title.strip()),
                        Event.start_date == current_datetime, # Compare full datetime
                        Event.type == EventType.VIRTUAL_SESSION
                    ).first()

                    if event:
                        # Found in DB, cache its ID
                        processed_event_ids[event_key] = event.id
                        # REMOVED: DB found success log
                        
                        # Update session_host for existing events if not set
                        if not event.session_host or event.session_host != 'PREPKC':
                            event.session_host = 'PREPKC'
                            print(f"UPDATED existing virtual event {event.id} ({event.title}) with session_host: PREPKC")
                    else:
                        # Modified logic: Allow certain "incomplete" statuses to create events
                        # when no existing event is found
                        can_create_event_statuses = [
                            'teacher no-show',
                            'teacher cancelation', 
                            'local professional no-show',
                            'pathful professional no-show',
                            'technical difficulties',
                            'count'
                        ]
                        
                        is_primary_row_status = status_str not in ['simulcast', '']
                        can_create_incomplete_event = status_str in can_create_event_statuses
                        
                        if is_primary_row_status or can_create_incomplete_event:
                            # REMOVED: Event creation success log
                            event = Event(
                                title=title,
                                start_date=current_datetime, # Use precise datetime
                                # Basic duration logic, refine if needed
                                end_date=current_datetime.replace(hour=current_datetime.hour+1) if current_datetime else None,
                                duration=60,
                                type=EventType.VIRTUAL_SESSION,
                                format=EventFormat.VIRTUAL,
                                status=EventStatus.map_status(status_str), # Status from creating row
                                original_status_string=status_str,  # Store original status string
                                session_id=extract_session_id(row_data.get('Session Link')),
                                session_host='PREPKC'  # Set default host for virtual sessions
                            )
                            db.session.add(event)
                            db.session.flush() # Flush to get the new event.id
                            processed_event_ids[event_key] = event.id # Cache using the datetime key
                            # REMOVED: New event ID success log
                        else:
                            # This row is truly secondary (simulcast, count, empty), but no existing event found.
                            # Process teacher data standalone if it exists.
                            print(f"WARNING - Row {row_index + 1} ('{title}'): Secondary status '{status_str}' but no existing event found for datetime {current_datetime.isoformat()}. Processing TEACHER ONLY.")
                            if row_data.get('Teacher Name') and not pd.isna(row_data.get('Teacher Name')):
                                process_teacher_data(row_data, is_simulcast)
                            continue # Skip further event processing for this row


                # If we don't have an event object here, something went wrong or it was skipped above
                if not event:
                    print(f"ERROR - Row {row_index + 1} ('{title}'): Could not find or create event for datetime {current_datetime.isoformat()}.")
                    warning_count += 1
                    errors.append(f"Skipped row {row_index + 1} ('{title}'): Could not find or create event for {current_datetime.isoformat()}.")
                    continue

                # --- District Handling (should run for EVERY row with a district) ---
                # Move this OUTSIDE the primary logic block
                if row_data.get('District') and not pd.isna(row_data.get('District')):
                    district_name = safe_str(row_data.get('District'))
                    if district_name:
                        # Check if this district is already associated with this event
                        existing_district = next((d for d in event.districts if d.name == district_name), None)
                        if not existing_district:
                            add_district_to_event(event, district_name)
                            #print(f"DEBUG: Added district '{district_name}' to event '{event.title}' from row {row_index + 1}")

                # --- Primary Logic Block ---
                # Run this block only ONCE per specific event instance (title + datetime)
                primary_logic_run_key = (title, current_datetime.isoformat())
                if is_primary_row_status and not primary_logic_already_run.get(primary_logic_run_key, False):
                    event_processed_in_this_row = True
                    # Get the date key for aggregation (date part only)
                    current_date_key = current_datetime.date().isoformat()
                    # REMOVED: Primary logic processing header
                    primary_logic_already_run[primary_logic_run_key] = True # Mark primary logic as done for this event instance

                    # --- Participant Count Calculation (Based on Title and DATE ONLY, requires School Name) ---
                    # REMOVED: Participant count calculation log
                    qualifying_teacher_rows_count = 0
                    event.participant_count = 0 # Reset count for this specific event instance

                    # Iterate through all rows again specifically for participant count calculation
                    for lookup_row_index_pc, lookup_row_data_pc in enumerate(all_rows_for_lookup):
                        lookup_title_pc = clean_string_value(lookup_row_data_pc.get('Session Title'))

                        # Fast skip if title doesn't match
                        if lookup_title_pc != title:
                            continue

                        # --- Attempt to parse DATE ONLY from the lookup row ---
                        lookup_date_str_pc = lookup_row_data_pc.get('Date')
                        lookup_date_key_pc = None # Reset for each lookup row
                        if not pd.isna(lookup_date_str_pc):
                            try:
                                date_str_cleaned_pc = str(lookup_date_str_pc).strip()
                                if '/' in date_str_cleaned_pc:
                                    parts_pc = date_str_cleaned_pc.split('/')
                                    if len(parts_pc) >= 2:
                                        month_str_pc, day_str_pc = parts_pc[0], parts_pc[1]
                                        if month_str_pc.isdigit() and day_str_pc.isdigit():
                                            month_pc = int(month_str_pc)
                                            day_pc = int(day_str_pc)
                                            if 1 <= month_pc <= 12 and 1 <= day_pc <= 31:
                                                # Determine virtual session year (July 1st to July 1st)
                                                current_dt_utc_pc = datetime.now(timezone.utc)
                                                if current_dt_utc_pc.month >= 7:  # Changed from >= 6 to >= 7
                                                    year_pc = current_dt_utc_pc.year if month_pc >= 7 else current_dt_utc_pc.year + 1  # Changed from >= 6 to >= 7
                                                else:
                                                    year_pc = current_dt_utc_pc.year - 1 if month_pc >= 7 else current_dt_utc_pc.year  # Changed from >= 6 to >= 7
                                                try:
                                                    date_obj_only_pc = datetime(year_pc, month_pc, day_pc).date()
                                                    lookup_date_key_pc = date_obj_only_pc.isoformat()
                                                except ValueError:
                                                    pass # Invalid date components
                            except Exception as e_pc:
                                # REMOVED: Date parsing error log (too verbose)
                                lookup_date_key_pc = None
                        # --- End Date Only Parsing ---


                        # Skip if date doesn't match the current event's date key
                        if lookup_date_key_pc != current_date_key:
                            continue

                        # Now check status, teacher presence, AND school presence
                        lookup_status_str_pc = safe_str(lookup_row_data_pc.get('Status', '')).lower().strip()
                        lookup_teacher_name_pc = lookup_row_data_pc.get('Teacher Name')
                        lookup_school_name_pc = lookup_row_data_pc.get('School Name') # Get School Name

                        if (lookup_status_str_pc in ['successfully completed', 'simulcast'] and
                            lookup_teacher_name_pc and not pd.isna(lookup_teacher_name_pc) and
                            lookup_school_name_pc and not pd.isna(lookup_school_name_pc)): # Added check for non-empty School Name
                            # REMOVED: Qualification success log
                            qualifying_teacher_rows_count += 1

                    # Update the event's participant count
                    event.participant_count = qualifying_teacher_rows_count * 25
                    # REMOVED: Participant count success log
                    # --- End Participant Count Calculation ---


                    # Update core event details from this primary row
                    event.status = EventStatus.map_status(status_str)
                    event.original_status_string = status_str  # Store original status string
                    event.session_id = extract_session_id(row_data.get('Session Link'))
                    
                    # Update title if it has changed
                    if row_data.get('Session Title') and row_data.get('Session Title') != event.title:
                        event.title = row_data.get('Session Title')
                    
                    # Update other fields using existing Event model fields
                    event.series = row_data.get('Topic/Theme')  # Use series instead of topic
                    event.additional_information = row_data.get('Session Type')  # Store session type in additional_information
                    event.registration_link = row_data.get('Session Link')  # Use registration_link instead of session_link
                    
                    # Update date/time if they have changed (be careful with timezone handling)
                    if current_datetime and current_datetime != event.start_date:
                        event.start_date = current_datetime
                        event.end_date = current_datetime + timedelta(hours=1)  # Default 1 hour duration
                    
                    # Always ensure session_host is set
                    if not event.session_host:
                        event.session_host = 'PREPKC'

                    # --- School Handling (following events import pattern) ---
                    primary_school_name = row_data.get('School Name')
                    if primary_school_name and not pd.isna(primary_school_name):
                        # Get district for school creation context (prefer event's primary district)
                        school_district = None
                        if event.district_partner:
                            school_district = get_or_create_district(event.district_partner)

                        school = get_or_create_school(primary_school_name, school_district)
                        if school:
                            event.school = school.id
                            # REMOVED: School setting success log

                    # --- Presenter/Volunteer Handling (moved to run for all rows) ---
                    # Note: Presenter processing is now handled outside the primary logic block
                    # to ensure POC data is processed for all rows, including simulcast rows

                    # --- Update Metrics (if applicable, from primary row) ---
                    if event.status == EventStatus.COMPLETED:
                        # REMOVED: Metrics update log
                        # Set default metrics if not already set, or adjust as needed
                        # event.participant_count = event.participant_count or 0 # Handled above
                        event.registered_count = event.registered_count or 0
                        event.attended_count = event.attended_count or 0 # Keep attended_count separate? Or set it equal to participant_count? Let's keep it separate for now.
                        event.volunteers_needed = event.volunteers_needed or 1
                        if not event.duration: event.duration = 60

                    # REMOVED: Primary logic completion log


                # --- Teacher Processing (runs for EVERY row with a teacher associated with THIS event instance) ---
                # This check implicitly relies on the 'event' object being correctly identified for the row's datetime
                if row_data.get('Teacher Name') and not pd.isna(row_data.get('Teacher Name')):
                     # REMOVED: Teacher processing log
                     # Pass the correct 'is_simulcast' flag for the *current row*
                     # Associate teacher with the specific event instance found/created above
                     process_teacher_for_event(row_data, event, is_simulcast)

                # --- Presenter Processing (runs for EVERY row with a presenter, regardless of primary logic) ---
                # This ensures POC data is processed for all rows, including simulcast rows
                presenter_name = row_data.get('Presenter')
                if presenter_name and not pd.isna(presenter_name):
                    # REMOVED: Presenter processing log
                    process_presenter(row_data, event, is_simulcast)


                # Commit changes potentially made in this iteration (event creation/update, teacher association)
                db.session.commit()
                if event_processed_in_this_row: # Count success if primary event logic ran
                     success_count += 1
                # Decide how to count success if only teacher was processed (currently not counted)


            except Exception as e:
                 db.session.rollback() # Rollback on error for the specific row
                 error_count += 1
                 title_for_error = clean_string_value(row_data.get('Session Title', 'Unknown'))
                 dt_str = current_datetime.isoformat() if 'current_datetime' in locals() and current_datetime else "Unknown Time"
                 error_msg = f"ERROR - Row {row_index + 1} for '{title_for_error}' at {dt_str}: {str(e)}"
                 print(error_msg)
                 errors.append(error_msg)
                 current_app.logger.error(f"Import error processing row {row_index + 1} for '{title_for_error}' at {dt_str}: {e}", exc_info=True)
                 # Ensure current_datetime is cleared or handled for the next iteration if error occurred mid-process
                 current_datetime = None

        # Summary of results
        print(f"\n=== Import Complete ===")
        print(f"Success: {success_count} events processed (new + updated)")
        print(f"Warnings: {warning_count}")  
        print(f"Errors: {error_count}")
        if errors:
            print(f"Error details: {len(errors)} total issues")
        print("💡 Note: Import updates existing events with latest data - no purge needed!")
        print("========================")
        
        # Invalidate virtual session caches to ensure reports show updated data
        try:
            invalidate_virtual_session_caches()
            print("✅ Virtual session caches invalidated - reports will show fresh data")
        except Exception as e:
            print(f"⚠️ Warning: Could not invalidate caches: {str(e)}")
        
        return jsonify({
            'success': True,
            'successCount': success_count, # Note: Success count reflects primary event logic runs
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback() # Rollback any remaining transaction on overall failure
        current_app.logger.error("Sheet import failed", exc_info=True)
        error_msg = f"Overall import failed: {str(e)}"
        print(f"CRITICAL ERROR: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 400

def clean_time_string(time_str):
    """Clean and validate time string - handles multiple formats"""
    if not time_str or pd.isna(time_str):
        return None
    
    time_str = str(time_str).strip()
    if not time_str:
        return None
        
    # Remove duplicate AM/PM
    time_str = time_str.replace(' PM PM', ' PM').replace(' AM AM', ' AM')
    
    # Try different time formats
    time_formats = [
        '%I:%M %p',    # 11:00 AM, 2:30 PM
        '%H:%M',       # 14:30, 09:30 (24-hour format)
        '%I:%M',       # 11:00, 2:30 (12-hour without AM/PM)
        '%H:%M:%S',    # 14:30:00
        '%I:%M:%S %p', # 11:00:00 AM
        '%I %p',       # 11 AM
        '%H'           # 14 (just hour)
    ]
    
    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            # If it's a format without AM/PM and hour is <= 12, assume AM for morning times
            if fmt in ['%I:%M', '%H:%M'] and parsed_time.hour <= 12:
                # For times like "9:30", assume it's AM if <= 12
                return parsed_time
            elif fmt in ['%I:%M', '%H:%M'] and parsed_time.hour > 12:
                # For times > 12 without AM/PM, treat as 24-hour format
                return parsed_time
            else:
                return parsed_time
        except ValueError:
            continue
    
    # If all formats fail, log warning and return None
    current_app.logger.warning(f"Invalid time format: {time_str}")
    return None

def generate_school_id(name):
    """Generate a unique ID for virtual schools that matches Salesforce length"""
    if pd.isna(name) or not name:
        name = "Unknown School"
    
    # Ensure name is a string
    name = str(name).strip()
    
    timestamp = datetime.now(timezone.utc).strftime('%y%m%d')
    name_hash = hashlib.sha256(name.lower().encode()).hexdigest()[:8]
    base_id = f"VRT{timestamp}{name_hash}"
    
    # Ensure exactly 18 characters
    base_id = base_id[:18].ljust(18, '0')
    
    # Check if ID exists and append counter if needed
    counter = 1
    new_id = base_id
    while School.query.filter_by(id=new_id).first():
        counter_str = str(counter).zfill(2)
        new_id = (base_id[:-2] + counter_str)
        counter += 1
    
    return new_id

def get_or_create_school(name, district=None):
    """Get or create school by name with improved district handling"""
    try:
        if pd.isna(name) or not name:
            return None
            
        # Clean and standardize the school name
        name = str(name).strip()
        if not name:
            return None
            
        # Try to find existing school
        school = School.query.filter(
            func.lower(School.name) == func.lower(name)
        ).first()
        
        if not school:
            try:
                school = School(
                    id=generate_school_id(name),
                    name=name,
                    district_id=district.id if district else None,
                    normalized_name=name.lower(),
                    salesforce_district_id=district.salesforce_id if district and district.salesforce_id else None
                )
                db.session.add(school)
                db.session.flush()
            except Exception as e:
                current_app.logger.error(f"Error creating school {name}: {str(e)}")
                return None
        
        return school
        
    except Exception as e:
        current_app.logger.error(f"Error in get_or_create_school for {name}: {str(e)}")
        return None

def extract_session_id(session_link):
    """Safely extract session ID from link with type checking"""
    try:
        if pd.isna(session_link) or session_link is None:
            return None
            
        # Convert float to string if needed
        if isinstance(session_link, (int, float)):
            return str(int(session_link))
            
        # If it's a URL, extract the last part
        link_str = str(session_link).strip()
        if '/' in link_str:
            return link_str.split('/')[-1]
        return link_str
    except Exception as e:
        current_app.logger.warning(f"Error extracting session ID: {e} from {session_link}")
        return None



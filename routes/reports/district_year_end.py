from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required
from datetime import datetime
import pytz
import io
import pandas as pd
import xlsxwriter

from models.event import Event, EventAttendance, EventStatus, EventType, EventStudentParticipation
from models.district_model import District
from models.school_model import School
from models.reports import DistrictYearEndReport
from models.volunteer import EventParticipation
from models import db
from models.organization import Organization, VolunteerOrganization
from models.student import Student

from routes.reports.common import (
    DISTRICT_MAPPING, 
    get_current_school_year, 
    get_school_year_date_range,
    generate_district_stats,
    cache_district_stats,
    get_district_student_count_for_event
)

# Create blueprint
district_year_end_bp = Blueprint('district_year_end', __name__)

def load_routes(bp):
    @bp.route('/reports/district/year-end')
    @login_required
    def district_year_end():
        # Get school year from query params or default to current
        school_year = request.args.get('school_year', get_current_school_year())
        host_filter = request.args.get('host_filter', 'all')  # 'all' or 'prepkc'
        
        # Get cached reports for the school year and host_filter
        cached_reports = DistrictYearEndReport.query.filter_by(school_year=school_year, host_filter=host_filter).all()
        
        district_stats = {report.district.name: report.report_data for report in cached_reports}
        
        if not district_stats:
            district_stats = generate_district_stats(school_year, host_filter=host_filter)
            cache_district_stats_with_events(school_year, district_stats, host_filter=host_filter)
        
        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first
        
        # Convert UTC time to Central time for display
        last_updated = None
        if cached_reports:
            utc_time = min(report.last_updated for report in cached_reports)
            central = pytz.timezone('America/Chicago')
            last_updated = utc_time.replace(tzinfo=pytz.UTC).astimezone(central)
        
        return render_template(
            'reports/district_year_end.html',
            districts=district_stats,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            last_updated=last_updated,
            host_filter=host_filter
        )

    @bp.route('/reports/district/year-end/refresh', methods=['POST'])
    @login_required
    def refresh_district_year_end():
        """Refresh the cached district year-end report data"""
        school_year = request.args.get('school_year', get_current_school_year())
        host_filter = request.args.get('host_filter', 'all')
        try:
            # Delete existing cached reports for this school year and host_filter
            deleted_count = DistrictYearEndReport.query.filter_by(school_year=school_year, host_filter=host_filter).delete()
            db.session.commit()
            
            # Generate new stats
            district_stats = generate_district_stats(school_year, host_filter=host_filter)
            
            # Cache the stats and events data
            cache_district_stats_with_events(school_year, district_stats, host_filter=host_filter)
            
            return jsonify({
                'success': True, 
                'message': f'Successfully refreshed data for {school_year[:2]}-{school_year[2:]} school year'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/reports/district/year-end/detail/<district_name>')
    @login_required
    def district_year_end_detail(district_name):
        """Show detailed year-end report for a specific district"""
        school_year = request.args.get('school_year', get_current_school_year())
        host_filter = request.args.get('host_filter', 'all')
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Get the district's mapping info
        district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                                if mapping['name'] == district_name), None)
        
        # Try to get cached data first (use host_filter)
        cached_report = DistrictYearEndReport.query.filter_by(
            district_id=district.id,
            school_year=school_year,
            host_filter=host_filter
        ).first()
        
        events_by_month = {}
        total_events = 0
        unique_volunteer_count = 0
        unique_student_count = 0 # Initialize unique student count
        stats = {}

        if cached_report:
            stats = cached_report.report_data or {} # Use cached stats
            # Check if we have cached events data
            if cached_report.events_data:
                events_by_month = cached_report.events_data.get('events_by_month', {})
                total_events = cached_report.events_data.get('total_events', 0)
                unique_volunteer_count = cached_report.events_data.get('unique_volunteer_count', 0)
                unique_student_count = cached_report.events_data.get('unique_student_count', 0) # Get from cache

                # Calculate unique_organization_count from cached events_by_month
                volunteer_ids = set()
                for month_data in events_by_month.values():
                    for event in month_data.get('events', []):
                        event_id = event['id']
                        participations = EventParticipation.query.filter_by(event_id=event_id).all()
                        for p in participations:
                            if p.status in ['Attended', 'Completed', 'Successfully Completed']:
                                volunteer_ids.add(p.volunteer_id)
                org_ids = (
                    db.session.query(VolunteerOrganization.organization_id)
                    .filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids))
                    .distinct()
                    .all()
                )
                unique_organization_count = len(org_ids)

                # Only use cached data if host_filter is 'all' or if we're confident the cache is correct
                # For now, always regenerate when host_filter != 'all' to ensure accuracy
                if stats and host_filter == 'all':
                    return render_template(
                        'reports/district_year_end_detail.html',
                        district=district,
                        school_year=school_year,
                        stats=stats,
                        events_by_month=events_by_month,
                        schools_by_level={'High': [], 'Middle': [], 'Elementary': [], None: []}, # Placeholder - needs calculation if not cached
                        total_events=total_events,
                        unique_volunteer_count=unique_volunteer_count,
                        unique_student_count=unique_student_count, # Pass to template
                        unique_organization_count=unique_organization_count,
                        host_filter=host_filter
                    )
        
        # If we reach here, either no cache or missing parts (stats or events_data)
        # We'll calculate stats after the events query

        # If we get here, we need to generate the events data (or it was missing from cache)
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ['connector_session']

        # Build query conditions (Duplicate logic - consider refactoring into a helper)
        query_conditions = [
            Event.districts.contains(district),
            Event.school.in_([school.id for school in district.schools]),
            *[Event.title.ilike(f"%{school.name}%") for school in district.schools],
            *[Event.district_partner.ilike(f"%{school.name}%") for school in district.schools],
            Event.district_partner.ilike(f"%{district.name}%"),
            Event.district_partner.ilike(f"%{district.name.replace(' School District', '')}%")
        ]

        if district_mapping and 'aliases' in district_mapping:
            for alias in district_mapping['aliases']:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Fetch events
        events_query = (Event.query
            .outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                ~Event.type.in_([EventType(t) for t in excluded_event_types]),
                db.or_(*query_conditions)
            )
            .order_by(Event.start_date)
        )
        if host_filter == 'prepkc':
            events_query = events_query.filter(Event.session_host == 'PREPKC')
        events = events_query.all()
        
        # Calculate stats from filtered events (always recalculate when filter is applied)
        if host_filter != 'all' or not stats:
            stats = {
                'total_events': len(events),
                'total_in_person_students': sum(
                    get_district_student_count_for_event(e, district.id) for e in events if e.type != EventType.VIRTUAL_SESSION
                ),
                'total_virtual_students': sum(
                    get_district_student_count_for_event(e, district.id) for e in events if e.type == EventType.VIRTUAL_SESSION
                ),
                'total_volunteers': sum(
                    len([p for p in e.volunteer_participations if p.status in ['Attended', 'Completed', 'Successfully Completed']]) for e in events
                ),
                'total_volunteer_hours': sum(
                    sum(p.delivery_hours or 0 for p in e.volunteer_participations if p.status in ['Attended', 'Completed', 'Successfully Completed']) for e in events
                ),
                'event_types': {},
            }
            for e in events:
                t = e.type.value if e.type else 'Unknown'
                stats['event_types'][t] = stats['event_types'].get(t, 0) + 1
        
        event_ids = [event.id for event in events]
        total_events = len(events)

        # Fetch student participations
        student_participations = EventStudentParticipation.query.filter(
            EventStudentParticipation.event_id.in_(event_ids)
        ).all()

        # Set to track unique volunteer and student IDs
        unique_volunteers = set()
        unique_students = set() # Track unique student IDs
        
        # Organize events by month (Duplicate logic - consider refactoring)
        events_by_month = {}
        for event in events:
            month = event.start_date.strftime('%B %Y')
            if month not in events_by_month:
                events_by_month[month] = {
                    'events': [],
                    'total_students': 0,
                    'total_volunteers': 0,
                    'total_volunteer_hours': 0,
                    'unique_volunteers': set(),
                    'volunteer_engagement_count': 0,
                    'unique_students': set() # Add monthly set
                }
            
            # Get attendance and volunteer data
            student_count = get_district_student_count_for_event(event, district.id)
            
            volunteer_participations = [p for p in event.volunteer_participations 
                                      if p.status in ['Attended', 'Completed', 'Successfully Completed']]
            volunteer_count = len(volunteer_participations)
            volunteer_hours = sum(p.delivery_hours or 0 for p in volunteer_participations)
            
            # Update event data and totals in events_by_month
            event_date = datetime.fromisoformat(event.start_date.isoformat())
            events_by_month[month]['events'].append({
                'id': event.id,
                'title': event.title,
                'date': event_date.strftime('%m/%d/%Y'),
                'time': event_date.strftime('%I:%M %p'),
                'type': event.type.value if event.type else None,
                'location': event.location or '',
                'student_count': student_count,
                'volunteer_count': volunteer_count,
                'volunteer_hours': volunteer_hours,
                'students': student_count,
                'volunteers': volunteer_count
            })
            events_by_month[month]['total_students'] += student_count
            events_by_month[month]['total_volunteers'] += volunteer_count
            events_by_month[month]['total_volunteer_hours'] += volunteer_hours
            events_by_month[month]['volunteer_engagement_count'] += volunteer_count
            
            # Track unique volunteers (overall and monthly)
            for p in volunteer_participations:
                unique_volunteers.add(p.volunteer_id)
                events_by_month[month]['unique_volunteers'].add(p.volunteer_id)

            # Track unique students (overall and monthly) - filter by district
            if event.type == EventType.VIRTUAL_SESSION:
                # For virtual events, we can't track individual unique students
                # since the count is calculated from teachers
                pass
            else:
                # Get student IDs for this specific district and event
                district_student_ids = (
                    db.session.query(EventStudentParticipation.student_id)
                    .join(Student, EventStudentParticipation.student_id == Student.id)
                    .join(School, Student.school_id == School.id)
                    .filter(
                        EventStudentParticipation.event_id == event.id,
                        EventStudentParticipation.status == 'Attended',
                        School.district_id == district.id
                    )
                    .all()
                )
                event_student_ids = {student_id[0] for student_id in district_student_ids}
                unique_students.update(event_student_ids)
                events_by_month[month]['unique_students'].update(event_student_ids)

        # Calculate overall unique counts
        unique_volunteer_count = len(unique_volunteers)
        unique_student_count = len(unique_students) # Calculate overall unique students

        # Process the events data for storage/display
        for month, data in events_by_month.items():
            data['unique_volunteer_count'] = len(data['unique_volunteers'])
            data['unique_volunteers'] = list(data['unique_volunteers'])  # Convert set to list for JSON storage
            data['volunteer_engagements'] = data['volunteer_engagement_count']
            data['unique_student_count'] = len(data['unique_students']) # Calculate monthly unique students
            data['unique_students'] = list(data['unique_students']) # Convert set to list for JSON

        # Cache the newly generated events data if we have a report object
        if cached_report:
            cached_report.events_data = {
                'events_by_month': events_by_month,
                'total_events': total_events,
                'unique_volunteer_count': unique_volunteer_count,
                'unique_student_count': unique_student_count # Cache the student count
            }
            db.session.commit()
        # If there was no cached_report object initially (e.g., first view after refresh),
        # we might consider creating one here, similar to cache_district_stats_with_events.
        # For now, we only update if it already existed.

        # Calculate unique organization count
        volunteer_ids = set()
        for event in events:
            for p in event.volunteer_participations:
                if p.status in ['Attended', 'Completed', 'Successfully Completed']:
                    volunteer_ids.add(p.volunteer_id)

        # Get all unique organization IDs for these volunteers
        org_ids = (
            db.session.query(VolunteerOrganization.organization_id)
            .filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids))
            .distinct()
            .all()
        )
        unique_organization_count = len(org_ids)

        return render_template(
            'reports/district_year_end_detail.html',
            district=district,
            school_year=school_year,
            stats=stats,
            events_by_month=events_by_month,
            schools_by_level={'High': [], 'Middle': [], 'Elementary': [], None: []}, # Placeholder
            total_events=total_events,
            unique_volunteer_count=unique_volunteer_count,
            unique_student_count=unique_student_count, # Pass to template
            unique_organization_count=unique_organization_count,
            host_filter=host_filter
        )

    @bp.route('/reports/district/year-end/<district_name>/excel')
    @login_required
    def district_year_end_excel(district_name):
        """Generate Excel file for district year-end report"""
        school_year = request.args.get('school_year', get_current_school_year())
        host_filter = request.args.get('host_filter', 'all')
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Get cached report data
        cached_report = DistrictYearEndReport.query.filter_by(
            district_id=district.id,
            school_year=school_year,
            host_filter=host_filter
        ).first()
        
        if not cached_report:
            # Generate new stats if not cached
            district_stats = generate_district_stats(school_year, host_filter=host_filter)
            stats = district_stats.get(district_name, {})
            events_data = None
        else:
            stats = cached_report.report_data or {}
            events_data = cached_report.events_data
        
        # Create Excel file
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#467599',
            'font_color': 'white',
            'border': 1
        })
        
        # Summary Sheet
        summary_data = {
            'Metric': [
                'Total Events',
                'Total Students Reached',
                'Unique Students',
                'Total Volunteers',
                'Unique Volunteers',
                'Total Volunteer Hours',
                'Schools Reached',
                'Career Clusters'
            ],
            'Value': [
                stats.get('total_events', 0),
                stats.get('total_students', 0),
                stats.get('unique_student_count', 0),
                stats.get('total_volunteers', 0),
                stats.get('unique_volunteer_count', 0),
                stats.get('total_volunteer_hours', 0),
                stats.get('schools_reached', 0),
                stats.get('career_clusters', 0)
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        worksheet = writer.sheets['Summary']
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
        worksheet.conditional_format('A1:B9', {'type': 'no_blanks', 'format': header_format})
        
        # Event Types Sheet
        if stats.get('event_types'):
            event_types_data = {
                'Event Type': list(stats['event_types'].keys()),
                'Count': list(stats['event_types'].values())
            }
            event_types_df = pd.DataFrame(event_types_data)
            event_types_df.to_excel(writer, sheet_name='Event Types', index=False)
            
            # Format event types sheet
            worksheet = writer.sheets['Event Types']
            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:B', 15)
            worksheet.conditional_format('A1:B1', {'type': 'no_blanks', 'format': header_format})
        
        # Monthly Breakdown Sheet
        if stats.get('monthly_breakdown'):
            monthly_data = []
            for month, data in stats['monthly_breakdown'].items():
                monthly_data.append({
                    'Month': month,
                    'Events': data.get('events', 0),
                    'Students': data.get('students', 0),
                    'Unique Students': data.get('unique_student_count', 0),
                    'Volunteers': data.get('volunteers', 0),
                    'Unique Volunteers': data.get('unique_volunteer_count', 0),
                    'Volunteer Hours': data.get('volunteer_hours', 0)
                })
            
            monthly_df = pd.DataFrame(monthly_data)
            monthly_df.to_excel(writer, sheet_name='Monthly Breakdown', index=False)
            
            # Format monthly breakdown sheet
            worksheet = writer.sheets['Monthly Breakdown']
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:G', 15)
            worksheet.conditional_format('A1:G1', {'type': 'no_blanks', 'format': header_format})
        
        # Events Detail Sheet
        if events_data and events_data.get('events_by_month'):
            events_detail = []
            for month, data in events_data['events_by_month'].items():
                for event in data['events']:
                    events_detail.append({
                        'Month': month,
                        'Date': event['date'],
                        'Time': event['time'],
                        'Event Title': event['title'],
                        'Type': event['type'],
                        'Location': event['location'],
                        'Students': event['student_count'],
                        'Volunteers': event['volunteer_count'],
                        'Volunteer Hours': event['volunteer_hours']
                    })
            
            events_df = pd.DataFrame(events_detail)
            events_df.to_excel(writer, sheet_name='Events Detail', index=False)
            
            # Format events detail sheet
            worksheet = writer.sheets['Events Detail']
            worksheet.set_column('A:A', 20)  # Month
            worksheet.set_column('B:B', 12)  # Date
            worksheet.set_column('C:C', 12)  # Time
            worksheet.set_column('D:D', 40)  # Event Title
            worksheet.set_column('E:E', 20)  # Type
            worksheet.set_column('F:F', 30)  # Location
            worksheet.set_column('G:I', 15)  # Numbers
            worksheet.conditional_format('A1:I1', {'type': 'no_blanks', 'format': header_format})
        
        writer.close()
        output.seek(0)
        
        # Create filename
        filename = f"{district_name.replace(' ', '_')}_{school_year}_Year_End_Report.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
        )

    @bp.route('/reports/district/year-end/detail/<district_name>/filtered-stats')
    @login_required
    def get_filtered_stats(district_name):
        """Get precise filtered stats for selected event types"""
        school_year = request.args.get('school_year', get_current_school_year())
        host_filter = request.args.get('host_filter', 'all')
        event_types = request.args.getlist('event_types[]')
        
        if not event_types:
            return jsonify({'error': 'No event types specified'}), 400
        
        # Get district
        district = District.query.filter_by(name=district_name).first()
        if not district:
            return jsonify({'error': 'District not found'}), 404
        
        # Get the district's mapping info
        district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                                if mapping['name'] == district_name), None)
        
        # Get events of specified types for this district
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ['connector_session']
        
        # Build query conditions (same logic as main detail view)
        query_conditions = [
            Event.districts.contains(district),
            Event.school.in_([school.id for school in district.schools]),
            *[Event.title.ilike(f"%{school.name}%") for school in district.schools],
            *[Event.district_partner.ilike(f"%{school.name}%") for school in district.schools],
            Event.district_partner.ilike(f"%{district.name}%"),
            Event.district_partner.ilike(f"%{district.name.replace(' School District', '')}%")
        ]
        
        if district_mapping and 'aliases' in district_mapping:
            for alias in district_mapping['aliases']:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )
        
        events_query = (Event.query
            .outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                Event.type.in_([EventType(t) for t in event_types]),
                db.or_(*query_conditions)
            )
            .order_by(Event.start_date)
        )
        
        # Apply host filter if specified
        if host_filter == 'prepkc':
            events_query = events_query.filter(Event.session_host == 'PREPKC')
        
        events = events_query.all()
        
        # Calculate precise unique counts
        unique_volunteers = set()
        unique_students = set()
        total_events = len(events)
        total_students = 0
        total_in_person_students = 0
        total_virtual_students = 0
        total_volunteers = 0
        total_volunteer_hours = 0
        
        for event in events:
            # Get volunteer participations
            volunteer_participations = [p for p in event.volunteer_participations 
                                      if p.status in ['Attended', 'Completed', 'Successfully Completed']]
            
            for p in volunteer_participations:
                unique_volunteers.add(p.volunteer_id)
            
            total_volunteers += len(volunteer_participations)
            total_volunteer_hours += sum(p.delivery_hours or 0 for p in volunteer_participations)
            
            # Get student count for this district
            student_count = get_district_student_count_for_event(event, district.id)
            total_students += student_count
            
            # Categorize students by event type
            if event.type == EventType.VIRTUAL_SESSION:
                total_virtual_students += student_count
            else:
                total_in_person_students += student_count
            
            # Get unique students for non-virtual events
            if event.type != EventType.VIRTUAL_SESSION:
                district_student_ids = (
                    db.session.query(EventStudentParticipation.student_id)
                    .join(Student, EventStudentParticipation.student_id == Student.id)
                    .join(School, Student.school_id == School.id)
                    .filter(
                        EventStudentParticipation.event_id == event.id,
                        EventStudentParticipation.status == 'Attended',
                        School.district_id == district.id
                    )
                    .all()
                )
                unique_students.update(student_id[0] for student_id in district_student_ids)
        
        # Get unique organizations
        if unique_volunteers:
            org_ids = (
                db.session.query(VolunteerOrganization.organization_id)
                .filter(VolunteerOrganization.volunteer_id.in_(unique_volunteers))
                .distinct()
                .all()
            )
            unique_organization_count = len(org_ids)
        else:
            unique_organization_count = 0
        
        return jsonify({
            'totalEvents': total_events,
            'totalStudents': total_students,
            'uniqueStudents': len(unique_students),
            'totalInPersonStudents': total_in_person_students,
            'totalVirtualStudents': total_virtual_students,
            'totalVolunteers': total_volunteers,
            'uniqueVolunteers': len(unique_volunteers),
            'totalVolunteerHours': total_volunteer_hours,
            'uniqueOrganizations': unique_organization_count
        })

    @bp.route('/reports/district/year-end/detail/<district_name>/filtered-participants')
    @login_required
    def get_filtered_participants(district_name):
        """Get filtered volunteers and students for selected event types"""
        school_year = request.args.get('school_year', get_current_school_year())
        event_types = request.args.getlist('event_types[]')
        
        if not event_types:
            return jsonify({'error': 'No event types specified'}), 400
        
        # Get district
        district = District.query.filter_by(name=district_name).first()
        if not district:
            return jsonify({'error': 'District not found'}), 404
        
        # Get the district's mapping info
        district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                                if mapping['name'] == district_name), None)
        
        # Get events of specified types for this district
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ['connector_session']
        
        # Build query conditions (same logic as main detail view)
        query_conditions = [
            Event.districts.contains(district),
            Event.school.in_([school.id for school in district.schools]),
            *[Event.title.ilike(f"%{school.name}%") for school in district.schools],
            *[Event.district_partner.ilike(f"%{school.name}%") for school in district.schools],
            Event.district_partner.ilike(f"%{district.name}%"),
            Event.district_partner.ilike(f"%{district.name.replace(' School District', '')}%")
        ]
        
        if district_mapping and 'aliases' in district_mapping:
            for alias in district_mapping['aliases']:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )
        
        events = (Event.query
            .outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                Event.type.in_([EventType(t) for t in event_types]),
                db.or_(*query_conditions)
            )
            .order_by(Event.start_date)
            .all())
        
        # Get filtered volunteer IDs
        filtered_volunteer_ids = set()
        for event in events:
            volunteer_participations = [p for p in event.volunteer_participations 
                                      if p.status in ['Attended', 'Completed', 'Successfully Completed']]
            for p in volunteer_participations:
                filtered_volunteer_ids.add(p.volunteer_id)
        
        # Get filtered student IDs (excluding virtual sessions)
        filtered_student_ids = set()
        non_virtual_events = [e for e in events if e.type != EventType.VIRTUAL_SESSION]
        
        for event in non_virtual_events:
            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == 'Attended',
                    School.district_id == district.id
                )
                .all()
            )
            filtered_student_ids.update(student_id[0] for student_id in district_student_ids)
        
        return jsonify({
            'volunteer_ids': list(filtered_volunteer_ids),
            'student_ids': list(filtered_student_ids),
            'event_ids': [event.id for event in events]
        })

def cache_district_stats_with_events(school_year, district_stats, host_filter='all'):
    """Cache district stats and events data for all districts"""
    for district_name, stats in district_stats.items():
        district = District.query.filter_by(name=district_name).first()
        if not district:
            continue

        # Get or create report
        report = DistrictYearEndReport.query.filter_by(
            district_id=district.id,
            school_year=school_year,
            host_filter=host_filter
        ).first()
        
        if not report:
            report = DistrictYearEndReport(
                district_id=district.id,
                school_year=school_year,
                host_filter=host_filter
            )
            db.session.add(report)
        
        report.report_data = stats
        
        # Generate events data (mostly for monthly breakdown)
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ['connector_session']

        # Build query conditions (same as generate_district_stats)
        query_conditions = [
            Event.districts.contains(district),
            Event.school.in_([school.id for school in district.schools]),
            *[Event.title.ilike(f"%{school.name}%") for school in district.schools],
            *[Event.district_partner.ilike(f"%{school.name}%") for school in district.schools],
            Event.district_partner.ilike(f"%{district.name}%"),
            Event.district_partner.ilike(f"%{district.name.replace(' School District', '')}%")
        ]
        district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items()
                               if mapping['name'] == district_name), None)
        if district_mapping and 'aliases' in district_mapping:
            for alias in district_mapping['aliases']:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(Event.districts.any(District.name.ilike(f"%{alias}%")))

        # Fetch events
        events_query = (Event.query
            .outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                ~Event.type.in_([EventType(t) for t in excluded_event_types]),
                db.or_(*query_conditions)
            )
            .order_by(Event.start_date)
        )
        
        # Apply host filter if specified
        if host_filter == 'prepkc':
            events_query = events_query.filter(Event.session_host == 'PREPKC')
        
        events = events_query.all()
        
        event_ids = [event.id for event in events]
        
        # Fetch student participations for these events
        student_participations = EventStudentParticipation.query.filter(
            EventStudentParticipation.event_id.in_(event_ids)
        ).all()
        
        # Set to track unique volunteer and student IDs for the whole district
        unique_volunteers = set()
        unique_students = set() # Track unique student IDs
        
        # Organize events by month
        events_by_month = {}
        for event in events:
            month = event.start_date.strftime('%B %Y')
            if month not in events_by_month:
                events_by_month[month] = {
                    'events': [],
                    'total_students': 0,
                    'total_volunteers': 0,
                    'total_volunteer_hours': 0,
                    'unique_volunteers': set(),
                    'volunteer_engagement_count': 0,
                    'unique_students': set() # Add set for monthly unique students
                }
            
            # Use participant_count for virtual sessions, otherwise use attendance logic
            student_count = get_district_student_count_for_event(event, district.id)
            
            volunteer_participations = [p for p in event.volunteer_participations 
                                      if p.status in ['Attended', 'Completed', 'Successfully Completed']]
            volunteer_count = len(volunteer_participations)
            volunteer_hours = sum(p.delivery_hours or 0 for p in volunteer_participations)
            
            event_date = datetime.fromisoformat(event.start_date.isoformat())
            events_by_month[month]['events'].append({
                'id': event.id,
                'title': event.title,
                'date': event_date.strftime('%m/%d/%Y'),
                'time': event_date.strftime('%I:%M %p'),
                'type': event.type.value if event.type else None,
                'location': event.location or '',
                'student_count': student_count,
                'volunteer_count': volunteer_count,
                'volunteer_hours': volunteer_hours,
                'students': student_count,
                'volunteers': volunteer_count
            })
            events_by_month[month]['total_students'] += student_count
            events_by_month[month]['total_volunteers'] += volunteer_count
            events_by_month[month]['total_volunteer_hours'] += volunteer_hours
            events_by_month[month]['volunteer_engagement_count'] += volunteer_count
            
            # Track unique volunteers (overall and monthly)
            for p in volunteer_participations:
                unique_volunteers.add(p.volunteer_id)
                events_by_month[month]['unique_volunteers'].add(p.volunteer_id)
            
            # Track unique students (overall and monthly) - filter by district
            if event.type == EventType.VIRTUAL_SESSION:
                # For virtual events, we can't track individual unique students
                # since the count is calculated from teachers
                pass
            else:
                # Get student IDs for this specific district and event
                district_student_ids = (
                    db.session.query(EventStudentParticipation.student_id)
                    .join(Student, EventStudentParticipation.student_id == Student.id)
                    .join(School, Student.school_id == School.id)
                    .filter(
                        EventStudentParticipation.event_id == event.id,
                        EventStudentParticipation.status == 'Attended',
                        School.district_id == district.id
                    )
                    .all()
                )
                event_student_ids = {student_id[0] for student_id in district_student_ids}
                unique_students.update(event_student_ids)
                events_by_month[month]['unique_students'].update(event_student_ids)

        # Process the events data for storage
        for month, data in events_by_month.items():
            data['unique_volunteer_count'] = len(data['unique_volunteers'])
            data['unique_volunteers'] = list(data['unique_volunteers']) # Convert set to list for JSON
            data['volunteer_engagements'] = data['volunteer_engagement_count']
            data['unique_student_count'] = len(data['unique_students']) # Calculate monthly unique student count
            data['unique_students'] = list(data['unique_students']) # Convert set to list for JSON

        # Cache the events data
        report.events_data = {
            'events_by_month': events_by_month,
            'total_events': len(events),
            'unique_volunteer_count': len(unique_volunteers),
            'unique_student_count': len(unique_students) # Store overall unique student count
        }

    db.session.commit()

#!/usr/bin/env python3
"""
Debug script to check classroom count exclusion logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.event import Event, EventTeacher, EventParticipation
from models.volunteer import Volunteer
from models.organization import Organization

def debug_classroom_count():
    """Debug the classroom count exclusion logic"""
    with app.app_context():
        # Find all "Designing Tomorrow" events
        events = Event.query.filter(
            Event.title.like('%Designing Tomorrow%')
        ).all()
        
        print(f"Found {len(events)} events with 'Designing Tomorrow' in title:")
        
        for event in events:
            print(f"\n{'='*60}")
            print(f"Event: {event.title} (ID: {event.id})")
            print(f"Date: {event.start_date}")
            
            # Check volunteers who participated
            participations = db.session.query(
                EventParticipation, Volunteer
            ).join(
                Volunteer, EventParticipation.volunteer_id == Volunteer.id
            ).filter(
                EventParticipation.event_id == event.id
            ).all()
            
            print(f"\nVolunteers who participated:")
            for participation, volunteer in participations:
                print(f"  - {volunteer.first_name} {volunteer.last_name} (ID: {volunteer.id})")
                print(f"    Status: {participation.status}")
                print(f"    Exclude from reports: {volunteer.exclude_from_reports}")
            
            # Check if any excluded volunteer participated
            excluded_volunteer_participated = db.session.query(
                EventParticipation
            ).join(
                Volunteer, EventParticipation.volunteer_id == Volunteer.id
            ).filter(
                EventParticipation.event_id == event.id,
                Volunteer.exclude_from_reports == True
            ).first()
            
            print(f"\nExcluded volunteer participated: {excluded_volunteer_participated is not None}")
            
            # Check teachers
            teachers = db.session.query(
                EventTeacher
            ).filter(
                EventTeacher.event_id == event.id
            ).all()
            
            print(f"\nTeachers:")
            for teacher in teachers:
                print(f"  - Teacher ID: {teacher.teacher_id}, Status: {teacher.status}")
            
            # Check classroom count with current logic
            classroom_count = db.session.query(
                db.func.count(db.distinct(EventTeacher.teacher_id))
            ).filter(
                EventTeacher.event_id == event.id,
                EventTeacher.status.in_(['simulcast', 'successfully completed'])
            ).scalar()
            
            print(f"\nClassroom count (current logic): {classroom_count}")
            
            # Check classroom count with exclusion logic
            if excluded_volunteer_participated:
                print("Classroom count (with exclusion): 0")
            else:
                print(f"Classroom count (with exclusion): {classroom_count}")
        
        # Also check Stephanie specifically
        print(f"\n{'='*60}")
        print("Checking Stephanie Anastasopoulos specifically:")
        stephanie = Volunteer.query.filter(
            Volunteer.first_name.ilike('%Stephanie%'),
            Volunteer.last_name.ilike('%Anastasopoulos%')
        ).first()
        
        if stephanie:
            print(f"Found Stephanie: {stephanie.first_name} {stephanie.last_name} (ID: {stephanie.id})")
            print(f"Exclude from reports: {stephanie.exclude_from_reports}")
            
            # Check all her participations
            her_participations = db.session.query(
                EventParticipation, Event
            ).join(
                Event, EventParticipation.event_id == Event.id
            ).filter(
                EventParticipation.volunteer_id == stephanie.id
            ).all()
            
            print(f"\nStephanie's participations:")
            for participation, event in her_participations:
                print(f"  - Event: {event.title} (ID: {event.id})")
                print(f"    Date: {event.start_date}")
                print(f"    Status: {participation.status}")
        else:
            print("Stephanie not found")

if __name__ == "__main__":
    debug_classroom_count() 
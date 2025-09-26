#!/usr/bin/env python3
"""
Volunteers by Event Performance Optimization Script
==================================================

This script optimizes the volunteers by event report by:
1. Adding missing database indexes
2. Creating optimized query functions
3. Testing performance improvements

Usage:
    python scripts/optimize_volunteers_by_event.py
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from time import perf_counter

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from app import app
from models import db
from models.event import Event, EventStatus, EventType
from models.volunteer import EventParticipation, Volunteer
from models.organization import Organization, VolunteerOrganization
from sqlalchemy import and_, or_, func, text


def add_performance_indexes():
    """Add missing database indexes for volunteers by event queries."""
    print("🔧 Adding performance indexes for volunteers by event...")
    
    try:
        with app.app_context():
            # Add indexes for future events queries
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_future_status 
                ON event(start_date, status)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_participation_future 
                ON event_participation(volunteer_id, event_id, status)
            """))
            
            # Add composite index for volunteer total count queries
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_volunteer_total_count 
                ON event_participation(volunteer_id, status)
            """))
            
            # Add index for last volunteer date queries
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_last_volunteer 
                ON event(start_date, id)
            """))
            
            db.session.commit()
            print("✅ Performance indexes added successfully")
            
    except Exception as e:
        print(f"❌ Error adding indexes: {e}")
        db.session.rollback()


def optimized_query_volunteers(start_date, end_date, selected_types, title_contains=None):
    """Optimized version of the volunteers by event query."""
    print("🚀 Running optimized volunteers by event query...")
    
    start_time = perf_counter()
    
    # Single query with proper joins and aggregation
    query = db.session.query(
        Volunteer.id,
        Volunteer.first_name,
        Volunteer.last_name,
        func.count(EventParticipation.id).label('event_count'),
        func.max(Event.start_date).label('last_event_date'),
        Organization.name.label('organization_name')
    ).join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)\
    .join(Event, Event.id == EventParticipation.event_id)\
    .outerjoin(VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id)\
    .outerjoin(Organization, VolunteerOrganization.organization_id == Organization.id)\
    .filter(
        Event.start_date >= start_date,
        Event.start_date <= end_date,
        Event.status == EventStatus.COMPLETED,
        Event.type.in_(selected_types),
        EventParticipation.status.in_([
            "Attended", "Completed", "Successfully Completed", "Simulcast"
        ]),
        Volunteer.exclude_from_reports == False
    )
    
    if title_contains:
        like = f"%{title_contains.strip()}%"
        query = query.filter(Event.title.ilike(like))
    
    query = query.group_by(
        Volunteer.id, 
        Volunteer.first_name, 
        Volunteer.last_name,
        Organization.name
    ).order_by(func.max(Event.start_date).desc())
    
    results = query.all()
    
    # Get volunteer IDs for additional queries
    volunteer_ids = [row.id for row in results]
    
    # Single query for total volunteer counts (all time)
    total_counts = {}
    if volunteer_ids:
        total_count_query = db.session.query(
            EventParticipation.volunteer_id,
            func.count(EventParticipation.id).label('total_count')
        ).join(Event, Event.id == EventParticipation.event_id)\
        .filter(
            EventParticipation.volunteer_id.in_(volunteer_ids),
            EventParticipation.status.in_([
                "Attended", "Completed", "Successfully Completed", "Simulcast"
            ]),
            Event.status == EventStatus.COMPLETED
        ).group_by(EventParticipation.volunteer_id)
        
        for row in total_count_query.all():
            total_counts[row.volunteer_id] = row.total_count
    
    # Single query for future events
    future_events = {}
    if volunteer_ids:
        future_query = db.session.query(
            EventParticipation.volunteer_id,
            Event.id,
            Event.title,
            Event.start_date,
            Event.type
        ).join(Event, Event.id == EventParticipation.event_id)\
        .filter(
            EventParticipation.volunteer_id.in_(volunteer_ids),
            Event.start_date > datetime.now(timezone.utc),
            Event.status.in_([
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.REQUESTED,
            ]),
            EventParticipation.status.notin_([
                "Cancelled", "No Show", "Declined", "Withdrawn"
            ])
        ).order_by(EventParticipation.volunteer_id, Event.start_date)
        
        for row in future_query.all():
            if row.volunteer_id not in future_events:
                future_events[row.volunteer_id] = []
            future_events[row.volunteer_id].append({
                'id': row.id,
                'title': row.title,
                'date': row.start_date,
                'type': row.type.value if row.type else None
            })
    
    # Convert to the expected format
    volunteers = []
    for row in results:
        volunteer_id = row.id
        future_events_list = future_events.get(volunteer_id, [])
        
        volunteers.append({
            'id': volunteer_id,
            'name': f"{row.first_name} {row.last_name}",
            'email': None,  # We'll get this separately if needed
            'organization': row.organization_name or 'Independent',
            'event_count': int(row.event_count or 0),
            'last_event_date': row.last_event_date,
            'total_volunteer_count': total_counts.get(volunteer_id, 0),
            'future_events': future_events_list,
            'future_events_count': len(future_events_list),
            'events': []  # We'll populate this if needed for detailed view
        })
    
    duration = (perf_counter() - start_time) * 1000
    print(f"✅ Optimized query completed in {duration:.1f}ms, returned {len(volunteers)} volunteers")
    
    return volunteers


def test_performance():
    """Test the performance improvements."""
    print("\n🧪 Testing performance improvements...")
    
    with app.app_context():
        # Test with last 365 days
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)
        
        print(f"Testing with date range: {start_date.date()} to {end_date.date()}")
        
        # Test optimized query
        selected_types = [EventType.CAREER_FAIR, EventType.DATA_VIZ]
        volunteers = optimized_query_volunteers(start_date, end_date, selected_types)
        
        print(f"\n📊 Results:")
        print(f"Volunteers found: {len(volunteers)}")
        
        # Show sample data
        if volunteers:
            sample = volunteers[0]
            print(f"Sample volunteer: {sample['name']} - {sample['event_count']} events, {sample['total_volunteer_count']} total")
            print(f"Future events: {sample['future_events_count']}")


def main():
    """Main optimization function."""
    print("🚀 Volunteers by Event Performance Optimization")
    print("=" * 60)
    
    with app.app_context():
        # Step 1: Add performance indexes
        add_performance_indexes()
        
        # Step 2: Test performance
        test_performance()
        
        print("\n✅ Optimization complete!")
        print("\nNext steps:")
        print("1. Update the volunteers_by_event.py route to use optimized queries")
        print("2. Test the report in the browser")
        print("3. Monitor performance improvements")


if __name__ == "__main__":
    main()

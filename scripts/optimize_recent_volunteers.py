#!/usr/bin/env python3
"""
Recent Volunteers Performance Optimization Script
===============================================

This script optimizes the recent volunteers report by:
1. Adding missing database indexes
2. Creating optimized query functions
3. Testing performance improvements

Usage:
    python scripts/optimize_recent_volunteers.py
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
from models.event import Event, EventStatus
from models.volunteer import EventParticipation, Volunteer
from models.organization import Organization, VolunteerOrganization
from sqlalchemy import and_, or_, func, text


def add_performance_indexes():
    """Add missing database indexes for recent volunteers queries."""
    print("🔧 Adding performance indexes...")
    
    try:
        with app.app_context():
            # Add indexes for EventParticipation table
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_participation_volunteer_id 
                ON event_participation(volunteer_id)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_participation_event_id 
                ON event_participation(event_id)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_participation_status 
                ON event_participation(status)
            """))
            
            # Add composite index for common query pattern
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_participation_volunteer_status 
                ON event_participation(volunteer_id, status)
            """))
            
            # Add indexes for Volunteer table (inherits from Contact)
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_volunteer_first_volunteer_date 
                ON volunteer(first_volunteer_date)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_contact_exclude_from_reports 
                ON contact(exclude_from_reports)
            """))
            
            # Add composite index for volunteer queries
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_contact_exclude_first_date 
                ON contact(exclude_from_reports, id)
            """))
            
            # Add index for event queries
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_event_start_date_status 
                ON event(start_date, status)
            """))
            
            db.session.commit()
            print("✅ Performance indexes added successfully")
            
    except Exception as e:
        print(f"❌ Error adding indexes: {e}")
        db.session.rollback()


def optimized_query_active_volunteers(start_date, end_date, title_contains=None):
    """Optimized version of the active volunteers query."""
    print("🚀 Running optimized active volunteers query...")
    
    start_time = perf_counter()
    
    # Use a single query with proper joins and aggregation
    query = db.session.query(
        Volunteer.id,
        Volunteer.first_name,
        Volunteer.last_name,
        func.count(EventParticipation.id).label('event_count'),
        func.sum(EventParticipation.delivery_hours).label('total_hours'),
        func.max(Event.start_date).label('last_event_date'),
        func.max(Event.type).label('last_event_type'),
        Organization.name.label('organization_name')
    ).join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)\
    .join(Event, Event.id == EventParticipation.event_id)\
    .outerjoin(VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id)\
    .outerjoin(Organization, VolunteerOrganization.organization_id == Organization.id)\
    .filter(
        Event.start_date >= start_date,
        Event.start_date <= end_date,
        Event.status == EventStatus.COMPLETED,
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
    
    # Convert to dict format
    volunteers = []
    for row in results:
        volunteers.append({
            'id': row.id,
            'name': f"{row.first_name} {row.last_name}",
            'email': None,  # We'll get this separately if needed
            'organization': row.organization_name or 'Independent',
            'event_count': int(row.event_count or 0),
            'total_hours': float(row.total_hours or 0.0),
            'last_event_date': row.last_event_date,
            'last_event_type': row.last_event_type.value if row.last_event_type else None,
            'events': []  # We'll populate this separately if needed
        })
    
    duration = (perf_counter() - start_time) * 1000
    print(f"✅ Optimized query completed in {duration:.1f}ms, returned {len(volunteers)} volunteers")
    
    return volunteers


def optimized_query_first_time_volunteers(start_date, end_date):
    """Optimized version of the first-time volunteers query."""
    print("🚀 Running optimized first-time volunteers query...")
    
    start_time = perf_counter()
    
    # Single query with proper joins and aggregation
    query = db.session.query(
        Volunteer.id,
        Volunteer.first_name,
        Volunteer.last_name,
        Volunteer.first_volunteer_date,
        func.count(EventParticipation.id).label('total_events'),
        func.sum(EventParticipation.delivery_hours).label('total_hours'),
        Organization.name.label('organization_name')
    ).outerjoin(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)\
    .outerjoin(Event, and_(
        EventParticipation.event_id == Event.id,
        Event.start_date >= start_date,
        Event.start_date <= end_date,
        Event.status == EventStatus.COMPLETED,
        EventParticipation.status.in_([
            "Attended", "Completed", "Successfully Completed"
        ])
    ))\
    .outerjoin(VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id)\
    .outerjoin(Organization, VolunteerOrganization.organization_id == Organization.id)\
    .filter(
        Volunteer.first_volunteer_date >= start_date,
        Volunteer.first_volunteer_date <= end_date,
        Volunteer.exclude_from_reports == False
    )\
    .group_by(
        Volunteer.id,
        Volunteer.first_name,
        Volunteer.last_name,
        Volunteer.first_volunteer_date,
        Organization.name
    )\
    .order_by(Volunteer.first_volunteer_date.desc())
    
    results = query.all()
    
    # Convert to dict format
    volunteers = []
    for row in results:
        volunteers.append({
            'id': row.id,
            'name': f"{row.first_name} {row.last_name}",
            'first_volunteer_date': row.first_volunteer_date,
            'total_events': int(row.total_events or 0),
            'total_hours': float(row.total_hours or 0.0),
            'organization': row.organization_name or 'Independent',
            'events': []  # We'll populate this separately if needed
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
        
        # Test optimized active volunteers query
        active_volunteers = optimized_query_active_volunteers(start_date, end_date)
        
        # Test optimized first-time volunteers query
        first_time_volunteers = optimized_query_first_time_volunteers(start_date, end_date)
        
        print(f"\n📊 Results:")
        print(f"Active volunteers: {len(active_volunteers)}")
        print(f"First-time volunteers: {len(first_time_volunteers)}")
        
        # Show sample data
        if active_volunteers:
            print(f"\nSample active volunteer: {active_volunteers[0]['name']} - {active_volunteers[0]['event_count']} events")
        
        if first_time_volunteers:
            print(f"Sample first-time volunteer: {first_time_volunteers[0]['name']} - {first_time_volunteers[0]['total_events']} events")


def main():
    """Main optimization function."""
    print("🚀 Recent Volunteers Performance Optimization")
    print("=" * 50)
    
    with app.app_context():
        # Step 1: Add performance indexes
        add_performance_indexes()
        
        # Step 2: Test performance
        test_performance()
        
        print("\n✅ Optimization complete!")
        print("\nNext steps:")
        print("1. Update the recent_volunteers.py route to use optimized queries")
        print("2. Test the report in the browser")
        print("3. Monitor performance improvements")


if __name__ == "__main__":
    main()

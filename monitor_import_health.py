#!/usr/bin/env python3
"""
Import Health Monitoring Script
==============================

This script monitors the health of the import system and checks for potential
data integrity issues that could cause volunteers to not appear in event lists.

Should be run after each nightly import to ensure data consistency.
"""

import sys

sys.path.append(".")

from datetime import datetime, timedelta

from app import app
from models import db
from models.event import Event, EventStatus
from models.volunteer import EventParticipation


def check_import_health():
    """Check for potential import health issues."""
    print("Checking import system health...")
    print("=" * 50)

    issues_found = []

    with app.app_context():
        # 1. Check for "Scheduled" status on completed events
        scheduled_on_completed = (
            db.session.query(EventParticipation)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                EventParticipation.status == "Scheduled",
                Event.status == EventStatus.COMPLETED,
            )
            .count()
        )

        if scheduled_on_completed > 0:
            issues_found.append(
                f"ISSUE: {scheduled_on_completed} volunteers have 'Scheduled' status on completed events"
            )
        else:
            print("✓ No 'Scheduled' volunteers on completed events")

        # 2. Check for participation records without delivery hours
        missing_hours = EventParticipation.query.filter(
            (EventParticipation.delivery_hours.is_(None))
            | (EventParticipation.delivery_hours == 0),
            EventParticipation.status.in_(["Attended", "Completed"]),
        ).count()

        if missing_hours > 0:
            issues_found.append(
                f"ISSUE: {missing_hours} attended volunteers missing delivery hours"
            )
        else:
            print("✓ All attended volunteers have delivery hours")

        # 3. Check for events with volunteers but no participation records
        events_with_volunteers = (
            db.session.query(Event.id).join(Event.volunteers).distinct().count()
        )

        events_with_participation = (
            db.session.query(Event.id)
            .join(EventParticipation, Event.id == EventParticipation.event_id)
            .distinct()
            .count()
        )

        events_missing_participation = (
            events_with_volunteers - events_with_participation
        )
        if events_missing_participation > 0:
            issues_found.append(
                f"ISSUE: {events_missing_participation} events have volunteers but no participation records"
            )
        else:
            print("✓ All events with volunteers have participation records")

        # 4. Check recent import activity
        recent_imports = EventParticipation.query.filter(
            EventParticipation.id > (EventParticipation.query.count() - 100)
        ).count()

        print(f"Recent participation records: {recent_imports}")

        # 5. Status distribution check
        status_counts = (
            db.session.query(
                EventParticipation.status, db.func.count(EventParticipation.id)
            )
            .group_by(EventParticipation.status)
            .all()
        )

        print("\nParticipation status distribution:")
        for status, count in status_counts:
            print(f"  {status}: {count}")

        # 6. Check for events completed in last 30 days with proper status updates
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_completed_events = Event.query.filter(
            Event.status == EventStatus.COMPLETED, Event.start_date >= thirty_days_ago
        ).count()

        recent_attended_participation = (
            db.session.query(EventParticipation)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date >= thirty_days_ago,
                EventParticipation.status == "Attended",
            )
            .count()
        )

        print(f"\nRecent activity (last 30 days):")
        print(f"  Completed events: {recent_completed_events}")
        print(f"  Attended participations: {recent_attended_participation}")

        # Summary
        print("\n" + "=" * 50)
        if issues_found:
            print("HEALTH CHECK FAILED - Issues found:")
            for issue in issues_found:
                print(f"  {issue}")
            return False
        else:
            print("HEALTH CHECK PASSED - No issues detected")
            return True


def main():
    """Main monitoring function."""
    success = check_import_health()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

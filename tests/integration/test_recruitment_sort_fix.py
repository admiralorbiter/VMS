"""
Test Suite for Recruitment Search Sorting Fix (TC-310)

Verifies that the "Times Volunteered" sort in Recruitment Search correctly
excludes non-attended events (No-Show, Cancelled, Scheduled).
"""

from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.event import Event, EventFormat, EventStatus, EventType
from models.volunteer import EventParticipation, Volunteer


def test_sorting_by_times_volunteered_excludes_noshows(client, auth_headers, app):
    """
    TC-310: Verify that sorting by 'Times Volunteered' only counts attended events.

    Setup:
    - V1: 1 Attended event
    - V2: 5 No-Show events (Should have count 0 for sorting)

    Expected:
    - When sorting DESC, V1 (count 1) should come before V2 (count 0).
    - If logic is broken, V2 (count 5) will come before V1.
    """
    with app.app_context():
        # Create volunteers
        v1 = Volunteer(
            first_name="Real", last_name="Volunteer", salesforce_individual_id="003_V1"
        )
        v2 = Volunteer(
            first_name="Flaky", last_name="Volunteer", salesforce_individual_id="003_V2"
        )
        db.session.add_all([v1, v2])
        db.session.commit()

        # Create event
        event = Event(
            title="Sort Test Event",
            type=EventType.IN_PERSON,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            status=EventStatus.CONFIRMED,
            salesforce_id="EVT_SORT_001",
        )
        db.session.add(event)
        db.session.commit()

        # V1: 1 Attended
        p1 = EventParticipation(
            event_id=event.id,
            volunteer_id=v1.id,
            status="Attended",
            salesforce_id="EP_V1_1",
        )

        # V2: 5 No-Shows
        participations_v2 = []
        for i in range(5):
            participations_v2.append(
                EventParticipation(
                    event_id=event.id,
                    volunteer_id=v2.id,
                    status="No-Show",
                    salesforce_id=f"EP_V2_{i}",
                )
            )

        db.session.add(p1)
        db.session.add_all(participations_v2)
        db.session.commit()

        # Store IDs for verification
        v1_id = v1.id
        v2_id = v2.id

    # Request sorted by times_volunteered DESC
    response = client.get(
        "/reports/recruitment/search?sort=times_volunteered&order=desc",
        headers=auth_headers,
    )

    assert response.status_code == 200
    content = response.data.decode()

    # Find positions of names in the response
    pos_v1 = content.find("Real Volunteer")
    pos_v2 = content.find("Flaky Volunteer")

    assert pos_v1 != -1
    assert pos_v2 != -1

    # Clean up first
    with app.app_context():
        EventParticipation.query.filter(
            EventParticipation.volunteer_id.in_([v1_id, v2_id])
        ).delete(synchronize_session=False)
        Volunteer.query.filter(Volunteer.id.in_([v1_id, v2_id])).delete(
            synchronize_session=False
        )
        Event.query.filter_by(salesforce_id="EVT_SORT_001").delete(
            synchronize_session=False
        )
        db.session.commit()

    # V1 (1 attended) should appear BEFORE V2 (0 attended, 5 no-show)
    # If bug exists, V2 (5 total) will appear before V1 (1 total)
    assert (
        pos_v1 < pos_v2
    ), "Volunteer with actual attendance should be ranked higher than volunteer with only no-shows"

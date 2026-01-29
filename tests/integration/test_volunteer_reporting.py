from datetime import datetime, timedelta

import pytest

from models import Event, Volunteer, db
from models.volunteer import EventParticipation, VolunteerStatus


class TestVolunteerReporting:
    """
    Integration tests for Volunteer Reporting Dashboard (TC-700 to TC-703).
    """

    @pytest.fixture
    def reporting_data(self, client):
        """Seed data for reporting tests based on Test Pack 6 specs."""
        from models.contact import ContactTypeEnum, Email

        # Create Volunteers (without email arg)
        v1 = Volunteer(
            first_name="Victor", last_name="V1", status=VolunteerStatus.ACTIVE
        )
        v2 = Volunteer(first_name="Ella", last_name="V2", status=VolunteerStatus.ACTIVE)
        v3 = Volunteer(first_name="Sam", last_name="V3", status=VolunteerStatus.ACTIVE)
        v6 = Volunteer(
            first_name="Casey", last_name="V6", status=VolunteerStatus.ACTIVE
        )
        v7 = Volunteer(
            first_name="Jordan", last_name="V7", status=VolunteerStatus.ACTIVE
        )

        db.session.add_all([v1, v2, v3, v6, v7])
        db.session.commit()

        # Create Emails
        emails = [
            Email(
                email="v1@example.com",
                contact_id=v1.id,
                type=ContactTypeEnum.personal,
                primary=True,
            ),
            Email(
                email="v2@example.com",
                contact_id=v2.id,
                type=ContactTypeEnum.personal,
                primary=True,
            ),
            Email(
                email="v3@example.com",
                contact_id=v3.id,
                type=ContactTypeEnum.personal,
                primary=True,
            ),
            Email(
                email="v6@example.com",
                contact_id=v6.id,
                type=ContactTypeEnum.personal,
                primary=True,
            ),
            Email(
                email="v7@example.com",
                contact_id=v7.id,
                type=ContactTypeEnum.personal,
                primary=True,
            ),
        ]
        db.session.add_all(emails)
        db.session.commit()

        # Create Events (Past events for reporting)
        evt = Event(title="Test Event", start_date=datetime.now() - timedelta(days=10))
        db.session.add(evt)
        db.session.commit()

        # Log Hours (Hours: Victor=10, Jordan=8, Casey=6, Ella=3, Sam=1)
        self._add_participation(v1, 10, evt)
        self._add_participation(v7, 8, evt)
        self._add_participation(v6, 6, evt)
        self._add_participation(v2, 3, evt)
        self._add_participation(v3, 1, evt)

        return {"v1": v1, "v2": v2, "v3": v3, "v6": v6, "v7": v7}

    def _add_participation(self, volunteer, hours, event):
        p = EventParticipation(
            volunteer_id=volunteer.id,
            event_id=event.id,
            status="Attended",
            delivery_hours=float(hours),
        )
        db.session.add(p)
        db.session.commit()

    def test_leaderboard_by_hours(self, client, reporting_data):
        """
        TC-700: Verify leaderboard ranks by total hours descending.
        Expected: Victor (10) > Jordan (8) > Casey (6) > Ella (3) > Sam (1)
        """
        from sqlalchemy import desc, func

        results = (
            db.session.query(
                Volunteer,
                func.sum(EventParticipation.delivery_hours).label("total_hours"),
            )
            .join(EventParticipation)
            .group_by(Volunteer.id)
            .order_by(desc("total_hours"))
            .all()
        )

        # Assert Ordering
        assert len(results) == 5
        assert results[0][0].first_name == "Victor" and results[0].total_hours == 10
        assert results[1][0].first_name == "Jordan" and results[1].total_hours == 8
        assert results[2][0].first_name == "Casey" and results[2].total_hours == 6
        assert results[3][0].first_name == "Ella" and results[3].total_hours == 3
        assert results[4][0].first_name == "Sam" and results[4].total_hours == 1

    def test_leaderboard_by_events(self, client):
        """
        TC-701: Verify leaderboard ranks by event count.
        """
        v1 = Volunteer(
            first_name="EventKing", last_name="One", status=VolunteerStatus.ACTIVE
        )
        v2 = Volunteer(
            first_name="EventPrince", last_name="Two", status=VolunteerStatus.ACTIVE
        )
        db.session.add_all([v1, v2])
        db.session.commit()

        # Create 4 events for V1
        for i in range(4):
            e = Event(title=f"E1-{i}", start_date=datetime.now())
            db.session.add(e)
            db.session.commit()
            p = EventParticipation(
                volunteer_id=v1.id, event_id=e.id, status="Attended", delivery_hours=1
            )
            db.session.add(p)

        # Create 2 events for V2
        for i in range(2):
            e = Event(title=f"E2-{i}", start_date=datetime.now())
            db.session.add(e)
            db.session.commit()
            p = EventParticipation(
                volunteer_id=v2.id, event_id=e.id, status="Attended", delivery_hours=1
            )
            db.session.add(p)

        db.session.commit()

        # Verify Query Logic (Event Count)
        from sqlalchemy import desc, func

        results = (
            db.session.query(
                Volunteer, func.count(EventParticipation.id).label("event_count")
            )
            .join(EventParticipation)
            .filter(EventParticipation.status == "Attended")
            .group_by(Volunteer.id)
            .order_by(desc("event_count"))
            .all()
        )

        assert results[0][0].first_name == "EventKing"
        assert results[0].event_count == 4
        assert results[1][0].first_name == "EventPrince"
        assert results[1].event_count == 2

    def test_time_range_filter(self, client):
        """
        TC-703: Verify rankings update based on date range.
        """
        v1 = Volunteer(
            first_name="TimeTraveler", last_name="X", status=VolunteerStatus.ACTIVE
        )
        db.session.add(v1)
        db.session.commit()

        # 5 hours LAST YEAR
        old_event = Event(
            title="Old Event", start_date=datetime.now() - timedelta(days=400)
        )
        db.session.add(old_event)
        db.session.commit()
        self._add_participation(v1, 5, old_event)

        # 5 hours THIS MONTH
        new_event = Event(
            title="New Event", start_date=datetime.now() - timedelta(days=10)
        )
        db.session.add(new_event)
        db.session.commit()
        self._add_participation(v1, 5, new_event)

        # Query for THIS YEAR only
        from sqlalchemy import func

        start_of_year = datetime.now() - timedelta(days=300)

        results = (
            db.session.query(func.sum(EventParticipation.delivery_hours))
            .join(Event)
            .filter(
                EventParticipation.volunteer_id == v1.id,
                Event.start_date >= start_of_year,
            )
            .scalar()
        )

        assert results == 5  # Should ignore the 5 hours from last year

    def _add_participation(self, volunteer, hours, event):
        p = EventParticipation(
            volunteer_id=volunteer.id,
            event_id=event.id,
            status="Attended",
            delivery_hours=float(hours),
        )
        db.session.add(p)
        db.session.commit()

import sys
from collections import defaultdict

from sqlalchemy import func

try:
    # Ensure app context and DB are available
    from app import app, db
    from models.event import EventStudentParticipation
except Exception as e:
    print(f"Error importing app/models: {e}")
    sys.exit(1)


def main() -> int:
    with app.app_context():
        # Find duplicate pairs by (event_id, student_id)
        rows = (
            db.session.query(
                EventStudentParticipation.event_id,
                EventStudentParticipation.student_id,
                func.count("*").label("cnt"),
            )
            .group_by(
                EventStudentParticipation.event_id,
                EventStudentParticipation.student_id,
            )
            .having(func.count("*") > 1)
            .all()
        )

        if not rows:
            print("No duplicate (event_id, student_id) pairs found.")
            return 0

        print(f"Found {len(rows)} duplicate (event_id, student_id) pairs:")
        # For each duplicate pair, list record ids and salesforce_ids
        for event_id, student_id, cnt in rows:
            print(f"- Event {event_id}, Student {student_id}: count={cnt}")
            records = (
                db.session.query(EventStudentParticipation)
                .filter(
                    EventStudentParticipation.event_id == event_id,
                    EventStudentParticipation.student_id == student_id,
                )
                .all()
            )
            for rec in records:
                print(
                    f"  id={rec.id} sf_id={rec.salesforce_id} status={rec.status} hours={rec.delivery_hours}"
                )

        return 0


if __name__ == "__main__":
    raise SystemExit(main())

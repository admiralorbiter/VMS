from datetime import datetime, timezone

from models import db
from models.teacher_progress import TeacherProgress
from routes.reports.virtual_session import compute_teacher_progress_tracking


def test_teacher_progress_deduplicates_name_variations(app):
    with app.app_context():
        teacher = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Banneker",
            name="Ada Rivas Moreno",
            email="ada.rivas.moreno@example.com",
            grade="3",
            target_sessions=2,
        )
        db.session.add(teacher)
        db.session.commit()

        tracking_data = compute_teacher_progress_tracking(
            "Kansas City Kansas Public Schools",
            "2025-2026",
            datetime(2025, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 7, 31, tzinfo=timezone.utc),
        )

        assert "Banneker" in tracking_data
        teachers = tracking_data["Banneker"]["teachers"]

        # Ensure the teacher only appears once even with multiple name variations
        assert len(teachers) == 1
        assert teachers[0]["name"] == "Ada Rivas Moreno"

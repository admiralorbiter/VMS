"""
Unit tests for services/virtual_computation_service.py

Tests cover pure functions that don't require DB access:
- is_teacher_attended
- district_name_matches
- apply_runtime_filters
- calculate_summaries_from_sessions
- apply_sorting_and_pagination
"""

import pytest

from services.virtual_computation_service import (
    COMPLETED_STATUSES,
    MAIN_DISTRICTS,
    apply_runtime_filters,
    apply_sorting_and_pagination,
    calculate_summaries_from_sessions,
    district_name_matches,
    is_teacher_attended,
)

# ── Helpers ───────────────────────────────────────────────────────────


class _FakeTeacherReg:
    """Minimal stand-in for an EventTeacher record."""

    def __init__(self, status=None, attendance_confirmed_at=None):
        self.status = status
        self.attendance_confirmed_at = attendance_confirmed_at


def _session(
    district="Kansas City Kansas Public Schools",
    status="completed",
    teacher_name="Jane Smith",
    school_name="Test School",
    session_title="Career Talk",
    presenter="John Doe",
    presenter_data=None,
    topic_theme="STEM",
    **overrides,
):
    """Build a session dict matching the shape virtual_computation_service expects."""
    data = {
        "district": district,
        "status": status,
        "teacher_name": teacher_name,
        "school_name": school_name,
        "session_title": session_title,
        "presenter": presenter,
        "presenter_data": presenter_data,
        "topic_theme": topic_theme,
        "date": "01/15/25",
        "time": "10:00 AM",
        "session_type": "virtual",
        "presenter_organization": "Acme Corp",
        "event_id": None,
    }
    data.update(overrides)
    return data


# ── is_teacher_attended ───────────────────────────────────────────────


class TestIsTeacherAttended:

    def test_attendance_confirmed_at_set(self):
        """Primary signal: attendance_confirmed_at is set."""
        tr = _FakeTeacherReg(attendance_confirmed_at="2025-01-15T10:00:00")
        assert is_teacher_attended(tr) is True

    def test_status_attended(self):
        """Fallback signal: status string says 'attended'."""
        assert is_teacher_attended(_FakeTeacherReg(status="attended")) is True

    def test_status_count(self):
        assert is_teacher_attended(_FakeTeacherReg(status="count")) is True

    def test_status_completed(self):
        assert is_teacher_attended(_FakeTeacherReg(status="completed")) is True

    def test_no_show_overrides_confirmed_at(self):
        """No-show always overrides even if attendance_confirmed_at is set."""
        tr = _FakeTeacherReg(
            status="no show", attendance_confirmed_at="2025-01-15T10:00:00"
        )
        assert is_teacher_attended(tr) is False

    def test_no_show_hyphenated(self):
        assert is_teacher_attended(_FakeTeacherReg(status="teacher no-show")) is False

    def test_no_show_underscore(self):
        assert is_teacher_attended(_FakeTeacherReg(status="no_show")) is False

    def test_did_not_attend(self):
        assert is_teacher_attended(_FakeTeacherReg(status="did not attend")) is False

    def test_cancelled_overrides_confirmed_at(self):
        tr = _FakeTeacherReg(
            status="cancelled", attendance_confirmed_at="2025-01-15T10:00:00"
        )
        assert is_teacher_attended(tr) is False

    def test_withdrawal(self):
        assert is_teacher_attended(_FakeTeacherReg(status="withdraw")) is False

    def test_no_signals_returns_false(self):
        """No attendance_confirmed_at + no matching status → False."""
        assert is_teacher_attended(_FakeTeacherReg(status="registered")) is False

    def test_none_status(self):
        assert is_teacher_attended(_FakeTeacherReg(status=None)) is False

    def test_empty_status(self):
        assert is_teacher_attended(_FakeTeacherReg(status="")) is False

    def test_uppercase_attended_still_matches(self):
        """Status comparison should be case-insensitive."""
        assert is_teacher_attended(_FakeTeacherReg(status="Attended")) is True

    def test_uppercase_completed_still_matches(self):
        assert is_teacher_attended(_FakeTeacherReg(status="COMPLETED")) is True

    def test_mixed_case_no_show(self):
        assert is_teacher_attended(_FakeTeacherReg(status="No Show")) is False


# ── district_name_matches ─────────────────────────────────────────────


class TestDistrictNameMatches:

    def test_exact_match(self):
        assert district_name_matches("Test District", "Test District") is True

    def test_case_insensitive_match(self):
        assert district_name_matches("test district", "Test District") is True

    def test_no_match(self):
        assert district_name_matches("District A", "District B") is False

    def test_none_target(self):
        assert district_name_matches(None, "Test") is False

    def test_none_compare(self):
        assert district_name_matches("Test", None) is False

    def test_empty_strings(self):
        assert district_name_matches("", "") is False

    def test_whitespace_handling(self):
        assert district_name_matches("  Test  ", "Test") is True


# ── apply_runtime_filters ────────────────────────────────────────────


class TestApplyRuntimeFilters:

    def test_no_filters_returns_all(self):
        sessions = [_session(), _session()]
        result = apply_runtime_filters(sessions, {})
        assert len(result) == 2

    def test_career_cluster_filter(self):
        sessions = [
            _session(topic_theme="STEM"),
            _session(topic_theme="Healthcare"),
            _session(topic_theme="stem and engineering"),
        ]
        result = apply_runtime_filters(sessions, {"career_cluster": "STEM"})
        assert len(result) == 2  # "STEM" and "stem and engineering"

    def test_school_filter(self):
        sessions = [
            _session(school_name="Lincoln Elementary"),
            _session(school_name="Washington Middle"),
        ]
        result = apply_runtime_filters(sessions, {"school": "Lincoln"})
        assert len(result) == 1
        assert result[0]["school_name"] == "Lincoln Elementary"

    def test_district_filter(self):
        sessions = [
            _session(district="District A"),
            _session(district="District B"),
        ]
        result = apply_runtime_filters(sessions, {"district": "District A"})
        assert len(result) == 1

    def test_status_filter_with_mapping(self):
        sessions = [
            _session(status="completed"),
            _session(status="successfully completed"),
            _session(status="draft"),
        ]
        result = apply_runtime_filters(sessions, {"status": "completed"})
        assert len(result) == 2

    def test_search_filter_matches_teacher(self):
        sessions = [
            _session(teacher_name="Jane Smith"),
            _session(teacher_name="Bob Jones"),
        ]
        result = apply_runtime_filters(sessions, {"search": "jane"})
        assert len(result) == 1

    def test_search_filter_matches_title(self):
        sessions = [
            _session(session_title="Career Day"),
            _session(session_title="Mock Interview"),
        ]
        result = apply_runtime_filters(sessions, {"search": "career"})
        assert len(result) == 1

    def test_search_filter_matches_presenter(self):
        sessions = [
            _session(presenter="Dr. Smith", teacher_name="Alice Brown"),
            _session(presenter="Prof. Brown", teacher_name="Bob Clark"),
        ]
        result = apply_runtime_filters(sessions, {"search": "smith"})
        assert len(result) == 1

    def test_combined_filters(self):
        sessions = [
            _session(topic_theme="STEM", school_name="Lincoln"),
            _session(topic_theme="STEM", school_name="Washington"),
            _session(topic_theme="Arts", school_name="Lincoln"),
        ]
        result = apply_runtime_filters(
            sessions, {"career_cluster": "STEM", "school": "Lincoln"}
        )
        assert len(result) == 1

    def test_empty_session_list(self):
        result = apply_runtime_filters([], {"career_cluster": "STEM"})
        assert result == []

    def test_none_topic_theme_excluded_by_cluster_filter(self):
        """Session with topic_theme=None should be excluded by career_cluster filter."""
        sessions = [_session(topic_theme=None)]
        result = apply_runtime_filters(sessions, {"career_cluster": "STEM"})
        assert len(result) == 0

    def test_none_school_name_excluded_by_school_filter(self):
        """Session with school_name=None should be excluded by school filter."""
        sessions = [_session(school_name=None)]
        result = apply_runtime_filters(sessions, {"school": "Lincoln"})
        assert len(result) == 0

    def test_none_teacher_name_excluded_by_search(self):
        """Session with teacher_name=None should not crash during search."""
        sessions = [_session(teacher_name=None, presenter=None, session_title=None)]
        result = apply_runtime_filters(sessions, {"search": "anything"})
        assert len(result) == 0


# ── calculate_summaries_from_sessions ─────────────────────────────────


class TestCalculateSummariesFromSessions:

    def test_empty_data(self):
        districts, overall = calculate_summaries_from_sessions([])
        assert districts == {}
        assert overall["teacher_count"] == 0
        assert overall["experience_count"] == 0

    def test_single_completed_session(self):
        sessions = [
            _session(
                district="Kansas City Kansas Public Schools",
                status="completed",
                teacher_name="Jane Smith",
                school_name="Test School",
                presenter="John Doe",
                presenter_data=[
                    {"name": "John Doe", "id": 1, "organization_name": "Acme"}
                ],
            )
        ]
        districts, overall = calculate_summaries_from_sessions(sessions)
        assert "Kansas City Kansas Public Schools" in districts
        assert overall["teacher_count"] == 1
        assert overall["experience_count"] == 1
        assert overall["professional_count"] == 1

    def test_non_completed_sessions_excluded_from_counts(self):
        sessions = [
            _session(status="draft"),
            _session(status="cancelled"),
            _session(status="requested"),
        ]
        _, overall = calculate_summaries_from_sessions(sessions)
        assert overall["experience_count"] == 0

    def test_simulcast_counted_as_completed(self):
        sessions = [_session(status="simulcast", presenter_data=None)]
        _, overall = calculate_summaries_from_sessions(sessions)
        assert overall["experience_count"] == 1

    def test_unique_teachers_deduplicated(self):
        sessions = [
            _session(teacher_name="Jane Smith", session_title="Session 1"),
            _session(teacher_name="Jane Smith", session_title="Session 2"),
            _session(teacher_name="Bob Jones", session_title="Session 3"),
        ]
        _, overall = calculate_summaries_from_sessions(sessions)
        assert overall["teacher_count"] == 2

    def test_non_main_districts_excluded_by_default(self):
        sessions = [
            _session(district="Kansas City Kansas Public Schools"),
            _session(district="Some Other District"),
        ]
        districts, _ = calculate_summaries_from_sessions(
            sessions, show_all_districts=False
        )
        assert "Kansas City Kansas Public Schools" in districts
        assert "Some Other District" not in districts

    def test_show_all_districts(self):
        sessions = [
            _session(district="Kansas City Kansas Public Schools"),
            _session(district="Some Other District"),
        ]
        districts, _ = calculate_summaries_from_sessions(
            sessions, show_all_districts=True
        )
        assert "Some Other District" in districts

    def test_student_count_is_teacher_count_times_25(self):
        sessions = [
            _session(teacher_name="Jane Smith"),
            _session(teacher_name="Bob Jones"),
        ]
        _, overall = calculate_summaries_from_sessions(sessions)
        assert overall["student_count"] == overall["teacher_count"] * 25

    def test_local_professional_tracking(self):
        sessions = [
            _session(
                presenter_data=[
                    {"name": "Local Pro", "id": 1, "is_local": True},
                ],
                event_id=100,
            )
        ]
        _, overall = calculate_summaries_from_sessions(sessions)
        assert overall["local_professional_count"] == 1
        assert overall["local_session_count"] == 1

    def test_none_teacher_name_handled(self):
        """Session with teacher_name=None should not crash summaries."""
        sessions = [_session(teacher_name=None, school_name=None)]
        districts, overall = calculate_summaries_from_sessions(
            sessions, show_all_districts=True
        )
        assert overall["teacher_count"] == 0
        assert overall["experience_count"] == 1

    def test_none_district_excluded(self):
        """Session with district=None should not crash."""
        sessions = [_session(district=None)]
        districts, overall = calculate_summaries_from_sessions(
            sessions, show_all_districts=True
        )
        assert overall["experience_count"] == 0  # skipped because no district

    def test_poc_professional_tracking(self):
        sessions = [
            _session(
                presenter_data=[
                    {
                        "name": "POC Pro",
                        "id": 2,
                        "is_people_of_color": True,
                    },
                ],
                event_id=200,
            )
        ]
        _, overall = calculate_summaries_from_sessions(sessions)
        assert overall["professional_of_color_count"] == 1
        assert overall["poc_session_count"] == 1


# ── apply_sorting_and_pagination ──────────────────────────────────────


class TestApplySortingAndPagination:

    def test_default_pagination(self):
        sessions = [_session() for _ in range(30)]
        result = apply_sorting_and_pagination(sessions, {}, {"year": "24-25"})
        assert len(result["paginated_data"]) == 25
        assert result["pagination"]["total_records"] == 30
        assert result["pagination"]["total_pages"] == 2

    def test_custom_per_page(self):
        sessions = [_session() for _ in range(10)]
        result = apply_sorting_and_pagination(
            sessions, {"per_page": "5"}, {"year": "24-25"}
        )
        assert len(result["paginated_data"]) == 5

    def test_page_2(self):
        sessions = [_session(teacher_name=f"Teacher {i}") for i in range(30)]
        result = apply_sorting_and_pagination(
            sessions, {"page": "2", "per_page": "25"}, {"year": "24-25"}
        )
        assert len(result["paginated_data"]) == 5  # 30 - 25 = 5

    def test_invalid_page_defaults_to_1(self):
        sessions = [_session()]
        result = apply_sorting_and_pagination(
            sessions, {"page": "abc"}, {"year": "24-25"}
        )
        assert result["pagination"]["current_page"] == 1

    def test_negative_page_defaults_to_1(self):
        sessions = [_session()]
        result = apply_sorting_and_pagination(
            sessions, {"page": "-1"}, {"year": "24-25"}
        )
        assert result["pagination"]["current_page"] == 1

    def test_sort_by_teacher_name(self):
        sessions = [
            _session(teacher_name="Zara"),
            _session(teacher_name="Adam"),
        ]
        result = apply_sorting_and_pagination(
            sessions, {"sort": "teacher_name", "order": "asc"}, {"year": "24-25"}
        )
        assert result["paginated_data"][0]["teacher_name"] == "Adam"
        assert result["paginated_data"][1]["teacher_name"] == "Zara"

    def test_sort_desc(self):
        sessions = [
            _session(teacher_name="Adam"),
            _session(teacher_name="Zara"),
        ]
        result = apply_sorting_and_pagination(
            sessions, {"sort": "teacher_name", "order": "desc"}, {"year": "24-25"}
        )
        assert result["paginated_data"][0]["teacher_name"] == "Zara"

    def test_empty_session_list(self):
        result = apply_sorting_and_pagination([], {}, {"year": "24-25"})
        assert result["paginated_data"] == []
        assert result["pagination"]["total_records"] == 0
        assert result["pagination"]["total_pages"] == 0

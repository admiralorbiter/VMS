"""
Teacher Routes Module
====================

This module handles all teacher-related functionality including:
- Teacher management and viewing
- Salesforce import for teachers
- Teacher exclusion from reports
- Teacher-specific operations

Key Features:
- Teacher listing and pagination
- Salesforce data import
- Teacher exclusion management
- Teacher detail views
- Contact information management
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from config import Config
from models import db
from models.school_model import School
from models.teacher import Teacher, TeacherStatus
from routes.decorators import admin_required, global_users_only

# Create Blueprint for teacher routes
teachers_bp = Blueprint("teachers", __name__)


@teachers_bp.route("/teachers")
@login_required
@global_users_only
def list_teachers():
    """
    Main teacher management page showing paginated list of teachers.

    Returns:
        Rendered template with paginated teacher data
    """
    # Get pagination parameters from request
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    # Query teachers with pagination - simplified for better performance
    teachers_query = Teacher.query.order_by(Teacher.last_name, Teacher.first_name)

    # Apply pagination directly
    teachers = teachers_query.paginate(page=page, per_page=per_page, error_out=False)

    # Create a pagination-like object
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if page > 1 else None
            self.next_num = page + 1 if page < self.pages else None

        def iter_pages(
            self, left_edge=2, left_current=2, right_current=2, right_edge=2
        ):
            last = 0
            for num in range(1, self.pages + 1):
                if (
                    num <= left_edge
                    or (
                        num > self.page - left_current - 1
                        and num < self.page + right_current
                    )
                    or num > self.pages - right_edge
                ):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    # Get schools for the filter dropdown (with limit for performance)
    schools = School.query.order_by(School.name).limit(100).all()

    return render_template(
        "teachers/teachers.html",
        teachers=teachers,
        schools=schools,
        current_page=page,
        per_page=per_page,
        total_teachers=teachers.total,
        per_page_options=[10, 25, 50, 100],
    )


@teachers_bp.route("/teachers/toggle-exclude-reports/<int:id>", methods=["POST"])
@login_required
@global_users_only
@admin_required
def toggle_teacher_exclude_reports(id):
    """Toggle the exclude_from_reports field for a teacher - Admin only"""

    try:
        teacher = db.session.get(Teacher, id)
        if not teacher:
            return jsonify({"success": False, "message": "Teacher not found"}), 404

        # Get the new value from the request
        data = request.get_json()
        exclude_from_reports = data.get("exclude_from_reports", False)

        # Update the field
        teacher.exclude_from_reports = exclude_from_reports
        db.session.commit()

        status = "excluded" if exclude_from_reports else "included"
        return jsonify(
            {"success": True, "message": f"Teacher {status} from reports successfully"}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@teachers_bp.route("/teachers/view/<int:teacher_id>")
@login_required
@global_users_only
def view_teacher(teacher_id):
    """
    View detailed information for a specific teacher.

    Args:
        id: Database ID of the teacher

    Returns:
        Rendered template with detailed teacher information
    """
    try:
        teacher = Teacher.query.get_or_404(teacher_id)

        # Get related contact information
        primary_email = teacher.emails.filter_by(primary=True).first()
        primary_phone = teacher.phones.filter_by(primary=True).first()
        primary_address = teacher.addresses.filter_by(primary=True).first()

        # Debug: Print school relationship info
        print(f"Teacher: {teacher.first_name} {teacher.last_name}")
        print(f"School ID: {teacher.school_id}")
        print(f"Salesforce School ID: {teacher.salesforce_school_id}")
        print(f"School relationship: {teacher.school}")

        return render_template(
            "teachers/view.html",
            teacher=teacher,
            primary_email=primary_email,
            primary_phone=primary_phone,
            primary_address=primary_address,
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@teachers_bp.route("/teachers/edit/<int:teacher_id>", methods=["GET", "POST"])
@login_required
@global_users_only
@admin_required
def edit_teacher(teacher_id):
    """
    Edit teacher information - Admin only

    Args:
        teacher_id: Database ID of the teacher

    Returns:
        Rendered template with edit form or redirect on success
    """

    try:
        teacher = Teacher.query.get_or_404(teacher_id)

        if request.method == "POST":
            # Update teacher information
            teacher.first_name = request.form.get("first_name", teacher.first_name)
            teacher.last_name = request.form.get("last_name", teacher.last_name)
            teacher.salesforce_id = request.form.get(
                "salesforce_id", teacher.salesforce_id
            )
            teacher.status = TeacherStatus(
                request.form.get("status", teacher.status.value)
            )
            teacher.school_id = request.form.get("school_id", teacher.school_id)
            teacher.exclude_from_reports = "exclude_from_reports" in request.form

            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": f"Teacher {teacher.first_name} {teacher.last_name} updated successfully",
                }
            )

        # GET request - show edit form
        schools = School.query.order_by(School.name).all()

        return render_template("teachers/edit.html", teacher=teacher, schools=schools)

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@teachers_bp.route("/teachers/merge")
@login_required
@global_users_only
@admin_required
def teacher_merge():
    """Admin UI to search and merge duplicate Teacher records."""
    return render_template("teachers/merge.html")


@teachers_bp.route("/teachers/merge/candidates")
@login_required
@global_users_only
@admin_required
def teacher_merge_candidates():
    """AJAX: find suspected duplicate pairs (same first, diff last, shared events)."""
    from collections import defaultdict

    from models.event import EventTeacher
    from models.teacher_progress import TeacherProgress
    from services.teacher_matching_service import normalize_name

    teachers = Teacher.query.filter(Teacher.active == True).all()

    # Index by normalized first name
    by_first = defaultdict(list)
    for t in teachers:
        nf = normalize_name(t.first_name or "")
        if nf:
            by_first[nf].append(t)

    # Batch: all event_teacher pairs for fast shared-event lookup
    et_rows = db.session.execute(
        db.text("SELECT teacher_id, event_id FROM event_teacher")
    ).fetchall()
    events_by_teacher = defaultdict(set)
    for tid, eid in et_rows:
        events_by_teacher[tid].add(eid)

    # Find pairs: same first name, different last name, 2+ shared events
    candidates = []
    seen = set()
    for first, group in by_first.items():
        if len(group) < 2:
            continue
        for i, t1 in enumerate(group):
            nl1 = normalize_name(t1.last_name or "")
            e1 = events_by_teacher.get(t1.id, set())
            if not e1:
                continue
            s1 = t1.school.name if t1.school else None
            s1_real = s1 and s1 != "--"
            for t2 in group[i + 1 :]:
                nl2 = normalize_name(t2.last_name or "")
                if nl1 == nl2:
                    continue  # Same last name = exact-name dup, not this category
                e2 = events_by_teacher.get(t2.id, set())
                if not e2:
                    continue

                # Filter 1: if both have real schools and they differ, skip
                s2 = t2.school.name if t2.school else None
                s2_real = s2 and s2 != "--"
                if s1_real and s2_real and s1 != s2:
                    continue

                # Filter 2: require 90%+ overlap AND min 2 shared
                shared = len(e1 & e2)
                min_events = min(len(e1), len(e2))
                if shared < 2 or min_events == 0 or shared / min_events < 0.9:
                    continue

                pair_key = tuple(sorted([t1.id, t2.id]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                overlap_pct = round(100 * shared / min_events)
                candidates.append(
                    {
                        "teacher_a": {
                            "id": t1.id,
                            "first_name": t1.first_name or "",
                            "last_name": t1.last_name or "",
                            "school": s1 or "--",
                            "event_count": len(e1),
                            "tp_count": TeacherProgress.query.filter_by(
                                teacher_id=t1.id
                            ).count(),
                        },
                        "teacher_b": {
                            "id": t2.id,
                            "first_name": t2.first_name or "",
                            "last_name": t2.last_name or "",
                            "school": s2 or "--",
                            "event_count": len(e2),
                            "tp_count": TeacherProgress.query.filter_by(
                                teacher_id=t2.id
                            ).count(),
                        },
                        "shared_events": shared,
                        "overlap_pct": overlap_pct,
                    }
                )

    # Sort by shared events descending (highest confidence first)
    candidates.sort(key=lambda c: c["shared_events"], reverse=True)
    return jsonify(candidates[:50])


@teachers_bp.route("/teachers/merge/search")
@login_required
@global_users_only
@admin_required
def teacher_merge_search():
    """AJAX: search teachers by name for the merge UI."""
    from models.event import EventTeacher
    from models.teacher_progress import TeacherProgress

    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    results = (
        Teacher.query.filter(
            Teacher.active == True,
            db.or_(
                Teacher.first_name.ilike(f"%{q}%"),
                Teacher.last_name.ilike(f"%{q}%"),
            ),
        )
        .limit(20)
        .all()
    )

    return jsonify(
        [
            {
                "id": t.id,
                "first_name": t.first_name or "",
                "last_name": t.last_name or "",
                "school": t.school.name if t.school else "--",
                "email": t.cached_email or "--",
                "import_source": t.import_source or "--",
                "event_count": EventTeacher.query.filter_by(teacher_id=t.id).count(),
                "tp_count": TeacherProgress.query.filter_by(teacher_id=t.id).count(),
            }
            for t in results
        ]
    )


@teachers_bp.route("/teachers/merge/compare")
@login_required
@global_users_only
@admin_required
def teacher_merge_compare():
    """AJAX: get detailed comparison data for two teachers."""
    from models.event import EventTeacher
    from models.teacher_progress import TeacherProgress

    id_a = request.args.get("id_a", type=int)
    id_b = request.args.get("id_b", type=int)
    if not id_a or not id_b:
        return jsonify({"error": "Both teacher IDs required"}), 400

    teacher_a = db.session.get(Teacher, id_a)
    teacher_b = db.session.get(Teacher, id_b)
    if not teacher_a or not teacher_b:
        return jsonify({"error": "Teacher not found"}), 404

    def teacher_data(t):
        ets = EventTeacher.query.filter_by(teacher_id=t.id).all()
        tps = TeacherProgress.query.filter_by(teacher_id=t.id).all()
        return {
            "id": t.id,
            "first_name": t.first_name or "",
            "last_name": t.last_name or "",
            "school": t.school.name if t.school else "--",
            "email": t.cached_email or "--",
            "import_source": t.import_source or "--",
            "active": t.active,
            "events": [{"event_id": et.event_id, "status": et.status} for et in ets],
            "event_count": len(ets),
            "tp_count": len(tps),
            "tp_names": [tp.name for tp in tps],
        }

    data_a = teacher_data(teacher_a)
    data_b = teacher_data(teacher_b)

    # Find shared events
    events_a = {e["event_id"]: e["status"] for e in data_a["events"]}
    events_b = {e["event_id"]: e["status"] for e in data_b["events"]}
    shared = set(events_a.keys()) & set(events_b.keys())

    return jsonify(
        {
            "teacher_a": data_a,
            "teacher_b": data_b,
            "shared_events": len(shared),
            "shared_event_details": [
                {
                    "event_id": eid,
                    "status_a": events_a[eid],
                    "status_b": events_b[eid],
                }
                for eid in sorted(shared)
            ],
        }
    )


@teachers_bp.route("/teachers/merge/execute", methods=["POST"])
@login_required
@global_users_only
@admin_required
def teacher_merge_execute():
    """POST: merge duplicate Teacher into canonical with audit trail."""
    import json
    from datetime import datetime, timezone

    from models.event import EventTeacher
    from models.pathful_import import PathfulUnmatchedRecord
    from models.student import Student
    from models.teacher_progress import TeacherProgress

    data = request.get_json()
    keep_id = data.get("keep_id")
    merge_id = data.get("merge_id")

    if not keep_id or not merge_id or keep_id == merge_id:
        return jsonify({"error": "Invalid teacher IDs"}), 400

    canonical = db.session.get(Teacher, keep_id)
    duplicate = db.session.get(Teacher, merge_id)
    if not canonical or not duplicate:
        return jsonify({"error": "Teacher not found"}), 404

    STATUS_PRIORITY = {"attended": 3, "no_show": 2, "registered": 1}
    undo = {
        "canonical_id": canonical.id,
        "duplicate_id": duplicate.id,
        "canonical_name": f"{canonical.first_name} {canonical.last_name}",
        "duplicate_name": f"{duplicate.first_name} {duplicate.last_name}",
        "merged_by": current_user.username,
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "ets_moved": [],
        "ets_deduped": [],
        "status_upgrades": [],
        "tps_moved": [],
        "students_moved": [],
    }

    try:
        # EventTeacher: status-aware merge
        canon_events = {
            et.event_id: et
            for et in EventTeacher.query.filter_by(teacher_id=canonical.id).all()
        }

        for et in EventTeacher.query.filter_by(teacher_id=duplicate.id).all():
            if et.event_id in canon_events:
                canon_et = canon_events[et.event_id]
                dup_p = STATUS_PRIORITY.get(et.status, 0)
                canon_p = STATUS_PRIORITY.get(canon_et.status, 0)
                if dup_p > canon_p:
                    undo["status_upgrades"].append(
                        {
                            "event_id": et.event_id,
                            "old": canon_et.status,
                            "new": et.status,
                        }
                    )
                    canon_et.status = et.status
                    if et.confirmed_at and not canon_et.confirmed_at:
                        canon_et.confirmed_at = et.confirmed_at
                db.session.delete(et)
                undo["ets_deduped"].append(et.event_id)
            else:
                et.teacher_id = canonical.id
                undo["ets_moved"].append(et.event_id)

        # TeacherProgress
        for tp in TeacherProgress.query.filter_by(teacher_id=duplicate.id).all():
            tp.teacher_id = canonical.id
            undo["tps_moved"].append(tp.id)

        # Student
        for s in Student.query.filter_by(teacher_id=duplicate.id).all():
            s.teacher_id = canonical.id
            undo["students_moved"].append(s.id)

        # PathfulUnmatchedRecord
        for um in PathfulUnmatchedRecord.query.filter_by(
            resolved_teacher_id=duplicate.id
        ).all():
            um.resolved_teacher_id = canonical.id

        # Mark duplicate inactive
        duplicate.active = False
        duplicate.import_source = (
            f"{duplicate.import_source}|merged_into_{canonical.id}"
            if duplicate.import_source
            else f"merged_into_{canonical.id}"
        )

        db.session.commit()

        # Save audit log
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_path = f"data/td035_name_merge_2026_03_13/merge_ui_{timestamp}.json"
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(undo, f, indent=2)
        except FileNotFoundError:
            pass  # Directory may not exist; audit info is in the response

        return jsonify(
            {
                "success": True,
                "message": (
                    f"Merged '{undo['duplicate_name']}' into "
                    f"'{undo['canonical_name']}'. "
                    f"ETs moved: {len(undo['ets_moved'])}, "
                    f"deduped: {len(undo['ets_deduped'])}, "
                    f"upgrades: {len(undo['status_upgrades'])}"
                ),
                "audit": undo,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def load_routes(bp):
    """Load teacher routes into the main blueprint"""
    bp.register_blueprint(teachers_bp)

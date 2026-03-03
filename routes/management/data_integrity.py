"""
Data integrity route handlers for management.

Contains data flag review and student participation deduplication.
"""

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from routes.decorators import admin_required


def register_data_integrity_routes(bp):
    """Register data integrity routes on the management blueprint."""

    @bp.route("/admin/data-flags")
    @login_required
    @admin_required
    def data_flags():
        """
        Admin page to review all teacher data flags across tenants.

        Permission Requirements:
            - Admin access required

        Query Parameters:
            type: Filter by flag type (missing_session, not_tracked, other)
            status: Filter by status (open, resolved, all). Default: open
        """

        from models.teacher_data_flag import TeacherDataFlag, TeacherDataFlagType

        # Build query
        q = TeacherDataFlag.query

        # Status filter (default to open)
        status = request.args.get("status", "open")
        if status == "open":
            q = q.filter_by(is_resolved=False)
        elif status == "resolved":
            q = q.filter_by(is_resolved=True)

        # Type filter
        type_filter = request.args.get("type", "")
        if type_filter in TeacherDataFlagType.all_types():
            q = q.filter_by(flag_type=type_filter)

        flags = q.order_by(TeacherDataFlag.created_at.desc()).all()

        # Stats — always count open flags regardless of current filter
        total_open = TeacherDataFlag.query.filter_by(is_resolved=False).count()
        count_by_type = {}
        for ft in TeacherDataFlagType.all_types():
            count_by_type[ft] = TeacherDataFlag.query.filter_by(
                is_resolved=False, flag_type=ft
            ).count()

        return render_template(
            "management/data_flags.html",
            flags=flags,
            total_open=total_open,
            count_by_type=count_by_type,
        )

    @bp.route("/admin/scan-student-participation-duplicates")
    @login_required
    @admin_required
    def scan_student_participation_duplicates():
        """
        Scan for duplicate EventStudentParticipation records by (event_id, student_id).

        Admin-only utility to help decide on enforcing a unique constraint.
        Returns a simple HTML view if template exists, otherwise JSON.
        """

        from sqlalchemy import func

        from models.event import EventStudentParticipation

        dup_pairs = (
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

        results = []
        for event_id, student_id, cnt in dup_pairs:
            records = (
                db.session.query(EventStudentParticipation)
                .filter(
                    EventStudentParticipation.event_id == event_id,
                    EventStudentParticipation.student_id == student_id,
                )
                .all()
            )
            results.append(
                {
                    "event_id": event_id,
                    "student_id": student_id,
                    "count": int(cnt or 0),
                    "records": [
                        {
                            "id": r.id,
                            "salesforce_id": r.salesforce_id,
                            "status": r.status,
                            "delivery_hours": r.delivery_hours,
                            "created_at": getattr(r, "created_at", None),
                        }
                        for r in records
                    ],
                }
            )

        try:
            return render_template(
                "management/scan_student_participation_duplicates.html",
                duplicates=results,
            )
        except Exception:
            # Fallback JSON if template not present
            return jsonify({"duplicates": results, "total_pairs": len(results)})

    @bp.route("/admin/dedupe-student-participations", methods=["POST"])
    @bp.route("/dedupe-student-participations", methods=["POST"])
    @login_required
    @admin_required
    def dedupe_student_participations():
        """
        Admin action: deduplicate EventStudentParticipation by (event_id, student_id).

        Strategy per duplicate pair:
          - Keep the earliest created record (smallest id).
          - Merge fields (prefer non-null status, delivery_hours, age_group, salesforce_id).
          - Delete the other records.
        Returns JSON summary.
        """

        from sqlalchemy import func

        from models.event import EventStudentParticipation

        summary = {"pairs": 0, "deleted": 0, "updated": 0}

        dup_pairs = (
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

        for event_id, student_id, cnt in dup_pairs:
            records = (
                db.session.query(EventStudentParticipation)
                .filter(
                    EventStudentParticipation.event_id == event_id,
                    EventStudentParticipation.student_id == student_id,
                )
                .order_by(EventStudentParticipation.id.asc())
                .all()
            )
            if not records:
                continue
            summary["pairs"] += 1

            keeper = records[0]
            for rec in records[1:]:
                # Merge non-null fields into keeper
                if getattr(keeper, "salesforce_id", None) is None and rec.salesforce_id:
                    keeper.salesforce_id = rec.salesforce_id
                if getattr(rec, "status", None):
                    keeper.status = rec.status
                if getattr(rec, "delivery_hours", None) is not None:
                    keeper.delivery_hours = rec.delivery_hours
                if getattr(rec, "age_group", None):
                    keeper.age_group = rec.age_group
                db.session.delete(rec)
                summary["deleted"] += 1
            summary["updated"] += 1

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e), "summary": summary}), 500

        return jsonify({"success": True, "summary": summary})

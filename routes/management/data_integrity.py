"""
Data integrity route handlers for management.

Contains data flag review and student participation deduplication.
"""

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from routes.decorators import admin_required, handle_route_errors


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

        Admin-only diagnostic utility to help decide on enforcing a unique constraint.
        Returns JSON summary of duplicate pairs.
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

        return jsonify({"duplicates": results, "total_pairs": len(results)})

    @bp.route("/admin/dedupe-student-participations", methods=["POST"])
    @bp.route("/dedupe-student-participations", methods=["POST"])
    @login_required
    @admin_required
    @handle_route_errors
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

        db.session.commit()

        return jsonify({"success": True, "summary": summary})

    # ── TD-034 Data Quality Dashboard ──────────────────────────────

    @bp.route("/admin/data-quality")
    @login_required
    @admin_required
    def data_quality_dashboard():
        """
        Admin dashboard to review DataQualityFlags from SF imports.

        Query Parameters:
            issue_type: Filter by issue type (all_caps_name, null_org_type, etc.)
            status: open | dismissed | fixed_in_sf | auto_fixed | all (default: open)
            entity_type: contact | organization | volunteer | all
            page: Pagination page number (default: 1)
        """
        from sqlalchemy import func

        from models.data_quality_flag import DataQualityFlag, DataQualityIssueType

        # Filters
        status = request.args.get("status", "open")
        issue_type = request.args.get("issue_type", "")
        entity_type = request.args.get("entity_type", "")
        page = request.args.get("page", 1, type=int)
        per_page = 50

        q = DataQualityFlag.query

        if status and status != "all":
            q = q.filter_by(status=status)

        if issue_type and issue_type in DataQualityIssueType.all_types():
            q = q.filter_by(issue_type=issue_type)

        if entity_type and entity_type != "all":
            q = q.filter_by(entity_type=entity_type)

        # Paginate
        pagination = q.order_by(DataQualityFlag.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Stats (always count open)
        total_open = DataQualityFlag.query.filter_by(status="open").count()
        total_all = DataQualityFlag.query.count()

        count_by_type = {}
        for it in DataQualityIssueType.all_types():
            count_by_type[it] = DataQualityFlag.query.filter_by(
                status="open", issue_type=it
            ).count()

        # Entity type breakdown
        entity_types = [
            r[0]
            for r in db.session.query(DataQualityFlag.entity_type)
            .distinct()
            .order_by(DataQualityFlag.entity_type)
            .all()
        ]

        return render_template(
            "management/data_quality_dashboard.html",
            flags=pagination.items,
            pagination=pagination,
            total_open=total_open,
            total_all=total_all,
            count_by_type=count_by_type,
            issue_types=DataQualityIssueType.all_types(),
            issue_type_display=DataQualityIssueType.display_name,
            entity_types=entity_types,
        )

    @bp.route("/admin/data-quality/<int:flag_id>/dismiss", methods=["POST"])
    @login_required
    @admin_required
    @handle_route_errors
    def dismiss_data_quality_flag(flag_id):
        """Dismiss a single DataQualityFlag."""
        from models.data_quality_flag import DataQualityFlag

        flag = DataQualityFlag.query.get_or_404(flag_id)
        data = request.get_json(silent=True) or {}
        status = data.get("status", "dismissed")
        notes = data.get("notes", "")

        flag.resolve(status=status, notes=notes, resolved_by=current_user.id)
        db.session.commit()

        return jsonify({"success": True, "id": flag_id, "status": status})

    @bp.route("/admin/data-quality/bulk-dismiss", methods=["POST"])
    @login_required
    @admin_required
    @handle_route_errors
    def bulk_dismiss_data_quality_flags():
        """Bulk-dismiss DataQualityFlags by issue type."""
        from models.data_quality_flag import DataQualityFlag

        data = request.get_json(silent=True) or {}
        issue_type = data.get("issue_type")
        status = data.get("status", "dismissed")
        notes = data.get("notes", "")

        if not issue_type:
            return jsonify({"error": "issue_type required"}), 400

        flags = DataQualityFlag.query.filter_by(
            status="open", issue_type=issue_type
        ).all()

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        for f in flags:
            f.status = status
            f.resolved_at = now
            f.resolved_by = current_user.id
            f.resolution_notes = notes

        db.session.commit()

        return jsonify({"success": True, "count": len(flags), "issue_type": issue_type})

    @bp.route("/admin/import-health")
    @login_required
    @admin_required
    @handle_route_errors
    def import_health():
        """
        Dashboard for monitoring Salesforce import pipelines health.
        """
        from datetime import datetime, timezone

        from models.data_quality_flag import DataQualityFlag, DataQualityIssueType
        from models.pending_participation import PendingParticipationImport
        from models.sync_log import SyncLog

        sync_types = [
            "organizations",
            "volunteers",
            "affiliations",
            "events",
            "history",
            "students",
            "student_participations",
            "teachers",
            "schools",
            "classes",
        ]

        now = datetime.now(timezone.utc)

        health_data = []
        for st in sync_types:
            log = SyncLog.get_latest_by_type(st)
            watermark, buffer_hours = SyncLog.get_watermark_with_buffer(st)

            watermark_age_hours = None
            if watermark:
                if watermark.tzinfo is None:
                    watermark = watermark.replace(tzinfo=timezone.utc)
                watermark_age_hours = (now - watermark).total_seconds() / 3600

            health_data.append(
                {
                    "sync_type": st,
                    "last_run": log,
                    "watermark_age_hours": watermark_age_hours,
                    "recovery_mode": buffer_hours == 48,
                }
            )

        pending_stats = {
            "total": PendingParticipationImport.query.filter(
                PendingParticipationImport.resolved_at.is_(None)
            ).count(),
            "orphaned": PendingParticipationImport.query.filter(
                PendingParticipationImport.resolved_at.is_(None),
                PendingParticipationImport.error_reason == "likely_sf_orphan",
            ).count(),
            "resolvable": PendingParticipationImport.query.filter(
                PendingParticipationImport.resolved_at.is_(None),
                (PendingParticipationImport.error_reason != "likely_sf_orphan")
                | (PendingParticipationImport.error_reason.is_(None)),
            ).count(),
        }

        open_flags = DataQualityFlag.query.filter_by(
            issue_type=DataQualityIssueType.UNMATCHED_SF_PARTICIPATION, status="open"
        ).count()

        return render_template(
            "management/import_health.html",
            health_data=health_data,
            pending_stats=pending_stats,
            open_flags=open_flags,
        )

    @bp.route("/admin/import-health/pending-export")
    @login_required
    @admin_required
    def export_pending_participations():
        """Export orphaned Salesforce participation IDs as CSV."""
        import csv
        import io

        from flask import Response

        from models.pending_participation import PendingParticipationImport

        orphans = PendingParticipationImport.query.filter(
            PendingParticipationImport.resolved_at.is_(None),
            PendingParticipationImport.error_reason == "likely_sf_orphan",
        ).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["sf_participation_id", "sf_contact_id", "sf_session_id", "first_seen_at"]
        )

        for orphan in orphans:
            writer.writerow(
                [
                    orphan.sf_participation_id,
                    orphan.sf_contact_id,
                    orphan.sf_session_id,
                    orphan.first_seen_at.isoformat() if orphan.first_seen_at else "",
                ]
            )

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-disposition": "attachment; filename=orphaned_participations.csv"
            },
        )

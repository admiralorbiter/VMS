from datetime import datetime

from flask import Blueprint, render_template, request
from flask_login import login_required

from models.event import EventStatus
from models.pathways import Pathway

# Create blueprint
pathways_bp = Blueprint("pathways", __name__)


def load_routes(bp):
    @bp.route("/reports/pathways")
    @login_required
    def pathways_report():
        # Get filter parameters
        search = request.args.get("search", "").strip()
        selected_year = int(request.args.get("year", datetime.now().year))

        # Base query
        query = Pathway.query

        # Apply search filter if provided
        if search:
            query = query.filter(Pathway.name.ilike(f"%{search}%"))

        # Get all pathways
        pathways = query.all()

        # Get current year for the year filter dropdown
        current_year = datetime.now().year

        return render_template("reports/pathways.html", pathways=pathways, search=search, selected_year=selected_year, current_year=current_year)

    @bp.route("/reports/pathways/<int:pathway_id>")
    @login_required
    def pathway_detail(pathway_id):
        # Get the pathway
        pathway = Pathway.query.get_or_404(pathway_id)

        # Get active events (not completed or cancelled)
        active_events = [event for event in pathway.events if event.status not in [EventStatus.COMPLETED, EventStatus.CANCELLED]]

        # Calculate total attendance
        total_attendance = sum(event.attended_count or 0 for event in pathway.events)

        return render_template("reports/pathway_detail.html", pathway=pathway, active_events=active_events, total_attendance=total_attendance)

"""
KCTAA Special Volunteer Match Report
====================================

This module provides a special report that matches a provided list of KCTAA
personnel names against volunteers in the system, showing volunteer activity
counts and match quality indicators.

Key Features:
- Reads KCTAA name list from CSV file
- Performs exact and fuzzy name matching
- Shows volunteer participation statistics
- Displays match quality scores and indicators
- Supports HTML and CSV export formats

Name Matching:
- Exact match: First + last name match (case-insensitive, punctuation-insensitive)
- Fuzzy match: Similarity-based matching for near-matches
- Multiple matches: Returns all matches per CSV person when multiple volunteers match

Data Source:
- CSV file: data/kctaa_first_last_names.csv
- Format: First Name, Last Name

Report Routes:
- GET /reports/kctaa: HTML view with filters
- GET /reports/kctaa.csv: CSV export
"""

import csv
import io
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from flask import Blueprint, current_app, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import and_, func, or_

from models import db
from models.contact import Email
from models.event import Event, EventStatus
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation, Volunteer

# Create blueprint
kctaa_special_bp = Blueprint("kctaa_special", __name__)

# Configuration constants
FUZZY_MATCH_THRESHOLD = 90  # Minimum similarity score (0-100) for fuzzy matches
DEFAULT_MIN_SCORE = 0.9  # Default minimum match score for filtering (0.0-1.0)


def _normalize_name(name):
    """
    Normalize a name for matching by removing punctuation and standardizing case.

    Args:
        name: Name string to normalize

    Returns:
        Normalized name string (lowercase, punctuation removed)
    """
    if not name:
        return ""
    # Remove punctuation (periods, commas, apostrophes, etc.)
    normalized = re.sub(r"[^\w\s]", "", str(name))
    # Convert to lowercase and strip whitespace
    normalized = normalized.lower().strip()
    return normalized


def _read_kctaa_csv(file_path=None):
    """
    Read and normalize KCTAA name list from CSV file.

    Args:
        file_path: Optional path to CSV file. If None, uses default from config or data directory.

    Returns:
        List of dicts with keys: first_name, last_name, normalized_first, normalized_last, normalized_full
    """
    if file_path is None:
        # Try config first, then default location
        file_path = current_app.config.get(
            "KCTAA_NAME_LIST_PATH", "data/kctaa_first_last_names.csv"
        )
        # If relative path, make it relative to project root
        if not os.path.isabs(file_path):
            # Calculate project root: go up from routes/reports/kctaa_special.py -> routes/reports -> routes -> project root
            current_file = Path(__file__)
            project_root = (
                current_file.parent.parent.parent
            )  # routes/reports -> routes -> project root
            file_path = project_root / file_path

    csv_records = []

    # Convert to Path object if it's a string
    if isinstance(file_path, str):
        file_path = Path(file_path)
    elif not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Check if file exists and log helpful info
    if not file_path.exists():
        current_app.logger.error(f"KCTAA CSV file not found: {file_path}")
        current_app.logger.error(f"Absolute path: {file_path.resolve()}")
        current_app.logger.error(f"Current working directory: {os.getcwd()}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                first = row.get("First Name", "").strip()
                last = row.get("Last Name", "").strip()

                if not first and not last:
                    continue  # Skip empty rows

                normalized_first = _normalize_name(first)
                normalized_last = _normalize_name(last)
                normalized_full = f"{normalized_first} {normalized_last}".strip()

                csv_records.append(
                    {
                        "index": idx,
                        "first_name": first,
                        "last_name": last,
                        "normalized_first": normalized_first,
                        "normalized_last": normalized_last,
                        "normalized_full": normalized_full,
                    }
                )
        current_app.logger.info(
            f"Successfully loaded {len(csv_records)} KCTAA names from {file_path}"
        )
    except FileNotFoundError:
        current_app.logger.error(f"KCTAA CSV file not found: {file_path}")
        current_app.logger.error(f"Absolute path: {file_path.resolve()}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error reading KCTAA CSV: {str(e)}")
        current_app.logger.error(f"File path: {file_path}")
        current_app.logger.error(f"Absolute path: {file_path.resolve()}")
        import traceback

        current_app.logger.error(traceback.format_exc())
        return []

    return csv_records


def _load_volunteers_with_stats():
    """
    Load all volunteers with their participation statistics.

    Returns:
        Dict mapping volunteer_id to volunteer data with participation stats
    """
    # Query volunteers with aggregated participation stats
    # Note: We'll get organization and email separately to avoid duplicate rows
    query = (
        db.session.query(
            Volunteer.id,
            Volunteer.first_name,
            Volunteer.last_name,
            func.count(EventParticipation.id).label("event_count"),
            func.sum(EventParticipation.delivery_hours).label("total_hours"),
            func.max(Event.start_date).label("last_event_date"),
        )
        .outerjoin(
            EventParticipation,
            and_(
                EventParticipation.volunteer_id == Volunteer.id,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed", "Simulcast"]
                ),
            ),
        )
        .outerjoin(
            Event,
            and_(
                Event.id == EventParticipation.event_id,
                Event.status == EventStatus.COMPLETED,
            ),
        )
        .filter(Volunteer.exclude_from_reports == False)
        .group_by(
            Volunteer.id,
            Volunteer.first_name,
            Volunteer.last_name,
        )
    )

    volunteers = {}
    for row in query.all():
        vol_id = row.id
        normalized_first = _normalize_name(row.first_name)
        normalized_last = _normalize_name(row.last_name)
        normalized_full = f"{normalized_first} {normalized_last}".strip()

        volunteers[vol_id] = {
            "id": vol_id,
            "first_name": row.first_name or "",
            "last_name": row.last_name or "",
            "email": "",  # Will be populated from Email table
            "organization": "Independent",  # Default, will be updated if primary org found
            "normalized_first": normalized_first,
            "normalized_last": normalized_last,
            "normalized_full": normalized_full,
            "event_count": int(row.event_count or 0),
            "total_hours": float(row.total_hours or 0.0),
            "last_event_date": row.last_event_date,
        }

    # Post-process to get primary email for volunteers
    # Query primary emails separately to avoid duplicates
    volunteer_ids = list(volunteers.keys())
    if volunteer_ids:
        primary_emails = (
            db.session.query(Email.contact_id, Email.email)
            .filter(Email.contact_id.in_(volunteer_ids), Email.primary == True)
            .all()
        )

        # If no primary email found for some volunteers, try any email
        emails_map = {row.contact_id: row.email for row in primary_emails}
        volunteers_without_primary = [
            vid for vid in volunteer_ids if vid not in emails_map
        ]

        if volunteers_without_primary:
            any_emails = (
                db.session.query(Email.contact_id, Email.email)
                .filter(Email.contact_id.in_(volunteers_without_primary))
                .all()
            )
            # Only add if not already in map (avoid duplicates)
            for row in any_emails:
                if row.contact_id not in emails_map:
                    emails_map[row.contact_id] = row.email

        # Update volunteers with email addresses
        for vol_id, email in emails_map.items():
            if vol_id in volunteers:
                volunteers[vol_id]["email"] = email or ""

    # Post-process to get primary organization for volunteers
    # Query primary organizations separately to avoid duplicates
    if volunteer_ids:
        primary_orgs = (
            db.session.query(VolunteerOrganization.volunteer_id, Organization.name)
            .join(
                Organization, VolunteerOrganization.organization_id == Organization.id
            )
            .filter(VolunteerOrganization.is_primary == True)
            .all()
        )

        for vol_id, org_name in primary_orgs:
            if vol_id in volunteers:
                if org_name and not (len(org_name) == 18 and org_name.isalnum()):
                    volunteers[vol_id]["organization"] = org_name

    return volunteers


def _fuzzy_similarity(str1, str2):
    """
    Calculate fuzzy similarity score between two strings.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score as float between 0.0 and 1.0 (1.0 = identical)
    """
    return SequenceMatcher(None, str1, str2).ratio()


def _match_kctaa_names_to_volunteers(csv_records, volunteers, min_score=0.0):
    """
    Match CSV names to volunteers using exact and fuzzy matching.

    Args:
        csv_records: List of CSV name records from _read_kctaa_csv
        volunteers: Dict of volunteer data from _load_volunteers_with_stats
        min_score: Minimum match score (0.0-1.0) for filtering results

    Returns:
        List of match records, one per (CSV person, volunteer) pair
    """
    matches = []

    for csv_rec in csv_records:
        csv_normalized_first = csv_rec["normalized_first"]
        csv_normalized_last = csv_rec["normalized_last"]
        csv_normalized_full = csv_rec["normalized_full"]

        # Find exact matches first
        exact_matches = []
        for vol_id, vol_data in volunteers.items():
            if (
                vol_data["normalized_first"] == csv_normalized_first
                and vol_data["normalized_last"] == csv_normalized_last
            ):
                exact_matches.append((vol_id, vol_data, 1.0))

        # If we have exact matches, return all of them
        if exact_matches:
            match_count = len(exact_matches)
            for vol_id, vol_data, score in exact_matches:
                if score >= min_score:
                    matches.append(
                        {
                            "csv_index": csv_rec["index"],
                            "csv_first_name": csv_rec["first_name"],
                            "csv_last_name": csv_rec["last_name"],
                            "csv_full_name": f"{csv_rec['first_name']} {csv_rec['last_name']}",
                            "volunteer_id": vol_id,
                            "volunteer_name": f"{vol_data['first_name']} {vol_data['last_name']}",
                            "volunteer_email": vol_data["email"],
                            "volunteer_organization": vol_data["organization"],
                            "event_count": vol_data["event_count"],
                            "total_hours": vol_data["total_hours"],
                            "last_event_date": vol_data["last_event_date"],
                            "match_type": "exact",
                            "match_score": score,
                            "is_exact_match": True,
                            "match_count": match_count,
                        }
                    )
        else:
            # No exact matches, try fuzzy matching
            fuzzy_matches = []
            for vol_id, vol_data in volunteers.items():
                # Compare normalized full names
                similarity = _fuzzy_similarity(
                    csv_normalized_full, vol_data["normalized_full"]
                )
                similarity_score = similarity * 100  # Convert to 0-100 scale

                if similarity_score >= FUZZY_MATCH_THRESHOLD:
                    fuzzy_matches.append((vol_id, vol_data, similarity))

            # Sort by score descending
            fuzzy_matches.sort(key=lambda x: x[2], reverse=True)

            # Return all fuzzy matches
            match_count = len(fuzzy_matches)
            for vol_id, vol_data, score in fuzzy_matches:
                if score >= min_score:
                    matches.append(
                        {
                            "csv_index": csv_rec["index"],
                            "csv_first_name": csv_rec["first_name"],
                            "csv_last_name": csv_rec["last_name"],
                            "csv_full_name": f"{csv_rec['first_name']} {csv_rec['last_name']}",
                            "volunteer_id": vol_id,
                            "volunteer_name": f"{vol_data['first_name']} {vol_data['last_name']}",
                            "volunteer_email": vol_data["email"],
                            "volunteer_organization": vol_data["organization"],
                            "event_count": vol_data["event_count"],
                            "total_hours": vol_data["total_hours"],
                            "last_event_date": vol_data["last_event_date"],
                            "match_type": "fuzzy",
                            "match_score": score,
                            "is_exact_match": False,
                            "match_count": match_count,
                        }
                    )

            # If no matches at all, add a "no match" record if min_score allows
            if not fuzzy_matches and min_score == 0.0:
                matches.append(
                    {
                        "csv_index": csv_rec["index"],
                        "csv_first_name": csv_rec["first_name"],
                        "csv_last_name": csv_rec["last_name"],
                        "csv_full_name": f"{csv_rec['first_name']} {csv_rec['last_name']}",
                        "volunteer_id": None,
                        "volunteer_name": None,
                        "volunteer_email": None,
                        "volunteer_organization": None,
                        "event_count": 0,
                        "total_hours": 0.0,
                        "last_event_date": None,
                        "match_type": "none",
                        "match_score": 0.0,
                        "is_exact_match": False,
                        "match_count": 0,
                    }
                )

    return matches


def load_routes(bp):
    """
    Load KCTAA special report routes into the provided blueprint.

    Args:
        bp: Flask Blueprint to register routes with

    Routes:
        GET /reports/kctaa: HTML view with filters
        GET /reports/kctaa.csv: CSV export
    """

    @bp.route("/reports/kctaa")
    @login_required
    def kctaa_report():
        """
        Display the KCTAA volunteer match report.

        Query Parameters:
            min_score: Minimum match score (0.0-1.0) for filtering (default: 0.9)
            include_unmatched: Include unmatched CSV names (0 or 1, default: 0)

        Returns:
            Rendered HTML template with match results
        """
        # Parse query parameters
        min_score = request.args.get("min_score", DEFAULT_MIN_SCORE, type=float)
        include_unmatched = request.args.get("include_unmatched", "0") == "1"

        # Read CSV names
        csv_records = _read_kctaa_csv()
        if not csv_records:
            return render_template(
                "reports/kctaa_special.html",
                error="Could not load KCTAA name list. Please check the CSV file path.",
                matches=[],
                min_score=min_score,
                include_unmatched=include_unmatched,
            )

        # Load volunteers with stats
        volunteers = _load_volunteers_with_stats()

        # Perform matching
        all_matches = _match_kctaa_names_to_volunteers(
            csv_records, volunteers, min_score=min_score
        )

        # Filter out unmatched if requested
        if not include_unmatched:
            all_matches = [m for m in all_matches if m["match_type"] != "none"]

        # Sort results: exact matches first, then by match score descending, then by name
        all_matches.sort(
            key=lambda x: (
                x["match_type"]
                == "exact",  # Exact matches first (True sorts before False)
                -x["match_score"],  # Higher scores first
                x["csv_full_name"].lower(),  # Then alphabetical
            )
        )

        return render_template(
            "reports/kctaa_special.html",
            matches=all_matches,
            min_score=min_score,
            include_unmatched=include_unmatched,
            total_csv_records=len(csv_records),
            total_matches=len([m for m in all_matches if m["match_type"] != "none"]),
        )

    @bp.route("/reports/kctaa.csv")
    @login_required
    def kctaa_report_csv():
        """
        Export KCTAA volunteer match report as CSV.

        Query Parameters:
            min_score: Minimum match score (0.0-1.0) for filtering (default: 0.9)
            include_unmatched: Include unmatched CSV names (0 or 1, default: 0)

        Returns:
            CSV file download
        """
        # Parse query parameters (same as HTML view)
        min_score = request.args.get("min_score", DEFAULT_MIN_SCORE, type=float)
        include_unmatched = request.args.get("include_unmatched", "0") == "1"

        # Read CSV names
        csv_records = _read_kctaa_csv()
        if not csv_records:
            # Return empty CSV if no data
            output = io.StringIO()
            output.write("Error,Could not load KCTAA name list\n")
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode("utf-8")),
                mimetype="text/csv",
                download_name="KCTAA_Volunteer_Matches_Error.csv",
                as_attachment=True,
            )

        # Load volunteers with stats
        volunteers = _load_volunteers_with_stats()

        # Perform matching
        all_matches = _match_kctaa_names_to_volunteers(
            csv_records, volunteers, min_score=min_score
        )

        # Filter out unmatched if requested
        if not include_unmatched:
            all_matches = [m for m in all_matches if m["match_type"] != "none"]

        # Build DataFrame
        rows = []
        for match in all_matches:
            last_event_str = (
                match["last_event_date"].strftime("%m/%d/%Y")
                if match["last_event_date"]
                else ""
            )
            rows.append(
                {
                    "CSV First Name": match["csv_first_name"],
                    "CSV Last Name": match["csv_last_name"],
                    "CSV Full Name": match["csv_full_name"],
                    "Matched Volunteer Name": match["volunteer_name"] or "",
                    "Volunteer Email": match["volunteer_email"] or "",
                    "Volunteer Organization": match["volunteer_organization"] or "",
                    "Event Count": match["event_count"],
                    "Total Hours": round(match["total_hours"], 1),
                    "Last Event Date": last_event_str,
                    "Match Type": match["match_type"].title(),
                    "Match Score": round(match["match_score"], 3),
                    "Is Exact Match": "Yes" if match["is_exact_match"] else "No",
                    "Match Count": match["match_count"],
                }
            )

        # Create DataFrame and export
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)

        from datetime import datetime

        filename = f"KCTAA_Volunteer_Matches_{datetime.now().strftime('%Y%m%d')}.csv"

        return send_file(
            output,
            mimetype="text/csv",
            download_name=filename,
            as_attachment=True,
        )

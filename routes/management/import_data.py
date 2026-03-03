"""
Import/data management route handlers.

Contains file import, Salesforce district import, school management,
and school level update routes.
"""

import os

import pandas as pd
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import func

from config import Config
from models import db
from models.district_model import District
from models.school_model import School
from routes.decorators import admin_required, global_users_only
from routes.utils import log_audit_action


def register_import_data_routes(bp):
    """Register import/data management routes on the management blueprint."""

    @bp.route("/admin/import", methods=["POST"])
    @login_required
    @admin_required
    def import_data():
        """
        Handle data import functionality.

        Processes file uploads for data import operations. Currently
        a placeholder for future import functionality.

        Permission Requirements:
            - Admin access required

        Form Parameters:
            import_file: File to import

        Returns:
            Redirect to admin panel with success/error message

        Raises:
            403: Unauthorized access attempt
        """

        if "import_file" not in request.files:
            flash("No file provided", "error")
            return redirect(url_for("management.admin"))

        file = request.files["import_file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("management.admin"))

        # TODO: Process the file and import data
        # This will be implemented after creating the model

        flash("Import started successfully", "success")
        return redirect(url_for("management.admin"))

    @bp.route("/management/import-districts", methods=["POST"])
    @login_required
    @admin_required
    def import_districts():

        try:
            # Define Salesforce query
            salesforce_query = """
            SELECT Id, Name, School_Code_External_ID__c
            FROM Account
            WHERE Type = 'School District'
            """

            # Connect to Salesforce
            sf = Salesforce(
                username=Config.SF_USERNAME,
                password=Config.SF_PASSWORD,
                security_token=Config.SF_SECURITY_TOKEN,
                domain="login",
            )

            # Execute the query
            result = sf.query_all(salesforce_query)
            sf_rows = result.get("records", [])

            success_count = 0
            error_count = 0
            errors = []

            # Process each row from Salesforce
            for row in sf_rows:
                try:
                    # Check if district exists
                    existing_district = District.query.filter_by(
                        salesforce_id=row["Id"]
                    ).first()

                    if existing_district:
                        # Update existing district
                        existing_district.name = row["Name"]
                        existing_district.district_code = row[
                            "School_Code_External_ID__c"
                        ]
                    else:
                        # Create new district
                        new_district = District(
                            salesforce_id=row["Id"],
                            name=row["Name"],
                            district_code=row["School_Code_External_ID__c"],
                        )
                        db.session.add(new_district)

                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(
                        f"Error processing district {row.get('Name')}: {str(e)}"
                    )

            # Commit changes
            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {success_count} districts with {error_count} errors",
                    "processed_count": success_count,
                    "error_count": error_count,
                    "errors": errors,
                }
            )

        except SalesforceAuthenticationFailed:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Failed to authenticate with Salesforce",
                    }
                ),
                401,
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @bp.route("/schools")
    @login_required
    @global_users_only
    @admin_required
    def schools():

        # Filters and pagination
        district_q = request.args.get("district_q", "").strip()
        school_q = request.args.get("school_q", "").strip()
        level_q = request.args.get("level", "").strip()
        d_page = request.args.get("d_page", type=int, default=1)
        d_per_page = request.args.get("d_per_page", type=int, default=25)
        s_page = request.args.get("s_page", type=int, default=1)
        s_per_page = request.args.get("s_per_page", type=int, default=25)

        # Districts query
        dq = District.query
        if district_q:
            like = f"%{district_q.lower()}%"
            # Support name and district_code if present
            code_col = getattr(District, "district_code", None)
            if code_col is not None:
                dq = dq.filter(
                    func.lower(District.name).like(like)
                    | func.lower(code_col).like(like)
                )
            else:
                dq = dq.filter(func.lower(District.name).like(like))
        districts_pagination = dq.order_by(District.name).paginate(
            page=d_page, per_page=d_per_page, error_out=False
        )
        districts = districts_pagination.items

        # Schools query
        sq = School.query
        if school_q:
            sq = sq.filter(func.lower(School.name).like(f"%{school_q.lower()}%"))
        if district_q:
            sq = sq.join(District, isouter=True).filter(
                func.lower(District.name).like(f"%{district_q.lower()}%")
            )
        if level_q:
            sq = sq.filter(func.lower(School.level) == level_q.lower())
        schools_pagination = sq.order_by(School.name).paginate(
            page=s_page, per_page=s_per_page, error_out=False
        )
        schools_list = schools_pagination.items
        sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
        sheet_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else None
        )

        return render_template(
            "management/schools.html",
            districts=districts,
            schools=schools_list,
            d_pagination=districts_pagination,
            s_pagination=schools_pagination,
            filters={
                "district_q": district_q,
                "school_q": school_q,
                "level": level_q,
                "d_page": d_page,
                "d_per_page": d_per_page,
                "s_page": s_page,
                "s_per_page": s_per_page,
            },
            sheet_url=sheet_url,
        )

    @bp.route("/management/schools/<school_id>", methods=["DELETE"])
    @login_required
    @admin_required
    def delete_school(school_id):

        try:
            school = School.query.get_or_404(school_id)
            db.session.delete(school)
            db.session.commit()
            log_audit_action(
                action="delete", resource_type="school", resource_id=school_id
            )
            return jsonify({"success": True, "message": "School deleted successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/management/districts/<district_id>", methods=["DELETE"])
    @login_required
    @admin_required
    def delete_district(district_id):

        try:
            district = District.query.get_or_404(district_id)
            db.session.delete(district)  # This will cascade delete associated schools
            db.session.commit()
            log_audit_action(
                action="delete", resource_type="district", resource_id=district_id
            )
            return jsonify(
                {
                    "success": True,
                    "message": "District and associated schools deleted successfully",
                }
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/management/update-school-levels", methods=["POST"])
    @login_required
    @admin_required
    def update_school_levels_route():
        return update_school_levels()


def update_school_levels():
    """
    Update school level fields from Google Sheets CSV.

    Exposed as a module-level function so it can be called directly
    by external code (e.g. school_import.py) in addition to the route handler.
    """
    try:
        sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
        if not sheet_id:
            raise ValueError("School mapping Google Sheet ID not configured")

        # Try primary URL format
        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        )

        try:
            df = pd.read_csv(csv_url)
        except Exception as e:
            current_app.logger.error(f"Failed to read CSV: {str(e)}")
            # Try alternative URL format
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            df = pd.read_csv(csv_url)

        success_count = 0
        error_count = 0
        errors = []

        # Process each row
        for _, row in df.iterrows():
            try:
                # Skip rows without an ID or Level
                if pd.isna(row["Id"]) or pd.isna(row["Level"]):
                    continue

                # Find the school by Salesforce ID
                school = School.query.get(row["Id"])
                if school:
                    school.level = row["Level"].strip()
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"School not found with ID: {row['Id']}")

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing school {row.get('Id')}: {str(e)}")

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully updated {success_count} schools with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("School level update failed", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400

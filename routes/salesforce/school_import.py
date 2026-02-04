"""
Salesforce School and Class Import Routes
==========================================

This module handles the Salesforce data import functionality for schools,
districts, and classes. Extracted from routes/management/management.py
to consolidate all Salesforce import routes.

Routes:
- /management/import-schools: Import schools and districts
- /management/import-districts: Import districts only
- /management/import-classes: Import class records
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from config import Config
from models import db
from models.class_model import Class
from models.district_model import District
from models.school_model import School
from models.sync_log import SyncLog, SyncStatus

# Create Blueprint for Salesforce school import routes
school_import_bp = Blueprint("school_import", __name__)


@school_import_bp.route("/management/import-schools", methods=["POST"])
@login_required
def import_schools():
    """
    Import school and district data from Salesforce.

    This endpoint imports both districts and schools from Salesforce,
    with district import happening first to establish parent relationships.
    Supports delta sync for incremental imports.

    Returns:
        JSON response with import results and statistics
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        started_at = datetime.now(timezone.utc)

        # Delta sync support
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("schools_and_districts")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching schools/districts modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Starting school import process (FULL SYNC)...")

        # First, import districts
        district_query = """
        SELECT Id, Name, School_Code_External_ID__c, LastModifiedDate
        FROM Account
        WHERE Type = 'School District'
        """

        if is_delta and watermark:
            district_query += delta_helper.build_date_filter(watermark)

        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        district_result = sf.query_all(district_query)
        district_rows = district_result.get("records", [])

        district_success = 0
        district_errors = []

        for row in district_rows:
            try:
                existing_district = District.query.filter_by(
                    salesforce_id=row["Id"]
                ).first()

                if existing_district:
                    existing_district.name = row["Name"]
                    existing_district.district_code = row["School_Code_External_ID__c"]
                else:
                    new_district = District(
                        salesforce_id=row["Id"],
                        name=row["Name"],
                        district_code=row["School_Code_External_ID__c"],
                    )
                    db.session.add(new_district)

                district_success += 1
            except Exception as e:
                district_errors.append(
                    f"Error processing district {row.get('Name')}: {str(e)}"
                )

        db.session.commit()

        print(
            f"District import complete: {district_success} successes, {len(district_errors)} errors"
        )

        # Now proceed with school import
        school_query = """
        SELECT Id, Name, ParentId, Connector_Account_Name__c, School_Code_External_ID__c, LastModifiedDate
        FROM Account
        WHERE Type = 'School'
        """

        if is_delta and watermark:
            school_query += delta_helper.build_date_filter(watermark)

        school_result = sf.query_all(school_query)
        school_rows = school_result.get("records", [])

        school_success = 0
        school_errors = []

        for row in school_rows:
            try:
                existing_school = School.query.filter_by(id=row["Id"]).first()
                district = District.query.filter_by(
                    salesforce_id=row["ParentId"]
                ).first()

                if existing_school:
                    existing_school.name = row["Name"]
                    existing_school.district_id = district.id if district else None
                    existing_school.salesforce_district_id = row["ParentId"]
                    existing_school.normalized_name = row["Connector_Account_Name__c"]
                    existing_school.school_code = row["School_Code_External_ID__c"]
                else:
                    new_school = School(
                        id=row["Id"],
                        name=row["Name"],
                        district_id=district.id if district else None,
                        salesforce_district_id=row["ParentId"],
                        normalized_name=row["Connector_Account_Name__c"],
                        school_code=row["School_Code_External_ID__c"],
                    )
                    db.session.add(new_school)

                school_success += 1
            except Exception as e:
                school_errors.append(
                    f"Error processing school {row.get('Name')}: {str(e)}"
                )

        db.session.commit()

        print(
            f"School import complete: {school_success} successes, {len(school_errors)} errors"
        )

        # Update school levels
        from routes.management.management import update_school_levels

        level_update_response = update_school_levels()

        # Record sync log
        try:
            total_success = district_success + school_success
            total_errors = len(district_errors) + len(school_errors)
            sync_status = SyncStatus.SUCCESS.value
            if total_errors > 0:
                sync_status = (
                    SyncStatus.PARTIAL.value
                    if total_success > 0
                    else SyncStatus.FAILED.value
                )

            sync_log = SyncLog(
                sync_type="schools",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=sync_status,
                records_processed=total_success,
                records_failed=total_errors,
                is_delta_sync=is_delta,
                last_sync_watermark=(
                    datetime.now(timezone.utc)
                    if sync_status
                    in (SyncStatus.SUCCESS.value, SyncStatus.PARTIAL.value)
                    else None
                ),
            )
            db.session.add(sync_log)
            db.session.commit()
        except Exception as log_e:
            print(f"Warning: Failed to record sync log: {log_e}")

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {district_success} districts and {school_success} schools",
                "processed_count": district_success + school_success,
                "error_count": len(district_errors) + len(school_errors),
                "is_delta_sync": is_delta,
                "district_errors": district_errors,
                "school_errors": school_errors,
                "level_update": (
                    level_update_response.json
                    if hasattr(level_update_response, "json")
                    else None
                ),
            }
        )

    except SalesforceAuthenticationFailed:
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@school_import_bp.route("/management/import-districts", methods=["POST"])
@login_required
def import_districts():
    """
    Import district data only from Salesforce.

    This endpoint imports districts from Salesforce with full sync only.

    Returns:
        JSON response with import results and statistics
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        salesforce_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account
        WHERE Type = 'School District'
        """

        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        result = sf.query_all(salesforce_query)
        sf_rows = result.get("records", [])

        success_count = 0
        error_count = 0
        errors = []

        for row in sf_rows:
            try:
                existing_district = District.query.filter_by(
                    salesforce_id=row["Id"]
                ).first()

                if existing_district:
                    existing_district.name = row["Name"]
                    existing_district.district_code = row["School_Code_External_ID__c"]
                else:
                    new_district = District(
                        salesforce_id=row["Id"],
                        name=row["Name"],
                        district_code=row["School_Code_External_ID__c"],
                    )
                    db.session.add(new_district)

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing district {row.get('Name')}: {str(e)}")

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
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@school_import_bp.route("/management/import-classes", methods=["POST"])
@login_required
def import_classes():
    """
    Import class data from Salesforce.

    Fetches class information from Salesforce and synchronizes it
    with the local database. Handles both creation of new classes
    and updates to existing ones.

    Returns:
        JSON response with import results and statistics
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        started_at = datetime.now(timezone.utc)

        # Delta sync support
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("classes")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching classes modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Starting class import process (FULL SYNC)...")

        salesforce_query = """
        SELECT Id, Name, School__c, Class_Year_Number__c, LastModifiedDate
        FROM Class__c
        WHERE Id != null
        """

        # Add delta filter if using incremental sync
        if is_delta and watermark:
            salesforce_query += delta_helper.build_date_filter(watermark)

        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        result = sf.query_all(salesforce_query)
        sf_rows = result.get("records", [])

        success_count = 0
        error_count = 0
        errors = []

        for row in sf_rows:
            try:
                existing_class = Class.query.filter_by(salesforce_id=row["Id"]).first()

                if existing_class:
                    existing_class.name = row["Name"]
                    existing_class.school_salesforce_id = row["School__c"]
                    existing_class.class_year = int(row["Class_Year_Number__c"])
                else:
                    new_class = Class(
                        salesforce_id=row["Id"],
                        name=row["Name"],
                        school_salesforce_id=row["School__c"],
                        class_year=int(row["Class_Year_Number__c"]),
                    )
                    db.session.add(new_class)

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing class {row.get('Name')}: {str(e)}")

        db.session.commit()

        print(f"Class import complete: {success_count} successes, {error_count} errors")

        # Record sync log for dashboard tracking
        try:
            sync_status = SyncStatus.SUCCESS.value
            if error_count > 0:
                sync_status = (
                    SyncStatus.PARTIAL.value
                    if success_count > 0
                    else SyncStatus.FAILED.value
                )

            sync_log = SyncLog(
                sync_type="classes",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=sync_status,
                records_processed=success_count,
                records_failed=error_count,
                is_delta_sync=is_delta,
                last_sync_watermark=(
                    datetime.now(timezone.utc)
                    if sync_status
                    in (SyncStatus.SUCCESS.value, SyncStatus.PARTIAL.value)
                    else None
                ),
            )
            db.session.add(sync_log)
            db.session.commit()
        except Exception as log_e:
            print(f"Warning: Failed to record sync log: {log_e}")

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} classes with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "is_delta_sync": is_delta,
                "errors": errors,
            }
        )

    except SalesforceAuthenticationFailed:
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

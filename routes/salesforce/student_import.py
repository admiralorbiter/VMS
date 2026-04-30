"""
Salesforce Student Import Routes
================================

This module handles the Salesforce data import functionality for students.
Extracted from routes/students/routes.py to consolidate all Salesforce
import routes in one location.

Routes:
- /students/import-from-salesforce: Import student data from Salesforce (chunked)
"""

from datetime import datetime
from datetime import timezone as tz

from flask import Blueprint, jsonify, request
from flask_login import login_required

from models import db
from models.contact import Contact, ContactTypeEnum, Email, GenderEnum, Phone
from models.student import Student
from routes.decorators import global_users_only
from services.salesforce import get_salesforce_client, safe_query
from services.salesforce.errors import classify_exception, create_import_error
from utils.rate_limiter import limiter

# Create Blueprint for Salesforce student import routes
sf_student_import_bp = Blueprint("sf_student_import", __name__)


def _parse_date_simple(val):
    """Parse a date string without pandas — much faster for bulk import."""
    if not val:
        return None
    try:
        # Handles ISO 8601 like 2005-03-14 or 2005-03-14T00:00:00.000+0000
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@sf_student_import_bp.route("/students/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
@limiter.exempt  # Exempt from rate limiting - admin-only bulk import needs rapid pagination
def import_students_from_salesforce():
    """
    Import student data from Salesforce with chunked processing.

    This function handles large datasets by processing them in chunks
    to avoid memory issues and stay within Salesforce API limits.

    Args:
        chunk_size: Number of records to process per chunk (default: 2000)
        last_id: ID of last processed record for pagination

    Returns:
        JSON response with chunk processing results
    """
    try:
        started_at = datetime.now(tz.utc)

        # Delta sync support - check if incremental sync requested
        from services.salesforce import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("students")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        # Safely get JSON body (silent=True prevents 400 error on empty body)
        json_body = request.get_json(silent=True) or {}
        chunk_size = json_body.get(
            "chunk_size", 2000
        )  # Reduced to 2000 to stay within limits
        last_id = json_body.get(
            "last_id", None
        )  # Use ID-based pagination instead of offset

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching students modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print(
                f"Starting student import from Salesforce (chunk_size: {chunk_size}, last_id: {last_id})..."
            )

        # Connect to Salesforce using centralized client with retry
        sf = get_salesforce_client()

        # First, get total count for progress tracking
        count_query = """
        SELECT COUNT(Id) total
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        """
        # Apply delta filter to count query as well
        if is_delta and watermark:
            count_query += delta_helper.build_date_filter(watermark)

        result = safe_query(sf, count_query)
        if not result or "records" not in result or not result["records"]:
            return {
                "status": "error",
                "message": "Failed to get total record count from Salesforce",
                "errors": ["No records returned from Salesforce count query"],
            }
        total_records = result["records"][0]["total"]

        # Query for students using ID-based pagination with LastModifiedDate
        base_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email, Phone,
               Local_Student_ID__c, Birthdate, Gender__c, Racial_Ethnic_Background__c,
               npsp__Primary_Affiliation__c, Class__c, Legacy_Grade__c, Current_Grade__c,
               LastModifiedDate
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        {where_clause}
        {delta_clause}
        ORDER BY Id
        LIMIT {limit}
        """

        # Add WHERE clause for ID-based pagination
        where_clause = f"AND Id > '{last_id}'" if last_id else ""
        # Add delta filter
        delta_clause = (
            delta_helper.build_date_filter(watermark) if is_delta and watermark else ""
        )
        query = base_query.format(
            where_clause=where_clause, delta_clause=delta_clause, limit=chunk_size
        )

        print(
            f"Fetching students from Salesforce (chunk_size: {chunk_size}, last_id: {last_id}, delta: {is_delta})..."
        )
        result = safe_query(sf, query)
        student_rows = result.get("records", [])

        if not student_rows:
            print("No students returned for this chunk — import complete.")
            return {
                "success": True,
                "status": "success",
                "message": "No students to import in this chunk",
                "total_records": total_records,
                "processed_count": 0,
                "error_count": 0,
                "skipped_count": 0,
                "next_id": None,
                "is_complete": True,
                "is_delta_sync": is_delta,
                "errors": [],
                "processed_ids": [],
            }

        # --- O(1) Cache Pre-load ---
        # Build lookup sets/maps for this chunk to avoid per-row DB queries
        chunk_sf_ids = [row["Id"] for row in student_rows]

        # Map: salesforce_individual_id -> contact.id for existing students
        # Query Contact directly (no join needed — polymorphic type='student' is sufficient)
        existing_students = {
            sf_id: contact_id
            for sf_id, contact_id in db.session.query(
                Contact.salesforce_individual_id,
                Contact.id,
            )
            .filter(
                Contact.salesforce_individual_id.in_(chunk_sf_ids),
                Contact.type == "student",
            )
            .all()
        }

        # For existing students, pre-load their email/phone contact_ids
        existing_contact_ids = list(existing_students.values())
        # Map: contact_id -> Email object
        existing_emails = (
            {
                e.contact_id: e
                for e in Email.query.filter(
                    Email.contact_id.in_(existing_contact_ids),
                    Email.type == ContactTypeEnum.personal,
                ).all()
            }
            if existing_contact_ids
            else {}
        )
        # Map: contact_id -> Phone object
        existing_phones = (
            {
                p.contact_id: p
                for p in Phone.query.filter(
                    Phone.contact_id.in_(existing_contact_ids),
                    Phone.type == ContactTypeEnum.personal,
                ).all()
            }
            if existing_contact_ids
            else {}
        )

        print(
            f"  -> Chunk cache: {len(existing_students)} existing / "
            f"{len(student_rows) - len(existing_students)} new students"
        )
        # --- End cache pre-load ---

        success_count = 0
        error_count = 0
        errors = []
        processed_ids = []
        skipped_count = 0

        for i, row in enumerate(student_rows):
            sf_id = row.get("Id")
            first_name = (row.get("FirstName") or "").strip()
            last_name = (row.get("LastName") or "").strip()

            if not sf_id or not first_name or not last_name:
                skipped_count += 1
                error_count += 1
                errors.append(
                    create_import_error(
                        code="MISSING_REQUIRED_FIELDS",
                        row=row,
                        message=f"Missing required fields: {first_name} {last_name}",
                    ).to_dict()
                )
                continue

            try:
                is_new = sf_id not in existing_students

                if is_new:
                    student = Student()
                    student.salesforce_individual_id = sf_id
                    student.salesforce_account_id = row.get("AccountId")
                    db.session.add(student)
                else:
                    # Load the existing student object
                    contact_id = existing_students[sf_id]
                    student = db.session.get(Student, contact_id)
                    if not student:
                        # Fallback — shouldn't happen but be safe
                        student = Student()
                        student.salesforce_individual_id = sf_id
                        student.salesforce_account_id = row.get("AccountId")
                        db.session.add(student)
                        is_new = True

                # Update fields
                student.first_name = first_name
                student.last_name = last_name
                student.middle_name = (row.get("MiddleName") or "").strip() or None
                student.birthdate = _parse_date_simple(row.get("Birthdate"))
                student.student_id = (
                    row.get("Local_Student_ID__c") or ""
                ).strip() or None
                student.school_id = (
                    row.get("npsp__Primary_Affiliation__c") or ""
                ).strip() or None
                student.class_salesforce_id = (
                    row.get("Class__c") or ""
                ).strip() or None
                student.legacy_grade = (
                    row.get("Legacy_Grade__c") or ""
                ).strip() or None

                grade_raw = row.get("Current_Grade__c")
                if grade_raw is not None and str(grade_raw).strip() not in (
                    "",
                    "nan",
                    "None",
                ):
                    try:
                        student.current_grade = int(float(grade_raw))
                    except (ValueError, TypeError):
                        student.current_grade = None
                else:
                    student.current_grade = None

                # Gender
                gender_value = row.get("Gender__c")
                if gender_value:
                    if gender_value.upper() == "NA":
                        student.gender = GenderEnum.prefer_not_to_say
                    else:
                        gender_key = gender_value.lower().replace(" ", "_")
                        try:
                            student.gender = GenderEnum[gender_key]
                        except KeyError:
                            pass

                # Race/ethnicity
                racial_ethnic = row.get("Racial_Ethnic_Background__c")
                if racial_ethnic:
                    student.racial_ethnic = racial_ethnic.strip() or None

                # Flush to get ID for new records before contact info
                if is_new:
                    db.session.flush()
                    # Add to cache for future chunks (rare, but safe)
                    existing_students[sf_id] = student.id

                # --- Contact info via cache (no per-row queries) ---
                contact_id = student.id

                email_address = row.get("Email")
                if email_address and isinstance(email_address, str):
                    email_address = email_address.strip()
                    if email_address:
                        if contact_id in existing_emails:
                            existing_emails[contact_id].email = email_address
                        else:
                            email_record = Email(
                                contact_id=contact_id,
                                email=email_address,
                                type=ContactTypeEnum.personal,
                                primary=True,
                            )
                            db.session.add(email_record)
                            existing_emails[contact_id] = email_record

                phone_number = row.get("Phone")
                if phone_number and isinstance(phone_number, str):
                    phone_number = phone_number.strip()
                    if phone_number:
                        if contact_id in existing_phones:
                            existing_phones[contact_id].number = phone_number
                        else:
                            phone_record = Phone(
                                contact_id=contact_id,
                                number=phone_number,
                                type=ContactTypeEnum.personal,
                                primary=True,
                            )
                            db.session.add(phone_record)
                            existing_phones[contact_id] = phone_record

                success_count += 1
                processed_ids.append(sf_id)

            except Exception as e:
                db.session.rollback()
                error_count += 1
                skipped_count += 1
                import_error = create_import_error(
                    code=classify_exception(e),
                    row=row,
                    message=str(e),
                )
                errors.append(import_error.to_dict())
                continue

            # Batch commit every 100 records for resumability and performance
            if (i + 1) % 100 == 0:
                try:
                    db.session.commit()
                    print(
                        f"  -> Committed students batch {(i+1) // 100} ({success_count} successful, {skipped_count} skipped)"
                    )
                except Exception as batch_e:
                    db.session.rollback()
                    print(f"  -> Batch commit failed: {batch_e}")

        # Final commit for remaining records
        db.session.commit()

        # Get the last processed ID for the next chunk
        next_id = processed_ids[-1] if processed_ids else None
        is_complete = (
            len(student_rows) < chunk_size
        )  # If we got fewer records than chunk_size, we're done

        print(
            f"\nChunk complete - Created/Updated: {success_count}, Errors: {error_count}"
        )
        if errors:
            print("\nErrors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"- {error}")

        # Record sync log for delta sync tracking (only on final chunk)
        # This ensures watermark isn't set until all chunks are processed
        if is_complete:
            try:
                from models.sync_log import SyncStatus
                from services.salesforce.delta_sync import (
                    create_sync_log_with_watermark,
                )

                sync_status = SyncStatus.SUCCESS.value
                if error_count > 0:
                    sync_status = (
                        SyncStatus.PARTIAL.value
                        if success_count > 0
                        else SyncStatus.FAILED.value
                    )

                sync_log = create_sync_log_with_watermark(
                    sync_type="students",
                    started_at=started_at,
                    status=sync_status,
                    records_processed=success_count,
                    records_failed=error_count,
                    is_delta=is_delta,
                )
                db.session.add(sync_log)
                db.session.commit()
            except Exception as log_e:
                print(f"Warning: Failed to record sync log: {log_e}")

        return {
            "success": True,  # For frontend compatibility
            "status": "success",
            "message": f"Processed chunk of {len(student_rows)} students ({success_count} successful, {skipped_count} skipped, {error_count} errors)",
            "total_records": total_records,
            "processed_count": len(processed_ids),
            "error_count": error_count,
            "skipped_count": skipped_count,
            "next_id": next_id if not is_complete else None,
            "is_complete": is_complete,
            "is_delta_sync": is_delta,
            "errors": errors[:100],  # Limit error list size in response
            "processed_ids": processed_ids,
        }

    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        print(f"Error: {error_msg}")
        return {"status": "error", "message": error_msg, "errors": [str(e)]}

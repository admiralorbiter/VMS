"""
Salesforce Volunteer Import Routes

This module handles the Salesforce data import functionality for volunteers.
Extracted from routes.py to improve maintainability and allow focused
development on import logic.

Routes:
- /volunteers/import-from-salesforce: Import volunteer data from Salesforce
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

from config import Config
from models import db
from models.contact import (
    Address,
    ContactTypeEnum,
    EducationEnum,
    Email,
    GenderEnum,
    Phone,
    RaceEthnicityEnum,
)
from models.volunteer import ConnectorData, ConnectorSubscriptionEnum, Skill, Volunteer
from routes.decorators import global_users_only
from routes.utils import parse_date, parse_skills
from services.salesforce_mappers import (
    map_age_group,
    map_education_level,
    map_race_ethnicity,
)

# Create Blueprint for Salesforce import routes
salesforce_import_bp = Blueprint("salesforce_import", __name__)


@salesforce_import_bp.route("/volunteers/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
def import_from_salesforce():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        from datetime import timezone as tz

        started_at = datetime.now(tz.utc)

        # Delta sync support - check if incremental sync requested
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("volunteers")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching volunteers modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Starting volunteer import from Salesforce (FULL SYNC)...")

        # Define Salesforce query with LastModifiedDate for delta sync
        salesforce_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email,
               npe01__AlternateEmail__c, npe01__HomeEmail__c,
               npe01__WorkEmail__c, npe01__Preferred_Email__c,
               HomePhone, MobilePhone, npe01__WorkPhone__c, Phone,
               npe01__PreferredPhone__c,
               npsp__Primary_Affiliation__c, Title, Department, Gender__c,
               Birthdate, Last_Mailchimp_Email_Date__c, Last_Volunteer_Date__c,
               Last_Email_Message__c, Volunteer_Recruitment_Notes__c,
               Volunteer_Skills__c, Volunteer_Skills_Text__c,
               Volunteer_Interests__c,
               Number_of_Attended_Volunteer_Sessions__c,
               Racial_Ethnic_Background__c,
               Last_Activity_Date__c,
               First_Volunteer_Date__c,
               Last_Non_Internal_Email_Activity__c,
               Description, Highest_Level_of_Educational__c, Age_Group__c,
               DoNotCall, npsp__Do_Not_Contact__c, HasOptedOutOfEmail,
               EmailBouncedDate,
               MailingAddress, npe01__Home_Address__c, npe01__Work_Address__c,
               npe01__Other_Address__c, npe01__Primary_Address_Type__c,
               npe01__Secondary_Address_Type__c,
               Connector_Active_Subscription__c,
               Connector_Active_Subscription_Name__c,
               Connector_Affiliations__c,
               Connector_Industry__c,
               Connector_Joining_Date__c,
               Connector_Last_Login_Date_Time__c,
               Connector_Last_Update_Date__c,
               Connector_Profile_Link__c,
               Connector_Role__c,
               Connector_SignUp_Role__c,
               Connector_User_ID__c,
               LastModifiedDate
        FROM Contact
        WHERE (Contact_Type__c = 'Volunteer' OR Contact_Type__c = '')
        """

        # Add delta filter if using incremental sync
        if is_delta and watermark:
            salesforce_query += delta_helper.build_date_filter(watermark)

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
        total_records = len(sf_rows)

        print(
            f"Found {total_records} records to process{' (delta)' if is_delta else ''}"
        )

        success_count = 0
        error_count = 0
        created_count = 0
        updated_count = 0
        errors = []

        # Progress tracking
        progress_interval = max(1, total_records // 20)  # Show progress every 5%
        last_progress = 0

        # Process each row from Salesforce
        for i, row in enumerate(sf_rows):
            try:
                # Progress indicator
                if i >= last_progress + progress_interval:
                    progress = (i / total_records) * 100
                    print(
                        f"Progress: {progress:.1f}% ({i}/{total_records}) - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}"
                    )
                    last_progress = i

                # Check if volunteer exists
                volunteer = Volunteer.query.filter_by(
                    salesforce_individual_id=row["Id"]
                ).first()
                is_new = False
                updates = []

                if not volunteer:
                    volunteer = Volunteer()
                    volunteer.salesforce_individual_id = row["Id"]
                    db.session.add(volunteer)
                    is_new = True
                    updates.append("new")

                # Update volunteer fields only if they've changed
                if volunteer.salesforce_account_id != row["AccountId"]:
                    volunteer.salesforce_account_id = row["AccountId"]
                    updates.append("acc")

                new_first_name = (row.get("FirstName") or "").strip()
                if volunteer.first_name != new_first_name:
                    volunteer.first_name = new_first_name
                    updates.append("fn")

                new_last_name = (row.get("LastName") or "").strip()
                if volunteer.last_name != new_last_name:
                    volunteer.last_name = new_last_name
                    updates.append("ln")

                new_middle_name = (row.get("MiddleName") or "").strip()
                if volunteer.middle_name != new_middle_name:
                    volunteer.middle_name = new_middle_name
                    updates.append("mn")

                new_org_name = (row.get("npsp__Primary_Affiliation__c") or "").strip()
                if volunteer.organization_name != new_org_name:
                    volunteer.organization_name = new_org_name
                    updates.append("org")

                new_title = (row.get("Title") or "").strip()
                if volunteer.title != new_title:
                    volunteer.title = new_title
                    updates.append("title")

                new_department = (row.get("Department") or "").strip()
                if volunteer.department != new_department:
                    volunteer.department = new_department
                    updates.append("dept")

                # Handle gender enum
                gender_str = (
                    (row.get("Gender__c") or "").lower().replace(" ", "_").strip()
                )
                if gender_str and gender_str in [e.name for e in GenderEnum]:
                    if not volunteer.gender or volunteer.gender.name != gender_str:
                        volunteer.gender = GenderEnum[gender_str]
                        updates.append("gen")

                # Handle race/ethnicity using centralized mapper
                race_ethnicity_str = row.get("Racial_Ethnic_Background__c")
                enum_value = map_race_ethnicity(race_ethnicity_str)

                if enum_value:
                    if enum_value in [e.name for e in RaceEthnicityEnum]:
                        if (
                            not volunteer.race_ethnicity
                            or volunteer.race_ethnicity.name != enum_value
                        ):
                            volunteer.race_ethnicity = RaceEthnicityEnum[enum_value]
                            updates.append("race")
                    else:
                        print(
                            f"Warning: Unmapped race/ethnicity value '{race_ethnicity_str}' for volunteer {volunteer.id} ({volunteer.first_name} {volunteer.last_name})"
                        )
                elif volunteer.race_ethnicity != RaceEthnicityEnum.unknown:
                    volunteer.race_ethnicity = RaceEthnicityEnum.unknown
                    updates.append("race")

                # Handle dates
                new_birthdate = parse_date(row.get("Birthdate"))
                if volunteer.birthdate != new_birthdate:
                    volunteer.birthdate = new_birthdate
                    updates.append("bd")

                new_first_volunteer_date = parse_date(
                    row.get("First_Volunteer_Date__c")
                )
                if volunteer.first_volunteer_date != new_first_volunteer_date:
                    volunteer.first_volunteer_date = new_first_volunteer_date
                    updates.append("fvd")

                new_mailchimp_date = parse_date(row.get("Last_Mailchimp_Email_Date__c"))
                if volunteer.last_mailchimp_activity_date != new_mailchimp_date:
                    volunteer.last_mailchimp_activity_date = new_mailchimp_date
                    updates.append("mcd")

                new_volunteer_date = parse_date(row.get("Last_Volunteer_Date__c"))
                if volunteer.last_volunteer_date != new_volunteer_date:
                    volunteer.last_volunteer_date = new_volunteer_date
                    updates.append("lvd")

                new_activity_date = parse_date(row.get("Last_Activity_Date__c"))
                if volunteer.last_activity_date != new_activity_date:
                    volunteer.last_activity_date = new_activity_date
                    updates.append("lad")

                new_email_date = parse_date(row.get("Last_Email_Message__c"))
                if volunteer.last_email_date != new_email_date:
                    volunteer.last_email_date = new_email_date
                    updates.append("led")

                new_non_internal_email_date = parse_date(
                    row.get("Last_Non_Internal_Email_Activity__c")
                )
                if (
                    volunteer.last_non_internal_email_date
                    != new_non_internal_email_date
                ):
                    volunteer.last_non_internal_email_date = new_non_internal_email_date
                    updates.append("nied")

                new_notes = (row.get("Volunteer_Recruitment_Notes__c") or "").strip()
                if volunteer.notes != new_notes:
                    volunteer.notes = new_notes
                    updates.append("notes")

                # Handle description
                new_description = (row.get("Description") or "").strip()
                if volunteer.description != new_description:
                    volunteer.description = new_description
                    updates.append("desc")

                # Handle education level using centralized mapper
                education_str = (
                    row.get("Highest_Level_of_Educational__c") or ""
                ).strip()
                if education_str:
                    enum_value = map_education_level(education_str)
                    if enum_value and enum_value in [e.name for e in EducationEnum]:
                        if (
                            not volunteer.education
                            or volunteer.education.name != enum_value
                        ):
                            volunteer.education = EducationEnum[enum_value]
                            updates.append("edu")
                    elif volunteer.education != EducationEnum.UNKNOWN:
                        volunteer.education = EducationEnum.UNKNOWN
                        updates.append("edu")

                # Handle age group
                age_str = (row.get("Age_Group__c") or "").strip()
                if age_str:
                    new_age_group = map_age_group(age_str)
                    if volunteer.age_group != new_age_group:
                        volunteer.age_group = new_age_group
                        updates.append("age")

                # Handle interests
                interests_str = row.get("Volunteer_Interests__c")
                if (
                    interests_str is not None
                ):  # Only update if field exists in Salesforce data
                    interests_str = interests_str.strip()
                    if volunteer.interests != interests_str:
                        volunteer.interests = interests_str
                        updates.append("int")

                # Handle skills - only update if there are changes
                if row.get("Volunteer_Skills__c") or row.get(
                    "Volunteer_Skills_Text__c"
                ):
                    new_skills = parse_skills(
                        row.get("Volunteer_Skills_Text__c", ""),
                        row.get("Volunteer_Skills__c", ""),
                    )
                    current_skills = {skill.name for skill in volunteer.skills}
                    if set(new_skills) != current_skills:
                        # Clear existing skills
                        volunteer.skills = []
                        # Add new skills - use no_autoflush to prevent identity map warnings
                        with db.session.no_autoflush:
                            for skill_name in new_skills:
                                skill = Skill.query.filter_by(name=skill_name).first()
                                if not skill:
                                    skill = Skill(name=skill_name)
                                    db.session.add(skill)
                                if skill not in volunteer.skills:
                                    volunteer.skills.append(skill)
                        updates.append("skills")

                # Handle times_volunteered
                if row.get("Number_of_Attended_Volunteer_Sessions__c"):
                    try:
                        new_times = int(
                            float(row["Number_of_Attended_Volunteer_Sessions__c"])
                        )
                        if volunteer.times_volunteered != new_times:
                            volunteer.times_volunteered = new_times
                            updates.append("tv")
                    except (ValueError, TypeError):
                        if volunteer.times_volunteered != 0:
                            volunteer.times_volunteered = 0
                            updates.append("tv")

                # Handle contact preferences
                new_do_not_call = bool(row.get("DoNotCall"))
                if volunteer.do_not_call != new_do_not_call:
                    volunteer.do_not_call = new_do_not_call
                    updates.append("dnc")

                new_do_not_contact = bool(row.get("npsp__Do_Not_Contact__c"))
                if volunteer.do_not_contact != new_do_not_contact:
                    volunteer.do_not_contact = new_do_not_contact
                    updates.append("dnt")

                new_email_opt_out = bool(row.get("HasOptedOutOfEmail"))
                if volunteer.email_opt_out != new_email_opt_out:
                    volunteer.email_opt_out = new_email_opt_out
                    updates.append("eoo")

                # Handle email bounce date
                new_bounce_date = parse_date(row.get("EmailBouncedDate"))
                if volunteer.email_bounced_date != new_bounce_date:
                    volunteer.email_bounced_date = new_bounce_date
                    updates.append("ebd")

                # Handle emails
                email_fields = {
                    "npe01__WorkEmail__c": ContactTypeEnum.professional,
                    "Email": ContactTypeEnum.personal,
                    "npe01__HomeEmail__c": ContactTypeEnum.personal,
                    "npe01__AlternateEmail__c": ContactTypeEnum.personal,
                }

                # Get preferred email type
                preferred_email = (row.get("npe01__Preferred_Email__c") or "").lower()
                email_changes = False

                # Process each email field
                for email_field, email_type in email_fields.items():
                    email_value = row.get(email_field)
                    if not email_value:
                        continue

                    # Check if this should be the primary email based on preference
                    is_primary = False
                    if preferred_email:
                        if (
                            (
                                preferred_email == "work"
                                and email_field == "npe01__WorkEmail__c"
                            )
                            or (
                                preferred_email == "personal"
                                and email_field in ["npe01__HomeEmail__c", "Email"]
                            )
                            or (
                                preferred_email == "alternate"
                                and email_field == "npe01__AlternateEmail__c"
                            )
                        ):
                            is_primary = True
                    elif (
                        email_field == "Email"
                    ):  # Default to standard Email field as primary if no preference
                        is_primary = True

                    # Check if email already exists
                    email = Email.query.filter_by(
                        contact_id=volunteer.id, email=email_value
                    ).first()

                    if not email:
                        email = Email(
                            contact_id=volunteer.id,
                            email=email_value,
                            type=email_type,
                            primary=is_primary,
                        )
                        db.session.add(email)
                        email_changes = True
                    else:
                        # Update existing email type and primary status if changed
                        if email.type != email_type:
                            email.type = email_type
                            email_changes = True
                        if is_primary and not email.primary:
                            # Set all other emails to non-primary
                            Email.query.filter_by(
                                contact_id=volunteer.id, primary=True
                            ).update({"primary": False})
                            email.primary = True
                            email_changes = True

                if email_changes:
                    updates.append("emails")

                # Handle phone numbers
                phone_fields = {
                    "npe01__WorkPhone__c": ContactTypeEnum.professional,
                    "Phone": ContactTypeEnum.professional,  # Business Phone
                    "HomePhone": ContactTypeEnum.personal,
                    "MobilePhone": ContactTypeEnum.personal,
                }

                # Get preferred phone type
                preferred_phone = (row.get("npe01__PreferredPhone__c") or "").lower()
                phone_changes = False

                # Process each phone field
                for phone_field, phone_type in phone_fields.items():
                    phone_value = row.get(phone_field)
                    if not phone_value:
                        continue

                    # Check if this should be the primary phone based on preference
                    is_primary = False
                    if preferred_phone:
                        if (
                            (
                                preferred_phone == "work"
                                and phone_field in ["npe01__WorkPhone__c", "Phone"]
                            )
                            or (
                                preferred_phone == "home" and phone_field == "HomePhone"
                            )
                            or (
                                preferred_phone == "mobile"
                                and phone_field == "MobilePhone"
                            )
                        ):
                            is_primary = True
                    elif (
                        phone_field == "Phone"
                    ):  # Default to business Phone as primary if no preference
                        is_primary = True

                    # Check if phone already exists
                    phone = Phone.query.filter_by(
                        contact_id=volunteer.id, number=phone_value
                    ).first()

                    if not phone:
                        phone = Phone(
                            contact_id=volunteer.id,
                            number=phone_value,
                            type=phone_type,
                            primary=is_primary,
                        )
                        db.session.add(phone)
                        phone_changes = True
                    else:
                        # Update existing phone type and primary status if changed
                        if phone.type != phone_type:
                            phone.type = phone_type
                            phone_changes = True
                        if is_primary and not phone.primary:
                            # Set all other phones to non-primary
                            Phone.query.filter_by(
                                contact_id=volunteer.id, primary=True
                            ).update({"primary": False})
                            phone.primary = True
                            phone_changes = True

                if phone_changes:
                    updates.append("phones")

                # Handle addresses
                mailing_address = row.get("MailingAddress", {})
                if isinstance(mailing_address, dict):
                    # Find or create mailing address
                    mailing = next(
                        (
                            addr
                            for addr in volunteer.addresses
                            if addr.type == ContactTypeEnum.personal and addr.primary
                        ),
                        None,
                    )
                    if not mailing:
                        mailing = Address(
                            contact_id=volunteer.id,
                            type=ContactTypeEnum.personal,
                            primary=True,
                        )
                        volunteer.addresses.append(mailing)
                        updates.append("ma")

                    # Update mailing address fields
                    if mailing.address_line1 != mailing_address.get("street", ""):
                        mailing.address_line1 = mailing_address.get("street", "")
                        updates.append("ms")
                    if mailing.city != mailing_address.get("city", ""):
                        mailing.city = mailing_address.get("city", "")
                        updates.append("mc")
                    if mailing.state != mailing_address.get("state", ""):
                        mailing.state = mailing_address.get("state", "")
                        updates.append("mst")
                    if mailing.zip_code != mailing_address.get("postalCode", ""):
                        mailing.zip_code = mailing_address.get("postalCode", "")
                        updates.append("mz")
                    if mailing.country != mailing_address.get("country", ""):
                        mailing.country = mailing_address.get("country", "")
                        updates.append("mco")

                # Handle work address if present
                work_address = row.get("npe01__Work_Address__c", "")
                if work_address:
                    work = next(
                        (
                            addr
                            for addr in volunteer.addresses
                            if addr.type == ContactTypeEnum.professional
                        ),
                        None,
                    )
                    if not work:
                        work = Address(
                            contact_id=volunteer.id, type=ContactTypeEnum.professional
                        )
                        volunteer.addresses.append(work)
                        updates.append("wa")

                    # Parse work address string
                    try:
                        parts = work_address.split(",")
                        if len(parts) >= 1:
                            work.address_line1 = parts[0].strip()
                        if len(parts) >= 2:
                            work.city = parts[1].strip()
                        if len(parts) >= 3:
                            state_zip = parts[2].strip().split()
                            if len(state_zip) >= 1:
                                work.state = state_zip[0]
                            if len(state_zip) >= 2:
                                work.zip_code = state_zip[1]
                        updates.append("wu")
                    except Exception as e:
                        print(
                            f"Error parsing work address for {volunteer.first_name} {volunteer.last_name}: {str(e)}"
                        )

                # Set address types based on primary/secondary preferences
                primary_type = (row.get("npe01__Primary_Address_Type__c") or "").lower()
                secondary_type = (
                    row.get("npe01__Secondary_Address_Type__c") or ""
                ).lower()

                for addr in volunteer.addresses:
                    is_home = addr.type == ContactTypeEnum.personal
                    is_work = addr.type == ContactTypeEnum.professional

                    # Set primary based on preference
                    if (primary_type == "home" and is_home) or (
                        primary_type == "work" and is_work
                    ):
                        addr.primary = True
                    elif (secondary_type == "home" and is_home) or (
                        secondary_type == "work" and is_work
                    ):
                        addr.primary = False

                # Handle Connector data
                connector_data = {
                    "active_subscription": (
                        row.get("Connector_Active_Subscription__c") or ""
                    )
                    .strip()
                    .upper()
                    or "NONE",
                    "active_subscription_name": (
                        row.get("Connector_Active_Subscription_Name__c") or ""
                    ).strip(),
                    "affiliations": (
                        row.get("Connector_Affiliations__c") or ""
                    ).strip(),
                    "industry": (row.get("Connector_Industry__c") or "").strip(),
                    "joining_date": (
                        row.get("Connector_Joining_Date__c") or ""
                    ).strip(),
                    "last_login_datetime": (
                        row.get("Connector_Last_Login_Date_Time__c") or ""
                    ).strip(),
                    "last_update_date": parse_date(
                        row.get("Connector_Last_Update_Date__c")
                    ),
                    "profile_link": (
                        row.get("Connector_Profile_Link__c") or ""
                    ).strip(),
                    "role": (row.get("Connector_Role__c") or "").strip(),
                    "signup_role": (row.get("Connector_SignUp_Role__c") or "").strip(),
                    "user_auth_id": (row.get("Connector_User_ID__c") or "").strip(),
                }

                # Create or update connector data
                if not volunteer.connector:
                    volunteer.connector = ConnectorData(volunteer_id=volunteer.id)
                    updates.append("con")

                # Update connector fields if they exist in Salesforce data
                if connector_data["active_subscription"] in [
                    e.name for e in ConnectorSubscriptionEnum
                ]:
                    if (
                        volunteer.connector.active_subscription
                        != ConnectorSubscriptionEnum[
                            connector_data["active_subscription"]
                        ]
                    ):
                        volunteer.connector.active_subscription = (
                            ConnectorSubscriptionEnum[
                                connector_data["active_subscription"]
                            ]
                        )
                        updates.append("cs")

                for field, value in connector_data.items():
                    if (
                        field != "active_subscription" and value
                    ):  # Skip active_subscription as it's handled above
                        current_value = getattr(volunteer.connector, field)
                        if current_value != value:
                            setattr(volunteer.connector, field, value)
                            updates.append(f"c{field[:2]}")

                success_count += 1
                created_count = created_count + 1 if is_new else created_count
                updated_count = (
                    updated_count + 1 if not is_new and updates else updated_count
                )

                # Compact status output for each record
                if i < 10 or i % 100 == 0:  # Show first 10 and every 100th
                    status = (
                        "NEW"
                        if is_new
                        else f"UPD({','.join(updates)})" if updates else "OK"
                    )
                    print(
                        f"[{i+1:4d}] {status}: {volunteer.first_name} {volunteer.last_name}"
                    )

            except Exception as e:
                error_count += 1
                error_detail = {
                    "name": f"{row.get('FirstName', '')} {row.get('LastName', '')}",
                    "salesforce_id": row.get("Id", ""),
                    "error": str(e),
                }
                errors.append(error_detail)
                print(
                    f"[{i+1:4d}] ERROR: {error_detail['name']} (ID: {error_detail['salesforce_id']}) - {str(e)[:100]}"
                )
                db.session.rollback()

        # Final summary
        print(f"\n{'='*60}")
        print(f"IMPORT COMPLETE")
        print(f"{'='*60}")
        print(f"Total Records: {total_records}")
        print(f"Successful:    {success_count}")
        print(f"Created:       {created_count}")
        print(f"Updated:       {updated_count}")
        print(f"Errors:        {error_count}")
        print(f"{'='*60}")

        if errors:
            print(f"\nERROR SUMMARY (showing first 10):")
            for i, error in enumerate(errors[:10]):
                print(f"  {i+1:2d}. {error['name']} (ID: {error['salesforce_id']})")
                print(f"      {error['error'][:80]}...")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        # Commit all successful changes
        try:
            db.session.commit()

            # Record sync log for delta sync tracking
            try:
                from models.sync_log import SyncLog, SyncStatus

                sync_status = SyncStatus.SUCCESS.value
                if error_count > 0:
                    sync_status = (
                        SyncStatus.PARTIAL.value
                        if success_count > 0
                        else SyncStatus.FAILED.value
                    )

                sync_log = SyncLog(
                    sync_type="volunteers",
                    started_at=started_at,
                    completed_at=datetime.now(tz.utc),
                    status=sync_status,
                    records_processed=success_count,
                    records_failed=error_count,
                    is_delta_sync=is_delta,
                    last_sync_watermark=(
                        datetime.now(tz.utc)
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
                    "message": f"Successfully processed {success_count} volunteers (Created: {created_count}, Updated: {updated_count}) with {error_count} errors",
                    "processed_count": success_count,
                    "error_count": error_count,
                    "is_delta_sync": is_delta,
                }
            )
        except Exception as e:
            db.session.rollback()
            return (
                jsonify(
                    {"success": False, "message": f"Database commit error: {str(e)}"}
                ),
                500,
            )

    except SalesforceAuthenticationFailed:
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

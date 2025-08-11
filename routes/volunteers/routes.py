"""
Volunteer Management System - Routes

This module contains all the Flask routes for the volunteer management system.
It handles volunteer listing, creation, editing, viewing, and data import operations.

Key Features:
- Volunteer listing with filtering and pagination
- Individual volunteer view with detailed information
- Volunteer creation and editing forms
- Salesforce data import functionality
- Local status calculation and updates
- Volunteer deletion and purging operations

Routes:
- /volunteers: Main volunteer listing page
- /volunteers/add: Add new volunteer form
- /volunteers/view/<id>: View individual volunteer details
- /volunteers/edit/<id>: Edit volunteer information
- /volunteers/import-from-salesforce: Import volunteer data from Salesforce
- /volunteers/update-local-statuses: Bulk update local status calculations

Author: VMS Development Team
Last Updated: 2024
"""

from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import and_, or_, text

from config import Config
from forms import VolunteerForm
from models import db
from models.contact import Address, AgeGroupEnum, Contact, ContactTypeEnum, EducationEnum, Email, GenderEnum, LocalStatusEnum, Phone, RaceEthnicityEnum
from models.event import Event
from models.history import History
from models.organization import Organization, VolunteerOrganization
from models.volunteer import ConnectorData, ConnectorSubscriptionEnum, Engagement, EventParticipation, Skill, Volunteer, VolunteerSkill
from routes.utils import get_email_addresses, get_phone_numbers, parse_date, parse_skills
from utils.salesforce_importer import ImportConfig, SalesforceImporter

# Create Flask Blueprint for volunteer routes
volunteers_bp = Blueprint("volunteers", __name__)


# ============================================================================
# OPTIMIZED VOLUNTEER IMPORT FRAMEWORK
# ============================================================================


def validate_volunteer_record(record: dict) -> list:
    """
    Validate a volunteer record from Salesforce.

    Args:
        record: Dictionary containing volunteer data from Salesforce

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    if not record.get("Id"):
        errors.append("Missing Salesforce ID")
    elif len(record["Id"]) != 18:
        errors.append(f"Invalid Salesforce ID format: {record['Id']}")

    # Name validation
    if not record.get("FirstName") and not record.get("LastName"):
        errors.append("Missing both first and last name")

    # Email validation
    email = record.get("Email")
    if email and "@" not in email:
        errors.append(f"Invalid email format: {email}")

    # Phone validation (basic)
    phone = record.get("Phone")
    if phone and len(phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")) < 10:
        errors.append(f"Invalid phone format: {phone}")

    # Date validation
    birthdate = record.get("Birthdate")
    if birthdate:
        try:
            parsed_date = parse_date(birthdate)
            if parsed_date and parsed_date > datetime.now():
                errors.append("Birthdate cannot be in the future")
        except (ValueError, TypeError, AttributeError):
            errors.append("Invalid birthdate format")

    # Gender validation
    gender = record.get("Gender__c")
    if gender:
        gender_str = (gender or "").lower().replace(" ", "_").strip()
        if gender_str not in [e.name for e in GenderEnum]:
            errors.append(f"Invalid gender value: {gender}")

    # Education validation
    education = record.get("Highest_Level_of_Educational__c")
    if education:
        # Check if it's a valid education level (basic check)
        if len(education) > 100:  # Reasonable max length
            errors.append("Education field too long")

    return errors


def process_volunteer_record_optimized(record: dict, session) -> bool:
    """
    Process a single volunteer record using the optimized framework.

    Args:
        record: Dictionary containing volunteer data from Salesforce
        session: Database session

    Returns:
        True if processing was successful, False otherwise
    """
    try:
        # Debug: Log the record ID for tracking
        record_id = record.get("Id", "UNKNOWN")
        print(f"Processing volunteer record: {record_id}")

        # Create a completely fresh dictionary for each record to avoid reference issues
        # Extract all data from the record to ensure no shared references
        salesforce_id = (record.get("Id") or "").strip()
        salesforce_account_id = (record.get("AccountId") or "").strip()
        first_name = (record.get("FirstName") or "").strip()
        last_name = (record.get("LastName") or "").strip()
        middle_name = (record.get("MiddleName") or "").strip()
        organization_name = (record.get("npsp__Primary_Affiliation__c") or "").strip()
        title = (record.get("Title") or "").strip()
        department = (record.get("Department") or "").strip()
        industry = (record.get("Industry") or "").strip()
        birthdate = parse_date(record.get("Birthdate", ""))
        first_volunteer_date = parse_date(record.get("First_Volunteer_Date__c", ""))
        last_mailchimp_activity_date = parse_date(record.get("Last_Mailchimp_Email_Date__c", ""))
        last_volunteer_date = parse_date(record.get("Last_Volunteer_Date__c", ""))
        last_email_date = parse_date(record.get("Last_Email_Message__c", ""))
        last_non_internal_email_date = parse_date(record.get("Last_Non_Internal_Email_Activity__c", ""))
        notes = (record.get("Volunteer_Recruitment_Notes__c") or "").strip()

        # Create a fresh dictionary with the extracted data
        volunteer_data = {
            "salesforce_individual_id": salesforce_id,
            "salesforce_account_id": salesforce_account_id,
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "organization_name": organization_name,
            "title": title,
            "department": department,
            "industry": industry,
            "birthdate": birthdate,
            "first_volunteer_date": first_volunteer_date,
            "last_mailchimp_activity_date": last_mailchimp_activity_date,
            "last_volunteer_date": last_volunteer_date,
            "last_email_date": last_email_date,
            "last_non_internal_email_date": last_non_internal_email_date,
            "notes": notes,
        }

        # Debug: Log the actual salesforce_individual_id being used
        print(f"Record {record_id} using salesforce_individual_id: {volunteer_data['salesforce_individual_id']}")
        print(f"Record {record_id} first_name: {volunteer_data['first_name']}, last_name: {volunteer_data['last_name']}")

        # Handle gender enum with null safety
        gender_value = record.get("Gender__c") or ""
        gender_str = gender_value.lower().replace(" ", "_").strip()
        if gender_str in [e.name for e in GenderEnum]:
            volunteer_data["gender"] = GenderEnum[gender_str]

        # Handle times_volunteered
        if record.get("Number_of_Attended_Volunteer_Sessions__c"):
            try:
                volunteer_data["times_volunteered"] = int(float(record["Number_of_Attended_Volunteer_Sessions__c"]))
            except (ValueError, TypeError):
                volunteer_data["times_volunteered"] = 0

        # Use custom create_or_update_record for volunteers (handles salesforce_individual_id field)
        if not salesforce_id:
            print(f"Error: Missing Salesforce ID for volunteer record: {record_id}")
            return False

        # Try to find existing contact/volunteer safely without triggering autoflush
        try:
            with session.no_autoflush:
                existing_contact = session.query(Contact).filter_by(salesforce_individual_id=salesforce_id).first()

            if existing_contact:
                # Reuse existing contact; get/create the volunteer row bound to this contact id
                print(f"Found existing Contact for {record_id} (id={existing_contact.id}); ensuring Volunteer row exists")
                with session.no_autoflush:
                    existing_volunteer = session.query(Volunteer).filter_by(id=existing_contact.id).first()
                if existing_volunteer:
                    volunteer = existing_volunteer
                    # Update volunteer-specific fields
                    for key, value in volunteer_data.items():
                        if hasattr(Volunteer, key):
                            setattr(volunteer, key, value)
                    # Update base Contact fields on the existing contact
                    base_contact_keys = [
                        "salesforce_individual_id",
                        "salesforce_account_id",
                        "first_name",
                        "last_name",
                        "middle_name",
                        "notes",
                        "last_email_date",
                        "birthdate",
                        "gender",
                    ]
                    for key in base_contact_keys:
                        if key in volunteer_data and hasattr(existing_contact, key):
                            setattr(existing_contact, key, volunteer_data[key])
                else:
                    # Create a Volunteer row linked to existing Contact using raw insert to avoid parent insert
                    session.execute(text("INSERT INTO volunteer (id) VALUES (:id)"), {"id": existing_contact.id})
                    session.flush()
                    volunteer = session.query(Volunteer).filter_by(id=existing_contact.id).first()
                    # Populate volunteer-specific fields
                    for key, value in volunteer_data.items():
                        if hasattr(Volunteer, key):
                            setattr(volunteer, key, value)
                    # Update base Contact fields
                    base_contact_keys = [
                        "salesforce_individual_id",
                        "salesforce_account_id",
                        "first_name",
                        "last_name",
                        "middle_name",
                        "notes",
                        "last_email_date",
                        "birthdate",
                        "gender",
                    ]
                    for key in base_contact_keys:
                        if key in volunteer_data and hasattr(existing_contact, key):
                            setattr(existing_contact, key, volunteer_data[key])
                    # Set polymorphic type to volunteer
                    existing_contact.type = "volunteer"
            else:
                # No existing contact; create new volunteer (which will insert Contact + Volunteer rows)
                print(f"Creating new volunteer (no existing Contact): {record_id}")
                volunteer = Volunteer(**volunteer_data)
                session.add(volunteer)
                session.flush()  # Ensure volunteer.id is available for related rows

        except Exception as e:
            print(f"Error in create/update logic for volunteer {record_id}: {str(e)}")
            # If it's a unique constraint error, try to find and update the existing record
            if "UNIQUE constraint failed" in str(e) and "salesforce_individual_id" in str(e):
                try:
                    print(f"Attempting to recover from unique constraint error for volunteer {record_id}")
                    with session.no_autoflush:
                        existing_contact = session.query(Contact).filter_by(salesforce_individual_id=salesforce_id).first()
                    if existing_contact:
                        with session.no_autoflush:
                            existing_volunteer = session.query(Volunteer).filter_by(id=existing_contact.id).first()
                        if not existing_volunteer:
                            session.execute(text("INSERT INTO volunteer (id) VALUES (:id)"), {"id": existing_contact.id})
                            session.flush()
                            volunteer = session.query(Volunteer).filter_by(id=existing_contact.id).first()
                        else:
                            volunteer = existing_volunteer
                        # Update fields
                        for key, value in volunteer_data.items():
                            if hasattr(Volunteer, key):
                                setattr(volunteer, key, value)
                        base_contact_keys = [
                            "salesforce_individual_id",
                            "salesforce_account_id",
                            "first_name",
                            "last_name",
                            "middle_name",
                            "notes",
                            "last_email_date",
                            "birthdate",
                            "gender",
                        ]
                        for key in base_contact_keys:
                            if key in volunteer_data and hasattr(existing_contact, key):
                                setattr(existing_contact, key, volunteer_data[key])
                        existing_contact.type = "volunteer"
                        print(f"Recovered by linking existing Contact to Volunteer for {record_id}")
                        return True
                    else:
                        print(f"Could not find existing contact {record_id} after unique constraint error")
                        return False
                except Exception as recovery_error:
                    print(f"Error during recovery for volunteer {record_id}: {str(recovery_error)}")
                    return False
            return False

        # Handle emails
        try:
            new_emails = get_email_addresses(record)
            if new_emails:
                # Clear existing emails and add new ones
                volunteer.emails = new_emails
        except Exception as e:
            print(f"Error handling emails for volunteer {record_id}: {str(e)}")
            # Continue processing - don't fail the entire record

        # Handle phones
        try:
            new_phones = get_phone_numbers(record)
            if new_phones:
                # Clear existing phones and add new ones
                volunteer.phones = new_phones
        except Exception as e:
            print(f"Error handling phones for volunteer {record_id}: {str(e)}")
            # Continue processing - don't fail the entire record

        # Handle skills
        try:
            if record.get("Volunteer_Skills_Text__c") or record.get("Volunteer_Skills__c"):
                skills = parse_skills(record.get("Volunteer_Skills_Text__c", ""), record.get("Volunteer_Skills__c", ""))

                # Update skills
                for skill_name in skills:
                    skill = session.query(Skill).filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        session.add(skill)
                    if skill not in volunteer.skills:
                        volunteer.skills.append(skill)
        except Exception as e:
            print(f"Error handling skills for volunteer {record_id}: {str(e)}")
            # Continue processing - don't fail the entire record

        # Handle Connector data with null safety
        try:
            connector_data = {
                "active_subscription": ((record.get("Connector_Active_Subscription__c") or "").strip().upper() or "NONE"),
                "active_subscription_name": (record.get("Connector_Active_Subscription_Name__c") or "").strip(),
                "affiliations": (record.get("Connector_Affiliations__c") or "").strip(),
                "industry": (record.get("Connector_Industry__c") or "").strip(),
                "joining_date": (record.get("Connector_Joining_Date__c") or "").strip(),
                "last_login_datetime": (record.get("Connector_Last_Login_Date_Time__c") or "").strip(),
                "last_update_date": parse_date(record.get("Connector_Last_Update_Date__c")),
                "profile_link": (record.get("Connector_Profile_Link__c") or "").strip(),
                "role": (record.get("Connector_Role__c") or "").strip(),
                "signup_role": (record.get("Connector_SignUp_Role__c") or "").strip(),
                "user_auth_id": (record.get("Connector_User_ID__c") or "").strip(),
            }

            # Ensure volunteer has an id before touching connector data
            session.flush()

            connector = None
            # Check if user_auth_id is provided and not empty
            if connector_data["user_auth_id"]:
                # Check if a ConnectorData record already exists with this user_auth_id
                existing_connector = session.query(ConnectorData).filter_by(user_auth_id=connector_data["user_auth_id"]).first()

                if existing_connector:
                    # If the existing connector belongs to a different volunteer, skip this one
                    if existing_connector.volunteer_id != volunteer.id:
                        print(
                            f"Skipping connector data for volunteer {record_id}: user_auth_id {connector_data['user_auth_id']} already exists for volunteer {existing_connector.volunteer_id}"
                        )
                        # Continue processing the volunteer without connector data
                    else:
                        # Update the existing connector data for this volunteer
                        connector = existing_connector
                else:
                    # Create new connector data for this volunteer (use relationship, assign object)
                    connector = ConnectorData()
                    volunteer.connector = connector
                    session.add(connector)
            else:
                # No user_auth_id provided, create new connector data if volunteer doesn't have one
                connector = volunteer.connector
                if not connector:
                    connector = ConnectorData()
                    volunteer.connector = connector
                    session.add(connector)

            # Update connector fields if they exist in Salesforce data
            if connector and connector_data["active_subscription"] in [e.name for e in ConnectorSubscriptionEnum]:
                if connector.active_subscription != ConnectorSubscriptionEnum[connector_data["active_subscription"]]:
                    connector.active_subscription = ConnectorSubscriptionEnum[connector_data["active_subscription"]]

            if connector:
                for field, value in connector_data.items():
                    if field != "active_subscription" and value:  # Skip active_subscription as it's handled above
                        current_value = getattr(connector, field)
                        if current_value != value:
                            setattr(connector, field, value)
        except Exception as e:
            print(f"Error handling connector data for volunteer {record_id}: {str(e)}")
            # Continue processing - don't fail the entire record

        # Handle addresses
        try:
            # Handle mailing address
            mailing_address = record.get("MailingAddress", {})
            if isinstance(mailing_address, dict):
                # Find or create mailing address
                mailing = next((addr for addr in volunteer.addresses if addr.type == ContactTypeEnum.personal and addr.primary), None)
                if not mailing:
                    mailing = Address(contact_id=volunteer.id, type=ContactTypeEnum.personal, primary=True)
                    volunteer.addresses.append(mailing)

                # Update mailing address fields
                if mailing.address_line1 != mailing_address.get("street", ""):
                    mailing.address_line1 = mailing_address.get("street", "")
                if mailing.city != mailing_address.get("city", ""):
                    mailing.city = mailing_address.get("city", "")
                if mailing.state != mailing_address.get("state", ""):
                    mailing.state = mailing_address.get("state", "")
                if mailing.zip_code != mailing_address.get("postalCode", ""):
                    mailing.zip_code = mailing_address.get("postalCode", "")
                if mailing.country != mailing_address.get("country", ""):
                    mailing.country = mailing_address.get("country", "")

            # Handle work address if present
            work_address = record.get("npe01__Work_Address__c", "")
            if work_address:
                work = next((addr for addr in volunteer.addresses if addr.type == ContactTypeEnum.professional), None)
                if not work:
                    work = Address(contact_id=volunteer.id, type=ContactTypeEnum.professional)
                    volunteer.addresses.append(work)

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
                except Exception as e:
                    print(f"Error parsing work address for {volunteer.first_name} {volunteer.last_name}: {str(e)}")

            # Set address types based on primary/secondary preferences
            primary_type = (record.get("npe01__Primary_Address_Type__c") or "").lower()
            secondary_type = (record.get("npe01__Secondary_Address_Type__c") or "").lower()

            for addr in volunteer.addresses:
                is_home = addr.type == ContactTypeEnum.personal
                is_work = addr.type == ContactTypeEnum.professional

                # Set primary based on preference
                if (primary_type == "home" and is_home) or (primary_type == "work" and is_work):
                    addr.primary = True
                elif (secondary_type == "home" and is_home) or (secondary_type == "work" and is_work):
                    addr.primary = False

        except Exception as e:
            print(f"Error handling addresses for volunteer {record_id}: {str(e)}")
            # Continue processing - don't fail the entire record

        return True

    except Exception as e:
        # Log the error but don't fail the entire batch
        print(f"Error processing volunteer record {record_id}: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return False


def validate_affiliation_record(record: dict) -> list:
    """
    Validate a volunteer-organization affiliation record from Salesforce.

    Args:
        record: Dictionary containing affiliation data from Salesforce

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    if not record.get("Id"):
        errors.append("Missing affiliation Salesforce ID")
    elif len(record["Id"]) != 18:
        errors.append(f"Invalid affiliation Salesforce ID format: {record['Id']}")

    if not record.get("npe5__Contact__c"):
        errors.append("Missing contact ID in affiliation")
    elif len(record["npe5__Contact__c"]) != 18:
        errors.append(f"Invalid contact ID format: {record['npe5__Contact__c']}")

    if not record.get("npe5__Organization__c"):
        errors.append("Missing organization ID in affiliation")
    elif len(record["npe5__Organization__c"]) != 18:
        errors.append(f"Invalid organization ID format: {record['npe5__Organization__c']}")

    return errors


def process_affiliation_record_optimized(record: dict, session) -> bool:
    """
    Process a single volunteer-organization affiliation record using the optimized framework.

    Args:
        record: Dictionary containing affiliation data from Salesforce
        session: Database session

    Returns:
        True if processing was successful, False otherwise
    """
    try:
        # Get the volunteer and organization
        volunteer = session.query(Volunteer).filter_by(salesforce_individual_id=record["npe5__Contact__c"]).first()
        organization = session.query(Organization).filter_by(salesforce_id=record["npe5__Organization__c"]).first()

        if not volunteer:
            print(f"Volunteer not found for affiliation: {record['npe5__Contact__c']}")
            return False

        if not organization:
            print(f"Organization not found for affiliation: {record['npe5__Organization__c']}")
            return False

        # Check if affiliation already exists
        existing_affiliation = session.query(VolunteerOrganization).filter_by(volunteer_id=volunteer.id, organization_id=organization.id).first()

        if existing_affiliation:
            # Update existing affiliation
            existing_affiliation.role = record.get("npe5__Role__c", "").strip()
            existing_affiliation.status = record.get("npe5__Status__c", "").strip()
            existing_affiliation.is_primary = bool(record.get("npe5__Primary__c", False))
            existing_affiliation.start_date = parse_date(record.get("npe5__StartDate__c"))
            existing_affiliation.end_date = parse_date(record.get("npe5__EndDate__c"))
        else:
            # Create new affiliation
            new_affiliation = VolunteerOrganization(
                volunteer_id=volunteer.id,
                organization_id=organization.id,
                role=record.get("npe5__Role__c", "").strip(),
                status=record.get("npe5__Status__c", "").strip(),
                is_primary=bool(record.get("npe5__Primary__c", False)),
                start_date=parse_date(record.get("npe5__StartDate__c")),
                end_date=parse_date(record.get("npe5__EndDate__c")),
            )
            session.add(new_affiliation)

        return True

    except Exception as e:
        print(f"Error processing affiliation record: {str(e)}")
        return False


# ============================================================================
# LEGACY FUNCTIONS (for backward compatibility)
# ============================================================================


def process_volunteer_row(row, success_count, error_count, errors):
    """
    Process a single volunteer row from CSV data.

    This function handles the conversion of CSV data to Volunteer model instances,
    including proper data validation and relationship management.

    Args:
        row (dict): Dictionary containing volunteer data from CSV
        success_count (int): Current count of successful processing operations
        error_count (int): Current count of processing errors
        errors (list): List to collect error messages

    Returns:
        tuple: Updated (success_count, error_count)

    Note:
        This function is used primarily for CSV import operations and handles
        both new volunteer creation and existing volunteer updates.
    """
    try:
        # Check if volunteer exists by salesforce_id
        volunteer = None
        if row.get("Id"):
            volunteer = Volunteer.query.filter_by(salesforce_individual_id=row["Id"]).first()

        # If volunteer doesn't exist, create new one
        if not volunteer:
            volunteer = Volunteer()
            db.session.add(volunteer)

        # Update volunteer fields (handles both new and existing volunteers)
        volunteer.salesforce_individual_id = row.get("Id", "").strip()
        volunteer.salesforce_account_id = row.get("AccountId", "").strip()
        volunteer.first_name = row.get("FirstName", "").strip()
        volunteer.last_name = row.get("LastName", "").strip()
        volunteer.middle_name = row.get("MiddleName", "").strip()
        volunteer.organization_name = row.get("Primary Affiliation", "").strip()
        volunteer.title = row.get("Title", "").strip()
        volunteer.department = row.get("Department", "").strip()
        volunteer.industry = row.get("Industry", "").strip()

        # Handle gender enum
        gender_str = row.get("Gender", "").lower().replace(" ", "_").strip()
        if gender_str in [e.name for e in GenderEnum]:
            volunteer.gender = GenderEnum[gender_str]

        # Handle dates
        volunteer.birthdate = parse_date(row.get("Birthdate", ""))
        volunteer.first_volunteer_date = parse_date(row.get("First_Volunteer_Date__c", ""))
        volunteer.last_mailchimp_activity_date = parse_date(row.get("Last_Mailchimp_Email_Date__c", ""))
        volunteer.last_volunteer_date = parse_date(row.get("Last_Volunteer_Date__c", ""))
        volunteer.last_email_date = parse_date(row.get("Last_Email_Message__c", ""))
        volunteer.last_non_internal_email_date = parse_date(row.get("Last_Non_Internal_Email_Activity__c", ""))
        volunteer.notes = row.get("Notes", "").strip()

        # Handle emails
        new_emails = get_email_addresses(row)
        if new_emails:
            # Clear existing emails and add new ones
            volunteer.emails = new_emails

        # Handle phones
        new_phones = get_phone_numbers(row)
        if new_phones:
            # Clear existing phones and add new ones
            volunteer.phones = new_phones

        # Handle skills
        if row.get("Volunteer_Skills_Text__c") or row.get("Volunteer_Skills__c"):
            skills = parse_skills(row.get("Volunteer_Skills_Text__c", ""), row.get("Volunteer_Skills__c", ""))

            # Update skills
            for skill_name in skills:
                skill = Skill.query.filter_by(name=skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.session.add(skill)
                if skill not in volunteer.skills:
                    volunteer.skills.append(skill)

        # Add this new section to handle times_volunteered
        if row.get("Number_of_Attended_Volunteer_Sessions__c"):
            try:
                volunteer.times_volunteered = int(float(row["Number_of_Attended_Volunteer_Sessions__c"]))
            except (ValueError, TypeError):
                volunteer.times_volunteered = 0

        # Handle Connector data
        connector_data = {
            "active_subscription": (row.get("Connector_Active_Subscription__c") or "").strip().upper() or "NONE",
            "active_subscription_name": (row.get("Connector_Active_Subscription_Name__c") or "").strip(),
            "affiliations": (row.get("Connector_Affiliations__c") or "").strip(),
            "industry": (row.get("Connector_Industry__c") or "").strip(),
            "joining_date": (row.get("Connector_Joining_Date__c") or "").strip(),
            "last_login_datetime": (row.get("Connector_Last_Login_Date_Time__c") or "").strip(),
            "last_update_date": parse_date(row.get("Connector_Last_Update_Date__c")),
            "profile_link": (row.get("Connector_Profile_Link__c") or "").strip(),
            "role": (row.get("Connector_Role__c") or "").strip(),
            "signup_role": (row.get("Connector_SignUp_Role__c") or "").strip(),
            "user_auth_id": (row.get("Connector_User_ID__c") or "").strip(),
        }

        # Create or update connector data
        if not volunteer.connector:
            volunteer.connector = ConnectorData(volunteer_id=volunteer.id)

        # Update connector fields if they exist in Salesforce data
        if connector_data["active_subscription"] in [e.name for e in ConnectorSubscriptionEnum]:
            if volunteer.connector.active_subscription != ConnectorSubscriptionEnum[connector_data["active_subscription"]]:
                volunteer.connector.active_subscription = ConnectorSubscriptionEnum[connector_data["active_subscription"]]

        for field, value in connector_data.items():
            if field != "active_subscription" and value:  # Skip active_subscription as it's handled above
                current_value = getattr(volunteer.connector, field)
                if current_value != value:
                    setattr(volunteer.connector, field, value)

        return success_count + 1, error_count

    except Exception as e:
        db.session.rollback()
        errors.append(f"Error processing row: {str(e)}")
        return success_count, error_count + 1


@volunteers_bp.route("/volunteers")
@login_required
def volunteers():
    """
    Main volunteer listing page with filtering, sorting, and pagination.

    This route handles the primary volunteer management interface, providing:
    - Comprehensive filtering by name, organization, email, skills, and local status
    - Sorting by various fields with configurable direction
    - Pagination for large datasets
    - Real-time volunteer count calculations

    Query Parameters:
    - page: Current page number for pagination
    - per_page: Number of volunteers per page
    - search_name: Filter by volunteer name (supports multi-term search)
    - org_search: Filter by organization name, title, or department
    - email_search: Filter by email address
    - skill_search: Filter by volunteer skills
    - local_status: Filter by local status (local, partial, non_local, unknown)
    - sort_by: Field to sort by (name, times_volunteered, last_volunteer_date)
    - sort_direction: Sort direction (asc, desc)

    Returns:
        rendered template: volunteers/volunteers.html with volunteer data and filters
    """
    # Get pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    # Create a dict of current filters, including pagination params
    current_filters = {
        "search_name": request.args.get("search_name", "").strip(),
        "org_search": request.args.get("org_search", "").strip(),
        "email_search": request.args.get("email_search", "").strip(),
        "skill_search": request.args.get("skill_search", "").strip(),
        "local_status": request.args.get("local_status", ""),
        "per_page": per_page,
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Get sort parameters
    sort_by = request.args.get("sort_by", "last_volunteer_date")  # default sort field
    sort_direction = request.args.get("sort_direction", "desc")  # default direction

    # Add sort parameters to current_filters
    current_filters.update({"sort_by": sort_by, "sort_direction": sort_direction})

    # Start with a subquery to get the attended count
    # This calculates the actual number of events each volunteer has attended
    # by counting EventParticipation records with valid attendance statuses
    attended_count_subq = (
        db.session.query(EventParticipation.volunteer_id, db.func.count(EventParticipation.id).label("attended_count"))
        .filter(or_(EventParticipation.status == "Attended", EventParticipation.status == "Completed", EventParticipation.status == "Successfully Completed"))
        .group_by(EventParticipation.volunteer_id)
        .subquery()
    )

    # Build main query with joins for filtering and organization data
    # This complex query allows for efficient filtering across multiple related tables
    query = (
        db.session.query(Volunteer, db.func.coalesce(attended_count_subq.c.attended_count, 0).label("attended_count"))
        .outerjoin(attended_count_subq, Volunteer.id == attended_count_subq.c.volunteer_id)
        .outerjoin(VolunteerOrganization)
        .outerjoin(Organization, VolunteerOrganization.organization_id == Organization.id)
    )

    # Apply filters
    if current_filters.get("search_name"):
        # Split search terms and remove empty strings
        search_terms = [term.strip() for term in current_filters["search_name"].split() if term.strip()]

        # Build dynamic search condition
        name_conditions = []
        for term in search_terms:
            search_pattern = f"%{term}%"
            name_conditions.append(
                or_(
                    Volunteer.first_name.ilike(search_pattern),
                    Volunteer.middle_name.ilike(search_pattern),
                    Volunteer.last_name.ilike(search_pattern),
                    # Concatenated name search using SQLite's || operator
                    (Volunteer.first_name + " " + db.func.coalesce(Volunteer.middle_name, "") + " " + Volunteer.last_name).ilike(search_pattern),
                )
            )
        # Combine all conditions with AND (each term must match somewhere)
        if name_conditions:
            query = query.filter(and_(*name_conditions))

    if current_filters.get("org_search"):
        search_term = f"%{current_filters['org_search']}%"
        # The joins are already established in the main query, so we can directly filter
        query = query.filter(
            or_(
                # Search direct volunteer fields
                Volunteer.organization_name.ilike(search_term),
                Volunteer.title.ilike(search_term),
                Volunteer.department.ilike(search_term),
                # Search related organization fields
                Organization.name.ilike(search_term),
                VolunteerOrganization.role.ilike(search_term),
            )
        )

    if current_filters.get("email_search"):
        search_term = f"%{current_filters['email_search']}%"
        query = query.join(Email).filter(Email.email.ilike(search_term))

    if current_filters.get("skill_search"):
        search_term = f"%{current_filters['skill_search']}%"
        query = query.join(Volunteer.skills).filter(Skill.name.ilike(search_term))

    if current_filters.get("local_status"):
        query = query.filter(Volunteer.local_status == current_filters["local_status"])

    # Apply sorting based on parameters
    if sort_by:
        sort_column = None
        if sort_by == "name":
            sort_column = Volunteer.first_name + " " + db.func.coalesce(Volunteer.middle_name, "") + " " + Volunteer.last_name
        elif sort_by == "times_volunteered":
            sort_column = Volunteer.times_volunteered + db.func.coalesce(attended_count_subq.c.attended_count, 0) + Volunteer.additional_volunteer_count

        if sort_column is not None:
            if sort_direction == "desc":
                query = query.order_by(sort_column.desc(), Volunteer.last_name.asc())
            else:
                query = query.order_by(sort_column.asc(), Volunteer.last_name.asc())
        else:
            # Default sort
            query = query.order_by(Volunteer.last_volunteer_date.desc())

    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Transform the results to include the attended count and organization info
    volunteers_with_counts = []
    for result in pagination.items:
        volunteer_data = {"volunteer": result[0], "attended_count": result[1] or 0, "organizations": [], "organizations_json": []}  # JSON-serializable version

        # Get organization info with roles
        for vol_org in result[0].volunteer_organizations:
            org_info = {"organization": vol_org.organization, "role": vol_org.role, "status": vol_org.status, "is_primary": vol_org.is_primary}
            volunteer_data["organizations"].append(org_info)

            # Create JSON-serializable version
            org_json = {
                "organization": {"id": vol_org.organization.id, "name": vol_org.organization.name},
                "role": vol_org.role,
                "status": vol_org.status,
                "is_primary": vol_org.is_primary,
            }
            volunteer_data["organizations_json"].append(org_json)

        # Ensure organizations_json is always a list, even if empty
        if volunteer_data["organizations_json"] is None:
            volunteer_data["organizations_json"] = []

        # Debug: Print the organizations_json for the first few volunteers
        if len(volunteers_with_counts) < 3:
            print(f"Volunteer {result[0].id}: {len(volunteer_data['organizations_json'])} organizations")
            print(f"Organizations JSON: {volunteer_data['organizations_json']}")

        volunteers_with_counts.append(volunteer_data)

    return render_template("volunteers/volunteers.html", volunteers=volunteers_with_counts, pagination=pagination, current_filters=current_filters)


@volunteers_bp.route("/volunteers/add", methods=["GET", "POST"])
@login_required
def add_volunteer():
    form = VolunteerForm()

    if form.validate_on_submit():
        try:
            # Create and add volunteer first
            volunteer = Volunteer(
                salutation=form.salutation.data if form.salutation.data else None,
                first_name=form.first_name.data,
                middle_name=form.middle_name.data,
                last_name=form.last_name.data,
                suffix=form.suffix.data if form.suffix.data else None,
                organization_name=form.organization_name.data,
                title=form.title.data,
                department=form.department.data,
                industry=form.industry.data,
                notes=form.notes.data,
            )

            # Handle enums properly
            if form.gender.data:
                volunteer.gender = GenderEnum[form.gender.data]
            if form.local_status.data:
                volunteer.local_status = LocalStatusEnum[form.local_status.data]
            if form.race_ethnicity.data:
                volunteer.race_ethnicity = RaceEthnicityEnum[form.race_ethnicity.data]
            if form.education.data:
                volunteer.education = EducationEnum[form.education.data]

            db.session.add(volunteer)
            db.session.flush()  # This ensures volunteer has an ID before adding relationships

            # Add skills
            if form.skills.data:
                # Parse skills from textarea (assume comma-separated)
                skill_names = [skill.strip() for skill in form.skills.data.split(",") if skill.strip()]
                for skill_name in set(skill_names):
                    skill = Skill.query.filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.session.add(skill)
                        db.session.flush()
                    volunteer.skills.append(skill)

            # Add email
            if form.email.data:
                email_type = ContactTypeEnum.personal if form.email_type.data == "personal" else ContactTypeEnum.professional
                email = Email(email=form.email.data, type=email_type, primary=True, contact_id=volunteer.id)
                db.session.add(email)

            # Add phone
            if form.phone.data:
                phone_type = ContactTypeEnum.personal if form.phone_type.data == "personal" else ContactTypeEnum.professional
                phone = Phone(number=form.phone.data, type=phone_type, primary=True, contact_id=volunteer.id)
                db.session.add(phone)

            # Link to organization if provided
            if form.organization_name.data:
                VolunteerOrganization.link_volunteer_to_org(
                    volunteer=volunteer, org_name=form.organization_name.data, role=form.title.data, is_primary=True  # Use title as role for now
                )
                db.session.flush()

            db.session.commit()
            flash("Volunteer added successfully!", "success")
            return redirect(url_for("volunteers.volunteers"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error adding volunteer: {str(e)}", "error")

    return render_template("volunteers/add_volunteer.html", form=form)


@volunteers_bp.route("/volunteers/view/<int:id>")
@login_required
def view_volunteer(id):
    volunteer = db.session.get(Volunteer, id)
    if not volunteer:
        abort(404)

    # Get all participations for this volunteer, including virtual events
    participations = EventParticipation.query.filter_by(volunteer_id=id).join(Event, EventParticipation.event_id == Event.id).all()

    # Define status mapping for various event types and status values
    status_mapping = {
        # Standard statuses
        "Attended": "Attended",
        "Completed": "Attended",
        "No-Show": "No-Show",
        "No Show": "No-Show",
        "Cancelled": "Cancelled",
        "Canceled": "Cancelled",
        # Virtual-specific statuses
        "successfully completed": "Attended",
        "simulcast": "Attended",
        "technical difficulties": "No-Show",
        "local professional no-show": "No-Show",
        "pathful professional no-show": "No-Show",
        "teacher no-show": "No-Show",
        "teacher cancelation": "Cancelled",
        "Confirmed": "Attended",  # Could be pending or attended depending on your business logic
    }

    # Initialize participation stats with empty lists
    participation_stats = {"Attended": [], "No-Show": [], "Cancelled": []}

    # Process each participation record
    for participation in participations:
        # Get status from participation record, fall back to event status
        status = participation.status

        # If status isn't directly usable, try mapping it
        if status not in participation_stats:
            # Try using the mapping, default to 'Attended' if not found
            mapped_status = status_mapping.get(status, "Attended")

            # If still not valid, try lowercased version (handle case sensitivity)
            if mapped_status not in participation_stats and status:
                mapped_status = status_mapping.get(status.lower(), "Attended")
        else:
            mapped_status = status

        # Get the event date, handling virtual events that might store date differently
        event_date = None
        if participation.event.start_date:
            event_date = participation.event.start_date
        elif hasattr(participation.event, "date") and participation.event.date:
            event_date = participation.event.date
        else:
            # If no date available, create a default date to avoid errors
            event_date = datetime.now()

        # Add to appropriate category
        if mapped_status in participation_stats:
            participation_stats[mapped_status].append({"event": participation.event, "delivery_hours": participation.delivery_hours, "date": event_date})

    # Sort each list by date
    for status in participation_stats:
        participation_stats[status].sort(key=lambda x: x["date"], reverse=True)

    # Get history records for the volunteer
    histories = History.query.filter_by(volunteer_id=id, is_deleted=False).order_by(History.activity_date.desc()).all()

    # Create a dictionary of organization relationships for easy access in template
    org_relationships = {}
    for vol_org in volunteer.volunteer_organizations:
        org_relationships[vol_org.organization_id] = vol_org

    return render_template(
        "volunteers/view.html",
        volunteer=volunteer,
        emails=sorted(volunteer.emails, key=lambda x: x.primary, reverse=True),
        phones=sorted(volunteer.phones, key=lambda x: x.primary, reverse=True),
        participation_stats=participation_stats,
        histories=histories,
        org_relationships=org_relationships,
        now=datetime.now(),
    )


@volunteers_bp.route("/volunteers/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_volunteer(id):
    volunteer = db.session.get(Volunteer, id)
    if not volunteer:
        abort(404)

    form = VolunteerForm(obj=volunteer)

    # Populate form with existing data
    if request.method == "GET":
        # Handle enums properly
        if volunteer.gender:
            form.gender.data = volunteer.gender.name
        if volunteer.local_status:
            form.local_status.data = volunteer.local_status.name
        if volunteer.race_ethnicity:
            form.race_ethnicity.data = volunteer.race_ethnicity.name
        if volunteer.education:
            form.education.data = volunteer.education.name

        # Handle skills as comma-separated string
        if volunteer.skills:
            form.skills.data = ", ".join([skill.name for skill in volunteer.skills])

        # Handle email and phone safely
        try:
            emails_list = list(volunteer.emails) if volunteer.emails else []
            if emails_list:
                primary_email = next((email for email in emails_list if email.primary), None)
                if not primary_email:
                    primary_email = emails_list[0]
                if primary_email:
                    form.email.data = primary_email.email
                    form.email_type.data = primary_email.type.name
        except Exception as e:
            print(f"Error loading emails: {e}")

        try:
            phones_list = list(volunteer.phones) if volunteer.phones else []
            if phones_list:
                primary_phone = next((phone for phone in phones_list if phone.primary), None)
                if not primary_phone:
                    primary_phone = phones_list[0]
                if primary_phone:
                    form.phone.data = primary_phone.number
                    form.phone_type.data = primary_phone.type.name
        except Exception as e:
            print(f"Error loading phones: {e}")

    if form.validate_on_submit():
        try:
            print(f"Form data: {form.data}")  # Debug form data

            # Update basic fields
            volunteer.salutation = form.salutation.data if form.salutation.data else None
            volunteer.first_name = form.first_name.data
            volunteer.middle_name = form.middle_name.data
            volunteer.last_name = form.last_name.data
            volunteer.suffix = form.suffix.data if form.suffix.data else None
            volunteer.organization_name = form.organization_name.data
            volunteer.title = form.title.data
            volunteer.department = form.department.data
            volunteer.industry = form.industry.data
            volunteer.notes = form.notes.data

            print("Basic fields updated")  # Debug checkpoint

            # Handle enums with proper error checking
            try:
                if form.gender.data and form.gender.data != "":
                    volunteer.gender = GenderEnum[form.gender.data]
                else:
                    volunteer.gender = None

                if form.local_status.data and form.local_status.data != "":
                    volunteer.local_status = LocalStatusEnum[form.local_status.data]
                else:
                    volunteer.local_status = None

                if form.race_ethnicity.data and form.race_ethnicity.data != "":
                    volunteer.race_ethnicity = RaceEthnicityEnum[form.race_ethnicity.data]
                else:
                    volunteer.race_ethnicity = None

                if form.education.data and form.education.data != "":
                    volunteer.education = EducationEnum[form.education.data]
                else:
                    volunteer.education = None

                print("Enums updated")  # Debug checkpoint
            except KeyError as e:
                print(f"Enum error: {e}")
                flash(f"Invalid enum value: {str(e)}", "error")
                return redirect(url_for("volunteers.edit_volunteer", id=id))

            # Handle skills
            if form.skills.data and form.skills.data.strip() and form.skills.data != "[]":
                try:
                    # Clear existing skills
                    volunteer.skills = []
                    db.session.flush()

                    # Add new skills
                    skill_names = [skill.strip() for skill in form.skills.data.split(",") if skill.strip() and skill.strip() != "[]"]
                    for skill_name in set(skill_names):
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                            db.session.add(skill)
                            db.session.flush()
                        volunteer.skills.append(skill)
                    print(f"Skills updated: {skill_names}")  # Debug checkpoint
                except Exception as e:
                    print(f"Skills error: {e}")
                    flash(f"Error updating skills: {str(e)}", "error")
                    return redirect(url_for("volunteers.edit_volunteer", id=id))
            else:
                # Clear skills if empty
                volunteer.skills = []
                print("Skills cleared (empty input)")  # Debug checkpoint

            # Handle email with transaction safety
            if form.email.data:
                try:
                    Email.query.filter_by(contact_id=volunteer.id).delete()
                    email_type = ContactTypeEnum.personal if form.email_type.data == "personal" else ContactTypeEnum.professional
                    email = Email(contact_id=volunteer.id, email=form.email.data, type=email_type, primary=True)
                    db.session.add(email)
                    print(f"Email updated: {form.email.data}")  # Debug checkpoint
                except Exception as e:
                    print(f"Email error: {e}")
                    flash(f"Error updating email: {str(e)}", "error")
                    return redirect(url_for("volunteers.edit_volunteer", id=id))

            # Handle phone with transaction safety
            if form.phone.data:
                try:
                    Phone.query.filter_by(contact_id=volunteer.id).delete()
                    phone_type = ContactTypeEnum.personal if form.phone_type.data == "personal" else ContactTypeEnum.professional
                    phone = Phone(contact_id=volunteer.id, number=form.phone.data, type=phone_type, primary=True)
                    db.session.add(phone)
                    print(f"Phone updated: {form.phone.data}")  # Debug checkpoint
                except Exception as e:
                    print(f"Phone error: {e}")
                    flash(f"Error updating phone: {str(e)}", "error")
                    return redirect(url_for("volunteers.edit_volunteer", id=id))

            print("About to commit to database")  # Debug checkpoint
            db.session.commit()
            print("Database committed successfully")  # Debug checkpoint
            flash("Volunteer updated successfully", "success")
            redirect_url = url_for("volunteers.view_volunteer", id=volunteer.id)
            print(f"Redirecting to: {redirect_url}")  # Debug redirect URL
            return redirect(redirect_url)

        except Exception as e:
            db.session.rollback()
            print(f"General error in edit_volunteer: {str(e)}")  # Debug error
            flash(f"Error updating volunteer: {str(e)}", "error")
    else:
        # Form validation failed
        print(f"Form validation failed. Errors: {form.errors}")  # Debug validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template(
        "volunteers/edit.html",
        form=form,
        volunteer=volunteer,
        GenderEnum=GenderEnum,
        RaceEthnicityEnum=RaceEthnicityEnum,
        LocalStatusEnum=LocalStatusEnum,
        EducationEnum=EducationEnum,
    )


@volunteers_bp.route("/volunteers/purge", methods=["POST"])
@login_required
def purge_volunteers():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Get all volunteer IDs first
        volunteer_ids = db.session.query(Volunteer.id).all()
        volunteer_ids = [v[0] for v in volunteer_ids]

        if not volunteer_ids:
            return jsonify({"success": True, "message": "No volunteers found to purge"})

        print(f"Purging {len(volunteer_ids)} volunteers and all related data...")

        # Delete all related data for volunteers in the correct order
        # 1. Delete connector data (one-to-one relationship)
        ConnectorData.query.filter(ConnectorData.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        print("✓ Deleted connector data")

        # 2. Delete many-to-many relationships
        VolunteerSkill.query.filter(VolunteerSkill.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        VolunteerOrganization.query.filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        print("✓ Deleted volunteer skills and organization affiliations")

        # 3. Delete one-to-many relationships
        Engagement.query.filter(Engagement.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        EventParticipation.query.filter(EventParticipation.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        History.query.filter(History.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        print("✓ Deleted engagements, event participations, and history records")

        # 4. Delete contact-related data (emails, phones, addresses)
        Email.query.filter(Email.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        Phone.query.filter(Phone.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        Address.query.filter(Address.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        print("✓ Deleted contact information (emails, phones, addresses)")

        # 5. Delete volunteers (this will cascade to contact records due to inheritance)
        Volunteer.query.filter(Volunteer.id.in_(volunteer_ids)).delete(synchronize_session=False)
        print("✓ Deleted volunteer records")

        # 6. Clean up any orphaned contact records
        Contact.query.filter(Contact.id.in_(volunteer_ids)).delete(synchronize_session=False)
        print("✓ Cleaned up orphaned contact records")

        # 7. Clean up any orphaned email/phone records
        Email.query.filter(Email.contact_id.notin_(Contact.query.with_entities(Contact.id))).delete(synchronize_session=False)
        Phone.query.filter(Phone.contact_id.notin_(Contact.query.with_entities(Contact.id))).delete(synchronize_session=False)
        print("✓ Cleaned up orphaned email and phone records")

        db.session.commit()
        print("✓ Database transaction committed successfully")

        return jsonify({"success": True, "message": f"Successfully purged {len(volunteer_ids)} volunteers and all associated records"})

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during volunteer purge: {str(e)}")
        return jsonify({"success": False, "message": f"Error purging volunteers: {str(e)}"}), 500


@volunteers_bp.route("/volunteers/delete/<int:id>", methods=["DELETE"])
@login_required
def delete_volunteer(id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        volunteer = db.session.get(Volunteer, id)
        if not volunteer:
            abort(404)

        # Delete all related records first (in correct order due to foreign key constraints)
        Email.query.filter_by(contact_id=id).delete()
        Phone.query.filter_by(contact_id=id).delete()
        Address.query.filter_by(contact_id=id).delete()
        VolunteerSkill.query.filter_by(volunteer_id=id).delete()
        History.query.filter_by(volunteer_id=id).delete()
        EventParticipation.query.filter_by(volunteer_id=id).delete()
        VolunteerOrganization.query.filter_by(volunteer_id=id).delete()

        # Delete the volunteer
        db.session.delete(volunteer)
        db.session.commit()

        return jsonify({"success": True, "message": "Volunteer deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@volunteers_bp.route("/volunteers/import-from-salesforce", methods=["POST"])
@login_required
def import_from_salesforce():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        print("Starting volunteer import from Salesforce...")

        # Define Salesforce query
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
               Connector_User_ID__c
        FROM Contact
        WHERE Contact_Type__c = 'Volunteer' or Contact_Type__c=''
        """

        # Connect to Salesforce
        sf = Salesforce(username=Config.SF_USERNAME, password=Config.SF_PASSWORD, security_token=Config.SF_SECURITY_TOKEN, domain="login")

        # Execute the query
        result = sf.query_all(salesforce_query)
        sf_rows = result.get("records", [])

        success_count = 0
        error_count = 0
        created_count = 0
        updated_count = 0
        errors = []

        # Add comprehensive education mapping
        education_mapping = {
            # Exact matches
            "BACHELORS": "BACHELORS_DEGREE",
            "MASTERS": "MASTERS",
            "DOCTORATE": "DOCTORATE",
            # Common variations
            "BACHELOR": "BACHELORS_DEGREE",
            "BACHELOR'S": "BACHELORS_DEGREE",
            "BACHELORS DEGREE": "BACHELORS_DEGREE",
            "MASTER": "MASTERS",
            "MASTER'S": "MASTERS",
            "MASTERS DEGREE": "MASTERS",
            "PHD": "DOCTORATE",
            "PH.D": "DOCTORATE",
            "PH.D.": "DOCTORATE",
            "DOCTORAL": "DOCTORATE",
            # New Salesforce specific values
            "HIGH SCHOOL DIPLOMA OR GED": "HIGH_SCHOOL",
            "ADVANCED PROFESSIONAL DEGREE": "PROFESSIONAL",
            "PREFER NOT TO ANSWER": "UNKNOWN",
            # Other credentials
            "CERTIFICATE": "OTHER",
            "CERTIFICATION": "OTHER",
            "ASSOCIATE": "ASSOCIATES",
            "ASSOCIATES": "ASSOCIATES",
            "ASSOCIATE'S": "ASSOCIATES",
            "HIGH SCHOOL": "HIGH_SCHOOL",
            "GED": "HIGH_SCHOOL",
            "SOME COLLEGE": "SOME_COLLEGE",
            "PROFESSIONAL": "PROFESSIONAL",
            "PROFESSIONAL DEGREE": "PROFESSIONAL",
        }

        # Process each row from Salesforce
        for row in sf_rows:
            try:
                # Check if volunteer exists
                volunteer = Volunteer.query.filter_by(salesforce_individual_id=row["Id"]).first()
                is_new = False
                updates = []

                if not volunteer:
                    volunteer = Volunteer()
                    volunteer.salesforce_individual_id = row["Id"]
                    db.session.add(volunteer)
                    is_new = True
                    updates.append("Created new volunteer")

                # Update volunteer fields only if they've changed
                if volunteer.salesforce_account_id != row["AccountId"]:
                    volunteer.salesforce_account_id = row["AccountId"]
                    updates.append("account_id")

                new_first_name = (row.get("FirstName") or "").strip()
                if volunteer.first_name != new_first_name:
                    volunteer.first_name = new_first_name
                    updates.append("first_name")

                new_last_name = (row.get("LastName") or "").strip()
                if volunteer.last_name != new_last_name:
                    volunteer.last_name = new_last_name
                    updates.append("last_name")

                new_middle_name = (row.get("MiddleName") or "").strip()
                if volunteer.middle_name != new_middle_name:
                    volunteer.middle_name = new_middle_name
                    updates.append("middle_name")

                new_org_name = (row.get("npsp__Primary_Affiliation__c") or "").strip()
                if volunteer.organization_name != new_org_name:
                    volunteer.organization_name = new_org_name
                    updates.append("organization")

                new_title = (row.get("Title") or "").strip()
                if volunteer.title != new_title:
                    volunteer.title = new_title
                    updates.append("title")

                new_department = (row.get("Department") or "").strip()
                if volunteer.department != new_department:
                    volunteer.department = new_department
                    updates.append("department")

                # Handle gender enum
                gender_str = (row.get("Gender__c") or "").lower().replace(" ", "_").strip()
                if gender_str and gender_str in [e.name for e in GenderEnum]:
                    if not volunteer.gender or volunteer.gender.name != gender_str:
                        volunteer.gender = GenderEnum[gender_str]
                        updates.append("gender")

                # Handle race/ethnicity
                race_ethnicity_map = {
                    "Bi-racial/Multi-racial/Multicultural": "bi_multi_racial",
                    "Black": "black_african",
                    "Black/African American": "black",
                    "Prefer not to answer": "prefer_not_to_say",
                    "Native American/Alaska Native/First Nation": "native_american",
                    "White/Caucasian/European American": "white_caucasian",
                    "Hispanic American/Latino": "hispanic_american",
                    "Other POC": "other_poc",
                    "Asian American/Pacific Islander": "asian_pacific_islander",
                }

                # Set default mappings for common cases
                default_mapping = {
                    "Other POC": "other",
                    "White/Caucasian/European American": "white",
                    "Black": "black",
                    "Bi-racial/Multi-racial/Multicultural": "multi_racial",
                }

                race_ethnicity_str = row.get("Racial_Ethnic_Background__c")

                if race_ethnicity_str and race_ethnicity_str != "None":
                    # Clean the string for comparison
                    cleaned_str = race_ethnicity_str.strip()
                    if "AggregateResult" in cleaned_str:
                        cleaned_str = cleaned_str.replace("AggregateResult", "").strip()

                    # Try primary mapping first
                    enum_value = race_ethnicity_map.get(cleaned_str)

                    if enum_value and enum_value in [e.name for e in RaceEthnicityEnum]:
                        if not volunteer.race_ethnicity or volunteer.race_ethnicity.name != enum_value:
                            volunteer.race_ethnicity = RaceEthnicityEnum[enum_value]
                            updates.append("race_ethnicity")
                    else:
                        # Try default mapping if primary fails
                        default_value = default_mapping.get(cleaned_str)
                        if default_value and default_value in [e.name for e in RaceEthnicityEnum]:
                            if not volunteer.race_ethnicity or volunteer.race_ethnicity.name != default_value:
                                volunteer.race_ethnicity = RaceEthnicityEnum[default_value]
                                updates.append("race_ethnicity")
                elif volunteer.race_ethnicity != RaceEthnicityEnum.unknown:
                    volunteer.race_ethnicity = RaceEthnicityEnum.unknown
                    updates.append("race_ethnicity")

                # Handle dates
                new_birthdate = parse_date(row.get("Birthdate"))
                if volunteer.birthdate != new_birthdate:
                    volunteer.birthdate = new_birthdate
                    updates.append("birthdate")

                new_first_volunteer_date = parse_date(row.get("First_Volunteer_Date__c"))
                if volunteer.first_volunteer_date != new_first_volunteer_date:
                    volunteer.first_volunteer_date = new_first_volunteer_date
                    updates.append("first_volunteer_date")

                new_mailchimp_date = parse_date(row.get("Last_Mailchimp_Email_Date__c"))
                if volunteer.last_mailchimp_activity_date != new_mailchimp_date:
                    volunteer.last_mailchimp_activity_date = new_mailchimp_date
                    updates.append("mailchimp_date")

                new_volunteer_date = parse_date(row.get("Last_Volunteer_Date__c"))
                if volunteer.last_volunteer_date != new_volunteer_date:
                    volunteer.last_volunteer_date = new_volunteer_date
                    updates.append("volunteer_date")

                new_activity_date = parse_date(row.get("Last_Activity_Date__c"))
                if volunteer.last_activity_date != new_activity_date:
                    volunteer.last_activity_date = new_activity_date
                    updates.append("activity_date")

                new_email_date = parse_date(row.get("Last_Email_Message__c"))
                if volunteer.last_email_date != new_email_date:
                    volunteer.last_email_date = new_email_date
                    updates.append("email_date")

                new_non_internal_email_date = parse_date(row.get("Last_Non_Internal_Email_Activity__c"))
                if volunteer.last_non_internal_email_date != new_non_internal_email_date:
                    volunteer.last_non_internal_email_date = new_non_internal_email_date
                    updates.append("non_internal_email_date")

                new_notes = (row.get("Volunteer_Recruitment_Notes__c") or "").strip()
                if volunteer.notes != new_notes:
                    volunteer.notes = new_notes
                    updates.append("notes")

                # Handle description
                new_description = (row.get("Description") or "").strip()
                if volunteer.description != new_description:
                    volunteer.description = new_description
                    updates.append("description")

                # Handle education level with robust mapping
                education_str = (row.get("Highest_Level_of_Educational__c") or "").strip()
                if education_str:
                    try:
                        # Normalize the string (uppercase, remove special chars)
                        normalized_education = education_str.upper().replace(".", "").replace("-", " ")

                        # Try direct mapping first
                        enum_value = education_mapping.get(normalized_education)

                        if enum_value and enum_value in [e.name for e in EducationEnum]:
                            if not volunteer.education or volunteer.education.name != enum_value:
                                volunteer.education = EducationEnum[enum_value]
                                updates.append("education")
                        else:
                            # Log unmatched values for future mapping updates
                            print(f"Unmatched education value: {education_str}")
                            # Set to UNKNOWN for unmatched values
                            volunteer.education = EducationEnum.UNKNOWN
                            updates.append("education")

                    except (ValueError, KeyError) as e:
                        print(f"Error mapping education value '{education_str}': {str(e)}")
                        # Set to UNKNOWN if mapping fails
                        volunteer.education = EducationEnum.UNKNOWN
                        updates.append("education")

                # Handle age group
                age_str = (row.get("Age_Group__c") or "").strip()
                if age_str:
                    # Map Salesforce age groups to our enum
                    age_map = {
                        "Under 18": AgeGroupEnum.UNDER_18,
                        "18-24": AgeGroupEnum.AGE_18_24,
                        "25-34": AgeGroupEnum.AGE_25_34,
                        "35-44": AgeGroupEnum.AGE_35_44,
                        "45-54": AgeGroupEnum.AGE_45_54,
                        "55-64": AgeGroupEnum.AGE_55_64,
                        "65+": AgeGroupEnum.AGE_65_PLUS,
                    }
                    new_age_group = age_map.get(age_str, AgeGroupEnum.UNKNOWN)
                    if volunteer.age_group != new_age_group:
                        volunteer.age_group = new_age_group
                        updates.append("age_group")

                # Handle interests
                interests_str = row.get("Volunteer_Interests__c")
                if interests_str is not None:  # Only update if field exists in Salesforce data
                    interests_str = interests_str.strip()
                    if volunteer.interests != interests_str:
                        volunteer.interests = interests_str
                        updates.append("interests")

                # Handle skills - only update if there are changes
                if row.get("Volunteer_Skills__c") or row.get("Volunteer_Skills_Text__c"):
                    new_skills = parse_skills(row.get("Volunteer_Skills_Text__c", ""), row.get("Volunteer_Skills__c", ""))
                    current_skills = {skill.name for skill in volunteer.skills}
                    if set(new_skills) != current_skills:
                        # Clear existing skills
                        volunteer.skills = []
                        # Add new skills
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
                        new_times = int(float(row["Number_of_Attended_Volunteer_Sessions__c"]))
                        if volunteer.times_volunteered != new_times:
                            volunteer.times_volunteered = new_times
                            updates.append("times_volunteered")
                    except (ValueError, TypeError):
                        if volunteer.times_volunteered != 0:
                            volunteer.times_volunteered = 0
                            updates.append("times_volunteered")

                # Handle contact preferences
                new_do_not_call = bool(row.get("DoNotCall"))
                if volunteer.do_not_call != new_do_not_call:
                    volunteer.do_not_call = new_do_not_call
                    updates.append("do_not_call")

                new_do_not_contact = bool(row.get("npsp__Do_Not_Contact__c"))
                if volunteer.do_not_contact != new_do_not_contact:
                    volunteer.do_not_contact = new_do_not_contact
                    updates.append("do_not_contact")

                new_email_opt_out = bool(row.get("HasOptedOutOfEmail"))
                if volunteer.email_opt_out != new_email_opt_out:
                    volunteer.email_opt_out = new_email_opt_out
                    updates.append("email_opt_out")

                # Handle email bounce date
                new_bounce_date = parse_date(row.get("EmailBouncedDate"))
                if volunteer.email_bounced_date != new_bounce_date:
                    volunteer.email_bounced_date = new_bounce_date
                    updates.append("email_bounced_date")

                # Handle emails
                email_fields = {
                    "npe01__WorkEmail__c": ContactTypeEnum.professional,
                    "Email": ContactTypeEnum.personal,
                    "npe01__HomeEmail__c": ContactTypeEnum.personal,
                    "npe01__AlternateEmail__c": ContactTypeEnum.personal,
                }

                # Get preferred email type
                preferred_email = row.get("npe01__Preferred_Email__c", "").lower()
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
                            (preferred_email == "work" and email_field == "npe01__WorkEmail__c")
                            or (preferred_email == "personal" and email_field in ["npe01__HomeEmail__c", "Email"])
                            or (preferred_email == "alternate" and email_field == "npe01__AlternateEmail__c")
                        ):
                            is_primary = True
                    elif email_field == "Email":  # Default to standard Email field as primary if no preference
                        is_primary = True

                    # Check if email already exists
                    email = Email.query.filter_by(contact_id=volunteer.id, email=email_value).first()

                    if not email:
                        email = Email(contact_id=volunteer.id, email=email_value, type=email_type, primary=is_primary)
                        db.session.add(email)
                        email_changes = True
                    else:
                        # Update existing email type and primary status if changed
                        if email.type != email_type:
                            email.type = email_type
                            email_changes = True
                        if is_primary and not email.primary:
                            # Set all other emails to non-primary
                            Email.query.filter_by(contact_id=volunteer.id, primary=True).update({"primary": False})
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
                preferred_phone = row.get("npe01__PreferredPhone__c", "").lower()
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
                            (preferred_phone == "work" and phone_field in ["npe01__WorkPhone__c", "Phone"])
                            or (preferred_phone == "home" and phone_field == "HomePhone")
                            or (preferred_phone == "mobile" and phone_field == "MobilePhone")
                        ):
                            is_primary = True
                    elif phone_field == "Phone":  # Default to business Phone as primary if no preference
                        is_primary = True

                    # Check if phone already exists
                    phone = Phone.query.filter_by(contact_id=volunteer.id, number=phone_value).first()

                    if not phone:
                        phone = Phone(contact_id=volunteer.id, number=phone_value, type=phone_type, primary=is_primary)
                        db.session.add(phone)
                        phone_changes = True
                    else:
                        # Update existing phone type and primary status if changed
                        if phone.type != phone_type:
                            phone.type = phone_type
                            phone_changes = True
                        if is_primary and not phone.primary:
                            # Set all other phones to non-primary
                            Phone.query.filter_by(contact_id=volunteer.id, primary=True).update({"primary": False})
                            phone.primary = True
                            phone_changes = True

                if phone_changes:
                    updates.append("phones")

                # Handle addresses
                mailing_address = row.get("MailingAddress", {})
                if isinstance(mailing_address, dict):
                    # Find or create mailing address
                    mailing = next((addr for addr in volunteer.addresses if addr.type == ContactTypeEnum.personal and addr.primary), None)
                    if not mailing:
                        mailing = Address(contact_id=volunteer.id, type=ContactTypeEnum.personal, primary=True)
                        volunteer.addresses.append(mailing)
                        updates.append("mailing_address_created")

                    # Update mailing address fields
                    if mailing.address_line1 != mailing_address.get("street", ""):
                        mailing.address_line1 = mailing_address.get("street", "")
                        updates.append("mailing_street")
                    if mailing.city != mailing_address.get("city", ""):
                        mailing.city = mailing_address.get("city", "")
                        updates.append("mailing_city")
                    if mailing.state != mailing_address.get("state", ""):
                        mailing.state = mailing_address.get("state", "")
                        updates.append("mailing_state")
                    if mailing.zip_code != mailing_address.get("postalCode", ""):
                        mailing.zip_code = mailing_address.get("postalCode", "")
                        updates.append("mailing_zip")
                    if mailing.country != mailing_address.get("country", ""):
                        mailing.country = mailing_address.get("country", "")
                        updates.append("mailing_country")

                # Handle work address if present
                work_address = row.get("npe01__Work_Address__c", "")
                if work_address:
                    work = next((addr for addr in volunteer.addresses if addr.type == ContactTypeEnum.professional), None)
                    if not work:
                        work = Address(contact_id=volunteer.id, type=ContactTypeEnum.professional)
                        volunteer.addresses.append(work)
                        updates.append("work_address_created")

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
                        updates.append("work_address_updated")
                    except Exception as e:
                        print(f"Error parsing work address for {volunteer.first_name} {volunteer.last_name}: {str(e)}")

                # Set address types based on primary/secondary preferences
                primary_type = (row.get("npe01__Primary_Address_Type__c") or "").lower()
                secondary_type = (row.get("npe01__Secondary_Address_Type__c") or "").lower()

                for addr in volunteer.addresses:
                    is_home = addr.type == ContactTypeEnum.personal
                    is_work = addr.type == ContactTypeEnum.professional

                    # Set primary based on preference
                    if (primary_type == "home" and is_home) or (primary_type == "work" and is_work):
                        addr.primary = True
                    elif (secondary_type == "home" and is_home) or (secondary_type == "work" and is_work):
                        addr.primary = False

                # Handle Connector data
                connector_data = {
                    "active_subscription": (row.get("Connector_Active_Subscription__c") or "").strip().upper() or "NONE",
                    "active_subscription_name": (row.get("Connector_Active_Subscription_Name__c") or "").strip(),
                    "affiliations": (row.get("Connector_Affiliations__c") or "").strip(),
                    "industry": (row.get("Connector_Industry__c") or "").strip(),
                    "joining_date": (row.get("Connector_Joining_Date__c") or "").strip(),
                    "last_login_datetime": (row.get("Connector_Last_Login_Date_Time__c") or "").strip(),
                    "last_update_date": parse_date(row.get("Connector_Last_Update_Date__c")),
                    "profile_link": (row.get("Connector_Profile_Link__c") or "").strip(),
                    "role": (row.get("Connector_Role__c") or "").strip(),
                    "signup_role": (row.get("Connector_SignUp_Role__c") or "").strip(),
                    "user_auth_id": (row.get("Connector_User_ID__c") or "").strip(),
                }

                # Create or update connector data
                if not volunteer.connector:
                    volunteer.connector = ConnectorData(volunteer_id=volunteer.id)
                    updates.append("connector_created")

                # Update connector fields if they exist in Salesforce data
                if connector_data["active_subscription"] in [e.name for e in ConnectorSubscriptionEnum]:
                    if volunteer.connector.active_subscription != ConnectorSubscriptionEnum[connector_data["active_subscription"]]:
                        volunteer.connector.active_subscription = ConnectorSubscriptionEnum[connector_data["active_subscription"]]
                        updates.append("connector_subscription")

                for field, value in connector_data.items():
                    if field != "active_subscription" and value:  # Skip active_subscription as it's handled above
                        current_value = getattr(volunteer.connector, field)
                        if current_value != value:
                            setattr(volunteer.connector, field, value)
                            updates.append(f"connector_{field}")

                success_count += 1
                created_count = created_count + 1 if is_new else created_count
                updated_count = updated_count + 1 if not is_new and updates else updated_count

            except Exception as e:
                error_count += 1
                error_detail = {"name": f"{row.get('FirstName', '')} {row.get('LastName', '')}", "salesforce_id": row.get("Id", ""), "error": str(e)}
                errors.append(error_detail)
                db.session.rollback()

        # Commit all successful changes
        try:
            db.session.commit()
            print(f"\nImport complete - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")
            if errors:
                print(f"\nErrors encountered: {len(errors)}")
                for error in errors[:5]:  # Show only first 5 errors
                    print(f"- {error['name']}: {error['error']}")
                if len(errors) > 5:
                    print(f"... and {len(errors) - 5} more errors")

            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {success_count} volunteers (Created: {created_count}, Updated: {updated_count}) with {error_count} errors",
                }
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": f"Database commit error: {str(e)}"}), 500

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/import-from-salesforce-optimized", methods=["POST"])
@login_required
def import_volunteers_from_salesforce_optimized():
    """
    Optimized volunteer import from Salesforce using the new framework.

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures

    This is Phase 1 of the two-phase volunteer import pipeline:
    - Phase 1: Import volunteer data without organization affiliations
    - Phase 2: Import volunteer-organization affiliations separately

    Returns:
        JSON response with import statistics and error details
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        print("Starting optimized volunteer import from Salesforce...")
        print("Expected: ~10,000+ volunteers to process")
        print("Progress updates: Every 1,000 volunteers")
        print("Batch size: 500 volunteers per batch")
        print("Commit frequency: Every 10 batches (~5,000 volunteers)")

        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=500,  # Process 500 records at a time
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=10,  # Commit every 10 batches
        )

        # Initialize the Salesforce importer
        importer = SalesforceImporter(config)

        # Define the Salesforce query for volunteers
        volunteer_query = """
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
               Connector_User_ID__c
        FROM Contact
        WHERE Contact_Type__c = 'Volunteer' OR Contact_Type__c = ''
        ORDER BY LastName ASC, FirstName ASC
        """

        # Custom progress callback for detailed updates every 1k volunteers
        def progress_callback(processed_count, total_count, message):
            if processed_count % 1000 == 0 and processed_count > 0:
                percentage = (processed_count / total_count) * 100
                print(f"Progress: {processed_count:,}/{total_count:,} volunteers ({percentage:.1f}%) - {message}")

        # Execute the import using the optimized framework
        result = importer.import_data(
            query=volunteer_query,
            process_func=process_volunteer_record_optimized,
            validation_func=validate_volunteer_record,
            progress_callback=progress_callback,
        )

        # Prepare response message
        if result.success:
            message = f"Successfully processed {result.success_count:,} volunteers with {result.error_count:,} errors"
            if result.warnings:
                message += f" ({len(result.warnings)} warnings)"
        else:
            message = f"Import completed with {result.error_count:,} errors out of {result.total_records:,} records"

        return jsonify(
            {
                "success": result.success,
                "message": message,
                "statistics": {
                    "total_records": result.total_records,
                    "processed_count": result.processed_count,
                    "success_count": result.success_count,
                    "error_count": result.error_count,
                    "skipped_count": result.skipped_count,
                    "duration_seconds": result.duration_seconds,
                },
                "errors": result.errors[:10],  # Limit to first 10 errors
                "warnings": result.warnings[:10],  # Limit to first 10 warnings
            }
        )

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/import-affiliations-optimized", methods=["POST"])
@login_required
def import_volunteer_affiliations_optimized():
    """
    Optimized volunteer-organization affiliations import from Salesforce.

    This is Phase 2 of the two-phase volunteer import pipeline:
    - Phase 1: Import volunteer data (run first)
    - Phase 2: Import volunteer-organization affiliations (run second)

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures

    Returns:
        JSON response with import statistics and error details
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        print("Starting optimized volunteer affiliations import from Salesforce...")
        print("Expected: ~5,000+ affiliations to process")
        print("Progress updates: Every 500 affiliations")
        print("Batch size: 200 affiliations per batch")
        print("Commit frequency: Every 5 batches (~1,000 affiliations)")

        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=200,  # Process 200 records at a time (smaller due to complexity)
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=5,  # Commit every 5 batches
        )

        # Initialize the Salesforce importer
        importer = SalesforceImporter(config)

        # Define the Salesforce query for affiliations
        affiliation_query = """
        SELECT Id, Name, npe5__Organization__c, npe5__Contact__c,
               npe5__Role__c, npe5__Primary__c, npe5__Status__c,
               npe5__StartDate__c, npe5__EndDate__c
        FROM npe5__Affiliation__c
        WHERE npe5__Contact__c IN (
            SELECT Id FROM Contact
            WHERE Contact_Type__c = 'Volunteer' OR Contact_Type__c = ''
        )
        ORDER BY npe5__Contact__c ASC
        """

        # Custom progress callback for detailed updates every 500 affiliations
        def progress_callback(processed_count, total_count, message):
            if processed_count % 500 == 0 and processed_count > 0:
                percentage = (processed_count / total_count) * 100
                print(f"Progress: {processed_count:,}/{total_count:,} affiliations ({percentage:.1f}%) - {message}")

        # Execute the import using the optimized framework
        result = importer.import_data(
            query=affiliation_query,
            process_func=process_affiliation_record_optimized,
            validation_func=validate_affiliation_record,
            progress_callback=progress_callback,
        )

        # Prepare response message
        if result.success:
            message = f"Successfully processed {result.success_count:,} affiliations with {result.error_count:,} errors"
            if result.warnings:
                message += f" ({len(result.warnings)} warnings)"
        else:
            message = f"Import completed with {result.error_count:,} errors out of {result.total_records:,} records"

        return jsonify(
            {
                "success": result.success,
                "message": message,
                "statistics": {
                    "total_records": result.total_records,
                    "processed_count": result.processed_count,
                    "success_count": result.success_count,
                    "error_count": result.error_count,
                    "skipped_count": result.skipped_count,
                    "duration_seconds": result.duration_seconds,
                },
                "errors": result.errors[:10],  # Limit to first 10 errors
                "warnings": result.warnings[:10],  # Limit to first 10 warnings
            }
        )

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/import-pipeline-status", methods=["GET"])
@login_required
def get_volunteer_import_pipeline_status():
    """
    Get the status of the volunteer import pipeline.

    Provides comprehensive analysis of volunteer import status including:
    - Total volunteers in database
    - Volunteers with organization affiliations
    - Volunteers without organization affiliations
    - Missing organizations analysis
    - Recommendations for next steps

    Returns:
        JSON response with pipeline status and recommendations
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Get basic statistics
        total_volunteers = Volunteer.query.count()
        volunteers_with_affiliations = db.session.query(Volunteer).join(VolunteerOrganization).distinct().count()
        volunteers_without_affiliations = total_volunteers - volunteers_with_affiliations

        # Get affiliation statistics
        total_affiliations = VolunteerOrganization.query.count()
        active_affiliations = VolunteerOrganization.query.filter_by(status="Active").count()

        # Get organization statistics
        total_organizations = Organization.query.count()

        # Calculate completion percentages
        affiliation_completion = (volunteers_with_affiliations / total_volunteers * 100) if total_volunteers > 0 else 0

        # Generate recommendations
        recommendations = []

        if volunteers_without_affiliations > 0:
            recommendations.append(f"Run Phase 2 (affiliations import) to assign {volunteers_without_affiliations:,} volunteers to organizations")

        if total_volunteers == 0:
            recommendations.append("Run Phase 1 (volunteer import) to import volunteer data from Salesforce")

        if total_organizations == 0:
            recommendations.append("Import organizations before running Phase 2 (affiliations import)")

        # Prepare response
        status_data = {
            "pipeline_status": {
                "total_volunteers": total_volunteers,
                "volunteers_with_affiliations": volunteers_with_affiliations,
                "volunteers_without_affiliations": volunteers_without_affiliations,
                "affiliation_completion_percentage": round(affiliation_completion, 1),
                "total_affiliations": total_affiliations,
                "active_affiliations": active_affiliations,
                "total_organizations": total_organizations,
            },
            "recommendations": recommendations,
            "next_steps": [
                "1. Run Phase 1: Import volunteer data from Salesforce",
                "2. Run Phase 2: Import volunteer-organization affiliations",
                "3. Monitor the pipeline status for completion",
            ],
        }

        return jsonify({"success": True, "status": status_data})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/toggle-exclude-reports/<int:id>", methods=["POST"])
@login_required
def toggle_exclude_reports(id):
    """Toggle the exclude_from_reports field for a volunteer - Admin only"""
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin access required"}), 403

    try:
        volunteer = db.session.get(Volunteer, id)
        if not volunteer:
            return jsonify({"success": False, "message": "Volunteer not found"}), 404

        # Get the new value from the request
        data = request.get_json()
        exclude_from_reports = data.get("exclude_from_reports", False)

        # Update the field
        volunteer.exclude_from_reports = exclude_from_reports
        db.session.commit()

        status = "excluded from" if exclude_from_reports else "included in"
        return jsonify({"success": True, "message": f"Volunteer {status} reports successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@volunteers_bp.route("/volunteers/update-local-statuses", methods=["POST"])
@login_required
def update_local_statuses():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        print("Starting local status update for all volunteers...")
        updated_count = 0
        error_count = 0

        # Get all volunteers
        volunteers = Volunteer.query.all()

        for volunteer in volunteers:
            try:
                new_status = volunteer.calculate_local_status()
                if volunteer.local_status != new_status:
                    volunteer.local_status = new_status
                    volunteer.local_status_last_updated = datetime.utcnow()
                    updated_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error updating local status for {volunteer.first_name} {volunteer.last_name}: {str(e)}")

        db.session.commit()
        return jsonify({"success": True, "message": f"Updated {updated_count} volunteer statuses with {error_count} errors"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating local statuses: {str(e)}"}), 500


@volunteers_bp.route("/volunteers/<int:volunteer_id>/organizations")
@login_required
def get_organizations_json(volunteer_id):
    """Get organizations data for a specific volunteer as JSON"""
    try:
        volunteer = Volunteer.query.get_or_404(volunteer_id)
        organizations_data = []

        for vol_org in volunteer.volunteer_organizations:
            org_data = {
                "organization": {"id": vol_org.organization.id, "name": vol_org.organization.name},
                "role": vol_org.role,
                "status": vol_org.status,
                "is_primary": vol_org.is_primary,
            }
            organizations_data.append(org_data)

        return jsonify(organizations_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

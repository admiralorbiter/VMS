import hashlib
from datetime import datetime, timezone

import pandas as pd
from flask import current_app
from sqlalchemy import func

from models import db
from models.district_model import District
from models.school_model import School
from routes.reports.common import DISTRICT_MAPPING


def safe_str(value):
    """Safely convert a value to string, handling NaN and None"""
    if pd.isna(value) or value is None:
        return ""
    return str(value)


def get_or_create_district(name):
    """
    Get or create district by name, attempting to match aliases and standard names
    from DISTRICT_MAPPING to avoid creating duplicates.
    """
    if pd.isna(name) or not name or str(name).strip() == "":
        effective_name = "Unknown District"
        target_salesforce_id = None
    else:
        effective_name = str(name).strip()
        target_salesforce_id = None

        # --- Attempt to map the input name to a canonical Salesforce ID ---
        name_lower = effective_name.lower()
        for sf_id, mapping_info in DISTRICT_MAPPING.items():
            # Check exact canonical name
            if mapping_info["name"].lower() == name_lower:
                target_salesforce_id = sf_id
                effective_name = mapping_info["name"]  # Use the canonical name
                break
            # Check aliases
            if "aliases" in mapping_info:
                for alias in mapping_info["aliases"]:
                    if alias.lower() == name_lower:
                        target_salesforce_id = sf_id
                        effective_name = mapping_info["name"]  # Use the canonical name
                        break
            if target_salesforce_id:  # Stop searching if mapped
                break
        # --- End Mapping Attempt ---

    district = None
    # If we mapped to a Salesforce ID, prioritize finding the district by that ID
    if target_salesforce_id:
        district = District.query.filter_by(salesforce_id=target_salesforce_id).first()

    # If not found by Salesforce ID (or no mapping occurred), try finding by the effective name (case-insensitive)
    if not district:
        district = District.query.filter(
            func.lower(District.name) == func.lower(effective_name)
        ).first()

    # Only create a new district if absolutely not found and it's not 'Unknown District'
    if not district and effective_name != "Unknown District":
        # Only log when creating new districts (this could be worth knowing about)
        print(f"INFO: Creating new district: '{effective_name}'")
        # We create it without a Salesforce ID because we couldn't map it
        district = District(name=effective_name)
        db.session.add(district)
        db.session.flush()  # Flush to assign an ID

    # Handle 'Unknown District' case - find or create the specific 'Unknown' record
    elif not district and effective_name == "Unknown District":
        district = District.query.filter(
            func.lower(District.name) == "unknown district"
        ).first()
        if not district:
            # Only log when creating Unknown District for the first time
            print(f"INFO: Creating 'Unknown District'")
            district = District(name="Unknown District")
            db.session.add(district)
            db.session.flush()

    return district


def generate_school_id(name):
    """Generate a unique ID for virtual schools that matches Salesforce length"""
    if pd.isna(name) or not name:
        name = "Unknown School"

    # Ensure name is a string
    name = str(name).strip()

    timestamp = datetime.now(timezone.utc).strftime("%y%m%d")
    name_hash = hashlib.sha256(name.lower().encode()).hexdigest()[:8]
    base_id = f"VRT{timestamp}{name_hash}"

    # Ensure exactly 18 characters
    base_id = base_id[:18].ljust(18, "0")

    # Check if ID exists and append counter if needed
    counter = 1
    new_id = base_id
    while School.query.filter_by(id=new_id).first():
        counter_str = str(counter).zfill(2)
        new_id = base_id[:-2] + counter_str
        counter += 1

    return new_id


def get_or_create_school(name, district=None):
    """Get or create school by name with improved district handling"""
    try:
        if pd.isna(name) or not name:
            return None

        # Clean and standardize the school name
        name = str(name).strip()
        if not name:
            return None

        # Try to find existing school
        school = School.query.filter(
            func.lower(School.name) == func.lower(name)
        ).first()

        if not school:
            try:
                school = School(
                    id=generate_school_id(name),
                    name=name,
                    district_id=district.id if district else None,
                    normalized_name=name.lower(),
                    salesforce_district_id=(
                        district.salesforce_id
                        if district and district.salesforce_id
                        else None
                    ),
                )
                db.session.add(school)
                db.session.flush()
            except Exception as e:
                current_app.logger.error(f"Error creating school {name}: {str(e)}")
                return None

        return school

    except Exception as e:
        current_app.logger.error(f"Error in get_or_create_school: {str(e)}")
        return None

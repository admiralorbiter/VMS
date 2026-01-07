"""
Production script to fix race/ethnicity mapping for existing volunteers.

This script:
1. Finds volunteers with incorrect race/ethnicity values (Unknown, None, or Other when should be Other POC)
2. Checks their Salesforce records for actual race/ethnicity values
3. Updates the database with the correct values using the fixed mapping

This is a one-time fix script for production use.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from simple_salesforce import Salesforce

from app import create_app
from config import Config
from models import db
from models.contact import RaceEthnicityEnum
from models.volunteer import Volunteer


def map_race_ethnicity(race_ethnicity_str, race_ethnicity_map):
    """Map a Salesforce race/ethnicity string to enum value - same logic as import"""
    if not race_ethnicity_str or race_ethnicity_str == "None":
        return None

    # Clean the string
    cleaned_str = race_ethnicity_str.strip()
    if "AggregateResult" in cleaned_str:
        cleaned_str = cleaned_str.replace("AggregateResult", "").strip()

    # Try exact match first
    enum_value = race_ethnicity_map.get(cleaned_str)

    # If no exact match, try case-insensitive match
    if not enum_value:
        cleaned_lower = cleaned_str.lower()
        for sf_value, enum_name in race_ethnicity_map.items():
            if sf_value.lower() == cleaned_lower:
                enum_value = enum_name
                break

    # If still no match, try partial matching
    if not enum_value:
        cleaned_lower = cleaned_str.lower()
        if (
            "hispanic" in cleaned_lower
            or "latino" in cleaned_lower
            or "latina" in cleaned_lower
        ):
            enum_value = "hispanic"
        elif "black" in cleaned_lower or "african american" in cleaned_lower:
            enum_value = "black"
        elif "white" in cleaned_lower or "caucasian" in cleaned_lower:
            enum_value = "white"
        elif "asian" in cleaned_lower:
            enum_value = "asian"
        elif "pacific islander" in cleaned_lower or "hawaiian" in cleaned_lower:
            enum_value = "native_hawaiian"
        elif (
            "native american" in cleaned_lower
            or "alaska native" in cleaned_lower
            or "first nation" in cleaned_lower
            or "american indian" in cleaned_lower
        ):
            enum_value = "american_indian"
        elif (
            "multi" in cleaned_lower
            or "bi-racial" in cleaned_lower
            or "biracial" in cleaned_lower
        ):
            enum_value = "multi_racial"
        elif "two or more" in cleaned_lower:
            enum_value = "two_or_more"
        elif "prefer not" in cleaned_lower or "not to say" in cleaned_lower:
            enum_value = "prefer_not_to_say"
        elif "other poc" in cleaned_lower or "otherpoc" in cleaned_lower:
            enum_value = "other_poc"
        elif "other" in cleaned_lower:
            enum_value = "other"

    return enum_value


def main():
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("Production Race/Ethnicity Fix Script")
        print("=" * 80)
        print()

        # Define the mapping (same as in routes/volunteers/routes.py)
        race_ethnicity_map = {
            "Hispanic American/Latino": "hispanic",
            "Hispanic or Latino": "hispanic",
            "Hispanic": "hispanic",
            "Latino": "hispanic",
            "Latina": "hispanic",
            "Black": "black",
            "Black/African American": "black",
            "African American": "black",
            "Black or African American": "black",
            "White": "white",
            "White/Caucasian/European American": "white",
            "Caucasian": "white",
            "European American": "white",
            "Asian": "asian",
            "Asian American": "asian",
            "Asian American/Pacific Islander": "asian",
            "Pacific Islander": "native_hawaiian",
            "Native Hawaiian": "native_hawaiian",
            "Native Hawaiian or Other Pacific Islander": "native_hawaiian",
            "American Indian or Alaska Native": "american_indian",
            "Native American": "american_indian",
            "Alaska Native": "american_indian",
            "Native American/Alaska Native/First Nation": "american_indian",
            "First Nation": "american_indian",
            "Bi-racial": "bi_racial",
            "Multi-racial": "multi_racial",
            "Bi-racial/Multi-racial/Multicultural": "multi_racial",
            "Two or More Races": "two_or_more",
            "Two or more": "two_or_more",
            "Other": "other",
            "Other POC": "other_poc",
            "Prefer not to answer": "prefer_not_to_say",
            "Prefer not to say": "prefer_not_to_say",
        }

        valid_enum_names = [e.name for e in RaceEthnicityEnum]

        # Find volunteers that need fixing:
        # 1. Those with Unknown or None race/ethnicity
        # 2. Those with "Other" that might be "Other POC"
        unknown_volunteers = Volunteer.query.filter(
            db.or_(
                Volunteer.race_ethnicity == RaceEthnicityEnum.unknown,
                Volunteer.race_ethnicity.is_(None),
            ),
            Volunteer.salesforce_individual_id.isnot(None),
        ).all()

        other_volunteers = Volunteer.query.filter(
            Volunteer.race_ethnicity == RaceEthnicityEnum.other,
            Volunteer.salesforce_individual_id.isnot(None),
        ).all()

        print(
            f"Found {len(unknown_volunteers)} volunteers with 'Unknown' or None race/ethnicity"
        )
        print(f"Found {len(other_volunteers)} volunteers with 'Other' race/ethnicity")
        print(f"Total to check: {len(unknown_volunteers) + len(other_volunteers)}")
        print()

        if not unknown_volunteers and not other_volunteers:
            print("No volunteers to check.")
            return

        try:
            # Connect to Salesforce
            print("Connecting to Salesforce...")
            sf = Salesforce(
                username=Config.SF_USERNAME,
                password=Config.SF_PASSWORD,
                security_token=Config.SF_SECURITY_TOKEN,
                domain="login",
            )
            print("Connected successfully!")
            print()

            # Process in batches
            batch_size = 100
            updated_unknown = 0
            updated_other_poc = 0
            not_found_count = 0
            no_value_count = 0
            unmapped_count = 0

            all_volunteers = list(unknown_volunteers) + list(other_volunteers)

            for i in range(0, len(all_volunteers), batch_size):
                batch = all_volunteers[i : i + batch_size]
                sf_ids = [
                    v.salesforce_individual_id
                    for v in batch
                    if v.salesforce_individual_id
                ]

                if not sf_ids:
                    continue

                # Query Salesforce for this batch
                sf_query = f"""
                SELECT Id, FirstName, LastName, Racial_Ethnic_Background__c
                FROM Contact
                WHERE Id IN ({','.join([f"'{id}'" for id in sf_ids])})
                """

                try:
                    results = sf.query_all(sf_query)
                    sf_records = {r["Id"]: r for r in results["records"]}

                    # Update each volunteer in the batch
                    for volunteer in batch:
                        if not volunteer.salesforce_individual_id:
                            continue

                        sf_record = sf_records.get(volunteer.salesforce_individual_id)

                        if not sf_record:
                            not_found_count += 1
                            continue

                        sf_value_raw = sf_record.get("Racial_Ethnic_Background__c")
                        if sf_value_raw is None:
                            no_value_count += 1
                            continue

                        sf_value = str(sf_value_raw).strip()

                        if not sf_value or sf_value == "None":
                            no_value_count += 1
                            continue

                        # Map the value
                        enum_value = map_race_ethnicity(sf_value, race_ethnicity_map)

                        if enum_value and enum_value in valid_enum_names:
                            # Check if update is needed
                            current_value = (
                                volunteer.race_ethnicity.name
                                if volunteer.race_ethnicity
                                else None
                            )

                            if current_value != enum_value:
                                volunteer.race_ethnicity = RaceEthnicityEnum[enum_value]

                                if current_value in (None, "unknown"):
                                    updated_unknown += 1
                                elif (
                                    current_value == "other"
                                    and enum_value == "other_poc"
                                ):
                                    updated_other_poc += 1

                                if (updated_unknown + updated_other_poc) % 50 == 0:
                                    print(
                                        f"  Updated {updated_unknown + updated_other_poc} volunteers so far..."
                                    )
                                    db.session.commit()
                                elif (updated_unknown + updated_other_poc) % 10 == 0:
                                    print(
                                        f"  Updated {updated_unknown + updated_other_poc} volunteers..."
                                    )
                        else:
                            unmapped_count += 1
                            print(
                                f"  Warning: Unmapped value '{sf_value}' for {volunteer.first_name} {volunteer.last_name}"
                            )

                except Exception as e:
                    print(f"  Error processing batch {i//batch_size + 1}: {e}")
                    continue

            # Commit any remaining updates
            if (updated_unknown + updated_other_poc) % 50 != 0:
                db.session.commit()

            print()
            print("=" * 80)
            print("Update Summary")
            print("=" * 80)
            print(f"  Updated from Unknown/None: {updated_unknown} volunteers")
            print(f"  Updated from Other to Other POC: {updated_other_poc} volunteers")
            print(f"  Total updated: {updated_unknown + updated_other_poc} volunteers")
            print(f"  Not found in Salesforce: {not_found_count} volunteers")
            print(
                f"  No race/ethnicity value in Salesforce: {no_value_count} volunteers"
            )
            print(f"  Unmapped values: {unmapped_count} volunteers")
            print(f"  Total processed: {len(all_volunteers)} volunteers")
            print()

            if updated_unknown + updated_other_poc > 0:
                print("[SUCCESS] Database updated successfully!")
                print()
                print(
                    "Volunteers with race/ethnicity data in Salesforce are now correctly mapped."
                )
            else:
                print("No updates were needed.")

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
            db.session.rollback()


if __name__ == "__main__":
    main()

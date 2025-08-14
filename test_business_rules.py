#!/usr/bin/env python3
"""
Test script to debug business rule validation and check Salesforce field availability.
"""

import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_salesforce_fields():
    """Test what fields are available in Salesforce data."""
    try:
        from app import app
        from utils.salesforce_client import SalesforceClient

        with app.app_context():
            client = SalesforceClient()

            # Get volunteer sample to see available fields
            print("Getting volunteer sample data...")
            volunteers = client.get_volunteer_sample(5)

            if volunteers:
                print(f"\nFound {len(volunteers)} volunteer records")
                print("\nAvailable fields in first volunteer record:")
                for field, value in volunteers[0].items():
                    print(f"  {field}: {value}")

                # Check specific fields we're looking for in business rules
                print("\nChecking business rule fields:")
                business_rule_fields = [
                    "Status",
                    "Available_From__c",
                    "Available_Until__c",
                    "Volunteer_Skills__c",
                ]

                for field in business_rule_fields:
                    if field in volunteers[0]:
                        print(f"  ✅ {field}: {volunteers[0][field]}")
                    else:
                        print(f"  ❌ {field}: Not found")

            else:
                print("No volunteer data found")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


def test_business_rule_config():
    """Test business rule configuration loading."""
    try:
        from app import app
        from config.validation import get_config_section

        with app.app_context():
            business_config = get_config_section("business_rules")
            print("\nBusiness rule configuration:")
            print(
                f"  Validation settings: {business_config.get('validation_settings', {})}"
            )

            volunteer_rules = business_config.get("business_rules", {}).get(
                "volunteer", {}
            )
            print(f"\nVolunteer business rules:")
            for rule_name, rule_config in volunteer_rules.items():
                print(
                    f"  {rule_name}: {rule_config.get('type')} - {rule_config.get('description')}"
                )

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("Testing Salesforce field availability and business rule configuration...")
    test_salesforce_fields()
    test_business_rule_config()
    print("\nTest completed.")

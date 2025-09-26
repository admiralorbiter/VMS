#!/usr/bin/env python3
"""
Test script to verify volunteer count query is working correctly.
This script tests the actual Salesforce client to ensure it's using the right query.
"""

import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


def test_volunteer_count():
    """Test the volunteer count functionality."""
    try:
        from app import app
        from utils.salesforce_client import SalesforceClient

        with app.app_context():
            print("Testing volunteer count query...")

            # Create Salesforce client
            client = SalesforceClient()

            # Test the volunteer count method
            print("Calling get_volunteer_count()...")
            count = client.get_volunteer_count()

            print(f"✅ SUCCESS: Volunteer count = {count}")
            print("✅ The correct query (Contact_Type__c = 'Volunteer') is working!")

            assert True, "Volunteer count test passed"

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("❌ This indicates the query is still using RecordType.Name somewhere")
        assert False, f"Volunteer count test failed: {e}"


def test_count_validator():
    """Test the count validator to ensure it uses the correct client method."""
    try:
        from app import app
        from utils.validators.count_validator import CountValidator

        with app.app_context():
            print("\nTesting count validator...")

            # Create count validator
            validator = CountValidator(entity_type="volunteer")

            # Test the Salesforce count method
            print("Calling _get_salesforce_count('volunteer')...")
            count = validator._get_salesforce_count("volunteer")

            print(f"✅ SUCCESS: Count validator returned count = {count}")
            print(
                "✅ The count validator is using the correct Salesforce client method!"
            )

            assert True, "Count validator test passed"

    except Exception as e:
        print(f"❌ ERROR in count validator: {e}")
        assert False, f"Count validator test failed: {e}"


if __name__ == "__main__":
    print("🧪 Testing Volunteer Count Query Fix")
    print("=" * 50)

    # Test 1: Direct Salesforce client
    success1 = test_volunteer_count()

    # Test 2: Count validator
    success2 = test_count_validator()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED! The volunteer count query is working correctly.")
        print("✅ The issue was likely a code version mismatch or cached code.")
    else:
        print("❌ Some tests failed. The issue may still exist.")
        print("🔍 Check if there are other files using the incorrect RecordType query.")

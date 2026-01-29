"""
API Health Check Script (Simple)
================================

This script performs a basic health check on the Volunteer Signup API.
It is designed to be a lightweight connectivity test that can be run
manually or by automated systems to verify that the API endpoint
is reachable and returning valid JSON.

Usage:
    python scripts/check_api_health.py

Dependencies:
    - requests

Exit Codes:
    0: Success (API is UP)
    1: Failure (API is DOWN or unreachable)
"""

import sys

import requests


def check_api_health(url):
    """
    Check the health of the given URL.

    Performs a GET request to the specified URL and verifies:
    1. The status code is 200 OK.
    2. The response content type is JSON.

    Args:
        url (str): The full URL of the API endpoint to check.

    Returns:
        None: Prints status to stdout and exits with code 1 on failure.
    """
    print(f"Checking health of: {url}")
    try:
        # Perform HTTP GET request with a 10-second timeout
        response = requests.get(url, timeout=10)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ API is UP and returning 200 OK.")
            try:
                # Attempt to parse response as JSON to ensure validity
                data = response.json()
                # Print a snippet of the response for verification
                print(f"Response (first 100 chars): {str(data)[:100]}...")
            except ValueError:
                print("⚠️  API returned 200 but response is NOT JSON.")
        else:
            print(f"❌ API returned error status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        # Handle connection errors (e.g., DNS failure, timeout, connection refused)
        print(f"❌ API is DOWN or unreachable.")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # The production API endpoint URL
    URL = "https://voluntold-prepkc.pythonanywhere.com/events/volunteer_signup_api"
    check_api_health(URL)

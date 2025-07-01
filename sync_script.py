import requests
import os

# Replace with your actual PythonAnywhere URL for the Flask app
BASE_URL = 'https://polaris-jlane.pythonanywhere.com'
TOKEN = 'youcantrybutyoucantgetthroughthiswalloftext'

# Add debug print and token validation
if TOKEN is None:
    raise ValueError("TOKEN environment variable is not set")

def trigger_sync():
    endpoints = [
        ('/sync_recent_salesforce_data', 'Full Data Sync')
    ]

    for endpoint, name in endpoints:
        try:
            print(f"\nStarting {name} sync...")
            print(f"Using token: {TOKEN[:5]}...") # Print first 5 chars for verification
            
            response = requests.post(f"{BASE_URL}{endpoint}?token={TOKEN}")
            response.raise_for_status()
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")  # Print raw response
            
            try:
                json_response = response.json()
                print(f"{name} sync completed successfully: {json_response}")
            except ValueError as json_err:
                print(f"Could not parse JSON response: {json_err}")
                print(f"Raw response was: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"{name} sync failed: {e}")

if __name__ == '__main__':
    trigger_sync()

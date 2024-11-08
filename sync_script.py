import requests
import os

# Replace with your actual PythonAnywhere URL for the Flask app
URL = 'https://polaris-jlane.pythonanywhere.com/sync_upcoming_events'
TOKEN ='youcantrybutyoucantgetthroughthiswalloftext'

# Add debug print and token validation
if TOKEN is None:
    raise ValueError("TOKEN environment variable is not set")

def trigger_sync():
    try:
        print(f"Using token: {TOKEN[:5]}...") # Print first 5 chars for verification
        response = requests.post(f"{URL}?token={TOKEN}")
        response.raise_for_status()
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")  # Print raw response
        try:
            json_response = response.json()
            print(f"Sync completed successfully: {json_response}")
        except ValueError as json_err:
            print(f"Could not parse JSON response: {json_err}")
            print(f"Raw response was: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Sync failed: {e}")

if __name__ == '__main__':
    trigger_sync()

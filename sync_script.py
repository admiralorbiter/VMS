import requests
import os

# Replace with your actual PythonAnywhere URL for the Flask app
URL = 'https://jlane.pythonanywhere.com/sync_upcoming_events'
TOKEN = os.getenv('SYNC_AUTH_TOKEN')  # Alternatively, store it directly in this script

def trigger_sync():
    try:
        # Send the token as a query parameter
        response = requests.post(f"{URL}?token={TOKEN}")
        response.raise_for_status()
        print(f"Sync completed successfully: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Sync failed: {e}")

if __name__ == '__main__':
    trigger_sync()

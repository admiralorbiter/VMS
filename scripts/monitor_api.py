"""
Robust API Monitor with Email Alerting
======================================

This script monitors the health of the Volunteer Signup API and sends
email alerts via Mailjet if the API is down or malfunctioning.

Features:
- Checks API reachability and status code (Expects 200 OK).
- Verifies JSON response format.
- Sends email alerts to administrators upon failure.
- Uses environment variables for configuration/credentials.

Configuration (.env):
    MJ_APIKEY_PUBLIC: Mailjet Public Key
    MJ_APIKEY_PRIVATE: Mailjet Private Key
    MAIL_FROM: Sender email address
    DAILY_IMPORT_RECIPIENT: Alert recipient email address

Usage:
    python scripts/monitor_api.py

Dependencies:
    - requests
    - python-dotenv
    - mailjet_rest
"""

import logging
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv
from mailjet_rest import Client

# Configure logging to output to standard output (console)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


def get_mailjet_client():
    """
    Initialize and return the Mailjet client using environment variables.

    Returns:
        Client: Authenticated Mailjet client instance.
        None: If credentials are missing in environment variables.
    """
    api_key_public = os.environ.get("MJ_APIKEY_PUBLIC")
    api_key_private = os.environ.get("MJ_APIKEY_PRIVATE")

    if not api_key_public or not api_key_private:
        logger.warning("Mailjet credentials not found in environment.")
        return None

    return Client(auth=(api_key_public, api_key_private), version="v3.1")


def send_alert_email(error_message, url):
    """
    Send an HTML alert email to the configured administrator.

    Args:
        error_message (str): Description of the error encountered.
        url (str): The URL that failed the check.

    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    client = get_mailjet_client()
    if not client:
        return False

    sender_email = os.environ.get("MAIL_FROM")
    recipient_email = os.environ.get("DAILY_IMPORT_RECIPIENT")

    if not sender_email or not recipient_email:
        logger.warning("Missing MAIL_FROM or DAILY_IMPORT_RECIPIENT.")
        return False

    logger.info(f"Sending alert email to {recipient_email}...")

    # Construct the email payload for Mailjet API
    data = {
        "Messages": [
            {
                "From": {"Email": sender_email, "Name": "VMS Monitor"},
                "To": [{"Email": recipient_email, "Name": "Admin"}],
                "Subject": f"🚨 API ALERT: Volunteer Signup API Failed",
                "TextPart": f"The Volunteer Signup API check failed at {datetime.now()}.\n\nURL: {url}\nError: {error_message}\n\nPlease check the server status immediately.",
                "HTMLPart": f"""
                    <h3>🚨 API Health Check Failed</h3>
                    <p>The Volunteer Signup API check failed at <strong>{datetime.now()}</strong>.</p>
                    <ul>
                        <li><strong>URL:</strong> {url}</li>
                        <li><strong>Error:</strong> {error_message}</li>
                    </ul>
                    <p>Please check the server status immediately.</p>
                """,
            }
        ]
    }

    try:
        # Send the email
        result = client.send.create(data=data)
        if result.status_code == 200:
            logger.info("Alert email sent successfully.")
            return True
        else:
            logger.error(
                f"Failed to send email. Status: {result.status_code}, Response: {result.json()}"
            )
            return False
    except Exception as e:
        logger.error(f"Exception sending email: {e}")
        return False


def check_api_health(url, send_email=True):
    """
    Check the health of the given URL and optionally send alerts.

    Args:
        url (str): The URL to monitor.
        send_email (bool): Whether to trigger email alerts on failure. Default: True.

    Returns:
        tuple: (success (bool), message (str))
    """
    logger.info(f"Checking API health: {url}")

    try:
        # Perform GET request with 10 second timeout
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            logger.info("✅ API is UP (Status 200)")
            try:
                # Validate that response is proper JSON
                response.json()
                return True, "API is functioning correctly."
            except ValueError:
                return True, "API returned 200 but content is not JSON (Warning)."
        else:
            error_msg = f"API returned status code: {response.status_code}"
            logger.error(f"❌ {error_msg}")

            # Trigger alert if configured
            if send_email:
                send_alert_email(error_msg, url)

            return False, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Connection failed: {str(e)}"
        logger.error(f"❌ {error_msg}")

        # Trigger alert if configured
        if send_email:
            send_alert_email(error_msg, url)

        return False, error_msg


if __name__ == "__main__":
    # Main entry point for the monitoring script
    URL = "https://voluntold-prepkc.pythonanywhere.com/events/volunteer_signup_api"
    success, msg = check_api_health(URL)
    # Exit with 0 for success, 1 for failure (useful for CI/CD or cron jobs)
    sys.exit(0 if success else 1)

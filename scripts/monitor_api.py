"""
Robust API Monitor with Email Alerting
======================================

This script monitors the health of the Volunteer Signup API and logs
an alert if the API is down or malfunctioning.

Features:
- Checks API reachability and status code (Expects 200 OK).
- Verifies JSON response format.
- Logs alerts upon failure.
- Uses environment variables for configuration/credentials.


    MAIL_FROM: Sender email address
    DAILY_IMPORT_RECIPIENT: Alert recipient email address

Usage:
    python scripts/monitor_api.py

Dependencies:
    - requests
    - python-dotenv
"""

import logging
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

# Configure logging to output to standard output (console)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


def send_alert_email(error_message, url):
    """
    Placeholder for sending an alert email.

    Args:
        error_message (str): Description of the error encountered.
        url (str): The URL that failed the check.

    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    logger.info("Email alerting not currently configured (provider stubbed).")
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
    logger.info("Checking API health: %s", url)

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
            logger.error("❌ %s", error_msg)

            # Trigger alert if configured
            if send_email:
                send_alert_email(error_msg, url)

            return False, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Connection failed: {str(e)}"
        logger.error("❌ %s", error_msg)

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

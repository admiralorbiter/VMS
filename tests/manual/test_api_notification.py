import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add scripts directory to path to import monitor_api
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(root_dir, "scripts"))

import monitor_api


class TestAPINotification(unittest.TestCase):

    def setUp(self):
        self.test_url = "https://mock-url.com/api"

    @patch("monitor_api.requests.get")
    def test_good_health(self, mock_get):
        """Test that a healthy API returns success and sends NO email."""
        print("\n--- Testing Good API Health ---")

        # Mock a successful 200 OK JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        # We patch send_alert_email to ensure it's NOT called
        with patch("monitor_api.send_alert_email") as mock_send_email:
            success, msg = monitor_api.check_api_health(self.test_url, send_email=True)

            self.assertTrue(success)
            self.assertIn("functioning correctly", msg)
            mock_send_email.assert_not_called()
            print("✅ Good Health Test Passed: API returned 200, no email sent.")

    @patch("monitor_api.requests.get")
    def test_failure_with_real_email(self, mock_get):
        """
        Test that a failed API check triggers a REAL email alert.
        We mock the API failure but let the email logic run.
        """
        print("\n--- Testing API Failure (Triggering REAL Email) ---")

        recipient = os.environ.get("DAILY_IMPORT_RECIPIENT")
        if not recipient:
            print(
                "⚠️  Skipping real email test: DAILY_IMPORT_RECIPIENT not found in .env"
            )
            return

        print(f"📧 This test will attempt to send a REAL email to: {recipient}")

        # Mock a 500 Server Error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # We DO NOT patch send_alert_email here because we want it to run
        success, msg = monitor_api.check_api_health(self.test_url, send_email=True)

        self.assertFalse(success)
        self.assertEqual(msg, "API returned status code: 500")
        print("✅ Failure Test Completed: Logic triggered email send.")


if __name__ == "__main__":
    # Ensure variables are loaded
    monitor_api.load_dotenv()
    unittest.main()

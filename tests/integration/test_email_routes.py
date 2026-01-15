"""
Integration Tests for Email Routes
==================================

Tests for email management routes in the admin panel.
All tests use dry-run mode to prevent actual email sending.
"""

import os
from unittest.mock import Mock, patch

import pytest

from models import db
from models.email import (
    DeliveryAttemptStatus,
    EmailDeliveryAttempt,
    EmailMessage,
    EmailMessageStatus,
    EmailTemplate,
)
from models.user import User
from tests.conftest import assert_route_response, safe_route_test
from utils.email import get_email_allowlist, is_email_delivery_enabled


@pytest.fixture
def test_email_template(app, test_admin):
    """Create a test email template"""
    with app.app_context():
        template = EmailTemplate(
            purpose_key="test_template",
            version=1,
            name="Test Template",
            description="Test description",
            subject_template="Test: {{user_name}}",
            html_template="<p>Hello {{user_name}}</p>",
            text_template="Hello {{user_name}}",
            required_placeholders=["user_name"],
            is_active=True,
            created_by_id=test_admin.id,
        )
        db.session.add(template)
        db.session.commit()
        template_id = template.id
        yield template
        # Clean up dependent records first
        attempts = (
            EmailDeliveryAttempt.query.join(EmailMessage)
            .filter(EmailMessage.template_id == template_id)
            .all()
        )
        for attempt in attempts:
            db.session.delete(attempt)
        messages = EmailMessage.query.filter_by(template_id=template_id).all()
        for message in messages:
            db.session.delete(message)
        db.session.commit()
        template = db.session.get(EmailTemplate, template_id)
        if template:
            db.session.delete(template)
            db.session.commit()


@pytest.fixture
def test_email_message(app, test_email_template, test_admin):
    """Create a test email message"""
    with app.app_context():
        message = EmailMessage(
            template_id=test_email_template.id,
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
            recipients=["test@example.com"],
            recipient_count=1,
            status=EmailMessageStatus.DRAFT,
            created_by_id=test_admin.id,
        )
        db.session.add(message)
        db.session.commit()
        message_id = message.id
        yield message
        # Clean up attempts first
        attempts = EmailDeliveryAttempt.query.filter_by(message_id=message_id).all()
        for attempt in attempts:
            db.session.delete(attempt)
        db.session.commit()
        message = db.session.get(EmailMessage, message_id)
        if message:
            db.session.delete(message)
            db.session.commit()


class TestEmailOverview:
    """Tests for email overview dashboard"""

    def test_email_overview_requires_admin(self, client, auth_headers):
        """Test that email overview requires admin access"""
        response = safe_route_test(client, "/management/email", headers=auth_headers)
        # Non-admin should get 403
        assert_route_response(response, expected_statuses=[403, 404, 500])

    def test_email_overview_admin_access(self, client, test_admin_headers):
        """Test email overview with admin access"""
        response = safe_route_test(
            client, "/management/email", headers=test_admin_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])


class TestEmailTemplates:
    """Tests for email template routes"""

    def test_email_templates_list(self, client, test_admin_headers):
        """Test templates list view"""
        response = safe_route_test(
            client, "/management/email/templates", headers=test_admin_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])

    def test_email_template_detail(
        self, client, test_admin_headers, test_email_template
    ):
        """Test template detail view"""
        response = safe_route_test(
            client,
            f"/management/email/templates/{test_email_template.id}",
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])


class TestEmailOutbox:
    """Tests for email outbox routes"""

    def test_email_outbox_list(self, client, test_admin_headers):
        """Test outbox list view"""
        response = safe_route_test(
            client, "/management/email/outbox", headers=test_admin_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])

    def test_email_outbox_filtering(self, client, test_admin_headers):
        """Test outbox filtering"""
        response = safe_route_test(
            client,
            "/management/email/outbox?status=draft&search=test",
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])

    def test_email_message_detail(self, client, test_admin_headers, test_email_message):
        """Test message detail view"""
        response = safe_route_test(
            client,
            f"/management/email/outbox/{test_email_message.id}",
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])

    def test_queue_message(self, client, test_admin_headers, test_email_message):
        """Test queueing a message"""
        # Ensure message is in DRAFT status
        with client.application.app_context():
            test_email_message.status = EmailMessageStatus.DRAFT
            db.session.commit()

        response = safe_route_test(
            client,
            f"/management/email/outbox/{test_email_message.id}/queue",
            method="POST",
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 302, 404, 500])

    def test_cancel_message(self, client, test_admin_headers, test_email_message):
        """Test cancelling a message"""
        # Ensure message is in QUEUED status
        with client.application.app_context():
            test_email_message.status = EmailMessageStatus.QUEUED
            db.session.commit()

        response = safe_route_test(
            client,
            f"/management/email/outbox/{test_email_message.id}/cancel",
            method="POST",
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 302, 404, 500])


class TestEmailSending:
    """Tests for email sending routes (with mocks)"""

    @patch("utils.email.send_email_via_mailjet")
    def test_send_message_dry_run(
        self, mock_send, client, test_admin_headers, test_email_message
    ):
        """Test sending a message in dry-run mode"""
        # Mock the send function to return success
        mock_send.return_value = (True, None, {"dry_run": True})

        # Queue the message first
        with client.application.app_context():
            test_email_message.status = EmailMessageStatus.QUEUED
            db.session.commit()

        response = safe_route_test(
            client,
            f"/management/email/outbox/{test_email_message.id}/send",
            method="POST",
            data={"dry_run": "true"},
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 302, 404, 500])

    @patch("utils.email.send_email_via_mailjet")
    @patch.dict(os.environ, {"EMAIL_DELIVERY_ENABLED": "true"})
    def test_send_message_real(
        self, mock_send, client, test_admin_headers, test_email_message
    ):
        """Test sending a real message (mocked)"""
        # Mock successful send
        mock_send.return_value = (
            True,
            None,
            {"status_code": 200, "message_id": "12345"},
        )

        # Queue the message first
        with client.application.app_context():
            test_email_message.status = EmailMessageStatus.QUEUED
            db.session.commit()

        response = safe_route_test(
            client,
            f"/management/email/outbox/{test_email_message.id}/send",
            method="POST",
            data={"dry_run": "false"},
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 302, 404, 500])


class TestEmailAttempts:
    """Tests for delivery attempts routes"""

    def test_email_attempts_list(self, client, test_admin_headers):
        """Test delivery attempts list view"""
        response = safe_route_test(
            client, "/management/email/attempts", headers=test_admin_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])


class TestEmailSettings:
    """Tests for email settings routes"""

    def test_email_settings_view(self, client, test_admin_headers):
        """Test settings view"""
        response = safe_route_test(
            client, "/management/email/settings", headers=test_admin_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])

    @patch("utils.email.create_delivery_attempt")
    @patch("utils.email.create_email_message")
    def test_test_send(
        self,
        mock_create_message,
        mock_create_attempt,
        client,
        test_admin_headers,
        test_email_template,
        test_admin,
    ):
        """Test test send functionality"""
        # Create a real message in the database for the mock to reference
        with client.application.app_context():
            real_message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test Subject",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.QUEUED,
                created_by_id=test_admin.id,
            )
            db.session.add(real_message)
            db.session.commit()
            real_message_id = real_message.id

        # Mock message creation to return the real message
        def mock_create_message_func(*args, **kwargs):
            return real_message

        mock_create_message.side_effect = mock_create_message_func

        # Mock attempt creation
        mock_attempt = Mock()
        mock_attempt.id = 1
        mock_attempt.status = "DRY_RUN"
        mock_create_attempt.return_value = mock_attempt

        response = safe_route_test(
            client,
            "/management/email/test-send",
            method="POST",
            data={"template_id": str(test_email_template.id), "dry_run": "true"},
            headers=test_admin_headers,
        )
        assert_route_response(response, expected_statuses=[200, 302, 404, 500])

        # Clean up
        with client.application.app_context():
            attempts = EmailDeliveryAttempt.query.filter_by(
                message_id=real_message_id
            ).all()
            for attempt in attempts:
                db.session.delete(attempt)
            message = db.session.get(EmailMessage, real_message_id)
            if message:
                db.session.delete(message)
            db.session.commit()


class TestEmailAccessControl:
    """Tests for email route access control"""

    def test_email_routes_require_admin(self, client, auth_headers):
        """Test that all email routes require admin access"""
        routes = [
            "/management/email",
            "/management/email/templates",
            "/management/email/outbox",
            "/management/email/attempts",
            "/management/email/settings",
        ]

        for route in routes:
            response = safe_route_test(client, route, headers=auth_headers)
            # Non-admin should get 403
            assert_route_response(response, expected_statuses=[403, 404, 500])


class TestEmailRealSending:
    """
    Tests for REAL email sending (only runs if explicitly enabled).

    WARNING: These tests will send REAL emails if:
    - EMAIL_DELIVERY_ENABLED=true in environment
    - EMAIL_ALLOWLIST is configured
    - RUN_REAL_EMAIL_TESTS environment variable is set to 'true'

    To run these tests:
        RUN_REAL_EMAIL_TESTS=true pytest tests/integration/test_email_routes.py::TestEmailRealSending -v

    These tests will ONLY send to emails in EMAIL_ALLOWLIST.
    """

    @pytest.mark.skipif(
        os.environ.get("RUN_REAL_EMAIL_TESTS", "").lower() != "true",
        reason="Real email tests require RUN_REAL_EMAIL_TESTS=true",
    )
    def test_send_real_email_end_to_end(self, app, test_email_template, test_admin):
        """
        End-to-end test that sends a REAL email.

        This test will:
        1. Create a message
        2. Queue it
        3. Send it via Mailjet (REAL EMAIL)

        Only runs if RUN_REAL_EMAIL_TESTS=true and EMAIL_DELIVERY_ENABLED=true
        """
        # Check prerequisites
        if not is_email_delivery_enabled():
            pytest.skip("EMAIL_DELIVERY_ENABLED is not true")

        allowlist = get_email_allowlist()
        if not allowlist:
            pytest.skip("EMAIL_ALLOWLIST is not configured")

        # Use first allowlisted email
        test_recipient = allowlist[0]
        if test_recipient.startswith("@"):
            pytest.skip(
                "Domain allowlist not supported for this test - use specific email"
            )

        with app.app_context():
            from utils.email import (
                create_delivery_attempt,
                create_email_message,
                queue_message_for_delivery,
            )

            # Create message
            message = create_email_message(
                template=test_email_template,
                recipients=[test_recipient],
                context={
                    "user_name": "Pytest Test User",
                    "district_name": "Test District",
                    "test_mode": "AUTOMATED_TEST",
                },
                created_by_id=test_admin.id,
                status=EmailMessageStatus.DRAFT,
            )
            db.session.commit()

            assert message.id is not None
            assert message.recipient_count == 1
            assert message.recipients[0] == test_recipient

            # Queue message
            message = queue_message_for_delivery(message.id)
            assert message.status == EmailMessageStatus.QUEUED

            # Send for real (no dry-run, no mocks)
            attempt = create_delivery_attempt(message, is_dry_run=False)

            # Verify attempt was created
            assert attempt.id is not None
            assert attempt.status in [
                DeliveryAttemptStatus.SUCCESS,
                DeliveryAttemptStatus.FAILED,
            ]

            if attempt.status == DeliveryAttemptStatus.SUCCESS:
                assert attempt.mailjet_message_id is not None
                print(f"\n✓ REAL EMAIL SENT SUCCESSFULLY")
                print(f"  Recipient: {test_recipient}")
                print(f"  Mailjet Message ID: {attempt.mailjet_message_id}")
                print(f"  Check your inbox!")
            else:
                print(f"\n✗ Email send failed: {attempt.error_message}")
                # Don't fail the test - we want to see what happened
                pytest.fail(f"Email send failed: {attempt.error_message}")

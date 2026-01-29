"""
Unit Tests for Email Models
===========================

Tests for EmailTemplate, EmailMessage, and EmailDeliveryAttempt models.
"""

from datetime import datetime, timezone

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


@pytest.fixture
def test_admin_user(app):
    """Create an admin user for email tests"""
    with app.app_context():
        admin = User(
            username="email_admin",
            email="admin@example.com",
            password_hash="hash",
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id
        yield admin
        # Clean up in correct order - delete dependent records first
        # Delete delivery attempts
        attempts = (
            EmailDeliveryAttempt.query.join(EmailMessage)
            .filter(EmailMessage.created_by_id == admin_id)
            .all()
        )
        for attempt in attempts:
            db.session.delete(attempt)
        db.session.commit()

        # Delete messages
        messages = EmailMessage.query.filter_by(created_by_id=admin_id).all()
        for message in messages:
            db.session.delete(message)
        db.session.commit()

        # Delete templates
        templates = EmailTemplate.query.filter_by(created_by_id=admin_id).all()
        for template in templates:
            db.session.delete(template)
        db.session.commit()

        # Now safe to delete user
        admin = db.session.get(User, admin_id)
        if admin:
            db.session.delete(admin)
            db.session.commit()


@pytest.fixture
def test_email_template(app, test_admin_user):
    """Create a test email template"""
    with app.app_context():
        template = EmailTemplate(
            purpose_key="test_template",
            version=1,
            name="Test Template",
            description="A test template",
            subject_template="Test: {{user_name}}",
            html_template="<p>Hello {{user_name}}</p>",
            text_template="Hello {{user_name}}",
            required_placeholders=["user_name"],
            optional_placeholders=["district_name"],
            is_active=True,
            created_by_id=test_admin_user.id,
        )
        db.session.add(template)
        db.session.commit()
        template_id = template.id
        yield template
        # Clean up dependent records first
        # Delete delivery attempts for messages using this template
        attempts = (
            EmailDeliveryAttempt.query.join(EmailMessage)
            .filter(EmailMessage.template_id == template_id)
            .all()
        )
        for attempt in attempts:
            db.session.delete(attempt)
        db.session.commit()

        # Delete messages using this template
        messages = EmailMessage.query.filter_by(template_id=template_id).all()
        for message in messages:
            db.session.delete(message)
        db.session.commit()

        # Now safe to delete template
        template = db.session.get(EmailTemplate, template_id)
        if template:
            db.session.delete(template)
            db.session.commit()


class TestEmailTemplate:
    """Tests for EmailTemplate model"""

    def test_create_template(self, app, test_admin_user):
        """Test creating an email template"""
        with app.app_context():
            template = EmailTemplate(
                purpose_key="new_template",
                version=1,
                name="New Template",
                subject_template="Subject",
                html_template="<p>HTML</p>",
                text_template="Text",
                is_active=True,
                created_by_id=test_admin_user.id,
            )
            db.session.add(template)
            db.session.commit()

            assert template.id is not None
            assert template.purpose_key == "new_template"
            assert template.version == 1
            assert template.is_active is True

    def test_template_to_dict(self, test_email_template):
        """Test template to_dict method"""
        result = test_email_template.to_dict()
        assert result["id"] == test_email_template.id
        assert result["purpose_key"] == "test_template"
        assert result["version"] == 1
        assert result["is_active"] is True

    def test_template_relationships(self, test_email_template):
        """Test template relationships"""
        assert hasattr(test_email_template, "messages")
        assert test_email_template.created_by is not None


class TestEmailMessage:
    """Tests for EmailMessage model"""

    def test_create_message(self, app, test_email_template, test_admin_user):
        """Test creating an email message"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test Subject",
                html_body="<p>HTML</p>",
                text_body="Text",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.DRAFT,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            assert message.id is not None
            assert message.status == EmailMessageStatus.DRAFT
            assert message.recipient_count == 1
            assert len(message.recipients) == 1

    def test_message_status_transitions(
        self, app, test_email_template, test_admin_user
    ):
        """Test message status transitions"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.DRAFT,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            # DRAFT -> QUEUED
            message.status = EmailMessageStatus.QUEUED
            message.queued_at = datetime.now(timezone.utc)
            db.session.commit()
            assert message.status == EmailMessageStatus.QUEUED
            assert message.queued_at is not None

            # QUEUED -> SENT
            message.status = EmailMessageStatus.SENT
            message.sent_at = datetime.now(timezone.utc)
            db.session.commit()
            assert message.status == EmailMessageStatus.SENT
            assert message.sent_at is not None

    def test_message_excluded_recipients(
        self, app, test_email_template, test_admin_user
    ):
        """Test message with excluded recipients"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["valid@example.com"],
                recipient_count=1,
                excluded_recipients=[
                    {"email": "invalid@example.com", "reason": "Not in allowlist"}
                ],
                status=EmailMessageStatus.DRAFT,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            assert message.excluded_recipients is not None
            assert len(message.excluded_recipients) == 1
            assert message.excluded_recipients[0]["reason"] == "Not in allowlist"

    def test_message_to_dict(self, app, test_email_template, test_admin_user):
        """Test message to_dict method"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.DRAFT,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            result = message.to_dict()
            assert result["id"] == message.id
            assert result["status"] == "DRAFT"
            assert result["recipient_count"] == 1

    def test_message_relationships(self, app, test_email_template, test_admin_user):
        """Test message relationships"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.DRAFT,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            assert message.template is not None
            assert message.template.id == test_email_template.id
            assert message.created_by is not None
            assert hasattr(message, "delivery_attempts")


class TestEmailDeliveryAttempt:
    """Tests for EmailDeliveryAttempt model"""

    def test_create_delivery_attempt(self, app, test_email_template, test_admin_user):
        """Test creating a delivery attempt"""
        with app.app_context():
            # Create message first
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.QUEUED,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            # Create attempt
            attempt = EmailDeliveryAttempt(
                message_id=message.id,
                status=DeliveryAttemptStatus.PENDING,
                is_dry_run=True,
            )
            db.session.add(attempt)
            db.session.commit()

            assert attempt.id is not None
            assert attempt.status == DeliveryAttemptStatus.PENDING
            assert attempt.is_dry_run is True

    def test_delivery_attempt_status_transitions(
        self, app, test_email_template, test_admin_user
    ):
        """Test delivery attempt status transitions"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.QUEUED,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            attempt = EmailDeliveryAttempt(
                message_id=message.id,
                status=DeliveryAttemptStatus.PENDING,
                is_dry_run=False,
            )
            db.session.add(attempt)
            db.session.commit()

            # PENDING -> SUCCESS
            attempt.status = DeliveryAttemptStatus.SUCCESS
            attempt.mailjet_message_id = "12345"
            attempt.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            assert attempt.status == DeliveryAttemptStatus.SUCCESS
            assert attempt.mailjet_message_id == "12345"
            assert attempt.completed_at is not None

    def test_delivery_attempt_with_error(
        self, app, test_email_template, test_admin_user
    ):
        """Test delivery attempt with error"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.QUEUED,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            attempt = EmailDeliveryAttempt(
                message_id=message.id,
                status=DeliveryAttemptStatus.FAILED,
                error_message="Test error",
                error_details={"code": "TEST_ERROR"},
                is_dry_run=False,
            )
            db.session.add(attempt)
            db.session.commit()

            assert attempt.status == DeliveryAttemptStatus.FAILED
            assert attempt.error_message == "Test error"
            assert attempt.error_details["code"] == "TEST_ERROR"

    def test_delivery_attempt_to_dict(self, app, test_email_template, test_admin_user):
        """Test delivery attempt to_dict method"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.QUEUED,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            attempt = EmailDeliveryAttempt(
                message_id=message.id,
                status=DeliveryAttemptStatus.SUCCESS,
                is_dry_run=True,
            )
            db.session.add(attempt)
            db.session.commit()

            result = attempt.to_dict()
            assert result["id"] == attempt.id
            assert result["status"] == "SUCCESS"
            assert result["is_dry_run"] is True

    def test_delivery_attempt_relationships(
        self, app, test_email_template, test_admin_user
    ):
        """Test delivery attempt relationships"""
        with app.app_context():
            message = EmailMessage(
                template_id=test_email_template.id,
                subject="Test",
                html_body="<p>Test</p>",
                text_body="Test",
                recipients=["test@example.com"],
                recipient_count=1,
                status=EmailMessageStatus.QUEUED,
                created_by_id=test_admin_user.id,
            )
            db.session.add(message)
            db.session.commit()

            attempt = EmailDeliveryAttempt(
                message_id=message.id,
                status=DeliveryAttemptStatus.PENDING,
                is_dry_run=True,
            )
            db.session.add(attempt)
            db.session.commit()

            assert attempt.message is not None
            assert attempt.message.id == message.id

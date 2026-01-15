"""
Unit Tests for Email Utilities
==============================

Tests for email utility functions including safety gates, quality checks,
and Mailjet integration (mocked).
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from models import db
from models.email import (
    EmailDeliveryAttempt,
    EmailMessage,
    EmailMessageStatus,
    EmailTemplate,
)
from models.user import User
from utils.email import (
    EmailQualityError,
    EmailSafetyError,
    check_recipient_allowlist,
    check_safety_gates,
    create_email_message,
    get_email_allowlist,
    is_email_delivery_enabled,
    is_production_environment,
    render_template,
    validate_email_format,
    validate_recipients,
    validate_template_rendering,
)


@pytest.fixture
def test_email_template(app, test_admin):
    """Create a test email template"""
    with app.app_context():
        template = EmailTemplate(
            purpose_key="test_template",
            version=1,
            name="Test Template",
            subject_template="Hello {{user_name}}",
            html_template="<p>Hello {{user_name}} from {{district_name}}</p>",
            text_template="Hello {{user_name}} from {{district_name}}",
            required_placeholders=["user_name"],
            optional_placeholders=["district_name"],
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


class TestEmailValidation:
    """Tests for email validation functions"""

    def test_validate_email_format_valid(self):
        """Test validating valid email addresses"""
        is_valid, error = validate_email_format("test@example.com")
        assert is_valid is True
        assert error is None

    def test_validate_email_format_invalid(self):
        """Test validating invalid email addresses"""
        is_valid, error = validate_email_format("invalid-email")
        assert is_valid is False
        assert error is not None

    def test_validate_email_format_empty(self):
        """Test validating empty email"""
        is_valid, error = validate_email_format("")
        assert is_valid is False
        assert error is not None
        # Error message should indicate the email is invalid/empty
        assert (
            "required" in error.lower()
            or "empty" in error.lower()
            or "cannot be empty" in error.lower()
        )

    def test_validate_recipients_valid(self):
        """Test validating valid recipient list"""
        valid, excluded = validate_recipients(
            ["test1@example.com", "test2@example.com"]
        )
        assert len(valid) == 2
        assert len(excluded) == 0

    def test_validate_recipients_duplicate(self):
        """Test validating recipients with duplicates"""
        valid, excluded = validate_recipients(
            ["test@example.com", "test@example.com", "other@example.com"]
        )
        assert len(valid) == 2
        assert len(excluded) == 1
        assert excluded[0]["reason"] == "Duplicate"

    def test_validate_recipients_invalid_format(self):
        """Test validating recipients with invalid formats"""
        valid, excluded = validate_recipients(["invalid-email", "valid@example.com"])
        assert len(valid) == 1
        assert len(excluded) == 1
        assert "invalid" in excluded[0]["reason"].lower()


class TestAllowlistFunctions:
    """Tests for allowlist functions"""

    @patch.dict(os.environ, {"EMAIL_ALLOWLIST": "test@example.com,@testdomain.com"})
    def test_get_email_allowlist(self):
        """Test getting email allowlist"""
        allowlist = get_email_allowlist()
        assert len(allowlist) == 2
        assert "test@example.com" in allowlist
        assert "@testdomain.com" in allowlist

    @patch.dict(os.environ, {"EMAIL_ALLOWLIST": ""})
    def test_get_email_allowlist_empty(self):
        """Test getting empty allowlist"""
        allowlist = get_email_allowlist()
        assert len(allowlist) == 0

    def test_check_recipient_allowlist_exact_match(self):
        """Test allowlist check with exact match"""
        allowlist = ["test@example.com"]
        is_allowed, reason = check_recipient_allowlist("test@example.com", allowlist)
        assert is_allowed is True
        assert reason is None

    def test_check_recipient_allowlist_domain_match(self):
        """Test allowlist check with domain match"""
        allowlist = ["@example.com"]
        is_allowed, reason = check_recipient_allowlist("user@example.com", allowlist)
        assert is_allowed is True
        assert reason is None

    def test_check_recipient_allowlist_blocked(self):
        """Test allowlist check with blocked email"""
        allowlist = ["allowed@example.com"]
        is_allowed, reason = check_recipient_allowlist("blocked@example.com", allowlist)
        assert is_allowed is False
        assert reason is not None


class TestSafetyGates:
    """Tests for safety gate functions"""

    @patch.dict(os.environ, {"EMAIL_DELIVERY_ENABLED": "false"})
    def test_check_safety_gates_delivery_disabled(self):
        """Test safety gates when delivery is disabled"""
        is_allowed, error, excluded = check_safety_gates(
            ["test@example.com"], is_dry_run=False
        )
        assert is_allowed is False
        assert "disabled" in error.lower()

    @patch.dict(os.environ, {"EMAIL_DELIVERY_ENABLED": "false"})
    def test_check_safety_gates_dry_run_bypass(self):
        """Test that dry-run bypasses delivery check"""
        is_allowed, error, excluded = check_safety_gates(
            ["test@example.com"], is_dry_run=True
        )
        # Dry-run should allow even if delivery is disabled
        assert is_allowed is True

    @patch.dict(
        os.environ,
        {
            "EMAIL_DELIVERY_ENABLED": "true",
            "EMAIL_ALLOWLIST": "allowed@example.com",
            "FLASK_ENV": "development",
        },
    )
    def test_check_safety_gates_allowlist_enforcement(self):
        """Test allowlist enforcement in non-production"""
        is_allowed, error, excluded = check_safety_gates(
            ["allowed@example.com", "blocked@example.com"], is_dry_run=False
        )
        assert is_allowed is True  # At least one allowed
        assert len(excluded) == 1
        assert excluded[0]["email"] == "blocked@example.com"

    @patch.dict(
        os.environ,
        {
            "EMAIL_DELIVERY_ENABLED": "true",
            "EMAIL_ALLOWLIST": "allowed@example.com",
            "FLASK_ENV": "development",
        },
    )
    def test_check_safety_gates_all_blocked(self):
        """Test when all recipients are blocked"""
        is_allowed, error, excluded = check_safety_gates(
            ["blocked1@example.com", "blocked2@example.com"], is_dry_run=False
        )
        assert is_allowed is False
        assert "all recipients blocked" in error.lower()

    @patch.dict(
        os.environ,
        {
            "EMAIL_DELIVERY_ENABLED": "true",
            "EMAIL_MAX_RECIPIENTS": "5",
            "FLASK_ENV": "production",  # Skip allowlist in production
        },
    )
    def test_check_safety_gates_max_recipients(self):
        """Test max recipients limit"""
        recipients = [f"test{i}@example.com" for i in range(10)]
        is_allowed, error, excluded = check_safety_gates(recipients, is_dry_run=False)
        assert is_allowed is False
        # Error should mention exceeding maximum
        assert (
            "exceeds maximum" in error.lower()
            or "maximum" in error.lower()
            or "exceeds" in error.lower()
        )


class TestTemplateRendering:
    """Tests for template rendering functions"""

    def test_render_template(self, test_email_template):
        """Test rendering a template with context"""
        context = {"user_name": "John", "district_name": "Test District"}
        subject, html, text = render_template(test_email_template, context)

        assert "John" in subject
        assert "John" in html
        assert "John" in text
        assert "Test District" in html
        assert "Test District" in text

    def test_validate_template_rendering_complete(self, test_email_template):
        """Test template validation with complete context"""
        context = {"user_name": "John", "district_name": "Test District"}
        is_valid, missing = validate_template_rendering(test_email_template, context)
        assert is_valid is True
        assert len(missing) == 0

    def test_validate_template_rendering_missing(self, test_email_template):
        """Test template validation with missing placeholders"""
        context = {}  # Missing required user_name
        is_valid, missing = validate_template_rendering(test_email_template, context)
        assert is_valid is False
        assert len(missing) > 0


class TestMessageCreation:
    """Tests for message creation functions"""

    def test_create_email_message_success(self, app, test_email_template, test_admin):
        """Test creating an email message successfully"""
        with app.app_context():
            message = create_email_message(
                template=test_email_template,
                recipients=["test@example.com"],
                context={"user_name": "Test User", "district_name": "Test District"},
                created_by_id=test_admin.id,
                status=EmailMessageStatus.DRAFT,
            )
            db.session.commit()

            assert message.id is not None
            assert message.status == EmailMessageStatus.DRAFT
            assert message.recipient_count == 1
            assert message.quality_score is not None
            assert message.quality_checks is not None

    def test_create_email_message_missing_placeholder(
        self, app, test_email_template, test_admin
    ):
        """Test creating message with missing required placeholder"""
        with app.app_context():
            with pytest.raises(EmailQualityError):
                create_email_message(
                    template=test_email_template,
                    recipients=["test@example.com"],
                    context={},  # Missing required user_name
                    created_by_id=test_admin.id,
                )

    def test_create_email_message_quality_checks(
        self, app, test_email_template, test_admin
    ):
        """Test that quality checks run on message creation"""
        with app.app_context():
            # Provide all placeholders (required and optional) to avoid validation errors
            message = create_email_message(
                template=test_email_template,
                recipients=["test@example.com"],
                context={"user_name": "Test User", "district_name": "Test District"},
                created_by_id=test_admin.id,
            )
            db.session.commit()

            assert message.quality_checks is not None
            assert "recipient_validation" in message.quality_checks
            assert "template_validation" in message.quality_checks
            assert message.quality_score is not None
            assert 0 <= message.quality_score <= 100


class TestEnvironmentFunctions:
    """Tests for environment checking functions"""

    @patch.dict(os.environ, {"EMAIL_DELIVERY_ENABLED": "true"})
    def test_is_email_delivery_enabled_true(self):
        """Test delivery enabled check when true"""
        assert is_email_delivery_enabled() is True

    @patch.dict(os.environ, {"EMAIL_DELIVERY_ENABLED": "false"})
    def test_is_email_delivery_enabled_false(self):
        """Test delivery enabled check when false"""
        assert is_email_delivery_enabled() is False

    @patch.dict(os.environ, {"FLASK_ENV": "production"})
    def test_is_production_environment_true(self):
        """Test production environment check when true"""
        assert is_production_environment() is True

    @patch.dict(os.environ, {"FLASK_ENV": "development"})
    def test_is_production_environment_false(self):
        """Test production environment check when false"""
        assert is_production_environment() is False

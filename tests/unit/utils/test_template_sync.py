"""
Unit Tests for Email Template File Sync
=========================================

Tests for the file-based email template auto-import utility.
"""

import os
import tempfile
from pathlib import Path

import pytest

from models import db
from models.email import EmailTemplate
from utils.template_sync import sync_file_templates


@pytest.fixture
def template_dir(tmp_path):
    """Create a temporary directory for test template files."""
    return tmp_path


def _write_template(directory: Path, filename: str, content: str):
    """Write a YAML template file to the given directory."""
    filepath = directory / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


VALID_TEMPLATE = """
purpose_key: test_template
name: Test Template
description: A test email template
subject: "Test Subject - {{name}}"

required_placeholders:
  - name

html: |
  <html><body><h1>Hello {{name}}</h1></body></html>

text: |
  Hello {{name}}
"""

UPDATED_TEMPLATE = """
purpose_key: test_template
name: Test Template (Updated)
description: An updated test email template
subject: "Updated Test Subject - {{name}}"

required_placeholders:
  - name

html: |
  <html><body><h1>Updated Hello {{name}}</h1></body></html>

text: |
  Updated Hello {{name}}
"""

SECOND_TEMPLATE = """
purpose_key: second_template
name: Second Template
description: Another template
subject: "Second - {{value}}"

required_placeholders:
  - value

html: |
  <html><body><p>{{value}}</p></body></html>

text: |
  Value: {{value}}
"""

INVALID_TEMPLATE_MISSING_FIELDS = """
purpose_key: bad_template
name: Bad Template
"""

INVALID_TEMPLATE_BAD_YAML = """
purpose_key: [bad: yaml: syntax
  <<<not valid>>>
"""


class TestSyncFileTemplates:
    """Tests for sync_file_templates."""

    def test_creates_new_template(self, app, template_dir):
        """Empty DB + file exists → template created as v1."""
        with app.app_context():
            _write_template(template_dir, "test.yaml", VALID_TEMPLATE)

            stats = sync_file_templates(str(template_dir))

            assert stats["created"] == 1
            assert stats["updated"] == 0
            assert stats["skipped"] == 0

            template = EmailTemplate.query.filter_by(
                purpose_key="test_template"
            ).first()
            assert template is not None
            assert template.version == 1
            assert template.is_active is True
            assert template.name == "Test Template"
            assert "{{name}}" in template.subject_template

    def test_skips_unchanged_template(self, app, template_dir):
        """DB matches file → no-op."""
        with app.app_context():
            _write_template(template_dir, "test.yaml", VALID_TEMPLATE)

            # First sync: creates
            sync_file_templates(str(template_dir))

            # Second sync: should skip
            stats = sync_file_templates(str(template_dir))

            assert stats["created"] == 0
            assert stats["updated"] == 0
            assert stats["skipped"] == 1

            # Still only one version
            count = EmailTemplate.query.filter_by(purpose_key="test_template").count()
            assert count == 1

    def test_updates_changed_template(self, app, template_dir):
        """DB has old version, file content changed → new version created."""
        with app.app_context():
            # First sync with original content
            _write_template(template_dir, "test.yaml", VALID_TEMPLATE)
            sync_file_templates(str(template_dir))

            # Update the file
            _write_template(template_dir, "test.yaml", UPDATED_TEMPLATE)

            # Second sync should update
            stats = sync_file_templates(str(template_dir))

            assert stats["updated"] == 1
            assert stats["created"] == 0
            assert stats["skipped"] == 0

            # Old version should be deactivated
            old = EmailTemplate.query.filter_by(
                purpose_key="test_template", version=1
            ).first()
            assert old.is_active is False

            # New version should be active
            new = EmailTemplate.query.filter_by(
                purpose_key="test_template", version=2
            ).first()
            assert new is not None
            assert new.is_active is True
            assert new.name == "Test Template (Updated)"

    def test_ignores_ui_created_templates(self, app, template_dir):
        """UI-created templates with different purpose_keys are untouched."""
        with app.app_context():
            # Create a UI template
            ui_template = EmailTemplate(
                purpose_key="ui_created",
                version=1,
                name="UI Template",
                subject_template="UI Subject",
                html_template="<p>UI</p>",
                text_template="UI",
                is_active=True,
            )
            db.session.add(ui_template)
            db.session.commit()

            # Sync with a different purpose_key
            _write_template(template_dir, "test.yaml", VALID_TEMPLATE)
            sync_file_templates(str(template_dir))

            # UI template should be untouched
            ui = EmailTemplate.query.filter_by(purpose_key="ui_created").first()
            assert ui is not None
            assert ui.is_active is True
            assert ui.name == "UI Template"

    def test_handles_missing_directory(self, app):
        """No directory → graceful no-op."""
        with app.app_context():
            stats = sync_file_templates("/nonexistent/path/to/templates")

            assert stats["created"] == 0
            assert stats["updated"] == 0
            assert stats["skipped"] == 0
            assert stats["errors"] == 0

    def test_handles_empty_directory(self, app, template_dir):
        """Empty directory → no-op."""
        with app.app_context():
            stats = sync_file_templates(str(template_dir))

            assert stats["created"] == 0
            assert stats["skipped"] == 0

    def test_validates_required_fields(self, app, template_dir):
        """YAML missing required fields → skip with error count."""
        with app.app_context():
            _write_template(template_dir, "bad.yaml", INVALID_TEMPLATE_MISSING_FIELDS)

            stats = sync_file_templates(str(template_dir))

            assert stats["errors"] == 1
            assert stats["created"] == 0

            # No template should be created
            template = EmailTemplate.query.filter_by(purpose_key="bad_template").first()
            assert template is None

    def test_handles_invalid_yaml(self, app, template_dir):
        """Invalid YAML syntax → skip with error count."""
        with app.app_context():
            _write_template(template_dir, "invalid.yaml", INVALID_TEMPLATE_BAD_YAML)

            stats = sync_file_templates(str(template_dir))

            assert stats["errors"] == 1
            assert stats["created"] == 0

    def test_syncs_multiple_templates(self, app, template_dir):
        """Multiple valid YAML files → all synced."""
        with app.app_context():
            _write_template(template_dir, "first.yaml", VALID_TEMPLATE)
            _write_template(template_dir, "second.yaml", SECOND_TEMPLATE)

            stats = sync_file_templates(str(template_dir))

            assert stats["created"] == 2

            t1 = EmailTemplate.query.filter_by(purpose_key="test_template").first()
            t2 = EmailTemplate.query.filter_by(purpose_key="second_template").first()
            assert t1 is not None
            assert t2 is not None
            assert t1.is_active is True
            assert t2.is_active is True

    def test_supports_yml_extension(self, app, template_dir):
        """Both .yaml and .yml extensions should be discovered."""
        with app.app_context():
            _write_template(template_dir, "test.yml", VALID_TEMPLATE)

            stats = sync_file_templates(str(template_dir))

            assert stats["created"] == 1

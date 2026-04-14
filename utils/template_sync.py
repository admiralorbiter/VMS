"""
Email Template File Sync
=========================

Auto-discovers email template definition files (YAML) and syncs them to the
database on app startup. This replaces the manual seed-script approach, making
file-based templates the source of truth while leaving UI-created templates
untouched.

File format (YAML):
    purpose_key: <unique key>
    name: <display name>
    description: <optional description>
    subject: <subject template with {{placeholders}}>
    required_placeholders: [list]
    optional_placeholders: [list]  # optional
    html: |
      <full HTML template>
    text: |
      <full text template>
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from models import db
from models.email import EmailTemplate

logger = logging.getLogger(__name__)

# Default directory relative to the repository root
DEFAULT_TEMPLATE_DIR = "email_templates"


def _content_hash(subject: str, html: str, text: str) -> str:
    """Compute a SHA-256 hash of the template content for change detection."""
    combined = f"{subject}\n---\n{html}\n---\n{text}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _parse_template_file(filepath: Path) -> Optional[dict]:
    """Parse a single YAML template file and validate required fields.

    Returns a dict with the parsed template data, or None if invalid.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to parse template file %s: %s", filepath.name, e)
        return None

    if not isinstance(data, dict):
        logger.warning("Template file %s is not a valid YAML mapping", filepath.name)
        return None

    # Validate required fields
    required_fields = ["purpose_key", "name", "subject", "html", "text"]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        logger.warning(
            "Template file %s missing required fields: %s",
            filepath.name,
            ", ".join(missing),
        )
        return None

    return {
        "purpose_key": data["purpose_key"].strip(),
        "name": data["name"].strip(),
        "description": (data.get("description") or "").strip() or None,
        "subject_template": data["subject"].strip(),
        "html_template": data["html"].strip(),
        "text_template": data["text"].strip(),
        "required_placeholders": data.get("required_placeholders"),
        "optional_placeholders": data.get("optional_placeholders"),
    }


def sync_file_templates(directory: Optional[str] = None) -> dict:
    """Scan a directory for YAML template files and sync them to the database.

    For each file:
    - If no DB row exists for the purpose_key: create version 1 (active).
    - If a DB row exists but content differs: bump version, deactivate old,
      create new active version.
    - If a DB row exists and content matches: skip (no-op).

    Templates created via the UI (with purpose_keys that have no matching file)
    are left untouched.

    Args:
        directory: Path to template directory. Defaults to ``email_templates/``
                   relative to the repository root.

    Returns:
        Dict with counts: {"created": N, "updated": N, "skipped": N, "errors": N}
    """
    if directory is None:
        # Resolve relative to the repo root (two levels up from utils/)
        repo_root = Path(__file__).resolve().parent.parent
        directory = str(repo_root / DEFAULT_TEMPLATE_DIR)

    template_dir = Path(directory)
    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    if not template_dir.is_dir():
        logger.warning(
            "Email template directory not found: %s — skipping sync", template_dir
        )
        return stats

    yaml_files = sorted(template_dir.glob("*.yaml")) + sorted(
        template_dir.glob("*.yml")
    )

    if not yaml_files:
        logger.info("No template files found in %s", template_dir)
        return stats

    for filepath in yaml_files:
        parsed = _parse_template_file(filepath)
        if parsed is None:
            stats["errors"] += 1
            continue

        purpose_key = parsed["purpose_key"]
        file_hash = _content_hash(
            parsed["subject_template"],
            parsed["html_template"],
            parsed["text_template"],
        )

        # Find the currently active template for this purpose_key
        existing = (
            EmailTemplate.query.filter_by(purpose_key=purpose_key, is_active=True)
            .order_by(EmailTemplate.version.desc())
            .first()
        )

        if existing is None:
            # Also check for any inactive versions (in case all were deactivated)
            any_existing = (
                EmailTemplate.query.filter_by(purpose_key=purpose_key)
                .order_by(EmailTemplate.version.desc())
                .first()
            )

            if any_existing is None:
                # Brand new template — create version 1
                template = EmailTemplate(
                    purpose_key=purpose_key,
                    version=1,
                    name=parsed["name"],
                    description=parsed["description"],
                    subject_template=parsed["subject_template"],
                    html_template=parsed["html_template"],
                    text_template=parsed["text_template"],
                    required_placeholders=parsed["required_placeholders"],
                    optional_placeholders=parsed["optional_placeholders"],
                    is_active=True,
                )
                db.session.add(template)
                stats["created"] += 1
                logger.info(
                    "Template sync: created '%s' v1 from %s",
                    purpose_key,
                    filepath.name,
                )
            else:
                # Versions exist but none active — check if content changed
                existing_hash = _content_hash(
                    any_existing.subject_template,
                    any_existing.html_template,
                    any_existing.text_template,
                )
                if existing_hash == file_hash:
                    # Same content, just re-activate the latest version
                    any_existing.is_active = True
                    stats["skipped"] += 1
                    logger.debug(
                        "Template sync: re-activated '%s' v%d (unchanged)",
                        purpose_key,
                        any_existing.version,
                    )
                else:
                    # Content changed — create new version
                    new_version = any_existing.version + 1
                    template = EmailTemplate(
                        purpose_key=purpose_key,
                        version=new_version,
                        name=parsed["name"],
                        description=parsed["description"],
                        subject_template=parsed["subject_template"],
                        html_template=parsed["html_template"],
                        text_template=parsed["text_template"],
                        required_placeholders=parsed["required_placeholders"],
                        optional_placeholders=parsed["optional_placeholders"],
                        is_active=True,
                    )
                    db.session.add(template)
                    stats["updated"] += 1
                    logger.info(
                        "Template sync: updated '%s' to v%d from %s",
                        purpose_key,
                        new_version,
                        filepath.name,
                    )
        else:
            # Active template exists — check if content changed
            existing_hash = _content_hash(
                existing.subject_template,
                existing.html_template,
                existing.text_template,
            )

            if existing_hash == file_hash:
                # No changes
                stats["skipped"] += 1
                logger.debug(
                    "Template sync: skipped '%s' v%d (unchanged)",
                    purpose_key,
                    existing.version,
                )
            else:
                # Content changed — deactivate old, create new version
                new_version = existing.version + 1

                # Deactivate all versions for this purpose_key
                EmailTemplate.query.filter_by(purpose_key=purpose_key).update(
                    {"is_active": False}
                )

                template = EmailTemplate(
                    purpose_key=purpose_key,
                    version=new_version,
                    name=parsed["name"],
                    description=parsed["description"],
                    subject_template=parsed["subject_template"],
                    html_template=parsed["html_template"],
                    text_template=parsed["text_template"],
                    required_placeholders=parsed["required_placeholders"],
                    optional_placeholders=parsed["optional_placeholders"],
                    is_active=True,
                )
                db.session.add(template)
                stats["updated"] += 1
                logger.info(
                    "Template sync: updated '%s' to v%d from %s",
                    purpose_key,
                    new_version,
                    filepath.name,
                )

    db.session.commit()

    total = stats["created"] + stats["updated"] + stats["skipped"]
    logger.info(
        "Template sync complete: %d created, %d updated, %d unchanged, %d errors "
        "(from %d files)",
        stats["created"],
        stats["updated"],
        stats["skipped"],
        stats["errors"],
        len(yaml_files),
    )

    return stats

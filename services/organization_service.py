"""
Organization Name Resolution Service
====================================

Provides database-driven organization name resolution with auto-learning alias algorithms.
Implemented as part of Epic 19 (Organization Alias Resolution).

Usage:
    from services.organization_service import resolve_organization

    org = resolve_organization("Prep-KC, Inc.")
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

from flask import current_app

if TYPE_CHECKING:
    from models.organization import Organization

logger = logging.getLogger(__name__)


def clean_organization_suffix(name: str) -> str:
    """
    Strips common corporate suffixes and punctuation for fallback matching.
    e.g., "Prep-KC, Inc." -> "prepkc"
    """
    if not name:
        return ""

    # 1. Lowercase and strip whitespace
    clean = name.lower().strip()

    # 2. Remove all punctuation (commas, periods, hyphens, ampersands, quotes)
    clean = re.sub(r'[.,\-&\'"]', "", clean)

    # 3. Strip common corporate suffixes
    # Using \b to ensure we only strip whole words at the end or standalone
    suffixes = r"\b(inc|llc|company|corp|co|ltd|incorporated|corporation|group)\b"
    clean = re.sub(suffixes, "", clean)

    # 4. Final trim of any remaining whitespace or dangling characters
    return clean.strip()


def resolve_organization(
    name: str, caches: Optional[dict] = None
) -> Optional["Organization"]:
    """
    Resolve an organization name to an Organization model instance.

    Implements a strict 4-Tier lookup strategy (TD-052):
      1. Runtime Cache (Fastest) - if provided
      2. Exact Match (Case-insensitive DB query on Organization.name)
      3. Alias Match (Case-insensitive DB query on OrganizationAlias.name)
      4. Auto-Learning Suffix Stripper (Fallback regex matching)

    Returns None and logs a warning if the name cannot be resolved.
    """
    if not name or not name.strip():
        return None

    name = name.strip()

    from sqlalchemy import func

    from models import db
    from models.organization import Organization, OrganizationAlias

    # Tier 1: Cache Match
    if caches and "organization_by_name" in caches:
        cached_org = caches["organization_by_name"].get(name.lower())
        if cached_org:
            return cached_org

    # Tier 2: Exact Name Match (Case-Insensitive)
    org = Organization.query.filter(
        func.lower(Organization.name) == func.lower(name)
    ).first()
    if org:
        return org

    # Tier 3: Alias Match (Case-Insensitive)
    alias_row = OrganizationAlias.query.filter(
        func.lower(OrganizationAlias.name) == func.lower(name)
    ).first()
    if alias_row:
        return alias_row.organization

    # Tier 4: Suffix-Stripper Regex & Auto-Learning
    stripped_name = clean_organization_suffix(name)

    # If stripping didn't actually change anything meaningful, we can't learn from it
    if not stripped_name or stripped_name == name.lower().strip():
        logger.warning("Could not resolve organization name: '%s'", name)
        return None

    # Load all orgs to find a match for the stripped string
    # (Since we cleaned all DB orgs in Phase 0, we can safely compare stripped strings)
    all_orgs = Organization.query.all()

    fallback_match = None
    for candidate in all_orgs:
        if (
            candidate.name
            and clean_organization_suffix(candidate.name) == stripped_name
        ):
            fallback_match = candidate
            break

    if fallback_match:
        # We found a match using the fallback logic!
        # AUTO-LEARNING: Create a permanent OrganizationAlias so Tier 3 catches it instantly next time.
        logger.info(
            "Auto-learning OrganizationAlias: '%s' -> '%s' (ID %s)",
            name,
            fallback_match.name,
            fallback_match.id,
        )
        try:
            new_alias = OrganizationAlias(
                organization_id=fallback_match.id, name=name, is_auto_generated=True
            )
            db.session.add(new_alias)
            db.session.flush()  # Use flush instead of commit to protect outer transactions
        except Exception as e:
            # Handle possible race conditions or integrity errors securely
            db.session.rollback()
            logger.warning("Failed to auto-learn OrganizationAlias '%s': %s", name, e)

        return fallback_match

    # Not found at all
    logger.warning("Could not resolve organization name via any tier: '%s'", name)
    return None

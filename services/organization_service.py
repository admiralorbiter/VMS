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

    # Tier 4: Suffix-Stripper Regex (read-only probe)
    # B2: We no longer auto-learn aliases here. Instead we return None and let
    # the caller (_ensure_volunteer_org_link) create a quarantine ticket with
    # the near-match candidate embedded in raw_data for admin confirmation.
    # The alias is only written AFTER admin clicks "Confirm" in the quarantine UI.
    stripped_name = clean_organization_suffix(name)

    if not stripped_name or stripped_name == name.lower().strip():
        logger.warning("Could not resolve organization name: '%s'", name)
        return None

    # If a near-match exists, log it but do NOT write the alias.
    candidate = find_org_near_match(name)
    if candidate:
        logger.info(
            "Near-org match found (T4, quarantine-first): '%s' ~~ '%s' (ID %s). "
            "Queuing for admin confirmation instead of auto-learning alias.",
            name,
            candidate.name,
            candidate.id,
        )

    # Not found at all (or found but quarantined)
    logger.warning("Could not resolve organization name via any tier: '%s'", name)
    return None


def find_org_near_match(name: str) -> "Organization | None":
    """
    Probe-only version of the T4 suffix-strip logic.

    Returns the Organization that would have been auto-aliased by the old T4
    logic, WITHOUT writing anything to the database. Used by callers that want
    to surface the near-match candidate to an admin for confirmation.

    Returns None if no near-match is found.
    """
    if not name or not name.strip():
        return None

    from models.organization import Organization

    stripped_name = clean_organization_suffix(name.strip())
    if not stripped_name or stripped_name == name.strip().lower():
        return None

    all_orgs = Organization.query.all()
    for candidate in all_orgs:
        if (
            candidate.name
            and clean_organization_suffix(candidate.name) == stripped_name
        ):
            return candidate
    return None

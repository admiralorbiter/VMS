"""
District Name Resolution Service
=================================

Provides database-driven district name resolution, replacing the former
hardcoded DISTRICT_MAPPINGS dict in routes/utils.py (TD-010).

Usage:
    from services.district_service import resolve_district

    district = resolve_district("KCKPS")        # alias lookup
    district = resolve_district("GRANDVIEW C-4") # exact name match
"""

import logging
from typing import TYPE_CHECKING, Optional

from flask import current_app

if TYPE_CHECKING:
    from models.district_model import District

logger = logging.getLogger(__name__)

# ── Legacy alias seed data ────────────────────────────────────────────
# These are the 6 *real* aliases from the old DISTRICT_MAPPINGS dict.
# Identity mappings (key == value) are handled by the exact-name lookup
# in resolve_district(), so they do not need alias rows.
_LEGACY_ALIASES = {
    "KCKPS": "Kansas City Kansas Public Schools",
    "KCPS": "Kansas City Public Schools (MO)",
    "Hickman Mills": "Hickman Mills School District",
    "Grandview": "Grandview School District",
    "Center": "Center School District",
    "Allen Village": "Allen Village - District",
}


def resolve_district(name: str) -> Optional["District"]:
    """
    Resolve a district name (or alias) to a District model instance.

    Resolution order:
      1. Exact match on District.name
      2. Exact match on DistrictAlias.alias
      3. Case-insensitive match on District.name
      4. Case-insensitive match on DistrictAlias.alias

    Returns None and logs a warning if the name cannot be resolved.
    """
    if not name or not name.strip():
        return None

    name = name.strip()

    from models.district_model import District, DistrictAlias

    # 1. Exact name match (fastest, indexed)
    district = District.query.filter_by(name=name).first()
    if district:
        return district

    # 2. Exact alias match (indexed)
    alias_row = DistrictAlias.query.filter_by(alias=name).first()
    if alias_row:
        return alias_row.district

    # 3. Case-insensitive name match
    from sqlalchemy import func

    district = District.query.filter(
        func.lower(District.name) == func.lower(name)
    ).first()
    if district:
        return district

    # 4. Case-insensitive alias match
    alias_row = DistrictAlias.query.filter(
        func.lower(DistrictAlias.alias) == func.lower(name)
    ).first()
    if alias_row:
        return alias_row.district

    # Not found
    logger.warning(f"Could not resolve district name: '{name}'")
    return None


def seed_district_aliases() -> dict:
    """
    Seed the district_alias table from the legacy DISTRICT_MAPPINGS data.

    Only creates aliases where the target district exists in the DB and the
    alias doesn't already exist. Safe to run multiple times (idempotent).

    Returns a summary dict with counts of created, skipped, and missing aliases.
    """
    from models import db
    from models.district_model import District, DistrictAlias

    created = 0
    skipped = 0
    missing = []

    for alias_name, canonical_name in _LEGACY_ALIASES.items():
        # Skip if alias already exists
        existing = DistrictAlias.query.filter_by(alias=alias_name).first()
        if existing:
            skipped += 1
            continue

        # Find the target district
        district = District.query.filter_by(name=canonical_name).first()
        if not district:
            # Try case-insensitive
            from sqlalchemy import func

            district = District.query.filter(
                func.lower(District.name) == func.lower(canonical_name)
            ).first()

        if not district:
            missing.append(f"{alias_name} → {canonical_name} (district not found)")
            continue

        alias = DistrictAlias(alias=alias_name, district_id=district.id)
        db.session.add(alias)
        created += 1

    db.session.commit()

    summary = {
        "created": created,
        "skipped": skipped,
        "missing": missing,
    }
    logger.info(f"seed_district_aliases: {summary}")
    return summary

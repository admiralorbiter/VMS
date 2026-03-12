"""
Name Normalization Utilities
============================

Provides smart title-casing for names imported from Salesforce,
handling common prefixes (Mc, Mac, O', De, etc.) and hyphenated names.

Usage:
    from routes.name_utils import smart_title_case
    normalized = smart_title_case("O'BRIEN")  # -> "O'Brien"
"""

import re

# Prefixes that should keep the next character capitalized
_MC_MAC_PATTERN = re.compile(r"^(Mc|Mac)(\w)", re.IGNORECASE)

# Particles that should be lowercase (unless at start of name)
_LOWERCASE_PARTICLES = {"de", "del", "di", "la", "le", "van", "von", "el", "al"}


def smart_title_case(name):
    """
    Normalize a name to smart title case.

    Handles:
    - O'BRIEN -> O'Brien
    - MCCARTHY -> McCarthy
    - MACDONALD -> MacDonald
    - DE LA CRUZ -> De La Cruz
    - JEAN-PIERRE -> Jean-Pierre
    - Simple names: JOHN -> John

    Args:
        name: Raw name string (may be ALL CAPS, lowercase, or mixed)

    Returns:
        Properly cased name string, or the original if empty/None
    """
    if not name or not name.strip():
        return name

    name = name.strip()

    # Don't modify names that are already mixed case (likely correct)
    # A name is "ALL CAPS" if it has letters and all letters are uppercase
    has_letters = any(c.isalpha() for c in name)
    if has_letters and name != name.upper():
        return name

    # Process each part separated by spaces
    parts = name.split()
    result_parts = []

    for i, part in enumerate(parts):
        result_parts.append(_title_case_part(part))

    return " ".join(result_parts)


def _title_case_part(part):
    """
    Title-case a single name part, handling hyphens and special prefixes.
    """
    if not part:
        return part

    # Handle hyphenated names: JEAN-PIERRE -> Jean-Pierre
    if "-" in part:
        return "-".join(_title_case_part(sub) for sub in part.split("-"))

    # Handle apostrophes: O'BRIEN -> O'Brien
    if "'" in part:
        segments = part.split("'")
        return "'".join(seg.capitalize() if seg else seg for seg in segments)

    # Basic title case first
    titled = part.capitalize()

    # Handle Mc/Mac prefixes: MCCARTHY -> McCarthy, MACDONALD -> MacDonald
    mc_match = _MC_MAC_PATTERN.match(titled)
    if mc_match and len(part) > 3:  # Only for names longer than "Mac"
        prefix = mc_match.group(1)
        next_char = mc_match.group(2).upper()
        rest = titled[len(prefix) + 1 :]
        titled = f"{prefix}{next_char}{rest}"

    return titled


def is_all_caps_name(name):
    """
    Check if a name appears to be improperly ALL CAPS.

    Returns True only for names with 2+ letters that are all uppercase.
    Single-letter names and names with no letters return False.
    """
    if not name or len(name) < 2:
        return False
    has_letters = any(c.isalpha() for c in name)
    return has_letters and name == name.upper() and name != name.lower()

"""
Teacher Matching Service
========================

Shared utilities for matching teacher names to virtual session educators.
Used by both virtual usage routes and tenant teacher usage routes.

The service provides flexible name matching that handles:
- Case differences (Amy Otto vs AMY OTTO)
- Punctuation (O'Brien vs OBrien)
- Hyphenation (Mary Smith-Jones vs Mary Smith Jones)
- First/Last name ordering
"""

from typing import Any, Dict, List, Optional


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison by removing punctuation and lowercasing.

    Args:
        name: The name to normalize

    Returns:
        Normalized lowercase name with punctuation removed
    """
    if not name:
        return ""
    return (
        name.lower()
        .strip()
        .replace("-", " ")
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
    )


def build_teacher_alias_map(
    teachers: List[Any],
) -> tuple[Dict[int, int], Dict[str, int]]:
    """
    Build maps for teacher matching.

    Creates a progress counter map and an alias map that maps various
    name variations to teacher IDs for flexible matching.

    Args:
        teachers: List of teacher objects with id, name attributes

    Returns:
        tuple: (progress_map, alias_map)
            - progress_map: Dict[teacher_id, session_count] initialized to 0
            - alias_map: Dict[normalized_name, teacher_id]
    """
    teacher_progress_map = {}  # teacher_id -> completed_count
    teacher_alias_map = {}  # normalized_name -> teacher_id

    for teacher in teachers:
        teacher_progress_map[teacher.id] = 0

        # Create name variations for matching
        base_name = teacher.name.lower().strip()
        normalized = normalize_name(teacher.name)

        name_variations = [
            base_name,
            normalized,
        ]

        # Add first + last name variation if different from stored name
        parts = teacher.name.split()
        if len(parts) > 1:
            first_last = f"{parts[0]} {parts[-1]}".lower()
            name_variations.append(first_last)
            name_variations.append(normalize_name(first_last))

        # Store aliases pointing to teacher id
        for name_var in name_variations:
            if name_var:
                teacher_alias_map[name_var] = teacher.id

    return teacher_progress_map, teacher_alias_map


def match_educator_to_teacher(
    educator_name: str, alias_map: Dict[str, int], min_name_length: int = 3
) -> Optional[int]:
    """
    Match an educator name string to a teacher ID using flexible matching.

    Tries exact match first, then falls back to partial/fuzzy matching.

    Args:
        educator_name: The educator name from the session
        alias_map: Map of normalized names to teacher IDs
        min_name_length: Minimum name length for partial matching

    Returns:
        teacher_id if matched, None otherwise
    """
    if not educator_name:
        return None

    educator_key = educator_name.lower().strip()
    educator_normalized = normalize_name(educator_name)

    # Try exact match first
    teacher_id = alias_map.get(educator_key) or alias_map.get(educator_normalized)

    if teacher_id:
        return teacher_id

    # Try flexible matching - look for partial matches
    if len(educator_key) > min_name_length:
        for name_key, alias_teacher_id in alias_map.items():
            name_key_normalized = normalize_name(name_key)

            # Check if either version matches (partial match)
            if (
                educator_key in name_key
                or name_key in educator_key
                or educator_normalized in name_key_normalized
                or name_key_normalized in educator_normalized
            ):
                return alias_teacher_id

    return None


def count_sessions_for_teachers(
    events: List[Any], alias_map: Dict[str, int], progress_map: Dict[int, int]
) -> Dict[int, int]:
    """
    Count completed sessions for each teacher based on Event.educators field.

    Parses the semicolon-separated educators field from each event and
    matches names to teachers using the alias map.

    Args:
        events: List of Event objects with educators attribute
        alias_map: Map of normalized names to teacher IDs
        progress_map: Map of teacher IDs to session counts (will be modified)

    Returns:
        Updated progress_map with session counts
    """
    for event in events:
        if not event.educators:
            continue

        # Parse semicolon-separated educator names
        educator_names = [
            name.strip() for name in event.educators.split(";") if name.strip()
        ]

        for educator_name in educator_names:
            teacher_id = match_educator_to_teacher(educator_name, alias_map)

            if teacher_id and teacher_id in progress_map:
                progress_map[teacher_id] += 1

    return progress_map

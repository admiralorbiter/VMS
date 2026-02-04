"""
Salesforce Field Mappers
=========================

Centralized mapping definitions for converting Salesforce field values
to Polaris database enum values. This module consolidates all Salesforce-to-enum
mapping logic that was previously scattered throughout route handlers.

Usage:
    from services.salesforce import (
        map_education_level,
        map_race_ethnicity,
        map_age_group,
        map_participation_status
    )

    # Map Salesforce education value to enum name
    edu_enum_name = map_education_level("Bachelor's Degree")  # Returns "BACHELORS_DEGREE"

    # Map race/ethnicity with fallback
    race_enum_name = map_race_ethnicity("Hispanic American/Latino")  # Returns "hispanic"
"""

from typing import Optional

# =============================================================================
# EDUCATION LEVEL MAPPING
# =============================================================================
# Maps Salesforce education values to EducationEnum values
# Handles various capitalization and phrasing variations

EDUCATION_MAPPING = {
    # Exact matches
    "BACHELORS": "BACHELORS_DEGREE",
    "MASTERS": "MASTERS",
    "DOCTORATE": "DOCTORATE",
    # Common variations
    "BACHELOR": "BACHELORS_DEGREE",
    "BACHELOR'S": "BACHELORS_DEGREE",
    "BACHELORS DEGREE": "BACHELORS_DEGREE",
    "BACHELOR'S DEGREE": "BACHELORS_DEGREE",
    "MASTER": "MASTERS",
    "MASTER'S": "MASTERS",
    "MASTERS DEGREE": "MASTERS",
    "MASTER'S DEGREE": "MASTERS",
    "PHD": "DOCTORATE",
    "PH.D": "DOCTORATE",
    "PH.D.": "DOCTORATE",
    "DOCTORAL": "DOCTORATE",
    # Salesforce specific values
    "HIGH SCHOOL DIPLOMA OR GED": "HIGH_SCHOOL",
    "ADVANCED PROFESSIONAL DEGREE": "PROFESSIONAL",
    "PREFER NOT TO ANSWER": "UNKNOWN",
    # Other credentials
    "CERTIFICATE": "OTHER",
    "CERTIFICATION": "OTHER",
    "ASSOCIATE": "ASSOCIATES",
    "ASSOCIATES": "ASSOCIATES",
    "ASSOCIATE'S": "ASSOCIATES",
    "ASSOCIATE'S DEGREE": "ASSOCIATES",
    "HIGH SCHOOL": "HIGH_SCHOOL",
    "GED": "HIGH_SCHOOL",
    "SOME COLLEGE": "SOME_COLLEGE",
    "PROFESSIONAL": "PROFESSIONAL",
    "PROFESSIONAL DEGREE": "PROFESSIONAL",
}


def map_education_level(value: Optional[str], default: str = "UNKNOWN") -> str:
    """
    Map a Salesforce education level value to the corresponding enum name.

    Args:
        value: Salesforce education field value
        default: Default enum name if no mapping found

    Returns:
        String enum name suitable for EducationEnum[name]
    """
    if not value:
        return default
    normalized = value.strip().upper()
    return EDUCATION_MAPPING.get(normalized, default)


# =============================================================================
# RACE/ETHNICITY MAPPING
# =============================================================================
# Maps Salesforce racial/ethnic background values to RaceEthnicityEnum names

RACE_ETHNICITY_MAPPING = {
    # Hispanic/Latino variations
    "Hispanic American/Latino": "hispanic",
    "Hispanic or Latino": "hispanic",
    "Hispanic": "hispanic",
    "Latino": "hispanic",
    "Latina": "hispanic",
    # Black/African American variations
    "Black": "black",
    "Black/African American": "black",
    "African American": "black",
    "Black or African American": "black",
    # White variations
    "White": "white",
    "White/Caucasian/European American": "white",
    "Caucasian": "white",
    "European American": "white",
    # Asian variations
    "Asian": "asian",
    "Asian American": "asian",
    "Asian American/Pacific Islander": "asian",
    # Pacific Islander variations
    "Pacific Islander": "native_hawaiian",
    "Native Hawaiian": "native_hawaiian",
    "Native Hawaiian or Other Pacific Islander": "native_hawaiian",
    # American Indian/Alaska Native variations
    "American Indian or Alaska Native": "american_indian",
    "Native American": "american_indian",
    "Alaska Native": "american_indian",
    "Native American/Alaska Native/First Nation": "american_indian",
    "First Nation": "american_indian",
    # Multi-racial variations
    "Bi-racial": "bi_racial",
    "Multi-racial": "multi_racial",
    "Bi-racial/Multi-racial/Multicultural": "multi_racial",
    "Two or More Races": "two_or_more",
    "Two or more": "two_or_more",
    # Other variations
    "Other": "other",
    "Other POC": "other_poc",
    # Prefer not to say variations
    "Prefer not to answer": "prefer_not_to_say",
    "Prefer not to say": "prefer_not_to_say",
}

# Lowercase lookup for case-insensitive matching
_RACE_ETHNICITY_LOWER = {k.lower(): v for k, v in RACE_ETHNICITY_MAPPING.items()}


def map_race_ethnicity(
    value: Optional[str], default: Optional[str] = None
) -> Optional[str]:
    """
    Map a Salesforce racial/ethnic background value to the corresponding enum name.

    Attempts exact match first, then case-insensitive match, then partial matching
    for common patterns (hispanic, black, white, asian, etc.).

    Args:
        value: Salesforce Racial_Ethnic_Background__c field value
        default: Default enum name if no mapping found

    Returns:
        String enum name suitable for RaceEthnicityEnum[name], or default if not found
    """
    if not value or value == "None":
        return default

    cleaned = value.strip()
    if "AggregateResult" in cleaned:
        cleaned = cleaned.replace("AggregateResult", "").strip()

    # Try exact match first
    if cleaned in RACE_ETHNICITY_MAPPING:
        return RACE_ETHNICITY_MAPPING[cleaned]

    # Try case-insensitive match
    lower = cleaned.lower()
    if lower in _RACE_ETHNICITY_LOWER:
        return _RACE_ETHNICITY_LOWER[lower]

    # Try partial matching for common patterns
    if any(term in lower for term in ["hispanic", "latino", "latina"]):
        return "hispanic"
    if any(term in lower for term in ["black", "african american"]):
        return "black"
    if any(term in lower for term in ["white", "caucasian"]):
        return "white"
    if "asian" in lower:
        return "asian"
    if any(term in lower for term in ["pacific islander", "hawaiian"]):
        return "native_hawaiian"
    if any(
        term in lower
        for term in [
            "native american",
            "alaska native",
            "first nation",
            "american indian",
        ]
    ):
        return "american_indian"
    if any(term in lower for term in ["multi", "bi-racial", "two or more"]):
        return "multi_racial"
    if "prefer not" in lower:
        return "prefer_not_to_say"
    if "other" in lower:
        return "other"

    return default


# =============================================================================
# AGE GROUP MAPPING
# =============================================================================
# Maps Salesforce age group string values to AgeGroupEnum string names
# Uses string names to avoid circular imports; caller converts to enum

AGE_GROUP_MAPPING = {
    "Under 18": "UNDER_18",
    "18-24": "AGE_18_24",
    "25-34": "AGE_25_34",
    "35-44": "AGE_35_44",
    "45-54": "AGE_45_54",
    "55-64": "AGE_55_64",
    "65+": "AGE_65_PLUS",
}


def map_age_group(value: Optional[str]):
    """
    Map a Salesforce age group value to the corresponding AgeGroupEnum.

    Args:
        value: Salesforce Age_Group__c field value

    Returns:
        AgeGroupEnum value (UNKNOWN if not found)
    """
    # Lazy import to avoid circular dependency
    from models.contact import AgeGroupEnum

    if not value:
        return AgeGroupEnum.UNKNOWN
    cleaned = value.strip()
    enum_name = AGE_GROUP_MAPPING.get(cleaned, "UNKNOWN")
    return AgeGroupEnum[enum_name]


# =============================================================================
# GRADE LEVEL MAPPING
# =============================================================================
# Maps Salesforce grade level values to GradeLevelEnum names

GRADE_LEVEL_MAPPING = {
    "K": "KINDERGARTEN",
    "Kindergarten": "KINDERGARTEN",
    "1": "FIRST",
    "1st": "FIRST",
    "2": "SECOND",
    "2nd": "SECOND",
    "3": "THIRD",
    "3rd": "THIRD",
    "4": "FOURTH",
    "4th": "FOURTH",
    "5": "FIFTH",
    "5th": "FIFTH",
    "6": "SIXTH",
    "6th": "SIXTH",
    "7": "SEVENTH",
    "7th": "SEVENTH",
    "8": "EIGHTH",
    "8th": "EIGHTH",
    "9": "NINTH",
    "9th": "NINTH",
    "10": "TENTH",
    "10th": "TENTH",
    "11": "ELEVENTH",
    "11th": "ELEVENTH",
    "12": "TWELFTH",
    "12th": "TWELFTH",
}


def map_grade_level(value: Optional[str], default: str = "UNKNOWN") -> str:
    """
    Map a Salesforce grade level value to the corresponding enum name.

    Args:
        value: Salesforce grade level field value
        default: Default enum name if no mapping found

    Returns:
        String enum name suitable for GradeLevelEnum[name]
    """
    if not value:
        return default
    cleaned = value.strip()
    return GRADE_LEVEL_MAPPING.get(cleaned, default)


# =============================================================================
# PARTICIPATION STATUS MAPPING
# =============================================================================
# Maps various event participation status strings to normalized status values

PARTICIPATION_STATUS_MAPPING = {
    # Standard statuses
    "Attended": "Attended",
    "Completed": "Attended",
    "No-Show": "No-Show",
    "No Show": "No-Show",
    "NoShow": "No-Show",
    "Cancelled": "Cancelled",
    "Canceled": "Cancelled",
    "canceled": "Cancelled",
    "cancelled": "Cancelled",
    "CANCELLED": "Cancelled",
    "CANCELED": "Cancelled",
    "Scheduled": "Scheduled",
    "scheduled": "Scheduled",
    # Virtual-specific statuses
    "successfully completed": "Attended",
    "simulcast": "Attended",
    "technical difficulties": "No-Show",
    "local professional no-show": "No-Show",
    "pathful professional no-show": "No-Show",
    "teacher no-show": "No-Show",
    "teacher cancelation": "Cancelled",
    "teacher cancellation": "Cancelled",
    "Confirmed": "Attended",
    # Additional variations
    "Present": "Attended",
    "Absent": "No-Show",
    "Did Not Attend": "No-Show",
    "DID NOT ATTEND": "No-Show",
    "Event Cancelled": "Cancelled",
    "Event Canceled": "Cancelled",
    "EVENT CANCELLED": "Cancelled",
    "EVENT CANCELED": "Cancelled",
}


def map_participation_status(value: Optional[str], default: str = "Unknown") -> str:
    """
    Map a participation status string to a normalized status value.

    Args:
        value: Raw status string from participation record or event
        default: Default status if no mapping found

    Returns:
        Normalized status string: "Attended", "No-Show", "Cancelled", "Scheduled", or "Unknown"
    """
    if not value:
        return default

    # Try direct match first
    if value in PARTICIPATION_STATUS_MAPPING:
        return PARTICIPATION_STATUS_MAPPING[value]

    # Try lowercase match
    lower = value.lower()
    if lower in PARTICIPATION_STATUS_MAPPING:
        return PARTICIPATION_STATUS_MAPPING[lower]

    return default

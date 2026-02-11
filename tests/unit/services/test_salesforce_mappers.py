"""
Unit Tests for Salesforce Mapper Functions
==========================================

Comprehensive test suite for the field mapping functions used during
Salesforce data import. Tests cover all enum mappings, null handling,
edge cases, and case-insensitivity.

Coverage targets:
- map_education_level: All mappings + null + unknown values
- map_race_ethnicity: Exact match, case-insensitive, partial match, edge cases
- map_age_group: All age ranges + null handling
- map_grade_level: All grades K-12 + null handling
- map_participation_status: All statuses + case variations
"""

from unittest.mock import MagicMock, patch

import pytest

from services.salesforce.mappers import (
    AGE_GROUP_MAPPING,
    EDUCATION_MAPPING,
    GRADE_LEVEL_MAPPING,
    PARTICIPATION_STATUS_MAPPING,
    RACE_ETHNICITY_MAPPING,
    map_age_group,
    map_education_level,
    map_grade_level,
    map_participation_status,
    map_race_ethnicity,
)

# =============================================================================
# EDUCATION LEVEL MAPPING TESTS
# =============================================================================


class TestMapEducationLevel:
    """Tests for map_education_level function."""

    def test_null_value_returns_default(self):
        """Null/None values should return default."""
        assert map_education_level(None) == "UNKNOWN"
        assert map_education_level("") == "UNKNOWN"
        assert map_education_level(None, "OTHER") == "OTHER"

    def test_exact_matches_uppercase(self):
        """Test exact uppercase matches."""
        assert map_education_level("BACHELORS") == "BACHELORS_DEGREE"
        assert map_education_level("MASTERS") == "MASTERS"
        assert map_education_level("DOCTORATE") == "DOCTORATE"

    def test_common_variations(self):
        """Test common phrasing variations."""
        # Bachelor variations
        assert map_education_level("Bachelor") == "BACHELORS_DEGREE"
        assert map_education_level("Bachelor's") == "BACHELORS_DEGREE"
        assert map_education_level("Bachelors Degree") == "BACHELORS_DEGREE"
        assert map_education_level("Bachelor's Degree") == "BACHELORS_DEGREE"

        # Master variations
        assert map_education_level("Master") == "MASTERS"
        assert map_education_level("Master's") == "MASTERS"
        assert map_education_level("Masters Degree") == "MASTERS"
        assert map_education_level("Master's Degree") == "MASTERS"

        # PhD variations
        assert map_education_level("PhD") == "DOCTORATE"
        assert map_education_level("Ph.D") == "DOCTORATE"
        assert map_education_level("Ph.D.") == "DOCTORATE"
        assert map_education_level("Doctoral") == "DOCTORATE"

    def test_salesforce_specific_values(self):
        """Test Salesforce-specific education values."""
        assert map_education_level("High School Diploma or GED") == "HIGH_SCHOOL"
        assert map_education_level("Advanced Professional Degree") == "PROFESSIONAL"
        assert map_education_level("Prefer not to answer") == "UNKNOWN"

    def test_other_credentials(self):
        """Test other credential types."""
        assert map_education_level("Certificate") == "OTHER"
        assert map_education_level("Certification") == "OTHER"
        assert map_education_level("Associate") == "ASSOCIATES"
        assert map_education_level("Associates") == "ASSOCIATES"
        assert map_education_level("Associate's") == "ASSOCIATES"
        assert map_education_level("High School") == "HIGH_SCHOOL"
        assert map_education_level("GED") == "HIGH_SCHOOL"
        assert map_education_level("Some College") == "SOME_COLLEGE"
        assert map_education_level("Professional") == "PROFESSIONAL"

    def test_case_insensitivity(self):
        """Test that mapping is case-insensitive."""
        assert map_education_level("bachelors") == "BACHELORS_DEGREE"
        assert map_education_level("MASTERS") == "MASTERS"
        assert map_education_level("doctorate") == "DOCTORATE"
        assert map_education_level("PhD") == "DOCTORATE"

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is stripped."""
        assert map_education_level("  Bachelors  ") == "BACHELORS_DEGREE"
        assert map_education_level("\tMasters\n") == "MASTERS"

    def test_unknown_value_returns_default(self):
        """Unknown values should return the default."""
        assert map_education_level("Some Random Education") == "UNKNOWN"
        assert map_education_level("XYZ Degree") == "UNKNOWN"
        assert map_education_level("Unknown Value", "FALLBACK") == "FALLBACK"


# =============================================================================
# RACE/ETHNICITY MAPPING TESTS
# =============================================================================


class TestMapRaceEthnicity:
    """Tests for map_race_ethnicity function."""

    def test_null_value_returns_default(self):
        """Null/None values should return default."""
        assert map_race_ethnicity(None) is None
        assert map_race_ethnicity("") is None
        assert map_race_ethnicity("None") is None
        assert map_race_ethnicity(None, "other") == "other"

    def test_exact_matches(self):
        """Test exact string matches from mapping."""
        assert map_race_ethnicity("Hispanic American/Latino") == "hispanic"
        assert map_race_ethnicity("Black/African American") == "black"
        assert map_race_ethnicity("White") == "white"
        assert map_race_ethnicity("Asian") == "asian"
        assert map_race_ethnicity("Pacific Islander") == "native_hawaiian"
        assert (
            map_race_ethnicity("American Indian or Alaska Native") == "american_indian"
        )

    def test_case_insensitive_matches(self):
        """Test case-insensitive matching."""
        assert map_race_ethnicity("HISPANIC") == "hispanic"
        assert map_race_ethnicity("black") == "black"
        assert map_race_ethnicity("WHITE") == "white"
        assert map_race_ethnicity("asian") == "asian"

    def test_partial_matching_hispanic(self):
        """Test partial matching for Hispanic/Latino."""
        assert map_race_ethnicity("Some Hispanic Background") == "hispanic"
        assert map_race_ethnicity("Latino/Other") == "hispanic"
        assert map_race_ethnicity("Latina Heritage") == "hispanic"

    def test_partial_matching_black(self):
        """Test partial matching for Black/African American."""
        assert map_race_ethnicity("Black mixed") == "black"
        assert map_race_ethnicity("Part African American") == "black"

    def test_partial_matching_white(self):
        """Test partial matching for White/Caucasian."""
        assert map_race_ethnicity("White European") == "white"
        assert map_race_ethnicity("Caucasian American") == "white"

    def test_partial_matching_asian(self):
        """Test partial matching for Asian."""
        assert map_race_ethnicity("East Asian") == "asian"
        assert map_race_ethnicity("South Asian American") == "asian"

    def test_partial_matching_pacific_islander(self):
        """Test partial matching for Pacific Islander."""
        assert map_race_ethnicity("Pacific Islander descent") == "native_hawaiian"
        assert map_race_ethnicity("Hawaiian heritage") == "native_hawaiian"

    def test_partial_matching_american_indian(self):
        """Test partial matching for American Indian/Alaska Native."""
        assert map_race_ethnicity("Native American heritage") == "american_indian"
        assert map_race_ethnicity("Alaska Native descent") == "american_indian"
        assert map_race_ethnicity("First Nation member") == "american_indian"
        assert map_race_ethnicity("American Indian") == "american_indian"

    def test_partial_matching_multi_racial(self):
        """Test partial matching for multi-racial."""
        assert map_race_ethnicity("Multi-cultural background") == "multi_racial"
        assert (
            map_race_ethnicity("Bi-racial") == "bi_racial"
        )  # Exact match from mapping
        assert (
            map_race_ethnicity("Two or more races") == "two_or_more"
        )  # Exact match from mapping
        # Partial match for "multi" pattern when no exact match
        assert map_race_ethnicity("Multiethnic") == "multi_racial"

    def test_prefer_not_to_say(self):
        """Test prefer not to say variations."""
        assert map_race_ethnicity("Prefer not to answer") == "prefer_not_to_say"
        assert map_race_ethnicity("Prefer not to say") == "prefer_not_to_say"
        assert map_race_ethnicity("I prefer not to disclose") == "prefer_not_to_say"

    def test_other_category(self):
        """Test other category matching."""
        assert map_race_ethnicity("Other") == "other"
        assert map_race_ethnicity("Other POC") == "other_poc"
        assert map_race_ethnicity("Something other than listed") == "other"

    def test_aggregate_result_handling(self):
        """Test that AggregateResult prefix is handled."""
        assert map_race_ethnicity("AggregateResult Hispanic") == "hispanic"
        assert map_race_ethnicity("AggregateResultBlack/African American") == "black"

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert map_race_ethnicity("  White  ") == "white"
        assert map_race_ethnicity("\tAsian\n") == "asian"

    def test_unknown_value_returns_default(self):
        """Unknown values should return the default."""
        assert map_race_ethnicity("XYZ Category") is None
        assert map_race_ethnicity("Unknown", "fallback") == "fallback"


# =============================================================================
# AGE GROUP MAPPING TESTS
# =============================================================================


class TestMapAgeGroup:
    """Tests for map_age_group function."""

    def test_null_value_returns_unknown(self):
        """Null/None values should return UNKNOWN enum."""
        from models.contact import AgeGroupEnum

        result = map_age_group(None)
        assert result == AgeGroupEnum.UNKNOWN

    def test_empty_value_returns_unknown(self):
        """Empty string should return UNKNOWN enum."""
        from models.contact import AgeGroupEnum

        result = map_age_group("")
        assert result == AgeGroupEnum.UNKNOWN

    def test_under_18(self):
        """Test Under 18 age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("Under 18") == AgeGroupEnum.UNDER_18

    def test_age_18_24(self):
        """Test 18-24 age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("18-24") == AgeGroupEnum.AGE_18_24

    def test_age_25_34(self):
        """Test 25-34 age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("25-34") == AgeGroupEnum.AGE_25_34

    def test_age_35_44(self):
        """Test 35-44 age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("35-44") == AgeGroupEnum.AGE_35_44

    def test_age_45_54(self):
        """Test 45-54 age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("45-54") == AgeGroupEnum.AGE_45_54

    def test_age_55_64(self):
        """Test 55-64 age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("55-64") == AgeGroupEnum.AGE_55_64

    def test_age_65_plus(self):
        """Test 65+ age group mapping."""
        from models.contact import AgeGroupEnum

        assert map_age_group("65+") == AgeGroupEnum.AGE_65_PLUS

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        from models.contact import AgeGroupEnum

        assert map_age_group("  18-24  ") == AgeGroupEnum.AGE_18_24

    def test_unknown_age_group(self):
        """Unknown age group should return UNKNOWN enum."""
        from models.contact import AgeGroupEnum

        assert map_age_group("100+") == AgeGroupEnum.UNKNOWN


# =============================================================================
# GRADE LEVEL MAPPING TESTS
# =============================================================================


class TestMapGradeLevel:
    """Tests for map_grade_level function."""

    def test_null_value_returns_default(self):
        """Null/None values should return default."""
        assert map_grade_level(None) == "UNKNOWN"
        assert map_grade_level("") == "UNKNOWN"
        assert map_grade_level(None, "OTHER") == "OTHER"

    def test_kindergarten(self):
        """Test kindergarten mapping."""
        assert map_grade_level("K") == "KINDERGARTEN"
        assert map_grade_level("Kindergarten") == "KINDERGARTEN"

    def test_numeric_grades(self):
        """Test numeric grade formats."""
        assert map_grade_level("1") == "FIRST"
        assert map_grade_level("2") == "SECOND"
        assert map_grade_level("3") == "THIRD"
        assert map_grade_level("4") == "FOURTH"
        assert map_grade_level("5") == "FIFTH"
        assert map_grade_level("6") == "SIXTH"
        assert map_grade_level("7") == "SEVENTH"
        assert map_grade_level("8") == "EIGHTH"
        assert map_grade_level("9") == "NINTH"
        assert map_grade_level("10") == "TENTH"
        assert map_grade_level("11") == "ELEVENTH"
        assert map_grade_level("12") == "TWELFTH"

    def test_ordinal_grades(self):
        """Test ordinal grade formats (1st, 2nd, etc.)."""
        assert map_grade_level("1st") == "FIRST"
        assert map_grade_level("2nd") == "SECOND"
        assert map_grade_level("3rd") == "THIRD"
        assert map_grade_level("4th") == "FOURTH"
        assert map_grade_level("5th") == "FIFTH"
        assert map_grade_level("6th") == "SIXTH"
        assert map_grade_level("7th") == "SEVENTH"
        assert map_grade_level("8th") == "EIGHTH"
        assert map_grade_level("9th") == "NINTH"
        assert map_grade_level("10th") == "TENTH"
        assert map_grade_level("11th") == "ELEVENTH"
        assert map_grade_level("12th") == "TWELFTH"

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert map_grade_level("  5th  ") == "FIFTH"
        assert map_grade_level("\t10\n") == "TENTH"

    def test_unknown_value_returns_default(self):
        """Unknown values should return the default."""
        assert map_grade_level("13") == "UNKNOWN"
        assert map_grade_level("College") == "UNKNOWN"
        assert map_grade_level("PreK", "PRE_K") == "PRE_K"


# =============================================================================
# PARTICIPATION STATUS MAPPING TESTS
# =============================================================================


class TestMapParticipationStatus:
    """Tests for map_participation_status function."""

    def test_null_value_returns_default(self):
        """Null/None values should return default."""
        assert map_participation_status(None) == "Unknown"
        assert map_participation_status("") == "Unknown"
        assert map_participation_status(None, "Scheduled") == "Scheduled"

    def test_attended_statuses(self):
        """Test various attended status mappings."""
        assert map_participation_status("Attended") == "Attended"
        assert map_participation_status("Completed") == "Attended"
        assert map_participation_status("Confirmed") == "Attended"
        assert map_participation_status("Present") == "Attended"
        assert map_participation_status("successfully completed") == "Attended"
        assert map_participation_status("simulcast") == "Attended"

    def test_no_show_statuses(self):
        """Test various no-show status mappings."""
        assert map_participation_status("No-Show") == "No-Show"
        assert map_participation_status("No Show") == "No-Show"
        assert map_participation_status("NoShow") == "No-Show"
        assert map_participation_status("Absent") == "No-Show"
        assert map_participation_status("Did Not Attend") == "No-Show"
        assert map_participation_status("DID NOT ATTEND") == "No-Show"
        assert map_participation_status("technical difficulties") == "No-Show"
        assert map_participation_status("local professional no-show") == "No-Show"
        assert map_participation_status("pathful professional no-show") == "No-Show"
        assert map_participation_status("teacher no-show") == "No-Show"

    def test_cancelled_statuses(self):
        """Test various cancelled status mappings."""
        assert map_participation_status("Cancelled") == "Cancelled"
        assert map_participation_status("Canceled") == "Cancelled"
        assert map_participation_status("cancelled") == "Cancelled"
        assert map_participation_status("canceled") == "Cancelled"
        assert map_participation_status("CANCELLED") == "Cancelled"
        assert map_participation_status("CANCELED") == "Cancelled"
        assert map_participation_status("Event Cancelled") == "Cancelled"
        assert map_participation_status("Event Canceled") == "Cancelled"
        assert map_participation_status("EVENT CANCELLED") == "Cancelled"
        assert map_participation_status("EVENT CANCELED") == "Cancelled"
        assert map_participation_status("teacher cancelation") == "Cancelled"
        assert map_participation_status("teacher cancellation") == "Cancelled"

    def test_scheduled_statuses(self):
        """Test scheduled status mappings."""
        assert map_participation_status("Scheduled") == "Scheduled"
        assert map_participation_status("scheduled") == "Scheduled"

    def test_case_sensitivity_fallback(self):
        """Test that lowercase lookup is used as fallback."""
        # These should work through lowercase matching
        assert map_participation_status("CANCELLED") == "Cancelled"
        assert (
            map_participation_status("completed") == "Unknown"
        )  # Not in lowercase map

    def test_unknown_value_returns_default(self):
        """Unknown values should return the default."""
        assert map_participation_status("Random Status") == "Unknown"
        assert map_participation_status("XYZ", "Scheduled") == "Scheduled"


# =============================================================================
# MAPPING DICTIONARY COMPLETENESS TESTS
# =============================================================================


class TestMappingDictionaries:
    """Tests to verify mapping dictionaries are complete and consistent."""

    def test_education_mapping_has_all_common_values(self):
        """Verify education mapping contains common education levels."""
        expected_results = [
            "BACHELORS_DEGREE",
            "MASTERS",
            "DOCTORATE",
            "HIGH_SCHOOL",
            "ASSOCIATES",
            "SOME_COLLEGE",
            "PROFESSIONAL",
        ]
        actual_results = set(EDUCATION_MAPPING.values())
        for expected in expected_results:
            assert (
                expected in actual_results
            ), f"Missing {expected} in EDUCATION_MAPPING"

    def test_age_group_mapping_covers_all_ranges(self):
        """Verify age group mapping covers all age ranges."""
        expected_values = [
            "UNDER_18",
            "AGE_18_24",
            "AGE_25_34",
            "AGE_35_44",
            "AGE_45_54",
            "AGE_55_64",
            "AGE_65_PLUS",
        ]
        actual_values = list(AGE_GROUP_MAPPING.values())
        for expected in expected_values:
            assert expected in actual_values, f"Missing {expected} in AGE_GROUP_MAPPING"

    def test_grade_level_mapping_covers_k_through_12(self):
        """Verify grade level mapping covers K-12."""
        expected_grades = [
            "KINDERGARTEN",
            "FIRST",
            "SECOND",
            "THIRD",
            "FOURTH",
            "FIFTH",
            "SIXTH",
            "SEVENTH",
            "EIGHTH",
            "NINTH",
            "TENTH",
            "ELEVENTH",
            "TWELFTH",
        ]
        actual_grades = set(GRADE_LEVEL_MAPPING.values())
        for expected in expected_grades:
            assert (
                expected in actual_grades
            ), f"Missing {expected} in GRADE_LEVEL_MAPPING"

    def test_participation_status_mapping_covers_main_statuses(self):
        """Verify participation status mapping covers main status types."""
        expected_statuses = ["Attended", "No-Show", "Cancelled", "Scheduled"]
        actual_statuses = set(PARTICIPATION_STATUS_MAPPING.values())
        for expected in expected_statuses:
            assert (
                expected in actual_statuses
            ), f"Missing {expected} in PARTICIPATION_STATUS_MAPPING"

    def test_race_ethnicity_mapping_covers_census_categories(self):
        """Verify race/ethnicity mapping covers main census categories."""
        expected_categories = [
            "hispanic",
            "black",
            "white",
            "asian",
            "native_hawaiian",
            "american_indian",
            "other",
        ]
        actual_categories = set(RACE_ETHNICITY_MAPPING.values())
        for expected in expected_categories:
            assert (
                expected in actual_categories
            ), f"Missing {expected} in RACE_ETHNICITY_MAPPING"

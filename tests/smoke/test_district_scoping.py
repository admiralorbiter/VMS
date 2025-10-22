"""Smoke tests for district scoping feature."""

import json

import pytest

from models.user import SecurityLevel, User


def test_can_view_district_method():
    """Test User.can_view_district() method."""
    # Test global user
    global_user = User(
        username="global_test", email="global@test.com", scope_type="global"
    )
    assert global_user.can_view_district("Any District") == True
    assert global_user.can_view_district("Another District") == True

    # Test district-scoped user
    district_user = User(
        username="district_test",
        email="district@test.com",
        scope_type="district",
        allowed_districts='["District A", "District B"]',
    )
    assert district_user.can_view_district("District A") == True
    assert district_user.can_view_district("District B") == True
    assert district_user.can_view_district("District C") == False

    # Test user with no districts assigned
    no_district_user = User(
        username="no_district_test",
        email="nodistrict@test.com",
        scope_type="district",
        allowed_districts=None,
    )
    assert no_district_user.can_view_district("Any District") == False


def test_is_district_scoped_property():
    """Test User.is_district_scoped property."""
    global_user = User(scope_type="global")
    district_user = User(scope_type="district")
    school_user = User(scope_type="school")

    assert global_user.is_district_scoped == False
    assert district_user.is_district_scoped == True
    assert school_user.is_district_scoped == False


def test_is_school_scoped_property():
    """Test User.is_school_scoped property."""
    global_user = User(scope_type="global")
    district_user = User(scope_type="district")
    school_user = User(scope_type="school")

    assert global_user.is_school_scoped == False
    assert district_user.is_school_scoped == False
    assert school_user.is_school_scoped == True


def test_district_scoped_kck_access():
    """Test district-scoped user with KCK access."""
    kck_user = User(
        username="kck_test",
        email="kck@test.com",
        security_level=0,  # USER level
        scope_type="district",
        allowed_districts='["Kansas City Kansas Public Schools"]',
    )
    assert kck_user.security_level == 0
    assert kck_user.is_district_scoped == True
    assert kck_user.can_view_district("Kansas City Kansas Public Schools") == True
    assert kck_user.can_view_district("Other District") == False


def test_json_parsing_edge_cases():
    """Test JSON parsing edge cases in can_view_district method."""
    # Test with malformed JSON
    malformed_user = User(
        username="malformed_test",
        email="malformed@test.com",
        scope_type="district",
        allowed_districts='["District A", "District B"',  # Missing closing bracket
    )
    assert malformed_user.can_view_district("District A") == False

    # Test with empty string
    empty_user = User(
        username="empty_test",
        email="empty@test.com",
        scope_type="district",
        allowed_districts="",
    )
    assert empty_user.can_view_district("Any District") == False

    # Test with already parsed list (shouldn't happen in practice but good to test)
    list_user = User(
        username="list_test",
        email="list@test.com",
        scope_type="district",
        allowed_districts=["District A", "District B"],  # Already a list
    )
    assert list_user.can_view_district("District A") == True
    assert list_user.can_view_district("District C") == False


if __name__ == "__main__":
    # Run tests if script is executed directly
    test_can_view_district_method()
    test_is_district_scoped_property()
    test_is_school_scoped_property()
    test_district_scoped_kck_access()
    test_json_parsing_edge_cases()
    print("All smoke tests passed!")

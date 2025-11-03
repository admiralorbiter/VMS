import warnings
from datetime import datetime, timezone

import pytest

from models import db
from models.organization import (
    Organization,
    OrganizationTypeEnum,
    VolunteerOrganization,
    VolunteerOrganizationStatusEnum,
)


def test_new_organization(app):
    """Test creating a new organization"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(
                name="Test Organization",
                salesforce_id="001TEST123456789AB",
                description="Test Description",
                billing_street="123 Test St",
                billing_city="Test City",
                billing_state="TS",
                billing_postal_code="12345",
                billing_country="Test Country",
            )

            db.session.add(org)
            db.session.flush()

            # Test basic fields
            assert org.id is not None
            assert org.name == "Test Organization"
            assert org.salesforce_id == "001TEST123456789AB"

            # Test address fields
            assert org.billing_street == "123 Test St"
            assert org.billing_city == "Test City"
            assert org.billing_state == "TS"
            assert org.billing_postal_code == "12345"
            assert org.billing_country == "Test Country"

            # Test timestamps
            assert isinstance(org.created_at, datetime)
            assert isinstance(org.updated_at, datetime)

            # Test Salesforce URL
            expected_url = "https://prep-kc.lightning.force.com/lightning/r/Account/001TEST123456789AB/view"
            assert org.salesforce_url == expected_url

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_relationship(app, test_volunteer):
    """Test relationship between Organization and Volunteer"""
    with app.app_context():
        db.session.begin()
        try:
            # Create organization
            org = Organization(name="Test Corp", type=OrganizationTypeEnum.BUSINESS)
            db.session.add(org)
            db.session.flush()

            # Create volunteer organization relationship
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                role="Software Engineer",
                is_primary=True,
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            db.session.add(vol_org)
            db.session.flush()

            # Test relationships using IDs instead of object comparison
            assert len(org.volunteer_organizations) == 1
            assert len(org.volunteers) == 1
            assert org.volunteers[0].id == test_volunteer.id
            assert org.volunteer_organizations[0].volunteer_id == test_volunteer.id

            # Test relationship attributes
            vol_org = org.volunteer_organizations[0]
            assert vol_org.role == "Software Engineer"
            assert vol_org.is_primary is True
            assert vol_org.status == VolunteerOrganizationStatusEnum.CURRENT
            assert isinstance(vol_org.created_at, datetime)
            assert isinstance(vol_org.updated_at, datetime)

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_organization_timestamps(app):
    """Test organization timestamp behavior"""
    with app.app_context():
        db.session.begin()
        try:
            # Create organization
            org = Organization(name="Timestamp Test Org")
            db.session.add(org)
            db.session.commit()

            # Store initial timestamps
            created_at = org.created_at
            updated_at = org.updated_at

            # Update organization
            org.name = "Updated Org Name"
            db.session.commit()

            # Verify timestamps
            assert org.created_at == created_at  # Should not change
            # Add a small delay to ensure timestamp difference
            import time

            time.sleep(0.001)
            assert org.updated_at >= updated_at  # Should be updated

        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_organization_salesforce_url(app):
    """Test organization Salesforce URL generation"""
    with app.app_context():
        db.session.begin()
        try:
            # Test with Salesforce ID
            org_with_sf = Organization(
                name="SF Test Org", salesforce_id="001TEST123456789AB"
            )
            assert (
                org_with_sf.salesforce_url
                == "https://prep-kc.lightning.force.com/lightning/r/Account/001TEST123456789AB/view"
            )

            # Test without Salesforce ID
            org_without_sf = Organization(name="Non-SF Test Org")
            assert org_without_sf.salesforce_url is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_cascade(app, test_volunteer):
    """Test cascade behavior when deleting organizations"""
    with app.app_context():
        db.session.begin()
        try:
            # Create organization
            org = Organization(name="Cascade Test Org")
            db.session.add(org)
            db.session.commit()  # Commit to ensure IDs are assigned

            # Create volunteer organization relationship
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id, organization_id=org.id, role="Tester"
            )
            db.session.add(vol_org)
            db.session.commit()  # Commit to ensure relationship is saved

            # Store IDs for later verification
            org_id = org.id

            # Delete organization
            db.session.delete(org)
            db.session.commit()  # Commit the deletion

            # Verify cascade delete
            assert db.session.get(Organization, org_id) is None
            vol_org_exists = (
                db.session.query(VolunteerOrganization)
                .filter_by(volunteer_id=test_volunteer.id, organization_id=org_id)
                .first()
            )
            assert vol_org_exists is None

        except:
            db.session.rollback()
            raise


def test_organization_unique_salesforce_id(app):
    """Test that organizations cannot have duplicate Salesforce IDs"""
    with app.app_context():
        db.session.begin()
        try:
            # Create first organization
            org1 = Organization(name="First Org", salesforce_id="001TEST123456789AB")
            db.session.add(org1)
            db.session.flush()

            # Attempt to create second organization with same Salesforce ID
            org2 = Organization(name="Second Org", salesforce_id="001TEST123456789AB")
            db.session.add(org2)

            # Should raise IntegrityError due to unique constraint
            with pytest.raises(Exception):  # Replace with specific exception if known
                db.session.flush()

        finally:
            db.session.rollback()


def test_volunteer_organization_multiple_relationships(app, test_volunteer):
    """Test volunteer can have multiple organization relationships"""
    with app.app_context():
        db.session.begin()
        try:
            # Refresh test_volunteer in current session
            test_volunteer = db.session.merge(test_volunteer)

            # Create two organizations
            org1 = Organization(name="Primary Org")
            org2 = Organization(name="Secondary Org")
            db.session.add_all([org1, org2])
            db.session.flush()

            # Create relationships using IDs instead of objects
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org1.id,
                role="Manager",
                is_primary=True,
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            vol_org2 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org2.id,
                role="Contributor",
                is_primary=False,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            db.session.add_all([vol_org1, vol_org2])
            db.session.flush()

            # Refresh the test_volunteer to ensure relationships are loaded
            db.session.refresh(test_volunteer)

            # Verify relationships
            assert len(test_volunteer.organizations) == 2
            assert len(test_volunteer.volunteer_organizations) == 2

            # Verify only one primary relationship
            primary_orgs = [
                vo for vo in test_volunteer.volunteer_organizations if vo.is_primary
            ]
            assert len(primary_orgs) == 1
            assert primary_orgs[0].organization_id == org1.id

            db.session.commit()
        except:
            db.session.rollback()
            raise


def test_volunteer_organization_date_validation(app, test_volunteer):
    """Test date validation in volunteer organization relationships"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Date Test Org")
            db.session.add(org)
            db.session.flush()

            # Test valid date range - validator converts naive to timezone-aware
            start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                start_date=start_date,
                end_date=end_date,
            )
            db.session.add(vol_org)
            db.session.flush()

            # Verify dates were saved correctly (timezone-aware)
            assert vol_org.start_date == start_date
            assert vol_org.end_date == end_date
            assert vol_org.start_date.tzinfo == timezone.utc
            assert vol_org.end_date.tzinfo == timezone.utc

            db.session.commit()
        except:
            db.session.rollback()
            raise


def test_organization_address_fields(app):
    """Test organization address field validations"""
    with app.app_context():
        db.session.begin()
        try:
            # Test with minimal address info
            org1 = Organization(
                name="Minimal Address Org", billing_city="Test City", billing_state="TS"
            )
            db.session.add(org1)
            db.session.flush()

            # Test with full address info
            org2 = Organization(
                name="Full Address Org",
                billing_street="123 Test St\nSuite 100",  # Test multi-line street
                billing_city="Test City",
                billing_state="TS",
                billing_postal_code="12345-6789",  # Test extended ZIP
                billing_country="Test Country",
            )
            db.session.add(org2)
            db.session.flush()

            assert org1.id is not None
            assert org2.id is not None

            db.session.commit()
        except:
            db.session.rollback()
            raise


# ============================================================================
# Validation Tests
# ============================================================================


def test_name_validation_valid(app):
    """Test name validation with valid names"""
    with app.app_context():
        db.session.begin()
        try:
            # Test valid name
            org1 = Organization(name="Valid Org Name")
            db.session.add(org1)
            db.session.flush()
            assert org1.name == "Valid Org Name"

            # Test name with whitespace (should be stripped)
            org2 = Organization(name="  Whitespace Org  ")
            db.session.add(org2)
            db.session.flush()
            assert org2.name == "Whitespace Org"  # Should be stripped

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_name_validation_invalid(app):
    """Test name validation raises ValueError for invalid names"""
    with app.app_context():
        db.session.begin()
        try:
            # Test empty string raises ValueError
            with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
                org1 = Organization(name="")
                db.session.add(org1)
                db.session.flush()

            # Test whitespace-only raises ValueError
            with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
                org2 = Organization(name="   ")
                db.session.add(org2)
                db.session.flush()

            # Test None raises ValueError
            with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
                org3 = Organization(name=None)
                db.session.add(org3)
                db.session.flush()

        finally:
            db.session.rollback()
            db.session.close()


def test_type_validation_valid(app):
    """Test type validation with valid types"""
    with app.app_context():
        db.session.begin()
        try:
            # Test enum instance
            org1 = Organization(name="Test Org", type=OrganizationTypeEnum.BUSINESS)
            db.session.add(org1)
            db.session.flush()
            assert org1.type == OrganizationTypeEnum.BUSINESS

            # Test string value matching enum
            org2 = Organization(name="Test Org 2", type="Business")
            db.session.add(org2)
            db.session.flush()
            assert org2.type == OrganizationTypeEnum.BUSINESS

            # Test None (should be allowed)
            org3 = Organization(name="Test Org 3", type=None)
            db.session.add(org3)
            db.session.flush()
            assert org3.type is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_type_validation_salesforce_mappings(app):
    """Test type validation maps Salesforce type variations correctly"""
    with app.app_context():
        db.session.begin()
        try:
            # Test Corporate -> Business mapping
            org1 = Organization(name="Corp Org", type="Corporate")
            db.session.add(org1)
            db.session.flush()
            assert org1.type == OrganizationTypeEnum.BUSINESS

            # Test Post-Secondary -> School mapping
            org2 = Organization(name="School Org", type="Post-Secondary")
            db.session.add(org2)
            db.session.flush()
            assert org2.type == OrganizationTypeEnum.SCHOOL

            # Test nonprofit variations -> Non-profit
            org3 = Organization(name="Nonprofit Org", type="nonprofit")
            db.session.add(org3)
            db.session.flush()
            assert org3.type == OrganizationTypeEnum.NON_PROFIT

            org4 = Organization(name="Non-Profit Org", type="Non-Profit")
            db.session.add(org4)
            db.session.flush()
            assert org4.type == OrganizationTypeEnum.NON_PROFIT

            org5 = Organization(name="Non Profit Org", type="non profit")
            db.session.add(org5)
            db.session.flush()
            assert org5.type == OrganizationTypeEnum.NON_PROFIT

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_type_validation_invalid(app):
    """Test type validation raises ValueError for invalid types"""
    with app.app_context():
        db.session.begin()
        try:
            # Test invalid type string
            with pytest.raises(ValueError, match="Invalid organization type"):
                org = Organization(name="Test Org", type="InvalidType")
                db.session.add(org)
                db.session.flush()

        finally:
            db.session.rollback()
            db.session.close()


def test_last_activity_date_validation_timezone(app):
    """Test last_activity_date validation handles timezones correctly"""
    import warnings

    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Timezone Test Org")
            db.session.add(org)
            db.session.flush()

            # Test timezone-naive datetime adds UTC timezone with warning
            naive_dt = datetime(2024, 1, 15, 10, 0, 0)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                org.last_activity_date = naive_dt
                assert org.last_activity_date.tzinfo is not None
                assert org.last_activity_date.tzinfo == timezone.utc
                assert len(w) > 0
                assert any("Timezone-naive" in str(warning.message) for warning in w)

            # Test timezone-aware datetime returns as-is
            aware_dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            org.last_activity_date = aware_dt
            assert org.last_activity_date == aware_dt
            assert org.last_activity_date.tzinfo == timezone.utc

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_last_activity_date_validation_string_parsing(app):
    """Test last_activity_date validation parses string formats"""
    import warnings

    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Date Parse Test Org")
            db.session.add(org)
            db.session.flush()

            # Test ISO format date string
            org.last_activity_date = "2024-01-15 10:00:00"
            assert org.last_activity_date is not None
            assert org.last_activity_date.year == 2024
            assert org.last_activity_date.month == 1
            assert org.last_activity_date.day == 15
            assert org.last_activity_date.tzinfo == timezone.utc

            # Test date-only string
            org.last_activity_date = "2024-01-15"
            assert org.last_activity_date is not None
            assert org.last_activity_date.year == 2024
            assert org.last_activity_date.month == 1
            assert org.last_activity_date.day == 15

            # Test invalid date string returns None with warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                org.last_activity_date = "invalid date"
                assert org.last_activity_date is None
                assert len(w) > 0
                assert any(
                    "Invalid date format" in str(warning.message) for warning in w
                )

            # Test None returns None
            org.last_activity_date = None
            assert org.last_activity_date is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_address_fields_validation_warnings(app):
    """Test address field validation issues warnings for incomplete addresses"""
    import warnings

    with app.app_context():
        db.session.begin()
        try:
            # Test city without state issues warning
            org1 = Organization(name="City Only Org")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                org1.billing_city = "Kansas City"
                db.session.add(org1)
                db.session.flush()
                assert len(w) > 0
                assert any(
                    "City provided without state" in str(warning.message)
                    for warning in w
                )

            # Test state without postal code issues warning
            org2 = Organization(name="State Only Org")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                org2.billing_state = "MO"
                db.session.add(org2)
                db.session.flush()
                assert len(w) > 0
                assert any(
                    "State provided without postal code" in str(warning.message)
                    for warning in w
                )

            # Test street without city/state issues warning
            org3 = Organization(name="Street Only Org")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                org3.billing_street = "123 Main St"
                db.session.add(org3)
                db.session.flush()
                assert len(w) > 0
                assert any(
                    "Street address provided without city" in str(warning.message)
                    for warning in w
                )

            # Test postal code without state issues warning
            org4 = Organization(name="Postal Only Org")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                org4.billing_postal_code = "64111"
                db.session.add(org4)
                db.session.flush()
                assert len(w) > 0
                assert any(
                    "Postal code provided without state" in str(warning.message)
                    for warning in w
                )

            # Test whitespace stripping
            org5 = Organization(name="Whitespace Address Org")
            org5.billing_city = "  Kansas City  "
            org5.billing_state = "  MO  "
            db.session.add(org5)
            db.session.flush()
            assert org5.billing_city == "Kansas City"
            assert org5.billing_state == "MO"

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_status_validation(app, test_volunteer):
    """Test VolunteerOrganization status validation"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Status Test Org")
            db.session.add(org)
            db.session.flush()

            # Create additional volunteers to avoid unique constraint violations
            from models.volunteer import Volunteer

            vol2 = Volunteer(first_name="Status", last_name="Test2", middle_name="")
            vol3 = Volunteer(first_name="Status", last_name="Test3", middle_name="")
            vol4 = Volunteer(first_name="Status", last_name="Test4", middle_name="")
            db.session.add_all([vol2, vol3, vol4])
            db.session.flush()

            # Test string status value
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id, organization_id=org.id, status="Current"
            )
            db.session.add(vol_org1)
            db.session.flush()
            assert vol_org1.status == VolunteerOrganizationStatusEnum.CURRENT

            # Test enum instance (use different volunteer to avoid unique constraint)
            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            db.session.add(vol_org2)
            db.session.flush()
            assert vol_org2.status == VolunteerOrganizationStatusEnum.PAST

            # Test None defaults to CURRENT (use different volunteer)
            vol_org3 = VolunteerOrganization(
                volunteer_id=vol3.id, organization_id=org.id, status=None
            )
            db.session.add(vol_org3)
            db.session.flush()
            assert vol_org3.status == VolunteerOrganizationStatusEnum.CURRENT

            # Test case-insensitive matching (use different volunteer)
            vol_org4 = VolunteerOrganization(
                volunteer_id=vol4.id,
                organization_id=org.id,
                status="current",  # lowercase
            )
            db.session.add(vol_org4)
            db.session.flush()
            assert vol_org4.status == VolunteerOrganizationStatusEnum.CURRENT

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_status_validation_invalid(app, test_volunteer):
    """Test VolunteerOrganization status validation raises ValueError for invalid status"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Invalid Status Test Org")
            db.session.add(org)
            db.session.flush()

            with pytest.raises(ValueError, match="Invalid status"):
                vol_org = VolunteerOrganization(
                    volunteer_id=test_volunteer.id,
                    organization_id=org.id,
                    status="InvalidStatus",
                )
                db.session.add(vol_org)
                db.session.flush()

        finally:
            db.session.rollback()
            db.session.close()


def test_volunteer_organization_date_range_validation(app, test_volunteer):
    """Test VolunteerOrganization date range validation"""
    import warnings

    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Date Range Test Org")
            db.session.add(org)
            db.session.flush()

            # Create additional volunteers to avoid unique constraint violations
            from models.volunteer import Volunteer

            vol2 = Volunteer(first_name="DateRange", last_name="Test2", middle_name="")
            vol3 = Volunteer(first_name="DateRange", last_name="Test3", middle_name="")
            vol4 = Volunteer(first_name="DateRange", last_name="Test4", middle_name="")
            db.session.add_all([vol2, vol3, vol4])
            db.session.flush()

            # Test valid date range (end_date >= start_date) doesn't warn
            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                start_date=start_date,
                end_date=end_date,
            )
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                db.session.add(vol_org1)
                db.session.flush()
                # Should not warn for valid date range
                assert (
                    len(
                        [warn for warn in w if "before start date" in str(warn.message)]
                    )
                    == 0
                )

            # Test end_date < start_date issues warning (use different volunteer)
            # Warning is issued during assignment, not during flush
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                vol_org2 = VolunteerOrganization(
                    volunteer_id=vol2.id,
                    organization_id=org.id,
                    start_date=end_date,  # Later date
                    end_date=start_date,  # Earlier date
                )
                db.session.add(vol_org2)
                db.session.flush()
                assert len(w) > 0
                assert any("before start date" in str(warning.message) for warning in w)

            # Test timezone-naive dates converted with warning (use different volunteer)
            # Warning is issued during assignment, not during flush
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                vol_org3 = VolunteerOrganization(
                    volunteer_id=vol3.id,
                    organization_id=org.id,
                    start_date=datetime(2024, 1, 1),  # Naive datetime
                )
                db.session.add(vol_org3)
                db.session.flush()
                assert vol_org3.start_date.tzinfo == timezone.utc
                assert len(w) > 0
                assert any("Timezone-naive" in str(warning.message) for warning in w)

            # Test string date formats parsed (use different volunteer)
            vol_org4 = VolunteerOrganization(
                volunteer_id=vol4.id,
                organization_id=org.id,
                start_date="2024-01-15 10:00:00",
            )
            db.session.add(vol_org4)
            db.session.flush()
            assert vol_org4.start_date is not None
            assert vol_org4.start_date.year == 2024
            assert vol_org4.start_date.tzinfo == timezone.utc

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_date_range_invalid_format(app, test_volunteer):
    """Test VolunteerOrganization date range validation with invalid formats"""
    import warnings

    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Invalid Date Format Org")
            db.session.add(org)
            db.session.flush()

            # Test invalid date format returns None with warning
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id, organization_id=org.id
            )
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                vol_org.start_date = "invalid date format"
                assert vol_org.start_date is None
                assert len(w) > 0
                assert any(
                    "Invalid date format" in str(warning.message) for warning in w
                )

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_salesforce_id_validation(app):
    """Test Salesforce ID validation"""
    with app.app_context():
        db.session.begin()
        try:
            # Test valid 18-char ID (fixed: was 17 chars, now 18)
            org1 = Organization(name="Valid SF Org", salesforce_id="0011234567890ABCDE")
            db.session.add(org1)
            db.session.flush()
            assert org1.salesforce_id == "0011234567890ABCDE"

            # Test None returns None
            org2 = Organization(name="No SF Org", salesforce_id=None)
            db.session.add(org2)
            db.session.flush()
            assert org2.salesforce_id is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_salesforce_id_validation_invalid(app):
    """Test Salesforce ID validation raises ValueError for invalid formats"""
    with app.app_context():
        db.session.begin()
        try:
            # Test invalid format (too short)
            with pytest.raises(ValueError, match="Salesforce ID"):
                org = Organization(
                    name="Invalid SF Org", salesforce_id="001123"  # Too short
                )
                db.session.add(org)
                db.session.flush()

        finally:
            db.session.rollback()
            db.session.close()


# ============================================================================
# Property Tests
# ============================================================================


def test_volunteer_count(app, test_volunteer):
    """Test volunteer_count property"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Volunteer Count Test Org")
            db.session.add(org)
            db.session.flush()

            # Test with no volunteers
            assert org.volunteer_count == 0

            # Add volunteers with different statuses
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            db.session.add(vol_org1)
            db.session.flush()
            assert org.volunteer_count == 1

            # Add another volunteer (different status)
            from models.volunteer import Volunteer

            vol2 = Volunteer(first_name="Test2", last_name="Volunteer2", middle_name="")
            db.session.add(vol2)
            db.session.flush()

            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            db.session.add(vol_org2)
            db.session.flush()
            assert org.volunteer_count == 2  # Total count includes all statuses

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_count_with_statuses(app, test_volunteer):
    """Test volunteer_count includes all relationship statuses"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Status Count Test Org")
            db.session.add(org)
            db.session.flush()

            # Create volunteers with different statuses
            from models.volunteer import Volunteer

            volunteers = []
            for i in range(3):
                vol = Volunteer(
                    first_name=f"Test{i}", last_name=f"Volunteer{i}", middle_name=""
                )
                db.session.add(vol)
                volunteers.append(vol)
            db.session.flush()

            # Add relationships with different statuses
            statuses = [
                VolunteerOrganizationStatusEnum.CURRENT,
                VolunteerOrganizationStatusEnum.PAST,
                VolunteerOrganizationStatusEnum.PENDING,
            ]
            for vol, status in zip(volunteers, statuses):
                vol_org = VolunteerOrganization(
                    volunteer_id=vol.id, organization_id=org.id, status=status
                )
                db.session.add(vol_org)
            db.session.flush()

            # Total count should include all statuses
            assert org.volunteer_count == 3

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_active_volunteer_count(app, test_volunteer):
    """Test active_volunteer_count property counts only CURRENT status"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Active Count Test Org")
            db.session.add(org)
            db.session.flush()

            # Test with no volunteers
            assert org.active_volunteer_count == 0

            # Add volunteers with different statuses
            from models.volunteer import Volunteer

            vol1 = Volunteer(first_name="Current", last_name="Vol", middle_name="")
            vol2 = Volunteer(first_name="Past", last_name="Vol", middle_name="")
            vol3 = Volunteer(first_name="Pending", last_name="Vol", middle_name="")
            db.session.add_all([vol1, vol2, vol3])
            db.session.flush()

            # Add relationships with different statuses
            vol_org1 = VolunteerOrganization(
                volunteer_id=vol1.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            vol_org3 = VolunteerOrganization(
                volunteer_id=vol3.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PENDING,
            )
            db.session.add_all([vol_org1, vol_org2, vol_org3])
            db.session.flush()

            # Active count should only include CURRENT
            assert org.active_volunteer_count == 1
            assert org.volunteer_count == 3  # Total includes all

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_current_volunteers(app, test_volunteer):
    """Test current_volunteers property filters by CURRENT status"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Current Volunteers Test Org")
            db.session.add(org)
            db.session.flush()

            # Test with no volunteers
            assert len(org.current_volunteers) == 0

            # Add volunteers with different statuses
            from models.volunteer import Volunteer

            vol1 = Volunteer(first_name="Current", last_name="Vol", middle_name="")
            vol2 = Volunteer(first_name="Past", last_name="Vol", middle_name="")
            db.session.add_all([vol1, vol2])
            db.session.flush()

            vol_org1 = VolunteerOrganization(
                volunteer_id=vol1.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            db.session.add_all([vol_org1, vol_org2])
            db.session.flush()

            # Refresh to ensure relationships are loaded
            db.session.refresh(org)

            # current_volunteers should only include CURRENT status
            current = org.current_volunteers
            assert len(current) == 1
            assert current[0].id == vol1.id

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_primary_volunteers(app, test_volunteer):
    """Test primary_volunteers property"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Primary Volunteers Test Org")
            db.session.add(org)
            db.session.flush()

            # Test with no volunteers
            assert len(org.primary_volunteers) == 0

            # Add volunteers - one primary, one not
            from models.volunteer import Volunteer

            vol1 = Volunteer(first_name="Primary", last_name="Vol", middle_name="")
            vol2 = Volunteer(first_name="Secondary", last_name="Vol", middle_name="")
            db.session.add_all([vol1, vol2])
            db.session.flush()

            vol_org1 = VolunteerOrganization(
                volunteer_id=vol1.id, organization_id=org.id, is_primary=True
            )
            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id, organization_id=org.id, is_primary=False
            )
            db.session.add_all([vol_org1, vol_org2])
            db.session.flush()

            # Refresh to ensure relationships are loaded
            db.session.refresh(org)

            # primary_volunteers should only include is_primary=True
            primary = org.primary_volunteers
            assert len(primary) == 1
            assert primary[0].id == vol1.id

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_formatted_billing_address(app):
    """Test formatted_billing_address property"""
    with app.app_context():
        db.session.begin()
        try:
            # Test with full address
            org1 = Organization(
                name="Full Address Org",
                billing_street="123 Main St",
                billing_city="Kansas City",
                billing_state="MO",
                billing_postal_code="64111",
                billing_country="USA",
            )
            db.session.add(org1)
            db.session.flush()
            formatted = org1.formatted_billing_address
            assert formatted is not None
            assert "123 Main St" in formatted
            assert "Kansas City, MO 64111" in formatted
            assert "USA" not in formatted  # USA is excluded

            # Test with non-USA country
            org2 = Organization(
                name="International Org",
                billing_street="456 Oak Ave",
                billing_city="Toronto",
                billing_state="ON",
                billing_postal_code="M5H 2N2",
                billing_country="Canada",
            )
            db.session.add(org2)
            db.session.flush()
            formatted2 = org2.formatted_billing_address
            assert "Canada" in formatted2

            # Test with no address
            org3 = Organization(name="No Address Org")
            db.session.add(org3)
            db.session.flush()
            assert org3.formatted_billing_address is None

            # Test with partial address
            org4 = Organization(
                name="Partial Address Org",
                billing_city="Kansas City",
                billing_state="MO",
            )
            db.session.add(org4)
            db.session.flush()
            formatted4 = org4.formatted_billing_address
            assert formatted4 is not None
            assert "Kansas City, MO" in formatted4

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_has_address_info(app):
    """Test has_address_info property"""
    with app.app_context():
        db.session.begin()
        try:
            # Test with no address
            org1 = Organization(name="No Address Org")
            db.session.add(org1)
            db.session.flush()
            assert org1.has_address_info is False

            # Test with partial address
            org2 = Organization(name="Partial Address Org", billing_city="Kansas City")
            db.session.add(org2)
            db.session.flush()
            assert org2.has_address_info is True

            # Test with full address
            org3 = Organization(
                name="Full Address Org",
                billing_street="123 Main St",
                billing_city="Kansas City",
                billing_state="MO",
                billing_postal_code="64111",
                billing_country="USA",
            )
            db.session.add(org3)
            db.session.flush()
            assert org3.has_address_info is True

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_is_active(app, test_volunteer):
    """Test VolunteerOrganization is_active property"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Is Active Test Org")
            db.session.add(org)
            db.session.flush()

            # Test CURRENT status is active
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            db.session.add(vol_org1)
            db.session.flush()
            assert vol_org1.is_active is True

            # Test PAST status is not active
            from models.volunteer import Volunteer

            vol2 = Volunteer(first_name="Past", last_name="Vol", middle_name="")
            db.session.add(vol2)
            db.session.flush()

            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            db.session.add(vol_org2)
            db.session.flush()
            assert vol_org2.is_active is False

            # Test PENDING status is not active
            vol3 = Volunteer(first_name="Pending", last_name="Vol", middle_name="")
            db.session.add(vol3)
            db.session.flush()

            vol_org3 = VolunteerOrganization(
                volunteer_id=vol3.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PENDING,
            )
            db.session.add(vol_org3)
            db.session.flush()
            assert vol_org3.is_active is False

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_formatted_date_range(app, test_volunteer):
    """Test VolunteerOrganization formatted_date_range property"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Date Range Format Test Org")
            db.session.add(org)
            db.session.flush()

            # Create additional volunteers to avoid unique constraint violations
            from models.volunteer import Volunteer

            vol2 = Volunteer(first_name="DateFormat", last_name="Test2", middle_name="")
            vol3 = Volunteer(first_name="DateFormat", last_name="Test3", middle_name="")
            db.session.add_all([vol2, vol3])
            db.session.flush()

            # Test with start_date only (ongoing)
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                start_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                end_date=None,
            )
            db.session.add(vol_org1)
            db.session.flush()
            formatted1 = vol_org1.formatted_date_range
            assert formatted1 is not None
            assert "Started: January 15, 2024 (ongoing)" in formatted1

            # Test with both dates (range) - use different volunteer
            vol_org2 = VolunteerOrganization(
                volunteer_id=vol2.id,
                organization_id=org.id,
                start_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                end_date=datetime(2024, 3, 20, tzinfo=timezone.utc),
            )
            db.session.add(vol_org2)
            db.session.flush()
            formatted2 = vol_org2.formatted_date_range
            assert formatted2 is not None
            assert "January 15, 2024 - March 20, 2024" in formatted2

            # Test with no dates - use different volunteer
            vol_org3 = VolunteerOrganization(
                volunteer_id=vol3.id,
                organization_id=org.id,
                start_date=None,
                end_date=None,
            )
            db.session.add(vol_org3)
            db.session.flush()
            assert vol_org3.formatted_date_range is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


# ============================================================================
# Class Method Tests
# ============================================================================


def test_from_salesforce(app):
    """Test from_salesforce class method"""
    with app.app_context():
        db.session.begin()
        try:
            # Test empty strings converted to None
            sf_data = {
                "name": "SF Org",
                "type": "",
                "description": "",
                "billing_city": "Kansas City",
            }
            org = Organization.from_salesforce(sf_data)
            assert org.name == "SF Org"
            assert org.type is None
            assert org.description is None
            assert org.billing_city == "Kansas City"

            # Test type mapping
            sf_data2 = {"name": "Corporate Org", "type": "Corporate"}
            org2 = Organization.from_salesforce(sf_data2)
            assert org2.type == OrganizationTypeEnum.BUSINESS

            # Test Post-Secondary mapping
            sf_data3 = {"name": "School Org", "type": "Post-Secondary"}
            org3 = Organization.from_salesforce(sf_data3)
            assert org3.type == OrganizationTypeEnum.SCHOOL

            # Test nonprofit variation
            sf_data4 = {"name": "Nonprofit Org", "type": "nonprofit"}
            org4 = Organization.from_salesforce(sf_data4)
            assert org4.type == OrganizationTypeEnum.NON_PROFIT

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


# ============================================================================
# String Representation Tests
# ============================================================================


def test_organization_string_representations(app):
    """Test Organization __str__ and __repr__ methods"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="String Test Org")
            db.session.add(org)
            db.session.flush()

            # Test __str__
            assert str(org) == "String Test Org"

            # Test __repr__
            repr_str = repr(org)
            assert "Organization" in repr_str
            assert str(org.id) in repr_str
            assert "String Test Org" in repr_str

            # Test that setting name to None raises ValueError (validation prevents it)
            org2 = Organization(name="Test")
            db.session.add(org2)
            db.session.flush()
            with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
                org2.name = None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_string_representations(app, test_volunteer):
    """Test VolunteerOrganization __str__ and __repr__ methods"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="String Test Org")
            db.session.add(org)
            db.session.flush()

            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                role="Software Engineer",
                status=VolunteerOrganizationStatusEnum.CURRENT,
            )
            db.session.add(vol_org)
            db.session.flush()

            # Test __str__
            str_repr = str(vol_org)
            assert "Volunteer" in str_repr
            assert str(test_volunteer.id) in str_repr
            assert "String Test Org" in str_repr
            assert "Software Engineer" in str_repr
            assert "Current" in str_repr

            # Test __repr__ (uses enum.value which is "Current", not "CURRENT")
            repr_str = repr(vol_org)
            assert "VolunteerOrganization" in repr_str
            assert str(test_volunteer.id) in repr_str
            assert str(org.id) in repr_str
            assert "status=Current" in repr_str

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_organization_no_volunteers(app):
    """Test organization with no volunteers"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="No Volunteers Org")
            db.session.add(org)
            db.session.flush()

            assert org.volunteer_count == 0
            assert org.active_volunteer_count == 0
            assert len(org.current_volunteers) == 0
            assert len(org.primary_volunteers) == 0
            assert len(org.volunteers) == 0
            assert len(org.volunteer_organizations) == 0

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_organization_only_past_relationships(app, test_volunteer):
    """Test organization with only PAST relationships"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="Past Only Org")
            db.session.add(org)
            db.session.flush()

            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                status=VolunteerOrganizationStatusEnum.PAST,
            )
            db.session.add(vol_org)
            db.session.flush()

            assert org.volunteer_count == 1
            assert org.active_volunteer_count == 0  # No CURRENT
            assert len(org.current_volunteers) == 0

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_volunteer_organization_none_dates(app, test_volunteer):
    """Test VolunteerOrganization with None dates"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name="None Dates Org")
            db.session.add(org)
            db.session.flush()

            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                start_date=None,
                end_date=None,
            )
            db.session.add(vol_org)
            db.session.flush()

            assert vol_org.start_date is None
            assert vol_org.end_date is None
            assert vol_org.formatted_date_range is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

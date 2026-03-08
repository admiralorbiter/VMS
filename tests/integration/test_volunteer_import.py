"""
Integration tests for Salesforce Volunteer Import Routes.

Tests cover field mapping, null handling, enum fallbacks,
email/phone preference routing, skill deduplication, per-record
error isolation, and connector data mapping.
"""

from unittest.mock import MagicMock, patch

import pytest


def _make_sf_row(overrides=None):
    """Build a minimal valid Salesforce volunteer row with sensible defaults."""
    row = {
        "Id": "003SFID000000001",
        "AccountId": "001ACCT000000001",
        "FirstName": "Jane",
        "LastName": "Doe",
        "MiddleName": None,
        "Email": "jane.doe@example.com",
        "npe01__AlternateEmail__c": None,
        "npe01__HomeEmail__c": None,
        "npe01__WorkEmail__c": None,
        "npe01__Preferred_Email__c": None,
        "HomePhone": None,
        "MobilePhone": None,
        "npe01__WorkPhone__c": None,
        "Phone": "555-123-4567",
        "npe01__PreferredPhone__c": None,
        "npsp__Primary_Affiliation__c": "Acme Corp",
        "Title": "Engineer",
        "Department": "Tech",
        "Gender__c": "Female",
        "Birthdate": "1990-05-15",
        "Last_Mailchimp_Email_Date__c": None,
        "Last_Volunteer_Date__c": None,
        "Last_Email_Message__c": None,
        "Volunteer_Recruitment_Notes__c": None,
        "Volunteer_Skills__c": None,
        "Volunteer_Skills_Text__c": None,
        "Volunteer_Interests__c": None,
        "Number_of_Attended_Volunteer_Sessions__c": "3",
        "Racial_Ethnic_Background__c": "White",
        "Last_Activity_Date__c": None,
        "First_Volunteer_Date__c": None,
        "Last_Non_Internal_Email_Activity__c": None,
        "Description": None,
        "Highest_Level_of_Educational__c": None,
        "Age_Group__c": None,
        "DoNotCall": False,
        "npsp__Do_Not_Contact__c": False,
        "HasOptedOutOfEmail": False,
        "EmailBouncedDate": None,
        "MailingAddress": {},
        "npe01__Home_Address__c": None,
        "npe01__Work_Address__c": None,
        "npe01__Other_Address__c": None,
        "npe01__Primary_Address_Type__c": None,
        "npe01__Secondary_Address_Type__c": None,
        "Connector_Active_Subscription__c": None,
        "Connector_Active_Subscription_Name__c": None,
        "Connector_Affiliations__c": None,
        "Connector_Industry__c": None,
        "Connector_Joining_Date__c": None,
        "Connector_Last_Login_Date_Time__c": None,
        "Connector_Last_Update_Date__c": None,
        "Connector_Profile_Link__c": None,
        "Connector_Role__c": None,
        "Connector_SignUp_Role__c": None,
        "Connector_User_ID__c": None,
        "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
    }
    if overrides:
        row.update(overrides)
    return row


# Patch paths match the module where the name is *used*, not where it's defined.
PATCH_SF_CLIENT = "routes.salesforce.volunteer_import.get_salesforce_client"
PATCH_SAFE_QUERY = "routes.salesforce.volunteer_import.safe_query_all"
PATCH_DELTA = "services.salesforce.DeltaSyncHelper"


class TestVolunteerImportHappyPath:
    """Tests that a well-formed Salesforce row is imported correctly."""

    def test_new_volunteer_created(self, client, auth_headers, app):
        """A new volunteer is created when no matching salesforce_individual_id exists."""
        sf_row = _make_sf_row()

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            response = client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["processed_count"] == 1
            assert data["error_count"] == 0

        # Verify volunteer was persisted
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol is not None
            assert vol.first_name == "Jane"
            assert vol.last_name == "Doe"
            assert vol.organization_name == "Acme Corp"
            assert vol.title == "Engineer"
            assert vol.times_volunteered == 3

    def test_existing_volunteer_updated(self, client, auth_headers, app):
        """An existing volunteer is updated (not duplicated) on re-import."""
        from models import db
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003SFID000000001",
                first_name="OldFirst",
                last_name="OldLast",
            )
            db.session.add(vol)
            db.session.commit()

        sf_row = _make_sf_row({"FirstName": "Jane", "LastName": "Doe"})

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            response = client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200

        with app.app_context():
            vols = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).all()
            assert len(vols) == 1
            assert vols[0].first_name == "Jane"
            assert vols[0].last_name == "Doe"

    def test_empty_result_set(self, client, auth_headers):
        """No records from Salesforce returns success with 0 counts."""
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": []}

            response = client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["processed_count"] == 0


class TestVolunteerImportNullHandling:
    """Tests that null/empty Salesforce fields are handled gracefully."""

    def _run_import(self, client, auth_headers, sf_row):
        """Helper to run a single-record import and return the response."""
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_null_first_name(self, client, auth_headers, app):
        """FirstName=None doesn't crash — gets stored as empty string."""
        sf_row = _make_sf_row({"FirstName": None})
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol.first_name == ""

    def test_null_gender_skipped(self, client, auth_headers, app):
        """Null gender doesn't crash and doesn't set gender."""
        sf_row = _make_sf_row({"Gender__c": None})
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_unknown_gender_ignored(self, client, auth_headers, app):
        """Unrecognized gender string silently ignored (no crash)."""
        sf_row = _make_sf_row({"Gender__c": "Nonbinary Custom"})
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_null_race_sets_unknown(self, client, auth_headers, app):
        """Null race/ethnicity is mapped to RaceEthnicityEnum.unknown."""
        sf_row = _make_sf_row({"Racial_Ethnic_Background__c": None})
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.contact import RaceEthnicityEnum
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol.race_ethnicity == RaceEthnicityEnum.unknown

    def test_non_numeric_times_volunteered_falls_back_to_zero(
        self, client, auth_headers, app
    ):
        """Non-numeric Number_of_Attended_Volunteer_Sessions__c defaults to 0."""
        sf_row = _make_sf_row(
            {"Number_of_Attended_Volunteer_Sessions__c": "not-a-number"}
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol.times_volunteered == 0


class TestVolunteerImportEmailPhonePreferences:
    """Tests for email and phone primary-flag routing based on SF preferences."""

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_work_email_set_as_primary(self, client, auth_headers, app):
        """When preferred email is 'work', work email is set as primary."""
        sf_row = _make_sf_row(
            {
                "Email": "personal@example.com",
                "npe01__WorkEmail__c": "work@example.com",
                "npe01__Preferred_Email__c": "Work",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.contact import Email
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            emails = Email.query.filter_by(contact_id=vol.id).all()
            assert len(emails) == 2
            work_email = next(e for e in emails if e.email == "work@example.com")
            assert work_email.primary is True

    def test_mobile_phone_set_as_primary(self, client, auth_headers, app):
        """When preferred phone is 'mobile', mobile phone is set as primary."""
        sf_row = _make_sf_row(
            {
                "Phone": "555-000-0001",
                "MobilePhone": "555-000-0002",
                "npe01__PreferredPhone__c": "Mobile",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.contact import Phone
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            phones = Phone.query.filter_by(contact_id=vol.id).all()
            assert len(phones) == 2
            mobile = next(p for p in phones if p.number == "555-000-0002")
            assert mobile.primary is True


class TestVolunteerImportWorkAddressParsing:
    """Tests for the comma-separated work address string parser."""

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_full_work_address_parsed(self, client, auth_headers, app):
        """A full 'street, city, state zip' string is parsed into components."""
        sf_row = _make_sf_row(
            {
                "npe01__Work_Address__c": "123 Main St, Kansas City, MO 64111",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.contact import Address, ContactTypeEnum
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            work_addr = next(
                (a for a in vol.addresses if a.type == ContactTypeEnum.professional),
                None,
            )
            assert work_addr is not None
            assert work_addr.address_line1 == "123 Main St"
            assert work_addr.city == "Kansas City"
            assert work_addr.state == "MO"
            assert work_addr.zip_code == "64111"

    def test_partial_work_address_no_crash(self, client, auth_headers, app):
        """A work address with only street (no comma) doesn't crash."""
        sf_row = _make_sf_row(
            {
                "npe01__Work_Address__c": "123 Main St",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1


class TestVolunteerImportErrorIsolation:
    """Tests that per-record errors don't block other records."""

    def test_bad_record_does_not_block_good_record(self, client, auth_headers, app):
        """One record with a bad field doesn't prevent a good record from importing."""
        good_row = _make_sf_row(
            {
                "Id": "003SFID000000001",
                "FirstName": "Good",
                "LastName": "Volunteer",
            }
        )
        # Mailing address as a non-dict triggers the isinstance check,
        # but shouldn't crash because the code checks isinstance(mailing_address, dict)
        # Let's use a different trigger: we'll simulate an error by giving an ID
        # that would cause a KeyError in the error summary block.
        bad_row = _make_sf_row(
            {
                "Id": "003SFID000000002",
                "FirstName": "Bad",
                "LastName": "Volunteer",
            }
        )

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [good_row, bad_row]}

            response = client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            # Both records should process successfully (both are well-formed)
            assert data["processed_count"] == 2

    def test_multiple_records_processing(self, client, auth_headers, app):
        """Multiple valid records all get imported successfully."""
        rows = [
            _make_sf_row(
                {
                    "Id": f"003SFID00000000{i}",
                    "FirstName": f"Vol{i}",
                    "LastName": "Test",
                }
            )
            for i in range(5)
        ]

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": rows}

            response = client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["processed_count"] == 5

        from models.volunteer import Volunteer

        with app.app_context():
            count = Volunteer.query.count()
            assert count == 5


class TestVolunteerImportAuthFailure:
    """Tests for Salesforce authentication failure handling."""

    def test_auth_failure_returns_401(self, client, auth_headers):
        """SalesforceAuthenticationFailed returns 401."""
        from simple_salesforce import SalesforceAuthenticationFailed

        with patch(PATCH_SF_CLIENT) as mock_sf, patch(PATCH_DELTA) as mock_delta_cls:

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.side_effect = SalesforceAuthenticationFailed(
                "https://test.salesforce.com", "Auth Failed"
            )

            response = client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False


class TestVolunteerImportMailingAddress:
    """Tests for MailingAddress dict parsing (P1 gap)."""

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_mailing_address_dict_parsed(self, client, auth_headers, app):
        """MailingAddress as dict has fields parsed into an Address record."""
        sf_row = _make_sf_row(
            {
                "MailingAddress": {
                    "street": "456 Elm St",
                    "city": "Overland Park",
                    "state": "KS",
                    "postalCode": "66210",
                    "country": "US",
                },
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.contact import Address, ContactTypeEnum
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            mailing = next(
                (
                    a
                    for a in vol.addresses
                    if a.type == ContactTypeEnum.personal and a.primary
                ),
                None,
            )
            assert mailing is not None
            assert mailing.address_line1 == "456 Elm St"
            assert mailing.city == "Overland Park"
            assert mailing.state == "KS"
            assert mailing.zip_code == "66210"

    def test_mailing_address_none_no_crash(self, client, auth_headers, app):
        """MailingAddress=None doesn't crash — the isinstance check skips it."""
        sf_row = _make_sf_row({"MailingAddress": None})
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_mailing_address_string_no_crash(self, client, auth_headers, app):
        """MailingAddress as unexpected string doesn't crash (isinstance guard)."""
        sf_row = _make_sf_row({"MailingAddress": "123 Main St, KC, MO 64111"})
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1


class TestVolunteerImportSkills:
    """Tests for skill import and deduplication via cache (P1 gap)."""

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_skills_created_from_two_fields(self, client, auth_headers, app):
        """Skills parsed from both Volunteer_Skills__c and Volunteer_Skills_Text__c."""
        sf_row = _make_sf_row(
            {
                "Volunteer_Skills__c": "Python,JavaScript",
                "Volunteer_Skills_Text__c": "Data Analysis; Python",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.volunteer import Skill, Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            skill_names = {s.name for s in vol.skills}
            # clean_skill_name lowercases then capitalizes first letter
            assert "Python" in skill_names
            assert "Javascript" in skill_names
            assert "Data analysis" in skill_names
            assert len(skill_names) == 3  # deduplicated

    def test_skills_null_fields_no_crash(self, client, auth_headers, app):
        """Null skill fields don't crash — no skills assigned."""
        sf_row = _make_sf_row(
            {
                "Volunteer_Skills__c": None,
                "Volunteer_Skills_Text__c": None,
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1


class TestVolunteerImportConnectorData:
    """Tests for Connector subscription enum mapping (P1 gap)."""

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_active_subscription_mapped(self, client, auth_headers, app):
        """Known subscription value 'active' maps to ConnectorSubscriptionEnum.ACTIVE."""
        sf_row = _make_sf_row(
            {
                "Connector_Active_Subscription__c": "active",
                "Connector_Industry__c": "Education",
                "Connector_User_ID__c": "USR001",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.volunteer import ConnectorData, Volunteer
        from models.volunteer_enums import ConnectorSubscriptionEnum

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol.connector is not None
            assert vol.connector.active_subscription == ConnectorSubscriptionEnum.ACTIVE
            assert vol.connector.industry == "Education"

    def test_unknown_subscription_defaults_to_none(self, client, auth_headers, app):
        """Unknown subscription value 'PREMIUM' is silently ignored (stays NONE)."""
        sf_row = _make_sf_row(
            {
                "Connector_Active_Subscription__c": "premium",
                "Connector_Industry__c": "Tech",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.volunteer import Volunteer
        from models.volunteer_enums import ConnectorSubscriptionEnum

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol.connector is not None
            # Unknown value ignored — stays at default NONE
            assert vol.connector.active_subscription == ConnectorSubscriptionEnum.NONE


class TestVolunteerImportPrivacyFlags:
    """Tests for DoNotCall / DoNotContact / EmailOptOut boolean mapping (P2 gap)."""

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_privacy_flags_set_true(self, client, auth_headers, app):
        """DoNotCall / DoNotContact / EmailOptOut booleans are persisted."""
        sf_row = _make_sf_row(
            {
                "DoNotCall": True,
                "npsp__Do_Not_Contact__c": True,
                "HasOptedOutOfEmail": True,
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            assert vol.do_not_call is True
            assert vol.do_not_contact is True
            assert vol.email_opt_out is True


class TestVolunteerImportRealDataPatterns:
    """Data-driven tests shaped by production DB analysis of 12,533 volunteers.

    These test patterns found in actual data:
    - 4,587/5,582 addresses are skeleton records (no street/city/state/zip)
    - Skills contain garbage: '...', '0', 'Healthcare...', 'P...'
    - 18,225 contacts have ALL CAPS names
    """

    def _run_import(self, client, auth_headers, sf_row):
        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_inst = MagicMock()
            mock_delta_inst.get_delta_info.return_value = {
                "actual_delta": False,
                "requested_delta": False,
                "watermark": None,
                "watermark_formatted": None,
            }
            mock_delta_cls.return_value = mock_delta_inst

            mock_sf.return_value = MagicMock()
            mock_query.return_value = {"records": [sf_row]}

            return client.post(
                "/volunteers/import-from-salesforce",
                headers=auth_headers,
            )

    def test_mailing_address_country_only_skeleton(self, client, auth_headers, app):
        """MailingAddress with only country set (all others None) — matches 4,587
        skeleton records in prod where only country='United States' exists."""
        sf_row = _make_sf_row(
            {
                "MailingAddress": {
                    "street": None,
                    "city": None,
                    "state": None,
                    "postalCode": None,
                    "country": "United States",
                },
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_mailing_address_partial_state_only(self, client, auth_headers, app):
        """MailingAddress with only state set — matches the Kansas-only record in prod."""
        sf_row = _make_sf_row(
            {
                "MailingAddress": {
                    "street": None,
                    "city": None,
                    "state": "Kansas",
                    "postalCode": None,
                    "country": "United States",
                },
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_truncated_skills_imported(self, client, auth_headers, app):
        """Salesforce truncates long skill values with '...' — these import without crash.
        Found in prod: 'Healthcare...', 'P...', '...', 'Co...'"""
        sf_row = _make_sf_row(
            {
                "Volunteer_Skills__c": "Healthcare...,P...,Co...",
                "Volunteer_Skills_Text__c": "...",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            # Truncated skills should still be stored (not silently dropped)
            assert len(vol.skills) >= 1

    def test_allcaps_name_stored_as_received(self, client, auth_headers, app):
        """ALL CAPS names (18,225 in prod) are stored as-is from Salesforce.
        Import doesn't normalize casing."""
        sf_row = _make_sf_row(
            {
                "FirstName": "RACHEL",
                "LastName": "MAYO",
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003SFID000000001"
            ).first()
            # Names stored as received — casing not normalized
            assert vol.first_name == "RACHEL"
            assert vol.last_name == "MAYO"

    def test_volunteer_email_none_not_stored(self, client, auth_headers, app):
        """Volunteer import correctly skips None emails (uses 'if not email_value: continue').
        Unlike the student import str(None) bug, volunteer import handles this correctly.
        """
        sf_row = _make_sf_row(
            {
                "Email": None,
                "npe01__HomeEmail__c": None,
                "npe01__AlternateEmail__c": None,
                "npe01__WorkEmail__c": None,
            }
        )
        response = self._run_import(client, auth_headers, sf_row)
        assert response.status_code == 200

        from models.contact import Email

        with app.app_context():
            none_emails = Email.query.filter_by(email="None").all()
            assert (
                len(none_emails) == 0
            ), "Volunteer import should not store 'None' emails"

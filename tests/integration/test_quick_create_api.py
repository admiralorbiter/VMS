import pytest

from models import Organization, Teacher, Volunteer, db
from models.organization import VolunteerOrganization


def test_create_teacher_api(client, test_admin):
    """Test the immediate teacher creation API."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_admin.id)

    # 1. Valid Creation
    payload = {
        "first_name": "API_Teacher_First",
        "last_name": "API_Teacher_Last",
        "school": "API_School",
    }
    response = client.post("/virtual/usage/api/create-teacher", json=payload)
    if response.status_code != 200:
        print(f"ERROR RESPONSE: {response.get_json()}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["name"] == "API_Teacher_First API_Teacher_Last"
    assert "id" in data

    # Verify DB
    with client.application.app_context():
        teacher = Teacher.query.get(data["id"])
        assert teacher is not None
        assert teacher.first_name == "API_Teacher_First"
        assert teacher.school.name == "API_School"

    # 2. Duplicate Creation (Should return existing)
    response_dup = client.post("/virtual/usage/api/create-teacher", json=payload)
    assert response_dup.status_code == 200
    data_dup = response_dup.get_json()
    assert data_dup["success"] is True
    assert data_dup["id"] == data["id"]  # Should be same ID

    # 3. Missing Fields
    invalid_payload = {"first_name": "NoLast"}
    response_inv = client.post(
        "/virtual/usage/api/create-teacher", json=invalid_payload
    )
    assert response_inv.status_code == 400


def test_create_presenter_api(client, test_admin):
    """Test the immediate presenter creation API."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_admin.id)

    # 1. Valid Creation
    payload = {
        "first_name": "API_Pres_First",
        "last_name": "API_Pres_Last",
        "organization": "API_Org",
    }
    response = client.post("/virtual/usage/api/create-presenter", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["name"] == "API_Pres_First API_Pres_Last"
    assert data["organization"] == "API_Org"
    assert "id" in data

    # Verify DB
    with client.application.app_context():
        vol = Volunteer.query.get(data["id"])
        assert vol is not None
        assert vol.first_name == "API_Pres_First"

        # Verify Org Link
        vol_org = VolunteerOrganization.query.filter_by(volunteer_id=vol.id).first()
        assert vol_org is not None
        assert vol_org.organization.name == "API_Org"

    # 2. Missing Org (Should still work for volunteer)
    payload_no_org = {"first_name": "API_Solo", "last_name": "Person"}
    response_solo = client.post(
        "/virtual/usage/api/create-presenter", json=payload_no_org
    )
    assert response_solo.status_code == 200

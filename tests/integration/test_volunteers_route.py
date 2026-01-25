import pytest

from models import db
from models.contact import Email, LocalStatusEnum
from models.organization import Organization, VolunteerOrganization
from models.volunteer import Skill, Volunteer, VolunteerSkill


@pytest.fixture
def volunteers_route_data(app):
    with app.app_context():
        # Create Skills
        skill_python = Skill(name="Python")
        skill_java = Skill(name="Java")
        db.session.add_all([skill_python, skill_java])
        db.session.commit()

        # Create Organizations
        org_tech = Organization(name="TechCorp")
        org_edu = Organization(name="EduInstitute")
        db.session.add_all([org_tech, org_edu])
        db.session.commit()

        # Create Volunteers
        # V1: Victor, TechCorp, Local, Python, Title=Engineer
        v1 = Volunteer(
            first_name="Victor",
            last_name="One",
            title="Senior Engineer",
            industry="Technology",
            local_status=LocalStatusEnum.local,
            organization_name="TechCorp",  # Explicit field often used in this view
        )
        db.session.add(v1)
        db.session.commit()

        v1_email = Email(contact_id=v1.id, email="v1@example.com", primary=True)
        db.session.add(v1_email)

        # V2: Victoria, TechCorp, Unknown, Java
        v2 = Volunteer(
            first_name="Victoria",
            last_name="Two",
            title="Manager",
            industry="Technology",
            local_status=LocalStatusEnum.unknown,
            organization_name="TechCorp",
        )
        db.session.add(v2)
        db.session.commit()

        v2_email = Email(contact_id=v2.id, email="v2@example.com", primary=True)
        db.session.add(v2_email)

        # V3: Vol Three, Education (Industry), Local
        v3 = Volunteer(
            first_name="Vol",
            last_name="Three",
            title="Teacher",
            industry="Education",
            local_status=LocalStatusEnum.local,
            organization_name="EduInstitute",
        )
        db.session.add(v3)
        db.session.commit()

        v3_email = Email(contact_id=v3.id, email="v3@example.com", primary=True)
        db.session.add(v3_email)

        # V4: Vol Four, Local
        v4 = Volunteer(
            first_name="Vol",
            last_name="Four",
            title="Consultant",
            industry="Business",
            local_status=LocalStatusEnum.local,
        )
        db.session.add(v4)
        db.session.commit()

        v4_email = Email(contact_id=v4.id, email="v4@example.com", primary=True)
        db.session.add(v4_email)

        # Link Orgs (using relationship objects)
        vo1 = VolunteerOrganization(
            volunteer_id=v1.id,
            organization_id=org_tech.id,
            role="Senior Engineer",
            is_primary=True,
            status="Current",
        )
        vo2 = VolunteerOrganization(
            volunteer_id=v2.id,
            organization_id=org_tech.id,
            role="Manager",
            is_primary=True,
            status="Current",
        )
        # V3 linked to Edu
        vo3 = VolunteerOrganization(
            volunteer_id=v3.id,
            organization_id=org_edu.id,
            role="Teacher",
            is_primary=True,
            status="Current",
        )
        db.session.add_all([vo1, vo2, vo3])

        # Link Skills
        vs1 = VolunteerSkill(volunteer_id=v1.id, skill_id=skill_python.id)
        vs2 = VolunteerSkill(volunteer_id=v2.id, skill_id=skill_java.id)
        db.session.add_all([vs1, vs2])

        db.session.commit()

        yield


def test_volunteers_search_tc300(client, auth_headers, volunteers_route_data):
    """TC-300: Name search 'Vict' -> Returns V1, V2"""
    response = client.get("/volunteers?search_name=Vict", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" in content
    assert "Vol Three" not in content


def test_volunteers_org_filter_tc301(client, auth_headers, volunteers_route_data):
    """TC-301: Org filter 'TechCorp' -> Returns V1, V2"""
    response = client.get("/volunteers?org_search=TechCorp", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" in content
    assert "Vol Three" not in content


def test_volunteers_skill_filter_tc302(client, auth_headers, volunteers_route_data):
    """TC-302: Skill filter 'Python' -> Returns V1"""
    response = client.get("/volunteers?skill_search=Python", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" not in content


def test_volunteers_career_type_tc303(client, auth_headers, volunteers_route_data):
    """TC-303: Career/Industry 'Education' -> Returns V3"""
    # Using org_search to search for Industry
    response = client.get("/volunteers?org_search=Education", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    # Check for name parts because template might add extra spaces
    assert "Vol" in content
    assert "Three" in content
    assert "Victor" not in content


def test_volunteers_local_filter_tc304(client, auth_headers, volunteers_route_data):
    """TC-304: Local filter -> Returns V1, V3, V4"""
    # UI sends 'true' for Local
    response = client.get("/volunteers?local_status=true", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Vol" in content and "Three" in content
    assert "Four" in content
    assert "Victoria" not in content


def test_volunteers_role_filter_tc306(client, auth_headers, volunteers_route_data):
    """TC-306: Role search 'Engineer' -> Returns V1"""
    response = client.get("/volunteers?org_search=Engineer", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" not in content


def test_volunteers_empty_search_tc307(client, auth_headers, volunteers_route_data):
    """TC-307: Empty results"""
    response = client.get("/volunteers?search_name=NonExistent", headers=auth_headers)
    assert response.status_code == 200
    content = response.data.decode()
    # Looking for some "No volunteers found" message or empty table
    # I suspect the template might just show empty table.
    assert "Victor" not in content


def test_volunteers_performance_tc308(client, auth_headers, volunteers_route_data):
    """TC-308: Performance"""
    import time

    start = time.time()
    response = client.get("/volunteers", headers=auth_headers)
    end = time.time()
    assert end - start < 1.0

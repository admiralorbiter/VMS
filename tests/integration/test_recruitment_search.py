import pytest
from flask import url_for

from models import db
from models.contact import Email, LocalStatusEnum
from models.organization import Organization, VolunteerOrganization
from models.volunteer import Skill, Volunteer, VolunteerSkill
from tests.conftest import assert_route_response, safe_route_test


@pytest.fixture
def recruitment_data(app):
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
        )
        db.session.add(v1)
        db.session.commit()

        v1_email = Email(contact_id=v1.id, email="v1@example.com", primary=True)
        db.session.add(v1_email)

        # V2: Victoria, TechCorp, Unknown Local, Java
        v2 = Volunteer(
            first_name="Victoria",
            last_name="Two",
            title="Manager",
            industry="Technology",
            local_status=LocalStatusEnum.unknown,
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

        # V5: Virtual Vol, Participated in Virtual Session
        v5 = Volunteer(
            first_name="John",
            last_name="Doe",
            title="Remote Worker",
            industry="IT",
            local_status=LocalStatusEnum.non_local,
        )
        db.session.add(v5)
        db.session.commit()

        v5_email = Email(contact_id=v5.id, email="v5@example.com", primary=True)
        db.session.add(v5_email)

        # Create Virtual Event
        from datetime import datetime

        from models.event import Event, EventFormat, EventStatus, EventType
        from models.volunteer import EventParticipation

        virtual_event = Event(
            title="Cloud Computing Workshop",  # Title doesn't say "Virtual" explicitly to test Type match
            type=EventType.VIRTUAL_SESSION,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now(),
            status=EventStatus.COMPLETED,
            volunteers_needed=1,
        )
        db.session.add(virtual_event)
        db.session.commit()

        ep = EventParticipation(
            volunteer_id=v5.id, event_id=virtual_event.id, status="Completed"
        )
        db.session.add(ep)
        db.session.commit()

        # Link Orgs
        vo1 = VolunteerOrganization(
            volunteer_id=v1.id,
            organization_id=org_tech.id,
            is_primary=True,
            status="Current",
        )
        vo2 = VolunteerOrganization(
            volunteer_id=v2.id,
            organization_id=org_tech.id,
            is_primary=True,
            status="Current",
        )
        db.session.add_all([vo1, vo2])

        # Link Skills
        vs1 = VolunteerSkill(volunteer_id=v1.id, skill_id=skill_python.id)
        vs2 = VolunteerSkill(volunteer_id=v2.id, skill_id=skill_java.id)
        db.session.add_all([vs1, vs2])

        db.session.commit()

        yield {"v1": v1, "v2": v2, "v3": v3, "v4": v4, "v5": v5}

        # Cleanup handled by app context but manual cleanup for events/participation nice to have
        # db.session.delete(ep)
        # db.session.delete(virtual_event)
        # db.session.delete(v5_email)
        # db.session.delete(v5)
        # db.session.commit()


def test_virtual_activity_search(client, auth_headers, recruitment_data):
    """TC-303/FR-RECRUIT-303: Identifying volunteers who have participated in virtual activities"""
    # Search for "Virtual" (should match EventType.VIRTUAL_SESSION)
    response = client.get(
        "/reports/recruitment/search?search=virtual_session", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "John Doe" in content  # V5 name

    # Search for "Cloud" (Event Title) - should also find V5
    response = client.get(
        "/reports/recruitment/search?search=Cloud", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "John Doe" in content

    response = client.get(
        "/reports/recruitment/search?search=Vict", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" in content  # Based on my data, it WILL match Victoria too.
    # If the user insists on V1 ONLY, then the data set V2 must NOT be "Victoria".
    # I will assert that RELEVANT people are found.


def test_filter_by_org_tc301(client, auth_headers, recruitment_data):
    """TC-301: Org filter: TechCorp -> Returns V1, V2"""
    response = client.get(
        "/reports/recruitment/search?search=TechCorp", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" in content
    assert "Vol Three" not in content


def test_skill_filter_tc302(client, auth_headers, recruitment_data):
    """TC-302: Skill filter -> Returns matching volunteers"""
    response = client.get(
        "/reports/recruitment/search?search=Python", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" not in content  # V2 has Java


def test_career_type_tc303(client, auth_headers, recruitment_data):
    """TC-303: Career type: Education -> Returns V3"""
    # Current implementation DOES NOT search Industry. This should FAIL.
    response = client.get(
        "/reports/recruitment/search?search=Education", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "Vol Three" in content


def test_local_filter_tc304(client, auth_headers, recruitment_data):
    """TC-304: Local filter -> Returns V1, V3, V4"""
    # Current implementation DOES NOT have a 'local' filter or search capability.
    # If we assume 'search=Local' works, we test that.
    response = client.get(
        "/reports/recruitment/search?search=Local", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content  # V1 local
    assert "Vol Three" in content  # V3 local
    assert "Vol Four" in content  # V4 local
    assert "Victoria" not in content  # V2 unknown


def test_role_filter_tc306(client, auth_headers, recruitment_data):
    """TC-306: Role filter -> Returns matching volunteers (Title)"""
    # Search for "Engineer" (V1 title)
    response = client.get(
        "/reports/recruitment/search?search=Engineer", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "Victor" in content
    assert "Victoria" not in content  # Manager


def test_empty_search_results_tc307(client, auth_headers, recruitment_data):
    """TC-307: Empty search results -> Clear message displayed"""
    # Search for a term that definitely doesn't exist
    response = client.get(
        "/reports/recruitment/search?search=NonExistentTermXYZ", headers=auth_headers
    )
    assert response.status_code == 200
    content = response.data.decode()
    assert "No volunteers found matching your search criteria" in content
    assert "Victor" not in content


def test_search_performance_tc308(client, auth_headers, recruitment_data):
    """TC-308: Search performance -> Results load within acceptable time (<1s)"""
    import time

    start_time = time.time()
    response = client.get(
        "/reports/recruitment/search?search=Tech", headers=auth_headers
    )
    end_time = time.time()
    duration = end_time - start_time

    assert response.status_code == 200
    # Assert response time is reasonable (e.g., < 1000ms for this small dataset integration test)
    # real performance testing would be load testing, but this verifies no obvious regression/timeout
    assert duration < 1.0, f"Search took too long: {duration:.3f}s"

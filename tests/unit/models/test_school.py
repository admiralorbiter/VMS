import pytest

from models import db
from models.district_model import District
from models.school_model import School


def test_new_school(app):
    """Test creating a new school"""
    with app.app_context():
        school = School(
            id="0015f00000TEST123",
            name="Test High School",
            normalized_name="TEST HIGH SCHOOL",
            school_code="4045",
        )

        db.session.add(school)
        db.session.commit()

        # Test basic fields
        assert school.id == "0015f00000TEST123"
        assert school.name == "Test High School"
        assert school.normalized_name == "TEST HIGH SCHOOL"
        assert school.school_code == "4045"

        # Test __repr__ method
        assert str(school) == "<School Test High School>"

        # Cleanup
        db.session.delete(school)
        db.session.commit()


def test_school_district_relationship(app):
    """Test relationship between School and District"""
    with app.app_context():
        # Create a district first
        district = District(name="Test District", salesforce_id="0015f00000JVZsFAAX")
        db.session.add(district)
        db.session.commit()

        # Create school with district relationship
        school = School(
            id="0015f00000TEST456",
            name="District Test School",
            district_id=district.id,
            salesforce_district_id="0015f00000JVZsFAAX",
        )

        db.session.add(school)
        db.session.commit()

        # Test relationships
        assert school.district_id == district.id
        assert school.district.name == "Test District"
        assert school in district.schools

        # Test lazy loading of schools relationship
        schools_count = district.schools.count()
        assert schools_count == 1

        # Cleanup
        db.session.delete(school)
        db.session.delete(district)
        db.session.commit()


def test_school_without_district(app):
    """Test creating a school without a district"""
    with app.app_context():
        school = School(id="0015f00000TEST789", name="Independent School")
        db.session.add(school)
        db.session.commit()

        assert school.district_id is None
        assert school.district is None

        # Cleanup
        db.session.delete(school)
        db.session.commit()


def test_school_cascade_delete(app):
    """Test cascade delete behavior"""
    with app.app_context():
        # Create district first
        district = District(
            name="Test District",
            district_code="9999",
            salesforce_id="0015f00000TEST999",
        )
        db.session.add(district)
        db.session.commit()

        # Create school
        school = School(
            id="0015f00000TEST789",
            name="Cascade Test School",
            district_id=district.id,
            salesforce_district_id="0015f00000TEST999",
        )
        db.session.add(school)
        db.session.commit()

        # Store ID for verification
        school_id = school.id

        # Delete district
        db.session.delete(district)
        db.session.commit()

        # Verify school was deleted
        assert db.session.get(School, school_id) is None


def test_school_salesforce_district_id_mismatch(app):
    """Test handling of mismatched salesforce_district_id"""
    with app.app_context():
        district = District(name="Test District", salesforce_id="0015f00000JVZsFAAX")
        db.session.add(district)
        db.session.commit()

        school = School(
            id="0015f00000TEST456",
            name="Mismatch Test School",
            district_id=district.id,
            salesforce_district_id="DIFFERENT_ID",  # Mismatched ID
        )
        db.session.add(school)
        db.session.commit()

        assert school.district_id == district.id
        assert school.salesforce_district_id != district.salesforce_id

        # Cleanup
        db.session.delete(school)
        db.session.delete(district)
        db.session.commit()


def test_multiple_schools_per_district(app):
    """Test adding multiple schools to one district"""
    with app.app_context():
        district = District(
            name="Multi-School District", salesforce_id="0015f00000MULTI01"
        )
        db.session.add(district)
        db.session.commit()

        # Add multiple schools
        schools = []
        for i in range(3):
            school = School(
                id=f"0015f00000TEST{i}",
                name=f"School {i}",
                district_id=district.id,
                salesforce_district_id=district.salesforce_id,
            )
            schools.append(school)
            db.session.add(school)
        db.session.commit()

        # Verify relationships
        assert district.schools.count() == 3
        for school in schools:
            assert school.district_id == district.id

        # Cleanup
        for school in schools:
            db.session.delete(school)
        db.session.delete(district)
        db.session.commit()

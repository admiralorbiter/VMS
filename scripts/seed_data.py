"""
Seed Data Script for Polaris VMS
================================

Creates test data for development and testing purposes. Run with:
    python scripts/seed_data.py [options]

Options:
    --all           Seed all data
    --users         Seed users only
    --reference     Seed reference data (districts, schools)
    --people        Seed people (teachers, volunteers)
    --events        Seed virtual events
    --clear         Clear existing data first (USE WITH CAUTION)

Examples:
    python scripts/seed_data.py --all
    python scripts/seed_data.py --users --reference
    python scripts/seed_data.py --clear --all
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from models import db
from models.contact import ContactTypeEnum, Email
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher, TeacherStatus
from models.user import SecurityLevel, TenantRole, User
from models.volunteer import Volunteer, VolunteerStatus


def clear_data():
    """Clear existing data from the database. USE WITH CAUTION."""
    print("⚠️  Clearing existing data...")

    # Delete in order to respect foreign keys
    EventTeacher.query.delete()
    Event.query.filter(Event.type == EventType.VIRTUAL_SESSION).delete()
    Teacher.query.delete()
    Volunteer.query.delete()
    School.query.delete()
    District.query.delete()
    # Don't delete users by default - keep existing admin

    db.session.commit()
    print("✅ Data cleared")


def seed_users():
    """Create test users with different roles."""
    print("👤 Seeding users...")

    users_data = [
        {
            "username": "admin",
            "email": "admin@prepkc.org",
            "first_name": "Admin",
            "last_name": "User",
            "security_level": SecurityLevel.ADMIN,
        },
        {
            "username": "staff",
            "email": "staff@prepkc.org",
            "first_name": "Staff",
            "last_name": "Member",
            "security_level": SecurityLevel.MANAGER,
        },
        {
            "username": "coordinator",
            "email": "coordinator@prepkc.org",
            "first_name": "Program",
            "last_name": "Coordinator",
            "security_level": SecurityLevel.SUPERVISOR,
        },
        {
            "username": "viewer",
            "email": "viewer@prepkc.org",
            "first_name": "Report",
            "last_name": "Viewer",
            "security_level": SecurityLevel.USER,
        },
    ]

    created = 0
    for data in users_data:
        existing = User.query.filter_by(username=data["username"]).first()
        if not existing:
            user = User(**data)
            # Hash password using werkzeug
            from werkzeug.security import generate_password_hash

            user.password_hash = generate_password_hash("testpass123")
            db.session.add(user)
            created += 1
            print(f"  Created user: {data['username']}")
        else:
            print(f"  Skipped (exists): {data['username']}")

    db.session.commit()
    print(f"✅ Users seeded ({created} created)")


def seed_reference_data():
    """Create districts and schools for testing."""
    print("🏫 Seeding reference data (districts, schools)...")

    # Districts - include the "main districts" the Virtual Usage page filters for
    districts_data = [
        # Main districts (shown on Virtual Usage dashboard by default)
        {"name": "Hickman Mills School District", "district_code": "HMSD"},
        {"name": "Grandview School District", "district_code": "GSD"},
        {"name": "Kansas City Kansas Public Schools", "district_code": "KCKPS"},
        # Additional districts for testing
        {"name": "Kansas City Public Schools", "district_code": "KCPS"},
        {"name": "North Kansas City Schools", "district_code": "NKCS"},
    ]

    districts = {}
    for data in districts_data:
        existing = District.query.filter_by(name=data["name"]).first()
        if not existing:
            district = District(**data)
            db.session.add(district)
            db.session.flush()  # Get ID
            districts[data["district_code"]] = district
            print(f"  Created district: {data['name']}")
        else:
            districts[data["district_code"]] = existing
            print(f"  Skipped (exists): {data['name']}")

    db.session.commit()

    # Schools (need district IDs first)
    schools_data = [
        # Hickman Mills schools (main district)
        {
            "id": "SCH001",
            "name": "Hickman Mills High School",
            "district_code": "HMSD",
            "level": "High",
        },
        {
            "id": "SCH002",
            "name": "Smith-Hale Middle School",
            "district_code": "HMSD",
            "level": "Middle",
        },
        {
            "id": "SCH003",
            "name": "Ervin Elementary",
            "district_code": "HMSD",
            "level": "Elementary",
        },
        # Grandview schools (main district)
        {
            "id": "SCH004",
            "name": "Grandview High School",
            "district_code": "GSD",
            "level": "High",
        },
        {
            "id": "SCH005",
            "name": "Grandview Middle School",
            "district_code": "GSD",
            "level": "Middle",
        },
        {
            "id": "SCH006",
            "name": "Belvidere Elementary",
            "district_code": "GSD",
            "level": "Elementary",
        },
        # KCK schools (main district)
        {
            "id": "SCH007",
            "name": "Sumner Academy",
            "district_code": "KCKPS",
            "level": "High",
        },
        {
            "id": "SCH008",
            "name": "Washington High School",
            "district_code": "KCKPS",
            "level": "High",
        },
        {
            "id": "SCH009",
            "name": "Central Middle School",
            "district_code": "KCKPS",
            "level": "Middle",
        },
        # KCPS schools
        {
            "id": "SCH010",
            "name": "Lincoln College Preparatory Academy",
            "district_code": "KCPS",
            "level": "High",
        },
        {
            "id": "SCH011",
            "name": "Central High School",
            "district_code": "KCPS",
            "level": "High",
        },
        # NKCS schools
        {
            "id": "SCH012",
            "name": "Oak Park High School",
            "district_code": "NKCS",
            "level": "High",
        },
        {
            "id": "SCH013",
            "name": "Staley High School",
            "district_code": "NKCS",
            "level": "High",
        },
        {
            "id": "SCH014",
            "name": "Northgate Middle School",
            "district_code": "NKCS",
            "level": "Middle",
        },
    ]

    created = 0
    for data in schools_data:
        existing = School.query.get(data["id"])
        if not existing:
            district = districts.get(data["district_code"])
            if district:
                school = School(
                    id=data["id"],
                    name=data["name"],
                    district_id=district.id,
                    level=data["level"],
                    normalized_name=data["name"].lower(),
                )
                db.session.add(school)
                created += 1
                print(f"  Created school: {data['name']}")
        else:
            print(f"  Skipped (exists): {data['name']}")

    db.session.commit()
    print(f"✅ Reference data seeded ({created} schools created)")

    return districts


def seed_people():
    """Create test teachers and volunteers."""
    print("👥 Seeding people (teachers, volunteers)...")

    schools = School.query.all()
    if not schools:
        print("  ⚠️  No schools found. Run --reference first.")
        return

    # Teachers
    teachers_data = [
        {"first_name": "Sarah", "last_name": "Johnson", "department": "Science"},
        {"first_name": "Michael", "last_name": "Chen", "department": "Mathematics"},
        {"first_name": "Emily", "last_name": "Williams", "department": "English"},
        {
            "first_name": "David",
            "last_name": "Martinez",
            "department": "Social Studies",
        },
        {"first_name": "Jennifer", "last_name": "Brown", "department": "Technology"},
        {"first_name": "Robert", "last_name": "Taylor", "department": "Science"},
        {"first_name": "Lisa", "last_name": "Anderson", "department": "Mathematics"},
        {
            "first_name": "James",
            "last_name": "Thomas",
            "department": "Career Education",
        },
        {"first_name": "Maria", "last_name": "Garcia", "department": "Counseling"},
        {"first_name": "William", "last_name": "Jackson", "department": "Business"},
    ]

    teacher_created = 0
    for i, data in enumerate(teachers_data):
        email = f"{data['first_name'].lower()}.{data['last_name'].lower()}@school.edu"
        existing = Teacher.query.join(Email).filter(Email.email == email).first()

        if not existing:
            teacher = Teacher(
                first_name=data["first_name"],
                last_name=data["last_name"],
                department=data["department"],
                school_id=schools[i % len(schools)].id,
                status=TeacherStatus.ACTIVE,
                active=True,
            )
            db.session.add(teacher)
            db.session.flush()

            # Add email
            email_obj = Email(
                contact_id=teacher.id,
                email=email,
                type=ContactTypeEnum.professional,
                primary=True,
            )
            db.session.add(email_obj)
            teacher_created += 1
            print(f"  Created teacher: {data['first_name']} {data['last_name']}")

    db.session.commit()

    # Volunteers
    volunteers_data = [
        {
            "first_name": "Alex",
            "last_name": "Rivera",
            "organization_name": "Tech Corp",
            "title": "Software Engineer",
        },
        {
            "first_name": "Jordan",
            "last_name": "Smith",
            "organization_name": "Finance Inc",
            "title": "Financial Analyst",
        },
        {
            "first_name": "Taylor",
            "last_name": "Lee",
            "organization_name": "Healthcare Co",
            "title": "Nurse Practitioner",
        },
        {
            "first_name": "Morgan",
            "last_name": "Wilson",
            "organization_name": "Engineering LLC",
            "title": "Civil Engineer",
        },
        {
            "first_name": "Casey",
            "last_name": "Jones",
            "organization_name": "Marketing Agency",
            "title": "Marketing Manager",
        },
        {
            "first_name": "Riley",
            "last_name": "Davis",
            "organization_name": "Law Firm LLP",
            "title": "Attorney",
        },
        {
            "first_name": "Avery",
            "last_name": "Miller",
            "organization_name": "Biotech Inc",
            "title": "Research Scientist",
        },
        {
            "first_name": "Quinn",
            "last_name": "Moore",
            "organization_name": "Architecture Studio",
            "title": "Architect",
        },
    ]

    volunteer_created = 0
    for data in volunteers_data:
        email = f"{data['first_name'].lower()}.{data['last_name'].lower()}@company.com"
        existing = Volunteer.query.join(Email).filter(Email.email == email).first()

        if not existing:
            volunteer = Volunteer(
                first_name=data["first_name"],
                last_name=data["last_name"],
                organization_name=data["organization_name"],
                title=data["title"],
                status=VolunteerStatus.ACTIVE,
            )
            db.session.add(volunteer)
            db.session.flush()

            # Add email
            email_obj = Email(
                contact_id=volunteer.id,
                email=email,
                type=ContactTypeEnum.professional,
                primary=True,
            )
            db.session.add(email_obj)
            volunteer_created += 1
            print(f"  Created volunteer: {data['first_name']} {data['last_name']}")

    db.session.commit()
    print(
        f"✅ People seeded ({teacher_created} teachers, {volunteer_created} volunteers)"
    )


def seed_virtual_events():
    """Create test virtual events with various statuses for Phase D testing."""
    print("📅 Seeding virtual events...")

    schools = School.query.all()
    teachers = Teacher.query.limit(10).all()
    volunteers = Volunteer.query.limit(8).all()

    if not schools or not teachers:
        print("  ⚠️  Need schools and teachers. Run --reference and --people first.")
        return

    now = datetime.now(timezone.utc)

    # Virtual events with various statuses for testing Phase D features
    events_data = [
        # Completed events
        {
            "title": "Introduction to Software Engineering",
            "status": EventStatus.COMPLETED,
            "days_ago": 7,
            "school_idx": 0,
            "has_teacher": True,
            "has_presenter": True,
        },
        {
            "title": "Healthcare Careers Panel",
            "status": EventStatus.COMPLETED,
            "days_ago": 14,
            "school_idx": 1,
            "has_teacher": True,
            "has_presenter": True,
        },
        # Completed WITHOUT presenter (should get MISSING_PRESENTER flag)
        {
            "title": "Financial Literacy Workshop",
            "status": EventStatus.COMPLETED,
            "days_ago": 3,
            "school_idx": 2,
            "has_teacher": True,
            "has_presenter": False,  # Missing!
        },
        # Events missing teacher (should get MISSING_TEACHER flag)
        {
            "title": "Engineering Day",
            "status": EventStatus.CONFIRMED,
            "days_ago": -7,  # Future
            "school_idx": 3,
            "has_teacher": False,  # Missing!
            "has_presenter": True,
        },
        # Cancelled events without reason (should get NEEDS_REASON flag)
        {
            "title": "Career Fair 2026",
            "status": EventStatus.CANCELLED,
            "days_ago": 5,
            "school_idx": 4,
            "has_teacher": True,
            "has_presenter": False,
            "cancellation_reason": None,  # Missing!
        },
        # Cancelled event WITH reason (should NOT get flag)
        {
            "title": "Mock Interview Day",
            "status": EventStatus.CANCELLED,
            "days_ago": 10,
            "school_idx": 5,
            "has_teacher": True,
            "has_presenter": False,
            "cancellation_reason": "weather",
        },
        # Draft events in the past (should get NEEDS_ATTENTION flag)
        {
            "title": "Tech Talk Series",
            "status": EventStatus.DRAFT,
            "days_ago": 2,  # Past draft!
            "school_idx": 6,
            "has_teacher": False,
            "has_presenter": False,
        },
        # Upcoming confirmed events
        {
            "title": "College Application Workshop",
            "status": EventStatus.CONFIRMED,
            "days_ago": -14,  # Future
            "school_idx": 7,
            "has_teacher": True,
            "has_presenter": True,
        },
        {
            "title": "STEM Career Exploration",
            "status": EventStatus.CONFIRMED,
            "days_ago": -21,  # Future
            "school_idx": 8 % len(schools),
            "has_teacher": True,
            "has_presenter": True,
        },
        # Requested event
        {
            "title": "Entrepreneur Workshop",
            "status": EventStatus.REQUESTED,
            "days_ago": -30,  # Future
            "school_idx": 9 % len(schools),
            "has_teacher": True,
            "has_presenter": False,
        },
    ]

    created = 0
    for data in events_data:
        existing = Event.query.filter_by(
            title=data["title"], type=EventType.VIRTUAL_SESSION
        ).first()

        if not existing:
            event_date = now - timedelta(days=data["days_ago"])
            school = schools[data["school_idx"] % len(schools)]

            event = Event(
                title=data["title"],
                type=EventType.VIRTUAL_SESSION,
                format=EventFormat.VIRTUAL,
                status=data["status"],
                start_date=event_date,
                end_date=event_date + timedelta(hours=1),
                location="Pathful Virtual",
                school=school.id,
                import_source="seed_data",
                pathful_session_id=f"SEED-{created+1:04d}",
            )

            # Set cancellation reason if provided
            if data.get("cancellation_reason"):
                event.cancellation_reason = data["cancellation_reason"]

            db.session.add(event)
            db.session.flush()

            # Add teacher if specified
            if data.get("has_teacher") and teachers:
                teacher = teachers[created % len(teachers)]
                event_teacher = EventTeacher(
                    event_id=event.id,
                    teacher_id=teacher.id,
                    status=(
                        "confirmed"
                        if data["status"] == EventStatus.COMPLETED
                        else "pending"
                    ),
                )
                db.session.add(event_teacher)

            # Note: has_presenter would add to event_volunteers, but we're focusing on teacher tagging

            created += 1
            flag_info = []
            if data["status"] == EventStatus.COMPLETED and not data.get(
                "has_presenter"
            ):
                flag_info.append("MISSING_PRESENTER")
            if not data.get("has_teacher"):
                flag_info.append("MISSING_TEACHER")
            if data["status"] == EventStatus.CANCELLED and not data.get(
                "cancellation_reason"
            ):
                flag_info.append("NEEDS_REASON")
            if data["status"] == EventStatus.DRAFT and data["days_ago"] > 0:
                flag_info.append("NEEDS_ATTENTION")

            flags = f" → Flags: {', '.join(flag_info)}" if flag_info else ""
            print(f"  Created event: {data['title']} ({data['status'].value}){flags}")

    db.session.commit()
    print(f"✅ Virtual events seeded ({created} created)")
    print(
        "  ℹ️  Note: Several events are intentionally missing data to test Phase D flagging"
    )


def main():
    parser = argparse.ArgumentParser(description="Seed Polaris database with test data")
    parser.add_argument("--all", action="store_true", help="Seed all data")
    parser.add_argument("--users", action="store_true", help="Seed users only")
    parser.add_argument(
        "--reference",
        action="store_true",
        help="Seed reference data (districts, schools)",
    )
    parser.add_argument(
        "--people", action="store_true", help="Seed people (teachers, volunteers)"
    )
    parser.add_argument("--events", action="store_true", help="Seed virtual events")
    parser.add_argument(
        "--clear", action="store_true", help="Clear existing data first"
    )

    args = parser.parse_args()

    # Default to --all if no specific options provided
    if not any([args.all, args.users, args.reference, args.people, args.events]):
        args.all = True

    app = create_app()

    with app.app_context():
        print("\n🌱 Polaris Seed Data Script")
        print("=" * 40)

        if args.clear:
            confirm = input(
                "⚠️  This will delete existing data. Type 'yes' to confirm: "
            )
            if confirm.lower() == "yes":
                clear_data()
            else:
                print("Cancelled.")
                return

        if args.all or args.users:
            seed_users()

        if args.all or args.reference:
            seed_reference_data()

        if args.all or args.people:
            seed_people()

        if args.all or args.events:
            seed_virtual_events()

        print("\n" + "=" * 40)
        print("🎉 Seeding complete!")
        print("\nTest credentials:")
        print("  admin / testpass123 (Admin)")
        print("  staff / testpass123 (Manager)")
        print("  coordinator / testpass123 (Supervisor)")
        print("  viewer / testpass123 (User)")


if __name__ == "__main__":
    main()

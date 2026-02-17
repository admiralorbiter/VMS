"""
Synthetic Data Generator for VMS
=================================

Generates realistic synthetic data for testing and demos, matching all SQLAlchemy
models and relationships in the system, with support for edge cases.

Usage:
    python scripts/generate_synthetic_data.py [options]

Options:
    --seed SEED           Random seed for deterministic generation (default: random)
    --size SIZE           Dataset size: small, medium, or large (default: medium)
    --mode MODE           Generation mode: demo (happy path) or edge (boundary conditions)
    --counts MODEL=N      Custom counts per model (e.g., --counts volunteer=100 event=50)
    --reset               Clear existing data before generating (USE WITH CAUTION)

Examples:
    python scripts/generate_synthetic_data.py --size small --mode demo
    python scripts/generate_synthetic_data.py --seed 123 --size large --mode edge
    python scripts/generate_synthetic_data.py --counts volunteer=200 event=100
"""

import argparse
import random
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from models import db
from models.volunteer import Skill, Volunteer, VolunteerStatus, VolunteerSkill
from models.district_model import District
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from models.user import User, SecurityLevel, TenantRole
from models.tenant import Tenant
from models.contact import (
    Contact, ContactTypeEnum, Email, Phone, Address,
    GenderEnum, EducationEnum, LocalStatusEnum, RaceEthnicityEnum,
    AgeGroupEnum, SalutationEnum
)
from models.teacher import Teacher, TeacherStatus
from models.student import Student
from models.event import Event, EventType, EventStatus, EventFormat, CancellationReason, EventTeacher
from models.class_model import Class
from models.volunteer import Engagement, EventParticipation
from models.history import History, HistoryType
from models.attendance import EventAttendanceDetail
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date, timezone


class SyntheticDataGenerator:
    """Main generator class for synthetic data."""
    
    def __init__(self, seed=None, size='medium', mode='demo', counts=None):
        """
        Initialize the generator.
        
        Args:
            seed: Random seed for deterministic generation
            size: Dataset size ('small', 'medium', 'large')
            mode: Generation mode ('demo' or 'edge')
            counts: Dict of custom model counts {model_name: count}
        """
        self.seed = seed or random.randint(1, 1000000)
        self.size = size
        self.mode = mode
        self.counts = counts or {}
        
        # Set random seeds for deterministic generation
        random.seed(self.seed)
        
        # Initialize Faker with seed
        try:
            from faker import Faker
            Faker.seed(self.seed)
            self.fake = Faker()
        except ImportError:
            print("ERROR: Faker library not installed. Install with: pip install faker")
            sys.exit(1)
        
        # Size presets
        self.size_presets = {
            'small': {
                'district': 2,
                'school': 5,
                'class': 10,
                'teacher': 10,
                'volunteer': 15,
                'student': 20,
                'event': 10,
                'engagement': 20,
                'history': 15,
            },
            'medium': {
                'district': 5,
                'school': 15,
                'class': 30,
                'teacher': 30,
                'volunteer': 50,
                'student': 100,
                'event': 30,
                'engagement': 50,
                'history': 40,
            },
            'large': {
                'district': 10,
                'school': 50,
                'class': 100,
                'teacher': 100,
                'volunteer': 200,
                'student': 500,
                'event': 100,
                'engagement': 200,
                'history': 150,
            }
        }
    
    def get_count(self, model_name):
        """Get count for a model, checking custom counts first, then size presets."""
        if model_name in self.counts:
            return self.counts[model_name]
        if self.size in self.size_presets:
            return self.size_presets[self.size].get(model_name, 10)
        return 10
    
    def generate_skills(self):
        """Generate Skill records."""
        count = self.get_count('skill')
        print(f"  Creating {count} skills...")
        
        skill_names = [
            "Python Programming", "JavaScript", "Project Management", "Marketing",
            "Financial Analysis", "Data Science", "Public Speaking", "Leadership",
            "Graphic Design", "Sales", "Teaching", "Mentoring", "Event Planning",
            "Software Engineering", "Database Administration", "Web Development",
            "Mobile Development", "Cloud Computing", "Cybersecurity", "Machine Learning"
        ]
        
        created = 0
        for i in range(count):
            try:
                # Use predefined names or generate new ones
                if i < len(skill_names):
                    name = skill_names[i]
                else:
                    name = f"{self.fake.job()} Skills"
                
                # Check if skill already exists
                existing = Skill.query.filter_by(name=name).first()
                if existing:
                    continue
                
                skill = Skill(name=name)
                db.session.add(skill)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating skill {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} skills")
        return Skill.query.all()
    
    def generate_districts(self):
        """Generate District records."""
        count = self.get_count('district')
        print(f"  Creating {count} districts...")
        
        # Predefined district names for realism
        district_names = [
            "Kansas City Public Schools", "Shawnee Mission School District",
            "Blue Valley School District", "Olathe School District",
            "Hickman Mills School District", "Grandview School District",
            "Kansas City Kansas Public Schools", "North Kansas City Schools",
            "Raytown School District", "Independence School District"
        ]
        
        created = 0
        for i in range(count):
            try:
                if i < len(district_names):
                    name = district_names[i]
                    code = ''.join(word[0] for word in name.split()[:4]).upper()[:4]
                else:
                    name = f"{self.fake.city()} School District"
                    code = self.fake.lexify(text='????').upper()
                
                # Generate Salesforce ID (18 characters)
                salesforce_id = self.fake.lexify(text='?' * 18).upper()
                
                # Check if district already exists
                existing = District.query.filter_by(name=name).first()
                if existing:
                    continue
                
                district = District(
                    name=name,
                    district_code=code,
                    salesforce_id=salesforce_id
                )
                db.session.add(district)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating district {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} districts")
        return District.query.all()
    
    def generate_organizations(self):
        """Generate Organization records."""
        count = self.get_count('organization')
        print(f"  Creating {count} organizations...")
        
        org_types = ["Business", "Non-profit", "Educational", "Government", "Healthcare", "Technology"]
        
        created = 0
        for i in range(count):
            try:
                # Generate Salesforce ID (18 characters)
                salesforce_id = self.fake.lexify(text='?' * 18).upper()
                
                # Check if organization already exists
                existing = Organization.query.filter_by(salesforce_id=salesforce_id).first()
                if existing:
                    continue
                
                org = Organization(
                    name=self.fake.company(),
                    type=random.choice(org_types) if self.mode == 'demo' else (
                        random.choice(org_types) if random.random() > 0.1 else None  # 10% NULL in edge mode
                    ),
                    description=self.fake.text(max_nb_chars=200) if self.mode == 'demo' or random.random() > 0.2 else None,
                    salesforce_id=salesforce_id,
                    billing_street=self.fake.street_address(),
                    billing_city=self.fake.city(),
                    billing_state=self.fake.state_abbr(),
                    billing_postal_code=self.fake.postcode(),
                    billing_country="USA"
                )
                db.session.add(org)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating organization {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} organizations")
        return Organization.query.all()
    
    def generate_schools(self, districts):
        """Generate School records (depends on districts)."""
        if not districts:
            print("    ⚠️  No districts available, skipping schools")
            return []
        
        count = self.get_count('school')
        print(f"  Creating {count} schools...")
        
        school_levels = ["Elementary", "Middle", "High"]
        
        created = 0
        for i in range(count):
            try:
                # Pick a random district
                district = random.choice(districts)
                level = random.choice(school_levels)
                
                # Generate Salesforce ID (18 characters)
                school_id = self.fake.lexify(text='?' * 18).upper()
                
                # Check if school already exists
                existing = School.query.get(school_id)
                if existing:
                    continue
                
                name = f"{self.fake.company()} {level} School"
                
                school = School(
                    id=school_id,
                    name=name,
                    district_id=district.id,
                    level=level,
                    school_code=self.fake.lexify(text='???').upper(),
                    normalized_name=name.lower().replace(" ", "_")
                )
                db.session.add(school)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating school {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} schools")
        return School.query.all()
    
    def generate_classes(self, schools):
        """Generate Class records (depends on schools)."""
        if not schools:
            print("    ⚠️  No schools available, skipping classes")
            return []
        
        count = self.get_count('class')
        print(f"  Creating {count} classes...")
        
        # Generate current academic year (starts in August)
        now = datetime.now()
        if now.month >= 8:
            current_year = now.year
        else:
            current_year = now.year - 1
        
        class_names = [
            "Algebra I", "Geometry", "Biology", "Chemistry", "Physics",
            "English 9", "English 10", "English 11", "English 12",
            "World History", "US History", "Government", "Economics",
            "Art I", "Art II", "Band", "Choir", "PE", "Health"
        ]
        
        created = 0
        for i in range(count):
            try:
                school = random.choice(schools)
                
                # Generate Salesforce ID (18 characters)
                salesforce_id = self.fake.lexify(text='?' * 18).upper()
                
                # Check if class already exists
                existing = Class.query.filter_by(salesforce_id=salesforce_id).first()
                if existing:
                    continue
                
                # Use predefined names or generate
                if i < len(class_names):
                    name = class_names[i]
                else:
                    name = f"{self.fake.word().title()} {random.randint(1, 4)}"
                
                # Class year can be current or previous
                class_year = current_year if random.random() > 0.2 else (current_year - 1)
                
                class_obj = Class(
                    salesforce_id=salesforce_id,
                    name=name,
                    school_salesforce_id=school.id,
                    class_year=class_year
                )
                db.session.add(class_obj)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating class {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} classes")
        return Class.query.all()
    
    def generate_tenants(self):
        """Generate Tenant records."""
        count = self.get_count('tenant')
        if count == 0:
            return []
        
        print(f"  Creating {count} tenants...")
        
        created = 0
        for i in range(count):
            try:
                name = f"{self.fake.city()} School District" if i == 0 else f"{self.fake.company()} District"
                slug = name.lower().replace(" ", "-").replace("'", "")[:50]
                
                # Check if tenant already exists
                existing = Tenant.query.filter_by(slug=slug).first()
                if existing:
                    continue
                
                tenant = Tenant(
                    name=name,
                    slug=slug,
                    active=True
                )
                db.session.add(tenant)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating tenant {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} tenants")
        return Tenant.query.all()
    
    def generate_users(self, tenants=None):
        """Generate User records with all SecurityLevel and TenantRole values."""
        count = self.get_count('user')
        print(f"  Creating {count} users...")
        
        # Distribution: 1 admin, 2 managers, 3 supervisors, rest users
        security_levels = [
            SecurityLevel.ADMIN,
            SecurityLevel.MANAGER, SecurityLevel.MANAGER,
            SecurityLevel.SUPERVISOR, SecurityLevel.SUPERVISOR, SecurityLevel.SUPERVISOR,
        ]
        
        tenant_roles = [TenantRole.ADMIN, TenantRole.COORDINATOR, TenantRole.VIRTUAL_ADMIN, TenantRole.USER]
        
        created = 0
        for i in range(count):
            try:
                # Assign security level
                if i < len(security_levels):
                    security_level = security_levels[i]
                else:
                    security_level = SecurityLevel.USER
                
                # Generate unique username and email
                username = f"{self.fake.user_name()}{i}{random.randint(100, 999)}"
                email = f"{self.fake.email()}"
                
                # Check if user already exists
                existing = User.query.filter(
                    (User.username == username) | (User.email == email)
                ).first()
                if existing:
                    continue
                
                # Assign tenant and role (some users are tenant-scoped)
                tenant_id = None
                tenant_role = None
                if tenants and random.random() < 0.3:  # 30% are tenant-scoped
                    tenant = random.choice(tenants)
                    tenant_id = tenant.id
                    tenant_role = random.choice(tenant_roles)
                
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash("testpass123"),  # Default test password
                    first_name=self.fake.first_name(),
                    last_name=self.fake.last_name(),
                    security_level=security_level,
                    tenant_id=tenant_id,
                    tenant_role=tenant_role
                )
                db.session.add(user)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating user {i}: {e}")
        
        db.session.commit()
        print(f"    ✅ Created {created} users")
        return User.query.all()
    
    def generate_volunteers(self, organizations, skills):
        """Generate Volunteer records (polymorphic Contact)."""
        count = self.get_count('volunteer')
        print(f"  Creating {count} volunteers...")
        
        industries = ["Technology", "Healthcare", "Finance", "Education", "Manufacturing", "Retail", "Legal", "Engineering"]
        titles = ["Software Engineer", "Manager", "Analyst", "Director", "Specialist", "Coordinator", "Consultant", "Executive"]
        
        created = 0
        for i in range(count):
            try:
                # Create Contact base first
                contact = Contact(
                    first_name=self.fake.first_name(),
                    last_name=self.fake.last_name(),
                    gender=random.choice(list(GenderEnum)),
                    birthdate=self.fake.date_of_birth(minimum_age=22, maximum_age=65),
                    education_level=random.choice(list(EducationEnum)),
                    race_ethnicity=random.choice(list(RaceEthnicityEnum)) if self.mode == 'demo' or random.random() > 0.2 else None,
                    age_group=random.choice(list(AgeGroupEnum)),
                    salesforce_individual_id=self.fake.lexify(text='?' * 18).upper() if random.random() > 0.1 else None
                )
                db.session.add(contact)
                db.session.flush()  # Get the ID
                
                # Create Volunteer
                volunteer = Volunteer(
                    id=contact.id,
                    organization_name=random.choice(organizations).name if organizations and random.random() > 0.2 else self.fake.company(),
                    title=random.choice(titles),
                    department=self.fake.word().title() if self.mode == 'demo' or random.random() > 0.3 else None,
                    industry=random.choice(industries),
                    education=random.choice(list(EducationEnum)) if random.random() > 0.1 else None,
                    local_status=random.choice(list(LocalStatusEnum)),
                    status=random.choice(list(VolunteerStatus)),
                    first_volunteer_date=self.fake.date_between(start_date='-2y', end_date='today') if random.random() > 0.1 else None,
                    last_volunteer_date=self.fake.date_between(start_date='-6m', end_date='today') if random.random() > 0.1 else None,
                    times_volunteered=random.randint(0, 50) if self.mode == 'demo' else (random.randint(0, 200) if random.random() > 0.1 else 0),
                    interests=self.fake.text(max_nb_chars=200) if self.mode == 'demo' or random.random() > 0.3 else None
                )
                db.session.add(volunteer)
                
                # Add email
                email = Email(
                    contact_id=contact.id,
                    email=self.fake.email(),
                    type=ContactTypeEnum.personal,
                    primary=True
                )
                db.session.add(email)
                
                # Add phone (80% chance)
                if random.random() > 0.2:
                    phone = Phone(
                        contact_id=contact.id,
                        number=self.fake.phone_number()[:20],  # Limit length
                        type=ContactTypeEnum.personal,
                        primary=True
                    )
                    db.session.add(phone)
                
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating volunteer {i}: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} volunteers")
        return Volunteer.query.all()
    
    def generate_teachers(self, schools):
        """Generate Teacher records (polymorphic Contact)."""
        if not schools:
            print("    ⚠️  No schools available, skipping teachers")
            return []
        
        count = self.get_count('teacher')
        print(f"  Creating {count} teachers...")
        
        departments = ["Mathematics", "Science", "English", "History", "Art", "Physical Education", "Technology", "Counseling"]
        
        created = 0
        for i in range(count):
            try:
                # Create Contact base first
                contact = Contact(
                    first_name=self.fake.first_name(),
                    last_name=self.fake.last_name(),
                    gender=random.choice(list(GenderEnum)),
                    birthdate=self.fake.date_of_birth(minimum_age=25, maximum_age=60),
                    education_level=random.choice(list(EducationEnum)),
                    salesforce_individual_id=self.fake.lexify(text='?' * 18).upper() if random.random() > 0.1 else None
                )
                db.session.add(contact)
                db.session.flush()
                
                # Create Teacher
                school = random.choice(schools)
                teacher = Teacher(
                    id=contact.id,
                    department=random.choice(departments),
                    school_id=school.id,
                    status=random.choice(list(TeacherStatus)),
                    connector_role=random.choice(["Mentor", "Speaker", "Advisor"]) if random.random() < 0.3 else None,
                    connector_active=random.choice([True, False]) if random.random() < 0.3 else False
                )
                db.session.add(teacher)
                
                # Add email
                email = Email(
                    contact_id=contact.id,
                    email=self.fake.email(),
                    type=ContactTypeEnum.professional,
                    primary=True
                )
                db.session.add(email)
                
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating teacher {i}: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} teachers")
        return Teacher.query.all()
    
    def generate_students(self, schools, teachers, classes):
        """Generate Student records (polymorphic Contact)."""
        if not schools:
            print("    ⚠️  No schools available, skipping students")
            return []
        
        count = self.get_count('student')
        print(f"  Creating {count} students...")
        
        created = 0
        for i in range(count):
            try:
                # Create Contact base first
                contact = Contact(
                    first_name=self.fake.first_name(),
                    last_name=self.fake.last_name(),
                    gender=random.choice(list(GenderEnum)),
                    birthdate=self.fake.date_of_birth(minimum_age=6, maximum_age=18),
                    salesforce_individual_id=self.fake.lexify(text='?' * 18).upper() if random.random() > 0.1 else None
                )
                db.session.add(contact)
                db.session.flush()
                
                # Create Student
                school = random.choice(schools)
                grade = random.randint(0, 12)
                
                # Assign class (70% of students have a class)
                class_salesforce_id = None
                if classes and random.random() < 0.7:
                    class_obj = random.choice(classes)
                    class_salesforce_id = class_obj.salesforce_id
                
                student = Student(
                    id=contact.id,
                    current_grade=grade,
                    student_id=f"STU{self.fake.random_number(digits=6)}",
                    school_id=school.id,
                    class_salesforce_id=class_salesforce_id,
                    teacher_id=random.choice(teachers).id if teachers and random.random() > 0.3 else None,
                    racial_ethnic=random.choice(["White", "Black or African American", "Hispanic or Latino", "Asian", "Native American", "Other"]) if self.mode == 'demo' or random.random() > 0.2 else None,
                    school_code=self.fake.lexify(text='???').upper(),
                    ell_language=random.choice(["Spanish", "French", "Arabic", None]),
                    gifted=random.choice([True, False]) if random.random() > 0.1 else None,
                    lunch_status=random.choice(["Free", "Reduced", "Paid"]) if self.mode == 'demo' or random.random() > 0.2 else None,
                    active=True
                )
                db.session.add(student)
                
                # Add email (70% chance for students)
                if random.random() < 0.7:
                    email = Email(
                        contact_id=contact.id,
                        email=self.fake.email(),
                        type=ContactTypeEnum.personal,
                        primary=True
                    )
                    db.session.add(email)
                
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating student {i}: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} students")
        return Student.query.all()
    
    def generate_events(self, districts, schools, teachers, volunteers):
        """Generate Event records with all EventType and EventStatus values."""
        count = self.get_count('event')
        print(f"  Creating {count} events...")
        
        if not schools:
            print("    ⚠️  No schools available, skipping events")
            return []
        
        # Get all enum values
        event_types = list(EventType)
        event_statuses = list(EventStatus)
        event_formats = list(EventFormat)
        cancellation_reasons = list(CancellationReason)
        
        created = 0
        for i in range(count):
            try:
                school = random.choice(schools)
                event_type = random.choice(event_types)
                event_format = random.choice(event_formats)
                event_status = random.choice(event_statuses)
                
                # Generate realistic dates based on status
                now = datetime.now(timezone.utc)
                if event_status in [EventStatus.COMPLETED, EventStatus.CANCELLED]:
                    # Past events
                    start_date = self.fake.date_time_between(start_date='-1y', end_date='-1d', tzinfo=timezone.utc)
                elif event_status == EventStatus.DRAFT:
                    # Can be past or future
                    start_date = self.fake.date_time_between(start_date='-6m', end_date='+6m', tzinfo=timezone.utc)
                else:
                    # Future events
                    start_date = self.fake.date_time_between(start_date='now', end_date='+6m', tzinfo=timezone.utc)
                
                end_date = start_date + timedelta(hours=random.randint(1, 8))
                
                # Generate event
                event = Event(
                    title=self.fake.sentence(nb_words=4).title().rstrip('.'),
                    description=self.fake.text(max_nb_chars=500) if self.mode == 'demo' or random.random() > 0.2 else None,
                    type=event_type,
                    format=event_format,
                    status=event_status,
                    start_date=start_date,
                    end_date=end_date,
                    location=self.fake.address() if event_format == EventFormat.IN_PERSON else "Virtual",
                    school=school.id,
                    capacity=random.randint(10, 100) if self.mode == 'demo' else (random.randint(1, 500) if random.random() > 0.1 else None),
                    salesforce_id=self.fake.lexify(text='?' * 18).upper() if random.random() > 0.1 else None,
                    import_source=random.choice(["seed_data", "manual", "salesforce", "pathful_direct"]) if random.random() > 0.1 else None
                )
                
                # Add cancellation reason if cancelled
                if event_status == EventStatus.CANCELLED:
                    if self.mode == 'edge' and random.random() < 0.3:
                        # Edge case: cancelled without reason
                        event.cancellation_reason = None
                    else:
                        event.cancellation_reason = random.choice(cancellation_reasons)
                
                db.session.add(event)
                db.session.flush()
                
                # Add teacher registration (70% of events have teachers)
                if teachers and random.random() < 0.7:
                    teacher = random.choice(teachers)
                    event_teacher = EventTeacher(
                        event_id=event.id,
                        teacher_id=teacher.id,
                        status=random.choice(["confirmed", "pending", "cancelled"])
                    )
                    db.session.add(event_teacher)
                
                # Add district associations (50% of events)
                if districts and random.random() < 0.5:
                    num_districts = random.randint(1, min(2, len(districts)))
                    event_districts = random.sample(districts, num_districts)
                    for district in event_districts:
                        event.districts.append(district)
                
                # Add volunteer associations (60% of events)
                if volunteers and random.random() < 0.6:
                    num_volunteers = random.randint(1, min(5, len(volunteers)))
                    event_volunteers = random.sample(volunteers, num_volunteers)
                    for volunteer in event_volunteers:
                        event.volunteers.append(volunteer)
                
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating event {i}: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} events")
        return Event.query.all()
    
    def generate_volunteer_skills(self, volunteers, skills):
        """Generate VolunteerSkill relationships (many-to-many)."""
        if not volunteers or not skills:
            return
        
        print(f"  Creating volunteer-skill relationships...")
        
        created = 0
        for volunteer in volunteers:
            try:
                # Each volunteer gets 2-5 skills
                num_skills = random.randint(2, 5) if self.mode == 'demo' else (
                    random.randint(0, 10) if random.random() > 0.1 else 0  # Edge: some with many, some with none
                )
                
                if num_skills > 0:
                    volunteer_skills = random.sample(skills, min(num_skills, len(skills)))
                    for skill in volunteer_skills:
                        # Check if relationship already exists
                        existing = VolunteerSkill.query.filter_by(
                            volunteer_id=volunteer.id,
                            skill_id=skill.id
                        ).first()
                        if not existing:
                            volunteer_skill = VolunteerSkill(
                                volunteer_id=volunteer.id,
                                skill_id=skill.id,
                                source=random.choice(["user_selected", "admin_selected"])
                            )
                            db.session.add(volunteer_skill)
                            created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating volunteer-skill relationship: {e}")
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} volunteer-skill relationships")
    
    def generate_volunteer_organizations(self, volunteers, organizations):
        """Generate VolunteerOrganization relationships (many-to-many)."""
        if not volunteers or not organizations:
            return
        
        print(f"  Creating volunteer-organization relationships...")
        
        titles = ["Software Engineer", "Manager", "Analyst", "Director", "Specialist"]
        created = 0
        for volunteer in volunteers:
            try:
                # Each volunteer gets 1-3 organization associations
                num_orgs = random.randint(1, 3) if self.mode == 'demo' else (
                    random.randint(0, 5) if random.random() > 0.1 else 0  # Edge: some with many, some with none
                )
                
                if num_orgs > 0:
                    volunteer_orgs = random.sample(organizations, min(num_orgs, len(organizations)))
                    for i, org in enumerate(volunteer_orgs):
                        # Check if relationship already exists
                        existing = VolunteerOrganization.query.filter_by(
                            volunteer_id=volunteer.id,
                            organization_id=org.id
                        ).first()
                        if not existing:
                            vol_org = VolunteerOrganization(
                                volunteer_id=volunteer.id,
                                organization_id=org.id,
                                role=random.choice(titles),
                                is_primary=(i == 0)  # First one is primary
                            )
                            db.session.add(vol_org)
                            created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating volunteer-organization relationship: {e}")
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} volunteer-organization relationships")
    
    def generate_event_participations(self, volunteers, events):
        """Generate EventParticipation records."""
        if not volunteers or not events:
            return
        
        print(f"  Creating event participations...")
        
        participation_statuses = ["Attended", "Completed", "Successfully Completed", "No-Show", "Cancelled"]
        participant_types = ["Volunteer", "Presenter"]
        
        created = 0
        # Create participations for some volunteer-event pairs
        for event in events:
            try:
                # Each event gets 1-5 volunteer participations
                num_participations = random.randint(1, 5) if self.mode == 'demo' else (
                    random.randint(0, 10) if random.random() > 0.1 else 0  # Edge: some with many, some with none
                )
                
                if num_participations > 0:
                    event_volunteers = random.sample(volunteers, min(num_participations, len(volunteers)))
                    for volunteer in event_volunteers:
                        # Check if participation already exists
                        existing = EventParticipation.query.filter_by(
                            volunteer_id=volunteer.id,
                            event_id=event.id
                        ).first()
                        if not existing:
                            status = random.choice(participation_statuses)
                            
                            # Calculate delivery hours based on event duration
                            delivery_hours = None
                            if event.start_date and event.end_date:
                                duration_hours = (event.end_date - event.start_date).total_seconds() / 3600
                                if status in ["Attended", "Completed", "Successfully Completed"]:
                                    delivery_hours = max(0.5, duration_hours)
                            
                            participation = EventParticipation(
                                volunteer_id=volunteer.id,
                                event_id=event.id,
                                status=status,
                                delivery_hours=delivery_hours,
                                salesforce_id=self.fake.lexify(text='?' * 18).upper() if random.random() > 0.1 else None,
                                age_group=random.choice(["18-25", "26-35", "36-45", "46-55", "56-65"]) if random.random() > 0.2 else None,
                                email=self.fake.email(),
                                title=volunteer.title if volunteer.title else random.choice(["Software Engineer", "Manager", "Analyst"]),
                                participant_type=random.choice(participant_types) if event.format == EventFormat.VIRTUAL else "Volunteer"
                            )
                            db.session.add(participation)
                            created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating event participation: {e}")
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} event participations")
    
    def generate_engagements(self, volunteers):
        """Generate Engagement records."""
        if not volunteers:
            return
        
        count = self.get_count('engagement')
        print(f"  Creating {count} engagements...")
        
        engagement_types = ["Phone Call", "Email", "Training", "Orientation", "Meeting", "Event Planning", "Follow-up"]
        
        created = 0
        for i in range(count):
            try:
                volunteer = random.choice(volunteers)
                
                engagement = Engagement(
                    volunteer_id=volunteer.id,
                    engagement_date=self.fake.date_between(start_date='-6m', end_date='today'),
                    engagement_type=random.choice(engagement_types),
                    notes=self.fake.text(max_nb_chars=200) if self.mode == 'demo' or random.random() > 0.3 else None
                )
                db.session.add(engagement)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating engagement {i}: {e}")
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} engagements")
    
    def generate_history_records(self, volunteers, events, users):
        """Generate History records."""
        if not volunteers:
            return
        
        count = self.get_count('history')
        print(f"  Creating {count} history records...")
        
        history_types = ["note", "activity", "status_change", "system", "other"]
        activity_types = ["Phone Call", "Email", "Meeting", "Status Update", "Note Added", "System Update"]
        actions = ["created", "updated", "contacted", "status_changed", "note_added"]
        
        created = 0
        for i in range(count):
            try:
                volunteer = random.choice(volunteers)
                event = random.choice(events) if events and random.random() < 0.3 else None
                user = random.choice(users) if users else None
                
                history = History(
                    contact_id=volunteer.id,
                    event_id=event.id if event else None,
                    action=random.choice(actions),
                    summary=self.fake.sentence(nb_words=6),
                    description=self.fake.text(max_nb_chars=300) if self.mode == 'demo' or random.random() > 0.2 else None,
                    activity_type=random.choice(activity_types),
                    activity_date=self.fake.date_time_between(start_date='-6m', end_date='now', tzinfo=timezone.utc),
                    activity_status=random.choice(["completed", "pending", "in_progress"]) if random.random() > 0.1 else None,
                    history_type=random.choice(history_types),
                    created_by_id=user.id if user else None,
                    is_deleted=False
                )
                db.session.add(history)
                created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating history record {i}: {e}")
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} history records")
    
    def generate_event_attendance_details(self, events):
        """Generate EventAttendanceDetail records (one-to-one with events)."""
        if not events:
            return
        
        print(f"  Creating event attendance details...")
        
        created = 0
        # Create attendance details for some events (60% in demo, variable in edge)
        for event in events:
            try:
                # Check if attendance detail already exists
                existing = EventAttendanceDetail.query.filter_by(event_id=event.id).first()
                if existing:
                    continue
                
                # Create attendance detail for some events
                if self.mode == 'demo':
                    should_create = random.random() < 0.6  # 60% of events
                else:
                    should_create = random.random() < 0.8  # 80% in edge mode
                
                if should_create:
                    # Calculate realistic values
                    num_volunteers = len(event.volunteers) if event.volunteers else random.randint(1, 5)
                    total_students = random.randint(10, 50) if self.mode == 'demo' else (
                        random.randint(1, 200) if random.random() > 0.1 else None  # Edge: some with extreme values
                    )
                    
                    students_per_volunteer = None
                    if total_students and num_volunteers > 0:
                        students_per_volunteer = total_students // num_volunteers
                    
                    detail = EventAttendanceDetail(
                        event_id=event.id,
                        num_classrooms=random.randint(1, 5) if self.mode == 'demo' or random.random() > 0.2 else None,
                        rotations=random.randint(1, 4) if self.mode == 'demo' or random.random() > 0.2 else None,
                        students_per_volunteer=students_per_volunteer,
                        total_students=total_students,
                        attendance_in_sf=random.choice([True, False]),
                        pathway=random.choice(["STEM", "Arts", "Business", "Healthcare", None]) if self.mode == 'demo' or random.random() > 0.2 else None,
                        groups_rotations=self.fake.text(max_nb_chars=100) if self.mode == 'demo' or random.random() > 0.3 else None,
                        is_stem=random.choice([True, False]) if random.random() > 0.1 else None,
                        attendance_link=self.fake.url() if random.random() < 0.3 else None
                    )
                    db.session.add(detail)
                    created += 1
            except Exception as e:
                print(f"    ⚠️  Error creating attendance detail: {e}")
                continue
        
        db.session.commit()
        print(f"    ✅ Created {created} event attendance details")
    
    def print_summary(self):
        """Print summary of generated data."""
        print()
        print("=" * 60)
        print("📊 GENERATION SUMMARY")
        print("=" * 60)
        
        try:
            counts = {
                "Skills": Skill.query.count(),
                "Districts": District.query.count(),
                "Organizations": Organization.query.count(),
                "Schools": School.query.count(),
                "Classes": Class.query.count(),
                "Tenants": Tenant.query.count() if Tenant.query.count() > 0 else None,
                "Users": User.query.count(),
                "Volunteers": Volunteer.query.count(),
                "Teachers": Teacher.query.count(),
                "Students": Student.query.count(),
                "Events": Event.query.count(),
                "VolunteerSkills": VolunteerSkill.query.count(),
                "VolunteerOrganizations": VolunteerOrganization.query.count(),
                "EventParticipations": EventParticipation.query.count(),
                "Engagements": Engagement.query.count(),
                "History": History.query.count(),
                "EventAttendanceDetails": EventAttendanceDetail.query.count(),
            }
            
            # Remove None values
            counts = {k: v for k, v in counts.items() if v is not None}
            
            print(f"Seed: {self.seed}")
            print(f"Size: {self.size}")
            print(f"Mode: {self.mode}")
            print()
            print("Records created:")
            for model, count in sorted(counts.items()):
                print(f"  {model:25}: {count:4}")
            
            print("=" * 60)
            print("✅ Generation complete!")
            
        except Exception as e:
            print(f"⚠️  Error generating summary: {e}")
    
    def generate(self):
        """Main generation method."""
        print(f"🌱 Starting synthetic data generation")
        print(f"   Seed: {self.seed}")
        print(f"   Size: {self.size}")
        print(f"   Mode: {self.mode}")
        print()
        
        app = create_app()
        with app.app_context():
            try:
                # Generate independent models first
                skills = self.generate_skills()
                districts = self.generate_districts()
                organizations = self.generate_organizations()
                tenants = self.generate_tenants()
                
                # Generate dependent models
                schools = self.generate_schools(districts)
                classes = self.generate_classes(schools)
                users = self.generate_users(tenants)
                
                # Generate Contact hierarchy (polymorphic)
                volunteers = self.generate_volunteers(organizations, skills)
                teachers = self.generate_teachers(schools)
                students = self.generate_students(schools, teachers, classes)
                
                # Generate Events
                events = self.generate_events(districts, schools, teachers, volunteers)
                
                # Generate many-to-many relationships
                self.generate_volunteer_skills(volunteers, skills)
                self.generate_volunteer_organizations(volunteers, organizations)
                
                # Generate participation and activity tracking
                self.generate_event_participations(volunteers, events)
                self.generate_engagements(volunteers)
                self.generate_history_records(volunteers, events, users)
                self.generate_event_attendance_details(events)
                
                # Print summary
                self.print_summary()
            except Exception as e:
                print(f"❌ Error during generation: {e}")
                db.session.rollback()
                raise


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate synthetic data for VMS testing and demos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for deterministic generation (default: random)'
    )
    
    parser.add_argument(
        '--size',
        choices=['small', 'medium', 'large'],
        default='medium',
        help='Dataset size preset (default: medium)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['demo', 'edge'],
        default='demo',
        help='Generation mode: demo (happy path) or edge (boundary conditions)'
    )
    
    parser.add_argument(
        '--counts',
        action='append',
        help='Custom model counts (e.g., --counts volunteer=100 event=50). Can be used multiple times.'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Clear existing data before generating (USE WITH CAUTION)'
    )
    
    return parser.parse_args()


def parse_counts(counts_args):
    """Parse --counts arguments into a dictionary."""
    counts = {}
    if counts_args:
        for arg in counts_args:
            try:
                model, count = arg.split('=')
                counts[model] = int(count)
            except ValueError:
                print(f"WARNING: Invalid count format '{arg}'. Expected 'model=count'")
    return counts


def main():
    """Main entry point."""
    args = parse_args()
    
    # Parse custom counts
    counts = parse_counts(args.counts)
    
    # Create generator
    generator = SyntheticDataGenerator(
        seed=args.seed,
        size=args.size,
        mode=args.mode,
        counts=counts
    )
    
    # Handle reset
    if args.reset:
        confirm = input("⚠️  This will delete existing data. Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
        
        app = create_app()
        with app.app_context():
            print("Clearing existing data...")
            try:
                # Delete in reverse dependency order (children first, then parents)
                from models.volunteer import VolunteerSkill
                from models.organization import VolunteerOrganization
                
                # Delete relationship tables first
                EventAttendanceDetail.query.delete()
                EventParticipation.query.delete()
                History.query.delete()
                Engagement.query.delete()
                VolunteerSkill.query.delete()
                VolunteerOrganization.query.delete()
                EventTeacher.query.delete()
                
                # Delete main entities
                Event.query.delete()
                Student.query.delete()
                Teacher.query.delete()
                Volunteer.query.delete()
                Contact.query.delete()  # Parent of Volunteer/Teacher/Student
                Class.query.delete()
                School.query.delete()
                User.query.delete()
                Organization.query.delete()
                District.query.delete()
                Skill.query.delete()
                
                db.session.commit()
                print("✅ Data cleared")
            except Exception as e:
                print(f"❌ Error clearing data: {e}")
                db.session.rollback()
                return
    
    # Generate data
    generator.generate()


if __name__ == '__main__':
    main()


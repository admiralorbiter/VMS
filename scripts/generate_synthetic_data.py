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
from models.volunteer import Skill
from models.district_model import District
from models.organization import Organization
from models.school_model import School
from models.user import User, SecurityLevel, TenantRole
from models.tenant import Tenant
from werkzeug.security import generate_password_hash


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
                'teacher': 10,
                'volunteer': 15,
                'student': 20,
                'event': 10,
            },
            'medium': {
                'district': 5,
                'school': 15,
                'teacher': 30,
                'volunteer': 50,
                'student': 100,
                'event': 30,
            },
            'large': {
                'district': 10,
                'school': 50,
                'teacher': 100,
                'volunteer': 200,
                'student': 500,
                'event': 100,
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
                users = self.generate_users(tenants)
                
                # TODO: Add more model generation
                
                print()
                print("✅ Generation complete!")
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
                # Delete in reverse dependency order
                from models.volunteer import VolunteerSkill
                from models.organization import VolunteerOrganization
                
                VolunteerSkill.query.delete()
                VolunteerOrganization.query.delete()
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


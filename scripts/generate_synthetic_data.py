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


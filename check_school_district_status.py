#!/usr/bin/env python3
"""Check the status of School and District entities in the validation system."""

from app import app
from models import db
from models.validation.result import ValidationResult


def check_entity_status():
    """Check the current status of School and District entities."""
    with app.app_context():
        print("=== School and District Entity Status ===")

        # Check validation results
        school_results = ValidationResult.query.filter_by(entity_type="school").count()
        district_results = ValidationResult.query.filter_by(
            entity_type="district"
        ).count()

        print(f"School validation results: {school_results}")
        print(f"District validation results: {district_results}")

        # Check total validation results
        total_results = ValidationResult.query.count()
        print(f"\nTotal validation results in system: {total_results}")

        # Count by entity type
        from sqlalchemy import func

        entity_counts = (
            db.session.query(
                ValidationResult.entity_type, func.count(ValidationResult.id)
            )
            .group_by(ValidationResult.entity_type)
            .all()
        )

        print("\nEntity type counts:")
        for entity_type, count in entity_counts:
            print(f"  {entity_type}: {count}")

        print("\n=== End Status Check ===")


if __name__ == "__main__":
    check_entity_status()

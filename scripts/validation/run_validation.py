#!/usr/bin/env python3
"""
CLI script for running Salesforce data validations.

This script provides a command-line interface for executing various types
of data validation between VMS and Salesforce.
"""

import argparse
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables from .env file FIRST, before any other imports
load_dotenv()

# Add the project root to the Python path (scripts/validation is 2 levels deep)
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def run_fast_validation(user_id: int = None):
    """Run fast validation checks."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine

        logger.info("Starting fast validation...")

        with app.app_context():
            engine = get_validation_engine()
            run = engine.run_fast_validation(user_id=user_id)

            logger.info(f"Fast validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Fast validation failed: {e}")
        raise


def run_slow_validation(user_id: int = None):
    """Run slow validation checks."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine

        logger.info("Starting slow validation...")

        with app.app_context():
            engine = get_validation_engine()
            run = engine.run_slow_validation(user_id=user_id)

            logger.info(f"Slow validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Slow validation failed: {e}")
        raise


def run_count_validation(entity_type: str = "all", user_id: int = None):
    """Run count validation for specific entity type."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine
        from utils.validators.count_validator import CountValidator

        logger.info(f"Starting count validation for {entity_type}...")

        with app.app_context():
            # Create validator
            validator = CountValidator(run_id=None, entity_type=entity_type)

            # Run validation
            engine = get_validation_engine()
            run = engine.run_custom_validation(
                validators=[validator],
                run_type="count",
                name=f"Count Validation - {entity_type.title()}",
                user_id=user_id,
            )

            logger.info(f"Count validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")

            return run

    except Exception as e:
        logger.error(f"Count validation failed: {e}")
        raise


def run_field_completeness_validation(entity_type: str = "all", user_id: int = None):
    """Run field completeness validation for specific entity type."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine
        from utils.validators.field_completeness_validator import (
            FieldCompletenessValidator,
        )

        logger.info(f"Starting field completeness validation for {entity_type}...")

        with app.app_context():
            # Create validator
            validator = FieldCompletenessValidator(run_id=None, entity_type=entity_type)

            # Run validation
            engine = get_validation_engine()
            run = engine.run_custom_validation(
                validators=[validator],
                run_type="field_completeness",
                name=f"Field Completeness Validation - {entity_type.title()}",
                user_id=user_id,
            )

            logger.info(f"Field completeness validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Field completeness validation failed: {e}")
        raise


def run_data_type_validation(entity_type: str = "all", user_id: int = None):
    """Run data type validation for specific entity type."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine
        from utils.validators.data_type_validator import DataTypeValidator

        logger.info(f"Starting data type validation for {entity_type}...")

        with app.app_context():
            # Create validator
            validator = DataTypeValidator(run_id=None, entity_type=entity_type)

            # Run validation
            engine = get_validation_engine()
            run = engine.run_custom_validation(
                validators=[validator],
                run_type="data_type_validation",
                name=f"Data Type Validation - {entity_type.title()}",
                user_id=user_id,
            )

            logger.info(f"Data type validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Data type validation failed: {e}")
        raise


def run_relationship_validation(entity_type: str = "all", user_id: int = None):
    """Run relationship integrity validation for specific entity type."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine
        from utils.validators.relationship_validator import RelationshipValidator

        logger.info(f"Starting relationship validation for {entity_type}...")

        with app.app_context():
            # Create validator
            validator = RelationshipValidator(run_id=None, entity_type=entity_type)

            # Run validation
            engine = get_validation_engine()
            run = engine.run_custom_validation(
                validators=[validator],
                run_type="relationship_validation",
                name=f"Relationship Validation - {entity_type.title()}",
                user_id=user_id,
            )

            logger.info(f"Relationship validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Relationship validation failed: {e}")
        raise


def run_business_rule_validation(entity_type: str = "all", user_id: int = None):
    """Run business rule validation for specific entity type."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine
        from utils.validators.business_rule_validator import BusinessRuleValidator

        logger.info(f"Starting business rule validation for {entity_type}...")

        with app.app_context():
            # Create validator
            validator = BusinessRuleValidator(run_id=None, entity_type=entity_type)

            # Run validation
            engine = get_validation_engine()
            run = engine.run_custom_validation(
                validators=[validator],
                run_type="business_rule_validation",
                name=f"Business Rule Validation - {entity_type.title()}",
                user_id=user_id,
            )

            logger.info(f"Business rule validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Business rule validation failed: {e}")
        raise


def run_comprehensive_validation(entity_type: str = "all", user_id: int = None):
    """Run comprehensive validation for all validation types on specified entity."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine

        logger.info(f"Starting comprehensive validation for {entity_type}...")

        with app.app_context():
            # Run comprehensive validation (all validation types)
            engine = get_validation_engine()
            run = engine.run_comprehensive_validation(
                entity_type=entity_type,
                run_type="comprehensive",
                name=f"Comprehensive Validation - {entity_type.title()}",
                user_id=user_id,
            )

            logger.info(f"Comprehensive validation completed successfully!")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Results: {run.total_checks} total checks")
            logger.info(f"Execution time: {run.execution_time_seconds}s")

            return run

    except Exception as e:
        logger.error(f"Comprehensive validation failed: {e}")
        raise


def show_run_status(run_id: int):
    """Show status of a validation run."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine

        with app.app_context():
            engine = get_validation_engine()
            run_data = engine.get_run_status(run_id)

            if not run_data:
                logger.error(f"Run {run_id} not found")
                return

            logger.info(f"Run {run_id} Status:")
            logger.info(f"  Type: {run_data.get('run_type')}")
            logger.info(f"  Name: {run_data.get('name')}")
            logger.info(f"  Status: {run_data.get('status')}")
            logger.info(f"  Started: {run_data.get('started_at')}")
            logger.info(f"  Completed: {run_data.get('completed_at')}")
            logger.info(f"  Progress: {run_data.get('progress_percentage')}%")
            logger.info(f"  Total Checks: {run_data.get('total_checks')}")
            logger.info(f"  Passed: {run_data.get('passed_checks')}")
            logger.info(f"  Warnings: {run_data.get('warnings')}")
            logger.info(f"  Errors: {run_data.get('errors')}")
            logger.info(f"  Critical: {run_data.get('critical_issues')}")

            if run_data.get("execution_time_seconds"):
                logger.info(
                    f"  Execution Time: {run_data.get('execution_time_seconds')}s"
                )

            if run_data.get("memory_usage_mb"):
                logger.info(f"  Memory Usage: {run_data.get('memory_usage_mb')} MB")

    except Exception as e:
        logger.error(f"Failed to get run status: {e}")


def show_recent_runs(limit: int = 10, run_type: str = None):
    """Show recent validation runs."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine

        with app.app_context():
            engine = get_validation_engine()
            runs = engine.get_recent_runs(limit=limit, run_type=run_type)

            if not runs:
                logger.info("No validation runs found")
                return

            logger.info(f"Recent Validation Runs (limit: {limit}):")
            logger.info("-" * 80)

            for run in runs:
                logger.info(f"Run {run['id']}: {run['name']}")
                logger.info(
                    f"  Results: {run['total_checks']} checks, "
                    f"{run['passed_checks']} passed, "
                    f"{run['warnings']} warnings, "
                    f"{run['errors']} errors, "
                    f"{run['critical_issues']} critical"
                )
                logger.info("-" * 80)

    except Exception as e:
        logger.error(f"Failed to get recent runs: {e}")


def show_run_results(run_id: int, severity: str = None, entity_type: str = None):
    """Show results for a validation run."""
    try:
        # Import and set up Flask app context
        from app import app
        from utils.validation_engine import get_validation_engine

        with app.app_context():
            engine = get_validation_engine()
            results = engine.get_run_results(
                run_id, severity=severity, entity_type=entity_type
            )

            if not results:
                logger.info(f"No results found for run {run_id}")
                return

            logger.info(f"Results for Run {run_id}:")
            if severity:
                logger.info(f"  Severity filter: {severity}")
            if entity_type:
                logger.info(f"  Entity type filter: {entity_type}")
            logger.info("-" * 80)

            for result in results:
                logger.info(
                    f"[{result['severity'].upper()}] {result['entity_type']}: {result['message']}"
                )
                if result.get("field_name"):
                    logger.info(f"  Field: {result['field_name']}")
                if result.get("expected_value") and result.get("actual_value"):
                    logger.info(
                        f"  Expected: {result['expected_value']}, Actual: {result['actual_value']}"
                    )
                logger.info("-" * 40)

    except Exception as e:
        logger.error(f"Failed to get run results: {e}")


def clear_validation_data(
    older_than_days: int = None, entity_type: str = None, user_id: int = None
):
    """Clear old validation data from the database."""
    try:
        # Import and set up Flask app context
        from datetime import datetime, timedelta

        from app import app, db
        from models.validation.history import ValidationHistory
        from models.validation.metric import ValidationMetric
        from models.validation.result import ValidationResult
        from models.validation.run import ValidationRun

        logger.info("Starting validation data cleanup...")

        with app.app_context():
            # Build query filters for ValidationRun (only by date and user)
            run_filters = []

            if older_than_days:
                cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
                run_filters.append(ValidationRun.started_at < cutoff_date)
                logger.info(
                    f"Clearing data older than {older_than_days} days (before {cutoff_date})"
                )

            if user_id:
                run_filters.append(ValidationRun.created_by == user_id)
                logger.info(f"Clearing data for user ID: {user_id}")

            # Get run IDs that match the basic filters
            base_run_ids = [
                run.id for run in ValidationRun.query.filter(*run_filters).all()
            ]

            # If entity_type is specified, filter by ValidationResult.entity_type
            if entity_type and entity_type != "all":
                # Get run IDs that have results for the specified entity_type
                entity_run_ids = [
                    result.run_id
                    for result in ValidationResult.query.filter_by(
                        entity_type=entity_type
                    ).all()
                    if result.run_id in base_run_ids
                ]
                run_ids = entity_run_ids
                logger.info(f"Clearing data for entity type: {entity_type}")
            else:
                run_ids = base_run_ids

            # Count records to be deleted
            runs_to_delete = len(run_ids)

            if run_ids:
                results_to_delete = ValidationResult.query.filter(
                    ValidationResult.run_id.in_(run_ids)
                ).count()
                history_to_delete = ValidationHistory.query.filter(
                    ValidationHistory.run_id.in_(run_ids)
                ).count()
                metrics_to_delete = ValidationMetric.query.filter(
                    ValidationMetric.run_id.in_(run_ids)
                ).count()
            else:
                results_to_delete = 0
                history_to_delete = 0
                metrics_to_delete = 0

            logger.info(f"Records to be deleted:")
            logger.info(f"  - Validation Runs: {runs_to_delete}")
            logger.info(f"  - Validation Results: {results_to_delete}")
            logger.info(f"  - Validation History: {history_to_delete}")
            logger.info(f"  - Validation Metrics: {metrics_to_delete}")

            if runs_to_delete == 0:
                logger.info("No old validation data found to clear.")
                return

            # Delete in correct order (respecting foreign keys)
            if results_to_delete > 0:
                ValidationResult.query.filter(
                    ValidationResult.run_id.in_(run_ids)
                ).delete(synchronize_session=False)
                logger.info(f"Deleted {results_to_delete} validation results")

            if history_to_delete > 0:
                ValidationHistory.query.filter(
                    ValidationHistory.run_id.in_(run_ids)
                ).delete(synchronize_session=False)
                logger.info(f"Deleted {history_to_delete} validation history records")

            if metrics_to_delete > 0:
                ValidationMetric.query.filter(
                    ValidationMetric.run_id.in_(run_ids)
                ).delete(synchronize_session=False)
                logger.info(f"Deleted {metrics_to_delete} validation metrics")

            if runs_to_delete > 0:
                ValidationRun.query.filter(ValidationRun.id.in_(run_ids)).delete(
                    synchronize_session=False
                )
                logger.info(f"Deleted {runs_to_delete} validation runs")

            # Commit the changes
            db.session.commit()

            logger.info("Validation data cleanup completed successfully!")
            logger.info(
                f"Total records deleted: {runs_to_delete + results_to_delete + history_to_delete + metrics_to_delete}"
            )

    except Exception as e:
        logger.error(f"Validation data cleanup failed: {e}")
        raise


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Salesforce Data Validation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run fast validation
  python run_validation.py fast

  # Run slow validation
  python run_validation.py slow

  # Run count validation for volunteers
  python run_validation.py count --entity-type volunteer

  # Run field completeness validation for volunteers
  python run_validation.py field-completeness --entity-type volunteer

  # Run data type validation for volunteers
  python run_validation.py data-type --entity-type volunteer

  # Show status of a specific run
  python run_validation.py status --run-id 123

  # Show recent runs
  python run_validation.py recent --limit 5

  # Show results for a run
  python run_validation.py results --run-id 123
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Fast validation command
    fast_parser = subparsers.add_parser("fast", help="Run fast validation")
    fast_parser.add_argument(
        "--user-id", type=int, help="User ID initiating validation"
    )

    # Slow validation command
    slow_parser = subparsers.add_parser("slow", help="Run slow validation")
    slow_parser.add_argument(
        "--user-id", type=int, help="User ID initiating validation"
    )

    # Count validation command
    count_parser = subparsers.add_parser("count", help="Run count validation")
    count_parser.add_argument(
        "--entity-type",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        default="all",
        help="Entity type to validate",
    )
    count_parser.add_argument(
        "--user-id", type=int, help="User ID initiating validation"
    )

    # Field completeness validation command
    field_completeness_parser = subparsers.add_parser(
        "field-completeness", help="Run field completeness validation"
    )
    field_completeness_parser.add_argument(
        "--entity-type",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        default="all",
        help="Entity type to validate",
    )
    field_completeness_parser.add_argument(
        "--user-id", type=int, help="User ID initiating validation"
    )

    # Data type validation command
    data_type_parser = subparsers.add_parser(
        "data-type", help="Run data type validation"
    )
    data_type_parser.add_argument(
        "--entity-type",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        default="all",
        help="Entity type to validate",
    )
    data_type_parser.add_argument(
        "--user-id", type=int, help="User ID initiating validation"
    )

    # Relationship validation command
    relationship_parser = subparsers.add_parser(
        "relationships", help="Run relationship integrity validation"
    )
    relationship_parser.add_argument(
        "--entity-type",
        default="all",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        help="Entity type to validate (default: all)",
    )
    relationship_parser.add_argument(
        "--user-id", type=int, help="User ID for the validation run"
    )

    # Business rules validation command
    business_rules_parser = subparsers.add_parser(
        "business-rules", help="Run business rule validation"
    )
    business_rules_parser.add_argument(
        "--entity-type",
        default="all",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        help="Entity type to validate (default: all)",
    )
    business_rules_parser.add_argument(
        "--user-id", type=int, help="User ID for the validation run"
    )

    # Comprehensive validation command
    comprehensive_parser = subparsers.add_parser(
        "comprehensive", help="Run comprehensive validation (all validation types)"
    )
    comprehensive_parser.add_argument(
        "--entity-type",
        default="all",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        help="Entity type to validate (default: all)",
    )
    comprehensive_parser.add_argument(
        "--user-id", type=int, help="User ID for the validation run"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show validation run status")
    status_parser.add_argument(
        "--run-id", type=int, required=True, help="Validation run ID"
    )

    # Recent runs command
    recent_parser = subparsers.add_parser("recent", help="Show recent validation runs")
    recent_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of runs to show"
    )
    recent_parser.add_argument(
        "--run-type",
        choices=["fast", "slow", "realtime", "custom"],
        help="Filter by run type",
    )

    # Results command
    results_parser = subparsers.add_parser(
        "results", help="Show validation run results"
    )
    results_parser.add_argument(
        "--run-id", type=int, required=True, help="Validation run ID"
    )
    results_parser.add_argument(
        "--severity",
        choices=["info", "warning", "error", "critical"],
        help="Filter by severity",
    )
    results_parser.add_argument("--entity-type", help="Filter by entity type")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear old validation data")
    clear_parser.add_argument(
        "--older-than-days", type=int, help="Number of days ago to keep data"
    )
    clear_parser.add_argument(
        "--entity-type",
        choices=[
            "all",
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
            "school",
            "district",
        ],
        help="Entity type to filter by (optional)",
    )
    clear_parser.add_argument(
        "--user-id", type=int, help="User ID to filter by (optional)"
    )

    args = parser.parse_args()

    # Help command
    if args.command == "help" or len(sys.argv) == 1:
        print("Salesforce Data Validation System")
        print("=" * 40)
        print()
        print("Available commands:")
        print("  fast          - Run fast validation (record counts only)")
        print("  slow          - Run comprehensive validation")
        print("  count         - Run count validation for specific entity")
        print("  field-completeness - Run field completeness validation")
        print("  data-type     - Run data type validation")
        print("  relationships - Run relationship integrity validation")
        print("  business-rules - Run business rule validation")
        print("  comprehensive - Run comprehensive validation (all types)")
        print("  status        - Show validation run status")
        print("  results       - Show validation results")
        print("  clear         - Clear old validation data")
        print("  help          - Show this help message")
        print()
        print("Examples:")
        print("  python run_validation.py fast")
        print("  python run_validation.py slow")
        print("  python run_validation.py count --entity-type volunteer")
        print(
            "  python run_validation.py field-completeness --entity-type organization"
        )
        print("  python run_validation.py data-type --entity-type student")
        print("  python run_validation.py relationships --entity-type volunteer")
        print("  python run_validation.py business-rules --entity-type volunteer")
        print("  python run_validation.py comprehensive --entity-type volunteer")
        print("  python run_validation.py status --run-id 123")
        print("  python run_validation.py results --run-id 123")
        print("  python run_validation.py clear --older-than-days 30")
        print("  python run_validation.py clear --entity-type volunteer")
        print()
        print("For detailed help on a specific command:")
        print("  python run_validation.py <command> --help")
        return

    try:
        if args.command == "fast":
            run_fast_validation(args.user_id)
        elif args.command == "slow":
            run_slow_validation(args.user_id)
        elif args.command == "count":
            run_count_validation(args.entity_type, args.user_id)
        elif args.command == "field-completeness":
            run_field_completeness_validation(args.entity_type, args.user_id)
        elif args.command == "data-type":
            run_data_type_validation(args.entity_type, args.user_id)
        elif args.command == "relationships":
            run_relationship_validation(args.entity_type, args.user_id)
        elif args.command == "business-rules":
            run_business_rule_validation(args.entity_type, args.user_id)
        elif args.command == "comprehensive":
            run_comprehensive_validation(args.entity_type, args.user_id)
        elif args.command == "status":
            show_run_status(args.run_id)
        elif args.command == "recent":
            show_recent_runs(args.limit, args.run_type)
        elif args.command == "results":
            show_run_results(args.run_id, args.severity, args.entity_type)
        elif args.command == "clear":
            clear_validation_data(args.older_than_days, args.entity_type, args.user_id)
        else:
            logger.error(f"Unknown command: {args.command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

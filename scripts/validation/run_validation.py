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
        choices=["all", "volunteer", "organization", "event", "student", "teacher"],
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
        choices=["all", "volunteer", "organization", "event", "student", "teacher"],
        default="all",
        help="Entity type to validate",
    )
    field_completeness_parser.add_argument(
        "--user-id", type=int, help="User ID initiating validation"
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
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
        elif args.command == "status":
            show_run_status(args.run_id)
        elif args.command == "recent":
            show_recent_runs(args.limit, args.run_type)
        elif args.command == "results":
            show_run_results(args.run_id, args.severity, args.entity_type)
        else:
            logger.error(f"Unknown command: {args.command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

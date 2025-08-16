#!/usr/bin/env python3
"""
Data Population Script for Phase 3.4 Features

This script generates test data to populate the new historical tracking
and aggregation features.
"""

import logging
import os
import random
import sys
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import app
from models import db
from models.validation import (
    ValidationHistory,
    ValidationMetric,
    ValidationResult,
    ValidationRun,
)
from utils.services.history_service import ValidationHistoryService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_validation_runs():
    """Create test validation runs with metrics."""

    with app.app_context():
        try:
            logger.info("🔄 Creating test validation runs...")

            # Create multiple validation runs over the past 30 days
            for i in range(30):
                run_date = datetime.utcnow() - timedelta(days=i)

                # Create validation run
                run = ValidationRun(
                    run_type="business_rule_validation",
                    name=f'Test Run {i+1} - {run_date.strftime("%Y-%m-%d")}',
                    status="completed",
                    started_at=run_date,
                    completed_at=run_date + timedelta(minutes=5),
                    execution_time_seconds=300,
                    memory_usage_mb=random.uniform(50, 150),
                    cpu_usage_percent=random.uniform(20, 80),
                )

                db.session.add(run)
                db.session.flush()  # Get the run ID

                # Create validation results
                create_test_results(run.id, run_date)

                # Create validation metrics
                create_test_metrics(run.id, run_date)

                logger.info(
                    f"✅ Created test run {i+1} for {run_date.strftime('%Y-%m-%d')}"
                )

            db.session.commit()
            logger.info("🎉 All test validation runs created successfully!")

        except Exception as e:
            logger.error(f"❌ Error creating test runs: {e}")
            db.session.rollback()
            raise


def create_test_results(run_id, run_date):
    """Create test validation results."""

    entity_types = [
        "volunteer",
        "organization",
        "event",
        "student",
        "teacher",
        "school",
        "district",
    ]
    validation_types = ["business_rules", "field_completeness", "data_types"]
    severities = ["info", "warning", "error", "critical"]

    for entity_type in entity_types:
        for validation_type in validation_types:
            # Create 5-15 results per entity/type combination
            num_results = random.randint(5, 15)

            for j in range(num_results):
                result = ValidationResult(
                    run_id=run_id,
                    entity_type=entity_type,
                    validation_type=validation_type,
                    field_name=f"test_field_{j}",
                    severity=random.choice(severities),
                    message=f"Test validation message {j}",
                    expected_value=f"expected_{j}",
                    actual_value=f"actual_{j}",
                    metadata={"test": True, "iteration": j},
                )

                db.session.add(result)


def create_test_metrics(run_id, run_date):
    """Create test validation metrics."""

    metric_names = [
        "field_completeness",
        "data_type_accuracy",
        "business_rule_compliance",
        "quality_score",
        "execution_time",
        "memory_usage",
    ]

    entity_types = [
        "volunteer",
        "organization",
        "event",
        "student",
        "teacher",
        "school",
        "district",
        "all",
    ]

    for metric_name in metric_names:
        for entity_type in entity_types:
            # Create metric with realistic values
            if metric_name == "field_completeness":
                value = random.uniform(70, 100)  # 70-100%
                unit = "percentage"
            elif metric_name == "data_type_accuracy":
                value = random.uniform(85, 100)  # 85-100%
                unit = "percentage"
            elif metric_name == "business_rule_compliance":
                value = random.uniform(80, 95)  # 80-95%
                unit = "percentage"
            elif metric_name == "quality_score":
                value = random.uniform(65, 90)  # 65-90%
                unit = "percentage"
            elif metric_name == "execution_time":
                value = random.uniform(100, 500)  # 100-500 seconds
                unit = "seconds"
            elif metric_name == "memory_usage":
                value = random.uniform(50, 200)  # 50-200 MB
                unit = "mb"

            # Add some trend variation (improving over time)
            days_ago = (datetime.utcnow() - run_date).days
            trend_factor = 1 + (days_ago * 0.01)  # Slight improvement over time
            value = min(100, value * trend_factor) if unit == "percentage" else value

            metric = ValidationMetric(
                run_id=run_id,
                metric_name=metric_name,
                metric_value=value,
                metric_category="quality" if "percentage" in unit else "performance",
                metric_unit=unit,
                entity_type=entity_type,
                timestamp=run_date,
                metric_date=run_date,
            )

            db.session.add(metric)


def populate_historical_data():
    """Populate historical data from the test runs."""

    with app.app_context():
        try:
            logger.info("📊 Populating historical data...")

            history_service = ValidationHistoryService()

            # Create history from recent runs (last 30 days)
            total_created = history_service.populate_history_from_recent_runs(days=30)

            logger.info(f"✅ Created {total_created} historical records")

        except Exception as e:
            logger.error(f"❌ Error populating historical data: {e}")
            raise


def verify_data_population():
    """Verify that data was populated correctly."""

    with app.app_context():
        try:
            logger.info("🔍 Verifying data population...")

            # Check validation runs
            total_runs = ValidationRun.query.count()
            logger.info(f"   Total validation runs: {total_runs}")

            # Check validation results
            total_results = ValidationResult.query.count()
            logger.info(f"   Total validation results: {total_results}")

            # Check validation metrics
            total_metrics = ValidationMetric.query.count()
            logger.info(f"   Total validation metrics: {total_metrics}")

            # Check historical records
            total_history = ValidationHistory.query.count()
            logger.info(f"   Total historical records: {total_history}")

            # Check data distribution
            entity_counts = (
                db.session.query(
                    ValidationHistory.entity_type, db.func.count(ValidationHistory.id)
                )
                .group_by(ValidationHistory.entity_type)
                .all()
            )

            logger.info("   Historical records by entity type:")
            for entity_type, count in entity_counts:
                logger.info(f"     {entity_type}: {count}")

            logger.info("✅ Data population verification complete!")

        except Exception as e:
            logger.error(f"❌ Error verifying data: {e}")
            raise


def main():
    """Main data population process."""

    logger.info("🚀 Starting Phase 3.4 data population...")

    try:
        # Step 1: Create test validation runs
        create_test_validation_runs()

        # Step 2: Populate historical data
        populate_historical_data()

        # Step 3: Verify data population
        verify_data_population()

        logger.info("🎉 Phase 3.4 data population completed successfully!")
        logger.info("\n📋 Next steps:")
        logger.info(
            "   1. Test the aggregation service: python scripts/validation/test_aggregation_service.py"
        )
        logger.info(
            "   2. Test the history service: python scripts/validation/test_history_service.py"
        )
        logger.info(
            "   3. Explore the data using the user guide: docs/PHASE_3_4_USER_GUIDE.md"
        )

    except Exception as e:
        logger.error(f"❌ Data population failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

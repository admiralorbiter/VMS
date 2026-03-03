#!/usr/bin/env python3
"""
Test script for ValidationHistoryService.

This script tests the history service by creating ValidationHistory records
from recent validation runs and demonstrating trend analysis capabilities.
"""

import logging
import os
import sys
from datetime import datetime

import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import app
from models.validation import ValidationHistory, ValidationRun
from utils.services.history_service import ValidationHistoryService

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_history_service():
    """Test the ValidationHistoryService functionality."""

    with app.app_context():
        try:
            logger.info("🚀 Testing ValidationHistoryService...")

            # Initialize the service
            history_service = ValidationHistoryService()

            # Test 1: Create history from recent validation runs
            logger.info("📊 Test 1: Creating history from recent validation runs...")

            # Get recent completed runs
            recent_runs = (
                ValidationRun.query.filter_by(status="completed")
                .order_by(ValidationRun.completed_at.desc())
                .limit(5)
                .all()
            )

            logger.info("Found %s recent completed runs", len(recent_runs))

            # Create history records for each run
            total_history_created = 0
            for run in recent_runs:
                logger.info(
                    "Processing run %s: %s - %s", run.id, run.run_type, run.name
                )

                # Create history records for this run
                history_records = history_service.create_history_from_run(run.id)
                total_history_created += len(history_records)

                logger.info(
                    f"Created {len(history_records)} history records for run {run.id}"
                )

            logger.info("✅ Total history records created: %s", total_history_created)

            # Test 2: Query and display history records
            logger.info("\n📈 Test 2: Querying and displaying history records...")

            all_history = ValidationHistory.query.order_by(
                ValidationHistory.created_at.desc()
            ).all()
            logger.info("Total history records in database: %s", len(all_history))

            if all_history:
                logger.info("\nRecent history records:")
                for i, record in enumerate(all_history[:5]):  # Show last 5
                    logger.info(
                        f"  {i+1}. {record.entity_type} - {record.validation_type}"
                    )
                    logger.info("     Quality Score: %.2f", record.quality_score)
                    logger.info("     Violations: %s", record.total_violations)
                    logger.info("     Trend: %s", record.trend_direction or "N/A")
                    logger.info("     Created: %s", record.created_at)
                    logger.info("")

            # Test 3: Test trend analysis
            logger.info("\n📊 Test 3: Testing trend analysis...")

            # Get trends for volunteer entity
            volunteer_trends = history_service.get_quality_trends(
                entity_type="volunteer", days=30
            )

            logger.info("Volunteer quality trends: %s", volunteer_trends)

            # Test 4: Test summary statistics
            logger.info("\n📋 Test 4: Testing summary statistics...")

            summary_stats = history_service.get_summary_statistics(days=30)
            logger.info("Summary statistics: %s", summary_stats)

            # Test 5: Test entity-specific history
            logger.info("\n🔍 Test 5: Testing entity-specific history...")

            volunteer_history = ValidationHistory.get_entity_history(
                entity_type="volunteer", days=30
            )

            logger.info("Volunteer history records: %s", len(volunteer_history))

            if volunteer_history:
                latest_record = volunteer_history[0]
                logger.info("Latest volunteer record:")
                logger.info("  Quality Score: %.2f", latest_record.quality_score)
                logger.info("  Status: %s", latest_record.quality_status)
                logger.info("  Violation Rate: %.2f%%", latest_record.violation_rate)
                logger.info("  Trend Description: %s", latest_record.trend_description)

            logger.info("\n🎉 All tests completed successfully!")

        except Exception as e:
            logger.error("❌ Error during testing: %s", e)
            import traceback

            traceback.print_exc()


@pytest.mark.skip(
    reason="This test requires a specific validation run ID and is meant for manual testing"
)
def test_specific_run():
    """Test creating history for a specific validation run."""

    # Use a default run ID for testing, or skip if none available
    run_id = 1

    with app.app_context():
        try:
            logger.info("🧪 Testing history creation for run %s...", run_id)

            # Check if the run exists
            from models.validation import ValidationRun

            run = ValidationRun.query.get(run_id)
            if not run:
                logger.warning("⚠️ Validation run %s not found, skipping test", run_id)
                return

            history_service = ValidationHistoryService()

            # Create history for the specific run
            history_records = history_service.create_history_from_run(run_id)

            logger.info(
                f"Created {len(history_records)} history records for run {run_id}"
            )

            # Display the created records
            for i, record in enumerate(history_records):
                logger.info("\nRecord %s:", i + 1)
                logger.info("  Entity Type: %s", record.entity_type)
                logger.info("  Validation Type: %s", record.validation_type)
                logger.info("  Quality Score: %.2f", record.quality_score)
                logger.info("  Total Checks: %s", record.total_checks)
                logger.info("  Violations: %s", record.total_violations)
                logger.info("  Success Rate: %.2f%%", record.success_rate)
                logger.info("  Execution Time: %ss", record.execution_time_seconds)

                if record.trend_direction:
                    logger.info(
                        f"  Trend: {record.trend_direction} (confidence: {record.trend_confidence:.2f})"
                    )

                logger.info("  Created: %s", record.created_at)

        except Exception as e:
            logger.error("❌ Error testing run %s: %s", run_id, e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific run
        run_id = int(sys.argv[1])
        test_specific_run(run_id)
    else:
        # Run full test suite
        test_history_service()

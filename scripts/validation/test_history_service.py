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

            logger.info(f"Found {len(recent_runs)} recent completed runs")

            # Create history records for each run
            total_history_created = 0
            for run in recent_runs:
                logger.info(f"Processing run {run.id}: {run.run_type} - {run.name}")

                # Create history records for this run
                history_records = history_service.create_history_from_run(run.id)
                total_history_created += len(history_records)

                logger.info(
                    f"Created {len(history_records)} history records for run {run.id}"
                )

            logger.info(f"✅ Total history records created: {total_history_created}")

            # Test 2: Query and display history records
            logger.info("\n📈 Test 2: Querying and displaying history records...")

            all_history = ValidationHistory.query.order_by(
                ValidationHistory.created_at.desc()
            ).all()
            logger.info(f"Total history records in database: {len(all_history)}")

            if all_history:
                logger.info("\nRecent history records:")
                for i, record in enumerate(all_history[:5]):  # Show last 5
                    logger.info(
                        f"  {i+1}. {record.entity_type} - {record.validation_type}"
                    )
                    logger.info(f"     Quality Score: {record.quality_score:.2f}")
                    logger.info(f"     Violations: {record.total_violations}")
                    logger.info(f"     Trend: {record.trend_direction or 'N/A'}")
                    logger.info(f"     Created: {record.created_at}")
                    logger.info("")

            # Test 3: Test trend analysis
            logger.info("\n📊 Test 3: Testing trend analysis...")

            # Get trends for volunteer entity
            volunteer_trends = history_service.get_quality_trends(
                entity_type="volunteer", days=30
            )

            logger.info(f"Volunteer quality trends: {volunteer_trends}")

            # Test 4: Test summary statistics
            logger.info("\n📋 Test 4: Testing summary statistics...")

            summary_stats = history_service.get_summary_statistics(days=30)
            logger.info(f"Summary statistics: {summary_stats}")

            # Test 5: Test entity-specific history
            logger.info("\n🔍 Test 5: Testing entity-specific history...")

            volunteer_history = ValidationHistory.get_entity_history(
                entity_type="volunteer", days=30
            )

            logger.info(f"Volunteer history records: {len(volunteer_history)}")

            if volunteer_history:
                latest_record = volunteer_history[0]
                logger.info(f"Latest volunteer record:")
                logger.info(f"  Quality Score: {latest_record.quality_score:.2f}")
                logger.info(f"  Status: {latest_record.quality_status}")
                logger.info(f"  Violation Rate: {latest_record.violation_rate:.2f}%")
                logger.info(f"  Trend Description: {latest_record.trend_description}")

            logger.info("\n🎉 All tests completed successfully!")

        except Exception as e:
            logger.error(f"❌ Error during testing: {e}")
            import traceback

            traceback.print_exc()


def test_specific_run(run_id: int):
    """Test creating history for a specific validation run."""

    with app.app_context():
        try:
            logger.info(f"🧪 Testing history creation for run {run_id}...")

            history_service = ValidationHistoryService()

            # Create history for the specific run
            history_records = history_service.create_history_from_run(run_id)

            logger.info(
                f"Created {len(history_records)} history records for run {run_id}"
            )

            # Display the created records
            for i, record in enumerate(history_records):
                logger.info(f"\nRecord {i+1}:")
                logger.info(f"  Entity Type: {record.entity_type}")
                logger.info(f"  Validation Type: {record.validation_type}")
                logger.info(f"  Quality Score: {record.quality_score:.2f}")
                logger.info(f"  Total Checks: {record.total_checks}")
                logger.info(f"  Violations: {record.total_violations}")
                logger.info(f"  Success Rate: {record.success_rate:.2f}%")
                logger.info(f"  Execution Time: {record.execution_time_seconds}s")

                if record.trend_direction:
                    logger.info(
                        f"  Trend: {record.trend_direction} (confidence: {record.trend_confidence:.2f})"
                    )

                logger.info(f"  Created: {record.created_at}")

        except Exception as e:
            logger.error(f"❌ Error testing run {run_id}: {e}")
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

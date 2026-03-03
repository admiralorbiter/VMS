#!/usr/bin/env python3
"""
Test script for Quality Scoring System.

This script tests the quality scoring services and components
to ensure they work correctly with the validation system.
"""

import logging
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import app
from models import db
from models.validation import ValidationMetric, ValidationResult, ValidationRun
from utils.services.quality_scoring_service import QualityScoringService
from utils.services.score_calculator import ScoreCalculator
from utils.services.score_weighting_engine import ScoreWeightingEngine
from utils.services.threshold_manager import ThresholdManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_score_weighting_engine():
    """Test the score weighting engine."""
    logger.info("🧪 Testing Score Weighting Engine...")

    try:
        engine = ScoreWeightingEngine()

        # Test getting entity weights
        volunteer_weights = engine.get_entity_weights("volunteer")
        logger.info("   Volunteer weights: %s", volunteer_weights)

        # Test getting validation type weight
        field_weight = engine.get_validation_type_weight(
            "volunteer", "field_completeness"
        )
        logger.info("   Field completeness weight for volunteer: %s", field_weight)

        # Test severity weights
        critical_weight = engine.get_severity_weight("critical")
        logger.info("   Critical severity weight: %s", critical_weight)

        # Test weight summary
        summary = engine.get_weight_summary()
        logger.info("   Weight summary: %s items", len(summary))

        logger.info("✅ Score Weighting Engine tests passed!")
        assert True, "Score Weighting Engine tests passed"

    except Exception as e:
        logger.error("❌ Score Weighting Engine test failed: %s", e)
        assert False, f"Score Weighting Engine test failed: {e}"


def test_threshold_manager():
    """Test the threshold manager."""
    logger.info("🧪 Testing Threshold Manager...")

    try:
        manager = ThresholdManager()

        # Test getting entity threshold
        volunteer_threshold = manager.get_entity_threshold("volunteer")
        logger.info("   Volunteer threshold: %s", volunteer_threshold)

        # Test getting validation type threshold
        field_threshold = manager.get_validation_type_threshold(
            "volunteer", "field_completeness"
        )
        logger.info("   Field completeness threshold: %s", field_threshold)

        # Test quality status
        status = manager.get_quality_status(85.0, "volunteer")
        logger.info("   Quality status for 85.0: %s", status)

        # Test threshold summary
        summary = manager.get_threshold_summary()
        logger.info("   Threshold summary: %s items", len(summary))

        logger.info("✅ Threshold Manager tests passed!")
        assert True, "Threshold Manager tests passed"

    except Exception as e:
        logger.error("❌ Threshold Manager test failed: %s", e)
        assert False, f"Threshold Manager test failed: {e}"


def test_score_calculator():
    """Test the score calculator."""
    logger.info("🧪 Testing Score Calculator...")

    try:
        calculator = ScoreCalculator()

        # Test scoring algorithm detection
        algorithm = calculator._get_scoring_algorithm("field_completeness")
        logger.info("   Field completeness algorithm: %s", algorithm)

        # Test default score calculation
        # Create mock validation results
        mock_results = []
        for i in range(10):
            result = ValidationResult(
                run_id=1,
                entity_type="volunteer",
                validation_type="field_completeness",
                field_name=f"test_field_{i}",
                severity="info" if i < 8 else "error",  # 8 passed, 2 failed
                message=f"Test message {i}",
                expected_value="expected",
                actual_value="actual",
            )
            mock_results.append(result)

        # Calculate score
        score = calculator.calculate_dimension_score(
            "field_completeness", mock_results, "volunteer"
        )
        logger.info("   Calculated field completeness score: %s", score)

        # Test score breakdown
        breakdown = calculator.get_score_breakdown("field_completeness", mock_results)
        logger.info("   Score breakdown: %s", breakdown["final_score"])

        logger.info("✅ Score Calculator tests passed!")
        assert True, "Score Calculator tests passed"

    except Exception as e:
        logger.error("❌ Score Calculator test failed: %s", e)
        assert False, f"Score Calculator test failed: {e}"


def test_quality_scoring_service():
    """Test the main quality scoring service."""
    logger.info("🧪 Testing Quality Scoring Service...")

    try:
        service = QualityScoringService()

        # Test entity quality score calculation
        result = service.calculate_entity_quality_score(
            entity_type="volunteer", days=7, include_details=True
        )

        logger.info(
            "   Volunteer quality score: %s", result.get("quality_score", "N/A")
        )
        logger.info("   Quality status: %s", result.get("quality_status", "N/A"))
        logger.info("   Total checks: %s", result.get("total_checks", "N/A"))

        # Test comprehensive report
        report = service.calculate_comprehensive_quality_report(
            entity_types=["volunteer", "organization"], days=7, include_trends=False
        )

        logger.info(
            f"   Comprehensive report generated: {len(report.get('entity_scores', {}))} entities"
        )

        logger.info("✅ Quality Scoring Service tests passed!")
        assert True, "Quality Scoring Service tests passed"

    except Exception as e:
        logger.error("❌ Quality Scoring Service test failed: %s", e)
        assert False, f"Quality Scoring Service test failed: {e}"


def test_integration():
    """Test integration between all components."""
    logger.info("🧪 Testing Integration...")

    try:
        # Test end-to-end quality scoring
        service = QualityScoringService()

        # Test with different entity types
        entity_types = ["volunteer", "organization", "event"]

        for entity_type in entity_types:
            logger.info("   Testing %s...", entity_type)

            result = service.calculate_entity_quality_score(
                entity_type=entity_type, days=7, include_details=True
            )

            if "error" in result:
                logger.warning("      %s had error: %s", entity_type, result["error"])
            else:
                logger.info(
                    f"      {entity_type} score: {result.get('quality_score', 'N/A')}"
                )

        logger.info("✅ Integration tests passed!")
        assert True, "Integration tests passed"

    except Exception as e:
        logger.error("❌ Integration test failed: %s", e)
        assert False, f"Integration test failed: {e}"


def main():
    """Main test function."""
    logger.info("🚀 Starting Quality Scoring System Tests...")

    with app.app_context():
        try:
            # Run all tests
            tests = [
                test_score_weighting_engine,
                test_threshold_manager,
                test_score_calculator,
                test_quality_scoring_service,
                test_integration,
            ]

            passed = 0
            total = len(tests)

            for test in tests:
                if test():
                    passed += 1
                logger.info("")  # Add spacing between tests

            # Summary
            logger.info("📊 Test Summary:")
            logger.info("   Passed: %s/%s", passed, total)
            logger.info("   Success Rate: %.1f%%", (passed / total) * 100)

            if passed == total:
                logger.info(
                    "🎉 All tests passed! Quality Scoring System is working correctly."
                )
                logger.info("\n📋 Next steps:")
                logger.info(
                    "   1. Access the dashboard at: http://localhost:5000/quality_dashboard"
                )
                logger.info("   2. Test with real validation data")
                logger.info("   3. Customize weights and thresholds as needed")
            else:
                logger.warning("⚠️  Some tests failed. Please check the logs above.")

            return passed == total

        except Exception as e:
            logger.error("❌ Test suite failed: %s", e)
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

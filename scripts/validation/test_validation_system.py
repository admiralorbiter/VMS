#!/usr/bin/env python3
"""
Test script for the Salesforce Data Validation System.

This script tests the basic functionality of the validation system
without requiring a full database or Salesforce connection.
"""

import logging
import os
import sys
from datetime import datetime

# Add the project root to the Python path (scripts/validation is 2 levels deep)
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_config_loading():
    """Test configuration loading."""
    logger.info("Testing configuration loading...")

    try:
        from config.validation import get_config, validate_config

        # Test config loading
        config = get_config()
        logger.info(f"Configuration loaded successfully with {len(config)} sections")

        # Test config validation
        errors = validate_config()
        if errors:
            logger.warning(f"Configuration validation warnings: {errors}")
        else:
            logger.info("Configuration validation passed")

        # Test specific sections
        from config.validation import get_config_section

        thresholds = get_config_section("thresholds")
        logger.info(f"Thresholds loaded: {thresholds}")

        return True

    except Exception as e:
        logger.error(f"Configuration loading failed: {e}")
        return False


def test_validation_models():
    """Test validation model creation."""
    logger.info("Testing validation models...")

    try:
        from models.validation.metric import ValidationMetric
        from models.validation.result import ValidationResult
        from models.validation.run import ValidationRun

        # Test model creation
        run = ValidationRun(
            run_type="test",
            name="Test Validation Run",
            description="Test run for validation system testing",
        )

        result = ValidationResult.create_result(
            run_id=1,
            entity_type="test",
            severity="info",
            message="Test validation result",
            validation_type="test",
        )

        metric = ValidationMetric.create_metric(
            metric_name="test_metric",
            metric_value=95.5,
            metric_category="quality",
            metric_unit="percentage",
        )

        logger.info("Validation models created successfully")
        logger.info(f"Run: {run}")
        logger.info(f"Result: {result}")
        logger.info(f"Metric: {metric}")

        return True

    except Exception as e:
        logger.error(f"Validation model testing failed: {e}")
        return False


def test_validation_base():
    """Test validation base classes."""
    logger.info("Testing validation base classes...")

    try:
        from utils.validation_base import (
            DataValidator,
            ValidationContext,
            ValidationRule,
        )

        # Test context creation
        context = ValidationContext(run_id=1, user_id=1)
        logger.info(f"Validation context created: {context}")

        # Test config access
        config_section = context.get_config_section("thresholds")
        logger.info(f"Config section accessed: {config_section}")

        logger.info("Validation base classes tested successfully")
        return True

    except Exception as e:
        logger.error(f"Validation base testing failed: {e}")
        return False


def test_count_validator():
    """Test count validator (without database connection)."""
    logger.info("Testing count validator...")

    try:
        from utils.validators.count_validator import CountValidator

        # Test validator creation
        validator = CountValidator(run_id=1, entity_type="volunteer")
        logger.info(f"Count validator created: {validator}")

        # Test configuration access
        tolerance = validator.tolerance_percentage
        logger.info(f"Tolerance percentage: {tolerance}")

        # Test entity type
        entity_type = validator.get_entity_type()
        logger.info(f"Entity type: {entity_type}")

        logger.info("Count validator tested successfully")
        return True

    except Exception as e:
        logger.error(f"Count validator testing failed: {e}")
        return False


def test_validation_engine():
    """Test validation engine (without database connection)."""
    logger.info("Testing validation engine...")

    try:
        from utils.validation_engine import ValidationEngine

        # Test engine creation
        engine = ValidationEngine()
        logger.info(f"Validation engine created: {engine}")

        # Test configuration access
        config = engine.config
        logger.info(f"Engine configuration loaded: {len(config)} rules")

        logger.info("Validation engine tested successfully")
        return True

    except Exception as e:
        logger.error(f"Validation engine testing failed: {e}")
        return False


def test_salesforce_client():
    """Test Salesforce client (without actual connection)."""
    logger.info("Testing Salesforce client...")

    try:
        from utils.salesforce_client import (
            SalesforceClientError,
            SalesforceConnectionError,
            SalesforceRateLimitError,
        )

        # Test exception classes
        logger.info("Salesforce client exception classes imported successfully")

        # Test client class (without initialization)
        from utils.salesforce_client import SalesforceClient

        logger.info("Salesforce client class imported successfully")

        logger.info("Salesforce client tested successfully")
        return True

    except Exception as e:
        logger.error(f"Salesforce client testing failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    logger.info("=" * 60)
    logger.info("Starting Salesforce Data Validation System Tests")
    logger.info("=" * 60)

    tests = [
        ("Configuration Loading", test_config_loading),
        ("Validation Models", test_validation_models),
        ("Validation Base Classes", test_validation_base),
        ("Count Validator", test_count_validator),
        ("Validation Engine", test_validation_engine),
        ("Salesforce Client", test_salesforce_client),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing: {test_name} ---")
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                logger.info(f"✓ {test_name} PASSED")
            else:
                logger.error(f"✗ {test_name} FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "PASSED" if success else "FAILED"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! The validation system is ready for use.")
        return True
    else:
        logger.error(
            f"❌ {total - passed} tests failed. Please check the errors above."
        )
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during testing: {e}")
        sys.exit(1)

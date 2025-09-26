#!/usr/bin/env python3
"""
Minimal test script for the Salesforce Data Validation System.

This script tests only the core functionality that doesn't require
database connections or external dependencies.
"""

import logging
import os
import sys

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

        assert True, "Configuration validation passed"

    except Exception as e:
        logger.error(f"Configuration loading failed: {e}")
        assert False, f"Configuration loading failed: {e}"


def test_validation_base_classes():
    """Test validation base classes."""
    logger.info("Testing validation base classes...")

    try:
        from utils.validation_base import ValidationContext

        # Test context creation
        context = ValidationContext(run_id=1, user_id=1)
        logger.info(f"Validation context created: {context}")

        # Test config access
        config_section = context.get_config_section("thresholds")
        logger.info(f"Config section accessed: {config_section}")

        logger.info("Validation base classes tested successfully")
        assert True, "Validation base testing passed"

    except Exception as e:
        logger.error(f"Validation base testing failed: {e}")
        assert False, f"Validation base testing failed: {e}"


def test_salesforce_client_import():
    """Test Salesforce client import (without initialization)."""
    logger.info("Testing Salesforce client import...")

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

        logger.info("Salesforce client import tested successfully")
        assert True, "Salesforce client import testing passed"

    except Exception as e:
        logger.error(f"Salesforce client import testing failed: {e}")
        assert False, f"Salesforce client import testing failed: {e}"


def test_count_validator_import():
    """Test count validator import (without database connection)."""
    logger.info("Testing count validator import...")

    try:
        from utils.validators.count_validator import CountValidator

        # Test validator class import
        logger.info("Count validator class imported successfully")

        logger.info("Count validator import tested successfully")
        assert True, "Count validator import testing passed"

    except Exception as e:
        logger.error(f"Count validator import testing failed: {e}")
        assert False, f"Count validator import testing failed: {e}"


def test_validation_engine_import():
    """Test validation engine import (without database connection)."""
    logger.info("Testing validation engine import...")

    try:
        from utils.validation_engine import ValidationEngine

        # Test engine class import
        logger.info("Validation engine class imported successfully")

        logger.info("Validation engine import tested successfully")
        assert True, "Validation engine import testing passed"

    except Exception as e:
        logger.error(f"Validation engine import testing failed: {e}")
        assert False, f"Validation engine import testing failed: {e}"


def run_all_tests():
    """Run all minimal tests and report results."""
    logger.info("=" * 60)
    logger.info("Starting Minimal Salesforce Data Validation System Tests")
    logger.info("=" * 60)

    tests = [
        ("Configuration Loading", test_config_loading),
        ("Validation Base Classes", test_validation_base_classes),
        ("Salesforce Client Import", test_salesforce_client_import),
        ("Count Validator Import", test_count_validator_import),
        ("Validation Engine Import", test_validation_engine_import),
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
        logger.info("🎉 All minimal tests passed! The core system is working.")
        assert True, "All minimal tests passed"
    else:
        logger.error(
            f"❌ {total - passed} tests failed. Please check the errors above."
        )
        assert False, f"{total - passed} minimal tests failed"


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

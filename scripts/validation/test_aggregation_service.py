#!/usr/bin/env python3
"""
Test script for DataAggregationService.

This script demonstrates the new aggregation capabilities including:
- Rolling averages and moving windows
- Trend pattern detection
- Data summarization
- Performance optimization
"""

import logging
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import app
from models.validation import ValidationMetric
from utils.services.aggregation_service import DataAggregationService

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_rolling_averages():
    """Test rolling averages calculation."""

    with app.app_context():
        try:
            logger.info("🧮 Testing rolling averages calculation...")

            aggregation_service = DataAggregationService()

            # Test rolling averages for field completeness
            rolling_avg_result = aggregation_service.calculate_rolling_averages(
                metric_name="field_completeness",
                entity_type="volunteer",
                window_size=7,
                days=30,
            )

            logger.info(f"Rolling averages result: {rolling_avg_result}")

            if rolling_avg_result.get("rolling_averages"):
                logger.info(
                    f"✅ Successfully calculated {len(rolling_avg_result['rolling_averages'])} rolling averages"
                )
                logger.info(f"   Data points: {rolling_avg_result['data_points']}")
                logger.info(
                    f"   Overall average: {rolling_avg_result['overall_average']:.2f}"
                )
                logger.info(
                    f"   Overall std dev: {rolling_avg_result['overall_std_deviation']:.2f}"
                )
            else:
                logger.warning("⚠️ No rolling averages calculated - insufficient data")

            return rolling_avg_result

        except Exception as e:
            logger.error(f"❌ Error testing rolling averages: {e}")
            import traceback

            traceback.print_exc()
            return None


def test_moving_windows():
    """Test moving windows with different sizes."""

    with app.app_context():
        try:
            logger.info("🪟 Testing moving windows calculation...")

            aggregation_service = DataAggregationService()

            # Test moving windows for business rule compliance
            moving_windows_result = aggregation_service.calculate_moving_windows(
                metric_name="business_rule_compliance",
                entity_type="volunteer",
                window_sizes=[3, 7, 14],
                days=30,
            )

            logger.info(f"Moving windows result: {moving_windows_result}")

            if moving_windows_result.get("windows"):
                logger.info(
                    f"✅ Successfully calculated moving windows for {len(moving_windows_result['windows'])} window sizes"
                )

                # Show comparison results
                comparison = moving_windows_result.get("comparison", {})
                for window_name, comp_data in comparison.items():
                    logger.info(
                        f"   {window_name}: stability={comp_data.get('stability', 0):.3f}, "
                        f"responsiveness={comp_data.get('responsiveness', 0):.3f}"
                    )
            else:
                logger.warning("⚠️ No moving windows calculated - insufficient data")

            return moving_windows_result

        except Exception as e:
            logger.error(f"❌ Error testing moving windows: {e}")
            import traceback

            traceback.print_exc()
            return None


def test_trend_patterns():
    """Test trend pattern detection."""

    with app.app_context():
        try:
            logger.info("📈 Testing trend pattern detection...")

            aggregation_service = DataAggregationService()

            # Test pattern detection for data type accuracy
            patterns_result = aggregation_service.detect_trend_patterns(
                metric_name="data_type_accuracy",
                entity_type="volunteer",
                days=90,
                min_pattern_length=3,
            )

            logger.info(f"Pattern detection result: {patterns_result}")

            if patterns_result.get("patterns"):
                logger.info(
                    f"✅ Successfully detected {len(patterns_result['patterns'])} patterns"
                )

                for pattern in patterns_result["patterns"]:
                    pattern_type = pattern.get("pattern_type", "unknown")
                    description = pattern.get("description", "No description")
                    confidence = pattern.get("confidence", 0)

                    logger.info(f"   Pattern: {pattern_type} - {description}")
                    logger.info(f"     Confidence: {confidence:.3f}")
            else:
                logger.warning(
                    "⚠️ No patterns detected - insufficient data or no patterns found"
                )

            return patterns_result

        except Exception as e:
            logger.error(f"❌ Error testing trend patterns: {e}")
            import traceback

            traceback.print_exc()
            return None


def test_data_summary():
    """Test comprehensive data summary generation."""

    with app.app_context():
        try:
            logger.info("📊 Testing comprehensive data summary generation...")

            aggregation_service = DataAggregationService()

            # Generate summary for volunteer entity
            summary_result = aggregation_service.generate_data_summary(
                entity_type="volunteer", days=30, include_patterns=True
            )

            logger.info(f"Data summary result: {summary_result}")

            if summary_result.get("metrics_summary"):
                logger.info(f"✅ Successfully generated data summary")
                logger.info(
                    f"   Metrics analyzed: {summary_result['performance_summary']['total_metrics_analyzed']}"
                )
                logger.info(
                    f"   Total data points: {summary_result['performance_summary']['total_data_points']}"
                )

                # Show metrics summary
                for metric_name, metric_data in summary_result[
                    "metrics_summary"
                ].items():
                    logger.info(
                        f"   {metric_name}: mean={metric_data['mean']:.2f}, "
                        f"std={metric_data['std_deviation']:.2f}, "
                        f"count={metric_data['count']}"
                    )
            else:
                logger.warning("⚠️ No data summary generated - insufficient data")

            return summary_result

        except Exception as e:
            logger.error(f"❌ Error testing data summary: {e}")
            import traceback

            traceback.print_exc()
            return None


def test_performance_optimization():
    """Test performance optimization recommendations."""

    with app.app_context():
        try:
            logger.info("⚡ Testing performance optimization recommendations...")

            aggregation_service = DataAggregationService()

            # Test optimization for field completeness metric
            optimization_result = aggregation_service.optimize_aggregation_performance(
                metric_name="field_completeness",
                entity_type="volunteer",
                target_response_time=1.0,
            )

            logger.info(f"Performance optimization result: {optimization_result}")

            if optimization_result.get("recommended_strategy"):
                logger.info(f"✅ Successfully generated optimization recommendations")
                logger.info(f"   Dataset size: {optimization_result['dataset_size']}")
                logger.info(
                    f"   Recommended strategy: {optimization_result['recommended_strategy']}"
                )
                logger.info(
                    f"   Recommended window size: {optimization_result['recommended_window_size']}"
                )
                logger.info(
                    f"   Estimated response time: {optimization_result['estimated_response_time']:.3f}s"
                )

                # Show optimization tips
                tips = optimization_result.get("optimization_tips", [])
                if tips:
                    logger.info("   Optimization tips:")
                    for tip in tips:
                        logger.info(f"     • {tip}")
            else:
                logger.warning("⚠️ No optimization recommendations generated")

            return optimization_result

        except Exception as e:
            logger.error(f"❌ Error testing performance optimization: {e}")
            import traceback

            traceback.print_exc()
            return None


def test_metric_trends():
    """Test the new ValidationMetric trend calculation methods."""

    with app.app_context():
        try:
            logger.info("📊 Testing ValidationMetric trend calculation methods...")

            # Test trend calculation for a specific metric
            trend_result = ValidationMetric.calculate_trends_for_metric(
                metric_name="field_completeness", entity_type="volunteer", days=30
            )

            logger.info(f"Metric trend result: {trend_result}")

            if trend_result.get("trend") != "insufficient_data":
                logger.info(f"✅ Successfully calculated metric trends")
                logger.info(f"   Trend: {trend_result['trend']}")
                logger.info(f"   Confidence: {trend_result['confidence']:.3f}")
                logger.info(f"   Data points: {trend_result['data_points']}")
                logger.info(
                    f"   Change percentage: {trend_result['change_percentage']:.2f}%"
                )
            else:
                logger.warning("⚠️ Insufficient data for trend calculation")

            # Test period-based summary
            period_summary = ValidationMetric.get_metric_summary_by_period(
                metric_name="field_completeness",
                period="daily",
                entity_type="volunteer",
                days=30,
            )

            logger.info(f"Period summary result: {period_summary}")

            if period_summary.get("periods"):
                logger.info(f"✅ Successfully generated period summary")
                logger.info(f"   Total periods: {period_summary['total_periods']}")
                logger.info(f"   Total values: {period_summary['total_values']}")
            else:
                logger.warning("⚠️ No period summary generated - insufficient data")

            return {"trend_result": trend_result, "period_summary": period_summary}

        except Exception as e:
            logger.error(f"❌ Error testing metric trends: {e}")
            import traceback

            traceback.print_exc()
            return None


def main():
    """Run all aggregation service tests."""

    logger.info("🚀 Starting DataAggregationService tests...")

    results = {}

    # Test 1: Rolling averages
    results["rolling_averages"] = test_rolling_averages()

    # Test 2: Moving windows
    results["moving_windows"] = test_moving_windows()

    # Test 3: Trend patterns
    results["trend_patterns"] = test_trend_patterns()

    # Test 4: Data summary
    results["data_summary"] = test_data_summary()

    # Test 5: Performance optimization
    results["performance_optimization"] = test_performance_optimization()

    # Test 6: Metric trends
    results["metric_trends"] = test_metric_trends()

    # Summary
    logger.info("\n📋 Test Summary:")
    successful_tests = sum(1 for result in results.values() if result is not None)
    total_tests = len(results)

    logger.info(f"   Successful tests: {successful_tests}/{total_tests}")

    if successful_tests == total_tests:
        logger.info("🎉 All tests completed successfully!")
    else:
        logger.warning(f"⚠️ {total_tests - successful_tests} tests failed or had issues")

    return results


if __name__ == "__main__":
    main()

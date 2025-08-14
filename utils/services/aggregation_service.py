# utils/services/aggregation_service.py
"""
Data Aggregation Service for Phase 3.4.

This service provides advanced data aggregation capabilities including:
- Rolling averages and moving windows
- Trend calculations and statistical analysis
- Data summarization and pattern detection
- Performance optimization for large datasets
"""

import logging
import math
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from models import db
from models.validation import ValidationHistory, ValidationMetric, ValidationRun


class DataAggregationService:
    """
    Service for aggregating and analyzing validation data.

    This service provides comprehensive data aggregation capabilities
    for trend analysis, performance monitoring, and quality assessment.
    """

    def __init__(self):
        """Initialize the data aggregation service."""
        self.logger = logging.getLogger(__name__)

        # Configuration for aggregation
        self.default_window_sizes = {
            "hourly": 24,  # 24 hours
            "daily": 7,  # 7 days
            "weekly": 4,  # 4 weeks
            "monthly": 3,  # 3 months
            "quarterly": 4,  # 4 quarters
        }

        # Statistical thresholds
        self.anomaly_threshold = 2.0  # Standard deviations for anomaly detection
        self.trend_confidence_threshold = 0.7  # Minimum confidence for trend analysis

    def calculate_rolling_averages(
        self,
        metric_name: str,
        entity_type: str = None,
        window_size: int = 7,
        aggregation_period: str = "daily",
        days: int = 30,
    ) -> Dict:
        """
        Calculate rolling averages for a specific metric.

        Args:
            metric_name: Name of the metric to analyze
            entity_type: Optional entity type filter
            window_size: Size of the rolling window
            aggregation_period: Period for aggregation
            days: Number of days to look back

        Returns:
            Dictionary containing rolling average data
        """
        try:
            # Get metrics for the specified period
            metrics = ValidationMetric.get_metrics_by_name(
                metric_name=metric_name, entity_type=entity_type, days=days
            )

            if not metrics:
                return {
                    "metric_name": metric_name,
                    "entity_type": entity_type,
                    "window_size": window_size,
                    "aggregation_period": aggregation_period,
                    "rolling_averages": [],
                    "data_points": 0,
                    "message": "No metrics found for the specified criteria",
                }

            # Sort metrics by timestamp
            metrics.sort(key=lambda x: x.timestamp)

            # Calculate rolling averages
            rolling_averages = []
            values = [m.float_value for m in metrics]
            timestamps = [m.timestamp for m in metrics]

            for i in range(window_size - 1, len(values)):
                window_values = values[i - window_size + 1 : i + 1]
                window_avg = sum(window_values) / len(window_values)

                rolling_averages.append(
                    {
                        "timestamp": timestamps[i].isoformat(),
                        "value": window_avg,
                        "window_start": timestamps[i - window_size + 1].isoformat(),
                        "window_end": timestamps[i].isoformat(),
                        "data_points": len(window_values),
                        "min_value": min(window_values),
                        "max_value": max(window_values),
                        "std_deviation": (
                            statistics.stdev(window_values)
                            if len(window_values) > 1
                            else 0.0
                        ),
                    }
                )

            return {
                "metric_name": metric_name,
                "entity_type": entity_type,
                "window_size": window_size,
                "aggregation_period": aggregation_period,
                "rolling_averages": rolling_averages,
                "data_points": len(metrics),
                "total_windows": len(rolling_averages),
                "overall_average": sum(values) / len(values) if values else 0.0,
                "overall_std_deviation": (
                    statistics.stdev(values) if len(values) > 1 else 0.0
                ),
            }

        except Exception as e:
            self.logger.error(f"Error calculating rolling averages: {e}")
            return {
                "error": str(e),
                "metric_name": metric_name,
                "entity_type": entity_type,
            }

    def calculate_moving_windows(
        self,
        metric_name: str,
        entity_type: str = None,
        window_sizes: List[int] = None,
        days: int = 30,
    ) -> Dict:
        """
        Calculate moving windows with different sizes for comparison.

        Args:
            metric_name: Name of the metric to analyze
            entity_type: Optional entity type filter
            window_sizes: List of window sizes to calculate
            days: Number of days to look back

        Returns:
            Dictionary containing moving window data for different sizes
        """
        if window_sizes is None:
            window_sizes = [3, 7, 14, 30]

        results = {}

        for window_size in window_sizes:
            results[f"window_{window_size}"] = self.calculate_rolling_averages(
                metric_name=metric_name,
                entity_type=entity_type,
                window_size=window_size,
                days=days,
            )

        # Calculate comparison metrics
        comparison = self._compare_window_performances(results)

        return {
            "metric_name": metric_name,
            "entity_type": entity_type,
            "window_sizes": window_sizes,
            "windows": results,
            "comparison": comparison,
        }

    def _compare_window_performances(self, window_results: Dict) -> Dict:
        """Compare performance of different window sizes."""
        comparison = {}

        for window_name, result in window_results.items():
            if "rolling_averages" in result and result["rolling_averages"]:
                # Calculate stability (lower std dev = more stable)
                stability_scores = [
                    w["std_deviation"] for w in result["rolling_averages"]
                ]
                avg_stability = (
                    sum(stability_scores) / len(stability_scores)
                    if stability_scores
                    else 0.0
                )

                # Calculate responsiveness (how quickly it follows changes)
                values = [w["value"] for w in result["rolling_averages"]]
                if len(values) > 1:
                    changes = [
                        abs(values[i] - values[i - 1]) for i in range(1, len(values))
                    ]
                    responsiveness = sum(changes) / len(changes) if changes else 0.0
                else:
                    responsiveness = 0.0

                comparison[window_name] = {
                    "stability": avg_stability,
                    "responsiveness": responsiveness,
                    "data_points": result["data_points"],
                    "total_windows": result["total_windows"],
                }

        return comparison

    def detect_trend_patterns(
        self,
        metric_name: str,
        entity_type: str = None,
        days: int = 90,
        min_pattern_length: int = 5,
    ) -> Dict:
        """
        Detect trend patterns in metric data.

        Args:
            metric_name: Name of the metric to analyze
            entity_type: Optional entity type filter
            days: Number of days to analyze
            min_pattern_length: Minimum length for pattern detection

        Returns:
            Dictionary containing detected patterns
        """
        try:
            # Get metrics for trend analysis
            metrics = ValidationMetric.get_metrics_by_name(
                metric_name=metric_name, entity_type=entity_type, days=days
            )

            if len(metrics) < min_pattern_length:
                return {
                    "metric_name": metric_name,
                    "entity_type": entity_type,
                    "patterns": [],
                    "message": f"Insufficient data points. Need at least {min_pattern_length}, got {len(metrics)}",
                }

            # Sort by timestamp
            metrics.sort(key=lambda x: x.timestamp)
            values = [m.float_value for m in metrics]
            timestamps = [m.timestamp for m in metrics]

            # Detect patterns
            patterns = []

            # Linear trend
            linear_trend = self._detect_linear_trend(values, timestamps)
            if linear_trend:
                patterns.append(linear_trend)

            # Cyclical patterns
            cyclical_patterns = self._detect_cyclical_patterns(values, timestamps)
            patterns.extend(cyclical_patterns)

            # Seasonal patterns
            seasonal_patterns = self._detect_seasonal_patterns(values, timestamps)
            patterns.extend(seasonal_patterns)

            # Anomaly detection
            anomalies = self._detect_anomalies(values, timestamps)
            if anomalies:
                patterns.append(anomalies)

            return {
                "metric_name": metric_name,
                "entity_type": entity_type,
                "analysis_period_days": days,
                "total_data_points": len(metrics),
                "patterns": patterns,
                "pattern_count": len(patterns),
            }

        except Exception as e:
            self.logger.error(f"Error detecting trend patterns: {e}")
            return {
                "error": str(e),
                "metric_name": metric_name,
                "entity_type": entity_type,
            }

    def _detect_linear_trend(
        self, values: List[float], timestamps: List[datetime]
    ) -> Optional[Dict]:
        """Detect linear trend in the data."""
        if len(values) < 2:
            return None

        # Calculate linear regression
        x_values = [(ts - timestamps[0]).days for ts in timestamps]
        y_values = values

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        # Calculate slope and intercept
        if n * sum_x2 - sum_x * sum_x == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # Calculate R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum(
            (y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values)
        )
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        # Determine trend strength and direction
        if abs(slope) < 0.01:
            trend_strength = "stable"
        elif abs(slope) < 0.1:
            trend_strength = "weak"
        elif abs(slope) < 0.5:
            trend_strength = "moderate"
        else:
            trend_strength = "strong"

        # Determine trend direction
        if abs(slope) < 0.01:
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"

        return {
            "pattern_type": "linear_trend",
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "trend_strength": trend_strength,
            "trend_direction": trend_direction,
            "confidence": min(1.0, r_squared * (len(values) / 10.0)),
            "description": f"{trend_strength.title()} {trend_direction} trend (R² = {r_squared:.3f})",
        }

    def _detect_cyclical_patterns(
        self, values: List[float], timestamps: List[datetime]
    ) -> List[Dict]:
        """Detect cyclical patterns in the data."""
        patterns = []

        if len(values) < 6:  # Need at least 6 points for cycle detection
            return patterns

        # Simple cycle detection using autocorrelation
        for cycle_length in range(
            2, min(len(values) // 2, 30)
        ):  # Look for cycles up to 30 days
            autocorr = self._calculate_autocorrelation(values, cycle_length)

            if autocorr > 0.7:  # Strong correlation threshold
                patterns.append(
                    {
                        "pattern_type": "cyclical",
                        "cycle_length": cycle_length,
                        "autocorrelation": autocorr,
                        "confidence": autocorr,
                        "description": f"Cyclical pattern with {cycle_length}-day cycle (correlation: {autocorr:.3f})",
                    }
                )

        return patterns

    def _detect_seasonal_patterns(
        self, values: List[float], timestamps: List[datetime]
    ) -> List[Dict]:
        """Detect seasonal patterns in the data."""
        patterns = []

        if len(values) < 30:  # Need at least 30 days for seasonal detection
            return patterns

        # Group by week of year
        weekly_groups = defaultdict(list)
        for i, ts in enumerate(timestamps):
            week_num = ts.isocalendar()[1]
            weekly_groups[week_num].append(values[i])

        # Calculate weekly averages
        weekly_averages = {}
        for week, week_values in weekly_groups.items():
            if len(week_values) >= 2:  # Need at least 2 values per week
                weekly_averages[week] = sum(week_values) / len(week_values)

        if len(weekly_averages) >= 4:  # Need at least 4 weeks
            # Check for weekly patterns
            weekly_values = list(weekly_averages.values())
            weekly_std = (
                statistics.stdev(weekly_values) if len(weekly_values) > 1 else 0.0
            )
            weekly_mean = sum(weekly_values) / len(weekly_values)

            # If variation is significant, it might indicate a weekly pattern
            if weekly_std > weekly_mean * 0.2:  # 20% variation threshold
                patterns.append(
                    {
                        "pattern_type": "seasonal",
                        "season_length": "weekly",
                        "variation_coefficient": (
                            weekly_std / weekly_mean if weekly_mean > 0 else 0.0
                        ),
                        "confidence": min(
                            1.0,
                            (weekly_std / weekly_mean) * 2 if weekly_mean > 0 else 0.0,
                        ),
                        "description": f"Weekly seasonal pattern with {weekly_std/weekly_mean*100:.1f}% variation",
                    }
                )

        return patterns

    def _detect_anomalies(
        self, values: List[float], timestamps: List[datetime]
    ) -> Optional[Dict]:
        """Detect anomalies in the data using statistical methods."""
        if len(values) < 3:
            return None

        # Calculate z-scores
        mean_val = sum(values) / len(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0.0

        if std_val == 0:
            return None

        z_scores = [(v - mean_val) / std_val for v in values]
        anomalies = [
            i for i, z in enumerate(z_scores) if abs(z) > self.anomaly_threshold
        ]

        if anomalies:
            return {
                "pattern_type": "anomalies",
                "anomaly_count": len(anomalies),
                "anomaly_indices": anomalies,
                "anomaly_timestamps": [timestamps[i].isoformat() for i in anomalies],
                "anomaly_values": [values[i] for i in anomalies],
                "anomaly_z_scores": [z_scores[i] for i in anomalies],
                "threshold_used": self.anomaly_threshold,
                "description": f"Detected {len(anomalies)} anomalies using {self.anomaly_threshold}σ threshold",
            }

        return None

    def _calculate_autocorrelation(self, values: List[float], lag: int) -> float:
        """Calculate autocorrelation for a given lag."""
        if lag >= len(values):
            return 0.0

        # Calculate mean
        mean_val = sum(values) / len(values)

        # Calculate autocorrelation
        numerator = 0.0
        denominator = 0.0

        for i in range(len(values) - lag):
            numerator += (values[i] - mean_val) * (values[i + lag] - mean_val)
            denominator += (values[i] - mean_val) ** 2

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def generate_data_summary(
        self,
        entity_type: str = None,
        validation_type: str = None,
        days: int = 30,
        include_patterns: bool = True,
    ) -> Dict:
        """
        Generate comprehensive data summary for validation metrics.

        Args:
            entity_type: Optional entity type filter
            validation_type: Optional validation type filter
            days: Number of days to analyze
            include_patterns: Whether to include pattern detection

        Returns:
            Dictionary containing comprehensive data summary
        """
        try:
            summary = {
                "analysis_period_days": days,
                "entity_type": entity_type,
                "validation_type": validation_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics_summary": {},
                "trends_summary": {},
                "patterns_summary": {},
                "performance_summary": {},
            }

            # Get all metrics for the period
            all_metrics = ValidationMetric.get_metrics_by_name(
                metric_name=None, entity_type=entity_type, days=days  # Get all metrics
            )

            if not all_metrics:
                summary["message"] = "No metrics found for the specified criteria"
                return summary

            # Group metrics by name
            metrics_by_name = defaultdict(list)
            for metric in all_metrics:
                metrics_by_name[metric.metric_name].append(metric)

            # Analyze each metric
            for metric_name, metrics in metrics_by_name.items():
                # Basic statistics
                values = [m.float_value for m in metrics]
                summary["metrics_summary"][metric_name] = {
                    "count": len(metrics),
                    "mean": sum(values) / len(values) if values else 0.0,
                    "min": min(values) if values else 0.0,
                    "max": max(values) if values else 0.0,
                    "std_deviation": (
                        statistics.stdev(values) if len(values) > 1 else 0.0
                    ),
                    "latest_value": values[-1] if values else None,
                    "latest_timestamp": (
                        metrics[-1].timestamp.isoformat() if metrics else None
                    ),
                }

                # Trend analysis
                if len(metrics) >= 3:
                    trend_result = ValidationMetric.calculate_trends_for_metric(
                        metric_name=metric_name, entity_type=entity_type, days=days
                    )
                    summary["trends_summary"][metric_name] = trend_result

                # Pattern detection
                if include_patterns and len(metrics) >= 5:
                    patterns = self.detect_trend_patterns(
                        metric_name=metric_name, entity_type=entity_type, days=days
                    )
                    summary["patterns_summary"][metric_name] = patterns

            # Performance summary
            summary["performance_summary"] = {
                "total_metrics_analyzed": len(metrics_by_name),
                "total_data_points": len(all_metrics),
                "analysis_completion_time": datetime.utcnow().isoformat(),
            }

            return summary

        except Exception as e:
            self.logger.error(f"Error generating data summary: {e}")
            return {
                "error": str(e),
                "entity_type": entity_type,
                "validation_type": validation_type,
            }

    def optimize_aggregation_performance(
        self,
        metric_name: str,
        entity_type: str = None,
        target_response_time: float = 1.0,
    ) -> Dict:
        """
        Optimize aggregation performance for large datasets.

        Args:
            metric_name: Name of the metric to optimize
            entity_type: Optional entity type filter
            target_response_time: Target response time in seconds

        Returns:
            Dictionary containing optimization recommendations
        """
        try:
            # Get metric count to assess dataset size
            total_metrics = ValidationMetric.query.filter_by(metric_name=metric_name)
            if entity_type:
                total_metrics = total_metrics.filter_by(entity_type=entity_type)

            total_count = total_metrics.count()

            # Determine optimal aggregation strategy
            if total_count < 1000:
                strategy = "full_scan"
                recommended_window_size = 7
                use_indexing = False
            elif total_count < 10000:
                strategy = "sampled_aggregation"
                recommended_window_size = 14
                use_indexing = True
            else:
                strategy = "incremental_aggregation"
                recommended_window_size = 30
                use_indexing = True

            # Performance recommendations
            recommendations = {
                "dataset_size": total_count,
                "recommended_strategy": strategy,
                "recommended_window_size": recommended_window_size,
                "use_indexing": use_indexing,
                "estimated_response_time": self._estimate_response_time(
                    total_count, strategy
                ),
                "optimization_tips": self._get_optimization_tips(strategy, total_count),
            }

            return recommendations

        except Exception as e:
            self.logger.error(f"Error optimizing aggregation performance: {e}")
            return {"error": str(e)}

    def _estimate_response_time(self, dataset_size: int, strategy: str) -> float:
        """Estimate response time based on dataset size and strategy."""
        if strategy == "full_scan":
            return dataset_size * 0.001  # 1ms per record
        elif strategy == "sampled_aggregation":
            return dataset_size * 0.0001  # 0.1ms per record
        else:  # incremental_aggregation
            return dataset_size * 0.00001  # 0.01ms per record

    def _get_optimization_tips(self, strategy: str, dataset_size: int) -> List[str]:
        """Get optimization tips based on strategy and dataset size."""
        tips = []

        if strategy == "full_scan":
            tips.extend(
                [
                    "Consider adding database indexes on timestamp and entity_type",
                    "Use smaller time windows for analysis",
                    "Implement result caching for repeated queries",
                ]
            )
        elif strategy == "sampled_aggregation":
            tips.extend(
                [
                    "Use statistical sampling for large datasets",
                    "Implement progressive loading for real-time dashboards",
                    "Consider materialized views for common aggregations",
                ]
            )
        else:  # incremental_aggregation
            tips.extend(
                [
                    "Implement incremental update strategy",
                    "Use pre-aggregated summary tables",
                    "Consider time-series database optimization",
                ]
            )

        if dataset_size > 100000:
            tips.append("Consider implementing data archiving strategy")
            tips.append("Use parallel processing for large aggregations")

        return tips

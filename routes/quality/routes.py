"""
Quality Scoring Routes Module
=============================

This module provides comprehensive quality scoring and data validation functionality
for the Volunteer Management System (VMS). It handles quality metrics calculation,
validation result analysis, and data quality monitoring.

Key Features:
- Quality scoring dashboard and analytics
- Validation result filtering and analysis
- Performance metrics tracking
- Anomaly detection
- Validation data management and cleanup
- Quality settings configuration

Main Endpoints:
- GET /quality_dashboard - Quality scoring dashboard page
- GET /business_rules - Business rules documentation page
- POST /api/quality-score - Calculate quality scores for entities
- POST /api/clear-validation-data - Clear old validation data
- POST /api/run-validation - Trigger validation runs
- POST /api/run-multiple-validations - Batch validation runs
- GET /api/debug-validation-data - Debug validation data state
- GET/POST /api/quality-settings - Manage quality scoring configuration

Quality Scoring Features:
- Real-time data quality metrics calculation
- Comprehensive entity quality reports
- Validation result filtering and analysis
- Performance metrics tracking
- Anomaly detection
- Data cleanup utilities

Filtering and Analysis:
- Entity type-based filtering
- Date range filtering
- Validation type filtering
- Severity level filtering
- Comprehensive and targeted reports

Dependencies:
- Flask Blueprint for routing
- Validation models for data access
- Quality scoring services
- Database session management

Models Used:
- ValidationRun: Validation execution records
- ValidationResult: Individual validation results
- ValidationHistory: Historical validation data
- ValidationMetric: Performance metrics
"""

from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, render_template, request
from sqlalchemy import func

from models import db
from models.validation import (
    ValidationHistory,
    ValidationMetric,
    ValidationResult,
    ValidationRun,
)

# Create blueprint
quality_bp = Blueprint("quality", __name__)


@quality_bp.route("/quality_dashboard")
def quality_dashboard():
    """
    Quality scoring dashboard page.

    Provides a web interface for viewing data quality metrics, validation results,
    and quality scores for various entity types (volunteers, organizations, events, etc.).
    """
    return render_template("data_quality/quality_dashboard.html")


@quality_bp.route("/business_rules")
def business_rules():
    """
    Business rules documentation page.

    Displays the business rules and validation logic used by the quality scoring system.
    """
    return render_template("data_quality/business_rules.html")


@quality_bp.route("/api/quality-score", methods=["POST"])
def api_quality_score():
    """
    API endpoint for calculating quality scores.

    Calculates data quality metrics for entities based on validation history.
    Supports filtering by entity type, date range, validation type, and severity.

    Request Body:
        - entity_type (str): Type of entity to score (volunteer, organization, etc.)
        - days (int): Number of days to include in analysis (default: 30)
        - include_trends (bool): Include trend analysis (default: True)
        - validation_type (str, optional): Filter by validation type
        - severity_level (str, optional): Filter by severity level
        - quality_threshold (int): Minimum quality threshold (default: 80)
        - include_anomalies (bool): Include anomaly detection (default: True)

    Returns:
        JSON response with quality scores, validation results, metrics, and anomalies
    """
    try:
        data = request.get_json()
        entity_type = data.get("entity_type", "volunteer")
        days = data.get("days", 30)
        include_trends = data.get("include_trends", True)
        validation_type = data.get("validation_type")
        severity_level = data.get("severity_level")
        quality_threshold = data.get("quality_threshold", 80)
        include_anomalies = data.get("include_anomalies", True)

        # Initialize quality scoring services
        # These services provide the core quality scoring functionality
        from utils.services.quality_scoring_service import QualityScoringService
        from utils.services.score_weighting_engine import ScoreWeightingEngine
        from utils.services.threshold_manager import ThresholdManager

        quality_service = QualityScoringService()
        threshold_manager = ThresholdManager()
        weighting_engine = ScoreWeightingEngine()

        # Apply custom threshold if provided (override default of 80)
        if quality_threshold != 80:
            threshold_manager.set_entity_threshold(entity_type, quality_threshold)

        if entity_type == "all":
            # Generate comprehensive report for all entity types
            result = quality_service.calculate_comprehensive_quality_report(
                entity_types=None,  # Use default entity types
                days=days,
                include_trends=include_trends,
            )

            # Add validation results for all supported entity types
            all_validation_results = []
            for entity in [
                "volunteer",
                "organization",
                "event",
                "student",
                "teacher",
                "school",
                "district",
            ]:
                entity_results = get_filtered_validation_results(
                    entity, days, validation_type, severity_level
                )
                all_validation_results.extend(entity_results)
            result["validation_results"] = all_validation_results
        else:
            # Calculate score for specific entity type
            current_app.logger.info(
                f"Calculating quality score for entity: {entity_type}, days: {days}"
            )
            result = quality_service.calculate_entity_quality_score(
                entity_type=entity_type, days=days, include_details=True
            )
            current_app.logger.info(f"Quality service result: {result}")

            # Add detailed validation results (always include for dashboard display)
            validation_results = get_filtered_validation_results(
                entity_type, days, validation_type, severity_level
            )
            current_app.logger.info(
                f"Validation results count: {len(validation_results)}"
            )
            result["validation_results"] = validation_results

            # Add performance metrics (execution time, memory usage, etc.)
            result["performance_metrics"] = get_performance_metrics(entity_type, days)

            # Add anomaly detection if requested (statistical outliers)
            if include_anomalies:
                anomalies = get_anomalies(entity_type, days)
                result["anomalies"] = anomalies

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error in quality score API: {e}")
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/api/clear-validation-data", methods=["POST"])
def api_clear_validation_data():
    """
    API endpoint for clearing old validation data.

    Removes validation history data from the database based on age criteria.
    Useful for database maintenance and performance optimization.

    Request Body:
        - entity_type (str, optional): Specific entity type to clear, or "all"
        - older_than_days (int): Age threshold in days (default: 1)
                                 Set to 0 to clear ALL data regardless of age
        - user_id (int, optional): Filter by specific user who created the data

    Returns:
        JSON response with deletion counts and details
    """
    try:
        data = request.get_json()
        entity_type = data.get("entity_type")
        older_than_days = data.get("older_than_days", 1)
        user_id = data.get("user_id")  # Optional user ID filter

        # Log the request for debugging
        current_app.logger.info(
            f"Clear validation data request: entity_type={entity_type}, older_than_days={older_than_days}, user_id={user_id}"
        )

        # Build query filters for ValidationRun (filter by date and optional user)
        run_filters = []

        # If older_than_days is 0, clear ALL data regardless of age (DANGEROUS!)
        if older_than_days > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            run_filters.append(ValidationRun.started_at < cutoff_date)
            current_app.logger.info(
                f"Filtering by date: older than {older_than_days} days (before {cutoff_date})"
            )
        else:
            current_app.logger.info("Clearing ALL validation data regardless of age")

        if user_id:
            run_filters.append(ValidationRun.created_by == user_id)

        # Get run IDs that match the basic filters
        base_run_ids = [
            run.id for run in ValidationRun.query.filter(*run_filters).all()
        ]

        # If entity_type is specified, further filter by ValidationResult.entity_type
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
        else:
            run_ids = base_run_ids

        # Count records to be deleted for reporting purposes
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

        total_records = (
            runs_to_delete + results_to_delete + history_to_delete + metrics_to_delete
        )

        if total_records == 0:
            return jsonify(
                {
                    "success": True,
                    "message": "No old validation data found to clear",
                    "records_deleted": 0,
                }
            )

        # Delete in correct order (respecting foreign key constraints)
        # Must delete child records before parent records
        if results_to_delete > 0:
            ValidationResult.query.filter(ValidationResult.run_id.in_(run_ids)).delete(
                synchronize_session=False
            )

        if history_to_delete > 0:
            ValidationHistory.query.filter(
                ValidationHistory.run_id.in_(run_ids)
            ).delete(synchronize_session=False)

        if metrics_to_delete > 0:
            ValidationMetric.query.filter(ValidationMetric.run_id.in_(run_ids)).delete(
                synchronize_session=False
            )

        if runs_to_delete > 0:
            ValidationRun.query.filter(ValidationRun.id.in_(run_ids)).delete(
                synchronize_session=False
            )

        # Commit all changes atomically
        db.session.commit()

        current_app.logger.info(
            f"Cleared {total_records} old validation records (older than {older_than_days} days)"
        )

        return jsonify(
            {
                "success": True,
                "message": f"Successfully cleared {total_records} old validation records",
                "records_deleted": total_records,
                "details": {
                    "validation_runs": runs_to_delete,
                    "validation_results": results_to_delete,
                    "validation_history": history_to_delete,
                    "validation_metrics": metrics_to_delete,
                },
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error clearing validation data: {e}")
        return jsonify({"error": str(e)}), 500


def get_filtered_validation_results(
    entity_type, days, validation_type=None, severity_level=None
):
    """
    Get filtered validation results based on criteria.

    Retrieves validation results for a specific entity type within a time window,
    with optional filtering by validation type and severity level.

    Args:
        entity_type: Type of entity to get results for
        days: Number of days to look back
        validation_type: Optional filter by validation type
        severity_level: Optional filter by severity level

    Returns:
        List of validation result dictionaries
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        current_app.logger.info(
            f"Looking for validation results for {entity_type} in last {days} days (cutoff: {cutoff_date})"
        )

        # Get recent validation runs that completed successfully
        recent_runs = ValidationRun.query.filter(
            ValidationRun.completed_at >= cutoff_date,
            ValidationRun.status == "completed",
        ).all()

        run_ids = [run.id for run in recent_runs]
        current_app.logger.info(
            f"Found {len(run_ids)} completed validation runs: {run_ids}"
        )

        if not run_ids:
            current_app.logger.warning(
                f"No completed validation runs found in last {days} days"
            )
            return []

        # Build query with filters
        query = ValidationResult.query.filter(
            ValidationResult.run_id.in_(run_ids),
            ValidationResult.entity_type == entity_type,
        )

        if validation_type:
            query = query.filter(ValidationResult.validation_type == validation_type)

        if severity_level:
            query = query.filter(ValidationResult.severity == severity_level)

        # Limit results for performance (paginate large result sets)
        results = query.limit(100).all()
        current_app.logger.info(
            f"Found {len(results)} validation results for {entity_type}"
        )

        return [result.to_dict() for result in results]

    except Exception as e:
        current_app.logger.error(f"Error getting filtered validation results: {e}")
        return []


def get_performance_metrics(entity_type, days):
    """
    Get performance metrics for validation runs.

    Calculates average execution time, memory usage, CPU usage, and total runs
    for completed validation runs within the specified time period.

    Args:
        entity_type: Type of entity (currently unused but may be needed)
        days: Number of days to look back

    Returns:
        Dictionary with performance metrics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get aggregated performance metrics from recent runs
        metrics = (
            db.session.query(
                func.avg(ValidationRun.execution_time_seconds).label(
                    "avg_execution_time"
                ),
                func.avg(ValidationRun.memory_usage_mb).label("avg_memory_usage"),
                func.avg(ValidationRun.cpu_usage_percent).label("avg_cpu_usage"),
                func.count(ValidationRun.id).label("total_runs"),
            )
            .filter(
                ValidationRun.completed_at >= cutoff_date,
                ValidationRun.status == "completed",
            )
            .first()
        )

        return {
            "execution_time_seconds": round(metrics.avg_execution_time or 0, 2),
            "memory_usage_mb": round(metrics.avg_memory_usage or 0, 2),
            "cpu_usage_percent": round(metrics.avg_cpu_usage or 0, 2),
            "records_processed": metrics.total_runs or 0,
        }

    except Exception as e:
        current_app.logger.error(f"Error getting performance metrics: {e}")
        return {}


def get_anomalies(entity_type, days):
    """
    Get statistical anomalies for the entity type.

    Identifies validation results that deviate significantly from normal patterns,
    indicating potential data quality issues or system problems.

    Args:
        entity_type: Type of entity to analyze
        days: Number of days to look back

    Returns:
        List of anomaly dictionaries
    """
    try:
        anomalies = ValidationHistory.get_anomalies(
            entity_type=entity_type, days=days, anomaly_threshold=2.0
        )

        return [anomaly.to_dict() for anomaly in anomalies]

    except Exception as e:
        current_app.logger.error(f"Error getting anomalies: {e}")
        return []


@quality_bp.route("/api/run-validation", methods=["POST"])
def api_run_validation():
    """
    API endpoint for running validation checks to generate data.

    Triggers a comprehensive validation run for the specified entity type.
    This populates validation data that can then be analyzed via the quality dashboard.

    Request Body:
        - entity_type (str): Type of entity to validate (default: "volunteer")
        - validation_type (str): Type of validation (default: "comprehensive")

    Returns:
        JSON response with run ID, status, and total checks performed
    """
    try:
        data = request.get_json()
        entity_type = data.get("entity_type", "volunteer")
        validation_type = data.get("validation_type", "comprehensive")

        current_app.logger.info(
            f"Running validation: entity_type={entity_type}, validation_type={validation_type}"
        )

        # Import validation engine dynamically to avoid circular imports
        from utils.validation_engine import get_validation_engine

        with current_app.app_context():
            # Run comprehensive validation (all validation types)
            engine = get_validation_engine()
            run = engine.run_comprehensive_validation(
                entity_type=entity_type,
                run_type="comprehensive",
                name=f"Comprehensive Validation - {entity_type.title()}",
                user_id=None,
            )

            current_app.logger.info(
                f"Comprehensive validation completed: Run ID {run.id}"
            )

            return jsonify(
                {
                    "success": True,
                    "message": f"Comprehensive validation completed successfully",
                    "run_id": run.id,
                    "status": run.status,
                    "total_checks": run.total_checks,
                }
            )

    except Exception as e:
        current_app.logger.error(f"Error running validation: {e}")
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/api/run-multiple-validations", methods=["POST"])
def api_run_multiple_validations():
    """
    API endpoint for running validation checks for multiple entity types.

    Runs comprehensive validation across multiple entity types in a single request.
    Useful for generating quality reports for all entities at once.

    Request Body:
        - entity_types (list): List of entity types to validate (default: all)
        - validation_type (str): Type of validation (default: "comprehensive")

    Returns:
        JSON response with results for each entity type and overall success summary
    """
    try:
        data = request.get_json()
        entity_types = data.get(
            "entity_types",
            [
                "volunteer",
                "organization",
                "event",
                "student",
                "teacher",
                "school",
                "district",
            ],
        )
        validation_type = data.get("validation_type", "comprehensive")

        current_app.logger.info(
            f"Running multiple comprehensive validations: entity_types={entity_types}"
        )

        # Import validation engine dynamically to avoid circular imports
        from utils.validation_engine import get_validation_engine

        results = []

        with current_app.app_context():
            engine = get_validation_engine()

            # Process each entity type sequentially
            for entity_type in entity_types:
                try:
                    # Run comprehensive validation for this entity type
                    run = engine.run_comprehensive_validation(
                        entity_type=entity_type,
                        run_type="comprehensive",
                        name=f"Comprehensive Validation - {entity_type.title()}",
                        user_id=None,
                    )

                    results.append(
                        {
                            "entity_type": entity_type,
                            "success": True,
                            "run_id": run.id,
                            "status": run.status,
                            "total_checks": run.total_checks,
                        }
                    )

                    current_app.logger.info(
                        f"Comprehensive validation completed for {entity_type}: Run ID {run.id}"
                    )

                except Exception as e:
                    # Log but continue processing other entity types
                    current_app.logger.error(
                        f"Error running comprehensive validation for {entity_type}: {e}"
                    )
                    results.append(
                        {"entity_type": entity_type, "success": False, "error": str(e)}
                    )

        # Count successful runs for summary
        successful_runs = sum(1 for r in results if r["success"])
        total_runs = len(results)

        return jsonify(
            {
                "success": True,
                "message": f"Multiple comprehensive validations completed: {successful_runs}/{total_runs} successful",
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "results": results,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error running multiple validations: {e}")
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/api/debug-validation-data", methods=["GET"])
def api_debug_validation_data():
    """
    Debug endpoint to show current validation data in database.

    Provides diagnostic information about the current state of validation data,
    including total counts, recent runs, and entity type breakdowns.
    Useful for troubleshooting quality dashboard issues.

    Returns:
        JSON response with validation data statistics and recent activity
    """
    try:
        # Get counts of all validation data tables
        total_runs = ValidationRun.query.count()
        total_results = ValidationResult.query.count()
        total_history = ValidationHistory.query.count()
        total_metrics = ValidationMetric.query.count()

        # Get 5 most recent validation runs for inspection
        recent_runs = (
            ValidationRun.query.order_by(ValidationRun.started_at.desc()).limit(5).all()
        )
        recent_runs_data = []
        for run in recent_runs:
            recent_runs_data.append(
                {
                    "id": run.id,
                    "name": run.name,
                    "started_at": (
                        run.started_at.isoformat() if run.started_at else None
                    ),
                    "status": run.status,
                    "total_checks": run.total_checks,
                }
            )

        # Get entity type breakdown (count of validation results per entity type)
        entity_breakdown = (
            db.session.query(
                ValidationResult.entity_type, db.func.count(ValidationResult.id)
            )
            .group_by(ValidationResult.entity_type)
            .all()
        )

        entity_counts = {entity: count for entity, count in entity_breakdown}

        return jsonify(
            {
                "success": True,
                "total_counts": {
                    "validation_runs": total_runs,
                    "validation_results": total_results,
                    "validation_history": total_history,
                    "validation_metrics": total_metrics,
                },
                "recent_runs": recent_runs_data,
                "entity_breakdown": entity_counts,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error in debug validation data API: {e}")
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/api/quality-settings", methods=["GET", "POST"])
def api_quality_settings():
    """
    API endpoint for managing quality scoring settings.

    GET: Retrieves current quality scoring configuration including weights and thresholds
    POST: Updates quality scoring configuration (thresholds and weights)

    Request Body (POST):
        - thresholds (dict): Entity type -> threshold value mappings
        - weights (dict): Entity type -> weight configuration mappings

    Returns:
        JSON response with current/updated settings
    """
    try:
        from config.quality_scoring import QUALITY_THRESHOLDS, QUALITY_WEIGHTS
        from utils.services.score_weighting_engine import ScoreWeightingEngine
        from utils.services.threshold_manager import ThresholdManager

        threshold_manager = ThresholdManager()
        weighting_engine = ScoreWeightingEngine()

        if request.method == "GET":
            # Return current settings (active + defaults)
            settings = {
                "weights": weighting_engine.get_weight_summary(),
                "thresholds": threshold_manager.get_threshold_summary(),
                "default_weights": QUALITY_WEIGHTS,
                "default_thresholds": QUALITY_THRESHOLDS,
            }
            return jsonify(settings)

        elif request.method == "POST":
            # Update settings with provided values
            data = request.get_json()

            # Update thresholds (minimum quality scores per entity type)
            if "thresholds" in data:
                for entity_type, threshold in data["thresholds"].items():
                    threshold_manager.set_entity_threshold(entity_type, threshold)

            # Update weights (how different validation types contribute to scores)
            if "weights" in data:
                for entity_type, weights in data["weights"].items():
                    weighting_engine.set_entity_weight_override(entity_type, weights)

            return jsonify({"message": "Settings updated successfully"})

    except Exception as e:
        current_app.logger.error(f"Error in quality settings API: {e}")
        return jsonify({"error": str(e)}), 500

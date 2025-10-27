# app.py

import os
from datetime import datetime, timezone  # Keep this as it might be used elsewhere

from dotenv import load_dotenv

# Load environment variables from .env file FIRST, before any other imports
load_dotenv()

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from config import DevelopmentConfig, ProductionConfig
from forms import LoginForm
from models import User, db
from models.user import SecurityLevel
from routes.routes import init_routes
from utils import format_event_type_for_badge, short_date
from utils.cache_refresh_scheduler import start_cache_refresh_scheduler

app = Flask(__name__)
CORS(app)

# Load configuration based on the environment
flask_env = os.environ.get("FLASK_ENV", "development")

if flask_env == "production":
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # Redirect to 'login' view if unauthorized
login_manager.login_message_category = "info"

# Create instance directory if it doesn't exist
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Create DB tables on startup (idempotent). This will create any missing tables for new models.
with app.app_context():
    try:
        # Always call create_all; it only creates tables that don't exist
        db.create_all()
    except Exception as e:
        # Fallback/diagnostic output if something goes wrong creating tables
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"Database initialization error: {e}")
        print(f"Existing tables: {existing_tables}")


# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Add SecurityLevel to Flask's template context
@app.context_processor
def inject_security_levels():
    return {
        "SecurityLevel": SecurityLevel,
        "USER": SecurityLevel.USER,
        "SUPERVISOR": SecurityLevel.SUPERVISOR,
        "MANAGER": SecurityLevel.MANAGER,
        "ADMIN": SecurityLevel.ADMIN,
    }


# Initialize routes
init_routes(app)

app.jinja_env.filters["short_date"] = short_date
app.jinja_env.filters["event_type_badge"] = format_event_type_for_badge

# Add custom JSON filter for district scoping
import json


def from_json_filter(json_string):
    """Custom Jinja2 filter to parse JSON strings."""
    if not json_string or json_string == "None" or json_string == "null":
        return []
    try:
        if isinstance(json_string, str):
            return json.loads(json_string)
        return json_string
    except (json.JSONDecodeError, TypeError):
        return []


app.jinja_env.filters["from_json"] = from_json_filter


@app.route("/docs/<path:filename>")
def documentation(filename):
    return send_from_directory("documentation", filename)


# Quality Scoring Dashboard
@app.route("/quality_dashboard")
def quality_dashboard():
    """Quality scoring dashboard page."""
    return render_template("data_quality/quality_dashboard.html")


@app.route("/business_rules")
def business_rules():
    """Business rules documentation page."""
    return render_template("data_quality/business_rules.html")


@app.route("/api/quality-score", methods=["POST"])
def api_quality_score():
    """API endpoint for calculating quality scores."""
    try:
        data = request.get_json()
        entity_type = data.get("entity_type", "volunteer")
        days = data.get("days", 30)
        include_trends = data.get("include_trends", True)
        validation_type = data.get("validation_type")
        severity_level = data.get("severity_level")
        quality_threshold = data.get("quality_threshold", 80)
        include_anomalies = data.get("include_anomalies", True)

        # Initialize quality scoring service
        from models.validation import ValidationHistory, ValidationResult
        from utils.services.quality_scoring_service import QualityScoringService
        from utils.services.score_weighting_engine import ScoreWeightingEngine
        from utils.services.threshold_manager import ThresholdManager

        quality_service = QualityScoringService()
        threshold_manager = ThresholdManager()
        weighting_engine = ScoreWeightingEngine()

        # Apply custom threshold if provided
        if quality_threshold != 80:
            threshold_manager.set_entity_threshold(entity_type, quality_threshold)

        if entity_type == "all":
            # Generate comprehensive report
            result = quality_service.calculate_comprehensive_quality_report(
                entity_types=None,  # Use default entity types
                days=days,
                include_trends=include_trends,
            )

            # Add validation results for all entities
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
            # Calculate score for specific entity
            app.logger.info(
                f"Calculating quality score for entity: {entity_type}, days: {days}"
            )
            result = quality_service.calculate_entity_quality_score(
                entity_type=entity_type, days=days, include_details=True
            )
            app.logger.info(f"Quality service result: {result}")

            # Add detailed validation results (always include for dashboard)
            validation_results = get_filtered_validation_results(
                entity_type, days, validation_type, severity_level
            )
            app.logger.info(f"Validation results count: {len(validation_results)}")
            result["validation_results"] = validation_results

            # Add performance metrics
            result["performance_metrics"] = get_performance_metrics(entity_type, days)

            # Add anomaly detection if requested
            if include_anomalies:
                anomalies = get_anomalies(entity_type, days)
                result["anomalies"] = anomalies

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error in quality score API: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear-validation-data", methods=["POST"])
def api_clear_validation_data():
    """API endpoint for clearing old validation data."""
    try:
        data = request.get_json()
        entity_type = data.get("entity_type")
        older_than_days = data.get("older_than_days", 1)
        user_id = data.get("user_id")  # Optional user ID filter

        # Log the request for debugging
        app.logger.info(
            f"Clear validation data request: entity_type={entity_type}, older_than_days={older_than_days}, user_id={user_id}"
        )

        # Import required modules
        from datetime import datetime, timedelta

        from app import db
        from models.validation import (
            ValidationHistory,
            ValidationMetric,
            ValidationResult,
            ValidationRun,
        )

        # Build query filters for ValidationRun (only by date and user)
        run_filters = []

        # If older_than_days is 0, clear ALL data regardless of age
        if older_than_days > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            run_filters.append(ValidationRun.started_at < cutoff_date)
            app.logger.info(
                f"Filtering by date: older than {older_than_days} days (before {cutoff_date})"
            )
        else:
            app.logger.info("Clearing ALL validation data regardless of age")

        if user_id:
            run_filters.append(ValidationRun.created_by == user_id)

        # Get run IDs that match the basic filters
        base_run_ids = [
            run.id for run in ValidationRun.query.filter(*run_filters).all()
        ]

        # If entity_type is specified, filter by ValidationResult.entity_type
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

        # Count records to be deleted
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

        # Delete in correct order (respecting foreign keys)
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

        # Commit the changes
        db.session.commit()

        app.logger.info(
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
        app.logger.error(f"Error clearing validation data: {e}")
        return jsonify({"error": str(e)}), 500


def get_filtered_validation_results(
    entity_type, days, validation_type=None, severity_level=None
):
    """Get filtered validation results based on criteria."""
    try:
        from datetime import datetime, timedelta

        from models.validation import ValidationResult, ValidationRun

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        app.logger.info(
            f"Looking for validation results for {entity_type} in last {days} days (cutoff: {cutoff_date})"
        )

        # Get recent validation runs
        recent_runs = ValidationRun.query.filter(
            ValidationRun.completed_at >= cutoff_date,
            ValidationRun.status == "completed",
        ).all()

        run_ids = [run.id for run in recent_runs]
        app.logger.info(f"Found {len(run_ids)} completed validation runs: {run_ids}")

        if not run_ids:
            app.logger.warning(
                f"No completed validation runs found in last {days} days"
            )
            return []

        # Build query
        query = ValidationResult.query.filter(
            ValidationResult.run_id.in_(run_ids),
            ValidationResult.entity_type == entity_type,
        )

        if validation_type:
            query = query.filter(ValidationResult.validation_type == validation_type)

        if severity_level:
            query = query.filter(ValidationResult.severity == severity_level)

        # Limit results for performance
        results = query.limit(100).all()
        app.logger.info(f"Found {len(results)} validation results for {entity_type}")

        return [result.to_dict() for result in results]

    except Exception as e:
        app.logger.error(f"Error getting filtered validation results: {e}")
        return []


def get_performance_metrics(entity_type, days):
    """Get performance metrics for validation runs."""
    try:
        from datetime import datetime, timedelta

        from sqlalchemy import func

        from models.validation import ValidationRun

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get performance metrics from recent runs
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
        app.logger.error(f"Error getting performance metrics: {e}")
        return {}


def get_anomalies(entity_type, days):
    """Get statistical anomalies for the entity type."""
    try:
        from models.validation import ValidationHistory

        anomalies = ValidationHistory.get_anomalies(
            entity_type=entity_type, days=days, anomaly_threshold=2.0
        )

        return [anomaly.to_dict() for anomaly in anomalies]

    except Exception as e:
        app.logger.error(f"Error getting anomalies: {e}")
        return []


@app.route("/api/run-validation", methods=["POST"])
def api_run_validation():
    """API endpoint for running validation checks to generate data."""
    try:
        data = request.get_json()
        entity_type = data.get("entity_type", "volunteer")
        validation_type = data.get("validation_type", "comprehensive")

        app.logger.info(
            f"Running validation: entity_type={entity_type}, validation_type={validation_type}"
        )

        # Import validation engine
        from utils.validation_engine import get_validation_engine

        with app.app_context():
            # Run comprehensive validation (all validation types)
            engine = get_validation_engine()
            run = engine.run_comprehensive_validation(
                entity_type=entity_type,
                run_type="comprehensive",
                name=f"Comprehensive Validation - {entity_type.title()}",
                user_id=None,
            )

            app.logger.info(f"Comprehensive validation completed: Run ID {run.id}")

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
        app.logger.error(f"Error running validation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/run-multiple-validations", methods=["POST"])
def api_run_multiple_validations():
    """API endpoint for running validation checks for multiple entity types."""
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

        app.logger.info(
            f"Running multiple comprehensive validations: entity_types={entity_types}"
        )

        # Import validation engine
        from utils.validation_engine import get_validation_engine

        results = []

        with app.app_context():
            engine = get_validation_engine()

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

                    app.logger.info(
                        f"Comprehensive validation completed for {entity_type}: Run ID {run.id}"
                    )

                except Exception as e:
                    app.logger.error(
                        f"Error running comprehensive validation for {entity_type}: {e}"
                    )
                    results.append(
                        {"entity_type": entity_type, "success": False, "error": str(e)}
                    )

        # Count successful runs
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
        app.logger.error(f"Error running multiple validations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/debug-validation-data", methods=["GET"])
def api_debug_validation_data():
    """Debug endpoint to show current validation data in database."""
    try:
        from models.validation import (
            ValidationHistory,
            ValidationMetric,
            ValidationResult,
            ValidationRun,
        )

        # Get counts of all validation data
        total_runs = ValidationRun.query.count()
        total_results = ValidationResult.query.count()
        total_history = ValidationHistory.query.count()
        total_metrics = ValidationMetric.query.count()

        # Get recent runs
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

        # Get entity type breakdown
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
        app.logger.error(f"Error in debug validation data API: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/quality-settings", methods=["GET", "POST"])
def api_quality_settings():
    """API endpoint for managing quality scoring settings."""
    try:
        from config.quality_scoring import QUALITY_THRESHOLDS, QUALITY_WEIGHTS
        from utils.services.score_weighting_engine import ScoreWeightingEngine
        from utils.services.threshold_manager import ThresholdManager

        threshold_manager = ThresholdManager()
        weighting_engine = ScoreWeightingEngine()

        if request.method == "GET":
            # Return current settings
            settings = {
                "weights": weighting_engine.get_weight_summary(),
                "thresholds": threshold_manager.get_threshold_summary(),
                "default_weights": QUALITY_WEIGHTS,
                "default_thresholds": QUALITY_THRESHOLDS,
            }
            return jsonify(settings)

        elif request.method == "POST":
            # Update settings
            data = request.get_json()

            # Update thresholds
            if "thresholds" in data:
                for entity_type, threshold in data["thresholds"].items():
                    threshold_manager.set_entity_threshold(entity_type, threshold)

            # Update weights
            if "weights" in data:
                for entity_type, weights in data["weights"].items():
                    weighting_engine.set_entity_weight_override(entity_type, weights)

            return jsonify({"message": "Settings updated successfully"})

    except Exception as e:
        app.logger.error(f"Error in quality settings API: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Start cache refresh scheduler in production
    if flask_env == "production":
        try:
            start_cache_refresh_scheduler()
            app.logger.info("Cache refresh scheduler started")
        except Exception as e:
            app.logger.error(f"Failed to start cache refresh scheduler: {e}")

    # Use production-ready server configuration
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)

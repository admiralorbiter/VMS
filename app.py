# app.py

import os
from datetime import datetime, timezone  # Keep this as it might be used elsewhere

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from config import DevelopmentConfig, ProductionConfig
from forms import LoginForm
from models import User, db
from models.user import SecurityLevel
from routes.routes import init_routes
from utils import format_event_type_for_badge, short_date

# Load environment variables from .env file first
load_dotenv()

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


@app.route("/docs/<path:filename>")
def documentation(filename):
    return send_from_directory("documentation", filename)


# Quality Scoring Dashboard
@app.route("/quality_dashboard")
def quality_dashboard():
    """Quality scoring dashboard page."""
    return render_template("data_quality/quality_dashboard.html")


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
            for entity in ["volunteer", "organization", "event", "student", "teacher"]:
                entity_results = get_filtered_validation_results(
                    entity, days, validation_type, severity_level
                )
                all_validation_results.extend(entity_results)
            result["validation_results"] = all_validation_results
        else:
            # Calculate score for specific entity
            result = quality_service.calculate_entity_quality_score(
                entity_type=entity_type, days=days, include_details=True
            )

            # Add detailed validation results (always include for dashboard)
            validation_results = get_filtered_validation_results(
                entity_type, days, validation_type, severity_level
            )
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


def get_filtered_validation_results(
    entity_type, days, validation_type=None, severity_level=None
):
    """Get filtered validation results based on criteria."""
    try:
        from datetime import datetime, timedelta

        from models.validation import ValidationResult, ValidationRun

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get recent validation runs
        recent_runs = ValidationRun.query.filter(
            ValidationRun.completed_at >= cutoff_date,
            ValidationRun.status == "completed",
        ).all()

        run_ids = [run.id for run in recent_runs]

        if not run_ids:
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
    # Use production-ready server configuration
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)

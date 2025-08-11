# app.py

import os
from datetime import datetime, timezone  # Keep this as it might be used elsewhere

from dotenv import load_dotenv
from flask import Flask, send_from_directory
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
if os.environ.get("FLASK_ENV") == "production":
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


if __name__ == "__main__":
    # Use production-ready server configuration
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)

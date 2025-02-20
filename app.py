# app.py

from flask import Flask
from flask_cors import CORS
from models import db, User
from models.user import SecurityLevel
from flask_login import LoginManager
from forms import LoginForm
from routes.routes import init_routes
from config import DevelopmentConfig, ProductionConfig
from dotenv import load_dotenv
import os

# Load environment variables from .env file first
load_dotenv()

app = Flask(__name__)
CORS(app)

# Load configuration based on the environment
if os.environ.get('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Redirect to 'login' view if unauthorized
login_manager.login_message_category = 'info'

# Create instance directory if it doesn't exist
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Only create tables if they don't exist
with app.app_context():
    # Create all tables
    db.create_all()
    
    # Verify tables were created
    inspector = db.inspect(db.engine)
    expected_tables = ['event', 'event_volunteers', 'event_districts', 'event_skills', 'event_participation']
    existing_tables = inspector.get_table_names()
    
    missing_tables = [table for table in expected_tables if table not in existing_tables]
    if missing_tables:
        print(f"Warning: Missing tables detected: {missing_tables}")
        # Try to create missing tables specifically
        db.create_all()

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Add SecurityLevel to Flask's template context
@app.context_processor
def inject_security_levels():
    return {
        'SecurityLevel': SecurityLevel,
        'USER': SecurityLevel.USER,
        'SUPERVISOR': SecurityLevel.SUPERVISOR,
        'MANAGER': SecurityLevel.MANAGER,
        'ADMIN': SecurityLevel.ADMIN
    }

# Initialize routes
init_routes(app)

if __name__ == '__main__':
    # Use production-ready server configuration
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
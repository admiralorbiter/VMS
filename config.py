# config.py
import os

from dotenv import load_dotenv

# Load environment variables at config level
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Load Salesforce credentials from environment
    SF_USERNAME = os.environ.get("SF_USERNAME")
    SF_PASSWORD = os.environ.get("SF_PASSWORD")
    SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN")
    SYNC_AUTH_TOKEN = os.environ.get("SYNC_AUTH_TOKEN")
    CLIENT_PROJECTS_SHEET_ID = os.environ.get("CLIENT_PROJECTS_SHEET_ID")
    SCHOOL_MAPPING_GOOGLE_SHEET = os.environ.get("SCHOOL_MAPPING_GOOGLE_SHEET")

    # Encryption key for Google Sheets
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

    def __init__(self):
        self.validate_config()

    @classmethod
    def validate_config(cls):
        required_vars = ["SF_USERNAME", "SF_PASSWORD", "SF_SECURITY_TOKEN"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


class DevelopmentConfig(Config):
    DEBUG = False
    # Use absolute path for SQLite database with sqlite:/// protocol prefix
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "your_database.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"  # Add sqlite:/// prefix


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # Change to in-memory database
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    uri = os.environ.get("DATABASE_URL")  # Get the Heroku DATABASE_URL
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = uri

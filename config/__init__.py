# config/__init__.py
"""
Configuration package for VMS.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _normalize_sqlite_uri(uri):
    """
    Normalize SQLite URI to use absolute paths on Windows.
    Converts relative paths to absolute paths for better compatibility.
    """
    if not uri or not uri.startswith("sqlite:///"):
        return uri
    
    # Extract the path part after sqlite:///
    path = uri.replace("sqlite:///", "")
    
    # If it's a relative path, convert to absolute
    if not os.path.isabs(path):
        # Get the base directory (project root)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Convert to absolute path
        abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
        # Convert backslashes to forward slashes for SQLite URI (Windows compatibility)
        abs_path = abs_path.replace("\\", "/")
        return f"sqlite:///{abs_path}"
    
    # Already absolute, just normalize slashes
    path = path.replace("\\", "/")
    return f"sqlite:///{path}"


class Config:
    """Base configuration class."""

    # Get the absolute path to the instance directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    DEFAULT_DB_PATH = os.path.join(INSTANCE_DIR, "your_database.db")

    # Normalize the database URI to handle relative paths
    _db_uri = os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH}"
    SQLALCHEMY_DATABASE_URI = _normalize_sqlite_uri(_db_uri)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite timeout in seconds (default is 5 seconds, increase for long operations)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 20, "check_same_thread": False},
        "pool_pre_ping": True,
    }

    # Security settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = (
        os.environ.get("WTF_CSRF_SECRET_KEY") or "csrf-secret-key-change-in-production"
    )

    # Session cookie settings (env-agnostic defaults)
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "vms_session")

    # Flask-Login remember cookie settings
    REMEMBER_COOKIE_NAME = os.environ.get("REMEMBER_COOKIE_NAME", "vms_remember")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Session lifetime (seconds); default 8 hours
    PERMANENT_SESSION_LIFETIME = int(
        os.environ.get("SESSION_LIFETIME_SECONDS", 60 * 60 * 8)
    )

    # Salesforce configuration
    SF_USERNAME = os.environ.get("SF_USERNAME")
    SF_PASSWORD = os.environ.get("SF_PASSWORD")
    SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN")
    SF_DOMAIN = os.environ.get("SF_DOMAIN", "login")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    # Normalize the database URI to handle relative paths
    _db_uri = os.environ.get("DATABASE_URL") or f"sqlite:///{Config.DEFAULT_DB_PATH}"
    SQLALCHEMY_DATABASE_URI = _normalize_sqlite_uri(_db_uri)
    # Allow HTTP in local development
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    # Fallback to SQLite file if DATABASE_URL is not provided, so the app can boot
    # Normalize the database URI to handle relative paths
    _db_uri = os.environ.get("DATABASE_URL") or f"sqlite:///{Config.DEFAULT_DB_PATH}"
    SQLALCHEMY_DATABASE_URI = _normalize_sqlite_uri(_db_uri)
    # Require HTTPS in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing


# Default configuration
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}

__version__ = "1.0.0"

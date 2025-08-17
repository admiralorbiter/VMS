# config/__init__.py
"""
Configuration package for VMS.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Get the absolute path to the instance directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    DEFAULT_DB_PATH = os.path.join(INSTANCE_DIR, "your_database.db")

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = (
        os.environ.get("WTF_CSRF_SECRET_KEY") or "csrf-secret-key-change-in-production"
    )

    # Salesforce configuration
    SF_USERNAME = os.environ.get("SF_USERNAME")
    SF_PASSWORD = os.environ.get("SF_PASSWORD")
    SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN")
    SF_DOMAIN = os.environ.get("SF_DOMAIN", "login")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or f"sqlite:///{Config.DEFAULT_DB_PATH}"
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


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

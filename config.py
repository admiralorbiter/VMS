# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SF_USERNAME = os.getenv('SF_USERNAME')
    SF_PASSWORD = os.getenv('SF_PASSWORD')
    SF_SECURITY_TOKEN = os.getenv('SF_SECURITY_TOKEN')
    SYNC_AUTH_TOKEN = os.getenv('SYNC_AUTH_TOKEN')

    @classmethod
    def validate_config(cls):
        required_vars = ['SF_USERNAME', 'SF_PASSWORD', 'SF_SECURITY_TOKEN', 'SYNC_AUTH_TOKEN']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class DevelopmentConfig(Config):
    DEBUG = True
    # Use absolute path for SQLite database with sqlite:/// protocol prefix
    db_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 
        'instance', 
        'your_database.db'
    )
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'  # Add sqlite:/// prefix

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_database.db'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    uri = os.environ.get('DATABASE_URL')  # Get the Heroku DATABASE_URL
    if uri and uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = uri

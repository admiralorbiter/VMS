from __future__ import with_statement

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set SQLAlchemy URL from environment or use default
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if not db_url:
    # Fallback to default SQLite database
    db_url = "sqlite:///instance/your_database.db"

config.set_main_option("sqlalchemy.url", db_url)

# add your model's MetaData object here for 'autogenerate' support
# from yourapp import models

import os

# Add the project root to Python path for imports
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import models without initializing database connections
    # Create metadata object without database connection
    from sqlalchemy import MetaData

    from models.attendance import EventAttendanceDetail
    from models.bug_report import BugReport
    from models.class_model import Class
    from models.client_project_model import ClientProject
    from models.contact import Contact
    from models.district_model import District
    from models.event import Event
    from models.history import History
    from models.organization import Organization
    from models.pathways import Pathway
    from models.reports import (
        DistrictEngagementReport,
        DistrictYearEndReport,
        OrganizationReport,
    )
    from models.school_model import School
    from models.student import Student
    from models.teacher import Teacher
    from models.user import User
    from models.validation.metric import ValidationMetric
    from models.validation.result import ValidationResult
    from models.validation.run import ValidationRun
    from models.volunteer import Volunteer

    target_metadata = MetaData()

    # Reflect all tables from the existing database
    from sqlalchemy import create_engine

    engine = create_engine(db_url)
    target_metadata.reflect(bind=engine)

except ImportError as e:
    print(f"Error importing models: {e}")
    print("Make sure you're running alembic from the project root directory")
    sys.exit(1)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

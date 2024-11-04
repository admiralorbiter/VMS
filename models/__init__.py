from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import your models after db initialization
from .user import User
from .volunteer import Volunteer

# Export the things you want to make available when importing from models
__all__ = ['db', 'User', 'Volunteer']

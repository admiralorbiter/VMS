from enum import IntEnum
from datetime import datetime, timezone
from . import db
from flask_login import UserMixin

class SecurityLevel(IntEnum):
    USER = 0
    SUPERVISOR = 1
    MANAGER = 2
    ADMIN = 3

# User model
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    security_level = db.Column(db.Integer, default=SecurityLevel.USER, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        is_admin_value = kwargs.pop('is_admin', False)  # Extract is_admin before super().__init__
        super().__init__(**kwargs)
        if 'security_level' not in kwargs:
            self.is_admin = is_admin_value  # Use the setter to set security_level

    @property
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.security_level == SecurityLevel.ADMIN

    @is_admin.setter
    def is_admin(self, value):
        """Set admin status by updating security level"""
        self.security_level = SecurityLevel.ADMIN if value else SecurityLevel.USER

    def has_permission_level(self, required_level):
        """Check if user has required security level or higher"""
        return self.security_level >= required_level

    def can_manage_user(self, other_user):
        """Check if user can manage another user based on security level"""
        return self.security_level > other_user.security_level

    @classmethod
    def find_by_username_or_email(cls, login):
        """Find a user by either username or email"""
        return cls.query.filter(
            db.or_(
                cls.username == login,
                cls.email == login
            )
        ).first()
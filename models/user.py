from datetime import datetime, timezone
from . import db
from flask_login import UserMixin

# User model
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'is_admin' not in kwargs:
            self.is_admin = False

    @classmethod
    def find_by_username_or_email(cls, login):
        """Find a user by either username or email"""
        return cls.query.filter(
            db.or_(
                cls.username == login,
                cls.email == login
            )
        ).first()
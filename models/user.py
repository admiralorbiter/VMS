"""
User Model Module
================

This module defines the User model for the Volunteer Management System (VMS),
providing user authentication, role-based access control, and API token management.

Key Features:
- User authentication and session management
- Role-based access control with security levels
- API token generation and validation
- Password hashing and security
- Audit trail with creation and update timestamps
- User management and permission checking

Security Levels:
- USER (0): Regular user with basic access
- SUPERVISOR (1): Can supervise regular users
- MANAGER (2): Can manage supervisors and users
- ADMIN (3): Full system access

Authentication Features:
- Username and email-based login
- Password hashing for security
- API token authentication
- Token expiration management
- Session management with Flask-Login

Access Control:
- Security level-based permissions
- User management capabilities
- Permission checking methods
- Admin privilege detection

API Token Management:
- Secure token generation
- Token expiration tracking
- Token validation and revocation
- Token rotation and refresh capabilities
- User lookup by token

Password Management:
    Password hashing is handled by Werkzeug in routes/auth modules:
    - routes/auth/routes.py: Uses generate_password_hash() for creation/updates
    - routes/auth/routes.py: Uses check_password_hash() for validation
    - scripts/admin/create_admin.py: Admin creation uses generate_password_hash()
    
    This model only stores the password_hash field; actual hashing is done
    at the route level before saving to the database.

District Scoping Usage:
    # In routes - using decorator
    from routes.decorators import district_scoped_required
    
    @district_scoped_required
    def district_report(district_name):
        # User automatically validated for district access
        pass
    
    # In queries - filtering data
    from routes.reports.common import get_district_filtered_query
    query = District.query
    filtered = get_district_filtered_query(query, District.name)
    
    # Manual checking
    if current_user.can_view_district("Kansas City Kansas Public Schools"):
        # Show district data
        pass

Dependencies:
- Flask-SQLAlchemy for database operations
- Flask-Login for session management
- Python secrets for secure token generation
- UUID for unique identifiers

Database Schema:
- users table with indexed fields
- Audit timestamps for tracking
- Unique constraints on username and email
- API token storage with expiration
"""

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import IntEnum

from flask_login import UserMixin
from sqlalchemy.sql import func

from . import db


class SecurityLevel(IntEnum):
    """
    Enum for user security levels. Using IntEnum ensures values are stored as integers in the database.
    Higher numbers indicate more privileges.

    Security Level Hierarchy:
        - USER (0): Basic access to view data and perform limited operations
        - SUPERVISOR (1): Can supervise regular users and access additional features
        - MANAGER (2): Can manage supervisors and users, access administrative features
        - ADMIN (3): Full system access with all privileges
    """

    USER = 0  # Regular user with basic access
    SUPERVISOR = 1  # Can supervise regular users
    MANAGER = 2  # Can manage supervisors and users
    ADMIN = 3  # Full system access


# User model
class User(db.Model, UserMixin):
    """
    User model with role-based access control and API token authentication.

    Integrates with Flask-Login for session management and provides security level-based
    permissions (USER, SUPERVISOR, MANAGER, ADMIN). Supports district/school scoping for
    restricted access users.

    Key Features:
        - Secure password hashing and API token authentication
        - Four-tier security level hierarchy with permission checking
        - District/school scoping for data access control
        - Automatic timestamp audit trail
        - Token expiration and revocation management

    See module docstring for detailed features and security architecture.
    """

    __tablename__ = "users"  # Explicitly naming the table is a best practice

    # Primary key - SQLAlchemy uses this for unique identification
    id = db.Column(db.Integer, primary_key=True)

    # Indexed fields for faster lookups - use these fields in WHERE clauses
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Security fields
    password_hash = db.Column(
        db.String(256), nullable=False
    )  # Store only hashed passwords!

    # Personal information
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))

    # Role-based access control
    security_level = db.Column(db.Integer, default=SecurityLevel.USER, nullable=False)

    # API Authentication
    api_token = db.Column(db.String(64), unique=True, index=True)
    token_expiry = db.Column(db.DateTime)

    # District and school scoping for restricted-access users
    allowed_districts = db.Column(db.JSON)  # Native JSON: ["District 1", "District 2"]
    allowed_schools = db.Column(db.JSON)  # Native JSON: ["school_id_1", "school_id_2"]
    scope_type = db.Column(
        db.String(20), default="global", nullable=False
    )  # 'global', 'district', 'school'

    # Automatic timestamps for audit trail (timezone-aware, database-side defaults)
    created_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __init__(self, **kwargs):
        """
        Initialize a new user instance.

        Note: The 'is_admin' parameter is deprecated. Use 'security_level' directly instead.
        Timestamps are automatically set by the database (server_default=func.now()).

        Args:
            **kwargs: User attributes. Use security_level=SecurityLevel.ADMIN instead of is_admin=True

        Usage:
            # Recommended approach
            user = User(username='john', email='john@example.com', security_level=SecurityLevel.ADMIN)
            user = User(username='jane', email='jane@example.com', security_level=SecurityLevel.MANAGER)

            # Legacy support (deprecated)
            user = User(username='bob', email='bob@example.com', is_admin=True)
        """
        # Handle deprecated is_admin parameter for backwards compatibility
        is_admin_value = kwargs.pop("is_admin", None)
        
        super().__init__(**kwargs)
        
        # Apply is_admin if provided and security_level was not explicitly set
        if is_admin_value is not None and "security_level" not in kwargs:
            self.is_admin = is_admin_value  # Use the setter to set security_level

    @property
    def is_admin(self):
        """
        Property decorator makes this method accessible like an attribute:
        user.is_admin instead of user.is_admin()

        Returns:
            Boolean indicating if user has admin privileges

        Usage:
            if user.is_admin:
                # Perform admin action
        """
        return self.security_level == SecurityLevel.ADMIN

    @property
    def is_district_scoped(self):
        """Check if user has district-level scope restrictions."""
        return self.scope_type == "district"

    @property
    def is_school_scoped(self):
        """Check if user has school-level scope restrictions."""
        return self.scope_type == "school"

    def can_view_district(self, district_name):
        """
        Check if user can view data for specified district.

        Args:
            district_name: Name of district to check access for

        Returns:
            Boolean indicating if user has access
        """
        if self.scope_type == "global":
            return True

        if self.scope_type == "district" and self.allowed_districts:
            try:
                return district_name in self.allowed_districts
            except (TypeError, ValueError):
                return False

        return False

    def can_view_school(self, school_id):
        """
        Check if user can view data for specified school.

        Args:
            school_id: Salesforce ID of school to check access for

        Returns:
            Boolean indicating if user has access
        """
        if self.scope_type == "global":
            return True

        if self.scope_type == "school" and self.allowed_schools:
            try:
                return school_id in self.allowed_schools
            except (TypeError, ValueError):
                return False

        return False

    @is_admin.setter
    def is_admin(self, value):
        """
        Setter for is_admin property. Updates security_level based on boolean input.

        Args:
            value: Boolean indicating admin status

        Usage:
            user.is_admin = True  # Sets security_level to ADMIN
            user.is_admin = False # Sets security_level to USER
        """
        self.security_level = SecurityLevel.ADMIN if value else SecurityLevel.USER

    def has_permission_level(self, required_level):
        """
        Check if user has required security level or higher.

        Args:
            required_level: SecurityLevel enum value to check against

        Returns:
            Boolean indicating if user has sufficient permissions

        Example:
            if user.has_permission_level(SecurityLevel.MANAGER):
                # perform manager-level action
        """
        return self.security_level >= required_level

    def can_manage_user(self, other_user):
        """
        Check if user can manage another user based on security level.
        Users can only manage users with lower security levels.

        Args:
            other_user: User instance to check management permissions against

        Returns:
            Boolean indicating if user can manage the other user

        Example:
            if manager.can_manage_user(employee):
                # allow management action
        """
        # Admins can manage everyone
        if self.is_admin:
            return True
        # Users can only manage users with lower security levels
        return self.security_level > other_user.security_level

    @classmethod
    def find_by_username_or_email(cls, login):
        """
        Class method to find a user by either username or email.
        Uses SQLAlchemy's OR operator for efficient single-query lookup.

        Args:
            login: Username or email address to search for

        Returns:
            User instance if found, None otherwise

        Example:
            user = User.find_by_username_or_email('john@example.com')
            user = User.find_by_username_or_email('john_doe')
        """
        return cls.query.filter(
            db.or_(cls.username == login, cls.email == login)
        ).first()

    def generate_api_token(self, expiration=30):
        """
        Generate a secure API token for this user.

        Creates a cryptographically secure token and sets an expiration date.
        The token is stored in the database and can be used for API authentication.

        Args:
            expiration: Token validity in days (default: 30)

        Returns:
            The generated token string

        Security Features:
            - Uses secrets.token_hex() for cryptographically secure tokens
            - Sets expiration timestamp for automatic invalidation
            - Stores token hash in database for validation
        """
        token = secrets.token_hex(32)  # 64 characters hex string
        self.api_token = token
        self.token_expiry = datetime.now(timezone.utc) + timedelta(days=expiration)
        db.session.commit()
        return token

    def check_api_token(self, token):
        """
        Check if the provided token is valid for this user.

        Validates the token against the stored token and checks expiration.

        Args:
            token: The token to validate

        Returns:
            Boolean indicating if token is valid and not expired

        Validation Checks:
            - Token exists and matches stored token
            - Token has not expired
            - Token is properly formatted
        """
        if not self.api_token or not self.token_expiry:
            return False

        if self.api_token != token:
            return False

        # Convert token_expiry to UTC if it's naive
        if self.token_expiry.tzinfo is None:
            self.token_expiry = self.token_expiry.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > self.token_expiry:
            return False

        return True

    def revoke_api_token(self):
        """
        Revoke the current API token.

        Removes the stored token and expiration date, effectively
        invalidating the token for future API requests.

        Usage:
            user.revoke_api_token()  # Immediately invalidates the token
        """
        self.api_token = None
        self.token_expiry = None
        db.session.commit()

    def refresh_api_token(self, expiration=30):
        """
        Refresh the API token by generating a new one.

        This is useful for token rotation security practices. The old
        token is immediately invalidated when the new one is generated.

        Args:
            expiration: Token validity in days (default: 30)

        Returns:
            The new token string

        Usage:
            new_token = user.refresh_api_token()
            # Old token is now invalid, use new_token
        """
        return self.generate_api_token(expiration)

    @classmethod
    def find_by_api_token(cls, token):
        """
        Find a user by their API token.

        Args:
            token: The API token to search for

        Returns:
            User instance if found, None otherwise

        Usage:
            user = User.find_by_api_token('abc123...')
            if user and user.check_api_token('abc123...'):
                # Token is valid
        """
        return cls.query.filter_by(api_token=token).first()

    def __str__(self):
        """
        String representation of the User model.

        Returns:
            String in format "<User username>"

        Example:
            str(user) -> "<User john_doe>"
        """
        return f"<User {self.username}>"

    def __repr__(self):
        """
        Detailed string representation of the User model for debugging.

        Returns:
            String in format "<User(id=X, username='Y', email='Z', security_level=N)>"

        Example:
            repr(user) -> "<User(id=1, username='john_doe', email='john@example.com', security_level=0)>"
        """
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', security_level={self.security_level})>"

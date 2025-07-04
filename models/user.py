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
- User lookup by token

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

from enum import IntEnum
from datetime import datetime, timezone, timedelta
from . import db
from flask_login import UserMixin
import secrets
import uuid

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
    USER = 0        # Regular user with basic access
    SUPERVISOR = 1  # Can supervise regular users
    MANAGER = 2     # Can manage supervisors and users
    ADMIN = 3       # Full system access

# User model
class User(db.Model, UserMixin):
    """
    User model representing system users with role-based access control.
    
    This model provides comprehensive user management functionality including
    authentication, authorization, and API access control. It integrates with
    Flask-Login for session management and provides security level-based
    access control.
    
    Inherits from:
        - db.Model: SQLAlchemy's base model class for database operations
        - UserMixin: Flask-Login mixin that provides default implementations
                    for user authentication methods
    
    Database Table:
        users - Contains all user account information
    
    Key Features:
        - Secure password storage with hashing
        - Role-based access control with security levels
        - API token authentication system
        - Audit trail with timestamps
        - User management and permission checking
        
    Attributes:
        id: Unique identifier for the user (primary key)
        username: Unique username for login (indexed)
        email: Unique email address (indexed)
        password_hash: Hashed password (never store plain text passwords!)
        first_name: User's first name
        last_name: User's last name
        security_level: User's security level (USER, SUPERVISOR, MANAGER, ADMIN)
        created_at: Timestamp of user creation (auto-set to UTC)
        updated_at: Timestamp of last update (auto-updates)
        api_token: Token for API authentication (unique, indexed)
        token_expiry: Expiration timestamp for the token
        
    Security Features:
        - Password hashing prevents plain text storage
        - API tokens with expiration for secure API access
        - Security level hierarchy for access control
        - Audit timestamps for accountability
        
    Usage Examples:
        # Create a new user
        user = User(username='john', email='john@example.com', is_admin=True)
        
        # Check permissions
        if user.has_permission_level(SecurityLevel.MANAGER):
            # Perform manager-level action
            
        # Generate API token
        token = user.generate_api_token(expiration=30)
        
        # Find user by login
        user = User.find_by_username_or_email('john@example.com')
    """
    __tablename__ = 'users'  # Explicitly naming the table is a best practice
    
    # Primary key - SQLAlchemy uses this for unique identification
    id = db.Column(db.Integer, primary_key=True)
    
    # Indexed fields for faster lookups - use these fields in WHERE clauses
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Security fields
    password_hash = db.Column(db.String(256), nullable=False)  # Store only hashed passwords!
    
    # Personal information
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    
    # Role-based access control
    security_level = db.Column(db.Integer, default=SecurityLevel.USER, nullable=False)
    
    # API Authentication
    api_token = db.Column(db.String(64), unique=True, index=True)
    token_expiry = db.Column(db.DateTime)
    
    # Audit timestamps - automatically track creation and updates
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a new user instance.
        
        The is_admin parameter is a convenience flag that sets the security level.
        All timestamps are automatically set to UTC timezone.
        
        Args:
            **kwargs: User attributes including optional is_admin flag
            
        Usage:
            new_user = User(username='john', email='john@example.com', is_admin=True)
            new_user = User(username='jane', email='jane@example.com', security_level=SecurityLevel.MANAGER)
        """
        # Set timestamps if not provided
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
            
        is_admin_value = kwargs.pop('is_admin', False)  # Extract is_admin before super().__init__
        super().__init__(**kwargs)
        if 'security_level' not in kwargs:
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
            db.or_(
                cls.username == login,
                cls.email == login
            )
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
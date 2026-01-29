"""
Tenant Model Module
==================

This module defines the Tenant model for the District Suite multi-tenant system.
A Tenant represents an isolated district platform with its own configuration,
users, and optionally linked to an existing District entity.

Key Features:
- Multi-tenant isolation via unique slug identifiers
- JSON-based settings for feature flags and branding
- API key management for public event API
- CORS origin configuration per tenant
- Optional link to existing District for reference data

Database Table:
- tenant: Stores tenant configuration and metadata

Relationships:
- Many-to-one with District (optional link to reference data)
- Many-to-one with User (created_by audit trail)
- One-to-many with User (users assigned to this tenant)

Security Features:
- Hashed API keys (plain key shown only on generation)
- Inactive tenants return 404 on portal routes
- Feature flags control access to capabilities

Usage Examples:
    # Create a new tenant
    tenant = Tenant(
        slug='kckps',
        name='Kansas City Kansas Public Schools',
        created_by=current_user.id
    )

    # Get tenant by slug (for portal routes)
    tenant = Tenant.query.filter_by(slug='kckps', is_active=True).first()

    # Check if feature is enabled
    if tenant.is_feature_enabled('events'):
        # Show events management
"""

import hashlib
import secrets
from datetime import datetime, timezone

from models import db


class Tenant(db.Model):
    """
    Tenant model representing an isolated district platform.

    This model is the foundation of the District Suite multi-tenant system.
    Each tenant has its own configuration, feature flags, and user base.

    Database Table:
        tenant - Stores tenant configuration

    Key Features:
        - URL-safe slug for routing (/virtual/<slug>)
        - JSON settings for flexible configuration
        - API key management for public API
        - CORS configuration per tenant
        - Soft-delete via is_active flag

    Attributes:
        id: Primary key
        slug: URL-safe identifier (e.g., 'kckps'), unique
        name: Display name (e.g., 'Kansas City Kansas Public Schools')
        district_id: Optional FK to District for reference data
        is_active: Active status (inactive = 404)
        settings: JSON configuration (features, branding, portal)
        api_key_hash: Hashed API key for public event API
        api_key_created_at: When API key was last generated
        allowed_origins: CORS origins (comma-separated)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: FK to User who created tenant
    """

    __tablename__ = "tenant"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Core identification
    slug = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier used in routes",
    )
    name = db.Column(
        db.String(255), nullable=False, comment="Display name for the tenant"
    )

    # Optional link to existing District for reference data
    district_id = db.Column(
        db.Integer,
        db.ForeignKey("district.id"),
        nullable=True,
        comment="Optional FK to District for linked reference data",
    )

    # Status
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        comment="Inactive tenants cannot be accessed",
    )

    # JSON configuration
    settings = db.Column(
        db.JSON,
        default=dict,
        nullable=True,
        comment="Feature flags, branding, and portal configuration",
    )

    # API key management
    api_key_hash = db.Column(
        db.String(255), nullable=True, comment="SHA-256 hash of the API key"
    )
    api_key_created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        comment="When the API key was last generated",
    )

    # CORS configuration
    allowed_origins = db.Column(
        db.Text, nullable=True, comment="Comma-separated list of allowed CORS origins"
    )

    # Audit fields
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        comment="PrepKC admin who created the tenant",
    )

    # Relationships
    district = db.relationship(
        "District",
        backref=db.backref("tenants", lazy="dynamic"),
        foreign_keys=[district_id],
    )
    creator = db.relationship(
        "User",
        backref=db.backref("created_tenants", lazy="dynamic"),
        foreign_keys=[created_by],
    )

    # Default settings structure
    DEFAULT_SETTINGS = {
        "features": {
            "events_enabled": True,
            "volunteers_enabled": True,
            "recruitment_enabled": False,
            "prepkc_visibility_enabled": False,
        },
        "branding": {
            "primary_color": "#1976d2",
            "logo_url": None,
        },
        "portal": {
            "welcome_message": "Welcome to the District Portal",
            "teacher_login_label": "Teacher Login",
            "teacher_login_description": "Access your virtual session progress and resources",
            "staff_login_label": "District Staff Login",
            "staff_login_description": "View district-wide progress and analytics",
        },
    }

    def __init__(self, **kwargs):
        """Initialize tenant with default settings if not provided."""
        if "settings" not in kwargs or kwargs["settings"] is None:
            kwargs["settings"] = self.DEFAULT_SETTINGS.copy()
        super().__init__(**kwargs)

    def get_setting(self, *keys, default=None):
        """
        Get a nested setting value using dot-notation keys.

        Args:
            *keys: Path to the setting (e.g., 'features', 'events_enabled')
            default: Value to return if setting not found

        Returns:
            Setting value or default

        Example:
            tenant.get_setting('features', 'events_enabled')
            tenant.get_setting('branding', 'primary_color', default='#000')
        """
        value = self.settings
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
            if value is None:
                return default
        return value

    def set_setting(self, *keys, value):
        """
        Set a nested setting value.

        Args:
            *keys: Path to the setting
            value: Value to set

        Example:
            tenant.set_setting('features', 'recruitment_enabled', value=True)
        """
        if self.settings is None:
            self.settings = self.DEFAULT_SETTINGS.copy()

        current = self.settings
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def is_feature_enabled(self, feature_name):
        """
        Check if a feature is enabled for this tenant.

        Args:
            feature_name: Name of the feature (without '_enabled' suffix)

        Returns:
            Boolean indicating if feature is enabled
        """
        key = f"{feature_name}_enabled"
        return self.get_setting("features", key, default=False)

    def generate_api_key(self):
        """
        Generate a new API key for this tenant.

        Returns:
            The plain-text API key (only shown once)

        Security:
            - Generates cryptographically secure random key
            - Stores only the SHA-256 hash
            - Original key is returned but never stored
        """
        # Generate 32-byte (64 hex char) secure key
        plain_key = secrets.token_hex(32)

        # Store hash only
        self.api_key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        self.api_key_created_at = datetime.now(timezone.utc)

        return plain_key

    def validate_api_key(self, api_key):
        """
        Validate an API key against this tenant's stored hash.

        Args:
            api_key: Plain-text API key to validate

        Returns:
            Boolean indicating if key is valid
        """
        if not self.api_key_hash or not api_key:
            return False

        provided_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return secrets.compare_digest(self.api_key_hash, provided_hash)

    def revoke_api_key(self):
        """Revoke the current API key."""
        self.api_key_hash = None
        self.api_key_created_at = None

    def get_allowed_origins_list(self):
        """
        Get allowed CORS origins as a list.

        Returns:
            List of origin URLs
        """
        if not self.allowed_origins:
            return []
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    def set_allowed_origins_list(self, origins):
        """
        Set allowed CORS origins from a list.

        Args:
            origins: List of origin URLs
        """
        self.allowed_origins = ",".join(origins) if origins else None

    def get_portal_config(self):
        """
        Get configuration dict for district portal routes.

        Returns:
            Dict compatible with existing DISTRICT_PORTALS format
        """
        portal = self.get_setting("portal", default={})
        return {
            "slug": self.slug,
            "display_name": self.name,
            "short_name": self.slug.upper(),
            "welcome_message": portal.get("welcome_message", f"Welcome to {self.name}"),
            "teacher_login_label": portal.get("teacher_login_label", "Teacher Login"),
            "teacher_login_description": portal.get(
                "teacher_login_description",
                "Access your virtual session progress and resources",
            ),
            "staff_login_label": portal.get(
                "staff_login_label", "District Staff Login"
            ),
            "staff_login_description": portal.get(
                "staff_login_description", "View district-wide progress and analytics"
            ),
            "teacher_login_url": f"/virtual/{self.slug}/teacher/request-link",
            "staff_login_url": "/login",
        }

    def __repr__(self):
        """String representation for debugging."""
        return f"<Tenant {self.slug} ({self.name})>"

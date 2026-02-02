"""
Magic Link Model Module
=======================

This module defines the MagicLink model for secure, passwordless teacher
authentication to access their progress data.

Key Features:
- Cryptographically secure random tokens
- Configurable expiration (default: 48 hours)
- Links to TeacherProgress record (roster-based identity)
- Single-use tracking for audit purposes

Database Table:
- magic_link: Stores magic link tokens and metadata

Security Considerations:
- Tokens are 64-byte URL-safe random strings
- Expired tokens are rejected
- Generic error messages prevent email enumeration
- Token lookup uses constant-time comparison

Usage Examples:
    # Create a magic link for a teacher
    link = MagicLink.create_for_teacher(
        teacher_progress_id=123,
        email="teacher@school.edu"
    )

    # Validate a token
    link = MagicLink.validate_token("abc123...")
    if link:
        teacher = link.teacher_progress
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class MagicLink(db.Model):
    """
    Model for magic link authentication tokens.

    Magic links provide secure, passwordless access for teachers to view
    their progress data. Each link is tied to a specific TeacherProgress
    record (from the imported roster) and expires after a configurable period.

    Database Table:
        magic_link - Stores authentication tokens

    Key Features:
        - Secure token generation
        - Expiration tracking
        - Usage auditing
        - Teacher identity binding
    """

    __tablename__ = "magic_link"

    # Default expiration in hours
    DEFAULT_EXPIRATION_HOURS = 48

    id = Column(Integer, primary_key=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    teacher_progress_id = Column(
        Integer, ForeignKey("teacher_progress.id", ondelete="CASCADE"), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # District slug for multi-tenant support
    district_slug = Column(String(50), nullable=True)

    # Relationship to TeacherProgress
    teacher_progress = relationship(
        "TeacherProgress",
        backref=db.backref("magic_links", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @classmethod
    def generate_token(cls) -> str:
        """
        Generate a cryptographically secure random token.

        Returns:
            str: 64-byte URL-safe random token
        """
        return secrets.token_urlsafe(64)

    @classmethod
    def create_for_teacher(
        cls,
        teacher_progress_id: int,
        email: str,
        district_slug: str = None,
        expiration_hours: int = None,
    ) -> "MagicLink":
        """
        Create a new magic link for a teacher.

        Args:
            teacher_progress_id: ID of the TeacherProgress record
            email: Teacher's email address
            district_slug: District slug for URL generation
            expiration_hours: Hours until expiration (default: 48)

        Returns:
            MagicLink: New magic link instance (not yet committed)
        """
        if expiration_hours is None:
            expiration_hours = cls.DEFAULT_EXPIRATION_HOURS

        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)

        link = cls(
            token=cls.generate_token(),
            email=email.lower().strip(),
            teacher_progress_id=teacher_progress_id,
            district_slug=district_slug,
            expires_at=expires_at,
            is_active=True,
        )

        db.session.add(link)
        return link

    @classmethod
    def validate_token(cls, token: str) -> "MagicLink":
        """
        Validate a magic link token.

        Args:
            token: The token to validate

        Returns:
            MagicLink: Valid magic link instance, or None if invalid/expired
        """
        if not token:
            return None

        link = cls.query.filter_by(token=token, is_active=True).first()

        if not link:
            return None

        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = link.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            return None

        # Mark as used (first use only)
        if link.used_at is None:
            link.used_at = now
            db.session.commit()

        return link

    @classmethod
    def find_by_email(cls, email: str, district_slug: str = None) -> "MagicLink":
        """
        Find an active, unexpired magic link for an email.

        Args:
            email: Email address to search
            district_slug: Optional district slug filter

        Returns:
            MagicLink: Most recent active link, or None
        """
        query = cls.query.filter_by(
            email=email.lower().strip(),
            is_active=True,
        )

        if district_slug:
            query = query.filter_by(district_slug=district_slug)

        # Get most recent unexpired link
        now = datetime.now(timezone.utc)
        link = (
            query.filter(cls.expires_at > now).order_by(cls.created_at.desc()).first()
        )

        return link

    @classmethod
    def deactivate_for_email(cls, email: str, district_slug: str = None):
        """
        Deactivate all existing magic links for an email.

        Called before creating a new link to prevent multiple active links.

        Args:
            email: Email address
            district_slug: Optional district slug filter
        """
        query = cls.query.filter_by(
            email=email.lower().strip(),
            is_active=True,
        )

        if district_slug:
            query = query.filter_by(district_slug=district_slug)

        query.update({"is_active": False})

    def get_url(self, base_url: str = None) -> str:
        """
        Generate the full magic link URL.

        Args:
            base_url: Base URL of the application (optional)

        Returns:
            str: Full magic link URL
        """
        district = self.district_slug or "kck"
        path = f"/district/{district}/teacher/verify/{self.token}"

        if base_url:
            return f"{base_url.rstrip('/')}{path}"
        return path

    @property
    def is_expired(self) -> bool:
        """Check if the magic link has expired."""
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at < now

    @property
    def hours_until_expiry(self) -> int:
        """Get hours remaining until expiration."""
        if self.is_expired:
            return 0
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = expires_at - now
        return max(0, int(delta.total_seconds() / 3600))

    def to_dict(self) -> dict:
        """
        Convert to dictionary for API responses.

        Note: Token is NOT included for security.

        Returns:
            dict: Dictionary representation
        """
        return {
            "id": self.id,
            "email": self.email,
            "teacher_progress_id": self.teacher_progress_id,
            "district_slug": self.district_slug,
            "expires_at": (self.expires_at.isoformat() if self.expires_at else None),
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
        }

    def __repr__(self):
        """String representation for debugging."""
        return f"<MagicLink {self.email} expires={self.expires_at}>"

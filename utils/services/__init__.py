"""
Services Package
===============

This package contains service layer modules that provide business logic
and data access functionality, eliminating code duplication across routes.
"""

from .organization_service import OrganizationService

__all__ = ["OrganizationService"]

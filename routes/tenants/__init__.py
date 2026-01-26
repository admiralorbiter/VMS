"""
Tenant Management Blueprint
===========================

This module initializes the tenants blueprint for the District Suite
multi-tenant management system.
"""

from .routes import tenants_bp

__all__ = ["tenants_bp"]

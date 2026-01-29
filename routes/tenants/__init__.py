"""
Tenant Management Blueprint
===========================

This module initializes the tenants blueprint for the District Suite
multi-tenant management system.
"""

from .routes import tenants_bp
from .user_management import tenant_users_bp

__all__ = ["tenants_bp", "tenant_users_bp"]

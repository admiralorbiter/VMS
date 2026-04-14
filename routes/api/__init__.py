"""
API Routes Package

Public and authenticated API endpoints for VMS.
"""

from routes.api.public_events import public_api_bp
from routes.api.virtual_sessions import virtual_sessions_api_bp

__all__ = ["public_api_bp", "virtual_sessions_api_bp"]

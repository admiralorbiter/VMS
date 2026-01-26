"""
District Blueprint Initialization

This package contains routes for district-specific functionality.
Routes here require tenant context and are scoped to the user's tenant.
"""

from flask import Blueprint

# Create district blueprint
district_bp = Blueprint("district", __name__, url_prefix="/district")

# Import routes to register them
from routes.district import events  # noqa: F401, E402

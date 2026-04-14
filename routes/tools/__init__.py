"""
Tools Blueprint
===============

Blueprint for internal productivity tools available to all authenticated Polaris users.
"""

from flask import Blueprint

tools_bp = Blueprint("tools", __name__, url_prefix="/tools")

# Register tool routes
from routes.tools import newsletter  # noqa: F401, E402

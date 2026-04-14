"""Virtual Sessions API routes for district API (scaffold)."""

from flask import Blueprint, jsonify
from routes.api.public_events import require_api_key

virtual_sessions_api_bp = Blueprint(
    "virtual_sessions_api", __name__, url_prefix="/api/v1/district"
)


@virtual_sessions_api_bp.route(
    "/<tenant_slug>/virtual-sessions/health",
    methods=["GET"],
)
@require_api_key
def health_check(tenant_slug):
    return jsonify(
        {"success": True, "message": "Virtual Sessions API is running"}
    )

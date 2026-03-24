"""Virtual Sessions API routes for district API (scaffold)."""

from flask import Blueprint, jsonify

virtual_sessions_api_bp = Blueprint(
    "virtual_sessions_api", __name__, url_prefix="/api/v1/district"
)


@virtual_sessions_api_bp.route(
    "/<tenant_slug>/virtual-sessions/health",
    methods=["GET"],
)
def health_check(tenant_slug):
    return jsonify(
        {"success": True, "message": "Virtual Sessions API is running"}
    )

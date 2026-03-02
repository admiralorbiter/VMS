"""
Documentation Routes
====================

Blueprint for serving the MkDocs documentation site.
Extracted from app.py (TD-006).

Routes:
    - /docs/ — Documentation home page
    - /docs/<path:filename> — Documentation assets
"""

from flask import Blueprint, send_from_directory

docs_bp = Blueprint("docs", __name__)


@docs_bp.route("/docs/")
@docs_bp.route("/docs")
def documentation_index():
    """Serve the documentation home page."""
    return send_from_directory("documentation", "index.html")


@docs_bp.route("/docs/<path:filename>")
def documentation(filename):
    """Serve documentation assets."""
    # If the filename doesn't contain a dot (no extension), it's likely a
    # frontend route — let the frontend handle it by serving index.html
    if "." not in filename or filename.endswith("/"):
        return send_from_directory("documentation", "index.html")
    return send_from_directory("documentation", filename)

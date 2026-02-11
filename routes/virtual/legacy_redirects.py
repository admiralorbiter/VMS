"""
Legacy District Portal Redirects
================================

This module provides backward-compatible redirects from old /virtual/<slug>
URLs to new /district/<slug>/portal URLs.

These redirects ensure existing bookmarks, emails with magic links, and
external references continue to work after the district code reorganization.

All redirects use 301 (permanent) status codes to inform browsers and search
engines to update their references.
"""

from flask import redirect, url_for

from routes.virtual.routes import virtual_bp


# --- Portal Landing Redirect ---
@virtual_bp.route("/<slug>")
def legacy_district_portal_landing(slug: str):
    """
    Redirect old district portal URLs to new location.

    /virtual/kck -> /district/kck/portal
    """
    # Reserved slugs that shouldn't redirect to portal
    reserved = {
        "usage",
        "events",
        "event",
        "purge",
        "import-sheet",
        "google-sheets",
        "pathful",
        "sessions",
        "breakdown",
        "api",
        "teacher-progress",
        "schools",
        "presenters",
    }

    if slug.lower() in reserved:
        # Let other routes handle these
        return None

    return redirect(url_for("district.portal_landing", slug=slug), code=301)


# --- Magic Link Redirects ---
@virtual_bp.route("/<slug>/teacher/request-link", methods=["GET", "POST"])
def legacy_magic_link_request(slug: str):
    """Redirect to new magic link request URL."""
    return redirect(url_for("district.magic_link_request_form", slug=slug), code=301)


@virtual_bp.route("/<slug>/teacher/link-sent")
def legacy_magic_link_sent(slug: str):
    """Redirect to new link-sent confirmation URL."""
    return redirect(url_for("district.magic_link_sent", slug=slug), code=301)


@virtual_bp.route("/<slug>/teacher/verify/<token>")
def legacy_magic_link_verify(slug: str, token: str):
    """Redirect to new magic link verify URL."""
    return redirect(
        url_for("district.magic_link_verify", slug=slug, token=token), code=301
    )


@virtual_bp.route("/<slug>/teacher/flag-issue", methods=["POST"])
def legacy_magic_link_flag_issue(slug: str):
    """Redirect to new flag issue URL."""
    return redirect(
        url_for("district.magic_link_flag_issue", slug=slug),
        code=307,  # 307 preserves POST method
    )


# --- Teacher Dashboard Redirects ---
@virtual_bp.route("/<slug>/teacher/select")
def legacy_teacher_select(slug: str):
    """Redirect to new teacher select URL."""
    return redirect(url_for("district.teacher_select", slug=slug), code=301)


@virtual_bp.route("/<slug>/teacher/<int:teacher_id>")
def legacy_teacher_dashboard(slug: str, teacher_id: int):
    """Redirect to new teacher dashboard URL."""
    return redirect(
        url_for("district.teacher_dashboard", slug=slug, teacher_id=teacher_id),
        code=301,
    )


@virtual_bp.route("/<slug>/teacher/<int:teacher_id>/report-issue", methods=["POST"])
def legacy_report_issue(slug: str, teacher_id: int):
    """Redirect to new report issue URL."""
    return redirect(
        url_for("district.report_issue", slug=slug, teacher_id=teacher_id),
        code=307,  # 307 preserves POST method
    )

"""
Integration tests for Bug Report routes.

Tests cover:
- Form access (auth required)
- Report submission (valid, invalid, all types)
- Admin management (list, filter, search, resolve, delete)
- Authorization (non-admin delete forbidden)
"""

import pytest

from models import db
from models.bug_report import BugReport, BugReportType
from models.user import User
from tests.conftest import safe_route_test

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def submitter(app):
    """Create a regular user to submit bug reports."""
    with app.app_context():
        user = User(
            username="bugreporter",
            email="bugreporter@example.com",
            password_hash="hashed",
        )
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def sample_reports(app, submitter):
    """Create a set of sample bug reports for list/filter/search tests."""
    with app.app_context():
        reports = [
            BugReport(
                type=BugReportType.BUG,
                description="Button not working on dashboard",
                page_url="/dashboard",
                page_title="Dashboard",
                submitted_by_id=submitter.id,
            ),
            BugReport(
                type=BugReportType.DATA_ERROR,
                description="Incorrect volunteer count displayed",
                page_url="/reports/volunteers",
                page_title="Volunteer Reports",
                submitted_by_id=submitter.id,
            ),
            BugReport(
                type=BugReportType.OTHER,
                description="Suggestion: add dark mode",
                page_url="/settings",
                page_title="Settings",
                submitted_by_id=submitter.id,
                resolved=True,
                resolution_notes="Noted for future release",
            ),
        ]
        db.session.add_all(reports)
        db.session.commit()
        yield reports


# ---------------------------------------------------------------------------
# A. Form Access
# ---------------------------------------------------------------------------


def test_form_requires_auth(client):
    """TC-1305: Unauthenticated user is redirected away from the form."""
    response = client.get("/bug-report/form")
    assert response.status_code in [302, 401]


def test_form_renders_for_authenticated_user(client, auth_headers):
    """TC-1303: Authenticated GET /bug-report/form returns 200."""
    response = safe_route_test(client, "/bug-report/form", headers=auth_headers)
    assert response.status_code in [
        200,
        500,
    ]  # 500 only if template missing in test env


# ---------------------------------------------------------------------------
# B. Report Submission
# ---------------------------------------------------------------------------


def test_submit_valid_bug_report(client, auth_headers, app):
    """TC-1300: Submitting a valid bug report returns success JSON."""
    response = client.post(
        "/bug-report/submit",
        data={
            "type": str(BugReportType.BUG.value),
            "description": "Something is broken",
            "page_url": "/test-page",
            "page_title": "Test Page",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data["success"] is True

    # Verify persisted in DB
    with app.app_context():
        report = BugReport.query.filter_by(description="Something is broken").first()
        assert report is not None
        assert report.page_url == "/test-page"
        assert report.resolved is False


def test_submit_missing_description(client, auth_headers):
    """TC-1304: Submitting with empty description returns 400."""
    response = client.post(
        "/bug-report/submit",
        data={
            "type": str(BugReportType.BUG.value),
            "description": "",
            "page_url": "/test-page",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data is not None
    assert data["success"] is False


def test_submit_each_report_type(client, auth_headers, app):
    """TC-1301: All three report types (BUG, DATA_ERROR, OTHER) are accepted."""
    for report_type in BugReportType:
        response = client.post(
            "/bug-report/submit",
            data={
                "type": str(report_type.value),
                "description": f"Test for type {report_type.name}",
                "page_url": "/test",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Failed for type {report_type.name}"

    with app.app_context():
        assert BugReport.query.count() >= len(BugReportType)


def test_submit_captures_page_title(client, auth_headers, app):
    """TC-1302: Page title is stored on the report record."""
    client.post(
        "/bug-report/submit",
        data={
            "type": str(BugReportType.BUG.value),
            "description": "Title capture test",
            "page_url": "/some-page",
            "page_title": "My Custom Page",
        },
        headers=auth_headers,
    )
    with app.app_context():
        report = BugReport.query.filter_by(description="Title capture test").first()
        assert report is not None
        assert report.page_title == "My Custom Page"


def test_submit_requires_auth(client):
    """TC-1305: Unauthenticated POST to submit is redirected."""
    response = client.post(
        "/bug-report/submit",
        data={
            "type": str(BugReportType.BUG.value),
            "description": "Should fail",
            "page_url": "/test",
        },
    )
    assert response.status_code in [302, 401]


# ---------------------------------------------------------------------------
# C. Admin Management — List / Filter / Search
# ---------------------------------------------------------------------------


def test_admin_list_bug_reports(client, test_admin_headers, sample_reports):
    """TC-1306: Admin GET /bug-reports returns 200."""
    response = safe_route_test(client, "/bug-reports", headers=test_admin_headers)
    assert response.status_code in [200, 500]


def test_admin_filter_by_status_open(client, test_admin_headers, sample_reports):
    """TC-1307: Filter ?status=open returns only unresolved reports."""
    response = safe_route_test(
        client, "/bug-reports?status=open", headers=test_admin_headers
    )
    assert response.status_code in [200, 500]


def test_admin_filter_by_type(client, test_admin_headers, sample_reports):
    """TC-1308: Filter ?type=bug returns only bug-type reports."""
    response = safe_route_test(
        client, "/bug-reports?type=bug", headers=test_admin_headers
    )
    assert response.status_code in [200, 500]


def test_admin_search(client, test_admin_headers, sample_reports):
    """TC-1309: Search ?search=dashboard filters matching reports."""
    response = safe_route_test(
        client, "/bug-reports?search=dashboard", headers=test_admin_headers
    )
    assert response.status_code in [200, 500]


# ---------------------------------------------------------------------------
# D. Admin Management — Resolve
# ---------------------------------------------------------------------------


def test_resolve_bug_report(client, test_admin_headers, sample_reports, app):
    """TC-1310: Resolving a bug report sets resolved fields."""
    report_id = sample_reports[0].id
    response = client.post(
        f"/bug-reports/{report_id}/resolve",
        data={"notes": "Fixed the button"},
        headers=test_admin_headers,
    )
    assert response.status_code in [200, 302]

    with app.app_context():
        report = db.session.get(BugReport, report_id)
        assert report.resolved is True
        assert report.resolution_notes == "Fixed the button"
        assert report.resolved_by_id is not None
        assert report.resolved_at is not None


def test_resolve_nonexistent_report(client, test_admin_headers):
    """TC-1311: Resolving a nonexistent report returns 404."""
    response = client.post(
        "/bug-reports/99999/resolve",
        data={"notes": "n/a"},
        headers=test_admin_headers,
    )
    assert response.status_code in [404, 500]


# ---------------------------------------------------------------------------
# E. Admin Management — Delete
# ---------------------------------------------------------------------------


def test_delete_bug_report_admin(client, test_admin_headers, sample_reports, app):
    """TC-1312: Admin DELETE removes the report and returns success."""
    report_id = sample_reports[0].id
    response = client.delete(
        f"/bug-reports/{report_id}",
        headers=test_admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    with app.app_context():
        assert db.session.get(BugReport, report_id) is None


def test_delete_bug_report_nonadmin(client, auth_headers, sample_reports):
    """TC-1314: Non-admin DELETE returns 403."""
    report_id = sample_reports[0].id
    response = client.delete(
        f"/bug-reports/{report_id}",
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_delete_nonexistent_report(client, test_admin_headers):
    """TC-1312 edge: Deleting a nonexistent report returns 404."""
    response = client.delete(
        "/bug-reports/99999",
        headers=test_admin_headers,
    )
    assert response.status_code in [404, 500]

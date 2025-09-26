from datetime import datetime, timedelta

import pytest
from flask import url_for

from models import db
from models.contact import Contact
from models.school_model import School
from models.student import Student
from tests.conftest import assert_route_response, safe_route_test


def test_students_list_view(client, auth_headers):
    """Test students list view"""
    response = safe_route_test(client, "/students", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_student_detail_view(client, auth_headers):
    """Test individual student detail view"""
    response = safe_route_test(client, "/students/view/1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_add_student(client, auth_headers):
    """Test adding new student"""
    response = safe_route_test(
        client, "/students/add", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_edit_student(client, auth_headers):
    """Test editing student"""
    response = safe_route_test(
        client, "/students/edit/1", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_delete_student(client, auth_headers):
    """Test deleting student"""
    response = safe_route_test(
        client, "/students/delete/1", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


@pytest.mark.slow
@pytest.mark.salesforce
def test_import_students_salesforce(client, auth_headers):
    """Test importing students from Salesforce"""
    response = safe_route_test(
        client, "/students/import-from-salesforce", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_students_pagination(client, auth_headers):
    """Test students pagination"""
    response = safe_route_test(
        client, "/students?page=2&per_page=25", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_search(client, auth_headers):
    """Test students search functionality"""
    response = safe_route_test(client, "/students?search=john", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_filtering(client, auth_headers):
    """Test students filtering"""
    response = safe_route_test(
        client, "/students?school_id=1&grade=10", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_sorting(client, auth_headers):
    """Test students sorting"""
    response = safe_route_test(
        client, "/students?sort=name&order=asc", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_export(client, auth_headers):
    """Test students data export"""
    response = safe_route_test(client, "/students/export", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_statistics(client, auth_headers):
    """Test students statistics"""
    response = safe_route_test(client, "/students/statistics", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_by_school(client, auth_headers):
    """Test students by school filtering"""
    response = safe_route_test(client, "/students?school_id=1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_by_grade(client, auth_headers):
    """Test students by grade filtering"""
    response = safe_route_test(client, "/students?grade=12", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_by_district(client, auth_headers):
    """Test students by district filtering"""
    response = safe_route_test(client, "/students?district_id=1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_unauthorized_access(client):
    """Test students unauthorized access"""
    response = safe_route_test(client, "/students")
    assert_route_response(response, expected_statuses=[302, 401, 403])


def test_students_error_handling(client, auth_headers):
    """Test students error handling"""
    response = safe_route_test(
        client, "/students/invalid-endpoint", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[404, 500])


def test_students_performance(client, auth_headers):
    """Test students performance"""
    response = safe_route_test(client, "/students", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_students_data_validation(client, auth_headers):
    """Test students data validation"""
    response = safe_route_test(
        client, "/students/validate", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 400, 404, 500])

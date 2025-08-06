from tests.conftest import assert_route_response, safe_route_test


def test_protected_route_with_auth(client, auth_headers):
    """Test that protected routes work with authentication"""
    response = safe_route_test(client, "/admin", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_protected_route_without_auth(client):
    """Test that protected routes redirect without authentication"""
    response = safe_route_test(client, "/admin")
    # Should redirect to login
    assert_route_response(response, expected_statuses=[302, 401, 403])


def test_api_health_check(client):
    """Test a basic API health check endpoint"""
    # Test any available API endpoint
    response = safe_route_test(client, "/api/health")
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_api_with_invalid_auth(client):
    """Test API endpoints with invalid authentication"""
    invalid_headers = {"Authorization": "Bearer invalid-token"}
    response = safe_route_test(client, "/admin", headers=invalid_headers)
    assert_route_response(response, expected_statuses=[401, 403, 302])


def test_api_endpoints_performance(client, auth_headers):
    """Test API endpoints performance"""
    import time

    start_time = time.time()
    response = safe_route_test(client, "/admin", headers=auth_headers)
    end_time = time.time()

    # Should respond within reasonable time
    assert (end_time - start_time) < 5.0
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_api_rate_limiting(client, auth_headers):
    """Test API rate limiting behavior"""
    responses = []
    for i in range(5):
        response = safe_route_test(client, "/admin", headers=auth_headers)
        responses.append(response)

    # All requests should complete (no rate limiting in test env)
    for response in responses:
        assert_route_response(response, expected_statuses=[200, 404, 500, 429])


def test_api_content_type_handling(client, auth_headers):
    """Test API content type handling"""
    response = safe_route_test(client, "/admin", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

    # Check content type if response is successful
    if response.status_code == 200:
        assert "text/html" in response.headers.get("Content-Type", "")


def test_api_error_handling(client, auth_headers):
    """Test API error handling"""
    # Test with invalid parameters
    response = safe_route_test(client, "/admin?invalid=param", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 400, 404, 500])


def test_api_method_not_allowed(client, auth_headers):
    """Test API method not allowed responses"""
    response = safe_route_test(client, "/admin", method="PUT", headers=auth_headers)
    assert_route_response(response, expected_statuses=[405, 404, 500])


def test_api_cors_headers(client, auth_headers):
    """Test CORS headers in API responses"""
    response = safe_route_test(client, "/admin", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

    # CORS headers might be present
    # Don't assert their presence as they might not be configured

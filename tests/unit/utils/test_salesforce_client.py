"""
Unit tests for utils/salesforce_client.py focusing on connection, counts, samples, and health.
"""

import types

import pytest

from utils.salesforce_client import SalesforceClient, get_entity_count


class DummySF:
    def __init__(self, result_total=123, records=None):
        self._total = result_total
        self._records = records or [
            {"Id": "001", "attributes": {}},
            {"Id": "002", "attributes": {}},
        ]

    def query(self, q):
        # Return minimal structure
        return {"totalSize": self._total, "records": self._records}

    def describe(self):
        return {"sobjects": []}


@pytest.fixture
def client(monkeypatch):
    c = SalesforceClient(username="u", password="p", security_token="t")
    # Avoid sleeping / rate limit
    monkeypatch.setattr(c, "_rate_limit", lambda: None)
    # Force connection
    c.sf = DummySF()
    return c


def test_get_counts_success(client):
    assert isinstance(client.get_volunteer_count(), int)
    assert isinstance(client.get_organization_count(), int)
    assert isinstance(client.get_event_count(), int)
    assert isinstance(client.get_student_count(), int)
    assert isinstance(client.get_teacher_count(), int)


def test_get_samples_strip_attributes(client):
    # Ensure attributes are removed in sample methods
    orgs = client.get_organization_sample(limit=2)
    assert all("attributes" not in r for r in orgs)


def test_get_health_status_connected_and_not(client):
    status = client.get_health_status()
    assert status["salesforce_available"] in (True, False)
    assert isinstance(status["connected"], bool)

    # Without connection
    client.sf = None
    status2 = client.get_health_status()
    assert status2["connected"] is False


def test_get_entity_count_dispatch(monkeypatch):
    def factory():
        mocked = SalesforceClient(username="u", password="p", security_token="t")
        mocked.sf = DummySF(result_total=5)
        # Prevent any real connection attempts
        mocked._ensure_connection = lambda: None
        mocked._rate_limit = lambda: None
        # Prevent close from clearing sf
        mocked.close = lambda: None
        return mocked

    monkeypatch.setattr(
        "utils.salesforce_client.get_salesforce_client", lambda: factory()
    )

    assert get_entity_count("volunteer") == 5
    assert get_entity_count("organization") == 5
    assert get_entity_count("event") == 5

    with pytest.raises(ValueError):
        get_entity_count("unknown")

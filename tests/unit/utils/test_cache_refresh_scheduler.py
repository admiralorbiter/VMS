"""
Unit tests for utils/cache_refresh_scheduler.py focusing on controls and status.
"""

import types

import pytest

from utils.cache_refresh_scheduler import (
    CacheRefreshScheduler,
    get_cache_status,
    get_scheduler,
    refresh_all_caches,
    refresh_specific_cache,
)


class DummyThread:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True  # do not run target

    def join(self, timeout=None):
        return


def test_start_stop_idempotency(monkeypatch):
    scheduler = CacheRefreshScheduler(refresh_interval_hours=24)

    # Avoid starting a real thread
    import threading

    monkeypatch.setattr(threading, "Thread", DummyThread)

    scheduler.start()
    assert scheduler.is_running is True
    # Second start is a no-op
    scheduler.start()
    assert scheduler.is_running is True

    scheduler.stop()
    assert scheduler.is_running is False
    # Second stop should not fail
    scheduler.stop()
    assert scheduler.is_running is False


def test_refresh_all_and_specific_dispatch(monkeypatch):
    scheduler = CacheRefreshScheduler()

    calls = {
        "district": 0,
        "organization": 0,
        "virtual_session": 0,
        "volunteer": 0,
        "recruitment": 0,
    }

    monkeypatch.setattr(
        scheduler,
        "_refresh_district_caches",
        lambda: calls.__setitem__("district", calls["district"] + 1),
    )
    monkeypatch.setattr(
        scheduler,
        "_refresh_organization_caches",
        lambda: calls.__setitem__("organization", calls["organization"] + 1),
    )
    monkeypatch.setattr(
        scheduler,
        "_refresh_virtual_session_caches",
        lambda: calls.__setitem__("virtual_session", calls["virtual_session"] + 1),
    )
    monkeypatch.setattr(
        scheduler,
        "_refresh_volunteer_caches",
        lambda: calls.__setitem__("volunteer", calls["volunteer"] + 1),
    )
    monkeypatch.setattr(
        scheduler,
        "_refresh_recruitment_caches",
        lambda: calls.__setitem__("recruitment", calls["recruitment"] + 1),
    )

    # Ensure global get_scheduler returns our instance
    monkeypatch.setattr(
        "utils.cache_refresh_scheduler.get_scheduler", lambda: scheduler
    )

    # Refresh all
    scheduler._refresh_all_caches()
    assert all(v == 1 for v in calls.values())

    # Refresh specific via module function
    for key in list(calls.keys()):
        refresh_specific_cache(key)
        assert calls[key] == 2


def test_refresh_specific_invalid_type_raises(monkeypatch):
    scheduler = CacheRefreshScheduler()

    # Ensure global get_scheduler returns our instance
    monkeypatch.setattr(
        "utils.cache_refresh_scheduler.get_scheduler", lambda: scheduler
    )

    with pytest.raises(ValueError):
        refresh_specific_cache("unknown")


def test_status_payload(monkeypatch):
    scheduler = CacheRefreshScheduler()
    # Ensure global get_scheduler returns our instance
    monkeypatch.setattr(
        "utils.cache_refresh_scheduler.get_scheduler", lambda: scheduler
    )

    status = get_cache_status()
    assert set(
        ["is_running", "refresh_interval_hours", "last_refresh", "stats"]
    ) <= set(status.keys())

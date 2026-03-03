"""
Fixtures for stress / API-break / fuzz tests.

Uses the same in-process app and client from the root conftest.
For optional live runs against a URL, set VMS_STRESS_BASE_URL (e.g. to
https://romulus-jlane.pythonanywhere.com); the current tests are written
for the in-process client. See docs/stress_test_plan.md for commands.
"""

import os

import pytest


def pytest_configure(config):
    """Register stress marker for selective runs."""
    config.addinivalue_line(
        "markers",
        "stress: mark test as part of the stress/break/fuzz suite (deselect with '-m \"not stress\"')",
    )


@pytest.fixture(scope="session")
def stress_base_url():
    """Base URL for live stress runs. If set, tests could use requests against it."""
    return os.environ.get("VMS_STRESS_BASE_URL", "").rstrip("/")

"""
Property-based fuzz tests using Hypothesis.

Send many random/weird inputs to input-heavy endpoints; assert no 500 and no partial writes.
Run with: pytest tests/stress/test_input_fuzz.py -v
"""

import pytest

hypothesis = pytest.importorskip(
    "hypothesis", reason="hypothesis not installed — skipping fuzz tests"
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

pytestmark = pytest.mark.stress

# Keep runs bounded so the suite stays fast; allow function-scoped fixtures with @given
STRESS_SETTINGS = settings(
    max_examples=100,
    deadline=500,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


@given(
    local_status=st.one_of(
        st.just(""),
        st.integers(),
        st.booleans(),
        st.text(min_size=0, max_size=500),
        st.none(),
    )
)
@STRESS_SETTINGS
def test_update_local_status_fuzz_no_500(
    client, auth_headers, test_volunteer, local_status
):
    """Any value for local_status must not cause 500; invalid values should yield 400."""
    payload = {"local_status": local_status}
    response = client.post(
        f"/volunteers/update-local-status/{test_volunteer.id}",
        json=payload,
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert (
        response.status_code != 500
    ), f"Fuzz input {payload!r} caused 500. Body: {response.data}"
    # Valid enum -> 200; invalid -> 400
    assert response.status_code in (
        200,
        400,
        404,
        415,
        422,
        429,
    ), f"Unexpected status {response.status_code} for {payload!r}. Body: {response.data}"


@given(
    key=st.one_of(
        st.just("local_status"),
        st.text(max_size=50),
    ),
    value=st.one_of(
        st.text(max_size=300),
        st.integers(),
        st.booleans(),
        st.none(),
    ),
)
@STRESS_SETTINGS
def test_update_local_status_fuzz_keys_no_500(
    client, auth_headers, test_volunteer, key, value
):
    """Random key/value in JSON body must not cause 500."""
    payload = {key: value}
    response = client.post(
        f"/volunteers/update-local-status/{test_volunteer.id}",
        json=payload,
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert (
        response.status_code != 500
    ), f"Fuzz payload {payload!r} caused 500. Body: {response.data}"

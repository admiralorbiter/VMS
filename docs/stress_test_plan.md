# VMS Stress Test Plan

## 1. Scope

- **In scope:** Local app (`http://127.0.0.1:5050`) and approved test-production (staging) URL only.
- **Out of scope:** Production environment, real user data.
- **Tools:** Locust (load testing), pytest + requests (API break tests), Hypothesis (property-based/input fuzzing).

## 2. Test Scenarios

| Scenario | Purpose |
|----------|---------|
| **Baseline** | Low load (e.g. 1–5 users) for a few minutes; establish normal RPS, latency, error rate. |
| **Ramp** | Gradually increase concurrency (e.g. 5 → 10 → 25 → 50) to find breaking point or unacceptable latency. |
| **Soak** | Moderate load for 1–2 hours; check for memory growth, connection leaks, degradation over time. |
| **Break-the-app inputs** | Very long strings, unicode, invalid enums, weird dates; expect 4xx validation, not 500s. |
| **Data volume** | With large synthetic dataset: list/search/filter/pagination and export endpoints. |

## 3. How to Run Tests

### App and data

- **Start the app:** `python app.py` (listens on port 5050).
- **Populate data (optional):** `python scripts/generate_synthetic_data.py --size medium` (or `large` for volume tests).

### Locust

- **With UI:** `locust -f locustfile.py --host=http://127.0.0.1:5050`  
  Then open http://localhost:8089, set users and spawn rate, click "Start swarming."
- **Headless:** `locust -f locustfile.py --host=http://127.0.0.1:5050 --headless -u 10 -r 2 -t 1m`
- **Staging:** `locust -f locustfile.py --host=https://romulus-jlane.pythonanywhere.com`

Use two terminals: one for the app, one for Locust.

### Pytest stress suite (API break + Hypothesis fuzz)

- **Local (in-process, no server):**  
  `pytest tests/stress/ -v`
- **Run only API-break tests:**  
  `pytest tests/stress/test_api_break.py -v`
- **Run only Hypothesis fuzz tests:**  
  `pytest tests/stress/test_input_fuzz.py -v`
- **Exclude stress tests from normal runs:**  
  `pytest -m "not stress"`

These tests use the same in-process app as the rest of the test suite. For optional live runs against a running server or staging, set `VMS_STRESS_BASE_URL` (e.g. `http://127.0.0.1:5050` or `https://romulus-jlane.pythonanywhere.com`); the current tests are written for the in-process client.

## 4. Expected Behavior / Success Criteria

- Under low load: most requests succeed; document actual failure rate and cause (e.g. 429 from rate limiting).
- When rate limiting is active: 429 responses are expected from a single IP under load; note this in results.
- No unhandled 500s or crashes under baseline load; any 500s should be recorded as findings with repro steps.

## 5. Safe Stop Conditions

Stop the test if:

- Sustained high 5xx error rate (e.g. >5%).
- App crash, DB lock, or timeouts.
- Runaway CPU or memory (if observable).

## 6. What to Record

For each run: date, environment (local/staging), scenario name, concurrency/duration, requests/sec, failure rate, cause of failures (e.g. 429), and response time percentiles (median, p95). See `docs/stress_test_results.md` for the results template.

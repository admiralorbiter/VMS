# VMS Stress Test Results

## 1. Environment

- **Date of run:** 2026-02-24 (baseline: 5 users, spawn rate 1, 5 min).
- **App:** Local, http://127.0.0.1:5050.
- **Data:** Synthetic data (generator available; size/seed as used for run).
- **Tool:** Locust 2.17.0, `locustfile.py`.

---

## 2. Baseline Run (Low Load)

- **Scenario:** 5 users, spawn rate 1, 5 minutes. Mixed GETs to /, /volunteers, /events, /teachers, /students, /organizations.
- **Tool:** Locust with web UI; host http://127.0.0.1:5050.

### Results

| Metric | Value |
|--------|--------|
| Total requests | 844 |
| RPS | ~2.6 |
| Failure rate | 100% (844 failures) |
| Cause of failures | 429 Too Many Requests (rate limiting) |
| Median response (reported) | 5 ms |
| 99%ile response | ≤ 19 ms |

### Per-endpoint (Locust Statistics)

| Type | Name | # Requests | # Fails | Median (ms) | 90%ile (ms) | 99%ile (ms) | Avg (ms) | Min (ms) | Max (ms) |
|------|------|------------|---------|-------------|-------------|-------------|----------|----------|----------|
| GET | / | 241 | 241 | 4 | 5 | 8 | 5 | 3 | 19 |
| GET | /events | 154 | 154 | 5 | 6 | 7 | 5 | 3 | 8 |
| GET | /organizations | 98 | 98 | 5 | 7 | 10 | 5 | 4 | 10 |
| GET | /students | 93 | 93 | 5 | 8 | 11 | 5 | 3 | 11 |
| GET | /teachers | 116 | 116 | 5 | 6 | 7 | 5 | 3 | 9 |
| GET | /volunteers | 142 | 142 | 5 | 6 | 7 | 5 | 3 | 17 |
| **Aggregated** | | **844** | **844** | **5** | **6** | **10** | **5** | **3** | **19** |

### Failures

All 844 failures: 429 Too Many Requests (rate limiting) across the same endpoints as above.

### Conclusion

Under 5 users for 5 minutes, every request was rate-limited (429). RPS stayed ~2.6; reported response times (median 5 ms, max 19 ms) reflect the 429 response. The app is not overloaded—the limiter is capping traffic from a single IP. For baseline performance without rate limiting, limits would need to be relaxed in a dev/test environment.

---

## 3. Other Runs

### Run 2 (10 users, 5 min)

- **Scenario:** 10 users, spawn rate 1, 5 minutes. Mixed GETs to /, /volunteers, /events, /teachers, /students, /organizations.
- **Tool:** Locust with web UI; host http://127.0.0.1:5050.

#### Results

| Metric | Value |
|--------|--------|
| Total requests | 1,536 |
| RPS | ~5.2 |
| Failure rate | 100% (1,536 failures) |
| Cause of failures | 429 Too Many Requests (rate limiting) |
| Median response (reported) | 4 ms |
| 99%ile response | ≤ 21 ms |

#### Per-endpoint (Locust Statistics)

| Type | Name | # Requests | # Fails | Median (ms) | 90%ile (ms) | 99%ile (ms) | Avg (ms) | Min (ms) | Max (ms) |
|------|------|------------|---------|-------------|-------------|-------------|----------|----------|----------|
| GET | / | 438 | 438 | 4 | 5 | 6 | 4 | 3 | 21 |
| GET | /events | 273 | 273 | 4 | 5 | 6 | 4 | 3 | 17 |
| GET | /organizations | 163 | 163 | 4 | 5 | 6 | 4 | 3 | 7 |
| GET | /students | 196 | 196 | 4 | 5 | 8 | 4 | 3 | 10 |
| GET | /teachers | 190 | 190 | 4 | 5 | 17 | 4 | 3 | 20 |
| GET | /volunteers | 276 | 276 | 4 | 5 | 6 | 4 | 2 | 8 |
| **Aggregated** | | **1,536** | **1,536** | **4** | **5** | **6** | **4** | **2** | **21** |

#### Failures

All 1,536 failures: 429 Too Many Requests (rate limiting) across the same endpoints as above.

#### Conclusion

At 10 users for 5 minutes, every request was rate-limited (429). RPS ~5.2 (about 2× the 5-user baseline). Reported response times (median 4 ms, max 21 ms) reflect the 429 response. Same behavior as baseline: limiter caps traffic from a single IP.

### Run 3 (25 users, 5 min)

- **Scenario:** 25 users, spawn rate 1, 5 minutes. Mixed GETs to /, /volunteers, /events, /teachers, /students, /organizations.
- **Tool:** Locust with web UI; host http://127.0.0.1:5050.

#### Results

| Metric | Value |
|--------|--------|
| Total requests | 3,649 |
| RPS | ~12.6 |
| Failure rate | 100% (3,649 failures) |
| Cause of failures | 429 Too Many Requests (rate limiting) |
| Median response (reported) | 4 ms |
| 99%ile response | ≤ 29 ms |

#### Per-endpoint (Locust Statistics)

| Type | Name | # Requests | # Fails | Median (ms) | 90%ile (ms) | 99%ile (ms) | Avg (ms) | Min (ms) | Max (ms) |
|------|------|------------|---------|-------------|-------------|-------------|----------|----------|----------|
| GET | / | 1,057 | 1,057 | 4 | 6 | 7 | 5 | 3 | 18 |
| GET | /events | 667 | 667 | 4 | 6 | 8 | 5 | 3 | 29 |
| GET | /organizations | 408 | 408 | 4 | 6 | 8 | 5 | 3 | 19 |
| GET | /students | 436 | 436 | 4 | 6 | 7 | 5 | 3 | 12 |
| GET | /teachers | 407 | 407 | 4 | 6 | 8 | 5 | 3 | 18 |
| GET | /volunteers | 674 | 674 | 4 | 6 | 8 | 5 | 3 | 16 |
| **Aggregated** | | **3,649** | **3,649** | **4** | **6** | **8** | **5** | **3** | **29** |

#### Failures

All 3,649 failures: 429 Too Many Requests (rate limiting) across the same endpoints as above.

#### Conclusion

At 25 users for 5 minutes, every request was rate-limited (429). RPS ~12.6 (about 2.4× Run 2). Reported response times (median 4 ms, max 29 ms) reflect the 429 response. Same behavior: limiter caps traffic from a single IP.

### Run 4 (50 users, 5 min)

- **Scenario:** 50 users, spawn rate 1, 5 minutes. Mixed GETs to /, /volunteers, /events, /teachers, /students, /organizations.
- **Tool:** Locust with web UI; host http://127.0.0.1:5050.

#### Results

| Metric | Value |
|--------|--------|
| Total requests | 6,941 |
| RPS | ~24.9 |
| Failure rate | 100% (6,941 failures) |
| Cause of failures | 429 Too Many Requests (rate limiting) |
| Median response (reported) | 4 ms |
| 99%ile response | ≤ 26 ms |

#### Per-endpoint (Locust Statistics)

| Type | Name | # Requests | # Fails | Median (ms) | 90%ile (ms) | 99%ile (ms) | Avg (ms) | Min (ms) | Max (ms) |
|------|------|------------|---------|-------------|-------------|-------------|----------|----------|----------|
| GET | / | 2,038 | 2,038 | 4 | 6 | 9 | 5 | 2 | 24 |
| GET | /events | 1,254 | 1,254 | 4 | 6 | 10 | 5 | 3 | 26 |
| GET | /organizations | 805 | 805 | 4 | 6 | 8 | 5 | 2 | 15 |
| GET | /students | 781 | 781 | 4 | 6 | 10 | 5 | 2 | 18 |
| GET | /teachers | 815 | 815 | 4 | 6 | 11 | 5 | 2 | 21 |
| GET | /volunteers | 1,248 | 1,248 | 4 | 6 | 10 | 5 | 2 | 18 |
| **Aggregated** | | **6,941** | **6,941** | **4** | **6** | **10** | **5** | **2** | **26** |

#### Failures

All 6,941 failures: 429 Too Many Requests (rate limiting) across the same endpoints as above.

#### Conclusion

At 50 users for 5 minutes, every request was rate-limited (429). RPS ~24.9 (about 2× Run 3). Reported response times (median 4 ms, max 26 ms) reflect the 429 response. Ramp complete (5 → 10 → 25 → 50 users): rate limiter caps traffic from a single IP at all levels; no server overload observed.

### Soak Run (10 users, 1 hr)

- **Scenario:** 10 users, spawn rate 1, 1 hour. Mixed GETs to /, /volunteers, /events, /teachers, /students, /organizations.
- **Tool:** Locust with web UI; host http://127.0.0.1:5050.

#### Results

| Metric | Value |
|--------|--------|
| Total requests | 17,399 |
| RPS | ~5.2 |
| Failure rate | ~99% (17,201 failures) |
| Cause of failures | 429 Too Many Requests (rate limiting) |
| Median response (reported) | 5 ms |
| 99%ile response | 10 ms (aggregated); max 180 ms (single outlier) |

#### Per-endpoint (Locust Statistics)

| Type | Name | # Requests | # Fails | Median (ms) | 90%ile (ms) | 99%ile (ms) | Avg (ms) | Min (ms) | Max (ms) |
|------|------|------------|---------|-------------|-------------|-------------|----------|----------|----------|
| GET | / | 5,158 | 5,060 | 4 | 6 | 8 | 5 | 2 | 180 |
| GET | /events | 3,106 | 3,084 | 5 | 6 | 10 | 5 | 3 | 159 |
| GET | /organizations | 2,057 | 2,041 | 5 | 6 | 10 | 5 | 3 | 162 |
| GET | /students | 2,012 | 1,988 | 5 | 6 | 10 | 5 | 3 | 132 |
| GET | /teachers | 2,058 | 2,041 | 5 | 6 | 10 | 5 | 3 | 48 |
| GET | /volunteers | 3,008 | 2,987 | 5 | 6 | 10 | 5 | 3 | 137 |
| **Aggregated** | | **17,399** | **17,201** | **5** | **6** | **10** | **5** | **2** | **180** |

#### Failures

17,201 failures: 429 Too Many Requests (rate limiting) across the same endpoints. ~198 requests succeeded.

#### Conclusion

Sustained load for 1 hour at 10 users. RPS stable at ~5.2; ~99% of requests rate-limited (429). One response reached 180 ms (outlier); median remained 5 ms. No app crash or observable degradation over time.

### Staging Run (10 users, 5 min)

- **Scenario:** 10 users, spawn rate 1, 5 minutes. Target: **staging** (https://romulus-jlane.pythonanywhere.com). Mixed GETs to /, /volunteers, /events, /teachers, /students, /organizations.
- **Tool:** Locust with web UI; host https://romulus-jlane.pythonanywhere.com.

#### Results

| Metric | Value |
|--------|--------|
| Total requests | 1,512 |
| RPS | ~4.8 |
| Failure rate | ~87% (1,312 failures) |
| Cause of failures | Mostly 429 (rate limiting); 2× 502 Bad Gateway (see F-2) |
| Median response (reported) | 93 ms |
| 99%ile response | 300 ms (aggregated); max 19,430 ms (outlier) |

#### Per-endpoint (Locust Statistics)

| Type | Name | # Requests | # Fails | Median (ms) | 90%ile (ms) | 99%ile (ms) | Avg (ms) | Min (ms) | Max (ms) |
|------|------|------------|---------|-------------|-------------|-------------|----------|----------|----------|
| GET | / | 431 | 331 | 74 | 140 | 270 | 217 | 39 | 18,180 |
| GET | /events | 303 | 271 | 93 | 160 | 260 | 257 | 45 | 19,430 |
| GET | /organizations | 159 | 143 | 120 | 220 | 260 | 133 | 48 | 269 |
| GET | /students | 185 | 170 | 110 | 210 | 330 | 128 | 46 | 619 |
| GET | /teachers | 183 | 167 | 110 | 230 | 11,000 | 248 | 44 | 11,439 |
| GET | /volunteers | 251 | 230 | 100 | 190 | 280 | 173 | 46 | 14,388 |
| **Aggregated** | | **1,512** | **1,312** | **93** | **190** | **300** | **202** | **39** | **19,430** |

#### Failures

1,310× 429 Too Many Requests; 1× 502 on /students, 1× 502 on /teachers (see F-2).

#### Conclusion

Staging under same load (10 users, 5 min) shows much higher latency than local (median 93 ms vs ~5 ms) and large outliers (max 19+ s). Same 429 rate-limiting pattern; in addition, 2× 502 Bad Gateway under load. Staging environment (e.g. proxy, worker limits) may be the cause.

*(Add more runs above or below using the same format.)*

### Pytest stress suite (break/fuzz)

- **Run:** `pytest tests/stress/ -v` (in-process). **Result:** 12 passed (API break + Hypothesis fuzz). Suite executed and green; no failures.

---

## 4. Summary: top bottlenecks and crash/500 causes

### Top 5 bottlenecks (identified so far)

1. **Rate limiter per IP (429)** — Caps throughput from a single source; all Locust traffic from one machine is rate-limited (F-1).
2. **Staging 502 under load** — Two 502s on GET /students and GET /teachers on staging (F-2).
3. **Staging latency spikes** — Large outliers (e.g. 19+ s) on staging vs. local.
4. **Staging baseline latency** — Median ~93 ms vs. ~5 ms local (proxy/worker environment).
5. **TBD** — e.g. SQLite contention under heavy write load if observed.

### Top 5 crash/500 causes (identified so far)

1. **update_local_status: missing body or wrong Content-Type** → 500 (F-3).
2. **update_local_status: malformed JSON** → 500 (F-4).
3. **Staging 502 (proxy/worker)** — Counted as crash-like (F-2).
4. No other 500s observed in Locust or stress suite.
5. **TBD.**

---

## 5. Findings / Bug List

### F-1: 429 Too Many Requests under load from single IP

| Field | Value |
|-------|--------|
| **What** | Many requests return HTTP 429 (TOO MANY REQUESTS). |
| **When** | Locust with multiple simulated users from one machine (single IP). |
| **Where** | All endpoints: /, /volunteers, /events, /teachers, /students, /organizations. |
| **Why** | Rate limiter (e.g. Flask-Limiter) applied per IP; Locust traffic comes from one IP. |
| **Severity** | Low (by design). |
| **Repro** | 1) Start app: `python app.py`. 2) Start Locust: `locust -f locustfile.py --host=http://127.0.0.1:5050`. 3) Open http://localhost:8089, set users (e.g. 5), spawn rate 1, Start swarming. 4) Check Failures tab for 429. |

**Log snippet (app terminal):**
```
[2026-02-24 02:30:12,359] WARNING in rate_limiter: Rate limit exceeded: 127.0.0.1 - /login
127.0.0.1 - - [24/Feb/2026 02:30:12] "GET /login?next=/events HTTP/1.1" 429 -
127.0.0.1 - - [24/Feb/2026 02:30:12] "GET /organizations HTTP/1.1" 302 -
[2026-02-24 02:30:13,194] WARNING in rate_limiter: Rate limit exceeded: 127.0.0.1 - /
127.0.0.1 - - [24/Feb/2026 02:30:13] "GET / HTTP/1.1" 429 -
```

### F-2: 502 Bad Gateway on staging under load

| Field | Value |
|-------|--------|
| **What** | Two requests returned HTTP 502 Bad Gateway (1× GET /students, 1× GET /teachers). |
| **When** | Locust against staging, 10 users, spawn rate 1, 5 minutes. |
| **Where** | Staging only: https://romulus-jlane.pythonanywhere.com. Endpoints: /students, /teachers. |
| **Why** | Suspected: staging proxy or worker timeout/overload under load (e.g. PythonAnywhere limits). |
| **Severity** | Medium (staging; may indicate risk under production load). |
| **Repro** | 1) Locust: `locust -f locustfile.py --host=https://romulus-jlane.pythonanywhere.com`. 2) Open http://localhost:8089, set 10 users, spawn rate 1, Start swarming, run 5 min. 3) Check Failures tab for 502. |

### F-3: 500 on update_local_status when request has no JSON body or wrong Content-Type

| Field | Value |
|-------|--------|
| **What** | POST to `/volunteers/update-local-status/<id>` with no body or without `Content-Type: application/json` returns HTTP 500. |
| **When** | Stress test: API break suite (missing-body case). |
| **Where** | Endpoint: POST /volunteers/update-local-status/&lt;id&gt;. Local and staging. |
| **Why** | App uses `request.get_json()`; when body is missing or Content-Type is wrong, Flask/Werkzeug raises; exception is caught and returned as 500 instead of 415/400. |
| **Severity** | Low–Medium (bad client input should return 4xx, not 500). |
| **Repro** | Run: `pytest tests/stress/test_api_break.py::test_update_local_status_missing_body -v`. Or: POST to the endpoint with no body or with wrong Content-Type; observe 500 and JSON body with message like "415 Unsupported Media Type...". |

### F-4: 500 on update_local_status when request body is malformed JSON

| Field | Value |
|-------|--------|
| **What** | POST to `/volunteers/update-local-status/<id>` with malformed JSON body (e.g. plain text) returns HTTP 500. |
| **When** | Stress test: API break suite (malformed-JSON case). |
| **Where** | Endpoint: POST /volunteers/update-local-status/&lt;id&gt;. Local and staging. |
| **Why** | JSON decode failure is raised and returned as 500 instead of 400 Bad Request. |
| **Severity** | Low–Medium (invalid JSON should return 4xx, not 500). |
| **Repro** | Run: `pytest tests/stress/test_api_break.py::test_update_local_status_malformed_json_returns_4xx -v`. Or: POST with `Content-Type: application/json` and body `not json at all`; observe 500 and message like "400 Bad Request: Failed to decode JSON object...". |

*(Add more findings below as you discover 5xxs, timeouts, or other issues.)*

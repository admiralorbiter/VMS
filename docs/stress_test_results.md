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

*(Add more runs above or below using the same format.)*

---

## 4. Findings / Bug List

### F-1: 429 Too Many Requests under load from single IP

| Field | Value |
|-------|--------|
| **What** | Many requests return HTTP 429 (TOO MANY REQUESTS). |
| **When** | Locust with multiple simulated users from one machine (single IP). |
| **Where** | All endpoints: /, /volunteers, /events, /teachers, /students, /organizations. |
| **Why** | Rate limiter (e.g. Flask-Limiter) applied per IP; Locust traffic comes from one IP. |
| **Severity** | Low (by design). |
| **Repro** | 1) Start app: `python app.py`. 2) Start Locust: `locust -f locustfile.py --host=http://127.0.0.1:5050`. 3) Open http://localhost:8089, set users (e.g. 5), spawn rate 1, Start swarming. 4) Check Failures tab for 429. |

*(Add more findings below as you discover 5xxs, timeouts, or other issues.)*

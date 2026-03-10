# Intern Project: Virtual Events API

**Project Type:** Guided feature build (learning project)
**Estimated Duration:** 3–5 sessions
**Prerequisite:** Complete the [Developer Guide](index) setup and have the app
running locally.

> [!NOTE]
> This project walks you through building a **token-gated Virtual Events API**,
> modeled on the existing [Public Event API](api_reference). You will work in
> small, incremental parts — each part produces working, tested code that you
> will submit as a separate PR.

---

## Project Overview

### What You're Building

A new set of API endpoints that expose **upcoming virtual session data** for a
tenant. Unlike the existing Public Event API (which returns in-person volunteer
events), this API returns upcoming virtual sessions — online career-exploration
sessions that connect classrooms with industry professionals.

### Why It Matters

District partners need to pull virtual session data into their own dashboards
and reporting tools. This API gives them a clean, authenticated way to do that
without accessing the Polaris UI directly.

### Architecture at a Glance

```
┌──────────────┐       X-API-Key        ┌───────────────────────────────┐
│  District    │  ─────────────────────► │  /api/v1/district/{slug}      │
│  Dashboard   │  ◄───────────────────── │      /virtual-sessions        │
└──────────────┘       JSON response     └───────────────────────────────┘
                                                     │
                                               reads from
                                                     │
                                              ┌──────▼──────┐
                                              │  Event table │
                                              │  (filtered)  │
                                              └─────────────┘
```

### Key Reference Files

Before you start, read through these files to understand the patterns you'll
follow:

| File | What to look for |
|------|-----------------|
| [`routes/api/public_events.py`](file:///c:/Users/admir/Github/VMS/routes/api/public_events.py) | Complete working example — blueprint, decorator, endpoints, response format |
| [`routes/api/__init__.py`](file:///c:/Users/admir/Github/VMS/routes/api/__init__.py) | How blueprints are exported from the `api` package |
| [`models/event.py`](file:///c:/Users/admir/Github/VMS/models/event.py) | `Event` model, `EventType.VIRTUAL_SESSION`, `EventFormat.VIRTUAL` |
| [`models/tenant.py`](file:///c:/Users/admir/Github/VMS/models/tenant.py) | `validate_api_key()`, `generate_api_key()`, `get_allowed_origins_list()` |
| [`tests/integration/test_public_api.py`](file:///c:/Users/admir/Github/VMS/tests/integration/test_public_api.py) | Test patterns — how existing API tests are structured |
| [`documentation/content/developer/api_reference.md`](file:///c:/Users/admir/Github/VMS/documentation/content/developer/api_reference.md) | API documentation format and style |

---

## Part 1: Blueprint Scaffold & Hello World

**Goal:** Create a new blueprint file, register it, and verify a basic endpoint
returns JSON.

### Tasks

1. **Create the file** `routes/api/virtual_sessions.py`
2. **Create a Flask Blueprint** named `virtual_sessions_api_bp` with the URL
   prefix `/api/v1/district`
3. **Add a single test endpoint:**
   ```python
   @virtual_sessions_api_bp.route("/<tenant_slug>/virtual-sessions/health",
                                    methods=["GET"])
   def health_check(tenant_slug):
       return jsonify({"success": True, "message": "Virtual Sessions API is running"})
   ```
4. **Register the blueprint** in `routes/api/__init__.py` — add it to `__all__`
   and import it alongside the existing `public_api_bp`
5. **Register the blueprint in `app.py`** — find where `public_api_bp` is
   registered and add your new blueprint there too

### How to Verify

```bash
# Start the dev server
python app.py

# Test the endpoint (should return JSON with success: true)
curl http://localhost:5050/api/v1/district/test-tenant/virtual-sessions/health
```

### What to Submit (PR)

- `routes/api/virtual_sessions.py` (new file)
- `routes/api/__init__.py` (updated)
- `app.py` (updated)

---

## Part 2: API Key Authentication

**Goal:** Protect your endpoints with the same API key system used by the
Public Event API.

### Background Reading

Look at the `require_api_key` decorator in `routes/api/public_events.py`
(lines 35–99). Understand how it:
- Reads the `X-API-Key` header
- Looks up the tenant by slug
- Validates the key against the tenant's stored hash
- Sets `g.api_tenant` for downstream use

### Tasks

1. **Reuse the decorator.** Instead of copying it, import it from
   `public_events.py`:
   ```python
   from routes.api.public_events import require_api_key
   ```
2. **Apply the decorator** to your health check endpoint
3. **Test with and without a key** — you should get a `401` without a valid key

> [!INFO]
> **Thinking question:** Why is it better to import the existing decorator
> rather than copying the code? What would happen if we needed to change the
> auth logic later and it was duplicated?

### How to Verify

```bash
# Without API key — should return 401 with MISSING_API_KEY
curl http://localhost:5050/api/v1/district/kckps/virtual-sessions/health

# With invalid key — should return 401 with INVALID_API_KEY
curl -H "X-API-Key: bad-key" \
  http://localhost:5050/api/v1/district/kckps/virtual-sessions/health

# With valid key — should return 200 with success: true
# (Use a key from the district settings page, or generate one in a Python shell)
```

### What to Submit (PR)

- `routes/api/virtual_sessions.py` (updated with auth decorator)

---

## Part 3: List Upcoming Virtual Sessions Endpoint

**Goal:** Build the main `GET /virtual-sessions` endpoint that returns
**upcoming** virtual session data with pagination.

### Background Reading

Study the `list_events()` function in `public_events.py` (lines 137–220).
Note the patterns for:
- Query parameter parsing (`page`, `per_page`, date filters)
- Database query building with filters
- Response envelope structure (`success`, `data`, `pagination`, `meta`)

Also study the `build_event_response()` function (lines 108–134) to see how
the public API decides which fields to include in each event object.

### Tasks

1. **Design the response fields yourself.** Create a
   `build_virtual_session_response(event)` function that returns a dict.

   Open `models/event.py` and look at the `Event` model's columns. Ask
   yourself: *if I were a district partner building a dashboard to show my
   upcoming virtual sessions, what fields would I need?*

   > [!INFO]
   > **Hints to guide your thinking:**
   > - What identifies the session? (id, title)
   > - When does it happen? (date, time, duration)
   > - What is it about? (description, career area)
   > - Who participates? (student counts, educator counts)
   > - What's the status?
   >
   > Look at both the `build_event_response()` in `public_events.py` for
   > patterns, and the `Event` model columns for virtual-session-specific
   > fields like `career_cluster`, `registered_student_count`, etc.

   **Document your choices** in your PR description — explain why you included
   each field and why you excluded others.

2. **Create the `list_virtual_sessions` route:**
   - Path: `/<tenant_slug>/virtual-sessions`
   - Methods: `GET`, `OPTIONS`
   - Apply `@require_api_key`
   - Filter events by:
     - `Event.tenant_id == tenant.id`
     - `Event.type == EventType.VIRTUAL_SESSION` (this is the key filter!)
     - `Event.start_date >= now` (upcoming only!)
   - Order by `start_date` ascending (soonest first)
   - Support query params: `page`, `per_page`, `to_date` (upper bound)
   - Use the same response envelope as the public API

3. **Add rate limiting** using the same pattern as `public_events.py`:
   ```python
   from utils.rate_limiter import get_api_key_or_ip, limiter

   @limiter.limit("60 per minute; 1000 per hour; 10000 per day",
                   key_func=get_api_key_or_ip)
   ```

4. **Add CORS support:**
   ```python
   from flask_cors import cross_origin

   @cross_origin()
   ```

> [!INFO]
> **Thinking question:** Why does this API only return upcoming sessions
> instead of all sessions? Think about the use case — a district dashboard
> wants to show teachers and students what's coming up, not what already
> happened.

### How to Verify

```bash
# List upcoming virtual sessions (requires valid API key)
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:5050/api/v1/district/kckps/virtual-sessions"

# With pagination
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:5050/api/v1/district/kckps/virtual-sessions?page=1&per_page=5"

# With upper-bound date filter
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:5050/api/v1/district/kckps/virtual-sessions?to_date=2026-06-01"
```

### What to Submit (PR)

- `routes/api/virtual_sessions.py` (updated with list endpoint)
- In your PR description, explain which response fields you chose and why

---

## Part 4: Get Single Session Endpoint

**Goal:** Add a detail endpoint that returns a single virtual session by ID.

### Tasks

1. **GET `/<tenant_slug>/virtual-sessions/<session_id>`** — Returns a single
   virtual session by ID. Must verify:
   - The session belongs to the tenant
   - The session is a virtual session type (`EventType.VIRTUAL_SESSION`)
   - Returns `404` with `SESSION_NOT_FOUND` error code if not found
   - Reuse your `build_virtual_session_response()` function from Part 3

2. The endpoint needs `@require_api_key`, `@limiter.limit(...)`, and
   `@cross_origin()`

> [!INFO]
> **Thinking question:** Should this endpoint be restricted to upcoming
> sessions only, or should it allow looking up any session by ID (including
> past ones)? Think about the use case — a partner may have cached a session
> ID and want to refresh its details. What would be the better developer
> experience?

### How to Verify

```bash
# Get single session (valid ID)
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:5050/api/v1/district/kckps/virtual-sessions/123"

# Non-existent session (should return 404)
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:5050/api/v1/district/kckps/virtual-sessions/99999"
```

### What to Submit (PR)

- `routes/api/virtual_sessions.py` (updated with detail endpoint)

---

## Part 5: Tests

**Goal:** Write integration tests for the new API, following the patterns in
`tests/integration/test_public_api.py`.

### Tasks

1. **Create `tests/integration/test_virtual_sessions_api.py`**
2. **Write tests for each area:**

| Test Class | What to Test |
|-----------|-------------|
| `TestVirtualSessionRoutes` | Route/function exists, virtual session type filter works |
| `TestVirtualSessionAuth` | Missing key → 401, invalid key → 401, valid key works |
| `TestVirtualSessionResponse` | Envelope has `success`, `data`, `pagination`, `meta` |
| `TestVirtualSessionFields` | Response builder returns all expected fields |

3. **Run and verify:**
   ```bash
   python -m pytest tests/integration/test_virtual_sessions_api.py -v
   ```

### What to Submit (PR)

- `tests/integration/test_virtual_sessions_api.py` (new file)

---

## Part 6: Documentation

**Goal:** Document your API so district partners can use it.

### Tasks

1. **Create `documentation/content/developer/virtual_sessions_api_reference.md`**
   following the format of the existing
   [`api_reference.md`](api_reference)
2. Include:
   - Overview table (base URL, auth, format)
   - Authentication section (same as public API — shared keys)
   - All three endpoints with request/response examples
   - Rate limiting info
   - Error codes table
   - Example integrations (cURL, JavaScript fetch)
3. **Update the [Developer Guide](index)** to add a link to your new API docs
   in the Resources section

### What to Submit (PR)

- `documentation/content/developer/virtual_sessions_api_reference.md` (new)
- `documentation/content/developer/index.md` (updated with link)

---

## Stretch Goals (Optional)

If you finish all 6 parts and want to keep going:

- **Add a `career_cluster` filter** — Allow filtering virtual sessions by
  career cluster via a query parameter
- **Add a `status` filter** — Allow filtering by event status
- **Add a summary endpoint** — `GET /virtual-sessions/summary` that returns
  aggregate counts (total sessions, total students, unique career clusters)
- **Add a `GET /virtual-sessions/past` endpoint** — Like the main endpoint but
  returns completed sessions instead of upcoming ones
- **Consider extracting the shared `require_api_key` decorator** into a shared
  module like `routes/api/auth.py` so both blueprints can cleanly import it

---

## Tips for Success

1. **Work in small commits.** Each Part should be 1 PR.
2. **Read the existing code first.** The public events API is your roadmap.
3. **Run tests often.** `python -m pytest -v` after every change.
4. **Ask questions early.** If something is unclear, ask before guessing.
5. **Check the decorator order.** Flask decorators are applied bottom-up:
   the order is `@route`, `@limiter`, `@cross_origin`, `@require_api_key`.

---

*Created: March 2026*
*Parent project: [Public Event API Reference](api_reference)*

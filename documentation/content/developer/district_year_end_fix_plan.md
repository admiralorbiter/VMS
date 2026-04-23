# District Year-End Report — Bite-Sized Fix Plan

> **This document is the master resumable plan.** Each piece is fully independent.  
> If you stop mid-session, pick up exactly where you left off by checking off boxes.  
> Each piece has a built-in verification step so you know it's done before moving on.

**Last audited:** 2026-04-23  
**Tracking location:** `documentation/content/developer/district_year_end_fix_plan.md`

---

## Current State (Live Code Audit — 2026-04-23)

| Item | Status | File & Line |
|------|--------|-------------|
| Duplicate CSS link in `district_year_end.html` | 🔴 **Still present** | Lines 6–7 |
| Duplicate CSS link in `district_year_end_detail.html` | 🔴 **Still present** | Lines 6–7 |
| Missing `</div>` closing `.districts-grid` | 🔴 **Still present** | After line 171 |
| Dead `hostFilterForm` JS reference | 🟡 **Has null-guard, dead code remains** | Lines 196–203 |
| `print()` statements in `common.py` | 🔴 **Still present** | Lines 251–406 (~14 calls) |
| `print()` statements in `district_year_end/routes.py` | 🔴 **Still present** | Lines 194–213 |
| `print()` statements in `district_year_end/computation.py` | 🔴 **Still present** | Lines 491–502 |
| `print()` statements in `attendance.py` | 🔴 **Still present** | Lines 42–63 |
| Old URL tests (`/reports/district-year-end`) | 🔴 **Still present** | `test_report_routes.py` lines 56–69 |
| `cache_district_stats()` (superseded function) | 🔴 **Still present** | `common.py` lines 506–539 |
| Scheduler delete-only pattern | 🔴 **Still present** | `cache_refresh_scheduler.py` lines 205–308 |
| `DistrictEngagementReport` in scheduler | 🟡 **Low urgency** | `cache_refresh_scheduler.py` lines 188–190 |
| Stats keys (`total_students`, `unique_student_count`) | ✅ **Correctly set** | `common.py` lines 349, 468–476 |

---

## The 8 Pieces

---

### ✅ Piece 1 — Remove Duplicate CSS Links
**Risk:** Zero &nbsp;|&nbsp; **Time:** 5 min &nbsp;|&nbsp; **Restart needed:** No

**What:** Both main and detail templates load the same CSS twice — one hardcoded path (`/static/css/...`) and one via `url_for`. The hardcoded path breaks when Flask is mounted at a sub-path (e.g. on PythonAnywhere).

**Files:**
- `templates/reports/districts/district_year_end.html` — **delete line 6** (keep line 7)
- `templates/reports/districts/district_year_end_detail.html` — **delete line 6** (keep line 7)

Delete this line from each (the hardcoded one):
```html
<link rel="stylesheet" href="/static/css/district_year_end.css">
```
Keep this line in each (the `url_for` one):
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/district_year_end.css') }}">
```

**Verify:** Browser Network tab — stylesheet loads once with 200, not twice.

---

### ✅ Piece 1.5 — Add Missing Report CSS Styles
**Risk:** Low &nbsp;|&nbsp; **Time:** 10 min &nbsp;|&nbsp; **Restart needed:** No

**What:** The original developer created the HTML markup for `.district-card`, `.month-card`, `.activity-breakdown`, etc., but never added these classes to the respective CSS files. This is why the UI looked like unstyled, vertically stacked text.

**Files:**
- `static/css/district_year_end.css`
- `static/css/district_year_end_detail.css`

**What to do:** Append the missing grid layout and card styling rules to both CSS files.

**Verify:** Hard refresh the browser (Ctrl+Shift+R) — cards, grids, and hover effects appear correctly styled.

---

### ✅ Piece 2 — Fix Missing `</div>` (The Layout Break)
**Risk:** Low &nbsp;|&nbsp; **Time:** 10 min &nbsp;|&nbsp; **Restart needed:** No

**What:** In `district_year_end.html`, the `{% endfor %}` that ends the district card loop is at line 171. The `</div>` at line 172 closes the card's inner div — but the **outer `.districts-grid` container (opened at line 65) is never closed**. The pagination controls fall inside the grid, causing the layout break.

**File:** `templates/reports/districts/district_year_end.html`

Current (around lines 171–175):
```html
        {% endfor %}
            </div>

            <!-- Pagination Controls -->
            <div class="pagination-controls" id="paginationControls">
```

Change to:
```html
        {% endfor %}
    </div>  <!-- closes .districts-grid -->

    <!-- Pagination Controls -->
    <div class="pagination-controls" id="paginationControls">
```

**Verify:** Reload `/reports/district/year-end` — cards are in a grid, pagination sits cleanly below, not inside the last card.

---

### ☐ Piece 3 — Remove Dead `hostFilterForm` JS Code
**Risk:** Zero &nbsp;|&nbsp; **Time:** 5 min &nbsp;|&nbsp; **Restart needed:** No

**What:** The `updateReport()` JS function references `document.getElementById('hostFilterForm')` — a form that's commented out in the template. A null-guard already prevents crashes, but the dead code is confusing and should be removed.

**File:** `templates/reports/districts/district_year_end.html` (script block, lines 196–203)

Remove this entire block from `updateReport()`:
```javascript
// Also update the host filter form to include the new school year
const hostFilterForm = document.getElementById('hostFilterForm');
if (hostFilterForm) {
    const hiddenYearInput = hostFilterForm.querySelector('input[name="school_year"]');
    if (hiddenYearInput) {
        hiddenYearInput.value = select.value;
    }
}
```

**Verify:** Browser console shows no errors. Year select dropdown still works.

---

### ✅ Piece 4 — Remove Useless Prints and Clean Up Logging (Terminal Noise)
**Risk:** Low &nbsp;|&nbsp; **Time:** 20 min &nbsp;|&nbsp; **Restart needed:** Yes

**What:** ~20 `print()` calls across 4 files fire on every cache build or manual refresh. In production this exposes event IDs, student counts, and SQL in plain-text server logs.

**Files and what to do:**

#### `routes/reports/common.py` (lines 251–406, ~14 print calls)
Add at module level (after existing imports):
```python
import logging
logger = logging.getLogger(__name__)
```
Then remove the useless debug prints and replace the valuable ones with the appropriate level:
- Loop-level debugs (e.g. `Found {len(schools)}`, `Applying PREPKC filter`) → **Delete entirely**
- Event-level debugs (e.g. `Virtual event {event.id}...`) → **Delete entirely**
- SQL dump prints → **Delete entirely**
- `"Warning: Primary district ... not found"` line → `logger.warning(...)`
- `"Error caching district ..."` line (line 538) → `logger.error(...)`

#### `routes/reports/district_year_end/routes.py` (lines 194–213, ~5 print calls)
These are timing/progress prints in `refresh_district_year_end()`. Add logger and replace with `logger.info(...)`.

#### `routes/reports/district_year_end/computation.py` (lines 491–502, ~2 print calls)
Replace the progress print with `logger.debug(...)` and the error print with `logger.error(...)`.

#### `routes/reports/attendance.py` (lines 42–63, ~5 print calls)
**Delete entirely.** These were just parameter checks on route load and clutter the code.

**Verify:** Click "Refresh Data" on the year-end page. Terminal stays quiet — no flood of debug lines. Run the test suite to confirm nothing broke.

---

### ✅ Piece 5 — Update Old URL Tests
**Risk:** Low &nbsp;|&nbsp; **Time:** 15 min &nbsp;|&nbsp; **Restart needed:** No

**What:** Two tests in `test_report_routes.py` hit URLs that no longer exist (`/reports/district-year-end` and `/reports/district-year-end-detail`). They only "pass" because `safe_route_test` accepts 404 — giving false confidence that these pages work.

**File:** `tests/integration/test_report_routes.py` (lines 56–69)

Current:
```python
def test_district_year_end_report(client, auth_headers):
    response = safe_route_test(client, "/reports/district-year-end", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_district_year_end_detail_report(client, auth_headers):
    response = safe_route_test(client, "/reports/district-year-end-detail", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])
```

Change to:
```python
def test_district_year_end_report(client, auth_headers):
    """Test district year end report — main list page."""
    response = safe_route_test(client, "/reports/district/year-end", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_district_year_end_detail_report(client, auth_headers):
    """Detail page requires a valid district name — 404 is acceptable for a missing district."""
    response = safe_route_test(
        client, "/reports/district/year-end/detail/Hickman Mills School District",
        headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])
```

**Verify:** `pytest tests/integration/test_report_routes.py::test_district_year_end_report tests/integration/test_report_routes.py::test_district_year_end_detail_report -v` — both tests hit real URLs and assert meaningful status codes.

---

### ✅ Piece 6 — Deprecate Superseded `cache_district_stats()` in `common.py`
**Risk:** Low &nbsp;|&nbsp; **Time:** 10 min &nbsp;|&nbsp; **Restart needed:** Yes

**What:** `cache_district_stats()` in `common.py` (lines 506–539) only writes `report_data` to the cache — it doesn't write `events_data`. It's been superseded by `cache_district_stats_with_events()` in `computation.py`. Nothing currently calls it, but if it gets called accidentally in a future refactor, it silently writes incomplete cache records that break the event timeline view on the detail page.

**File:** `routes/reports/common.py` (lines 506–539)

**Option A (safest — add deprecation warning):**
```python
def cache_district_stats(school_year, district_stats):
    """
    DEPRECATED: Use cache_district_stats_with_events() in computation.py instead.
    This function does not store events_data and will produce incomplete cache records
    that break the district detail page event timeline.
    """
    import warnings
    warnings.warn(
        "cache_district_stats() is deprecated. Use cache_district_stats_with_events() from "
        "routes.reports.district_year_end.computation instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # ... rest of function unchanged
```

**Option B (cleanest — delete the function):** Confirm nothing calls it first:
```bash
grep -rn "cache_district_stats(" routes/ utils/ --include="*.py"
```
Expected: only one hit (the definition itself in `common.py`). If confirmed, delete the whole function.

**Verify:** `grep -rn "cache_district_stats(" routes/` — only `computation.py`'s `cache_district_stats_with_events` appears. No unexpected call sites.

---

### ✅ Piece 7 — Fix Scheduler Delete-Only Pattern
**Risk:** Medium &nbsp;|&nbsp; **Time:** 30 min &nbsp;|&nbsp; **Restart needed:** Yes

**What:** In `utils/cache_refresh_scheduler.py`, four methods follow the same broken pattern: unconditionally delete all caches, then leave a comment saying "will regenerate on next access." After every nightly run, the first user to hit org, virtual, volunteer, or recruitment report pages triggers a cold computation that can take 30–60 seconds.

**File:** `utils/cache_refresh_scheduler.py`

**The fix — replace unconditional delete with age-check delete:**

> [!IMPORTANT]
> Before writing the filter, check `models/reports.py` to confirm the exact timestamp column name for each model. It may be `last_updated`, `created_at`, or `updated_at`.

Pattern to apply to each of the 4 methods:
```python
def _refresh_organization_caches(self):
    """Prune stale organization caches (age > 24h). Fresh caches survive the scheduler."""
    logger.info("Pruning stale organization caches...")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    try:
        deleted_summary = OrganizationSummaryCache.query.filter(
            OrganizationSummaryCache.last_updated < cutoff
        ).delete()
        deleted_report = OrganizationReport.query.filter(
            OrganizationReport.last_updated < cutoff
        ).delete()
        deleted_detail = OrganizationDetailCache.query.filter(
            OrganizationDetailCache.last_updated < cutoff
        ).delete()
        db.session.commit()
        logger.info(
            "Pruned %d summary, %d report, %d detail org cache entries",
            deleted_summary, deleted_report, deleted_detail,
        )
    except Exception as e:
        logger.exception("Failed to prune stale organization caches: %s", str(e))
        db.session.rollback()
```

Apply the same pattern to `_refresh_virtual_session_caches`, `_refresh_volunteer_caches`, and `_refresh_recruitment_caches`.

**Verify:** Run `refresh_all_caches()` from the Flask shell. Then immediately hit `/reports/organization` — it should load from cache (fast), not recompute (30s+ wait).

---

### ✅ Piece 8 — Clean Up `DistrictEngagementReport` from Scheduler
**Risk:** Low &nbsp;|&nbsp; **Time:** 15 min &nbsp;|&nbsp; **Restart needed:** Yes

**What:** `DistrictEngagementReport` is imported in the scheduler and deleted nightly, but no route ever reads from or writes to it. It's a legacy model from before `DistrictYearEndReport` was created. The scheduler is running a nightly delete against an empty table.

**Steps:**
1. Confirm it's unused:
   ```bash
   grep -rn "DistrictEngagementReport" . --include="*.py"
   ```
   Expected: only `models/reports.py` (definition) + `cache_refresh_scheduler.py` (import + delete).

2. In `utils/cache_refresh_scheduler.py`:
   - Remove `DistrictEngagementReport` from the import list (around line 50)
   - Remove these two lines from `_refresh_district_caches()` (around lines 188–190):
     ```python
     DistrictEngagementReport.query.filter_by(school_year=school_year).delete()
     ```

3. In `models/reports.py`, add a deprecation comment to the class:
   ```python
   # DEPRECATED: No route reads from or writes to this model.
   # It predates DistrictYearEndReport and is kept only for DB migration history.
   # TODO: Write an Alembic migration to drop this table once confirmed empty in prod.
   class DistrictEngagementReport(db.Model):
       ...
   ```

**Verify:** Restart the app — no `ImportError`. Run the scheduler — no error about `DistrictEngagementReport`.

---

## Recommended Order

| # | Piece | Why this order |
|---|-------|----------------|
| **1** | Piece 1 — Duplicate CSS | Zero risk, 5 min, instant improvement |
| **1.5** | Piece 1.5 — Missing CSS | Solves the root cause of the broken card UI |
| **2** | Piece 2 — Missing `</div>` | Fixes the visible layout bug |
| **3** | Piece 3 — Dead JS reference | Cleans up after Piece 2, zero risk |
| **4** | Piece 4 — print → logger | Quiets the terminal before doing data work |
| **5** | Piece 5 — Update old tests | Makes test suite meaningful before fixing scheduler |
| **6** | Piece 6 — Deprecate old cache fn | Removes latent regression risk |
| **7** | Piece 7 — Scheduler age-check | Infrastructure fix, verify manually |
| **8** | Piece 8 — EngagementReport cleanup | Lowest urgency |

> **Pieces 1–3 (including 1.5)** can be done in one sitting in under 20 minutes. Template and CSS only, no restart needed. The UI will finally match the intended design.
> **Piece 4** is the next quick win — 20 min, restores clean terminal output.  
> **Pieces 5–6** are the code hygiene fixes — low risk, confirm tests actually pass.  
> **Pieces 7–8** are the infrastructure improvements — save for a focused session.

---

## Files Reference

| File | Relevant Pieces |
|------|-----------------|
| `templates/reports/districts/district_year_end.html` | 1, 2, 3 |
| `templates/reports/districts/district_year_end_detail.html` | 1 |
| `static/css/district_year_end.css` | 1.5 |
| `static/css/district_year_end_detail.css` | 1.5 |
| `routes/reports/common.py` | 4, 6 |
| `routes/reports/district_year_end/routes.py` | 4 |
| `routes/reports/district_year_end/computation.py` | 4 |
| `routes/reports/attendance.py` | 4 |
| `tests/integration/test_report_routes.py` | 5 |
| `utils/cache_refresh_scheduler.py` | 7, 8 |
| `models/reports.py` | 8 |

---

## Quick Verification Commands

Run after completing any Python file changes:

```bash
# Smoke test the report routes
pytest tests/integration/test_report_routes.py -v

# Check for any remaining print() in the reports package
grep -rn "print(" routes/reports/ --include="*.py"

# Confirm no remaining call sites for the old cache function
grep -rn "cache_district_stats(" routes/ utils/ --include="*.py"
```

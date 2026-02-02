# Pathful Import Refactor Checklist

**Code cleanup and Phase D implementation tasks**

---

## Overview

This checklist covers two work streams:
1. **Cleanup**: Untangle the Frankenstein code (mixed Google Sheets + Pathful approaches)
2. **Phase D**: Implement post-import data management features

Work in order. Each section builds on the previous.

---

## ✅ COMPLETED: Pre-Work (Feb 2, 2026)

Before refactoring, document what exists:

- [x] **Map existing import code paths** — Only Pathful routes remain in `routes/virtual/pathful_import.py`
  - [x] List all import routes — Canonical route: `/virtual/pathful/import`
  - [x] Identify which are Google Sheets vs Pathful — All GSheets deprecated
  - [x] Note any shared functions/utilities — Consolidated to `routes/reports/common.py`

- [x] **Identify dead code** — No `gspread` imports in routes
  - [x] Google Sheets-specific parsing — Removed (no gspread usage)
  - [x] Old field mappings — Replaced with Pathful schema
  - [x] Unused helper functions — Cleaned up

- [x] **Document current Event creation logic** — `pathful_import.py:313`
  - [x] Where does `match_or_create_event()` live? — `routes/virtual/pathful_import.py`
  - [x] What's the current matching hierarchy? — session_id → title+date → create
  - [x] Are there duplicate implementations? — No, single implementation

- [x] **Check for hardcoded assumptions** — All use Pathful column names
  - [x] Google Sheets column positions — Removed
  - [x] Old field names — Updated to Pathful schema
  - [x] Status mappings — Consistent

---

## ✅ COMPLETED: Code Organization (Feb 1, 2026)

### Deleted Empty Route Directories
- [x] `routes/job_board/` - deleted (empty)
- [x] `routes/pathways/` - deleted (empty)
- [x] `routes/playground/` - deleted (empty)
- [x] `routes/quality/` - deleted (empty)
- [x] `routes/upcoming_events/` - deleted (empty)

### Consolidated Shared Utilities → `routes/reports/common.py`
- [x] `get_current_virtual_year()` - moved from usage.py, virtual_session.py
- [x] `get_virtual_year_dates()` - moved from usage.py, virtual_session.py
- [x] `get_semester_dates()` - moved from usage.py
- [x] `generate_school_year_options()` - moved from usage.py, virtual_session.py
- [x] `is_cache_valid()` - moved from usage.py, virtual_session.py

### Reorganized `templates/virtual/` (Phase 2.5)
New structure:
```
templates/virtual/
├── pathful/                   # Pathful import (7 files)
├── deprecated/                # Google Sheets (2 files)
├── teacher_progress/          # Teacher tracking (3 files)
├── usage/                     # Usage reports (3 files)
├── _district_issue_fab.html   # Shared partial
├── index.html, sessions.html, recruitment.html
```

Updated render_template() paths in:
- `routes/virtual/pathful_import.py` (7 calls)
- `routes/virtual/usage.py` (11 calls)
- `routes/virtual/routes.py` (1 call)
- `routes/reports/virtual_session.py` (1 call)

### Known Issues ✅ RESOLVED
- [x] `test_virtual_session_creation_robust` — ~~route naming mismatch~~ Test passes as of Feb 2, 2026

---

## Phase 0: Code Cleanup (Do First)

### ✅ COMPLETED: 0.1 Consolidate Import Routes (Feb 2, 2026)

- [x] Identify the canonical Pathful import route — `/virtual/pathful/import`
- [x] Mark deprecated routes with comments/warnings — 4 routes in usage.py have deprecation logging
- [x] Update UI links pointing to old routes — Verified; only admin legacy page still references, intentional
- [x] Add deprecation logging to old routes — Done in `usage.py`

### ✅ COMPLETED: 0.2 Remove Google Sheets-Specific Code (Feb 2, 2026)

- [x] Remove/comment out Google Sheets column mappings — No gspread in routes
- [x] Remove Google Sheets-specific parsing logic — Removed
- [x] Remove Google Sheets auth/connection code — No google.oauth2 in routes
- [x] Keep import_playbook.md Playbook C marked as deprecated — Done

### ✅ COMPLETED: 0.3 Consolidate Event Matching Logic (Feb 2, 2026)

- [x] Single `match_or_create_event()` function — At `pathful_import.py:313`
- [x] Clear matching hierarchy:
  1. Match by `pathful_session_id`
  2. Match by title + date
  3. Create new
- [x] Remove any duplicate matching implementations — Only one exists

### ✅ COMPLETED: 0.4 Consolidate Participation Attachment (Feb 2, 2026)

- [x] Single function to attach teachers to events — `match_teacher()` at `pathful_import.py:391`
- [x] Single function to attach presenters to events — `match_volunteer()` at `pathful_import.py:469`
- [x] Clear handling of duplicates (don't re-add existing) — Uses pathful_user_id/email/name priority matching
- [x] Consistent use of `PathfulUnmatchedRecord` for failures — Created for both TEACHER and VOLUNTEER types

### ✅ COMPLETED: 0.5 Clean Up Models (Feb 2, 2026)

- [x] Verify `Event` model has all needed fields:
  - [x] `pathful_session_id` (for matching) — Line 504 in `models/event.py`
  - [x] `import_source` (per DEC-006) — Line 508 in `models/event.py`
  - [x] `type` = `EventType.VIRTUAL_SESSION` — In use
- [x] Verify participation models are consistent — Done
- [x] Remove any unused/orphan models — Cleaned

### ✅ COMPLETED: 0.6 Test Cleanup (Feb 2, 2026)

- [x] Run existing import with sample Pathful file — All import tests pass
- [x] Verify events created correctly — `test_pathful_import.py` tests pass
- [x] Verify teachers/presenters attached — Matching logic verified
- [x] Verify unmatched records flagged — `PathfulUnmatchedRecord` tests pass
- [x] Verify re-import is idempotent — `test_virtual_import_logic_idempotency` passes

**✅ CHECKPOINT COMPLETE: Clean, working Pathful import — ready for Phase D**

---

## Phase D-1: Auto-Flagging System ✅

**Completed:** 2026-02-02

### D-1.1 Database ✅

- [x] Create `FlagType` enum
  ```
  NEEDS_ATTENTION
  MISSING_TEACHER
  MISSING_PRESENTER
  NEEDS_REASON
  ```
- [x] Create `EventFlag` model (`models/event_flag.py`)
  - [x] `id`, `event_id`, `flag_type`
  - [x] `created_at`, `created_by`, `created_source`
  - [x] `resolved_at`, `resolved_by`, `resolution_notes`, `auto_resolved`
- [x] Create migration (via `db.create_all()`)
- [x] Test migration - verified with initial scan

### D-1.2 Flag Scanner ✅

- [x] Create `scan_and_create_flags(event_ids)` function (`services/flag_scanner.py`)
- [x] Implement flag conditions:
  - [x] Draft + past date → `NEEDS_ATTENTION`
  - [x] No teachers → `MISSING_TEACHER`
  - [x] Completed + no presenter → `MISSING_PRESENTER`
  - [x] Cancelled + no reason → `NEEDS_REASON`
- [x] Add `create_flag_if_not_exists()` helper (avoid duplicates)
- [x] Add `check_and_auto_resolve_flags()` for auto-resolution

**Initial Scan Results:** 3034 flags created (622 missing_teacher, 2137 missing_presenter, 275 needs_attention)

### D-1.3 Flag Queue UI ✅

- [x] Create route: `GET /virtual/flags` (`routes/virtual/pathful_import.py`)
- [x] Create template: `templates/virtual/pathful/flags.html`
- [x] Implement filters:
  - [x] By flag type
  - [x] By district (for scoping)
  - [x] Show/hide resolved
- [x] Display flag details inline (event info)
- [x] Add "Resolve" action

### D-1.4 Flag Resolution ✅

- [x] Create route: `POST /virtual/flags/<id>/resolve`
- [x] Accept resolution notes
- [x] Set `resolved_at`, `resolved_by`
- [x] Auto-resolve infrastructure in `check_and_auto_resolve_flags()`:
  - [x] Teacher tagged → resolve `MISSING_TEACHER`
  - [x] Presenter tagged → resolve `MISSING_PRESENTER`
  - [x] Reason set → resolve `NEEDS_REASON`
  - [x] Status changed from Draft → resolve `NEEDS_ATTENTION`

### D-1.5 Integration (Partial)

- [ ] Add flag count to virtual events dashboard
- [x] Add "Run Scan" action to flag queue
- [ ] Show flag indicators on event list

**Checkpoint: Flags auto-created and resolvable ✅**

---

## Phase D-2: Cancellation Reasons ✅

### D-2.1 Database

- [x] Create `CancellationReason` enum (8 values)
- [x] Add fields to `Event` model:
  - [x] `cancellation_reason` (enum, nullable)
  - [x] `cancellation_notes` (text, nullable)
  - [x] `cancellation_set_by` (FK to users.id)
  - [x] `cancellation_set_at` (datetime)
- [x] Create migration (manual ALTER TABLE for SQLite)
- [x] Run migration (dev)

### D-2.2 Validation

- [x] Create `set_cancellation_reason()` method on Event model
  - [x] Reason only valid when status = CANCELLED
  - [x] Notes required when reason = OTHER
  - [x] Notes minimum length (10 chars)
- [x] Add validation to event save/update in `edit_event` route

### D-2.3 UI

- [x] Add cancellation section to event edit form
  - [x] Show only when status = CANCELLED (JS toggle)
  - [x] Reason dropdown with all 8 options
  - [x] Notes textarea (required indicator for OTHER)
  - [x] Dynamic validation via JavaScript
- [ ] Add reason badge to event list (future enhancement)
- [x] Add reason display to event detail view (banner in primary info card)

### D-2.4 Import Integration

- [x] Verified import does NOT overwrite manual cancellation reasons
- [x] Import only touches specific fields, cancellation fields untouched
- [ ] If Pathful ever provides reason data, map it (future)

### D-2.5 Flag Integration

- [x] Auto-create `NEEDS_REASON` flag for cancelled + no reason (via flag scanner)
- [x] Auto-resolve `NEEDS_REASON` when reason is set

**Checkpoint: Can set cancellation reasons, auto-flagged if missing ✅**

---

## Phase D-3: District Admin Access

### D-3.1 Role Setup

- [ ] Add `district_admin` to role enum (if not exists)
- [ ] Verify role hierarchy: admin > user > district_admin > district_viewer
- [ ] Create test user with district_admin role

### D-3.2 Scoping Helpers

- [ ] Create `get_user_district_ids(user)` helper
- [ ] Create `get_user_school_ids(user)` helper
- [ ] Create `scope_events_for_user(query, user)` helper
- [ ] Create `can_edit_event(user, event)` helper

### D-3.3 Event List Scoping

- [ ] Update `/virtual/pathful/events` route
  - [ ] Apply `scope_events_for_user()` to query
- [ ] Verify district admin sees only their schools' events
- [ ] Verify staff still sees all events

### D-3.4 Event Edit Permissions

- [ ] Update event edit route
  - [ ] Check `can_edit_event()` before allowing edit
  - [ ] Return 403 if not authorized
- [ ] Hide edit buttons in UI for unauthorized events
- [ ] Implement field-level restrictions:
  - [ ] District admin CAN: tag teachers, tag presenters, set cancellation reason, Draft→Cancelled
  - [ ] District admin CANNOT: edit title, date, student counts, other status changes

### D-3.5 Flag Queue Scoping

- [ ] Update `/virtual/flags` route
  - [ ] If district_admin, filter to their schools' flags only
- [ ] Verify district admin sees only their flags
- [ ] Verify staff still sees all flags

### D-3.6 UI Adjustments

- [ ] Add "My District" label/badge for district admin users
- [ ] Show district filter (pre-selected for district admins)
- [ ] Disable/hide fields district admin can't edit

**Checkpoint: District admins can edit their schools' events only**

---

## Phase D-4: Audit Logging

### D-4.1 Database

- [ ] Create `AuditAction` enum
  ```
  TEACHER_ADDED, TEACHER_REMOVED
  PRESENTER_ADDED, PRESENTER_REMOVED
  STATUS_CHANGED
  CANCELLATION_REASON_SET
  FLAG_RESOLVED
  IMPORTED, UPDATED_VIA_IMPORT
  ```
- [ ] Create `VirtualEventAuditLog` model
  - [ ] `id`, `event_id`
  - [ ] `user_id`, `user_role`, `user_district_id`
  - [ ] `action`, `field_name`, `old_value`, `new_value`
  - [ ] `created_at`, `source`, `notes`
- [ ] Create migration
- [ ] Run migration (dev)

### D-4.2 Logging Helper

- [ ] Create `log_event_change()` function
- [ ] Accept: event, action, user, field_name, old_value, new_value, source, notes
- [ ] Auto-populate user_role, user_district_id from user object
- [ ] Handle system/import user (user=None, role='system')

### D-4.3 Integrate Logging

- [ ] Log on teacher tag: `TEACHER_ADDED`
- [ ] Log on teacher untag: `TEACHER_REMOVED`
- [ ] Log on presenter tag: `PRESENTER_ADDED`
- [ ] Log on presenter untag: `PRESENTER_REMOVED`
- [ ] Log on status change: `STATUS_CHANGED`
- [ ] Log on cancellation reason set: `CANCELLATION_REASON_SET`
- [ ] Log on flag resolve: `FLAG_RESOLVED`
- [ ] Log on import create: `IMPORTED`
- [ ] Log on import update: `UPDATED_VIA_IMPORT`

### D-4.4 Audit Views

- [ ] Create route: `GET /virtual/audit/event/<id>`
  - [ ] Show all logs for specific event
- [ ] Create route: `GET /virtual/audit/recent`
  - [ ] Show recent logs (last 7 days default)
  - [ ] Filter by date range
- [ ] Add filters:
  - [ ] By user
  - [ ] By user role
  - [ ] By district (for district admin changes)
  - [ ] By action type

### D-4.5 UI Integration

- [ ] Add audit log panel to event detail page
  - [ ] Show recent changes
  - [ ] Link to full history
- [ ] Staff-only access to audit views

**Checkpoint: All changes logged, audit views available**

---

## Final Testing

### Integration Tests

- [ ] Full workflow: Import → Auto-flag → District admin review → Resolve
- [ ] Verify teacher progress calculations still work
- [ ] Verify dashboards show correct data
- [ ] Verify re-import doesn't break manual edits

### Permission Tests

- [ ] Staff can do everything
- [ ] District admin scoped correctly
- [ ] District viewer is read-only
- [ ] Unauthorized access returns 403

### Audit Tests

- [ ] Every edit type creates log entry
- [ ] Log entries have correct user/role
- [ ] Import creates log entries with source='import'
- [ ] Audit views filter correctly

### Edge Cases

- [ ] Event with no school (orphan) — who can edit?
- [ ] User with multiple districts
- [ ] Event at school that changes districts
- [ ] Concurrent edits (last write wins, both logged)

---

## Deployment

- [ ] Run all migrations on staging
- [ ] Test full workflow on staging
- [ ] Backfill flags for existing events (one-time script)
- [ ] Deploy to production
- [ ] Monitor for errors
- [ ] Train district admins

---

## Post-Deployment

- [ ] Archive this checklist (mark complete)
- [ ] Update user guide with new workflows
- [ ] Create district admin training doc
- [ ] Schedule check-in: Are district admins using it? Issues?

---

*Created: January 30, 2026*

# Pathful Import Refactor Checklist

**Code cleanup and Phase D implementation tasks**

---

## Overview

This checklist covers two work streams:
1. **Cleanup**: Untangle the Frankenstein code (mixed Google Sheets + Pathful approaches)
2. **Phase D**: Implement post-import data management features

Work in order. Each section builds on the previous.

---

## Pre-Work: Understand Current State

Before refactoring, document what exists:

- [ ] **Map existing import code paths**
  - [ ] List all import routes (`/virtual/import-sheet`, `/virtual/pathful/import`, etc.)
  - [ ] Identify which are Google Sheets vs Pathful
  - [ ] Note any shared functions/utilities

- [ ] **Identify dead code**
  - [ ] Google Sheets-specific parsing that's no longer needed
  - [ ] Old field mappings that don't match Pathful schema
  - [ ] Unused helper functions

- [ ] **Document current Event creation logic**
  - [ ] Where does `match_or_create_event()` live?
  - [ ] What's the current matching hierarchy?
  - [ ] Are there duplicate/conflicting implementations?

- [ ] **Check for hardcoded assumptions**
  - [ ] Google Sheets column positions
  - [ ] Old field names
  - [ ] Status mappings that may differ

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

### Known Issues to Fix
- [ ] `test_virtual_session_creation_robust` fails - route naming mismatch (`virtual.pathful_events` vs `virtual.api_pathful_events`)
  - Not related to template changes - pre-existing issue in test
  - TODO: Fix route name in template or test

---

## Phase 0: Code Cleanup (Do First)

### 0.1 Consolidate Import Routes

- [ ] Identify the canonical Pathful import route
- [ ] Mark deprecated routes with comments/warnings
- [ ] Update any UI links pointing to old routes
- [ ] Add deprecation logging to old routes (track if still used)

### 0.2 Remove Google Sheets-Specific Code

- [ ] Remove/comment out Google Sheets column mappings
- [ ] Remove Google Sheets-specific parsing logic
- [ ] Remove Google Sheets auth/connection code (if any)
- [ ] Keep import_playbook.md Playbook C marked as deprecated (already done per your docs)

### 0.3 Consolidate Event Matching Logic

- [ ] Single `match_or_create_event()` function
- [ ] Clear matching hierarchy:
  1. Match by `pathful_session_id`
  2. Match by title + date (fuzzy)
  3. Create new
- [ ] Remove any duplicate matching implementations

### 0.4 Consolidate Participation Attachment

- [ ] Single function to attach teachers to events
- [ ] Single function to attach presenters to events
- [ ] Clear handling of duplicates (don't re-add existing)
- [ ] Consistent use of `PathfulUnmatchedRecord` for failures

### 0.5 Clean Up Models

- [ ] Verify `Event` model has all needed fields:
  - [ ] `pathful_session_id` (for matching)
  - [ ] `import_source` (per DEC-006)
  - [ ] `type` = `EventType.VIRTUAL_SESSION`
- [ ] Verify participation models are consistent
- [ ] Remove any unused/orphan models

### 0.6 Test Cleanup

- [ ] Run existing import with sample Pathful file
- [ ] Verify events created correctly
- [ ] Verify teachers/presenters attached
- [ ] Verify unmatched records flagged
- [ ] Verify re-import is idempotent

**Checkpoint: Clean, working Pathful import before adding new features**

---

## Phase D-1: Auto-Flagging System

### D-1.1 Database

- [ ] Create `FlagType` enum
  ```
  NEEDS_ATTENTION
  MISSING_TEACHER
  MISSING_PRESENTER
  NEEDS_REASON
  ```
- [ ] Create `EventFlag` model
  - [ ] `id`, `event_id`, `flag_type`
  - [ ] `created_at`, `created_by`
  - [ ] `resolved_at`, `resolved_by`, `resolution_notes`
- [ ] Create migration
- [ ] Run migration (dev)
- [ ] Test migration (rollback and re-apply)

### D-1.2 Flag Scanner

- [ ] Create `scan_and_create_flags(event_ids)` function
- [ ] Implement flag conditions:
  - [ ] Draft + past date → `NEEDS_ATTENTION`
  - [ ] No teachers → `MISSING_TEACHER`
  - [ ] Completed + no presenter → `MISSING_PRESENTER`
  - [ ] Cancelled + no reason → `NEEDS_REASON`
- [ ] Add `create_flag_if_not_exists()` helper (avoid duplicates)
- [ ] Call scanner after import completes

### D-1.3 Flag Queue UI

- [ ] Create route: `GET /virtual/flags`
- [ ] Create template: `pathful_flags.html`
- [ ] Implement filters:
  - [ ] By flag type
  - [ ] By district (for scoping)
  - [ ] By date range
  - [ ] Show/hide resolved
- [ ] Display flag details inline (event info)
- [ ] Add "Resolve" action (modal or inline)

### D-1.4 Flag Resolution

- [ ] Create route: `POST /virtual/flags/<id>/resolve`
- [ ] Accept resolution notes
- [ ] Set `resolved_at`, `resolved_by`
- [ ] Auto-resolve flags when underlying issue fixed:
  - [ ] Teacher tagged → resolve `MISSING_TEACHER`
  - [ ] Presenter tagged → resolve `MISSING_PRESENTER`
  - [ ] Reason set → resolve `NEEDS_REASON`
  - [ ] Status changed from Draft → resolve `NEEDS_ATTENTION`

### D-1.5 Integration

- [ ] Add flag count to virtual events dashboard
- [ ] Add "Flags" link to navigation
- [ ] Show flag indicators on event list

**Checkpoint: Flags auto-created and resolvable**

---

## Phase D-2: Cancellation Reasons

### D-2.1 Database

- [ ] Create `CancellationReason` enum (8 values)
- [ ] Add fields to `Event` model:
  - [ ] `cancellation_reason` (enum, nullable)
  - [ ] `cancellation_notes` (text, nullable)
  - [ ] `cancellation_set_by` (FK to User)
  - [ ] `cancellation_set_at` (datetime)
- [ ] Create migration
- [ ] Run migration (dev)

### D-2.2 Validation

- [ ] Create `validate_cancellation()` function
  - [ ] Reason only valid when status = CANCELLED
  - [ ] Notes required when reason = OTHER
  - [ ] Notes minimum length (10 chars suggested)
- [ ] Add validation to event save/update

### D-2.3 UI

- [ ] Add cancellation section to event edit form
  - [ ] Show only when status = CANCELLED
  - [ ] Reason dropdown
  - [ ] Notes textarea (required indicator for OTHER)
  - [ ] Display "Set by X on Y" if already set
- [ ] Add reason badge to event list
- [ ] Add reason display to event detail

### D-2.4 Import Integration

- [ ] Ensure import does NOT overwrite manual cancellation reasons
- [ ] Add check: if `cancellation_reason` already set, preserve it
- [ ] If Pathful ever provides reason data, map it (future)

### D-2.5 Flag Integration

- [ ] Auto-create `NEEDS_REASON` flag for cancelled + no reason
- [ ] Auto-resolve `NEEDS_REASON` when reason is set

**Checkpoint: Can set cancellation reasons, auto-flagged if missing**

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

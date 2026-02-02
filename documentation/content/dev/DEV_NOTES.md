# Pathful Import Refactor — Dev Notes

**Implementation guidance, patterns, and gotchas**

---

## Recent Changes Log

### Feb 1, 2026 — Code Organization Refactor
Cleaned up routes and templates structure. See `REFACTOR_CHECKLIST.md` for full details.

**Key changes:**
- Deleted 5 empty route directories
- Consolidated shared utilities to `routes/reports/common.py`
- Reorganized `templates/virtual/` into subdirectories (pathful/, deprecated/, teacher_progress/, usage/)

**TODO for next session:**
1. Run `pytest tests/ -v` to verify all tests pass
2. Fix `test_virtual_session_creation_robust` - route naming issue (`virtual.pathful_events` vs `virtual.api_pathful_events`)
3. Review deprecated Google Sheets templates in `templates/virtual/deprecated/`

---

## Architecture Principles

### Single Source of Truth Per Field

Every field should have exactly one owner. When in doubt:

| Field | Owner | Implication |
|-------|-------|-------------|
| Title, date, student counts | Pathful (via import) | Never edit in Polaris UI |
| Status | Hybrid | Import can set, manual can override |
| Teachers, presenters | Polaris | Import adds, manual can add/remove |
| Cancellation reason | Polaris | Import never touches |
| Flags | Polaris (system) | Auto-created, manually resolved |

### Import Should Be Additive, Not Destructive

When re-importing:
- **DO** update event core fields from Pathful
- **DO** add new teacher/presenter associations
- **DON'T** remove manually-added teachers/presenters
- **DON'T** overwrite manually-set cancellation reasons
- **DON'T** re-open resolved flags

### Audit Everything

If a human can change it, log it. If the system changes it, log it with `source='system'` or `source='import'`.

---

## Phase 0: Cleanup Notes

### Finding the Frankenstein

Look for these patterns that indicate mixed approaches:

```python
# Google Sheets patterns (old)
row[0], row[1], row[2]  # Positional column access
gspread, google.oauth2   # Google Sheets libraries
"Virtual Session Import"  # Old sheet names

# Pathful patterns (new)
row['Session ID'], row['Title']  # Named column access
openpyxl, pandas  # Excel libraries
pathful_session_id  # Pathful-specific field
```

### Consolidation Strategy

1. Keep the Pathful approach as canonical
2. Don't delete old code immediately — comment it out with `# DEPRECATED: Google Sheets approach`
3. Add logging to deprecated paths to see if they're still being hit
4. After 30 days with no hits, delete

### Matching Logic Consolidation

Current matching should follow this exact hierarchy:

```python
def match_or_create_event(row, import_batch_id):
    """
    Match hierarchy:
    1. Exact match on pathful_session_id
    2. Fuzzy match on title + date (within same day)
    3. Create new
    """
    session_id = row.get('Session ID')
    title = row.get('Title', '').strip()
    date = parse_date(row.get('Date'))

    # 1. Try session ID match
    if session_id:
        event = Event.query.filter_by(pathful_session_id=session_id).first()
        if event:
            return event, 'matched_session_id'

    # 2. Try title + date match
    if title and date:
        event = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.title == title,
            func.date(Event.start_date) == date.date()
        ).first()
        if event:
            # Backfill session_id if we matched by title+date
            if session_id and not event.pathful_session_id:
                event.pathful_session_id = session_id
            return event, 'matched_title_date'

    # 3. Create new
    event = Event(
        type=EventType.VIRTUAL_SESSION,
        title=title,
        start_date=date,
        pathful_session_id=session_id,
        import_source='pathful_direct',
        # ... other fields
    )
    db.session.add(event)
    return event, 'created'
```

---

## Phase D-1: Flagging Notes

### Flag Creation Pattern

Use a helper to avoid duplicate flags:

```python
def create_flag_if_not_exists(event, flag_type, created_by='system'):
    """Create flag only if no unresolved flag of this type exists."""
    existing = EventFlag.query.filter_by(
        event_id=event.id,
        flag_type=flag_type,
        resolved_at=None  # Only check unresolved
    ).first()

    if existing:
        return existing  # Already flagged

    flag = EventFlag(
        event_id=event.id,
        flag_type=flag_type,
        created_by=created_by
    )
    db.session.add(flag)
    return flag
```

### Auto-Resolution Pattern

When the underlying issue is fixed, resolve the flag automatically:

```python
def on_teacher_tagged(event, teacher):
    """Called when a teacher is tagged to an event."""
    # ... add teacher logic ...

    # Auto-resolve MISSING_TEACHER flag
    flag = EventFlag.query.filter_by(
        event_id=event.id,
        flag_type=FlagType.MISSING_TEACHER,
        resolved_at=None
    ).first()

    if flag:
        flag.resolved_at = datetime.utcnow()
        flag.resolved_by = current_user.id
        flag.resolution_notes = f"Auto-resolved: Teacher {teacher.name} tagged"
```

### When to Scan for Flags

Run the flag scanner:
- After each import completes (for imported events)
- As a nightly job (catch any stragglers)
- On-demand via admin action (if needed)

Don't scan on every event save — that's too expensive.

---

## Phase D-2: Cancellation Reason Notes

### Validation Location

Put validation in the model or a service layer, not just the route:

```python
class Event(db.Model):
    # ... fields ...

    def set_cancellation_reason(self, reason, notes=None, user=None):
        """Set cancellation reason with validation."""
        if self.status != EventStatus.CANCELLED:
            raise ValueError("Can only set cancellation reason for cancelled events")

        if reason == CancellationReason.OTHER:
            if not notes or len(notes.strip()) < 10:
                raise ValueError("Notes required for 'Other' reason (min 10 chars)")

        old_reason = self.cancellation_reason
        self.cancellation_reason = reason
        self.cancellation_notes = notes
        self.cancellation_set_by = user.id if user else None
        self.cancellation_set_at = datetime.utcnow()

        # Return old value for audit logging
        return old_reason
```

### Import Preservation

In the import logic, check before overwriting:

```python
def update_event_from_import(event, row):
    """Update event fields from import row."""
    # These fields always update from import
    event.title = row.get('Title', '').strip()
    event.start_date = parse_date(row.get('Date'))
    # ... etc

    # Status: update only if not manually changed
    new_status = map_pathful_status(row.get('Status'))
    if event.status != new_status:
        # Check if this looks like a manual override
        # (e.g., user set to CANCELLED with a reason)
        if event.cancellation_reason and event.status == EventStatus.CANCELLED:
            # User manually cancelled with reason — don't change status
            pass
        else:
            event.status = new_status

    # Cancellation reason: NEVER overwrite from import
    # (Pathful doesn't provide this, and we don't want to clear manual entries)
```

---

## Phase D-3: District Admin Scoping Notes

### The Scoping Helper Pattern

Create a reusable scoping pattern:

```python
# In a utils/scoping.py or similar

def get_user_scope(user):
    """Return scope info for user."""
    if user.role in ['admin', 'user']:
        return {'type': 'global'}

    if user.role == 'district_admin':
        district_ids = [d.id for d in user.districts]
        school_ids = db.session.query(School.id).filter(
            School.district_id.in_(district_ids)
        ).all()
        school_ids = [s[0] for s in school_ids]
        return {
            'type': 'district',
            'district_ids': district_ids,
            'school_ids': school_ids
        }

    if user.role == 'district_viewer':
        # Same logic but will be used for read-only
        # ...

    return {'type': 'none'}


def apply_event_scope(query, user):
    """Apply user's scope to an event query."""
    scope = get_user_scope(user)

    if scope['type'] == 'global':
        return query

    if scope['type'] == 'district':
        return query.filter(Event.school_id.in_(scope['school_ids']))

    # No access
    return query.filter(False)
```

### Permission Check Pattern

For edit operations, use a decorator or explicit check:

```python
from functools import wraps

def requires_event_edit_permission(f):
    """Decorator to check event edit permission."""
    @wraps(f)
    def decorated(event_id, *args, **kwargs):
        event = Event.query.get_or_404(event_id)

        if not can_edit_event(current_user, event):
            abort(403, "You don't have permission to edit this event")

        return f(event_id, *args, **kwargs)
    return decorated


def can_edit_event(user, event):
    """Check if user can edit this event."""
    scope = get_user_scope(user)

    if scope['type'] == 'global':
        return True

    if scope['type'] == 'district':
        return event.school_id in scope['school_ids']

    return False
```

### Field-Level Restrictions

District admins have limited edit capabilities:

```python
DISTRICT_ADMIN_EDITABLE_FIELDS = {
    'teachers',  # Can tag/untag
    'presenters',  # Can tag/untag
    'cancellation_reason',
    'cancellation_notes',
    # Status: only Draft → Cancelled
}

DISTRICT_ADMIN_STATUS_TRANSITIONS = {
    EventStatus.DRAFT: [EventStatus.CANCELLED],
    # No other transitions allowed
}

def can_district_admin_change_status(old_status, new_status):
    allowed = DISTRICT_ADMIN_STATUS_TRANSITIONS.get(old_status, [])
    return new_status in allowed
```

---

## Phase D-4: Audit Logging Notes

### Logging Helper

Keep it simple and consistent:

```python
def log_event_change(event, action, user=None, field_name=None,
                     old_value=None, new_value=None,
                     source='manual', notes=None):
    """Create audit log entry."""
    log = VirtualEventAuditLog(
        event_id=event.id,
        user_id=user.id if user else None,
        user_role=user.role if user else 'system',
        user_district_id=_get_user_primary_district(user),
        action=action,
        field_name=field_name,
        old_value=_serialize_value(old_value),
        new_value=_serialize_value(new_value),
        source=source,
        notes=notes
    )
    db.session.add(log)
    return log


def _get_user_primary_district(user):
    """Get primary district ID for district admins."""
    if not user or user.role != 'district_admin':
        return None
    if user.districts:
        return user.districts[0].id
    return None


def _serialize_value(value):
    """Convert value to string for storage."""
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return value.name
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)
```

### Where to Log

Log at the service layer, not the route layer. This ensures logging happens regardless of how the change is triggered:

```python
# services/event_service.py

def tag_teacher_to_event(event, teacher, user):
    """Tag a teacher to an event with logging."""
    # Check if already tagged
    existing = EventTeacher.query.filter_by(
        event_id=event.id,
        teacher_id=teacher.id
    ).first()

    if existing:
        return existing  # Already tagged, no-op

    # Create association
    et = EventTeacher(event_id=event.id, teacher_id=teacher.id)
    db.session.add(et)

    # Log it
    log_event_change(
        event=event,
        action=AuditAction.TEACHER_ADDED,
        user=user,
        field_name='teachers',
        old_value=None,
        new_value=teacher.email
    )

    # Auto-resolve flag
    resolve_flag_if_exists(event, FlagType.MISSING_TEACHER, user)

    return et
```

### Import Logging

For imports, log with source='import' and user=None:

```python
def import_event(row, import_batch_id):
    event, match_type = match_or_create_event(row, import_batch_id)

    if match_type == 'created':
        log_event_change(
            event=event,
            action=AuditAction.IMPORTED,
            source='import',
            notes=f"Import batch {import_batch_id}"
        )
    else:
        log_event_change(
            event=event,
            action=AuditAction.UPDATED_VIA_IMPORT,
            source='import',
            notes=f"Import batch {import_batch_id}, matched by {match_type}"
        )
```

---

## Gotchas and Edge Cases

### 1. Events Without Schools

Some virtual events might not have a school assigned. Decision needed:

**Option A**: Only staff can edit school-less events (district admins can't)
**Option B**: Require school assignment during import
**Option C**: Treat school-less as "global" (probably bad)

**Recommendation**: Option A — staff-only for orphan events

### 2. Multi-District Users

A district admin might be assigned to multiple districts. The scoping logic handles this, but:

- Audit log should capture their "primary" district (first in list)
- Consider showing which "hat" they're wearing in UI
- Filters should work across all their districts

### 3. School District Changes

If a school moves from District A to District B:

- Events stay with the school
- District admin access changes accordingly
- Historical audit logs still show the old district_id at time of edit

This is probably fine — just be aware.

### 4. Concurrent Edits

Two users edit the same event simultaneously:

- Last write wins (standard behavior)
- Both edits are logged separately
- No conflict detection needed (audit log shows what happened)

### 5. Large Imports

For very large imports (10,000+ rows):

- Consider batch commits (every 500 rows)
- Flag scanning should be batched too
- Add progress indicator to UI
- Consider async/background job for very large files

### 6. Re-Import Same File

User imports the same Pathful export twice:

- Should be idempotent
- Existing events updated, not duplicated
- No new audit log entries for "no change" updates
- Add logic to detect "nothing changed" and skip logging

```python
def update_event_from_import(event, row):
    changes = {}

    new_title = row.get('Title', '').strip()
    if event.title != new_title:
        changes['title'] = (event.title, new_title)
        event.title = new_title

    # ... repeat for other fields ...

    # Only log if something actually changed
    if changes:
        log_event_change(
            event=event,
            action=AuditAction.UPDATED_VIA_IMPORT,
            source='import',
            notes=f"Changed: {list(changes.keys())}"
        )

    return bool(changes)
```

---

## Testing Strategy

### Unit Tests

- Scoping helpers return correct school IDs
- Validation functions catch invalid states
- Logging helper creates correct entries
- Flag creation avoids duplicates

### Integration Tests

- Full import → flag → resolve workflow
- District admin can edit their schools
- District admin cannot edit other schools
- Re-import preserves manual changes

### Manual Testing Checklist

- [ ] Import a fresh Pathful export
- [ ] Verify flags created for draft+past events
- [ ] Log in as district admin
- [ ] Verify only their schools visible
- [ ] Edit an event (tag teacher)
- [ ] Verify audit log entry created
- [ ] Verify flag resolved
- [ ] Re-import same file
- [ ] Verify no duplicates, manual changes preserved

---

## File Organization Suggestion

```
routes/
  virtual/
    pathful_import.py      # Import routes
    pathful_events.py      # Event list/detail routes
    pathful_flags.py       # Flag queue routes (new)
    pathful_audit.py       # Audit log routes (new)

services/
  event_service.py         # Event business logic
  flag_service.py          # Flag creation/resolution (new)
  audit_service.py         # Audit logging (new)
  scoping_service.py       # User scope helpers (new)

models/
  event.py                 # Event model
  event_flag.py            # EventFlag model (new)
  audit_log.py             # VirtualEventAuditLog model (new)
  enums.py                 # All enums in one place
```

---

## Questions to Resolve Before Coding

1. **Orphan events (no school)** — Staff-only edit access?
2. **Multi-district users** — Show district picker or auto-expand scope?
3. **Audit retention** — How long to keep logs? Forever?
4. **Flag notifications** — Email district admins about new flags?
5. **Bulk operations** — Allow bulk tag/resolve? (Probably yes, but adds complexity)

---

## Refactor Strategy (January 2026)

### Hybrid Approach

The virtual data refactor uses a hybrid approach:

1. **Phase A: Backend Stabilization** — Add deprecation logging to legacy routes, update documentation
2. **Phase B: Page-by-Page Refactor** — Verify each page works with Pathful data, extract district code as-you-go
3. **Phase C: Final Cleanup** — Remove deprecated routes after verifying no usage

### Key Insight

The core data path (`compute_virtual_session_data` in `usage.py`) already reads from the database, **not** Google Sheets. The Google Sheets routes (lines 5519-6664) are **management** features for district reports, not data sources.

### Deprecation Tracking

All Google Sheets routes have been tagged with deprecation logging:

```python
logging.warning(
    "DEPRECATED: /usage/google-sheets route accessed by user=%s. "
    "This route is scheduled for removal.",
    current_user.username
)
```

Monitor logs for 30 days. If no access, safe to remove.

### District Code Extraction (Phase B)

When refactoring each page, extract district-specific logic to `routes/district/`:

- `virtual_usage_district` → `routes/district/virtual_usage.py`
- `virtual_district_teacher_breakdown` → `routes/district/teacher_breakdown.py`
- `compute_virtual_session_district_data` → `services/district_virtual_service.py`

---

*Created: January 30, 2026*
*Updated: January 31, 2026 — Added refactor strategy section*

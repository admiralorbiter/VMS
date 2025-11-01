# Timestamp Standards for VMS

**Last Updated:** 2025-10-31
**Status:** Active Standard

## Overview

This document establishes the standard pattern for handling timestamps in VMS models. Following these standards ensures consistency, reliability, and future Python compatibility.

## The Standard

### ✅ Correct Pattern (Database-Side Defaults)

**Always use database-side defaults for timestamp columns:**

```python
from sqlalchemy.sql import func
from sqlalchemy import Column, DateTime

class MyModel(db.Model):
    __tablename__ = "my_model"

    id = Column(Integer, primary_key=True)

    # Single timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamp with auto-update
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
```

### ❌ Wrong Pattern 1 (Python-Side Default - DEPRECATED)

**DO NOT use:** `default=datetime.utcnow`

```python
# BAD - Will be removed in Python 3.15
created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
```

**Why?** `datetime.utcnow()` is deprecated in Python 3.12+ and will be removed in Python 3.15.

### ❌ Wrong Pattern 2 (Lambda Default - BUGGY)

**DO NOT use:** `default=lambda: datetime.now(timezone.utc)`

```python
# BAD - Lambda evaluated only once at class definition!
created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

**Why?** The lambda is evaluated **once** when the class is defined, not when each instance is created. This means all instances get the same timestamp!

### ❌ Wrong Pattern 3 (Method Call Default)

**DO NOT use:** `default=datetime.now(timezone.utc)`

```python
# BAD - Evaluated once at class definition
created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
```

**Why?** Same issue as lambda - evaluated once when the model is imported.

## Key Requirements

### 1. Always Use `timezone=True`

All DateTime columns **must** include `timezone=True`:

```python
# Good
created_at = Column(DateTime(timezone=True), server_default=func.now())

# Bad - naive datetime
created_at = Column(DateTime, server_default=func.now())
```

### 2. Always Use `func.now()`

Use SQLAlchemy's `func.now()`, not Python's `datetime`:

```python
from sqlalchemy.sql import func

# Good
created_at = Column(DateTime(timezone=True), server_default=func.now())

# Bad
from datetime import datetime, timezone
created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
```

### 3. Use `server_default`, Not `default`

The key difference:

- `default=...` - Python-side, evaluated by SQLAlchemy
- `server_default=...` - Database-side, evaluated by PostgreSQL/SQLite

```python
# Good - Database evaluates
created_at = Column(DateTime(timezone=True), server_default=func.now())

# Bad - Python evaluates
created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
```

### 4. Auto-Update Pattern

For `updated_at` columns, use `onupdate=func.now()`:

```python
updated_at = Column(
    DateTime(timezone=True),
    server_default=func.now(),
    onupdate=func.now()
)
```

## Exception: Python-Side Timestamps in Methods

**It IS acceptable** to use `datetime.now(timezone.utc)` in model methods:

```python
from datetime import datetime, timezone

class ValidationRun(db.Model):
    def mark_completed(self):
        """Mark the validation run as completed."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)  # ✅ OK in methods
        self.progress_percentage = 100
```

**When to use Python-side:**
- Setting timestamps in methods (not column defaults)
- Calculating time differences
- Business logic that manipulates dates
- Bulk operations where you set timestamps manually

**When to use database-side:**
- Column defaults for `created_at`, `updated_at`
- Any automatic timestamp assignment
- Default values in model definitions

## Migration Guide

### Migrating Existing Models

To update existing models with the old pattern:

#### Step 1: Update Column Definition

**Before:**
```python
created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
```

**After:**
```python
from sqlalchemy.sql import func
created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
```

#### Step 2: Create Alembic Migration

```bash
alembic revision -m "standardize_timestamps_to_server_default"
```

In the migration file:

```python
def upgrade():
    # Add server_default to existing columns
    op.alter_column('table_name', 'created_at',
                    server_default=func.now())
    op.alter_column('table_name', 'updated_at',
                    server_default=func.now(),
                    existing_onupdate=func.now())

def downgrade():
    # Remove server_default (optional)
    op.alter_column('table_name', 'created_at', server_default=None)
    op.alter_column('table_name', 'updated_at', server_default=None, onupdate=None)
```

#### Step 3: Test Migration

Test on development database:
1. Backup database
2. Run migration
3. Verify existing records unchanged
4. Create new record - verify timestamp set
5. Update record - verify `updated_at` changes

### Common Patterns

#### Pattern 1: Simple Created Timestamp

```python
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### Pattern 2: Created + Updated

```python
class User(db.Model):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
```

#### Pattern 3: Optional Timestamp

```python
class Event(db.Model):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)  # No default
```

## Database Compatibility

### SQLite
- `func.now()` works correctly
- Stores UTC timestamps
- Proper timezone handling

### PostgreSQL (Production)
- `func.now()` maps to `NOW()` function
- Native timezone support
- Index-friendly

### Testing
- Use SQLite for unit tests (faster)
- PostgreSQL for integration tests
- Both should behave identically

## Testing Considerations

### Unit Tests

Test timestamp behavior:

```python
def test_new_record_gets_timestamp(db_session):
    """New records should get current timestamp."""
    record = MyModel(name="Test")
    db_session.add(record)
    db_session.commit()

    assert record.created_at is not None
    # Should be within last second
    assert (datetime.now(timezone.utc) - record.created_at).total_seconds() < 1

def test_updated_at_changes(db_session):
    """Updated records should have updated_at changed."""
    record = MyModel(name="Original")
    db_session.add(record)
    db_session.commit()

    original_updated = record.updated_at
    time.sleep(1)  # Ensure time passes

    record.name = "Modified"
    db_session.commit()

    assert record.updated_at > original_updated
```

### Integration Tests

Verify across database engines:

```python
@pytest.mark.parametrize("engine", ["sqlite", "postgresql"])
def test_timestamp_consistency(engine):
    """Timestamps should work consistently across engines."""
    # Test implementation
```

## Common Mistakes and Fixes

### Mistake 1: Forgetting timezone=True

```python
# BAD
created_at = Column(DateTime, server_default=func.now())

# GOOD
created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Mistake 2: Using datetime functions directly

```python
# BAD
from datetime import datetime
created_at = Column(DateTime(timezone=True), default=datetime.now)

# GOOD
from sqlalchemy.sql import func
created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Mistake 3: Inconsistent pattern in same model

```python
# BAD - mixing patterns
class MyModel(db.Model):
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)  # Old
    updated_at = Column(DateTime(timezone=True), server_default=func.now())  # New

# GOOD - consistent
class MyModel(db.Model):
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

## Questions to Ask

When reviewing timestamp code, ask:

1. ✅ Does it use `server_default=func.now()`?
2. ✅ Does it include `timezone=True`?
3. ✅ Is it consistent with other models?
4. ✅ Will it work in Python 3.15+?
5. ✅ Does it behave correctly across database engines?

## References

- [SQLAlchemy Column Defaults](https://docs.sqlalchemy.org/en/14/core/defaults.html)
- [Python datetime.utcnow deprecation](https://docs.python.org/3.12/library/datetime.html#datetime.datetime.utcnow)
- [SQLAlchemy func.now()](https://docs.sqlalchemy.org/en/14/core/functions.html#sqlalchemy.sql.functions.GenericFunction)

## Related Documents

- `docs/MODELS_REVIEW_REPORT.md` - Comprehensive models review
- `docs/living/Testing.md` - Testing standards
- `docs/Philosophy.md` - VMS development philosophy

---

**Questions?** Contact the development team or update this document.

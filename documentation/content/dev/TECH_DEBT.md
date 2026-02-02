# Tech Debt Tracker

This document tracks technical debt items identified during development that should be addressed in future iterations.

---

## TD-001: Inconsistent Enum vs String Storage for Role Fields

**Created:** 2026-02-02
**Priority:** Low
**Category:** Code Consistency / Type Safety

### Description

The codebase has inconsistent handling of enumerated fields:

| Field | Model | Storage Type |
|-------|-------|--------------|
| `EventStatus` | Event | Python Enum |
| `EventType` | Event | Python Enum |
| `CancellationReason` | Event | Python Enum |
| `tenant_role` | User | Plain String |

This inconsistency led to a bug where `audit_service.py:_get_user_role()` called `.value` on `tenant_role`, expecting it to be an enum.

### Root Cause

`tenant_role` was originally designed as a simple string field for flexibility, while Event fields were designed with stricter type safety using enums.

### Current Workaround

Added `hasattr` checks throughout the codebase:
```python
role_value = tenant_role.value if hasattr(tenant_role, 'value') else str(tenant_role)
```

### Proposed Solutions

**Option A: Convert `tenant_role` to Enum (Recommended)**
- Create `TenantRole` enum in `models/user.py`
- Add migration to convert existing string values
- Update all references to use enum
- Pros: Type safety, IDE autocomplete, consistent with Event model patterns
- Cons: Requires migration, more boilerplate

**Option B: Document String-Only Pattern**
- Add clear docstrings noting `tenant_role` is a string
- Add type hints: `tenant_role: Optional[str]`
- Pros: No migration needed
- Cons: Doesn't address underlying inconsistency

### Files Affected

- `models/user.py` - `tenant_role` field definition
- `services/audit_service.py` - `_get_user_role()` function
- `services/scoping.py` - Role checking functions
- Any future code that accesses `user.tenant_role`

### Related Issues

- Phase D-4 Audit Logging implementation
- Tenant user permission checks

---

*Add new tech debt items below following the same format.*

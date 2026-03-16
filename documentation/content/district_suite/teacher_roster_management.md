# Teacher Roster Management Improvement

**Status:** 📋 Proposed · **Priority:** Medium · **Created:** March 2026

> [!NOTE]
> This document is a **feature proposal** — it describes planned improvements, not current functionality. For the current teacher management workflow, see [District & Teacher Progress](../user_guide/district_teacher_progress.md).

---

## Problem Statement

Teachers are currently added to the VMS teacher roster through a **manual spreadsheet workflow**:

1. An internal VMS administrator opens or creates a Google Sheet with columns: `Building`, `Name`, `Email`, `Grade`
2. The admin adds/removes teacher rows manually
3. The admin runs the import via Polaris → the system processes the sheet (`roster_import.py`)
4. `TeacherProgress` records are created or updated, then linked to `Teacher` entities

**Pain Points:**

| Issue | Impact |
|-------|--------|
| Districts cannot add teachers themselves | Creates dependency on internal VMS staff for every roster change |
| Spreadsheet format must be exact | Column naming/ordering errors cause silent failures or import errors |
| No real-time feedback | Districts must wait for staff to run the import before seeing changes |
| Single-point-of-failure | If the spreadsheet is misconfigured, the entire import fails |
| No audit trail for individual additions | Only the bulk import is logged, not individual changes |

---

## Proposed Solutions

### Solution 1: Documented Self-Service Workflow (Short-Term)

Make the existing spreadsheet import process **district-friendly** by providing clear, step-by-step documentation that districts can follow independently.

#### What This Delivers

- A clear, visual guide for district staff to manage their own teacher roster
- Reduced dependency on internal VMS staff for routine changes
- No code changes required — operational improvement only

#### Proposed Workflow Steps

1. **Access the Google Sheet** — District admin receives a link to their district's shared teacher roster sheet
2. **Add/Edit Teachers** — Add new rows following the documented format:
   - **Building**: Exact school name (must match a school in the system)
   - **Name**: `First Last` format
   - **Email**: District email address (used as the unique identifier)
   - **Grade**: Optional grade level
3. **Trigger Import** — District admin navigates to their Polaris portal → clicks "Import Roster"
4. **Review Results** — Import summary shows records added, updated, and deactivated

#### Prerequisites

- [ ] Create a district-facing import guide (standalone page or section in user guide)
- [ ] Ensure the import UI is accessible to district admins (current role requirements may need review)
- [ ] Create a template Google Sheet with validation rules and example data
- [ ] Document common errors and troubleshooting steps

---

### Solution 2: Direct Add Feature (Long-Term — Preferred)

Add an **"Add Teacher"** button directly inside Polaris that allows district admins to add teachers without any spreadsheet dependency.

#### What This Delivers

- In-app teacher management: add, edit, deactivate teachers directly
- Real-time validation and feedback
- Individual audit trail for every change
- Eliminates spreadsheet dependency entirely

#### Feature Requirements (Proposed)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DISTRICT-601 | District admin can add a teacher via an in-app form (Building, Name, Email, Grade) | High |
| FR-DISTRICT-602 | System validates email uniqueness within the tenant before creation | High |
| FR-DISTRICT-603 | System fuzzy-matches building name to existing School records | Medium |
| FR-DISTRICT-604 | New teacher is automatically linked to a `Teacher` entity via `find_or_create_teacher()` | High |
| FR-DISTRICT-605 | District admin can edit an existing teacher's building, name, or grade | Medium |
| FR-DISTRICT-606 | District admin can deactivate a teacher (soft delete) | Medium |
| FR-DISTRICT-607 | All add/edit/deactivate actions are logged in `AuditLog` | High |
| FR-DISTRICT-608 | Bulk import via spreadsheet remains available as an alternative | Low |
| FR-DISTRICT-609 | District admin can search/filter the teacher roster by building, name, or status | Medium |

#### Technical Analysis

**Existing Patterns to Follow:**

The District Suite already implements an identical pattern for **volunteers** (Phase 3):

| Capability | Volunteers (Phase 3) | Teachers (Proposed) |
|-----------|----------------------|---------------------|
| Manual Add | `routes/district/volunteers.py` — CRUD routes + form | New routes + form needed |
| CSV/Sheet Import | `FR-SELFSERV-302` — CSV import with column mapping | Already exists (`roster_import.py`) |
| Search/Filter | `FR-SELFSERV-303` — Filter by name, org, status | Would mirror this pattern |
| Data Model | `DistrictVolunteer` association model | `TeacherProgress` already exists |
| Tenant Isolation | `FR-SELFSERV-305` — strict `tenant_id` scoping | Already enforced on `TeacherProgress` |

**Key Implementation Components:**

| Component | Effort | Notes |
|-----------|--------|-------|
| `routes/district/teachers.py` | Medium | CRUD routes, following `volunteers.py` pattern |
| `templates/district/teachers/*.html` | Medium | Form, list, detail — following volunteer template pattern |
| Teacher linking | Low | `find_or_create_teacher()` already exists in `services/teacher_service.py` |
| School matching | Low | `_find_school_by_building_name()` already exists in `utils/roster_import.py` |
| Audit logging | Low | `AuditLog` model already in use for attendance overrides |
| Permission check | Low | `@require_tenant_context` + role check (existing pattern) |

**Estimated Effort:** ~2–3 sprints (following the Phase 3 volunteer template)

---

## Decision Framework

| Factor | Solution 1 (Workflow Docs) | Solution 2 (Direct Add) |
|--------|---------------------------|------------------------|
| **Time to deliver** | Days | Weeks (2–3 sprints) |
| **Code changes** | None | Medium (~6 new files) |
| **User experience** | Improved but still spreadsheet-based | Native in-app experience |
| **Error rate** | Reduced via documentation | Eliminated via validation |
| **Scalability** | Limited — still manual | Scalable — self-service |
| **Recommendation** | ✅ Do now | ✅ Do after Phase 5 |

> [!IMPORTANT]
> **Recommendation:** Implement Solution 1 immediately to unblock districts, then pursue Solution 2 as part of a **Phase 6: Teacher Self-Service** in the District Suite roadmap.

---

## Related Documentation

- [District & Teacher Progress](../user_guide/district_teacher_progress.md) — Current user guide
- [Teacher Progress Matching](../user_guide/teacher_progress_matching.md) — Matching logic documentation
- [District Suite Phases](phases.md) — Multi-tenant development roadmap
- [Project Roadmap](../getting_started/roadmap.md) — Overall feature roadmap

---

*Last updated: March 2026*

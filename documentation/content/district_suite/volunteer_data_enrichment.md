# Volunteer Data Enrichment & Preference System

**Status:** 📋 Proposed · **Priority:** Medium · **Created:** March 2026

> [!NOTE]
> This document is a **feature proposal** — it describes planned improvements, not current functionality. No code changes have been made.

---

## Problem Statement

The system already tracks volunteer `local_status`, `is_people_of_color`, and `race_ethnicity` at the model level, but there is **no bulk import process** for staff to set these values from spreadsheet data. Additionally, there is **no preference/rating system** to flag volunteers as "Prefer" or "Avoid" for session assignments.

Currently, custom volunteer metadata lives in a staff-maintained spreadsheet that is disconnected from Polaris. This data needs to flow into the system so it can be used in reporting, session planning, and volunteer matching.

---

## Feature 1: Volunteer Enrichment Import

### What Exists Today

| Field | Model Column | Type | Current Population |
|-------|-------------|------|--------------------|
| Local Status | `Volunteer.local_status` | `LocalStatusEnum` (local / partial / non_local / unknown) | Auto-calculated from zip code + in-person event attendance; manual override via API |
| Person of Color | `Volunteer.is_people_of_color` | `Boolean` (indexed) | Not bulk-populated; used in ~20 reporting locations |
| Race/Ethnicity | `Contact.race_ethnicity` | `RaceEthnicityEnum` (12 values) | Populated from Salesforce import |

### What's Missing

A bulk import process that lets staff upload a spreadsheet to set these values across many volunteers at once. The current Salesforce import may populate some of these, but custom internal knowledge (e.g., "we know this volunteer is local because they told us") has no import path.

### Proposed Import Format

One volunteer per row, matched by email (primary key for identity resolution):

| Column | Required | Maps To | Notes |
|--------|----------|---------|-------|
| **Volunteer Name** | Yes | Display / matching fallback | First Last format |
| **Email** | Yes | Identity key | Used to match to existing `Volunteer` record |
| **Local Status** | No | `Volunteer.local_status` | Values: `local`, `partial`, `non_local`, `unknown` |
| **Person of Color** | No | `Volunteer.is_people_of_color` | Values: `TRUE` / `FALSE` |
| **Preference** | No | New `VolunteerPreference` model | Values: `prefer`, `avoid`, or blank |

> [!IMPORTANT]
> **Import rules:**
> - Email is required and used as the matching key (consistent with `find_or_create_teacher()` pattern)
> - All enrichment columns are optional — blank cells are skipped, not overwritten
> - Enrichment values override existing values only if non-blank
> - Import generates an audit log entry for compliance

### Proposed Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ENRICH-101 | Staff can upload a CSV/XLSX with volunteer enrichment data | High |
| FR-ENRICH-102 | System matches rows to existing volunteers by email (case-insensitive) | High |
| FR-ENRICH-103 | Unmatched rows are reported as warnings (not silent failures) | Medium |
| FR-ENRICH-104 | Import summary shows counts: matched, updated, skipped, unmatched | Medium |
| FR-ENRICH-105 | All field updates are logged in `AuditLog` | High |

### Technical Notes

- **Existing pattern:** Follows the same architecture as `utils/roster_import.py` (teacher roster import)
- **Matching:** Use email-first matching via `find_or_create_teacher()` pattern (already in `services/teacher_service.py`)
- **Route location:** `routes/admin/volunteer_enrichment.py` or similar
- **Estimated effort:** 1 sprint

---

## Feature 2: Volunteer Preference / Rating System

### Overview

A new system for flagging volunteers with preference indicators (Prefer / Avoid), starting simple and expandable to a full rating system.

### Phase 1 — Prefer / Avoid (Initial)

Simple binary preference tags per volunteer:

| Value | Meaning | Use Case |
|-------|---------|----------|
| **Prefer** | High priority for session assignments | Reliable, great presenter, positive feedback |
| **Avoid** | Should not be assigned to sessions | Past issues, complaints, no-shows |

### Phase 2 — Expanded Ratings (Future)

| Rating | Description |
|--------|-------------|
| Strongly Prefer | Exceptional — assign first when possible |
| Prefer | Positive — prioritize for assignments |
| Neutral | Default — no strong preference (implicit when no record exists) |
| Caution | Minor concerns — assign with awareness |
| Avoid | Do not assign — documented issues |

### Scoping: Who Can Rate?

| Role | Phase 1 (Internal) | Phase 2 (District-Facing) |
|------|-------------------|--------------------------|
| PrepKC Admin / Staff | ✅ Can set preferences globally | ✅ Can view all preferences (including tenant-set) |
| District Admin (Tenant) | ❌ Not yet | ✅ Can set preferences scoped to their tenant |
| Volunteer | ❌ | ❌ |

### Tenant Scoping

Preferences are **tenant-scoped** to support different district perspectives on the same volunteer:

- A district admin can flag a volunteer as "Prefer" or "Avoid" for their own tenant
- PrepKC admins can see preferences from all tenants for a shared volunteer (cross-tenant visibility)
- PrepKC-set preferences are global (no `tenant_id` — treated as the "system" perspective)

> [!NOTE]
> **Cross-tenant visibility** (PrepKC seeing tenant-set preferences) may be deferred if the current `DistrictVolunteer` association model doesn't easily support it. In that case, PrepKC preferences and tenant preferences operate independently, with cross-tenant aggregation as a later enhancement.

### Proposed Data Model

```
VolunteerPreference
├── id (PK)
├── volunteer_id (FK → volunteer.id)
├── tenant_id (FK → tenant.id, nullable — NULL = PrepKC global)
├── preference (Enum: PREFER / AVOID)
├── reason (Text — required, for audit trail)
├── created_by (FK → user.id)
├── created_at (DateTime)
├── updated_at (DateTime)
├── is_active (Boolean, default True — supports soft delete)
└── UniqueConstraint('volunteer_id', 'tenant_id') — one preference per volunteer per tenant
```

### Proposed Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-PREF-201 | Staff can set a Prefer or Avoid preference on a volunteer with a required reason | High |
| FR-PREF-202 | Preference is visible on the volunteer detail page | High |
| FR-PREF-203 | Preference can be removed or changed (with audit log) | Medium |
| FR-PREF-204 | Preference is visible in volunteer search results (icon or badge) | Medium |
| FR-PREF-205 | Preferences can be bulk-imported via enrichment spreadsheet (optional column) | Low |
| FR-PREF-206 | District admins can set tenant-scoped preferences (Phase 2) | Low |
| FR-PREF-207 | PrepKC admins can view tenant-set preferences on shared volunteers (Phase 2) | Low |
| FR-PREF-208 | Expanded rating scale (5-level) replaces binary Prefer/Avoid (Phase 2) | Low |

### Technical Notes

- **New model:** `VolunteerPreference` — new table, requires Alembic migration
- **New enum:** `PreferenceEnum` in `models/volunteer_enums.py`
- **UI integration:** Badge/icon on volunteer cards + detail page
- **Import integration:** Optional column in enrichment import (Feature 1)
- **Estimated effort:** 1–2 sprints (Phase 1 only)

---

## Implementation Sequence

| Order | Feature | Effort | Dependency |
|-------|---------|--------|------------|
| 1 | Enrichment Import (local status, POC flag) | 1 sprint | None — fields already exist |
| 2 | Preference Model + Internal UI | 1 sprint | None — new model |
| 3 | Preference in Enrichment Import | 0.5 sprint | Features 1 + 2 |
| 4 | District-Facing Preferences | 1 sprint | Feature 2 + tenant scoping |
| 5 | Expanded Rating Scale | 0.5 sprint | Feature 2 |
| 6 | Cross-Tenant Preference Visibility | 1 sprint | Feature 4 |

---

## Related Documentation

- [Project Roadmap](../getting_started/roadmap.md) — Overall feature roadmap
- [District Suite Phases](phases.md) — Multi-tenant development roadmap
- [Teacher Roster Management](teacher_roster_management.md) — Similar feature proposal for teacher data
- [Salesforce Import Roadmap](../developer/salesforce_import_roadmap.md) — Data import patterns

---

*Last updated: March 2026*

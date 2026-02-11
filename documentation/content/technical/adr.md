# Architecture Decision Records

Index of Architecture Decision Records (ADRs) for the VMS/Polaris system.

ADRs are immutable records of significant technical decisions that capture context, decision, and consequences.

---

## ADR Directory

### Global System Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| G-001 | Flask as Web Framework | ✅ Accepted | 2024-01 |
| G-002 | SQLite as Primary Database | ✅ Accepted | 2024-01 |
| G-003 | Vanilla JavaScript Frontend | ✅ Accepted | 2024-02 |

### Validation System Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| V-001 | 5-Tier Validation Architecture | ✅ Accepted | 2024-06 |
| V-002 | Quality Scoring Algorithm | ✅ Accepted | 2024-08 |
| V-003 | Business Rule Engine | ✅ Accepted | 2024-09 |

### Data Integration Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| D-001 | Salesforce API (Simple-Salesforce) | ✅ Accepted | 2024-03 |
| D-002 | Google Sheets Integration | ✅ Accepted | 2024-03 |
| D-003 | Daily Sync with Conflict Resolution | ✅ Accepted | 2024-04 |

### GUI Enhancement Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| U-001 | Mobile-First Responsive Design | ✅ Accepted | 2024-05 |
| U-002 | Custom CSS Design System | ✅ Accepted | 2024-05 |

---

## ADR Numbering Convention

| Prefix | Category |
|--------|----------|
| G-XXX | Global system decisions |
| V-XXX | Validation system decisions |
| D-XXX | Data integration decisions |
| U-XXX | User interface decisions |
| P-XXX | Performance decisions |
| S-XXX | Security decisions |

---

## ADR Lifecycle

| State | Description |
|-------|-------------|
| Proposed | Under consideration |
| Accepted | Approved and implemented |
| Deprecated | Superseded by newer approach |
| Archived | No longer relevant |

---

## Recent Decisions

### 2025-08-17: Removed Salesforce Pathway Import System

**Decision:** Remove complex Salesforce pathway import; replace with simpler event affiliation via `pathway_events.py`.

**What Was Removed:**
- `models/pathways.py` — Complex Pathway model
- `routes/pathways/` — Entire pathways blueprint
- `routes/reports/pathways.py` — Pathway reports
- Database tables: `pathway_contacts`, `pathway_events`

**What Was Kept:**
- `routes/events/pathway_events.py` — Unaffiliated event sync
- Simple `pathway` field in `EventAttendanceDetail`
- Pathway event types (`PATHWAY_CAMPUS_VISITS`, `PATHWAY_WORKPLACE_VISITS`)

**Benefits:**
- Simpler, maintainable codebase
- Focus on actual data relationships
- Reduced database complexity

---

## Creating New ADRs

### When to Create

- Technology choices affecting the entire system
- Architecture decisions impacting multiple components
- Integration decisions with external systems
- Data model changes affecting multiple entities
- Performance optimizations changing system behavior

### ADR Template

```markdown
---
title: "NNNN: <short decision>"
status: proposed | accepted | deprecated | archived
project: "<project_slug>"
date: YYYY-MM-DD
summary: "<one paragraph what/why>"
---

## Context
[What is the issue motivating this decision?]

## Decision
[What is the change we're proposing/doing?]

## Consequences
[What becomes easier or more difficult?]

## Alternatives Considered
[What other options were considered and why rejected?]
```

---

## Key ADR Summaries

### G-001: Flask as Web Framework

**Context:** Needed a Python web framework for VMS development.

**Decision:** Choose Flask over Django.

**Rationale:**
- Lightweight and flexible
- Python-native
- Easy PythonAnywhere deployment
- Good for solo development

### G-002: SQLite as Primary Database

**Context:** Needed database for development and production.

**Decision:** Use SQLite for both environments.

**Rationale:**
- File-based, no server setup
- Good for PythonAnywhere hosting
- Simplifies deployment

### V-001: 5-Tier Validation Architecture

**Context:** Needed comprehensive data validation.

**Decision:** Implement 5-tier system: Count, Completeness, Data Type, Relationship, Business Rules.

**Rationale:**
- Layered approach
- Configurable rules
- Comprehensive coverage

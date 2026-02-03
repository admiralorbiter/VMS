# Glossary

**Key terms and concepts used throughout VMS documentation**

---

## Systems

| Term | Definition |
|------|------------|
| **Polaris** | The core VMS application for virtual events, recruitment, dashboards, and reporting. Internal codename for the Volunteer Management System. |
| **VolunTeach** | Admin interface for event sync controls and website publishing. Syncs data from Salesforce and controls visibility on public pages. |
| **Salesforce (SF)** | Core CRM system and system of record for in-person events, volunteer data, student attendance, and email logging. |
| **Pathful** | Third-party platform for virtual event hosting. Handles signups, reminders, and attendance tracking for virtual sessions. Data is exported and imported into Polaris. |
| **VMS** | Volunteer Management System — the umbrella term for the integrated Polaris, VolunTeach, and Salesforce ecosystem. |
| **District Suite** | Multi-tenant extension allowing partner districts to run their own Polaris instance with isolated data. |

---

## Features

| Term | Definition |
|------|------------|
| **Magic Link** | A secure, single-use URL sent via email that allows teachers to access their progress data without creating an account. Links are time-limited and scope-restricted. |
| **In-Person Page Visibility** | A toggle in VolunTeach that controls whether an event appears on the public in-person events page at prepkc.org. |
| **District Linking** | The ability to associate events with specific districts, making them appear on district-specific website pages. |
| **DIA Event** | "Data in Action" events — a special event type that appears on both the main public page and the DIA-specific page automatically. |
| **Quick Create** | A feature in Polaris that allows creating new teacher or presenter records directly from the event creation form without navigating away. |
| **Presenter Recruitment View** | A Polaris dashboard showing upcoming virtual events that don't have a presenter assigned, with urgency indicators. |
| **Data Tracker** | Dashboard for monitoring data quality issues and viewing/resolving reported problems. |
| **Issue Reporting** | System allowing teachers and coordinators to flag incorrect data for review. |
| **Recruitment Notes** | Persistent notes attached to volunteer profiles to track outreach history and preferences. |
| **Cache Management** | Admin tools for refreshing pre-computed dashboard metrics and report caches. |

---

## Data Concepts

| Term | Definition |
|------|------------|
| **Source of Truth (SoT)** | The authoritative system for a given piece of data. Downstream systems copy but never edit SoT-owned fields. |
| **Normalized Email** | Email address converted to lowercase and trimmed. Used as the primary identity key for volunteers across systems. |
| **Idempotent Import** | An import that can be safely run multiple times without creating duplicates. Re-running produces the same result. |
| **Safe Merge** | Sync strategy that upserts records — updating existing records and inserting new ones — without deleting unmatched records. |
| **Tenant** | An isolated database environment for a partner district in the District Suite multi-tenant architecture. |
| **Session** | A single virtual event occurrence in Polaris (mapped from Pathful data). |
| **Event** | An in-person event managed in Salesforce and synced to VolunTeach. |

---

## Event Statuses

| Status | Definition |
|--------|------------|
| **Draft** | Event created but not yet submitted for approval. |
| **Requested** | Event submitted and awaiting confirmation from volunteers/schools. |
| **Confirmed** | Event confirmed with all parties, ready for publishing. |
| **Published** | Event visible on public website. |
| **Completed** | Event has occurred and attendance recorded. |
| **Cancelled** | Event was cancelled and will not occur. |

---

## Teacher Progress Statuses

| Status | Definition |
|--------|------------|
| **Achieved** | Teacher has completed ≥1 virtual session. |
| **In Progress** | Teacher has ≥1 future signup but 0 completed sessions. |
| **Not Started** | Teacher has no signups and 0 completed sessions. |

---

## Volunteer Statuses

| Status | Definition |
|--------|------------|
| **Local** | Volunteer is in the KC metro area (based on address analysis). |
| **Non-Local** | Volunteer is outside the KC metro area. |
| **Attended** | Volunteer attended the assigned event. |

---

## Roles

| Role | Access Level |
|------|--------------|
| **Admin** | Full system access including email templates, sync controls, and tenant management. |
| **User** | Standard staff access to events, volunteers, reports, and dashboards. |
| **District Viewer** | Read-only access to their assigned district's progress dashboard. |
| **District Admin** | (District Suite) Full access within their tenant's Polaris instance. |
| **District Coordinator** | (District Suite) Event and volunteer management within their tenant. |

---

## Abbreviations

| Abbrev. | Full Term |
|---------|-----------|
| **FR** | Functional Requirement (e.g., FR-INPERSON-101) |
| **TC** | Test Case (e.g., TC-001) |
| **US** | User Story (e.g., US-101) |
| **UC** | Use Case (e.g., UC-1) |
| **ADR** | Architecture Decision Record |
| **API** | Application Programming Interface |
| **CSV** | Comma-Separated Values (export format) |
| **ETL** | Extract, Transform, Load (data pipeline) |
| **KPI** | Key Performance Indicator |
| **POL** | Polaris |
| **RBAC** | Role-Based Access Control |
| **SF** | Salesforce |
| **SoT** | Source of Truth |
| **VT** | VolunTeach |
| **PATH** | Pathful |
| **WEB** | Public Website |

---

## Related Documentation

- [Getting Started](index) — System overview and documentation structure
- [Architecture](../technical/architecture) — Integration flows and source-of-truth ownership
- [RBAC Matrix](../security/rbac_matrix) — Complete role permissions

---

*Last updated: February 2026 · Version 1.1*

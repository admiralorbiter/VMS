# Reporting Requirements

**Polaris**

---

## Quick Navigation

| Category | Description |
|----------|-------------|
| [Dashboards](#dashboards) | Core reporting dashboards |
| [Ad Hoc & Export](#ad-hoc--export) | One-off queries and exports |
| [Partner Reconciliation](#partner-reconciliation) | External list matching |
| [Cache Management](#cache-management) | Performance optimization |
| [Year-End Reporting](#year-end-reporting) | District annual summaries |

---

## Dashboards

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-reporting-401"></a>**FR-REPORTING-401** | Polaris shall provide a volunteer thank-you dashboard/report showing top volunteers by hours and/or events. | TC-700–TC-703 | [US-701](user-stories#us-701) |
| <a id="fr-reporting-402"></a>**FR-REPORTING-402** | Polaris shall provide an organization participation dashboard/report. | TC-720–TC-722 | [US-702](user-stories#us-702) |
| <a id="fr-reporting-403"></a>**FR-REPORTING-403** | Polaris shall provide district/school impact dashboards. | TC-740–TC-744 | [US-703](user-stories#us-703) |
| <a id="fr-reporting-404"></a>**FR-REPORTING-404** | Polaris shall report at minimum: unique students reached, unique volunteers reached, total volunteer hours, and unique organizations engaged. | TC-740, TC-741 | [US-703](user-stories#us-703) |

---

## Ad Hoc & Export

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-reporting-405"></a>**FR-REPORTING-405** | Polaris shall support ad hoc querying/reporting for one-off participation questions (e.g., counts for a specific org). | TC-760–TC-762 | [US-704](user-stories#us-704) |
| <a id="fr-reporting-406"></a>**FR-REPORTING-406** | Polaris shall provide export outputs (e.g., CSV, Excel) suitable for grant and district reporting workflows. | TC-780–TC-783 | [US-701](user-stories#us-701), [US-702](user-stories#us-702), [US-703](user-stories#us-703), [US-704](user-stories#us-704) |

---

## Partner Reconciliation

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-reporting-407"></a>**FR-REPORTING-407** | The system shall generate **partner reconciliation reports** (e.g., KCTAA) matching external lists against internal volunteer data. | TC-800 | [US-705](user-stories#us-705) |
| <a id="fr-reporting-408"></a>**FR-REPORTING-408** | The system shall support **fuzzy name matching** (using difflib) for partner reconciliation to identify near-matches across systems. | TC-801 | [US-705](user-stories#us-705) |
| <a id="fr-reporting-409"></a>**FR-REPORTING-409** | The reconciliation report shall categorize matches as: **Exact Match**, **Fuzzy Match** (with confidence score), or **No Match**. | TC-802 | [US-705](user-stories#us-705) |

---

## Cache Management

> [!NOTE]
> The Cache Management System provides high-performance dashboard refreshes via a tiered caching strategy.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-reporting-420"></a>**FR-REPORTING-420** | The system shall implement a **tiered cache architecture** with Hot Cache (in-memory, TTL ≤ 5 min) and Warm Cache (database-backed, TTL configurable). | *TBD* | *Technical* |
| <a id="fr-reporting-421"></a>**FR-REPORTING-421** | Dashboard data shall be served from cache when available, with automatic refresh on cache miss. | *TBD* | *Technical* |
| <a id="fr-reporting-422"></a>**FR-REPORTING-422** | The system shall support **manual cache invalidation** triggers for specific dashboards or all caches. | *TBD* | *Technical* |
| <a id="fr-reporting-423"></a>**FR-REPORTING-423** | Cache status shall be visible on the admin dashboard showing: last refresh time, cache hit rate, and staleness indicators. | *TBD* | *Technical* |
| <a id="fr-reporting-424"></a>**FR-REPORTING-424** | The system shall automatically warm caches for frequently-accessed dashboards on startup and after scheduled data imports. | *TBD* | *Technical* |
| <a id="fr-reporting-425"></a>**FR-REPORTING-425** | Cache keys shall incorporate filter parameters (date range, district, school) to serve filtered views without re-computation. | *TBD* | *Technical* |

---

## Year-End Reporting

> [!NOTE]
> Year-End Reporting provides district-scoped annual summaries for grant reporting and stakeholder communications.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-reporting-430"></a>**FR-REPORTING-430** | The system shall provide a **District Year-End Report** aggregating annual metrics for a selected district and academic year. | *TBD* | *Technical* |
| <a id="fr-reporting-431"></a>**FR-REPORTING-431** | The year-end report shall include the following **auto-computed core metrics** per district per academic year: total events (in-person + virtual split), total students reached (in-person actual + virtual estimated), unique students (in-person only), total volunteer engagements, unique volunteers, total volunteer hours, unique organizations engaged, schools served, and career clusters. | TC-740, TC-741 | *Technical* |
| <a id="fr-reporting-431a"></a>**FR-REPORTING-431a** | The year-end report shall include a **program-type breakdown** computing student counts (total + unique) per program: Career Jumping, Career Speakers, Career/College Fair (HS students only), HealthStart, BFI, DIA, SLA, Client Connected Projects, P2T, P2GD, Math Relays (event count only), and Connector Sessions (teacher count + estimated students). See [Metrics Bible — YE-C4](metrics-bible#ye-c4) for exact EventType mappings. | *TBD* | *Technical* |
| <a id="fr-reporting-431b"></a>**FR-REPORTING-431b** | The year-end report shall include a **manual input layer** for program outcomes not derivable from event attendance: Math Relays splits (HS/JR participants, HS/MS awards), DIA IRC credentials earned, P2GD dual credit, P2T completions, CNA/CMA students, college credits (students + total), Careers on Wheels, and Holland 1916 visits. Stored in `DistrictManualInput` model. See [Metrics Bible — YE-C6](metrics-bible#ye-c6). | *TBD* | *Technical* |
| <a id="fr-reporting-432"></a>**FR-REPORTING-432** | The year-end report shall support **comparison to previous year** showing growth/decline percentages. | *TBD* | *Technical* |

> **FR-432 Status: Deferred.** Not implemented as of May 2026. Planned for a future sprint (Session 5+). No blocking dependencies; requires historical cache to be populated for prior years first.

| <a id="fr-reporting-433"></a>**FR-REPORTING-433** | Year-end reports shall be exportable as **PDF** and **Excel** for stakeholder distribution. | *TBD* | *Technical* |

> **FR-433 Status: Partial.** Excel export implemented (`GET /reports/district/year-end/<district>/excel`). PDF export deferred — out of current sprint scope.

| <a id="fr-reporting-434"></a>**FR-REPORTING-434** | The system shall allow scheduling of **automated year-end report generation** at academic year boundaries. | *TBD* | *Technical* |

> **FR-434 Status: Deferred.** Out of sprint scope. Depends on background task infrastructure (Tier 3.4 in Development Plan).

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [Reports Overview](reports-index) — Available report types
- [Metrics Bible](metrics-bible) — Calculation definitions
- [Cache Management Guide](cache-management) — Technical implementation

---

*Last updated: May 2026 · Version 1.2 — Expanded FR-431 into 431/431a/431b; added FR-432/433/434 status notes*

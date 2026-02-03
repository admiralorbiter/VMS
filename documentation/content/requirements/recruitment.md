# Volunteer Recruitment Requirements

**Polaris + Salesforce Email Logging**

---

## Search & Filtering

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-recruit-301"></a>**FR-RECRUIT-301** | Polaris shall provide a searchable list of volunteers. | TC-300 | [US-401](user-stories#us-401) |
| <a id="fr-recruit-302"></a>**FR-RECRUIT-302** | Polaris shall support filtering/search by volunteer name, organization, role, skills, and career type. | TC-301–TC-308 | [US-401](user-stories#us-401) |
| <a id="fr-recruit-303"></a>**FR-RECRUIT-303** | Polaris shall support identifying volunteers who have participated in virtual activities (including virtual-only). | TC-320–TC-322 | [US-401](user-stories#us-401) |

---

## Participation & Communication History

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-recruit-304"></a>**FR-RECRUIT-304** | Polaris shall display volunteer participation history including most recent volunteer date. | TC-340–TC-343 | [US-402](user-stories#us-402) |
| <a id="fr-recruit-305"></a>**FR-RECRUIT-305** | Polaris shall display communication history sourced from Salesforce email logging (Gmail add-on), including most recent contact date. | TC-360–TC-361 | [US-404](user-stories#us-404) |
| <a id="fr-recruit-306"></a>**FR-RECRUIT-306** | Polaris shall allow staff to record recruitment notes and outcomes where Polaris provides that UI. | TC-380–TC-381 | [US-403](user-stories#us-403) |
| <a id="fr-recruit-308"></a>**FR-RECRUIT-308** | Polaris shall import/sync logged email communication records from Salesforce and associate them to the correct volunteer/person. | TC-360–TC-366 | [US-404](user-stories#us-404) |
| <a id="fr-recruit-309"></a>**FR-RECRUIT-309** | Polaris shall distinguish "no communication logged" from "communication sync failure" (visibility into data completeness). | TC-363, TC-364 | [US-405](user-stories#us-405) |

---

## Intelligent Matching

The intelligent matching system is a multi-dimensional ranking engine that automates identification of optimal volunteer candidates for specific events.

### Core Matching Requirements

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-recruit-310"></a>**FR-RECRUIT-310** | The system shall rank volunteer candidates using a multi-dimensional scoring algorithm that evaluates: event type match, skill overlap, title/industry match, engagement level, recency, frequency, and locality. | TC-400–TC-410 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-311"></a>**FR-RECRUIT-311** | The system shall support user-defined **custom keywords** that take highest priority in matching, overriding automatic keyword derivation. | TC-411 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-312"></a>**FR-RECRUIT-312** | The system shall provide a "Match Score Breakdown" in the UI showing exactly which factors contributed to each candidate's score. | TC-412 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-313"></a>**FR-RECRUIT-313** | Matching results shall be cached in `RecruitmentCandidatesCache` with support for manual refresh when data changes. | TC-413 | *Technical* |

### Keyword Derivation

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-recruit-320"></a>**FR-RECRUIT-320** | The system shall derive matching keywords using a tiered fallback strategy: (1) Custom keywords, (2) Event type keywords, (3) Text analysis, (4) Pattern recognition, (5) Universal fallback. | TC-420 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-321"></a>**FR-RECRUIT-321** | For **event type-based keywords**, the system shall use pre-curated keyword sets mapped to event types (e.g., DATA_VIZ → data, analytics, visualization; CAREER_FAIR → career, networking, resume). | TC-421 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-322"></a>**FR-RECRUIT-322** | For **text analysis**, the system shall extract professional domains (Technology, Healthcare, etc.), tools (Excel, Tableau, SQL, etc.), and level indicators (entry-level, senior, director) from event titles and descriptions. | TC-422 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-323"></a>**FR-RECRUIT-323** | For **pattern recognition**, the system shall identify semantic patterns like "How to..." → tutorial, "Career in..." → career guidance, "Building..." → hands-on project work. | TC-423 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-324"></a>**FR-RECRUIT-324** | For **semantic context**, the system shall understand emotional/contextual meaning (e.g., "inspiring" → motivation, "solving challenges" → problem-solving, "leading" → leadership). | TC-424 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-325"></a>**FR-RECRUIT-325** | If all keyword derivation levels fail, the system shall fallback to universal keywords: volunteer, event, participation. | TC-425 | *Technical* |

### Scoring Weights

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-recruit-330"></a>**FR-RECRUIT-330** | **Event Type Match** shall contribute +1.0 points per matching event type in volunteer history. | TC-430 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-331"></a>**FR-RECRUIT-331** | **Skill Overlap** shall contribute +0.8 points per matching skill between event needs and volunteer profile. | TC-431 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-332"></a>**FR-RECRUIT-332** | **Title/Industry Match** shall contribute +0.6 points when volunteer's professional profile aligns with event domain. | TC-432 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-333"></a>**FR-RECRUIT-333** | **Connector Profile** shall contribute +0.4 points for volunteers with established engagement history. | TC-433 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-334"></a>**FR-RECRUIT-334** | **Recency Boost** shall contribute +0.35 points for activity within 90 days, +0.15 for 180 days. | TC-434 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-335"></a>**FR-RECRUIT-335** | **Frequency** shall contribute +0.3 points for 10+ events, +0.2 for 5+, +0.1 for 2+ events. | TC-435 | [US-406](user-stories#us-406) |
| <a id="fr-recruit-336"></a>**FR-RECRUIT-336** | **Locality** shall contribute +0.2 points for local volunteers, +0.1 for partial-local. | TC-436 | [US-406](user-stories#us-406) |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [Volunteer Search Guide](user-guide-volunteer-recruitment) — User documentation

---

*Last updated: February 2026 · Version 1.1*

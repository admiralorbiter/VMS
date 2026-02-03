# Student Roster & Attendance Requirements

**Salesforce (Source) → Polaris (Reporting)**

> [!NOTE]
> **Current Implementation:** Student rostering and attendance is managed in **Salesforce** and synced to Polaris via periodic manual imports. Future enhancements may add additional attendance capture methods directly in Polaris.

---

## Core Requirements

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-student-601"></a>**FR-STUDENT-601** | The system shall support associating students with events (student roster). **Source: Salesforce → Synced to Polaris.** | TC-600–TC-603 | [US-601](user-stories#us-601) |
| <a id="fr-student-602"></a>**FR-STUDENT-602** | The system shall support recording student attendance status per student-event participation. **Source: Salesforce → Synced to Polaris.** | TC-610–TC-613 | [US-602](user-stories#us-602) |
| <a id="fr-student-603"></a>**FR-STUDENT-603** | Polaris reporting shall use student attendance to compute unique students reached and other impact metrics by school and district. | TC-620–TC-624 | [US-603](user-stories#us-603) |
| <a id="fr-student-604"></a>**FR-STUDENT-604** | Reporting users shall be able to view student reach metrics by district, school, event type, and date range. | — | [US-603](user-stories#us-603) |
| <a id="fr-student-605"></a>**FR-STUDENT-605** | For virtual events, the system shall estimate student reach at **25 students per session** for reporting purposes (individual students are not tracked). | *Implicit* | *Technical* |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [Student Roster Guide](user-guide-student-management) — User documentation

---

*Last updated: February 2026 · Version 1.0*

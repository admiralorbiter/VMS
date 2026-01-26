# Test Pack 5: Student Attendance

Roster + attendance + impact metrics

> [!INFO]
> **Coverage**
> [FR-STUDENT-601](requirements#fr-student-601)–[FR-STUDENT-604](requirements#fr-student-604) (Student roster + attendance + metrics)

---

## Test Data

**District:** KCK (School A, School B)

#### Students

- S1, S2, S3 — School A
- S4, S5 — School B

#### Events + Attendance

- **E1 (School A):** S1=Attended, S2=Attended, S3=Absent
- **E2 (School B):** S2=Attended, S4=Attended, S5=Attended

**Expected unique attended:** S1, S2, S4, S5 = **4**

## Test Cases

> [!NOTE]
> **About These Tests**
> - **TC-600–TC-613 (Roster & Attendance):** These operations are performed **in Salesforce**. Polaris receives this data via periodic manual student imports (see [Playbook D3](import_playbook#d3-student-import)).
> - **TC-620–TC-691 (Reporting & Filters):** These are verified in Polaris after sync completes.
> - **Sync Verification:** See [Test Pack 7](test_packs/test_pack_7) for data sync integrity tests.

> [!TIP]
> **Virtual Events:** Virtual events do not track individual students. Student reach is estimated at **25 students per session**. This is reflected in reporting metrics but not tested via individual roster tests.

### A. Roster Creation

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-600"></a>**TC-600** | Add students to E1 | Roster entries created | Manual (Salesforce) | 2026-01-25 |
| <a id="tc-601"></a>**TC-601** | Add students to E2 | Entries created | Manual (Salesforce) | 2026-01-25 |
| <a id="tc-602"></a>**TC-602** | Duplicate prevention | No double-counting | Manual (Salesforce) | 2026-01-25 |
| <a id="tc-603"></a>**TC-603** | Bulk import | Multiple students added efficiently | Manual (Salesforce) | 2026-01-25 | Bulk import | Multiple students added efficiently |

### B. Attendance Recording

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-610"></a>**TC-610** | Record E1 attendance | Statuses saved | Manual (Salesforce) | 2026-01-25 |
| <a id="tc-611"></a>**TC-611** | Record E2 attendance | Statuses saved | Manual (Salesforce) | 2026-01-25 |
| <a id="tc-612"></a>**TC-612** | Edit propagates | S3 Absent→Attended updates metrics | Manual (Salesforce) | 2026-01-25 |
| <a id="tc-613"></a>**TC-613** | Attendance status validation | Only valid statuses accepted | Manual (Salesforce) | 2026-01-25 | Attendance status validation | Only valid statuses accepted |

### C. Polaris Reporting

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-620"></a>**TC-620** | District unique students | =4 (attendance-based) | Automated (Polaris) | TBD |
| <a id="tc-621"></a>**TC-621** | School A breakdown | =2 (S1, S2) | Automated (Polaris) | TBD |
| <a id="tc-622"></a>**TC-622** | School B breakdown | =3 (S2, S4, S5) | Automated (Polaris) | TBD |
| <a id="tc-623"></a>**TC-623** | Multi-event student | S2 counted once at district level | Automated (Polaris) | TBD |
| <a id="tc-624"></a>**TC-624** | Edit affects metrics | Total becomes 5 after TC-612 | Automated (Polaris) | TBD | Edit affects metrics | Total becomes 5 after TC-612 |

### D. Filters

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-640"></a>**TC-640** | Event type filter | In-person only works | Automated (Polaris) | TBD |
| <a id="tc-641"></a>**TC-641** | Date range filter | Excludes out-of-range events | Automated (Polaris) | TBD |
| <a id="tc-642"></a>**TC-642** | District filter | Only KCK events contribute | Automated (Polaris) | TBD | District filter | Only KCK events contribute |

### E. Privacy

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-690"></a>**TC-690** | District Viewer access | Aggregates only, no student PII | Automated (Polaris) | TBD |
| <a id="tc-691"></a>**TC-691** | Internal role access | Allowed per policy | Automated (Polaris) | TBD | Internal role access | Allowed per policy |

---

*Last updated: January 2026*
*Version: 1.0*

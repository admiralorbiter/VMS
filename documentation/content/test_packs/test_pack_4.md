# Test Pack 4: Volunteer Recruitment

Search + communication history + sync health

> [!INFO]
> **Coverage**
> [FR-RECRUIT-301](requirements#fr-recruit-301)–[FR-RECRUIT-306](requirements#fr-recruit-306) (Search + history), [FR-RECRUIT-308](requirements#fr-recruit-308)–[FR-RECRUIT-309](requirements#fr-recruit-309) (Comm sync + health UX)

---

## Test Data: Volunteer Set

| ID | Name | Org | Career | Local | Participation | Comms |
|----|------|-----|--------|-------|---------------|-------|
| V1 | Victor Cyber | TechCorp | Technology | Yes | In-person + Virtual | Yes |
| V2 | Ella Data | TechCorp | Technology | No | Virtual-only | Yes |
| V3 | Sam Teacher | EduOrg | Education | Yes | In-person only | No |
| V4 | Riley HR | PeopleCo | Business | Yes | None | Yes |

## Test Cases

### A. Volunteer Search

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-300"></a>**TC-300** | Name search "Vict" | Returns V1 only | Automated | 2026-01-25 |
| <a id="tc-301"></a>**TC-301** | Org filter: TechCorp | Returns V1, V2 | Automated | 2026-01-25 |
| <a id="tc-302"></a>**TC-302** | Skill filter | Returns matching volunteers | Automated | 2026-01-25 |
| <a id="tc-303"></a>**TC-303** | Career type: Education | Returns V3 | Automated | 2026-01-25 |
| <a id="tc-304"></a>**TC-304** | Local filter | Returns V1, V3, V4 | Automated | 2026-01-25 |
| <a id="tc-305"></a>**TC-305** | Combined filters | Intersection works | Manual | TBD |
| <a id="tc-306"></a>**TC-306** | Role filter | Returns matching volunteers | Automated | 2026-01-25 |
| <a id="tc-307"></a>**TC-307** | Empty search results | Clear message displayed | Automated | 2026-01-25 |
| <a id="tc-308"></a>**TC-308** | Search performance | Results load within acceptable time | Automated | 2026-01-25 |

### B. Virtual-Only

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-320"></a>**TC-320** | Virtual-only filter | Returns V2 only | Automated | 2026-01-25 |
| <a id="tc-321"></a>**TC-321** | Excludes mixed | V1 not included | Manual | TBD |
| <a id="tc-322"></a>**TC-322** | Excludes in-person only | V3 not included | Manual | TBD |

### C. Communication History

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-360"></a>**TC-360** | Comm history displays | V1 shows logged emails | Manual | TBD |
| <a id="tc-361"></a>**TC-361** | Last contacted correct | Matches most recent email | Manual | TBD |
| <a id="tc-362"></a>**TC-362** | Correct association | V2's email on V2, not V1 | Manual | TBD |
| <a id="tc-363"></a>**TC-363** | No comms state | V3 shows "No history logged" | Manual | TBD |
| <a id="tc-364"></a>**TC-364** | Sync failure state | Shows error, not "no comms" | Manual | TBD |
| <a id="tc-365"></a>**TC-365** | Idempotency | Re-sync = no duplicates | Manual | TBD |
| <a id="tc-366"></a>**TC-366** | Sync health visibility | Clear indication of sync status | Manual | TBD |

### D. Participation History

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-340"></a>**TC-340** | Participation history displays | V1 shows both in-person and virtual events | Automated | 2026-01-25 |
| <a id="tc-341"></a>**TC-341** | Most recent date correct | Matches latest participation | Automated | 2026-01-25 |
| <a id="tc-342"></a>**TC-342** | Event count accurate | Correct number of events displayed | Automated | 2026-01-25 |
| <a id="tc-343"></a>**TC-343** | No participation state | V4 shows appropriate message | Automated | 2026-01-25 |

### E. Recruitment Notes

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-380"></a>**TC-380** | Record recruitment note | Note saved and displayed | Manual | TBD |
| <a id="tc-381"></a>**TC-381** | Note outcome tracking | Outcome recorded correctly | Manual | TBD |

---

*Last updated: January 2026*
*Version: 1.1*

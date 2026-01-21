# Test Pack 3: Virtual Events

Polaris creation + Pathful import + historical data

> [!INFO]
> **Coverage**
> [FR-201](requirements#fr-201)–[FR-206](requirements#fr-206) (Virtual events), [FR-208](requirements#fr-208) (Local/non-local), [FR-204](requirements#fr-204) (Historical import), [FR-210](requirements#fr-210)–[FR-219](requirements#fr-219) (Presenter recruitment)

---

## Test Data

- **VE1 Virtual Career Talk** — Future date
- **VE2 Virtual Panel** — Future date
- **P1 Local Presenter** — local=true
- **P2 NonLocal Presenter** — local=false

## Test Cases

### A. Virtual Event Creation

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-200"></a>**TC-200** | Create event | Persists and reloads |
| <a id="tc-201"></a>**TC-201** | Edit event | Changes persist |
| <a id="tc-202"></a>**TC-202** | Tag teacher (SF search) | Link persists after save |
| <a id="tc-203"></a>**TC-203** | Tag presenter | Link persists |
| <a id="tc-204"></a>**TC-204** | Multi-teacher/presenter | All relationships preserved |
| <a id="tc-205"></a>**TC-205** | SF search failure | Clear error shown |

### B. Local/Non-Local

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-230"></a>**TC-230** | Flag persists | P1=local, P2=non-local displayed |
| <a id="tc-231"></a>**TC-231** | Filter by local | P1 appears, P2 doesn't |
| <a id="tc-232"></a>**TC-232** | Unknown flag handling | Displays "unknown", no crash |

### C. Pathful Import

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-250"></a>**TC-250** | Upcoming signup | Teacher becomes In Progress |
| <a id="tc-251"></a>**TC-251** | Completed attendance | Teacher becomes Achieved |
| <a id="tc-252"></a>**TC-252** | Idempotency | Re-import = no duplicates |
| <a id="tc-253"></a>**TC-253** | Duplicate rows in file | Deduplicated |
| <a id="tc-254"></a>**TC-254** | Status update | Upcoming → completed works |
| <a id="tc-255"></a>**TC-255** | Missing columns | Clear failure message |
| <a id="tc-256"></a>**TC-256** | Column rename | Alias mapping or clear error |
| <a id="tc-257"></a>**TC-257** | Unknown teacher | Row flagged unmatched |
| <a id="tc-258"></a>**TC-258** | Unknown event | Row flagged |
| <a id="tc-259"></a>**TC-259** | Attendance status mapping | Pathful status → Polaris status correct |
| <a id="tc-260"></a>**TC-260** | Bulk import performance | Large files process within timeout |

### D. Historical Google Sheets

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-270"></a>**TC-270** | Multi-line → one event | No duplicate events |
| <a id="tc-271"></a>**TC-271** | Teacher relationships | All teachers linked |
| <a id="tc-272"></a>**TC-272** | Presenter relationships | All presenters linked |
| <a id="tc-273"></a>**TC-273** | Idempotency | Double import = no duplicates |
| <a id="tc-274"></a>**TC-274** | Date range (2-4 years) | Events from specified years imported |
| <a id="tc-275"></a>**TC-275** | Multi-line mapping preserved | Event-teacher relationships maintained |

### E. Presenter Recruitment View

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-290"></a>**TC-290** | View shows only unpresented events | Events with no presenter appear; events with presenters excluded |
| <a id="tc-291"></a>**TC-291** | Future events only | Past events excluded regardless of presenter status |
| <a id="tc-292"></a>**TC-292** | Date range filter | Results match selected date range |
| <a id="tc-293"></a>**TC-293** | School filter | Results match selected school |
| <a id="tc-294"></a>**TC-294** | District filter | Results match selected district |
| <a id="tc-295"></a>**TC-295** | Multiple filters | Results match intersection of all applied filters |
| <a id="tc-296"></a>**TC-296** | Event disappears on presenter tag | Tag presenter → event removed from view immediately |
| <a id="tc-297"></a>**TC-297** | Presenter removed → event reappears | Remove last presenter → event returns to view |
| <a id="tc-298"></a>**TC-298** | Display required fields | Shows title, date/time, school/district, teacher count, days-until |
| <a id="tc-299"></a>**TC-299** | Navigate to volunteer search | Link/button opens volunteer recruitment correctly |

**Additional Test Data:**

- **VE3** — Future virtual event, no presenter, 5 days away (red badge)
- **VE4** — Future virtual event with presenter (P1)
- **VE5** — Past virtual event, no presenter
- **VE6** — Future virtual event, no presenter, 10 days away (yellow badge)
- **VE7** — Future virtual event, no presenter, 20 days away (blue badge)
- **User-Global** — Regular user with `scope_type='global'`
- **User-District** — Regular user with `scope_type='district'`

---

*Last updated: January 2026*
*Version: 1.0*

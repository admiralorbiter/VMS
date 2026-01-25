# Test Pack 3: Virtual Events

Polaris creation + Pathful import + historical data

> [!INFO]
> **Coverage**
> [FR-VIRTUAL-201](requirements#fr-virtual-201)–[FR-VIRTUAL-206](requirements#fr-virtual-206) (Virtual events), [FR-VIRTUAL-208](requirements#fr-virtual-208) (Local/non-local), [FR-VIRTUAL-204](requirements#fr-virtual-204) (Historical import), [FR-VIRTUAL-210](requirements#fr-virtual-210)–[FR-VIRTUAL-219](requirements#fr-virtual-219) (Presenter recruitment)

---

## Test Data

- **VE1 Virtual Career Talk** — Future date
- **VE2 Virtual Panel** — Future date
- **P1 Local Presenter** — local=true
- **P2 NonLocal Presenter** — local=false

## Test Cases

### A. Virtual Event Creation

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-200"></a>**TC-200** | Create event | Persists and reloads | Automated | 2026-01-24 |
| <a id="tc-201"></a>**TC-201** | Edit event | Changes persist | Automated | 2026-01-24 |
| <a id="tc-202"></a>**TC-202** | Tag teacher (SF search) | Link persists after save | Manual | TBD |
| <a id="tc-203"></a>**TC-203** | Tag presenter | Link persists | Manual | TBD |
| <a id="tc-204"></a>**TC-204** | Multi-teacher/presenter | All relationships preserved | Manual | TBD |
| <a id="tc-205"></a>**TC-205** | SF search failure | Clear error shown | Manual | TBD |

### B. Local/Non-Local

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-230"></a>**TC-230** | Flag persists | P1=local, P2=non-local displayed | Manual | TBD |
| <a id="tc-231"></a>**TC-231** | Filter by local | P1 appears, P2 doesn't | Manual | TBD |
| <a id="tc-232"></a>**TC-232** | Unknown flag handling | Displays "unknown", no crash | Manual | TBD |

### C. Pathful Import

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-250"></a>**TC-250** | Upcoming signup | Teacher becomes In Progress | Manual | TBD |
| <a id="tc-251"></a>**TC-251** | Completed attendance | Teacher becomes Achieved | Manual | TBD |
| <a id="tc-252"></a>**TC-252** | Idempotency | Re-import = no duplicates | Manual | TBD |
| <a id="tc-253"></a>**TC-253** | Duplicate rows in file | Deduplicated | Manual | TBD |
| <a id="tc-254"></a>**TC-254** | Status update | Upcoming → completed works | Manual | TBD |
| <a id="tc-255"></a>**TC-255** | Missing columns | Clear failure message | Manual | TBD |
| <a id="tc-256"></a>**TC-256** | Column rename | Alias mapping or clear error | Manual | TBD |
| <a id="tc-257"></a>**TC-257** | Unknown teacher | Row flagged unmatched | Manual | TBD |
| <a id="tc-258"></a>**TC-258** | Unknown event | Row flagged | Manual | TBD |
| <a id="tc-259"></a>**TC-259** | Attendance status mapping | Pathful status → Polaris status correct | Manual | TBD |
| <a id="tc-260"></a>**TC-260** | Bulk import performance | Large files process within timeout | Manual | TBD |

### D. Historical Google Sheets

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-270"></a>**TC-270** | Multi-line → one event | No duplicate events | Manual | TBD |
| <a id="tc-271"></a>**TC-271** | Teacher relationships | All teachers linked | Manual | TBD |
| <a id="tc-272"></a>**TC-272** | Presenter relationships | All presenters linked | Manual | TBD |
| <a id="tc-273"></a>**TC-273** | Idempotency | Double import = no duplicates | Manual | TBD |
| <a id="tc-274"></a>**TC-274** | Date range (2-4 years) | Events from specified years imported | Manual | TBD |
| <a id="tc-275"></a>**TC-275** | Multi-line mapping preserved | Event-teacher relationships maintained | Manual | TBD |

### E. Presenter Recruitment View

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-290"></a>**TC-290** | View shows only unpresented events | Events with no presenter appear; events with presenters excluded | Manual | TBD |
| <a id="tc-291"></a>**TC-291** | Future events only | Past events excluded regardless of presenter status | Manual | TBD |
| <a id="tc-292"></a>**TC-292** | Date range filter | Results match selected date range | Manual | TBD |
| <a id="tc-293"></a>**TC-293** | School filter | Results match selected school | Manual | TBD |
| <a id="tc-294"></a>**TC-294** | District filter | Results match selected district | Manual | TBD |
| <a id="tc-295"></a>**TC-295** | Multiple filters | Results match intersection of all applied filters | Manual | TBD |
| <a id="tc-296"></a>**TC-296** | Event disappears on presenter tag | Tag presenter → event removed from view immediately | Manual | TBD |
| <a id="tc-297"></a>**TC-297** | Presenter removed → event reappears | Remove last presenter → event returns to view | Manual | TBD |
| <a id="tc-298"></a>**TC-298** | Display required fields | Shows title, date/time, school/district, teacher count, days-until | Manual | TBD |
| <a id="tc-299"></a>**TC-299** | Navigate to volunteer search | Link/button opens volunteer recruitment correctly | Manual | TBD |

### F. Historical Salesforce Import

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-210"></a>**TC-210** | Historical import | 2–4 years of past events imported from Salesforce | Manual | TBD |
| <a id="tc-211"></a>**TC-211** | Historical data integrity | Event-participant relationships preserved | Manual | TBD |

**Additional Test Data:**

- **VE3** — Future virtual event, no presenter, 5 days away (red badge)
- **VE4** — Future virtual event with presenter (P1)
- **VE5** — Past virtual event, no presenter
- **VE6** — Future virtual event, no presenter, 10 days away (yellow badge)
- **VE7** — Future virtual event, no presenter, 20 days away (blue badge)
- **User-Global** — Regular user with `scope_type='global'`
- **User-District** — Regular user with `scope_type='district'`

---

## Detailed Test Specifications

### Historical Salesforce Import

#### FR-VIRTUAL-220: Historical Event Import

**Covered by:** [TC-210](#tc-210)

**Objective:** Verify that the system supports importing historical virtual event data from Salesforce (e.g., 2–4 years of past events).

**Prerequisites:**
- Salesforce with historical event data (2–4 years old)
- Historical import functionality enabled
- Sufficient database storage capacity

**Test Steps:**
1. Configure historical import date range (2–4 years)
2. Execute historical import
3. Monitor import progress
4. Verify events are imported
5. Verify event dates are preserved correctly
6. Verify all historical events are imported

**Expected Results:**
- Historical events are imported successfully
- Event dates from 2–4 years ago are preserved
- All historical events within date range are imported
- Import completes without errors
- Historical data is accessible in system

**Edge Cases:**
- Very old events (5+ years)
- Events at date range boundaries
- Large volume of historical events (1000+)
- Historical events with incomplete data

**Integration Points:**
- Salesforce historical data queries
- Date range filtering
- Batch processing for large datasets

#### FR-VIRTUAL-221: Historical Data Integrity

**Covered by:** [TC-211](#tc-211)

**Objective:** Verify that historical virtual import preserves event-participant relationships and maintains data integrity.

**Prerequisites:**
- Historical events with participant records in Salesforce
- Historical import functionality

**Test Steps:**
1. Execute historical import for events with participants
2. Verify events are imported
3. Verify participant records are imported
4. Verify event-participant relationships are maintained
5. Verify data integrity (no orphaned records)

**Expected Results:**
- Historical events imported with correct relationships
- Participant records linked to correct events
- No orphaned participation records
- Relationship integrity maintained
- All relationships from Salesforce preserved

**Edge Cases:**
- Historical event with participants that don't exist locally
- Historical participant with event that doesn't exist locally
- Complex relationship structures
- Historical data with data quality issues

**Integration Points:**
- Relationship mapping logic
- Data integrity validation
- Foreign key constraints

---

*Last updated: January 2026*
*Version: 1.1*

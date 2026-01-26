# Import Playbooks

**Step-by-step operational procedures**

## Reference

Field mappings in [Field Mappings](field_mappings). Entity definitions in [Data Dictionary](data_dictionary).

**Note:** These are operational procedures for running imports. For technical field mappings and data transformations, see [Field Mappings](field_mappings).

## Playbook A: Pathful Export → Polaris (via Virtual Session Import)

**Purpose:** Update teacher progress statuses (Achieved/In Progress/Not Started) and virtual participation records.

**Implementation Note:** Pathful data is imported via the Virtual Session Google Sheets import process. The Google Sheet contains Pathful export data formatted for import.

**Preconditions:**

- Teacher roster for district(s) is up-to-date (see [Playbook B](#playbook-b-teacher-roster-import))
- Virtual events mapped to Pathful IDs (via `Event.session_id`)
- Know import window (semester/date range)
- Google Sheet configured for virtual sessions in admin panel

**File Prep Checklist:**

- Make a working copy: `pathful_export___clean`
- Confirm required columns: SessionId, EventId, TeacherEmail, SessionStart, AttendanceStatus
- Normalize emails: lowercase, trim
- Check dates: parseable, correct timezone (ISO-8601 format preferred)
- Export as CSV or ensure Google Sheet format matches expected structure

**Required Columns (from Pathful Export):**

| Column | Required | Notes |
|--------|----------|-------|
| `SessionId` | ✅ | Unique session identifier |
| `EventId` | ✅ | Must match `Event.session_id` |
| `TeacherEmail` | ✅ | Normalized (lowercase, trim) |
| `SessionStart` | ✅ | ISO-8601 datetime format |
| `AttendanceStatus` | ✅ | Maps to attendance status enum |
| `ParticipantType` | ⛔️ | Optional, defaults to "Volunteer" |

**Run Import:**

1. Go to **Virtual → Import Sheet**
2. Select academic year from dropdown
3. System reads from configured Google Sheet (purpose = "virtual_sessions")
4. Automatic validation runs
5. Review validation results (errors/warnings)
6. If validation passes, click **Import**
7. Review import summary

**Expected Output:**

```
Rows processed: N
Rows created: A
Rows updated: B
Rows skipped (duplicates): C
Rows unmatched (teacher): D
Rows unmatched (event): E
Rows invalid: F
```

**Definition of Done:** F = 0, D + E explained, A + B + C = N

**Contract**: [Contract D: Pathful Export → Polaris](contract_d) for complete specification

**Error Resolution:**

**Unmatched Teachers:**
- **Cause:** Teacher email not in TeacherProgress roster
- **Resolution:**
  1. Import/update teacher roster first (see [Playbook B](#playbook-b-teacher-roster-import))
  2. Re-import Pathful data (idempotent - safe to re-run)
- **Reference:** Teacher Roster Import playbook

**Unmatched Events:**
- **Cause:** `Event.session_id` doesn't match Pathful `EventId`
- **Resolution:**
  1. Create/update Event record with correct `session_id`
  2. Verify event exists in system
  3. Re-import Pathful data
- **Reference:** Event management routes

**Invalid Rows:**
- **Cause:** Missing required columns, invalid data formats
- **Resolution:**
  1. Fix in source file (Google Sheet or CSV)
  2. Validate date formats (ISO-8601 preferred)
  3. Check email normalization
  4. Verify required fields present
  5. Re-import

**Implementation:**
- Route: `routes/virtual/routes.py` `/virtual/import-sheet`
- Validation: `validate_csv_row()` function
- Reference: [Field Mappings - Pathful Export](field_mappings#3-pathful-export--polaris)

## Playbook B: Teacher Roster Import

**Purpose:** Establish authoritative teacher list for dashboards and magic link eligibility.

**Required Columns:**

| Column | Required | Transform | Notes |
|--------|----------|-----------|-------|
| `Teacher Email` | ✅ | normalize: lowercase, trim | Primary key; join key for magic links + Pathful |
| `Teacher Name` | ✅ | direct | Teacher full name |
| `School` or `Building` | ✅ | direct | School/building name |
| `Grade` | ⛔️ | direct | Grade level (K, 1-12, HS, etc.) |
| `Academic Year` | ✅ | direct | e.g., "2024-2025" |
| `Virtual Year` | ✅ | direct | e.g., "2024-2025" |
| `Target Sessions` | ⛔️ | int, default: 1 | Target number of sessions; default: 1 |

**Prep:**

1. Normalize emails (lowercase, trim)
2. Standardize school/district names
3. Remove duplicates
4. Ensure `academic_year` and `virtual_year` match
5. Verify Google Sheet configured in admin panel (purpose = "teacher_progress_tracking")

**Run Import:**

 1. **Navigate to Import Interface:**
    - Go to the District Dashboard.
    - Click **Manage Google Sheets & Import Data**.

    ![Manage Google Sheets Button](content/images/teacher_import/manage_sheets.png)

 2. **Review Instructions & Year:**
    - Select the **Virtual Year** (e.g., 2025-2026).
    - Review the data format guide at the top of the page.

    ![Import Instructions](content/images/teacher_import/import_instructions.png)

 3. **Add Google Sheet:**
    - Click **Add Google Sheet**.
    - In the modal:
      - Select **District** (e.g., Kansas City Kansas Public Schools).
      - Select **Virtual Year**.
      - Enter a **Sheet Name** (e.g. "KCK Teachers 25-26").
      - Paste the **Google Sheet ID**.
    - Click **Add Sheet**.

    ![Add Sheet Modal](content/images/teacher_import/add_sheet_modal.png)

 4. **Run Import:**
    - Find your sheet in the list.
    - Click the green **Import** button.
    - Wait for the success message confirming added/updated records.

    ![Sheet List with Import Button](content/images/teacher_import/sheet_list_import.png)

 **Post-Import: Teacher Matching**

 After importing, you must link the imported roster names to VMS Teacher records.

 1. Click **Match Teachers** (purple button) or the link in the instruction banner.
 2. **Auto-Matching:**
    - Click **Run Auto-Match** to match by Email (Exact) and Name (Fuzzy).
 3. **Manual Matching:**
    - Check **Show unmatched only**.
    - For each unmatched teacher, select the correct VMS account from the dropdown.
    - Click **Match**.

 ![Teacher Matching Interface](content/images/teacher_import/match_interface.png)

 **Expected Output:**

 ```
 Teachers imported: N
 Teachers created: A
 Teachers updated: B
 Rows skipped: C
 ```

 **Note:** Import replaces all TeacherProgress records for the academic year. Previous data is deleted before importing new data.

 **Implementation:**
 - Route: `routes/virtual/usage.py` `/usage/district/<district_name>/teacher-progress/google-sheets/<int:sheet_id>/import`
 - Model: `models/teacher_progress.py` `TeacherProgress`
 - Reference: [Field Mappings - Teacher Roster Import](field_mappings#4-teacher-roster-import)

## Playbook C: Virtual Session Import (Google Sheets)

**Purpose:** Import virtual session data including teachers, presenters, and event details.

**Required Columns:**

| Column | Required | Notes |
|--------|----------|-------|
| `Session Title` | ✅ | Event title |
| `Date` | ✅ | Session date |
| `Time` | ⛔️ | Optional, defaults to 9:00 AM |
| `Teacher Name` | ⛔️ | Recommended |
| `School Name` | ⛔️ | Recommended |
| `District` | ⛔️ | Recommended |
| `Status` | ⛔️ | Completed, Simulcast, etc. |
| `Presenter` | ⛔️ | Presenter information |

**Prep:**

1. Ensure Google Sheet configured in admin panel (purpose = "virtual_sessions")
2. Verify academic year matches
3. Check required columns present
4. Validate date formats
5. Ensure first 3 rows are headers (system skips first 3 rows)

**Run Import:**

1. Go to **Virtual → Import Sheet**
2. Select academic year
3. System reads from configured Google Sheet
4. Automatic validation runs
5. Review errors/warnings in console/logs
6. Click **Import** if validation passes
7. Review import summary

**Expected Output:**

```
Events processed: N
Events created: A
Events updated: B
Teacher registrations created: C
Rows skipped: D
Errors: E
Warnings: F
```

**Validation Rules:**

- `Session Title` required (errors if missing)
- `Date` required (errors if missing)
- `Time` optional (warnings if missing, defaults to 9:00 AM)
- `Teacher Name` optional (warnings if missing)
- `School Name` optional (warnings if missing)
- `District` optional (warnings if missing)

**Implementation:**
- Route: `routes/virtual/routes.py` `/virtual/import-sheet`
- Validation: `validate_csv_row()` function in `routes/virtual/routes.py`
- Google Sheet: Configured via `GoogleSheet` model (purpose = "virtual_sessions")

## Playbook D: Salesforce Imports

**Purpose:** Import core data from Salesforce (volunteers, teachers, students, events, organizations, history, schools, classes).

**Preconditions:**

- Salesforce credentials configured in `config.py`
- Admin access required (`@admin_required` decorator)
- Know import scope (full vs. incremental)
- Network access to Salesforce API

**Access:** All Salesforce imports require:
- `@login_required`
- `@admin_required` or `@global_users_only`
- Admin user with `scope_type = 'global'`

### D1: Volunteer Import

**Route:** `/volunteers/import-from-salesforce`

**Source:** Salesforce Contact records where `Contact_Type__c = 'Volunteer'` or `Contact_Type__c = ''`

**Creates/updates:**
- Volunteer records
- Email addresses (multiple per volunteer)
- Phone numbers (multiple per volunteer)
- Addresses (multiple per volunteer)
- Skills (many-to-many relationship)
- Organizations (via affiliations)

**Idempotent:** Yes (by `salesforce_individual_id`)

**Run Import:**

1. Go to **Admin → Import** (or direct route)
2. Click **Import Volunteers from Salesforce**
3. System connects to Salesforce and queries Contact records
4. Review console output for progress
5. Review summary statistics

**Expected Output:**

```
Total Records: N
Successful: A
Created: B
Updated: C
Errors: D
```

**Implementation:**
- Route: `routes/volunteers/routes.py` `import_from_salesforce()`
- Reference: [Field Mappings - Volunteer Import](field_mappings#salesforce--polaris-volunteer-import)

### D2: Teacher Import

**Route:** `/teachers/import-from-salesforce`

**Source:** Salesforce Contact records where `Contact_Type__c = 'Teacher'`

**Creates/updates:**
- Teacher records
- Email addresses
- Phone numbers
- School associations

**Idempotent:** Yes (by `salesforce_individual_id`)

**Run Import:**

1. Go to **Admin → Import** (or direct route)
2. Click **Import Teachers from Salesforce**
3. System connects to Salesforce and queries Contact records
4. Review console output
5. Review summary statistics

**Expected Output:**

```
Total Records: N
Successful: A
Created: B
Updated: C
Errors: D
```

**Implementation:**
- Route: `routes/teachers/routes.py` `import_from_salesforce()`
- Reference: [Field Mappings - Teacher Import](field_mappings#salesforce--polaris-teacher-import)

### D3: Student Import

**Route:** `/students/import-from-salesforce`

**Source:** Salesforce Contact records where `Contact_Type__c = 'Student'`

**Creates/updates:**
- Student records
- Email addresses
- School associations
- Class associations
- Teacher associations

**Idempotent:** Yes (by `salesforce_individual_id`)

**Note:** Chunked import for large datasets. Processes in batches to avoid memory issues.

**Run Import:**

1. Go to **Admin → Import** (or direct route)
2. Click **Import Students from Salesforce**
3. System connects to Salesforce and queries Contact records
4. Processes in chunks (progress shown in console)
5. Review summary statistics

**Expected Output:**

```
Total Records: N
Successful: A
Created: B
Updated: C
Errors: D
Chunks processed: X
```

**Implementation:**
- Route: `routes/students/routes.py` `import_from_salesforce()`
- Chunked processing for large datasets

### D4: Event Import

**Route:** `/events/import-from-salesforce`

**Source:** Salesforce Event/Session records

**Creates/updates:**
- Event records
- EventParticipation (volunteer participation)
- EventStudentParticipation (student participation)
- EventTeacher (teacher participation)
- District associations
- School associations

**Idempotent:** Yes (by `salesforce_id`)

**Run Import:**

1. Go to **Admin → Import** (or direct route)
2. Click **Import Events from Salesforce**
3. System connects to Salesforce and queries Event records
4. Review console output (shows progress every 500 events)
5. Review summary statistics with status/type breakdowns

**Expected Output:**

```
Total from Salesforce: N
Successfully processed: A
Errors: B
Skipped (invalid): C

Status breakdown:
  [status]: [count]

Session type breakdown:
  [type]: [count]
```

**Implementation:**
- Route: `routes/events/routes.py` `import_events_from_salesforce()`
- Processes events and associated participations

### D5: Organization Import

**Route:** `/organizations/import-from-salesforce`

**Source:** Salesforce Account records

**Creates/updates:**
- Organization records
- Address information
- Volunteer associations (via affiliations)

**Idempotent:** Yes (by `salesforce_id`)

**Run Import:**

1. Go to **Admin → Import** (or direct route)
2. Click **Import Organizations from Salesforce**
3. System connects to Salesforce and queries Account records
4. Review console output
5. Review summary statistics

**Expected Output:**

```
Total Records: N
Successful: A
Created: B
Updated: C
Errors: D
```

**Implementation:**
- Route: `routes/organizations/routes.py` `import_organizations_from_salesforce()`

### D6: History Import

**Route:** `/history/import-from-salesforce`

**Source:** Salesforce Task and EmailMessage records

**Creates/updates:**
- History records (activity tracking)
- Links to Volunteers, Teachers, Events

**Idempotent:** Yes (by `salesforce_id`)

**Run Import:**

1. Go to **Admin → Import** (or direct route)
2. Click **Import History from Salesforce**
3. System connects to Salesforce and queries Task and EmailMessage records
4. Review console output (shows sample data)
5. Review summary statistics

**Expected Output:**

```
Total records to process: N
New records created: A
Records already exist: B
No matching contact: C
Other errors: D
Total skipped: E
```

**Implementation:**
- Route: `routes/history/routes.py` `import_history_from_salesforce()`
- Processes both Task and EmailMessage records
- Matches contacts by email or Salesforce ID

### D7: School Import

**Route:** `/management/import-schools`

**Source:** Salesforce Account records where Account type = School

**Creates/updates:**
- School records
- District associations
- Address information

**Idempotent:** Yes (by `salesforce_id`)

**Run Import:**

1. Go to **Admin → Management → Import Schools**
2. Click **Import Schools from Salesforce**
3. System connects to Salesforce and queries Account records
4. Review console output
5. Review summary statistics

**Expected Output:**

```
Total Records: N
Successful: A
Created: B
Updated: C
Errors: D
```

**Implementation:**
- Route: `routes/management/management.py` `import_schools()`

### D8: Class Import

**Route:** `/management/import-classes`

**Source:** Salesforce Class records

**Creates/updates:**
- Class records
- School associations
- Teacher associations

**Idempotent:** Yes (by `salesforce_id`)

**Run Import:**

1. Go to **Admin → Management → Import Classes**
2. Click **Import Classes from Salesforce**
3. System connects to Salesforce and queries Class records
4. Review console output
5. Review summary statistics

**Expected Output:**

```
Total Records: N
Successful: A
Created: B
Updated: C
Errors: D
```

**Implementation:**
- Route: `routes/management/management.py` `import_classes()`

### Daily Import Script

**Automated Imports:** The system includes a daily import script that runs all Salesforce imports in sequence.

**Script:** `scripts/daily_imports/daily_imports.py`

**Import Sequence:**

1. Organizations
2. Volunteers
3. Affiliations (volunteer-organization relationships)
4. Events
5. History
6. Schools
7. Classes
8. Teachers
9. Sync Unaffiliated Events

**Note:** Student imports (Students, Student Participations) are **excluded** from the automated script due to dataset size. They must be run manually via the Admin Import interface (see [D3: Student Import](#d3-student-import)).

**Usage:**

```bash
# Daily imports (organizations, volunteers, affiliations, events, history)
python scripts/daily_imports/daily_imports.py --daily

# Weekly imports (daily + schools, classes, teachers)
python scripts/daily_imports/daily_imports.py --weekly

# Full imports (all steps)
python scripts/daily_imports/daily_imports.py --full

# Only specific steps
python scripts/daily_imports/daily_imports.py --only volunteers,events
```

**Reference:** [Daily Import Scripts](daily_import_scripts)

## Import Log Template

Use this template to document each import run:

```
Import type: [Pathful / Roster / Virtual Session / Salesforce: Volunteer / etc.]
Run date/time: [YYYY-MM-DD HH:MM:SS UTC]
Run by: [username]
File name: [filename.csv or Google Sheet name]
Window: [date range or academic year]

Results:
  Processed: [N]
  Created: [A]
  Updated: [B]
  Skipped: [C]
  Unmatched: [D]
  Invalid: [E]

Decisions/notes: [any issues, resolutions, follow-ups]

Follow-ups: [action items]
```

**Example:**

```
Import type: Teacher Roster Import
Run date/time: 2025-01-15 14:30:00 UTC
Run by: admin_user
File name: KCK_Teacher_Roster_2024-2025
Window: 2024-2025

Results:
  Processed: 150
  Created: 145
  Updated: 5
  Skipped: 0
  Unmatched: 0
  Invalid: 0

Decisions/notes: All teachers imported successfully. 5 teachers updated with new grade assignments.

Follow-ups: None
```

## Column Change Procedure

**If external system changes export format:**

1. **Stop normal imports** - Pause scheduled imports if automated
2. **Save sample with new format** - Export sample file with new column structure
3. **Compare headers to mapping contract** - Review [Field Mappings](field_mappings) for expected columns
4. **Update Polaris alias mapping** - If column names changed, update mapping code
5. **Test on small file** - Import test file with 5-10 rows
6. **Verify results** - Check that data imported correctly
7. **Resume production imports** - Once verified, resume normal import schedule

**Implementation:**
- Field mappings defined in `documentation/content/field_mappings.md`
- Code changes may be required in import routes (e.g., `routes/virtual/routes.py`, `routes/volunteers/routes.py`)
- Update Field Mappings documentation if column names change

**Example Scenario:**

Pathful changes `TeacherEmail` column to `EducatorEmail`:

1. Stop Pathful imports
2. Save sample export with `EducatorEmail` column
3. Compare to Field Mappings (expects `TeacherEmail`)
4. Update code in `routes/virtual/routes.py` to map `EducatorEmail` → `TeacherEmail`
5. Test import with small file
6. Update Field Mappings documentation
7. Resume production imports

## Common Error Resolution

### Unmatched Teachers

**Cause:** Teacher email not in TeacherProgress roster

**Symptoms:**
- Import shows "Rows unmatched (teacher): D" where D > 0
- Teacher progress not updating
- Magic links not working for those teachers

**Resolution:**
1. Import/update teacher roster first (see [Playbook B](#playbook-b-teacher-roster-import))
2. Verify teacher email in roster matches Pathful export (normalized)
3. Re-import Pathful data (idempotent - safe to re-run)

**Prevention:** Always import teacher roster before Pathful data

### Unmatched Events

**Cause:** `Event.session_id` doesn't match Pathful `EventId`

**Symptoms:**
- Import shows "Rows unmatched (event): E" where E > 0
- Events not showing teacher participation
- Teacher progress not updating

**Resolution:**
1. Verify event exists in system
2. Check `Event.session_id` matches Pathful `EventId`
3. Create/update Event record with correct `session_id` if missing
4. Re-import Pathful data

**Prevention:** Ensure virtual events are created with correct `session_id` before importing Pathful data

### Invalid Rows

**Cause:** Missing required columns, invalid data formats

**Symptoms:**
- Import shows "Rows invalid: F" where F > 0
- Validation errors in console/logs
- Specific row numbers and error messages

**Resolution:**
1. Review error messages for specific issues
2. Fix in source file (Google Sheet or CSV):
   - Add missing required columns
   - Fix date formats (use ISO-8601: `YYYY-MM-DDTHH:MM:SS`)
   - Normalize emails (lowercase, trim)
   - Verify required fields present
3. Re-import

**Common Issues:**
- Date format: Use ISO-8601 or standard formats (YYYY-MM-DD)
- Email format: Ensure valid email addresses, normalize to lowercase
- Missing columns: Add required columns to source file

### Duplicate Rows

**Cause:** Same data imported twice

**Symptoms:**
- Import shows "Rows skipped (duplicates): C" where C > 0
- No errors, but rows not processed

**Resolution:**
- System handles idempotently (updates existing records)
- No action needed if duplicates are expected
- If unexpected, check source file for actual duplicates

**Note:** Check if duplicates indicate data quality issues in source system

### Salesforce Authentication Errors

**Cause:** Invalid Salesforce credentials or network issues

**Symptoms:**
- Import fails with authentication error
- 401 Unauthorized response

**Resolution:**
1. Verify Salesforce credentials in `config.py`:
   - `SF_USERNAME`
   - `SF_PASSWORD`
   - `SF_SECURITY_TOKEN`
2. Check network connectivity to Salesforce
3. Verify Salesforce user has API access
4. Retry import

### Google Sheet Access Errors

**Cause:** Google Sheet not accessible or invalid sheet ID

**Symptoms:**
- Import fails with "Error reading Google Sheet"
- "No Google Sheet configured" error

**Resolution:**
1. Verify Google Sheet configured in admin panel
2. Check sheet ID is correct
3. Verify sheet is publicly accessible (or service account has access)
4. Check sheet purpose matches import type:
   - "virtual_sessions" for virtual session import
   - "teacher_progress_tracking" for teacher roster import
5. Retry import

## Best Practices

### Pre-Import Checklist

- [ ] Verify source data is up-to-date
- [ ] Check required columns present
- [ ] Normalize emails (lowercase, trim)
- [ ] Validate date formats
- [ ] Remove obvious duplicates
- [ ] Backup current data (if needed)
- [ ] Verify import window/scope

### Post-Import Verification

- [ ] Review import summary statistics
- [ ] Verify "Invalid" count = 0
- [ ] Explain any "Unmatched" rows
- [ ] Check that Created + Updated + Skipped = Processed
- [ ] Spot-check imported data in system
- [ ] Document import in log template
- [ ] Follow up on any errors or warnings

### Import Scheduling

- **Daily:** Organizations, Volunteers, Events, History (via daily import script)
- **Weekly:** Schools, Classes, Teachers (via weekly import script)
- **As Needed:** Teacher Roster, Virtual Sessions, Pathful data

### Data Quality

- Always import teacher roster before Pathful data
- Ensure events exist before importing participations
- Verify Google Sheets are configured correctly
- Monitor import logs for patterns in errors
- Document any data quality issues found

---

*Last updated: January 2026*
*Version: 1.0*

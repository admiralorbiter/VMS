# Student Roster & Attendance

> **Audience:** Internal staff with Admin or User role (Salesforce access required)

This guide explains how to manage student participation in events. Student rostering and attendance is managed in **Salesforce** as the source of truth, then synced to **Polaris** for reporting.

> [!INFO]
> **Source of Truth**
> Salesforce is the system of record for student data. Polaris imports and aggregates this data for reporting purposes. All data entry happens in Salesforce.

## 1. Rostering Students

**Rostering** is the process of associating students with an event before it happens. This creates the universe of students who *should* attend.

### In Salesforce

1. Navigate to the **Session** record in Salesforce.
2. Find the **Session Participants** related list.
3. Click **"Add Students"** or **"New Session Participant"**.
4. Search for students by:
   - Name
   - School
   - District
   - Local Student ID
5. Select students and click **Add**.

> [!TIP]
> You can bulk-add students by using the **Import** feature or selecting multiple students from a filtered list view.

### What Gets Created

Each student-event association creates a `Session_Participant__c` record in Salesforce with:
- Student reference
- Event reference
- Status = "Registered" (default)

### Duplicate Prevention

The system prevents duplicate rosters:
- If a student is already rostered to an event, adding them again will not create a duplicate.
- Test Case: [TC-602](test_packs/test_pack_5#tc-602)

## 2. Marking Attendance

After an event occurs, you must record who actually attended. This is critical for accurate impact reporting.

### In Salesforce

1. Navigate to the **Session** record.
2. Go to the **Session Participants** related list.
3. For each student, update the **Attendance Status**:

| Status | Meaning | Impact on Reports |
|--------|---------|-------------------|
| **Attended** | Student was present | ✅ Counted in student reach |
| **Absent** | Student did not show up | ❌ Not counted |
| **Excused** | Known absence (e.g., illness) | ❌ Not counted |
| **No Show** | Unexcused absence | ❌ Not counted |

4. Click **Save** after updating statuses.

> [!WARNING]
> Changes to attendance status require a **manual sync** to appear in Polaris reports. See [Syncing to Polaris](#4-syncing-to-polaris) below.

## 3. Virtual Event Student Estimation

For **virtual events**, individual students are not tracked. Instead, the system uses a standard estimate:

| Event Type | Tracking Method | Student Count |
|------------|-----------------|---------------|
| In-Person | Individual roster | Actual count |
| Virtual | Standard estimate | **25 students per session** |

This estimate is applied automatically in all impact reports for virtual sessions.

**Related Requirement:** [FR-STUDENT-605](requirements#fr-student-605)

## 4. Syncing to Polaris

Student roster and attendance data is synced from Salesforce to Polaris via a **manual import process**.

### Why Manual Sync?

Due to the volume of student records, synchronization is triggered manually by administrators rather than running automatically. This allows:
- Control over sync timing
- Handling of large data volumes
- Verification before reporting

### Triggering a Sync

1. Log into **Polaris** as an Admin.
2. Navigate to **Admin > Sync Status**.
3. Click **"Import Student Participations"**.
4. Wait for the import to complete.

> [!INFO]
> Typical sync cadence is **every 2 weeks** or before major reporting periods.

### What Gets Synced

| Salesforce Field | Polaris Model | Notes |
|-----------------|---------------|-------|
| `Session_Participant__c.Id` | `EventStudentParticipation.salesforce_id` | Unique identifier |
| `Session_Participant__c.Session__c` | `EventStudentParticipation.event_id` | Links to Event |
| `Session_Participant__c.Student__c` | `EventStudentParticipation.student_id` | Links to Student |
| `Session_Participant__c.Status` | `EventStudentParticipation.status` | Attendance status |

**Related Documentation:** [Field Mappings - Student Participation](field_mappings#4-salesforce--polaris-student-participation-import)

## 5. Reporting Impact

Once synced, student attendance data feeds directly into impact reporting:

### Metrics Computed

| Metric | Calculation |
|--------|-------------|
| **Unique Students Reached** | COUNT(DISTINCT students with status = 'Attended') |
| **Student Reach by District** | Unique students per district |
| **Student Reach by School** | Unique students per school |
| **Student Reach by Event Type** | In-person (actual) + Virtual (×25 estimate) |

### Accessing Reports

1. Navigate to **Reports > Impact & KPIs**.
2. Use filters:
   - District
   - School
   - Event Type (In-Person, Virtual)
   - Date Range
3. Export to CSV for grant reporting.

**Related User Stories:** [US-603](user_stories#us-603)

## 6. Troubleshooting

### Problem: Student not appearing in roster

**Possible causes:**
- Student record doesn't exist in Salesforce
- Search filters too restrictive

**Solution:** Create the student record first, then add to roster.

### Problem: Attendance changes not reflected in Polaris

**Possible causes:**
- Manual sync hasn't been run
- Sync encountered errors

**Solution:**
1. Check last sync timestamp in Admin > Sync Status
2. Re-run the student participation import
3. Check error logs if sync fails

### Problem: Virtual event student count seems wrong

**Note:** Virtual events use a fixed 25-student estimate per session. Individual students are not tracked for virtual events.

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-601](user_stories#us-601), [US-602](user_stories#us-602), [US-603](user_stories#us-603) |
| **Requirements** | [FR-STUDENT-601](requirements#fr-student-601), [FR-STUDENT-602](requirements#fr-student-602), [FR-STUDENT-603](requirements#fr-student-603), [FR-STUDENT-604](requirements#fr-student-604), [FR-STUDENT-605](requirements#fr-student-605) |
| **Use Cases** | [UC-10](use_cases#uc-10) (Student Roster and Attendance) |
| **Test Coverage** | [Test Pack 5](test_packs/test_pack_5) (TC-600–TC-691) |

---

*Last updated: January 2026*
*Version: 2.0*

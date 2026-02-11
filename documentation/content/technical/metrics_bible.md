# Metrics Bible

**Canonical metric definitions — Source of Truth**

## Source of Truth

All dashboards and reports must use these definitions. Any deviation requires documented exception.

**Related Documentation:**
- [Data Dictionary](data_dictionary) - Entity and field definitions
- [Field Mappings](field_mappings) - Cross-system data flow specifications

## Global Conventions

### C1 — Reporting Window

All metrics computed within `[start_date, end_date]` unless marked "lifetime".

**Implementation:**
- Use `Event.start_date` for time attribution
- Date range filters apply to event start date, not import/creation date
- Timezone-aware datetime comparisons required

### C2 — Dedupe Keys

Unique identification for deduplication across metrics:

| Entity | Dedupe Key | Implementation |
|--------|------------|----------------|
| **Volunteers** | `normalized_email` | `Email.email` (lowercase + trim) via `Email` table join |
| **Teachers** | `normalized_email` | `Email.email` (lowercase + trim) via `Email` table join |
| **Students** | `student_id` | `Student.student_id` (school-specific identifier) |

**Email Normalization:**
- Applied via `get_email_addresses()` in `routes/utils.py`
- All emails stored in lowercase with trimmed whitespace
- Multiple emails per contact supported via `Email` table

### C3 — Eligibility

Record contributes to metric only if:
1. Event `start_date` falls within reporting window
2. Participation record meets status rule (see metric-specific rules)

**Exclusions:**
- Cancelled events (`Event.status = 'Cancelled'`)
- Deleted records (`is_deleted = True`)
- Events outside reporting window

### C4 — Time Attribution

Counts attributed to event date (`Event.start_date`), not import date or creation date.

**Rationale:** Metrics reflect when the activity occurred, not when data was synced.

### C5 — Unknown Data

Unknown school/district → "Unknown" bucket in aggregates, excluded from lists.

**Implementation:**
- `Event.school IS NULL` → "Unknown" school
- `Event.district_partner IS NULL` → "Unknown" district
- Aggregates include "Unknown" bucket
- Detail lists exclude records with unknown values

## Teacher Progress Statuses

Teacher progress tracking for virtual sessions uses the `TeacherProgress` entity and `EventTeacher` participation records.

| Status | Definition | Operational Rule |
|--------|------------|------------------|
| **Achieved** | Completed ≥1 virtual session | `COUNT(EventTeacher WHERE attendance_confirmed_at IS NOT NULL AND Event.start_date IN reporting_window) >= target_sessions` |
| **In Progress** | Has future signup, no completions | `Attended = 0 AND COUNT(EventTeacher WHERE status IN ('registered', 'attended') AND Event.start_date > NOW()) >= 1` |
| **Not Started** | No sessions at all | `Attended = 0 AND COUNT(EventTeacher) = 0` |

**Precedence:** Achieved → In Progress → Not Started (first match wins)

**Implementation:**
- Calculated via `TeacherProgress.get_progress_status()` method
- Uses `EventTeacher.attendance_confirmed_at` to determine completed sessions
- Uses `EventTeacher.status` and `Event.start_date` for planned sessions
- Reference: `models/teacher_progress.py`, `routes/virtual/usage.py`

## Student Metrics

### M10 — Unique Students Reached

**Definition:** Distinct students who attended ≥1 eligible event.

**Calculation:**
```sql
COUNT(DISTINCT EventStudentParticipation.student_id)
WHERE EventStudentParticipation.status = 'Attended'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
```

**Entity References:**
- `EventStudentParticipation` table
- `Student` entity (see [Data Dictionary](data_dictionary#entity-student))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Status Values:**
- `'Attended'` - Student attended the event
- `'Registered'` - Student registered but did not attend (excluded)
- `'No Show'` - Student did not attend (excluded)

**Deduplication:**
- Uses `Student.student_id` (C2)
- One student counted once per reporting window regardless of number of events attended

## Teacher Metrics (Virtual Sessions)

### M70 — Unique Teachers Reached (Virtual)

**Definition:** Distinct teachers who attended ≥1 virtual session.

**Calculation:**
```sql
COUNT(DISTINCT EventTeacher.teacher_id)
WHERE EventTeacher.attendance_confirmed_at IS NOT NULL
  AND Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status IN ('Completed', 'Simulcast')
```

**Entity References:**
- `EventTeacher` table (see [Data Dictionary](data_dictionary#entity-eventteacher))
- `Teacher` entity (see [Data Dictionary](data_dictionary#entity-teacher))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Deduplication:**
- Uses `normalized_email` via `Email` table join (C2)
- One teacher counted once per reporting window regardless of number of sessions

### M71 — Classrooms Reached

**Definition:** Distinct classrooms (teachers) reached via virtual sessions.

**Calculation:** Same as M70 (Unique Teachers Reached). Each teacher represents one classroom.

**Note:** In virtual sessions, "classroom" is equivalent to "teacher" since each teacher participates with their class.

### M72 — Confirmed Teachers

**Definition:** Teachers with confirmed attendance in virtual sessions.

**Calculation:**
```sql
COUNT(DISTINCT EventTeacher.teacher_id)
WHERE EventTeacher.attendance_confirmed_at IS NOT NULL
  AND Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
```

**Entity References:**
- `EventTeacher` table (see [Data Dictionary](data_dictionary#entity-eventteacher))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

### M73 — Estimated Students (Virtual)

**Definition:** Estimated student count for virtual sessions using standard classroom size.

**Calculation:**
```sql
COUNT(DISTINCT EventTeacher.teacher_id) × 25
WHERE EventTeacher.attendance_confirmed_at IS NOT NULL
  AND Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status IN ('Completed', 'Simulcast')
```

**Rationale:**
- Virtual sessions estimate student count as confirmed teachers × 25
- Standard classroom size assumption: 25 students per teacher
- Used when actual student attendance data is not available for virtual sessions

**Entity References:**
- `EventTeacher` table (see [Data Dictionary](data_dictionary#entity-eventteacher))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

## Volunteer Metrics

### M20 — Unique Volunteers Reached

**Definition:** Distinct volunteers with eligible participation.

**Calculation:**
```sql
COUNT(DISTINCT EventParticipation.volunteer_id)
WHERE EventParticipation.status IN ('Attended', 'Completed', 'Successfully Completed')
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
```

**Entity References:**
- `EventParticipation` table
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Status Values:**
- `'Attended'` - Volunteer attended the event
- `'Completed'` - Volunteer completed the event
- `'Successfully Completed'` - Volunteer successfully completed the event
- Excluded: `'No-Show'`, `'Cancelled'`, `'Registered'` (without attendance)

**Deduplication:**
- Uses `normalized_email` via `Email` table join (C2)
- One volunteer counted once per reporting window regardless of number of events

### M30 — Total Volunteer Hours

**Definition:** Sum of credited hours per volunteer participation.

**Calculation:**
```sql
SUM(EventParticipation.delivery_hours)
WHERE EventParticipation.status IN ('Attended', 'Completed', 'Successfully Completed')
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
  AND EventParticipation.delivery_hours IS NOT NULL
```

**Source:**
- Primary: `EventParticipation.delivery_hours` field (from Salesforce `Delivery_Hours__c`)
- Stored as `Float` in database
- Null values excluded from sum

**Fallback Calculation:**
If `delivery_hours` is NULL:
1. Use `Event.duration / 60` (convert minutes to hours) if `Event.duration` exists
2. Otherwise calculate from `(Event.end_date - Event.start_date).total_seconds() / 3600` (minimum 1.0 hour)
3. Default to 0.0 if no timing data available

**Implementation:**
- See `routes/events/routes.py` `fix_missing_participation_records()` function
- See `routes/reports/common.py` for aggregation logic

**Entity References:**
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

### M90 — Professionals of Color Count

**Definition:** Distinct volunteers who identify as people of color.

**Calculation:**
```sql
COUNT(DISTINCT EventParticipation.volunteer_id)
WHERE EventParticipation.status IN ('Attended', 'Completed', 'Successfully Completed')
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
  AND Volunteer.is_people_of_color = True
```

**Entity References:**
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Deduplication:**
- Uses `normalized_email` via `Email` table join (C2)
- One volunteer counted once per reporting window

### M91 — Local Professionals Count

**Definition:** Distinct volunteers with local status (within KC metro area).

**Calculation:**
```sql
COUNT(DISTINCT EventParticipation.volunteer_id)
WHERE EventParticipation.status IN ('Attended', 'Completed', 'Successfully Completed')
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
  AND Volunteer.local_status = 'local'
```

**Entity References:**
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Local Status Values:**
- `'local'` - Within KC metro area (included)
- `'partial'` - Within driving distance (excluded)
- `'non_local'` - Too far (excluded)
- `'unknown'` - No address data (excluded)

**Deduplication:**
- Uses `normalized_email` via `Email` table join (C2)
- One volunteer counted once per reporting window

### M92 — First-Time Volunteers

**Definition:** Volunteers whose first event in the reporting window is their first ever event participation.

**Calculation:**
```sql
COUNT(DISTINCT EventParticipation.volunteer_id)
WHERE EventParticipation.status IN ('Attended', 'Completed', 'Successfully Completed')
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
  AND NOT EXISTS (
    SELECT 1 FROM EventParticipation ep2
    JOIN Event e2 ON ep2.event_id = e2.id
    WHERE ep2.volunteer_id = EventParticipation.volunteer_id
      AND e2.start_date < :start_date
      AND ep2.status IN ('Attended', 'Completed', 'Successfully Completed')
  )
```

**Entity References:**
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Implementation:**
- See `routes/reports/first_time_volunteer.py` for calculation logic
- Compares against all historical events, not just reporting window

## Organization Metrics

### M40 — Unique Organizations Engaged

**Definition:** Distinct organizations with volunteer participation in reporting window.

**Calculation:**
```sql
COUNT(DISTINCT Volunteer.organization_name)
WHERE EventParticipation EXISTS
  AND EventParticipation.status IN ('Attended', 'Completed', 'Successfully Completed')
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
  AND Volunteer.organization_name IS NOT NULL
```

**Entity References:**
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Deduplication:**
- Uses `Volunteer.organization_name` (exact string match)
- Case-sensitive matching
- Null organization names excluded

## Event/Session Metrics

### M60 — Total Events/Sessions

**Definition:** Count of all eligible events in reporting window.

**Calculation:**
```sql
COUNT(DISTINCT Event.id)
WHERE Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Exclusions:**
- Cancelled events (`Event.status = 'Cancelled'`)
- Events outside reporting window

### M61 — Virtual Sessions Count

**Definition:** Count of virtual format events.

**Calculation:**
```sql
COUNT(DISTINCT Event.id)
WHERE Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Event Format:**
- `'Virtual'` - Virtual/online events (included)
- `'InPerson'` - In-person events (excluded)

### M62 — In-Person Sessions Count

**Definition:** Count of in-person format events.

**Calculation:**
```sql
COUNT(DISTINCT Event.id)
WHERE Event.format = 'InPerson'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Event Format:**
- `'InPerson'` - In-person events (included)
- `'Virtual'` - Virtual events (excluded)

### M63 — Cancelled Events Count

**Definition:** Count of events that were cancelled.

**Calculation:**
```sql
COUNT(DISTINCT Event.id)
WHERE Event.status = 'Cancelled'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Note:** Cancelled events are excluded from most metrics but tracked separately for reporting completeness.

## School Metrics

### M100 — Unique Schools Reached

**Definition:** Distinct schools with events in reporting window.

**Calculation:**
```sql
COUNT(DISTINCT Event.school)
WHERE Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
  AND Event.school IS NOT NULL
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))
- `School` entity (see [Data Dictionary](data_dictionary#entity-school))

**Deduplication:**
- Uses `Event.school` (FK to `School.id`)
- Null school values excluded (see C5)

## Virtual Session Experience Metrics

### M80 — Experience Count

**Definition:** Count of teacher-session participation pairs (one experience = one teacher in one session).

**Calculation:**
```sql
COUNT(EventTeacher.id)
WHERE Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status IN ('Completed', 'Simulcast')
  AND EventTeacher.attendance_confirmed_at IS NOT NULL
```

**Entity References:**
- `EventTeacher` table (see [Data Dictionary](data_dictionary#entity-eventteacher))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Note:** This counts each teacher-session combination separately. A teacher attending 3 sessions = 3 experiences.

### M81 — Local Session Count

**Definition:** Sessions where at least one presenter has local status.

**Calculation:**
```sql
COUNT(DISTINCT Event.id)
WHERE Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status IN ('Completed', 'Simulcast')
  AND EXISTS (
    SELECT 1 FROM EventParticipation ep
    JOIN Volunteer v ON ep.volunteer_id = v.id
    WHERE ep.event_id = Event.id
      AND ep.participant_type = 'Presenter'
      AND ep.status IN ('Attended', 'Completed', 'Successfully Completed')
      AND v.local_status = 'local'
  )
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))

**Implementation:**
- Checks if any presenter (participant_type = 'Presenter') has `Volunteer.local_status = 'local'`
- Session-level flag: if any presenter is local, entire session is counted as local

### M82 — POC Session Count

**Definition:** Sessions where at least one presenter identifies as a person of color.

**Calculation:**
```sql
COUNT(DISTINCT Event.id)
WHERE Event.format = 'Virtual'
  AND Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status IN ('Completed', 'Simulcast')
  AND EXISTS (
    SELECT 1 FROM EventParticipation ep
    JOIN Volunteer v ON ep.volunteer_id = v.id
    WHERE ep.event_id = Event.id
      AND ep.participant_type = 'Presenter'
      AND ep.status IN ('Attended', 'Completed', 'Successfully Completed')
      AND v.is_people_of_color = True
  )
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))
- `EventParticipation` table (see [Data Dictionary](data_dictionary#entity-eventparticipation))
- `Volunteer` entity (see [Data Dictionary](data_dictionary#entity-volunteer))

**Implementation:**
- Checks if any presenter has `Volunteer.is_people_of_color = True`
- Session-level flag: if any presenter is POC, entire session is counted as POC

### M83 — Local Session Percentage

**Definition:** Percentage of virtual sessions with local presenters.

**Calculation:**
```sql
(M81 / M61) × 100
WHERE M61 > 0
```

**Alternative:**
```sql
(COUNT(DISTINCT local_sessions) / COUNT(DISTINCT all_sessions)) × 100
```

**Entity References:**
- Derived from M81 (Local Session Count) and M61 (Virtual Sessions Count)

**Note:** Returns 0 if no virtual sessions exist in reporting window.

### M84 — POC Session Percentage

**Definition:** Percentage of virtual sessions with presenters of color.

**Calculation:**
```sql
(M82 / M61) × 100
WHERE M61 > 0
```

**Alternative:**
```sql
(COUNT(DISTINCT poc_sessions) / COUNT(DISTINCT all_sessions)) × 100
```

**Entity References:**
- Derived from M82 (POC Session Count) and M61 (Virtual Sessions Count)

**Note:** Returns 0 if no virtual sessions exist in reporting window.

## Ratio/Calculated Metrics

### M110 — Students per Volunteer (In-Person)

**Definition:** Calculated ratio of students to volunteers for in-person events with attendance detail.

**Calculation:**
```sql
FLOOR((EventAttendanceDetail.total_students / EventAttendanceDetail.num_classrooms) × EventAttendanceDetail.rotations)
WHERE Event.format = 'InPerson'
  AND EventAttendanceDetail.total_students IS NOT NULL
  AND EventAttendanceDetail.num_classrooms > 0
  AND EventAttendanceDetail.rotations > 0
```

**Entity References:**
- `EventAttendanceDetail` table (see [Data Dictionary](data_dictionary#entity-eventattendance))
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Formula:**
- `(Total Students / Classrooms) × Rotations`
- Result rounded down (FLOOR) to nearest integer
- Only calculated when all required fields are present and > 0

**Implementation:**
- See `models/attendance.py` `EventAttendanceDetail.calculate_students_per_volunteer()` method
- See `routes/reports/attendance.py` for usage

### M111 — Average Students per Volunteer

**Definition:** Average students per volunteer across events with attendance detail data.

**Calculation:**
```sql
AVG(M110)
WHERE M110 IS NOT NULL
```

**Alternative:**
```sql
SUM(calculated_students_per_volunteer) / COUNT(events_with_ratio)
WHERE calculated_students_per_volunteer IS NOT NULL
```

**Entity References:**
- Derived from M110 (Students per Volunteer) calculations
- `EventAttendanceDetail` table (see [Data Dictionary](data_dictionary#entity-eventattendance))

**Note:** Only includes events where all required attendance detail fields are available.

## Event Type Breakdowns

### M120 — Events by Type

**Definition:** Count of events grouped by event type.

**Calculation:**
```sql
SELECT Event.type, COUNT(DISTINCT Event.id) as count
FROM Event
WHERE Event.start_date >= :start_date
  AND Event.start_date <= :end_date
  AND Event.status != 'Cancelled'
GROUP BY Event.type
```

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))

**Event Types:**
- `IN_PERSON` - In-person events
- `VIRTUAL_SESSION` - Virtual sessions
- `CONNECTOR_SESSION` - Connector sessions
- `CAREER_FAIR` - Career fair events
- `CAREER_SPEAKER` - Career speaker events
- `DIA` - Data in Action events
- And other types as defined in `EventType` enum

**Implementation:**
- See `models/event.py` for complete `EventType` enum values
- Used for breakdowns and filtering in reports

## Attribution Rules

### M50 — District Attribution

Event's linked district determines roll-up.

**Implementation:**
- Primary: `Event.district_partner` (string field)
- Alternative: Via `event_districts` many-to-many relationship
- If both exist, `event_districts` relationship takes precedence for multi-district events

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))
- `District` entity (see [Data Dictionary](data_dictionary#entity-district))

### M51 — School Attribution

Attribute to event's school, not student's home school.

**Implementation:**
- Use `Event.school` (FK to `School.id`)
- Do NOT use `Student.school_id` (student's home school)
- Rationale: Metrics reflect where the activity occurred, not where students are enrolled

**Entity References:**
- `Event` entity (see [Data Dictionary](data_dictionary#entity-event))
- `School` entity (see [Data Dictionary](data_dictionary#entity-school))
- `Student` entity (see [Data Dictionary](data_dictionary#entity-student))

## Auditability

Every dashboard/export must show:

### Required Metadata

1. **Filters Used**
   - District filter (if applied)
   - School filter (if applied)
   - Date range (start_date, end_date)
   - Event type filter (if applied)
   - Event format filter (if applied)

2. **Metric Definition Version**
   - Format: "Metrics Bible v1.0"
   - Updated when metric definitions change
   - Links to this document

3. **Data Freshness**
   - Last sync/import time from Salesforce
   - Last Pathful import time (for virtual events)
   - Cache timestamp (if applicable)

### Implementation

**Example Footer:**
```
Metrics calculated per Metrics Bible v1.0
Filters: District=Kansas City Kansas, Date Range=2024-09-01 to 2025-05-31
Data as of: 2025-01-15 14:30:00 UTC (Salesforce sync: 2025-01-15 14:00:00 UTC)
```

**Reference:**
- See `routes/reports/` for implementation examples
- Cache timestamps in `OrganizationDetailCache`, `DistrictStatsCache` models

---

*Last updated: February 2026*
*Version: 1.0*

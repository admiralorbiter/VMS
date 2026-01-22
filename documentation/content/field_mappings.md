# Field Mappings

**Cross-system data flow specifications**

## Reference

Field definitions are in [Data Dictionary](data_dictionary). This page documents how data flows between systems.

## Normalization Rules (Apply Everywhere)

| Rule | Implementation | Notes |
|------|----------------|-------|
| **Emails** | `trim + lowercase` | Via `get_email_addresses()` in `routes/utils.py` |
| **Strings** | `trim`, collapse repeated whitespace | Applied throughout all string fields |
| **Dropdowns** | Must match controlled vocabulary; reject tampered values | Validated against enum values (GenderEnum, RaceEthnicityEnum, etc.) |
| **Dates** | ISO-8601 with explicit timezone (America/Chicago default) | Via `parse_date()` function in `routes/utils.py`; handles multiple formats |

**Date Parsing Details**:
- Handles ISO 8601 format: `2025-03-05T14:15:00.000+0000`
- Handles CSV format with time: `YYYY-MM-DD HH:MM:SS`
- Handles CSV format without seconds: `YYYY-MM-DD HH:MM`
- Handles date only: `YYYY-MM-DD`
- Returns `datetime` object with timezone support

## Canonical Join Keys

| Entity | Join Key | Format | Notes |
|--------|----------|--------|-------|
| In-person event | `Event.salesforce_id` | SF 18-char ID | Unique, indexed; required for in-person events |
| Volunteer | `Email.email` | Normalized lowercase | Primary join key; dedupe by normalized email |
| Teacher | `Email.email` or `TeacherProgress.email` | Normalized lowercase | Primary join key for roster matching; magic link eligibility |
| Pathful session | `SessionId + teacher_email` | Composite | Composite preferred for idempotent imports |

## 1. Salesforce → VolunTeach (In-person Sync)

**Sync Behavior**: Idempotent on `salesforce_id`. SF edits overwrite VT. VT-owned fields preserved.

**Implementation**: `routes/events/routes.py`, `routes/events/pathway_events.py`

| SF Field | VT/POL Field | Transform | Req | Notes |
|----------|--------------|-----------|-----|-------|
| `Event.Id` | `Event.salesforce_id` | direct | ✅ | 18-char SF ID; unique, indexed |
| `Event.Name` | `Event.title` | trim | ✅ | Required field |
| `Event.Start_Date_and_Time__c` | `Event.start_date` | `parse_date()` → ISO-8601 + tz | ✅ | Required; includes timezone |
| `Event.End_Date_and_Time__c` | `Event.end_date` | `parse_date()` → ISO-8601 + tz | ⛔️ | Optional |
| `Event.School__c` | `Event.school` | direct | ✅ | SF ID format; required for reporting; indexed |
| `Event.Location_Information__c` | `Event.location` | trim | ⛔️ | In-person only: full address string |
| `Event.Volunteers_Needed__c` | `Event.volunteers_needed` | `safe_convert_to_int()` → int ≥0 | ✅ | Required for website |
| `Event.Session_Type__c` | `Event.type` | `map_session_type()` → EventType enum | ✅ | Maps to EventType enum (IN_PERSON, VIRTUAL_SESSION, etc.) |
| `Event.Format__c` | `Event.format` | `map_event_format()` → EventFormat enum | ✅ | Maps to EventFormat enum (IN_PERSON, VIRTUAL) |
| `Event.Session_Status__c` | `Event.status` | direct string or EventStatus enum | ✅ | Maps to EventStatus enum (DRAFT, CONFIRMED, etc.) |
| `Event.Description__c` | `Event.description` | trim | ⛔️ | Optional |
| `Event.Additional_Information__c` | `Event.additional_information` | trim | ⛔️ | Optional |
| `Event.Session_Host__c` | `Event.session_host` | trim, default "PREPKC" | ⛔️ | Default: "PREPKC" |
| `Event.Non_Scheduled_Students_Count__c` | `Event.participant_count` | `safe_convert_to_int()` → int | ⛔️ | Total participants |
| `Event.Total_Requested_Volunteer_Jobs__c` | `Event.total_requested_volunteer_jobs` | `safe_convert_to_int()` → int ≥0 | ⛔️ | Total requested volunteer positions |
| `Event.Available_Slots__c` | `Event.available_slots` | `safe_convert_to_int()` → int ≥0 | ⛔️ | Available volunteer slots |
| `Event.Cancellation_Reason__c` | `Event.cancellation_reason` | `map_cancellation_reason()` → enum | ⛔️ | Maps to CancellationReason enum |
| `Event.District__c` or `Event.Parent_Account__c` | `Event.district_partner` | direct (via DISTRICT_MAPPINGS) | ⛔️ | District name; indexed |
| `Event.Legacy_Skill_Covered_for_the_Session__c` | `Event.skills` (many-to-many) | `parse_event_skills()` | ⛔️ | Parsed and linked to Skill table |
| `Event.Legacy_Skills_Needed__c` | `Event.skills` (many-to-many) | `parse_event_skills()` | ⛔️ | Parsed and linked to Skill table |
| `Event.Requested_Skills__c` | `Event.skills` (many-to-many) | `parse_event_skills()` | ⛔️ | Parsed and linked to Skill table |
| n/a | `Event.inperson_page_visible` | VT-controlled | ✅ | VT-owned; affects public in-person page only; preserved during sync |
| n/a | `Event.district_links[]` | VT-controlled | ⛔️ | VT-owned; linked events show on district pages; preserved during sync |

**VT-Owned Fields** (preserved, not overwritten by SF sync):
- `inperson_page_visible`: Boolean flag controlled by VolunTeach
- `district_links[]`: Array of district links controlled by VolunTeach

**Failure Handling**: Missing required fields (title, salesforce_id, start_date, school) cause event to be skipped with error logged.

## 2. Website Signup → SF + Polaris

**Sync Behavior**: Creates volunteer record in Polaris. May sync to Salesforce separately. Dedupe by normalized email.

**Implementation**: `forms.py`, `routes/volunteers/routes.py`

| Website Field | SF Target | POL Target | Transform | Req | Sensitivity |
|---------------|-----------|------------|-----------|-----|-------------|
| `first_name` | `Contact.FirstName` | `Volunteer.first_name` | trim | ✅ | Sensitive (PII) |
| `last_name` | `Contact.LastName` | `Volunteer.last_name` | trim | ✅ | Sensitive (PII) |
| `middle_name` | `Contact.MiddleName` | `Volunteer.middle_name` | trim | ⛔️ | Sensitive (PII) |
| `email` | `Contact.Email` | `Email.email` | normalize: lowercase + trim | ✅ | Sensitive (PII) |
| `organization_name` | `Contact.Organization__c` | `Volunteer.organization_name` | trim | ⛔️ | Internal |
| `title` | `Contact.Title` | `Volunteer.title` | trim | ⛔️ | Internal |
| `department` | `Contact.Department` | `Volunteer.department` | trim | ⛔️ | Internal |
| `industry` | `Contact.Industry` | `Volunteer.industry` | trim | ⛔️ | Internal |
| `gender` | `Contact.Gender__c` | `Volunteer.gender` | Must match GenderEnum | ⛔️ | Highly Sensitive |
| `race_ethnicity` | `Contact.Racial_Ethnic_Background__c` | `Volunteer.race_ethnicity` | Must match RaceEthnicityEnum | ⛔️ | Highly Sensitive |
| `education` | `Contact.Highest_Level_of_Educational__c` | `Volunteer.education` | Must match EducationEnum | ⛔️ | Highly Sensitive |
| `age_group` | `Contact.Age_Group__c` | `Contact.age_group` | Must match AgeGroupEnum | ⛔️ | Highly Sensitive |
| `skills` | `Contact.Volunteer_Skills__c` | `Volunteer.skills` (many-to-many) | comma-separated, cleaned, linked to Skill table | ⛔️ | Internal |
| `salutation` | `Contact.Salutation` | `Contact.salutation` | Must match SalutationEnum | ⛔️ | Sensitive |
| `suffix` | `Contact.Suffix` | `Contact.suffix` | Must match SuffixEnum | ⛔️ | Sensitive |
| `phone` | `Contact.Phone` | `Phone.number` | trim | ⛔️ | Sensitive (PII) |
| `local_status` | n/a | `Volunteer.local_status` | Must match LocalStatusEnum | ⛔️ | Internal |

**Dedupe Rule**: Match existing volunteer by normalized email (lowercase). If found, update existing record; otherwise create new.

**Validation**:
- Required fields: first_name, last_name, email
- Enum fields must match controlled vocabulary; invalid values rejected
- Email must be valid format (validated by Flask-WTF Email validator)

## 3. Pathful Export → Polaris

**Sync Behavior**: Idempotent on `SessionId + teacher_email` composite key. Unknown teacher/event → row flagged unmatched, not auto-created.

**Implementation**: Referenced in [Data Dictionary](data_dictionary#entity-eventparticipation) and requirements.

| Pathful Column | POL Target | Transform | Idempotency | Notes |
|----------------|------------|-----------|-------------|-------|
| `SessionId` | `EventParticipation.external_row_id` | direct | Primary key | For idempotent imports |
| `EventId` | `Event.session_id` or match by `Event.pathful_event_id` | direct | Must match known event | Must match existing Event record |
| `TeacherEmail` | `Teacher.email` | normalize: lowercase | Join key for roster | Primary join key; must match TeacherProgress or Teacher record |
| `SessionStart` | `EventParticipation` datetime fields | ISO-8601 | — | Session start datetime |
| `AttendanceStatus` | `EventParticipation.status` | Map to enum | — | Maps to attendance status enum |
| `ParticipantType` | `EventParticipation.participant_type` | direct | — | Default: "Volunteer"; also "Presenter" for virtual events |

**Failure Handling**:
- Unknown teacher: Row flagged as unmatched; teacher not auto-created
- Unknown event: Row flagged as unmatched; event not auto-created
- Missing required columns: Import fails with clear missing-columns message

**Idempotency**: Same file imported twice results in updates only, no duplicates (based on `SessionId + teacher_email` composite key).

## 4. Teacher Roster Import

**Sync Behavior**: Creates/updates TeacherProgress records. Used for progress tracking and magic-link eligibility.

**Implementation**: `models/teacher_progress.py`, `routes/virtual/usage.py`

| Roster Column | POL Target | Transform | Req | Notes |
|---------------|-----------|-----------|-----|-------|
| `Teacher Email` | `TeacherProgress.email` | normalize: lowercase | ✅ | Primary key; primary join key for magic links + Pathful |
| `Teacher Name` | `TeacherProgress.name` | split first/last if needed | ✅ | Teacher full name |
| `School` or `Building` | `TeacherProgress.building` | direct | ✅ | School/building name |
| `District` | derived from school relationship | via School.district_id | ⛔️ | Derived from school relationship |
| `Grade` | `TeacherProgress.grade` | direct | ⛔️ | Grade level (K, 1-12, HS, etc.) |
| `Academic Year` | `TeacherProgress.academic_year` | direct | ✅ | e.g., "2024-2025" |
| `Virtual Year` | `TeacherProgress.virtual_year` | direct | ✅ | e.g., "2024-2025" |
| `Target Sessions` | `TeacherProgress.target_sessions` | int, default: 1 | ⛔️ | Target number of sessions; default: 1 |

**Usage**: Used as authoritative list for progress tracking and magic-link eligibility. See [FR-DISTRICT-524](requirements#fr-district-524) and [US-504](user_stories#us-504).

**Matching to Teacher Records**: TeacherProgress entries can be matched to Teacher records via:
- Automatic matching: By email (normalized lowercase)
- Manual matching: Via admin interface (`/virtual/usage/match-teacher-progress`)

**Related Models**:
- `TeacherProgress.teacher_id` (optional FK to `Teacher.id`): Links to Teacher record when matched
- `TeacherProgress.created_by` (FK to `users.id`): User who created record

## Additional Data Flows

### Salesforce → Polaris (Volunteer Import)

**Implementation**: `routes/volunteers/routes.py` (`/volunteers/import-from-salesforce`)

| SF Field | POL Target | Transform | Notes |
|----------|------------|-----------|-------|
| `Contact.Id` | `Volunteer.salesforce_individual_id` | direct | 18-char SF ID |
| `Contact.AccountId` | `Volunteer.salesforce_account_id` | direct | SF Account ID |
| `Contact.FirstName` | `Volunteer.first_name` | trim | Required |
| `Contact.LastName` | `Volunteer.last_name` | trim | Required |
| `Contact.MiddleName` | `Volunteer.middle_name` | trim | Optional |
| `Contact.Email` | `Email.email` | normalize: lowercase + trim | Primary email |
| `Contact.npe01__Preferred_Email__c` | `Email.email` | normalize: lowercase + trim | Preferred email (primary flag) |
| `Contact.npsp__Primary_Affiliation__c` | `Volunteer.organization_name` | trim | Organization name |
| `Contact.Title` | `Volunteer.title` | trim | Job title |
| `Contact.Department` | `Volunteer.department` | trim | Department |
| `Contact.Industry` | `Volunteer.industry` | trim | Industry |
| `Contact.Gender__c` | `Volunteer.gender` | `map_gender()` → GenderEnum | Maps to enum |
| `Contact.Birthdate` | `Contact.birthdate` | `parse_date()` | Date of birth |
| `Contact.Racial_Ethnic_Background__c` | `Volunteer.race_ethnicity` | map to RaceEthnicityEnum | Maps to enum |
| `Contact.Highest_Level_of_Educational__c` | `Volunteer.education` | map to EducationEnum | Maps to enum |
| `Contact.Age_Group__c` | `Contact.age_group` | map to AgeGroupEnum | Maps to enum |
| `Contact.Volunteer_Skills__c` | `Volunteer.skills` (many-to-many) | `parse_volunteer_skills()` | Parsed and linked to Skill table |
| `Contact.First_Volunteer_Date__c` | `Volunteer.first_volunteer_date` | `parse_date()` | First volunteer date |
| `Contact.Last_Volunteer_Date__c` | `Volunteer.last_volunteer_date` | `parse_date()` | Last volunteer date |
| `Contact.DoNotCall` | `Contact.do_not_call` | direct boolean | Phone contact preference |
| `Contact.npsp__Do_Not_Contact__c` | `Contact.do_not_contact` | direct boolean | General contact preference |
| `Contact.HasOptedOutOfEmail` | `Contact.email_opt_out` | direct boolean | Email marketing preference |
| `Contact.EmailBouncedDate` | `Contact.email_bounced_date` | `parse_date()` | Failed email delivery tracking |

**Dedupe**: Match by `salesforce_individual_id` (SF Contact.Id). If found, update existing; otherwise create new.

### Salesforce → Polaris (Teacher Import)

**Implementation**: `routes/teachers/routes.py` (`/teachers/import-from-salesforce`)

| SF Field | POL Target | Transform | Notes |
|----------|------------|-----------|-------|
| `Contact.Id` | `Teacher.salesforce_individual_id` | direct | 18-char SF ID |
| `Contact.AccountId` | `Teacher.salesforce_account_id` | direct | SF Account ID |
| `Contact.FirstName` | `Teacher.first_name` | trim | Required |
| `Contact.LastName` | `Teacher.last_name` | trim | Required |
| `Contact.Email` | `Email.email` | normalize: lowercase + trim | Primary email |
| `Contact.npsp__Primary_Affiliation__c` | `Teacher.school_id` | direct | School SF ID |
| `Contact.Department` | `Teacher.department` | trim | Department |
| `Contact.Gender__c` | `Teacher.gender` | map to GenderEnum | Maps to enum |
| `Contact.Phone` | `Phone.number` | trim | Primary phone |

**Dedupe**: Match by `salesforce_individual_id` (SF Contact.Id). If found, update existing; otherwise create new.

### Salesforce → Polaris (Student Participation Import)

**Implementation**: `routes/events/routes.py` (`process_student_participation_row()`)

| SF Field | POL Target | Transform | Notes |
|----------|------------|-----------|-------|
| `Session_Participant__c.Id` | `EventStudentParticipation.salesforce_id` | direct | 18-char SF ID; unique |
| `Session_Participant__c.Session__c` | `EventStudentParticipation.event_id` | match by `Event.salesforce_id` | Must match existing Event |
| `Session_Participant__c.Contact__c` | `EventStudentParticipation.student_id` | match by `Student.salesforce_individual_id` | Must match existing Student |
| `Session_Participant__c.Status__c` | `EventStudentParticipation.status` | direct | e.g., 'Registered', 'Attended', 'No Show' |
| `Session_Participant__c.Delivery_Hours__c` | `EventStudentParticipation.delivery_hours` | parse float | Delivery hours |
| `Session_Participant__c.Age_Group__c` | `EventStudentParticipation.age_group` | direct | Age group at time of event |

**Idempotency**: Unique constraint on (`event_id`, `student_id`). If pair exists, update; otherwise create new.

---

*Last updated: January 2026*
*Version: 1.0*

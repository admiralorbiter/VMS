# Data Dictionary

**Canonical entity and field definitions — Source of Truth**

## Source of Truth

This is the authoritative reference for all entity definitions. Other documents reference these definitions rather than restating them.

**Related Documentation:**
- [Functional Requirements](requirements) - System requirements
- [User Stories](user_stories) - Business intent
- [Use Cases](use_cases) - End-to-end workflows
- [Non-Functional Requirements](non_functional_requirements) - Quality attributes

## Sensitivity Levels

| Level | Description | Examples |
|-------|-------------|----------|
| **Public** | Safe to show publicly | Event titles, public event listings |
| **Internal** | Internal-only, not sensitive | Organization names, event counts, status fields |
| **Sensitive** | PII like name/email; internal-only | Volunteer names, email addresses, phone numbers |
| **Highly Sensitive** | Students, demographics, regulated data | Student data, race/ethnicity, gender, age group, education attainment |

## Entity: Contact

**Base class for Volunteer, Teacher, and Student (polymorphic inheritance)**

**Table**: `contact`

**Inheritance**: Volunteer, Teacher, and Student inherit all Contact fields via SQLAlchemy polymorphic inheritance.

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key, unique, immutable |
| `type` | String(50) | POL | Internal | Polymorphic discriminator: 'volunteer', 'teacher', 'student' |
| `salesforce_individual_id` | String(18) | SF | Sensitive | Optional; unique when present; links to Salesforce Contact |
| `salesforce_account_id` | String(18) | SF | Internal | Optional; links to Salesforce Account |
| `salutation` | Enum(SalutationEnum) | WEB→SF/POL | Sensitive | Mr., Ms., Mrs., Dr., etc. |
| `first_name` | String(50) | WEB→SF/POL | Sensitive | Required; trim whitespace |
| `middle_name` | String(50) | WEB→SF/POL | Sensitive | Optional |
| `last_name` | String(50) | WEB→SF/POL | Sensitive | Required; trim whitespace |
| `suffix` | Enum(SuffixEnum) | WEB→SF/POL | Sensitive | Jr., Sr., II, III, Ph.D., etc. |
| `age_group` | Enum(AgeGroupEnum) | WEB→SF/POL | Highly Sensitive | Controlled vocabulary |
| `education_level` | Enum(EducationEnum) | WEB→SF/POL | Highly Sensitive | Controlled vocabulary |
| `birthdate` | Date | SF/POL | Highly Sensitive | Optional |
| `gender` | Enum(GenderEnum) | WEB→SF/POL | Highly Sensitive | Controlled vocabulary |
| `race_ethnicity` | Enum(RaceEthnicityEnum) | WEB→SF/POL | Highly Sensitive | Controlled vocabulary |
| `do_not_call` | Boolean | POL | Internal | Phone contact preference |
| `do_not_contact` | Boolean | POL | Internal | General contact preference |
| `email_opt_out` | Boolean | POL | Internal | Email marketing preference |
| `email_bounced_date` | DateTime | POL | Internal | Tracks failed email deliveries |
| `exclude_from_reports` | Boolean | POL | Internal | Excludes from reports and statistics |
| `last_email_date` | Date | POL | Internal | Date of last email communication |
| `notes` | Text | POL | Internal | General contact notes |
| `description` | Text | POL | Internal | General notes about contact |

**Related Tables**:
- `phone` - Multiple phone numbers per contact
- `email` - Multiple email addresses per contact
- `address` - Multiple addresses per contact

## Entity: Volunteer

**Inherits from Contact**

**Table**: `volunteer`

**Polymorphic Identity**: `volunteer`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer (FK to contact.id) | POL | Internal | Primary key, references contact.id |
| *All Contact fields* | *See Contact entity* | *See Contact entity* | *See Contact entity* | Inherits all Contact fields |
| `organization_name` | String(100) | WEB→SF/POL | Internal | Current workplace |
| `title` | String(50) | WEB→SF/POL | Internal | Job title |
| `department` | String(50) | POL | Internal | Department within organization |
| `industry` | String(50) | POL | Internal | Industry sector |
| `education` | Enum(EducationEnum) | WEB→SF/POL | Highly Sensitive | Alias for education_level from Contact |
| `local_status` | Enum(LocalStatusEnum) | Derived (POL) | Internal | Calculated: local, partial, non_local, unknown |
| `local_status_last_updated` | DateTime | POL | Internal | When local_status was last calculated |
| `is_people_of_color` | Boolean | POL | Highly Sensitive | For virtual session tracking |
| `first_volunteer_date` | Date | POL | Internal | First time they volunteered |
| `last_volunteer_date` | Date | POL | Internal | Most recent volunteer activity (indexed) |
| `last_non_internal_email_date` | Date | POL | Internal | Last external communication |
| `last_activity_date` | Date | POL | Internal | Any type of activity (indexed) |
| `times_volunteered` | Integer | SF/POL | Internal | Number of recorded volunteer sessions |
| `additional_volunteer_count` | Integer | POL | Internal | Manual adjustment to volunteer count |
| `last_mailchimp_activity_date` | Date | POL | Internal | Mailchimp engagement tracking |
| `mailchimp_history` | Text | POL | Internal | Historical email engagement data |
| `admin_contacts` | String(200) | POL | Internal | Staff members who've worked with this volunteer |
| `interests` | Text | POL | Internal | Semicolon-separated volunteer interests |
| `status` | Enum(VolunteerStatus) | POL | Internal | active, inactive, on_hold |

**Relationships**:
- Many-to-many with `Skill` (through `volunteer_skills`)
- Many-to-many with `Organization` (through `volunteer_organization`)
- One-to-many with `Engagement`
- One-to-many with `EventParticipation`
- One-to-one with `ConnectorData` (optional)

## Entity: Event

**Table**: `event`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL/VT | Internal | Primary key |
| `salesforce_id` | String(18) | SF | Internal | Required for in-person; unique; canonical join key; indexed |
| `title` | String(255) | SF/POL | Public | Required |
| `description` | Text | SF/POL | Public | Optional |
| `type` | Enum(EventType) | POL | Internal | InPerson, VirtualSession, CareerFair, etc. (indexed) |
| `format` | Enum(EventFormat) | POL | Internal | InPerson or Virtual (required) |
| `start_date` | DateTime(timezone=True) | SF/POL | Public | Required; includes timezone |
| `end_date` | DateTime(timezone=True) | SF/POL | Public | Optional |
| `duration` | Integer | SF/POL | Internal | Duration in minutes |
| `status` | Enum(EventStatus) | SF/POL | Internal | Draft, Requested, Confirmed, Published, Completed, Cancelled, etc. (indexed) |
| `cancellation_reason` | Enum(CancellationReason) | SF | Internal | Weather, LowEnrollment, etc. |
| `location` | String(255) | SF | Public | In-person only: full address string |
| `school` | String(18) (FK to school.id) | SF/POL | Internal | Required for reporting; indexed |
| `district_partner` | String(255) | SF/POL | Internal | District name; indexed |
| `available_slots` | Integer | SF→VT/POL | Public | **Imported from SF** (Available_Slots__c); available volunteer slots; defaults to 0 |
| `participant_count` | Integer | SF/POL | Internal | Total participants |
| `registered_count` | Integer | SF/POL | Internal | Registered participants (indexed) |
| `attended_count` | Integer | SF/POL | Internal | Attended participants |
| `scheduled_participants_count` | Integer | POL | Internal | Scheduled participants |
| `total_requested_volunteer_jobs` | Integer | POL | Internal | Total requested volunteer positions |
| `additional_information` | Text | SF/POL | Public | Additional event details |
| `session_id` | String(255) | SF/PATH | Internal | Pathful session ID for virtual events |
| `session_host` | String(255) | SF | Internal | Default: "PREPKC" |
| `series` | String(255) | SF/POL | Internal | Event series name |
| `registration_link` | String(1300) | SF/POL | Public | Registration URL |
| `original_status_string` | String(255) | SF | Internal | Original status string for analysis |
| `educators` | Text | SF/POL | Sensitive | Semicolon-separated educator names |
| `educator_ids` | Text | SF/POL | Internal | Semicolon-separated educator IDs |
| `professionals` | Text | SF/POL | Sensitive | Semicolon-separated professional names |
| `professional_ids` | Text | SF/POL | Internal | Semicolon-separated professional IDs |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |

**VolunTeach-Specific Fields** (managed in VolunTeach):
- `name` | String | SF→VT | Public | Event title (from SF Name)
- `event_type` | String | SF→VT | Public | Session type (from SF Session_Type__c)
- `date_and_time` | String | SF→VT | Public | Display string (from SF Date_and_Time_for_Cal__c)
- `display_on_website` | Boolean | SF→VT | Public | **Imported on creation only** from Display_on_Website__c; preserved locally on updates
- `status` | String | VT | Public | VT-managed: 'active' or 'archived'; auto-set based on slots
- `source` | String | VT | Internal | 'salesforce' for In-Person, 'virtual' for Virtual
- `note` | Text | VT | Internal | VT-only field for internal staff notes
- `districts` | Relationship | VT | Internal | VT-managed via EventDistrictMapping table

**Relationships**:
- Many-to-many with `Volunteer` (through `event_volunteers`)
- Many-to-many with `District` (through `event_districts`)
- Many-to-many with `Skill` (through `event_skills`)
- One-to-many with `EventTeacher` (teacher participation)
- One-to-many with `EventParticipation` (volunteer participation)
- One-to-many with `EventStudentParticipation` (student participation)
- One-to-one with `EventAttendanceDetail`
- One-to-one with `EventAttendance`
- One-to-many with `EventComment`

## Entity: Teacher

**Inherits from Contact**

**Table**: `teacher`

**Polymorphic Identity**: `teacher`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer (FK to contact.id) | POL | Internal | Primary key, references contact.id |
| *All Contact fields* | *See Contact entity* | *See Contact entity* | *See Contact entity* | Inherits all Contact fields |
| `department` | String(50) | SF/POL | Internal | Department within school |
| `school_id` | String(255) | SF/POL | Internal | Maps to npsp__Primary_Affiliation__c; indexed |
| `status` | Enum(TeacherStatus) | POL | Internal | active, inactive, on_leave, retired (indexed) |
| `active` | Boolean | POL | Internal | Active status flag |
| `connector_role` | String(50) | SF/POL | Internal | Role in connector program |
| `connector_active` | Boolean | SF/POL | Internal | Active in connector program |
| `connector_start_date` | Date | SF/POL | Internal | Connector program start |
| `connector_end_date` | Date | SF/POL | Internal | Connector program end |
| `last_email_message` | Date | SF/POL | Internal | Last email communication date |
| `last_mailchimp_date` | Date | SF/POL | Internal | Last Mailchimp email date |
| `salesforce_contact_id` | String(18) | SF | Sensitive | Unique when present; indexed |
| `salesforce_school_id` | String(18) | SF | Internal | School reference in Salesforce |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |

**Relationships**:
- Many-to-many with `Event` (through `event_teacher`)
- One-to-many with `Student` (via `teacher_id`)

## Entity: Student

**Inherits from Contact**

**Table**: `student`

**Polymorphic Identity**: `student`

**Privacy Note**: Student data is Highly Sensitive. District viewers see aggregates only, never student-level PII. See [Privacy & Data Handling](privacy_data_handling) and [NFR-4](non_functional_requirements#nfr-4).

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer (FK to contact.id) | POL | Highly Sensitive | Primary key, references contact.id |
| *All Contact fields* | *See Contact entity* | *See Contact entity* | *See Contact entity* | Inherits all Contact fields |
| `active` | Boolean | POL | Internal | Active status flag |
| `current_grade` | Integer | SF/POL | Highly Sensitive | Grade level 0-12 |
| `legacy_grade` | String(50) | SF | Highly Sensitive | Legacy Grade__C from Salesforce |
| `student_id` | String(50) | SF | Highly Sensitive | Local_Student_ID__c - School-specific identifier; indexed |
| `school_id` | String(18) (FK to school.id) | SF | Highly Sensitive | Required for aggregation; indexed |
| `class_salesforce_id` | String(18) (FK to class.salesforce_id) | SF | Highly Sensitive | References Class.salesforce_id; indexed |
| `teacher_id` | Integer (FK to teacher.id) | SF/POL | Highly Sensitive | References Teacher.id; indexed |
| `racial_ethnic` | String(100) | SF | Highly Sensitive | Student's racial/ethnic identification |
| `school_code` | String(50) | SF | Internal | School-specific code; indexed |
| `ell_language` | String(50) | SF | Highly Sensitive | English Language Learner primary language |
| `gifted` | Boolean | SF | Highly Sensitive | Gifted program participation status |
| `lunch_status` | String(50) | SF | Highly Sensitive | Student lunch program status |

**Relationships**:
- Many-to-one with `School` (via `school_id`)
- Many-to-one with `Teacher` (via `teacher_id`)
- Many-to-one with `Class` (via `class_salesforce_id`)
- One-to-many with `EventStudentParticipation`

## Entity: EventParticipation

**Volunteer participation in events**

**Table**: `event_participation`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key |
| `volunteer_id` | Integer (FK to volunteer.id) | WEB/SF/POL | Sensitive | Required; references Volunteer |
| `event_id` | Integer (FK to event.id) | SF/WEB/POL | Internal | Required; references Event |
| `status` | String(20) | SF/WEB/POL | Internal | Attended, Completed, Successfully Completed, No-Show, Cancelled, etc. |
| `delivery_hours` | Float | SF | Internal | Hours contributed to event |
| `salesforce_id` | String(18) | SF | Internal | Unique when present; links to Session_Participant__c |
| `age_group` | String(50) | SF/WEB | Highly Sensitive | Age group at time of event |
| `email` | String(255) | WEB | Sensitive | Email used for event registration |
| `title` | String(100) | WEB | Internal | Professional title at time of event |
| `participant_type` | String(50) | POL | Internal | Default: "Volunteer"; also "Presenter" for virtual events |
| `contact` | String(255) | WEB | Sensitive | Additional contact information |

**Relationships**:
- Many-to-one with `Volunteer` (via `volunteer_id`)
- Many-to-one with `Event` (via `event_id`)

**Implementation Note: Presenter Recruitment**

To identify events needing presenters, query for Virtual events where no EventParticipation record with `participant_type='Presenter'` exists:

```sql
SELECT events
WHERE event_type = 'Virtual'
  AND start_datetime > NOW()
  AND NOT EXISTS (
    SELECT 1 FROM event_participation
    WHERE participant_type = 'Presenter'
      AND event_id = events.id
  )
ORDER BY start_date ASC
```

Route: `/virtual/usage/recruitment` (implemented in `routes/virtual/usage.py`)

## Entity: EventTeacher

**Teacher participation in events**

**Table**: `event_teacher`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `event_id` | Integer (FK to event.id) | POL | Internal | Primary key (composite) |
| `teacher_id` | Integer (FK to teacher.id) | POL | Sensitive | Primary key (composite) |
| `status` | String(50) | POL | Internal | registered, attended, no_show, cancelled |
| `is_simulcast` | Boolean | POL | Internal | Simulcast participation flag |
| `attendance_confirmed_at` | DateTime(timezone=True) | POL | Internal | When attendance was confirmed |
| `notes` | Text | POL | Internal | Additional notes |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |

**Relationships**:
- Many-to-one with `Event` (via `event_id`)
- Many-to-one with `Teacher` (via `teacher_id`)

## Entity: EventStudentParticipation

**Student participation in events**

**Table**: `event_student_participation`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Highly Sensitive | Primary key |
| `salesforce_id` | String(18) | SF | Highly Sensitive | Unique when present; links to Session_Participant__c; indexed |
| `event_id` | Integer (FK to event.id) | SF | Highly Sensitive | Required; references Event; indexed |
| `student_id` | Integer (FK to student.id) | SF | Highly Sensitive | Required; references Student; indexed |
| `status` | String(50) | SF | Highly Sensitive | Registered, Attended, No Show, etc. |
| `delivery_hours` | Float | SF | Internal | Delivery hours from Delivery_Hours__c |
| `age_group` | String(100) | SF | Highly Sensitive | From Age_Group__c |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |

**Relationships**:
- Many-to-one with `Event` (via `event_id`)
- Many-to-one with `Student` (via `student_id`)

**Constraints**: Unique constraint on (`event_id`, `student_id`)

## Entity: Organization

**Table**: `organization`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key |
| `salesforce_id` | String(18) | SF | Internal | Unique when present; links to Salesforce Account; indexed |
| `name` | String(255) | WEB→SF/POL | Internal | Required; indexed |
| `type` | String(255) | POL | Internal | Organization classification |
| `description` | String(255) | POL | Internal | Organization description |
| `volunteer_salesforce_id` | String(18) | SF | Internal | Reference to volunteer record; indexed |
| `billing_street` | String(255) | SF | Internal | Billing address street |
| `billing_city` | String(255) | SF | Internal | Billing address city |
| `billing_state` | String(255) | SF | Internal | Billing address state |
| `billing_postal_code` | String(255) | SF | Internal | Billing address postal code |
| `billing_country` | String(255) | SF | Internal | Billing address country |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |
| `last_activity_date` | DateTime | POL | Internal | Business-level activity tracking |

**Relationships**:
- Many-to-many with `Volunteer` (through `volunteer_organization`)

## Entity: District

**Table**: `district`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key, auto-incrementing |
| `salesforce_id` | String(18) | SF | Internal | Unique when present; indexed |
| `name` | String(255) | SF/POL | Internal | Required; district's official name |
| `district_code` | String(20) | SF/POL | Internal | Optional external reference code |

**Relationships**:
- One-to-many with `School` (via `district_id` in School)
- Many-to-many with `Event` (through `event_districts`)

## Entity: School

**Table**: `school`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | String(255) | SF | Internal | Primary key; Salesforce ID format |
| `name` | String(255) | SF/POL | Internal | Required; school's official name |
| `district_id` | Integer (FK to district.id) | SF/POL | Internal | References District |
| `salesforce_district_id` | String(255) | SF | Internal | External district reference |
| `normalized_name` | String(255) | POL | Internal | Standardized name for consistent searching |
| `school_code` | String(255) | SF/POL | Internal | External reference code |
| `level` | String(50) | SF/POL | Internal | High, Elementary, Middle, etc. |

**Relationships**:
- Many-to-one with `District` (via `district_id`)
- One-to-many with `Event` (via `school` field)
- One-to-many with `Teacher` (via `school_id`)
- One-to-many with `Student` (via `school_id`)

## Entity: TeacherProgress

**Teacher progress tracking for virtual sessions**

**Table**: `teacher_progress`

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key |
| `academic_year` | String(10) | Roster | Internal | e.g., "2024-2025"; required |
| `virtual_year` | String(10) | Roster | Internal | e.g., "2024-2025"; required |
| `building` | String(100) | Roster | Internal | School/building name; required |
| `name` | String(200) | Roster | Sensitive | Teacher full name; required |
| `email` | String(255) | Roster | Sensitive | Teacher email; required; primary join key for magic links |
| `grade` | String(50) | Roster | Internal | Grade level (K, 1-12, HS, etc.) |
| `target_sessions` | Integer | Roster | Internal | Target number of sessions; default: 1 |
| `teacher_id` | Integer (FK to teacher.id) | POL | Internal | Optional; link to Teacher record |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |
| `created_by` | Integer (FK to users.id) | POL | Internal | User who created record |

**Relationships**:
- Many-to-one with `Teacher` (via `teacher_id`, optional)

**Usage**: Used as authoritative list for progress tracking and magic-link eligibility. See [FR-DISTRICT-524](requirements-district#fr-district-524) and [US-504](user-stories#us-504).

## Entity: Tenant (District Suite)

**Multi-tenant registry for district platforms**

**Table**: `tenant` (in main database only)

> [!NOTE]
> **District Suite** entity. Tenants represent district platforms with isolated databases and users.

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key |
| `slug` | String(50) | POL | Internal | Required; unique; URL-safe identifier (e.g., "kckps"); indexed |
| `name` | String(255) | POL | Internal | Required; display name (e.g., "KCKPS") |
| `district_id` | Integer (FK to district.id) | POL | Internal | Optional; link to existing District record |
| `is_active` | Boolean | POL | Internal | Default: True; deactivated tenants cannot be accessed |
| `settings` | JSON | POL | Internal | Tenant-specific configuration (feature flags, branding) |
| `api_key_hash` | String(255) | POL | Internal | Hashed API key for public event API |
| `api_key_created_at` | DateTime(timezone=True) | POL | Internal | When API key was last generated |
| `database_path` | String(500) | POL | Internal | Path to tenant's SQLite database file |
| `allowed_origins` | Text | POL | Internal | Comma-separated list of allowed CORS origins |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |
| `created_by` | Integer (FK to users.id) | POL | Internal | PrepKC admin who created tenant |

**Relationships**:
- Many-to-one with `District` (via `district_id`, optional)
- One-to-many with `TenantUser` (via `tenant_id`)

**Settings JSON Structure**:
```json
{
  "features": {
    "events_enabled": true,
    "volunteers_enabled": true,
    "recruitment_enabled": false,
    "prepkc_visibility_enabled": false
  },
  "branding": {
    "primary_color": "#1976d2",
    "logo_url": null
  }
}
```

**Reference:** [FR-TENANT-101](requirements-district-suite#fr-tenant-101) through [FR-TENANT-107](requirements-district-suite#fr-tenant-107)

## Entity: TenantUser (District Suite)

**Users scoped to a specific tenant**

**Table**: `tenant_user` (in tenant database)

> [!NOTE]
> TenantUser is stored in each tenant's database and represents district staff with access to that tenant only.

| Field | Type | Source | Sensitivity | Notes |
|-------|------|--------|-------------|-------|
| `id` | Integer | POL | Internal | Primary key |
| `email` | String(255) | POL | Sensitive | Required; unique within tenant; login identifier |
| `password_hash` | String(255) | POL | Internal | Hashed password |
| `first_name` | String(100) | POL | Sensitive | Required |
| `last_name` | String(100) | POL | Sensitive | Required |
| `role` | Enum(TenantRole) | POL | Internal | district_admin, district_coordinator, district_viewer |
| `is_active` | Boolean | POL | Internal | Default: True |
| `last_login_at` | DateTime(timezone=True) | POL | Internal | Tracks login history |
| `created_at` | DateTime(timezone=True) | POL | Internal | Auto-set on creation |
| `updated_at` | DateTime(timezone=True) | POL | Internal | Auto-updated on modification |

**TenantRole Enum**:
- `district_admin` - Full access to tenant features
- `district_coordinator` - Event and volunteer management
- `district_viewer` - Read-only access to dashboards

**Reference:** [FR-TENANT-103](requirements-district-suite#fr-tenant-103)

## Controlled Vocabularies

Managed in one place and validated everywhere. All enums are defined in `models/contact.py` and `models/event.py`.

### Education Attainment

**Enum**: `EducationEnum`
**Sensitivity**: Highly Sensitive
**Values**:
- `UNKNOWN` (empty string)
- `HIGH_SCHOOL` ("High School")
- `SOME_COLLEGE` ("Some College")
- `ASSOCIATES` ("Associates Degree")
- `BACHELORS_DEGREE` ("Bachelor's Degree")
- `MASTERS` ("Masters Degree")
- `DOCTORATE` ("Doctorate")
- `PROFESSIONAL` ("Professional Degree")
- `OTHER` ("Other")

### Race/Ethnicity

**Enum**: `RaceEthnicityEnum`
**Sensitivity**: Highly Sensitive
**Values**:
- `unknown` ("Unknown")
- `american_indian` ("American Indian or Alaska Native")
- `asian` ("Asian")
- `black` ("Black or African American")
- `hispanic` ("Hispanic or Latino")
- `native_hawaiian` ("Native Hawaiian or Other Pacific Islander")
- `white` ("White")
- `multi_racial` ("Multi-racial")
- `bi_racial` ("Bi-racial")
- `two_or_more` ("Two or More Races")
- `prefer_not_to_say` ("Prefer not to say")
- `other` ("Other")
- `other_poc` ("Other POC")

### Gender

**Enum**: `GenderEnum`
**Sensitivity**: Highly Sensitive
**Values**:
- `male` ("Male")
- `female` ("Female")
- `non_binary` ("Non-binary")
- `genderfluid` ("Genderfluid")
- `agender` ("Agender")
- `transgender` ("Transgender")
- `prefer_not_to_say` ("Prefer not to say")
- `other` ("Other")

### Age Group

**Enum**: `AgeGroupEnum`
**Sensitivity**: Highly Sensitive
**Values**:
- `UNKNOWN` (empty string)
- `UNDER_18` ("Under 18")
- `AGE_18_24` ("18-24")
- `AGE_25_34` ("25-34")
- `AGE_35_44` ("35-44")
- `AGE_45_54` ("45-54")
- `AGE_55_64` ("55-64")
- `AGE_65_PLUS` ("65+")

### Local Status

**Enum**: `LocalStatusEnum`
**Sensitivity**: Internal
**Values**:
- `local` ("local") - Within KC metro
- `partial` ("partial") - Within driving distance
- `non_local` ("non_local") - Too far
- `unknown` ("unknown") - No address data

### Event Type

**Enum**: `EventType`
**Sensitivity**: Internal
**Values**: `IN_PERSON`, `VIRTUAL_SESSION`, `CONNECTOR_SESSION`, `CAREER_JUMPING`, `CAREER_SPEAKER`, `EMPLOYABILITY_SKILLS`, `IGNITE`, `CAREER_FAIR`, `CLIENT_CONNECTED_PROJECT`, `PATHWAY_CAMPUS_VISITS`, `WORKPLACE_VISIT`, `PATHWAY_WORKPLACE_VISITS`, `COLLEGE_OPTIONS`, `DIA_CLASSROOM_SPEAKER`, `DIA`, `CAMPUS_VISIT`, `ADVISORY_SESSIONS`, `VOLUNTEER_ORIENTATION`, `VOLUNTEER_ENGAGEMENT`, `MENTORING`, `FINANCIAL_LITERACY`, `MATH_RELAYS`, `CLASSROOM_SPEAKER`, `INTERNSHIP`, `COLLEGE_APPLICATION_FAIR`, `FAFSA`, `CLASSROOM_ACTIVITY`, `HISTORICAL`, `DATA_VIZ`, `P2GD`, `SLA`, `HEALTHSTART`, `P2T`, `BFI`

### Event Format

**Enum**: `EventFormat`
**Sensitivity**: Internal
**Values**:
- `IN_PERSON` ("in_person")
- `VIRTUAL` ("virtual")

### Event Status

**Enum**: `EventStatus`
**Sensitivity**: Internal
**Values**: `COMPLETED`, `CONFIRMED`, `CANCELLED`, `REQUESTED`, `DRAFT`, `PUBLISHED`, `NO_SHOW`, `SIMULCAST`, `COUNT`

### Event Source (District Suite)

**Enum**: `EventSource`
**Sensitivity**: Internal
**Values**:
- `salesforce` ("salesforce") - Synced from Salesforce (PrepKC events)
- `polaris_prepkc` ("polaris_prepkc") - Created in Polaris by PrepKC staff
- `polaris_district` ("polaris_district") - Created in Polaris by district staff

### Attendance Status

**Enum**: `AttendanceStatus` (for EventAttendance)
**Sensitivity**: Internal
**Values**:
- `NOT_TAKEN` ("not_taken")
- `IN_PROGRESS` ("in_progress")
- `COMPLETED` ("completed")

### Participant Type

**Field**: `EventParticipation.participant_type`
**Sensitivity**: Internal
**Values**: `"Volunteer"` (default), `"Presenter"`, and other role types

### Tenant Role (District Suite)

**Enum**: `TenantRole`
**Sensitivity**: Internal
**Values**:
- `district_admin` ("district_admin") - Full tenant access
- `district_coordinator` ("district_coordinator") - Event/volunteer management
- `district_viewer` ("district_viewer") - Read-only dashboard access

### Volunteer Skills

**Table**: `skill`
**Sensitivity**: Internal
**Management**: Managed in Polaris config; stored in `skill` table with many-to-many relationship through `volunteer_skills`

### Career Type

**Sensitivity**: Internal
**Management**: Managed in Polaris config

---

*Last updated: February 2026*
*Version: 1.1*

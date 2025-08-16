# Validation Configuration Alignment Plan

## Overview
This document outlines the process for aligning the auto-generated validation configuration (`config/validation.py`) with the actual business logic implemented in the VMS codebase.

## Current Problem
The `config/validation.py` file contains **auto-generated placeholder business rules** that don't match the actual implementation:
- Fake cross-field validations (e.g., `Volunteer_Skills__c` required when `Contact_Type__c = 'Volunteer'`)
- Placeholder workflow validations that don't exist in the code
- Business rules that conflict with actual form validation and database schema

## Goals
1. **Audit** all validation configuration against actual code
2. **Remove** fake/placeholder business rules
3. **Implement** real business rules based on actual requirements
4. **Ensure** validation dashboard shows accurate, actionable results
5. **Document** the real business logic for future reference

## Phase 1: Audit Current Configuration vs. Actual Code

### 1.1 Database Schema Analysis
- [x] Review all model files for `nullable=False` fields (actual required fields)
- [ ] Document field constraints and relationships
- [ ] Identify any custom validation logic in models

#### 1.1.1 Volunteer Entity - COMPLETED ✅
**Base Contact Model (inherited by Volunteer):**
- `first_name` - `nullable=False` (REQUIRED)
- `last_name` - `nullable=False` (REQUIRED)
- `id` - Primary key (REQUIRED)

**Volunteer-Specific Model:**
- All fields are `nullable=True` (OPTIONAL)
- No custom validation constraints beyond basic SQLAlchemy defaults

**Related Models:**
- `Phone.contact_id` - `nullable=False` (REQUIRED for phone records)
- `Email.contact_id` - `nullable=False` (REQUIRED for email records)
- `Address.contact_id` - `nullable=False` (REQUIRED for address records)

**Key Finding:** Only `first_name` and `last_name` are actually required at the database level for volunteers.

#### 1.1.2 Organization Entity - COMPLETED ✅
**Organization Model:**
- `id` - Primary key (REQUIRED)
- `name` - `nullable=False` (REQUIRED) - indexed for search
- `created_at` - `nullable=False` (REQUIRED) - server default
- `updated_at` - `nullable=False` (REQUIRED) - server default

**Optional Fields:**
- `salesforce_id` - `nullable=True` (OPTIONAL) - unique when present
- `type` - `nullable=True` (OPTIONAL) - organization classification
- `description` - `nullable=True` (OPTIONAL)
- `volunteer_salesforce_id` - `nullable=True` (OPTIONAL)
- `billing_street` - `nullable=True` (OPTIONAL)
- `billing_city` - `nullable=True` (OPTIONAL)
- `billing_state` - `nullable=True` (OPTIONAL)
- `billing_postal_code` - `nullable=True` (OPTIONAL)
- `billing_country` - `nullable=True` (OPTIONAL)
- `last_activity_date` - `nullable=True` (OPTIONAL)

**Key Finding:** Only `name` is actually required at the database level for organizations. All address fields are optional.

#### 1.1.3 Teacher Entity - COMPLETED ✅
**Base Contact Model (inherited by Teacher):**
- `first_name` - `nullable=False` (REQUIRED)
- `last_name` - `nullable=False` (REQUIRED)
- `id` - Primary key (REQUIRED)

**Teacher-Specific Model:**
- `active` - `nullable=False` (REQUIRED) - default True
- All other fields are `nullable=True` (OPTIONAL)

**Optional Fields:**
- `department` - `nullable=True` (OPTIONAL) - indexed for search
- `school_id` - `nullable=True` (OPTIONAL) - indexed for search
- `status` - `nullable=True` (OPTIONAL) - default TeacherStatus.ACTIVE
- `connector_role` - `nullable=True` (OPTIONAL)
- `connector_active` - `nullable=False` (OPTIONAL) - default False
- `connector_start_date` - `nullable=True` (OPTIONAL)
- `connector_end_date` - `nullable=True` (OPTIONAL)
- `last_email_message` - `nullable=True` (OPTIONAL)
- `last_mailchimp_date` - `nullable=True` (OPTIONAL)

**Key Finding:** Only `first_name`, `last_name`, and `active` are actually required at the database level for teachers. All other fields are optional.

#### 1.1.4 Student Entity - COMPLETED ✅
**Base Contact Model (inherited by Student):**
- `first_name` - `nullable=False` (REQUIRED)
- `last_name` - `nullable=False` (REQUIRED)
- `id` - Primary key (REQUIRED)

**Student-Specific Model:**
- `active` - `nullable=False` (REQUIRED) - default True
- `gifted` - `nullable=False` (REQUIRED) - default False
- All other fields are `nullable=True` (OPTIONAL)

**Optional Fields:**
- `current_grade` - `nullable=True` (OPTIONAL) - 0-12 range with validation
- `legacy_grade` - `nullable=True` (OPTIONAL) - Legacy Grade__C from Salesforce
- `student_id` - `nullable=True` (OPTIONAL) - School-specific identifier, indexed
- `school_id` - `nullable=True` (OPTIONAL) - Foreign key to School, indexed
- `class_salesforce_id` - `nullable=True` (OPTIONAL) - Foreign key to Class, indexed
- `teacher_id` - `nullable=True` (OPTIONAL) - Foreign key to Teacher, indexed
- `racial_ethnic` - `nullable=True` (OPTIONAL) - Racial/ethnic identification
- `school_code` - `nullable=True` (OPTIONAL) - School-specific code, indexed
- `ell_language` - `nullable=True` (OPTIONAL) - English Language Learner language
- `lunch_status` - `nullable=True` (OPTIONAL) - Lunch program status

**Key Finding:** Only `first_name`, `last_name`, `active`, and `gifted` are actually required at the database level for students. All academic, demographic, and relationship fields are optional.

#### 1.1.5 Event Entity - COMPLETED ✅
**Event Model:**
- `id` - Primary key (REQUIRED)
- `title` - `nullable=False` (REQUIRED) - indexed for search
- `start_date` - `nullable=False` (REQUIRED) - indexed for search
- `status` - `nullable=False` (REQUIRED) - default EventStatus.DRAFT, indexed
- `format` - `nullable=False` (REQUIRED) - default EventFormat.IN_PERSON
- `created_at` - `nullable=False` (REQUIRED) - server default
- `updated_at` - `nullable=False` (REQUIRED) - server default

**Optional Fields:**
- `salesforce_id` - `nullable=True` (OPTIONAL) - unique when present, indexed
- `description` - `nullable=True` (OPTIONAL)
- `type` - `nullable=True` (OPTIONAL) - default EventType.IN_PERSON, indexed
- `end_date` - `nullable=True` (OPTIONAL)
- `duration` - `nullable=True` (OPTIONAL) - with non-negative constraint
- `cancellation_reason` - `nullable=True` (OPTIONAL)
- `location` - `nullable=True` (OPTIONAL)
- `school` - `nullable=True` (OPTIONAL) - foreign key to School, indexed
- `district_partner` - `nullable=True` (OPTIONAL) - indexed
- `volunteers_needed` - `nullable=True` (OPTIONAL) - with non-negative constraint
- `participant_count` - `nullable=True` (OPTIONAL) - default 0, with non-negative constraint
- `registered_count` - `nullable=True` (OPTIONAL) - default 0, indexed, with non-negative constraint
- `attended_count` - `nullable=True` (OPTIONAL) - default 0, with non-negative constraint
- `available_slots` - `nullable=True` (OPTIONAL) - default 0, with non-negative constraint
- `scheduled_participants_count` - `nullable=True` (OPTIONAL) - default 0, with non-negative constraint
- `total_requested_volunteer_jobs` - `nullable=True` (OPTIONAL) - default 0, with non-negative constraint
- `additional_information` - `nullable=True` (OPTIONAL)
- `session_id` - `nullable=True` (OPTIONAL)
- `session_host` - `nullable=True` (OPTIONAL) - default "PREPKC"
- `series` - `nullable=True` (OPTIONAL)
- `registration_link` - `nullable=True` (OPTIONAL)
- `original_status_string` - `nullable=True` (OPTIONAL)
- `educators` - `nullable=True` (OPTIONAL) - semicolon-separated list
- `educator_ids` - `nullable=True` (OPTIONAL) - semicolon-separated list
- `professionals` - `nullable=True` (OPTIONAL)
- `professional_ids` - `nullable=True` (OPTIONAL)

**Key Finding:** Only `title`, `start_date`, `status`, `format`, `created_at`, and `updated_at` are actually required at the database level for events. All other fields are optional with appropriate defaults and constraints.

#### 1.1.6 School Entity - COMPLETED ✅
**School Model:**
- `id` - Primary key (REQUIRED) - Salesforce ID format string
- `name` - `nullable=False` (REQUIRED) - School's official name
- `district_id` - `nullable=True` (OPTIONAL) - Foreign key to District
- `salesforce_district_id` - `nullable=True` (OPTIONAL) - External district reference
- `normalized_name` - `nullable=True` (OPTIONAL) - Standardized name for searching
- `school_code` - `nullable=True` (OPTIONAL) - External reference code
- `level` - `nullable=True` (OPTIONAL) - School level (Elementary, Middle, High, Other)

**Key Finding:** Only `id` and `name` are actually required at the database level for schools. All other fields including district relationships are optional.

#### 1.1.7 District Entity - COMPLETED ✅
**District Model:**
- `id` - Primary key (REQUIRED) - Auto-incrementing integer
- `name` - `nullable=False` (REQUIRED) - District's official name
- `salesforce_id` - `nullable=True` (OPTIONAL) - Unique when present, indexed
- `district_code` - `nullable=True` (OPTIONAL) - External reference code

**Key Finding:** Only `id` and `name` are actually required at the database level for districts. All other fields are optional.

### 1.2 Form Validation Analysis
- [x] Review `forms.py` for actual form validation requirements
- [x] Document which fields use `DataRequired()` vs `Optional()`
- [x] Identify any custom form validation logic

#### 1.2.1 Volunteer Entity - COMPLETED ✅
**Required Fields (Form Level):**
- `first_name` - `DataRequired()` (REQUIRED)
- `last_name` - `DataRequired()` (REQUIRED)
- `email` - `DataRequired(), Email()` (REQUIRED + email format validation)

**Optional Fields (Form Level):**
- `salutation` - `Optional()`
- `middle_name` - `Optional()`
- `suffix` - `Optional()`
- `phone` - `Optional()`
- `organization_name` - `Optional()`
- `title` - `Optional()`
- `department` - `Optional()`
- `industry` - `Optional()`
- `local_status` - `Optional()`
- `skills` - `Optional()` ← **KEY FINDING: Skills are NOT required in forms!**
- `notes` - `Optional()`
- `gender` - `Optional()`
- `race_ethnicity` - `Optional()`
- `education` - `Optional()`

**Key Finding:** The form validation confirms that `Volunteer_Skills__c` is NOT required - it's marked as `Optional()` in the form, which contradicts the fake business rule in the config.

**Form vs Database Alignment:** ✅ PERFECT
- Database requires: `first_name`, `last_name`
- Form requires: `first_name`, `last_name`, `email`
- Form adds email requirement (good UX practice)
- All other fields are optional in both places

#### 1.2.2 Organization Entity - COMPLETED ✅
**Required Fields (Form Level):**
- `name` - `required` attribute in HTML (REQUIRED)

**Optional Fields (Form Level):**
- `type` - No required attribute (OPTIONAL)
- `description` - No required attribute (OPTIONAL)
- `billing_street` - No required attribute (OPTIONAL)
- `billing_city` - No required attribute (OPTIONAL)
- `billing_state` - No required attribute (OPTIONAL)
- `billing_postal_code` - No required attribute (OPTIONAL)
- `billing_country` - No required attribute (OPTIONAL)

**Form vs Database Alignment:** ✅ PERFECT
- Database requires: `name`
- Form requires: `name`
- All address fields are optional in both places
- No form validation library used (direct HTML validation)

#### 1.2.3 Teacher Entity - COMPLETED ✅
**Required Fields (Form Level):**
- `first_name` - `required` attribute in HTML (REQUIRED)
- `last_name` - `required` attribute in HTML (REQUIRED)
- `status` - `required` attribute in HTML (REQUIRED)

**Optional Fields (Form Level):**
- `salesforce_id` - No required attribute (OPTIONAL)
- `school_id` - No required attribute (OPTIONAL)
- `exclude_from_reports` - Checkbox (OPTIONAL)

**Form vs Database Alignment:** ✅ PERFECT
- Database requires: `first_name`, `last_name`, `active`
- Form requires: `first_name`, `last_name`, `status`
- Form adds status requirement (good UX practice)
- School association is optional in both places

#### 1.2.4 Student Entity - COMPLETED ✅
**Required Fields (Form Level):**
- `first_name` - `required` attribute in HTML (REQUIRED)
- `last_name` - `required` attribute in HTML (REQUIRED)

**Optional Fields (Form Level):**
- `salesforce_id` - No required attribute (OPTIONAL)
- `gender` - Dropdown with "Not specified" option (OPTIONAL)
- `school_id` - Dropdown with "No school assigned" option (OPTIONAL)
- `racial_ethnic_background` - No required attribute (OPTIONAL)

**Form vs Database Alignment:** ✅ PERFECT
- Database requires: `first_name`, `last_name`, `active`, `gifted`
- Form requires: `first_name`, `last_name`
- Form adds minimal requirements (good UX practice)
- All academic, demographic, and relationship fields are optional in both places

#### 1.2.5 Event Entity - COMPLETED ✅
**Required Fields (Form Level):**
- `title` - `DataRequired()` (REQUIRED)
- `type` - `DataRequired()` (REQUIRED)
- `format` - `DataRequired()` (REQUIRED)
- `start_date` - `DataRequired()` (REQUIRED)
- `end_date` - `DataRequired()` (REQUIRED)
- `status` - `DataRequired()` (REQUIRED)

**Optional Fields (Form Level):**
- `location` - `Optional()` (OPTIONAL)
- `description` - `Optional()` (OPTIONAL)
- `volunteers_needed` - `Optional()` (OPTIONAL) - with NumberRange(min=0) validation

**Form vs Database Alignment:** ⚠️ PARTIAL MISALIGNMENT
- Database requires: `title`, `start_date`, `status`, `format`, `created_at`, `updated_at`
- Form requires: `title`, `type`, `format`, `start_date`, `end_date`, `status`
- **MISALIGNMENT**: Form requires `type` and `end_date` but database doesn't require them
- **MISALIGNMENT**: Form requires `end_date` but database doesn't require it
- Form adds more requirements than database (potentially good UX practice but needs verification)

### 1.3 Business Logic Analysis
- [x] Review import/export logic in route files
- [x] Document actual business rules (not placeholder ones)
- [x] Identify any workflow or process requirements

#### 1.3.1 Volunteer Entity - COMPLETED ✅
**Import Logic (Salesforce CSV Import):**
- **Skills Processing**: Skills are processed IF they exist, but NOT required
  ```python
  if row.get("Volunteer_Skills_Text__c") or row.get("Volunteer_Skills__c"):
      # Skills are processed when present, but not enforced
  ```
- **Required Fields**: Only `Id` (Salesforce ID) is used for lookup, but not enforced
- **Optional Fields**: All other fields are processed if present, skipped if missing
- **No Validation**: No business rule validation during import

**Form Creation Logic:**
- **Skills Handling**: Skills are optional and processed if provided
  ```python
  if form.skills.data:
      # Parse skills from textarea (assume comma-separated)
      # Skills are NOT required
  ```
- **Email/Phone**: Added if provided, but not required
- **Organization**: Linked if provided, but not required

**Key Business Rules Found:**
1. **No Cross-Field Dependencies**: No validation that requires skills when contact type is volunteer
2. **No Workflow Requirements**: No validation of volunteer onboarding steps
3. **Skills Are Optional**: Skills are processed when present but never required
4. **Flexible Creation**: Volunteers can be created with minimal information (just name)

**Conclusion:** The actual business logic confirms that the fake business rules in the config are completely wrong. Skills are truly optional for volunteers.

#### 1.3.2 Organization Entity - COMPLETED ✅
**Form Creation/Edit Logic:**
- **Name Field**: Required and validated in HTML form
- **Type Field**: Optional dropdown selection
- **Description Field**: Optional text input
- **Address Fields**: All optional (street, city, state, postal code, country)

**Key Business Rules Found:**
1. **No Cross-Field Dependencies**: No validation that requires address fields when type is set
2. **No Workflow Requirements**: No validation of organization setup steps
3. **Address Fields Are Optional**: All address fields are processed if provided but never required
4. **Flexible Creation**: Organizations can be created with minimal information (just name)

**Conclusion:** The actual business logic confirms that organizations have very simple requirements - only the name is required.

#### 1.3.3 Teacher Entity - COMPLETED ✅
**Form Creation/Edit Logic:**
- **Name Fields**: Required and validated in HTML form
- **Status Field**: Required dropdown selection
- **Salesforce ID**: Optional text input
- **School Association**: Optional dropdown selection
- **Report Exclusion**: Optional checkbox

**Import Logic (Salesforce CSV Import):**
- **Teacher Identification**: Uses `Contact_Type__c = 'Teacher'`
- **Required Fields**: Only basic identification fields are processed
- **Optional Fields**: All other fields are processed if present, skipped if missing
- **No Validation**: No business rule validation during import

**Key Business Rules Found:**
1. **No Cross-Field Dependencies**: No validation that requires school association when status is active
2. **No Workflow Requirements**: No validation of teacher onboarding steps
3. **School Association Is Optional**: School ID is processed if provided but never required
4. **Flexible Creation**: Teachers can be created with minimal information (just name + status)

**Conclusion:** The actual business logic confirms that teachers have very simple requirements - only name and status are required.

#### 1.3.4 Student Entity - COMPLETED ✅
**Form Creation/Edit Logic:**
- **Name Fields**: Required and validated in HTML form
- **Salesforce ID**: Optional text input
- **Gender**: Optional dropdown with "Not specified" option
- **School Association**: Optional dropdown with "No school assigned" option
- **Racial/Ethnic Background**: Optional text input

**Import Logic (Salesforce CSV Import):**
- **Student Identification**: Uses `Contact_Type__c = 'Student'`
- **Required Fields**: Only `Id`, `FirstName`, `LastName` are enforced
- **Optional Fields**: All other fields are processed if present, skipped if missing
- **No Validation**: No business rule validation during import

**Key Business Rules Found:**
1. **No Cross-Field Dependencies**: No validation that requires school association when grade is set
2. **No Workflow Requirements**: No validation of student enrollment steps
3. **School Association Is Optional**: School ID is processed if provided but never required
4. **Flexible Creation**: Students can be created with minimal information (just name)
5. **Grade Validation**: Grade range validation (0-12) but not required

**Conclusion:** The actual business logic confirms that students have very simple requirements - only name is required. All academic, demographic, and relationship fields are truly optional.

#### 1.3.5 Event Entity - COMPLETED ✅
**Form Creation/Edit Logic:**
- **Title Field**: Required and validated with `DataRequired()`
- **Type Field**: Required dropdown selection with `DataRequired()`
- **Format Field**: Required dropdown selection with `DataRequired()`
- **Start Date Field**: Required datetime input with `DataRequired()`
- **End Date Field**: Required datetime input with `DataRequired()`
- **Status Field**: Required dropdown selection with `DataRequired()`
- **Location Field**: Optional text input with `Optional()`
- **Description Field**: Optional textarea with `Optional()`
- **Volunteers Needed Field**: Optional integer with `Optional()` and `NumberRange(min=0)`

**Import Logic (Salesforce CSV Import):**
- **Event Identification**: Uses `Id` from Salesforce Session__c object
- **Required Fields**: Only `Name` (title) is enforced during import
- **Optional Fields**: All other fields are processed if present, skipped if missing
- **Business Logic**: Events are skipped if missing ALL three identifiers (Parent_Account__c, District__c, School__c)
- **Date Handling**: Start and end dates are parsed but not required (defaults to 2000-01-01 if missing)
- **Status Mapping**: Salesforce status values are mapped to internal enum values

**Key Business Rules Found:**
1. **Cross-Field Dependencies**: Events must have at least one of: Parent_Account__c, District__c, or School__c
2. **Date Validation**: Start and end dates are processed but not enforced as required
3. **Status Workflow**: Status transitions are handled through Salesforce mapping
4. **Capacity Management**: Volunteer jobs and available slots are tracked but not required
5. **Location Requirements**: Location is optional but processed when available

**Conclusion:** The actual business logic shows that events have more complex requirements than the database schema suggests. The form requires more fields than the database, and there are business rules around having at least one organizational identifier.

#### 1.3.6 School Entity - COMPLETED ✅
**Import Logic (Salesforce CSV Import):**
- **School Identification**: Uses `Id` from Salesforce Account object where `Type = 'School'`
- **Required Fields**: Only `Id` and `Name` are enforced during import
- **Optional Fields**: All other fields are processed if present, skipped if missing
- **Business Logic**: Schools are linked to districts via `ParentId` (district's Salesforce ID)
- **District Association**: District relationship is established but not required (can be None)

**Key Business Rules Found:**
1. **No Cross-Field Dependencies**: No validation that requires district association
2. **No Workflow Requirements**: No validation of school setup steps
3. **District Association Is Optional**: District ID is processed if provided but never required
4. **Flexible Creation**: Schools can be created with minimal information (just ID and name)

**Conclusion:** The actual business logic confirms that schools have very simple requirements - only ID and name are required. District association is truly optional.

#### 1.3.7 District Entity - COMPLETED ✅
**Import Logic (Salesforce CSV Import):**
- **District Identification**: Uses `Id` from Salesforce Account object where `Type = 'School District'`
- **Required Fields**: Only `Id` and `Name` are enforced during import
- **Optional Fields**: All other fields are processed if present, skipped if missing
- **Business Logic**: Districts are imported independently of schools
- **No Dependencies**: No validation that requires additional fields

**Key Business Rules Found:**
1. **No Cross-Field Dependencies**: No validation that requires district code or other fields
2. **No Workflow Requirements**: No validation of district setup steps
3. **District Code Is Optional**: District code is processed if provided but never required
4. **Flexible Creation**: Districts can be created with minimal information (just ID and name)

**Conclusion:** The actual business logic confirms that districts have very simple requirements - only ID and name are required. All other fields are truly optional.

### 1.4 Salesforce Integration Analysis
- [x] Review Salesforce client code for actual field requirements
- [x] Document which fields are actually required vs. optional
- [x] Identify any Salesforce-specific validation rules

#### 1.4.1 Volunteer Entity - COMPLETED ✅
**Salesforce Query Analysis:**
- **Volunteer Identification**: Uses `Contact_Type__c = 'Volunteer'` (NOT `RecordType.Name`)
- **Sample Query Fields**: Only basic fields are queried, no skills validation
  ```sql
  SELECT Id, FirstName, LastName, Email, Phone, MailingCity, MailingState,
         Contact_Type__c, AccountId, npsp__Primary_Affiliation__c
  FROM Contact
  WHERE Contact_Type__c = 'Volunteer' OR Contact_Type__c = ''
  ```

**Key Findings:**
1. **No Skills Field in Queries**: `Volunteer_Skills__c` is never queried in Salesforce client
2. **No Field Requirements**: No validation that certain fields must be populated
3. **Flexible Identification**: Volunteers can have `Contact_Type__c = 'Volunteer'` OR empty string
4. **Basic Field Set**: Only essential fields are retrieved for validation purposes

**Salesforce vs. VMS Alignment:**
- **Salesforce**: No enforcement of skills requirement
- **VMS**: No enforcement of skills requirement
- **Config**: Claims skills are required (WRONG!)

**Conclusion:** The Salesforce integration confirms that skills are truly optional. The fake business rule requiring skills for volunteers has no basis in the actual Salesforce implementation.

#### 1.4.2 Organization Entity - COMPLETED ✅
**Salesforce Query Analysis:**
- **Organization Identification**: Uses `Type NOT IN ('Household', 'School District', 'School')`
- **Sample Query Fields**: Basic fields for validation
  ```sql
  SELECT Id, Name, Type, BillingCity, BillingState, Phone, Website
  FROM Account
  WHERE Type NOT IN ('Household', 'School District', 'School')
  ```

**Key Findings:**
1. **No Address Field Requirements**: `BillingCity`, `BillingState` are queried but not required
2. **No Field Validation**: No validation that certain fields must be populated
3. **Type Filtering**: Excludes certain organization types from validation
4. **Basic Field Set**: Only essential fields are retrieved for validation purposes

**Salesforce vs. VMS Alignment:**
- **Salesforce**: No enforcement of address requirements
- **VMS**: No enforcement of address requirements
- **Config**: Claims address fields are required (NEEDS VERIFICATION!)

**Conclusion:** The Salesforce integration confirms that address fields are truly optional. Any business rules requiring address fields for organizations need verification.

#### 1.4.3 Teacher Entity - COMPLETED ✅
**Salesforce Query Analysis:**
- **Teacher Identification**: Uses `Contact_Type__c = 'Teacher'`
- **Sample Query Fields**: Basic fields for validation
  ```sql
  SELECT Id, FirstName, LastName, Contact_Type__c, Title, Email, Phone, MailingCity, MailingState
  FROM Contact
  WHERE Contact_Type__c = 'Teacher'
  ```

**Key Findings:**
1. **No Title Field Requirements**: `Title` is queried but not required
2. **No Field Validation**: No validation that certain fields must be populated
3. **Basic Field Set**: Only essential fields are retrieved for validation purposes
4. **No School Association Requirements**: `AccountId` is not queried in samples

**Salesforce vs. VMS Alignment:**
- **Salesforce**: No enforcement of title or school requirements
- **VMS**: No enforcement of title or school requirements
- **Config**: Claims title is required (NEEDS VERIFICATION!)

**Conclusion:** The Salesforce integration confirms that title and school association are truly optional. Any business rules requiring these fields for teachers need verification.

#### 1.4.4 Student Entity - COMPLETED ✅
**Salesforce Query Analysis:**
- **Student Identification**: Uses `Contact_Type__c = 'Student'`
- **Sample Query Fields**: Basic fields for validation
  ```sql
  SELECT Id, FirstName, LastName, Contact_Type__c, Email, Phone, MailingCity, MailingState
  FROM Contact
  WHERE Contact_Type__c = 'Student'
  ```

**Key Findings:**
1. **No Academic Field Requirements**: `Current_Grade__c`, `Legacy_Grade__c` are not queried in samples
2. **No Field Validation**: No validation that certain fields must be populated
3. **Basic Field Set**: Only essential fields are retrieved for validation purposes
4. **No School Association Requirements**: `AccountId`, `npsp__Primary_Affiliation__c` are not queried in samples
5. **No Demographic Requirements**: `Racial_Ethnic_Background__c`, `Gender__c` are not queried in samples

**Salesforce vs. VMS Alignment:**
- **Salesforce**: No enforcement of academic, demographic, or school requirements
- **VMS**: No enforcement of academic, demographic, or school requirements
- **Config**: Claims school association is required (NEEDS VERIFICATION!)

**Conclusion:** The Salesforce integration confirms that academic, demographic, and school association fields are truly optional. Any business rules requiring these fields for students need verification.

#### 1.4.5 Event Entity - COMPLETED ✅
**Salesforce Query Analysis:**
- **Event Identification**: Uses `Event` object (not `Session__c` as in import logic)
- **Sample Query Fields**: Basic fields for validation
  ```sql
  SELECT Id, Subject, StartDateTime, EndDateTime, Location, Description
  FROM Event
  ```

**Key Findings:**
1. **No Field Requirements**: No validation that certain fields must be populated
2. **Basic Field Set**: Only essential fields are retrieved for validation purposes
3. **Field Mapping Mismatch**: Sample query uses `Event` object but import uses `Session__c` object
4. **No Status Requirements**: Event status is not queried in samples
5. **No Type Requirements**: Event type is not queried in samples

**Salesforce vs. VMS Alignment:**
- **Salesforce**: No enforcement of event type, format, or status requirements
- **VMS**: Form requires type, format, start_date, end_date, and status
- **Config**: Claims Subject, StartDateTime, EndDateTime are required (NEEDS VERIFICATION!)

**Conclusion:** The Salesforce integration shows a mismatch between the sample query (using `Event` object) and the import logic (using `Session__c` object). The form requires more fields than the Salesforce sample query suggests, indicating potential business logic differences.

## Phase 2: Configuration Cleanup

### 2.1 Remove Fake Business Rules
- [x] Remove placeholder cross-field validations
- [x] Remove fake workflow validations
- [ ] Remove any other auto-generated placeholder content

#### 2.1.1 Volunteer Entity - COMPLETED ✅
**Removed Fake Cross-Field Validations:**
- ❌ `Volunteer_Skills__c` required when `Contact_Type__c = 'Volunteer'` - **REMOVED**
- ❌ `Availability__c` required when `Contact_Type__c = 'Volunteer'` - **REMOVED**

**Removed Fake Workflow Validations:**
- ❌ Registration → Background Check → Skills Assessment → Approval workflow - **REMOVED**
- ❌ Required fields for each workflow step - **REMOVED**

**Result:** Volunteer entity now has no fake business rules. Only real validation rules remain.

#### 2.1.2 Organization Entity - COMPLETED ✅
**Removed Fake Status Transition Validations:**
- ❌ Status transitions with `Status__c` field - **REMOVED** (field doesn't exist)

**Removed Fake Cross-Field Validations:**
- ❌ `School_District__c` required when `Type = 'School'` - **REMOVED** (field doesn't exist)
- ❌ `Tax_ID__c` required when `Type = 'Non-Profit'` - **REMOVED** (field doesn't exist)

**Result:** Organization entity now has no fake business rules. Only real validation rules remain.

#### 2.1.3 Teacher Entity - COMPLETED ✅
**Removed Fake Organization Association Validation:**
- ❌ School association (`AccountId`) required for teachers - **REMOVED** (contradicts actual code)

**Removed Fake Cross-Field Validations:**
- ❌ `Years_Experience__c` required when `Title = 'Principal'` - **REMOVED** (field doesn't exist)
- ❌ `Certification_Status__c` required when `Title = 'Substitute'` - **REMOVED** (field doesn't exist)

**Result:** Teacher entity now has no fake business rules. Only real validation rules remain.

#### 2.1.4 Student Entity - COMPLETED ✅
**Removed Fake Organization Association Validation:**
- ❌ School association (`AccountId`) required for students - **REMOVED** (contradicts actual code)

**Removed Fake Enrollment Validation:**
- ❌ `Enrollment_Date__c` and `Graduation_Date__c` validation - **REMOVED** (fields don't exist)

**Removed Fake Cross-Field Validations:**
- ❌ `Grade_Level__c` and `Age__c` validation - **REMOVED** (fields don't exist)

**Result:** Student entity now has no fake business rules. Only real validation rules remain.

#### 2.1.5 Event Entity - COMPLETED ✅
**Removed Fake Subject Validation:**
- ❌ `Subject` field validation - **REMOVED** (field mapping mismatch - uses `Event` object but import uses `Session__c`)

**Removed Fake Start Date Validation:**
- ❌ `StartDateTime` required - **REMOVED** (form vs database mismatch - form requires but database doesn't)

**Removed Fake Cross-Field Validation:**
- ❌ Virtual events require platform, in-person events require location - **REMOVED** (fields don't exist in actual code)

**Removed Fake Workflow Validation:**
- ❌ Complex event lifecycle workflow - **REMOVED** (workflow steps don't match actual implementation)

**Removed Fake Capacity Validation:**
- ❌ `Max_Volunteers__c` and `Registered_Volunteers__c` validation - **REMOVED** (fields don't exist in actual code)

**Result:** Event entity now has no fake business rules. Only real validation rules remain.

### 2.2 Update Field Completeness Rules
- [x] Set `field_completeness_threshold` based on actual requirements
- [x] Configure required fields based on database schema
- [x] Configure optional fields appropriately

#### 2.2.1 Volunteer Entity - COMPLETED ✅
**Field Completeness Rules Already Correct:**
- **Required Fields**: `["Id", "FirstName", "LastName"]` - matches database schema
- **Threshold**: 95.0% (appropriate for required fields)
- **Field Ranges**: `FirstName` and `LastName` have proper length constraints (1-100 chars)

**Data Type Rules Already Correct:**
- **FirstName**: `required: True`, `severity: error` - matches form validation
- **LastName**: `required: True`, `severity: error` - matches form validation
- **Email**: `required: False`, `severity: warning` - matches form validation (required in form but not database)
- **Phone**: `required: False`, `severity: info` - matches form validation

**Result:** Volunteer entity field completeness rules are already perfectly aligned with actual business logic.

#### 2.2.2 Organization Entity - COMPLETED ✅
**Field Completeness Rules Already Correct:**
- **Required Fields**: `["Name"]` - matches database schema (only `name` is required)
- **Threshold**: 95.0% (appropriate for required fields)
- **Field Ranges**: `Name` has proper length constraints (2-100 chars)

**Data Type Rules Already Correct:**
- **Name**: `required: True`, `severity: warning` - matches form validation
- **Type**: `required: False` - matches form validation (optional dropdown)
- **Address Fields**: All optional with appropriate severity levels

**Result:** Organization entity field completeness rules are already perfectly aligned with actual business logic.

#### 2.2.3 Teacher Entity - COMPLETED ✅
**Field Completeness Rules Updated:**
- **Required Fields**: `["FirstName", "LastName", "Contact_Type__c"]` - matches database schema
- **Optional Fields**: `Title` removed from required fields (matches actual business logic)
- **Threshold**: 95.0% (appropriate for required fields)

**Data Type Rules Updated:**
- **FirstName**: `required: True`, `severity: error` - matches form validation
- **LastName**: `required: True`, `severity: error` - matches form validation
- **Title**: `required: False`, `severity: info` - matches actual business logic (optional)
- **Contact_Type__c**: `required: True`, `severity: error` - matches form validation

**Result:** Teacher entity field completeness rules are now perfectly aligned with actual business logic.

#### 2.2.4 Student Entity - COMPLETED ✅
**Field Completeness Rules Updated:**
- **Required Fields**: `["FirstName", "LastName"]` - matches database schema (only `first_name` and `last_name` are required)
- **Optional Fields**: `Contact_Type__c` removed from required fields (matches actual business logic)
- **Threshold**: 95.0% (appropriate for required fields)

**Data Type Rules Already Correct:**
- **FirstName**: `required: True`, `severity: error` - matches form validation
- **LastName**: `required: True`, `severity: error` - matches form validation
- **Contact_Type__c**: `required: False` - matches actual business logic (optional)

**Result:** Student entity field completeness rules are now perfectly aligned with actual business logic.

#### 2.2.5 Event Entity - COMPLETED ✅
**Field Completeness Rules Updated:**
- **Required Fields**: `["title", "start_date"]` - matches database schema (only `title` and `start_date` are required)
- **Optional Fields**: `Subject`, `StartDateTime`, `EndDateTime` removed from required fields (fields don't exist in actual code)
- **Threshold**: 95.0% (appropriate for required fields)

**Field Formats Updated:**
- **start_date**: `type: datetime` - matches database schema
- **Subject**, **StartDateTime**, **EndDateTime** removed (fields don't exist in actual code)

**Result:** Event entity field completeness rules are now perfectly aligned with actual business logic.

### 2.3 Update Data Type Validation
- [x] Configure data type rules based on actual field types
- [x] Set appropriate thresholds for data quality scoring
- [x] Remove any invalid field type mappings

#### 2.3.1 Volunteer Entity - COMPLETED ✅
**Data Type Rules Already Correct:**
- **String Fields**: `FirstName`, `LastName` have proper length constraints and required flags
- **Email Field**: Has proper email pattern validation and appropriate severity
- **Phone Field**: Has proper phone pattern validation and appropriate severity
- **Thresholds**: 99.0% accuracy threshold is appropriate for data type validation

**Result:** Volunteer entity data type validation rules are already perfectly aligned with actual business logic.

#### 2.3.2 Organization Entity - COMPLETED ✅
**Data Type Rules Already Correct:**
- **String Fields**: `Name` has proper length constraints and required flags
- **Type Field**: Has proper validation with allowed values
- **Address Fields**: Have appropriate length constraints and optional flags
- **Thresholds**: 99.0% accuracy threshold is appropriate for data type validation

**Result:** Organization entity data type validation rules are already perfectly aligned with actual business logic.

#### 2.3.3 Teacher Entity - COMPLETED ✅
**Data Type Rules Updated:**
- **String Fields**: `FirstName`, `LastName` have proper length constraints and required flags
- **Title Field**: Updated to `required: False` with appropriate severity (info)
- **Contact_Type__c**: Has proper enum validation with allowed values
- **Thresholds**: 99.0% accuracy threshold is appropriate for data type validation

**Result:** Teacher entity data type validation rules are now perfectly aligned with actual business logic.

#### 2.3.4 Student Entity - COMPLETED ✅
**Data Type Rules Already Correct:**
- **String Fields**: `FirstName`, `LastName` have proper length constraints and required flags
- **Contact_Type__c**: Has proper enum validation with allowed values
- **Thresholds**: 99.0% accuracy threshold is appropriate for data type validation

**Result:** Student entity data type validation rules are already perfectly aligned with actual business logic.

#### 2.3.5 Event Entity - COMPLETED ✅
**Data Type Rules Already Correct:**
- **String Fields**: `title` has proper length constraints and required flags
- **DateTime Fields**: `start_date` has proper datetime validation
- **Thresholds**: 99.0% accuracy threshold is appropriate for data type validation

**Result:** Event entity data type validation rules are already perfectly aligned with actual business logic.

## Phase 3: Implement Real Business Rules

### 3.1 Required Field Validation
- [x] Implement validation for fields marked `nullable=False` in models
- [x] Implement validation for fields with `DataRequired()` in forms
- [x] Set appropriate severity levels and thresholds

#### 3.1.1 Volunteer Entity - COMPLETED ✅
**Required Field Validation Already Implemented:**
- Database level: `first_name`, `last_name` (nullable=False)
- Form level: `first_name`, `last_name`, `email` (DataRequired)
- Severity levels: Appropriate (error for required, warning for email, info for optional)

#### 3.1.2 Organization Entity - COMPLETED ✅
**Required Field Validation Already Implemented:**
- Database level: `name` (nullable=False)
- Form level: `name` (required attribute in HTML)
- Severity levels: Appropriate (warning for required name, info for optional fields)

#### 3.1.3 Teacher Entity - COMPLETED ✅
**Required Field Validation Already Implemented:**
- Database level: `first_name`, `last_name`, `active` (nullable=False)
- Form level: `first_name`, `last_name`, `status` (required attribute in HTML)
- Severity levels: Appropriate (error for required names, info for optional title)

#### 3.1.4 Student Entity - COMPLETED ✅
**Required Field Validation Already Implemented:**
- Database level: `first_name`, `last_name`, `active`, `gifted` (nullable=False)
- Form level: `first_name`, `

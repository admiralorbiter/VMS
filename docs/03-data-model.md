---
title: "VMS Data Model"
description: "Complete database schema, relationships, and data structures for the Volunteer Management System"
tags: [data-model, database, schema, relationships]
---

# VMS Data Model

## 🗄️ Database Schema Overview

The VMS system uses SQLite as the primary database with a relational schema designed to support volunteer management, event tracking, and comprehensive reporting. The data model follows normalization principles while maintaining performance for complex queries.

**Key Design Pattern**: The system uses **polymorphic inheritance** where `Contact` is the base class, and `Volunteer`, `Teacher`, and `Student` inherit from it. This allows for shared contact information while maintaining specialized data for each type.

## 📊 Entity Relationship Diagram

```mermaid
erDiagram
    CONTACT {
        int id PK
        string type
        string salesforce_individual_id UK
        string salesforce_account_id
        string first_name
        string last_name
        string middle_name
        enum salutation
        enum suffix
        enum age_group
        enum education_level
        date birthdate
        enum gender
        enum race_ethnicity
        boolean do_not_call
        boolean do_not_contact
        boolean email_opt_out
        datetime email_bounced_date
        boolean exclude_from_reports
        date last_email_date
        text notes
        datetime created_at
        datetime updated_at
    }

    VOLUNTEER {
        int id FK
        string organization_name
        string title
        string department
        string industry
        enum education
        enum local_status
        datetime local_status_last_updated
        boolean is_people_of_color
        date first_volunteer_date
        date last_volunteer_date
        date last_non_internal_email_date
        date last_activity_date
        int times_volunteered
        int additional_volunteer_count
        date last_mailchimp_activity_date
        text mailchimp_history
        string admin_contacts
        text interests
        enum status
    }

    TEACHER {
        int id FK
        string school_id FK
        string subject_area
        string grade_level
        string department
        string title
        boolean is_active
        date last_activity_date
    }

    STUDENT {
        int id FK
        string school_id FK
        string grade_level
        string student_id
        date enrollment_date
        boolean is_active
        date last_activity_date
    }

    CONNECTOR_DATA {
        int id PK
        int volunteer_id FK
        enum active_subscription
        string active_subscription_name
        string role
        string signup_role
        string profile_link
        text affiliations
        string industry
        string user_auth_id UK
        string joining_date
        string last_login_datetime
        date last_update_date
        datetime created_at
        datetime updated_at
    }

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string first_name
        string last_name
        int security_level
        string api_token UK
        datetime token_expiry
        datetime created_at
        datetime updated_at
    }

    ORGANIZATION {
        int id PK
        string salesforce_id UK
        string name
        string type
        text address
        string city
        string state
        string postal_code
        string country
        datetime created_at
        datetime updated_at
    }

    EVENT {
        int id PK
        string salesforce_id UK
        string title
        text description
        enum type
        enum format
        datetime start_date
        datetime end_date
        int duration
        enum status
        enum cancellation_reason
        string location
        string school FK
        string district_partner
        int volunteers_needed
        int participant_count
        int registered_count
        int attended_count
        int available_slots
        int scheduled_participants_count
        int total_requested_volunteer_jobs
        text additional_information
        string session_id
        string session_host
        string series
        string registration_link
        string original_status_string
        text educators
        text educator_ids
        text professionals
        text professional_ids
        datetime created_at
        datetime updated_at
    }

    EVENT_ATTENDANCE_DETAIL {
        int id PK
        int event_id FK
        enum status
        datetime last_taken
        int total_attendance
        datetime created_at
        datetime updated_at
    }

    EVENT_TEACHER {
        int event_id FK
        int teacher_id FK
        string status
        boolean is_simulcast
        datetime attendance_confirmed_at
        text notes
        datetime created_at
        datetime updated_at
    }

    EVENT_STUDENT_PARTICIPATION {
        int id PK
        string salesforce_id UK
        int event_id FK
        int student_id FK
        string status
        float delivery_hours
        string age_group
        datetime created_at
        datetime updated_at
    }

    SKILL {
        int id PK
        string name UK
    }

    VOLUNTEER_SKILLS {
        int volunteer_id FK
        int skill_id FK
        enum source
        string interest_level
    }

    ENGAGEMENT {
        int id PK
        int volunteer_id FK
        date engagement_date
        string engagement_type
        text notes
    }

    EVENT_PARTICIPATION {
        int id PK
        int volunteer_id FK
        int event_id FK
        string status
        float delivery_hours
        string salesforce_id UK
        string age_group
        string email
        string title
        string participant_type
        string contact
    }

    SCHOOL {
        int id PK
        string name
        string district FK
        string address
        string city
        string state
        string zip_code
        string phone
        string website
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    DISTRICT {
        int id PK
        string name
        string salesforce_id UK
        string address
        string city
        string state
        string zip_code
        string phone
        string website
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    CLASS {
        int id PK
        string name
        int school_id FK
        string grade_level
        string subject_area
        string teacher_name
        int student_count
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    CLIENT_PROJECTS {
        int id PK
        string name
        string description
        string client_name
        string status
        date start_date
        date end_date
        string google_sheet_id
        datetime created_at
        datetime updated_at
    }

    PATHWAY {
        int id PK
        string name
        string description
        string salesforce_id UK
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    BUG_REPORTS {
        int id PK
        string type
        text description
        string status
        int reported_by FK
        datetime created_at
        datetime resolved_at
    }

    GOOGLE_SHEETS {
        int id PK
        string name
        string url
        string type
        datetime created_at
        datetime updated_at
    }

    HISTORY {
        int id PK
        string action
        string table_name
        int record_id
        text old_values
        text new_values
        int user_id FK
        datetime created_at
    }

    PHONE {
        int id PK
        int contact_id FK
        string number
        enum type
        boolean primary
    }

    EMAIL {
        int id PK
        int contact_id FK
        string email
        enum type
        boolean primary
    }

    ADDRESS {
        int id PK
        int contact_id FK
        string address_line1
        string address_line2
        string city
        string state
        string zip_code
        string country
        enum type
        boolean primary
    }

    VOLUNTEER_ORGANIZATION {
        int volunteer_id FK
        int organization_id FK
        string role
        date start_date
        date end_date
        boolean is_primary
    }

    EVENT_VOLUNTEERS {
        int event_id FK
        int volunteer_id FK
        string role
        string status
        datetime registered_at
    }

    EVENT_DISTRICTS {
        int event_id FK
        int district_id FK
    }

    EVENT_SKILLS {
        int event_id FK
        int skill_id FK
    }

    CONTACT ||--o{ PHONE : has
    CONTACT ||--o{ EMAIL : has
    CONTACT ||--o{ ADDRESS : has
    CONTACT ||--o{ HISTORY : tracks

    CONTACT ||--|| VOLUNTEER : is_a
    CONTACT ||--|| TEACHER : is_a
    CONTACT ||--|| STUDENT : is_a

    VOLUNTEER ||--|| CONNECTOR_DATA : has
    VOLUNTEER ||--o{ VOLUNTEER_SKILLS : has
    VOLUNTEER ||--o{ ENGAGEMENT : participates
    VOLUNTEER ||--o{ EVENT_PARTICIPATION : participates
    VOLUNTEER ||--o{ VOLUNTEER_ORGANIZATION : belongs_to

    TEACHER ||--o{ EVENT_TEACHER : participates
    STUDENT ||--o{ EVENT_STUDENT_PARTICIPATION : participates

    SCHOOL ||--o{ TEACHER : employs
    SCHOOL ||--o{ STUDENT : enrolls
    SCHOOL ||--o{ CLASS : contains
    SCHOOL ||--o{ EVENT : hosts

    DISTRICT ||--o{ SCHOOL : contains
    DISTRICT ||--o{ EVENT : sponsors

    ORGANIZATION ||--o{ VOLUNTEER_ORGANIZATION : employs

    EVENT ||--|| EVENT_ATTENDANCE_DETAIL : tracks
    EVENT ||--o{ EVENT_TEACHER : involves
    EVENT ||--o{ EVENT_STUDENT_PARTICIPATION : involves
    EVENT ||--o{ EVENT_VOLUNTEERS : involves
    EVENT ||--o{ EVENT_DISTRICTS : involves
    EVENT ||--o{ EVENT_SKILLS : requires

    SKILL ||--o{ VOLUNTEER_SKILLS : possessed_by
    SKILL ||--o{ EVENT_SKILLS : required_by

    USERS ||--o{ HISTORY : performs
    USERS ||--o{ BUG_REPORTS : reports
```

## 📋 Detailed Table Definitions

### 1. Contact Table (Base Class)

**Purpose**: Base contact information and demographics for all contact types

```sql
CREATE TABLE contact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50),  -- Polymorphic discriminator
    salesforce_individual_id VARCHAR(18) UNIQUE,
    salesforce_account_id VARCHAR(18),
    salutation VARCHAR(20),
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    last_name VARCHAR(50) NOT NULL,
    suffix VARCHAR(20),
    description TEXT,
    age_group VARCHAR(20) DEFAULT 'Unknown',
    education_level VARCHAR(50) DEFAULT 'Unknown',
    birthdate DATE,
    gender VARCHAR(20),
    race_ethnicity VARCHAR(50),
    do_not_call BOOLEAN DEFAULT FALSE,
    do_not_contact BOOLEAN DEFAULT FALSE,
    email_opt_out BOOLEAN DEFAULT FALSE,
    email_bounced_date DATETIME,
    exclude_from_reports BOOLEAN DEFAULT FALSE,
    last_email_date DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- `idx_contact_salesforce_individual_id` on `salesforce_individual_id`
- `idx_contact_type` on `type`
- `idx_contact_name` on `last_name`, `first_name`

### 2. Volunteer Table (Inherits from Contact)

**Purpose**: Volunteer-specific information and activity tracking

```sql
CREATE TABLE volunteer (
    id INTEGER PRIMARY KEY,
    organization_name VARCHAR(100),
    title VARCHAR(50),
    department VARCHAR(50),
    industry VARCHAR(50),
    education VARCHAR(50),
    local_status VARCHAR(20) DEFAULT 'unknown',
    local_status_last_updated DATETIME,
    is_people_of_color BOOLEAN DEFAULT FALSE,
    first_volunteer_date DATE,
    last_volunteer_date DATE,
    last_non_internal_email_date DATE,
    last_activity_date DATE,
    times_volunteered INTEGER DEFAULT 0,
    additional_volunteer_count INTEGER DEFAULT 0,
    last_mailchimp_activity_date DATE,
    mailchimp_history TEXT,
    admin_contacts VARCHAR(200),
    interests TEXT,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (id) REFERENCES contact(id)
);
```

**Indexes**:
- `idx_volunteer_local_status` on `local_status`
- `idx_volunteer_status` on `status`
- `idx_volunteer_last_activity` on `last_activity_date`
- `idx_volunteer_is_people_of_color` on `is_people_of_color`

### 3. Teacher Table (Inherits from Contact)

**Purpose**: Teacher-specific information and school associations

```sql
CREATE TABLE teacher (
    id INTEGER PRIMARY KEY,
    school_id VARCHAR(18),
    subject_area VARCHAR(100),
    grade_level VARCHAR(20),
    department VARCHAR(100),
    title VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_date DATE,
    FOREIGN KEY (id) REFERENCES contact(id)
);
```

### 4. Student Table (Inherits from Contact)

**Purpose**: Student-specific information and enrollment data

```sql
CREATE TABLE student (
    id INTEGER PRIMARY KEY,
    school_id VARCHAR(18),
    grade_level VARCHAR(20),
    student_id VARCHAR(50),
    enrollment_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_date DATE,
    FOREIGN KEY (id) REFERENCES contact(id)
);
```

### 5. Connector Data Table

**Purpose**: Specialized data for connector program volunteers

```sql
CREATE TABLE connector_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    active_subscription VARCHAR(20) DEFAULT '',
    active_subscription_name VARCHAR(255),
    role VARCHAR(20),
    signup_role VARCHAR(20),
    profile_link VARCHAR(1300),
    affiliations TEXT,
    industry VARCHAR(255),
    user_auth_id VARCHAR(7) UNIQUE,
    joining_date VARCHAR(50),
    last_login_datetime VARCHAR(50),
    last_update_date DATE,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id),
    UNIQUE(volunteer_id, user_auth_id)
);
```

### 6. Users Table

**Purpose**: System user authentication and management

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    first_name VARCHAR(64),
    last_name VARCHAR(64),
    security_level INTEGER DEFAULT 0,
    api_token VARCHAR(64) UNIQUE,
    token_expiry DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- `idx_users_username` on `username`
- `idx_users_email` on `email`
- `idx_users_api_token` on `api_token`
- `idx_users_security_level` on `security_level`

### 7. Event Table

**Purpose**: Event management and scheduling

```sql
CREATE TABLE event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salesforce_id VARCHAR(18) UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) DEFAULT 'in_person',
    format VARCHAR(20) NOT NULL DEFAULT 'in_person',
    start_date DATETIME NOT NULL,
    end_date DATETIME,
    duration INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    cancellation_reason VARCHAR(20),
    location VARCHAR(255),
    school VARCHAR(18),
    district_partner VARCHAR(255),
    volunteers_needed INTEGER,
    participant_count INTEGER DEFAULT 0,
    registered_count INTEGER DEFAULT 0,
    attended_count INTEGER DEFAULT 0,
    available_slots INTEGER DEFAULT 0,
    scheduled_participants_count INTEGER DEFAULT 0,
    total_requested_volunteer_jobs INTEGER DEFAULT 0,
    additional_information TEXT,
    session_id VARCHAR(255),
    session_host VARCHAR(255) DEFAULT 'PREPKC',
    series VARCHAR(255),
    registration_link VARCHAR(1300),
    original_status_string VARCHAR(255),
    educators TEXT,
    educator_ids TEXT,
    professionals TEXT,
    professional_ids TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- `idx_event_salesforce_id` on `salesforce_id`
- `idx_event_status_date` on `status`, `start_date`
- `idx_event_status_date_type` on `status`, `start_date`, `type`
- `idx_event_district_partner` on `district_partner`
- `idx_event_school` on `school`
- `idx_event_type` on `type`
- `idx_event_status` on `status`

### 8. Event Attendance Detail Table

**Purpose**: Attendance tracking for events

```sql
CREATE TABLE event_attendance_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'not_taken',
    last_taken DATETIME,
    total_attendance INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES event(id)
);
```

### 9. Event Teacher Association Table

**Purpose**: Many-to-many relationship between events and teachers with attendance tracking

```sql
CREATE TABLE event_teacher (
    event_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'registered',
    is_simulcast BOOLEAN DEFAULT FALSE,
    attendance_confirmed_at DATETIME,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, teacher_id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (teacher_id) REFERENCES teacher(id)
);
```

### 10. Event Student Participation Table

**Purpose**: Student participation tracking in events

```sql
CREATE TABLE event_student_participation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salesforce_id VARCHAR(18) UNIQUE,
    event_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    status VARCHAR(50),
    delivery_hours FLOAT,
    age_group VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (student_id) REFERENCES student(id)
);
```

**Indexes**:
- `idx_event_student_participation_salesforce_id` on `salesforce_id`
- `idx_event_student_participation_event_id` on `event_id`
- `idx_event_student_participation_student_id` on `student_id`

### 11. Skill and Volunteer Skills Tables

**Purpose**: Skill tracking and volunteer-skill associations

```sql
CREATE TABLE skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE volunteer_skills (
    volunteer_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    source VARCHAR(50),
    interest_level VARCHAR(20),
    PRIMARY KEY (volunteer_id, skill_id),
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id),
    FOREIGN KEY (skill_id) REFERENCES skill(id)
);
```

### 12. Engagement Table

**Purpose**: Volunteer engagement activity tracking

```sql
CREATE TABLE engagement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    engagement_date DATE,
    engagement_type VARCHAR(50),
    notes TEXT,
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id)
);
```

### 13. Event Participation Table

**Purpose**: Volunteer participation in specific events

```sql
CREATE TABLE event_participation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    delivery_hours FLOAT,
    salesforce_id VARCHAR(18) UNIQUE,
    age_group VARCHAR(50),
    email VARCHAR(255),
    title VARCHAR(100),
    participant_type VARCHAR(50) DEFAULT 'Volunteer',
    contact VARCHAR(255),
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id),
    FOREIGN KEY (event_id) REFERENCES event(id)
);
```

**Indexes**:
- `idx_event_participation_salesforce_id` on `salesforce_id`
- `idx_event_participation_volunteer_id` on `volunteer_id`
- `idx_event_participation_event_id` on `event_id`

### 14. School Table

**Purpose**: School information and district associations

```sql
CREATE TABLE school (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    district VARCHAR(255),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    phone VARCHAR(20),
    website VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 15. District Table

**Purpose**: District information and organization

```sql
CREATE TABLE district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    salesforce_id VARCHAR(18) UNIQUE,
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    phone VARCHAR(20),
    website VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 16. Organization Table

**Purpose**: Organization information and volunteer associations

```sql
CREATE TABLE organization (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salesforce_id VARCHAR(18) UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 17. Volunteer Organization Association Table

**Purpose**: Many-to-many relationship between volunteers and organizations

```sql
CREATE TABLE volunteer_organization (
    volunteer_id INTEGER NOT NULL,
    organization_id INTEGER NOT NULL,
    role VARCHAR(100),
    start_date DATE,
    end_date DATE,
    is_primary BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (volunteer_id, organization_id),
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id),
    FOREIGN KEY (organization_id) REFERENCES organization(id)
);
```

### 18. Event Association Tables

**Purpose**: Many-to-many relationships for events

```sql
CREATE TABLE event_volunteers (
    event_id INTEGER NOT NULL,
    volunteer_id INTEGER NOT NULL,
    role VARCHAR(100),
    status VARCHAR(50),
    registered_at DATETIME,
    PRIMARY KEY (event_id, volunteer_id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (volunteer_id) REFERENCES volunteer(id)
);

CREATE TABLE event_districts (
    event_id INTEGER NOT NULL,
    district_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, district_id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (district_id) REFERENCES district(id)
);

CREATE TABLE event_skills (
    event_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, skill_id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (skill_id) REFERENCES skill(id)
);
```

### 19. Contact Information Tables

**Purpose**: Multiple contact methods per contact

```sql
CREATE TABLE phone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    number VARCHAR(20),
    type VARCHAR(20),
    primary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (contact_id) REFERENCES contact(id)
);

CREATE TABLE email (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    email VARCHAR(100),
    type VARCHAR(20),
    primary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (contact_id) REFERENCES contact(id)
);

CREATE TABLE address (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    address_line1 VARCHAR(100),
    address_line2 VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50),
    type VARCHAR(20),
    primary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (contact_id) REFERENCES contact(id)
);
```

### 20. Supporting Tables

**Purpose**: Additional system functionality

```sql
CREATE TABLE bug_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50),
    description TEXT,
    status VARCHAR(20),
    reported_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (reported_by) REFERENCES users(id)
);

CREATE TABLE google_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    url VARCHAR(500),
    type VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action VARCHAR(100),
    table_name VARCHAR(100),
    record_id INTEGER,
    old_values TEXT,
    new_values TEXT,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE client_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    description TEXT,
    client_name VARCHAR(255),
    status VARCHAR(50),
    start_date DATE,
    end_date DATE,
    google_sheet_id VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pathway (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    description TEXT,
    salesforce_id VARCHAR(18) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE class (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    school_id INTEGER,
    grade_level VARCHAR(20),
    subject_area VARCHAR(100),
    teacher_name VARCHAR(255),
    student_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES school(id)
);
```

## 🔗 Data Relationships

### One-to-Many Relationships
- **Contact → Phone/Email/Address**: One contact can have multiple contact methods
- **Contact → History**: One contact can have multiple history records
- **Volunteer → Engagement**: One volunteer can have multiple engagements
- **Volunteer → EventParticipation**: One volunteer can participate in multiple events
- **Event → EventAttendanceDetail**: One event has one attendance detail record
- **Event → EventComment**: One event can have multiple comments
- **School → Teacher/Student**: One school can have multiple teachers/students
- **District → School**: One district can have multiple schools
- **User → History**: One user can perform multiple history actions

### Many-to-Many Relationships
- **Volunteer ↔ Organization**: Through `volunteer_organization` table
- **Volunteer ↔ Skill**: Through `volunteer_skills` table
- **Event ↔ Volunteer**: Through `event_volunteers` table
- **Event ↔ District**: Through `event_districts` table
- **Event ↔ Skill**: Through `event_skills` table
- **Event ↔ Teacher**: Through `event_teacher` table
- **Event ↔ Student**: Through `event_student_participation` table

### One-to-One Relationships
- **Volunteer ↔ ConnectorData**: Specialized data for connector program volunteers
- **Event ↔ EventAttendanceDetail**: Attendance tracking for events

## 📊 Data Validation Rules

### Contact Validation
- First and last names are required
- Email addresses must be valid format
- Phone numbers should follow standard format
- Age group must be valid enum value
- Education level must be valid enum value

### Volunteer Validation
- Local status is calculated based on address
- Volunteer dates must be valid and logical
- Times volunteered must be non-negative
- Education level must be valid enum value

### Event Validation
- Start date must be before end date
- Status transitions must be valid
- Attendance counts cannot exceed capacity
- Title must be non-empty and reasonable length

### User Validation
- Username and email must be unique
- Security level must be valid enum value
- API tokens must be unique and properly formatted

## 🔍 Common Queries

### Volunteer Queries
```sql
-- Find active volunteers by local status
SELECT v.*, c.first_name, c.last_name
FROM volunteer v
JOIN contact c ON v.id = c.id
WHERE v.local_status = 'local' AND v.status = 'active';

-- Find volunteers with specific skills
SELECT v.*, c.first_name, c.last_name, s.name as skill_name
FROM volunteer v
JOIN contact c ON v.id = c.id
JOIN volunteer_skills vs ON v.id = vs.volunteer_id
JOIN skill s ON vs.skill_id = s.id
WHERE s.name = 'Python Programming';

-- Find volunteers by organization
SELECT v.*, c.first_name, c.last_name, o.name as org_name
FROM volunteer v
JOIN contact c ON v.id = c.id
JOIN volunteer_organization vo ON v.id = vo.volunteer_id
JOIN organization o ON vo.organization_id = o.id
WHERE o.name = 'Tech Company';
```

### Event Queries
```sql
-- Find upcoming events by type
SELECT * FROM event
WHERE start_date > CURRENT_TIMESTAMP
AND type = 'career_fair'
AND status = 'Confirmed'
ORDER BY start_date;

-- Find events with attendance issues
SELECT e.*, ead.status as attendance_status
FROM event e
LEFT JOIN event_attendance_detail ead ON e.id = ead.event_id
WHERE ead.status = 'not_taken'
AND e.start_date < CURRENT_TIMESTAMP;

-- Find events by district
SELECT e.*, d.name as district_name
FROM event e
JOIN event_districts ed ON e.id = ed.event_id
JOIN district d ON ed.district_id = d.id
WHERE d.name = 'Kansas City School District';
```

### Report Queries
```sql
-- Volunteer activity summary
SELECT
    COUNT(DISTINCT v.id) as total_volunteers,
    COUNT(DISTINCT ep.event_id) as total_events,
    SUM(ep.delivery_hours) as total_hours
FROM volunteer v
LEFT JOIN event_participation ep ON v.id = ep.volunteer_id
WHERE ep.status = 'Attended';

-- Event participation by type
SELECT
    e.type,
    COUNT(DISTINCT e.id) as event_count,
    COUNT(ep.id) as participation_count,
    AVG(ep.delivery_hours) as avg_hours
FROM event e
LEFT JOIN event_participation ep ON e.id = ep.event_id
WHERE e.status = 'Completed'
GROUP BY e.type;
```

## 📥 Data Import/Export

### Salesforce Integration
- **Contact Sync**: Imports contact data from Salesforce Contact records
- **Event Sync**: Imports event data from Salesforce Session records
- **Participation Sync**: Imports participation data from Session_Participant__c records
- **Organization Sync**: Imports organization data from Salesforce Account records

### Google Sheets Integration
- **Report Export**: Exports report data to Google Sheets
- **Data Import**: Imports data from Google Sheets for bulk operations
- **Real-time Sync**: Maintains synchronization with Google Sheets

### CSV Import/Export
- **Bulk Operations**: Supports CSV import for volunteer, event, and organization data
- **Report Export**: Exports reports to CSV format
- **Data Backup**: Creates CSV backups of critical data

## 🔧 Database Maintenance

### Index Optimization
- **Query Performance**: Indexes on frequently queried fields
- **Composite Indexes**: Multi-column indexes for complex queries
- **Foreign Key Indexes**: Automatic indexing on foreign key relationships

### Data Cleanup
- **Duplicate Detection**: Identifies and merges duplicate records
- **Data Validation**: Ensures data integrity and consistency
- **Archive Strategy**: Moves old data to archive tables

### Backup Strategy
- **Daily Backups**: Automated daily database backups
- **Point-in-Time Recovery**: Transaction log backups for recovery
- **Export Backups**: CSV exports for data portability

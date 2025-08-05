# Polaris Notes

# Polaris Overview

Polaris is a custom web application designed to supplement Salesforce by capturing and managing data that SF alone cannot easily handle—particularly data from virtual sessions. It unifies this information into a single “data pool” and offers reporting features that streamline day-to-day operations for staff.

## Goals

1. **Fill Data Gaps from Virtual Sessions**
    - *Goal:* Combine and centralize session-related data that is not currently tracked in Salesforce.
    - *Metric:*
2. **Enhanced Reporting & Data Insights**
    - *Goal:* Develop a robust reporting system that captures key metrics—such as volunteer participation, student reach, and engagement trends—to provide stakeholders (e.g., schools, donors, and partners) with clear, data-driven insights into program impact.
3. **Enhanced Volunteer Matching**
    - *Goal:* Facilitate effective volunteer matching by enabling staff to quickly identify and assign volunteers based on specific criteria (skills, availability, experience).
4. **Future Extensions & Scalability**
    - *Goal:* Create a flexible foundation that can easily incorporate new features or data sources (like scheduling or additional integrations).

## Features

### **1. Data Integration**

- **Virtual Session Data Pool**: Aggregate attendance, volunteer participation, and other key details from online platforms and google sheets.
- **Central Repository**: Maintain a single source of truth for all session records, ensuring consistency and accuracy.

### **2. Volunteer & Attendance Tracking**

- **Volunteer Profiles**: Store basic information about volunteers, including any relevant skills or engagement history.
- **Attendance Records**: Log who attended each session—whether it’s volunteers, students, or teachers.

### **3. Reporting System**

- **Immediate Insights**: Generate usage reports, volunteer engagement summaries, or attendance analytics in just a few clicks.
- **Data Visualization**: View simple charts and metrics that highlight trends (e.g., total volunteer hours, average session attendance).
- **Export & Share**: Download or share these reports to support decision-making and communicate impact.

### 4. Volunteer Search & Matching

- **Narrow & Wide Searches**: Quickly search for volunteers using targeted criteria (e.g., specific skills, availability, interests) or broader searches for general availability.
- **Matching Suggestions**: Identify and match volunteers efficiently to appropriate events or roles, enhancing volunteer engagement and utilization.

### **5. Event Calendar (Basic)**

- **Event Overviews**: View a calendar of upcoming or past sessions and filter by date range.
- **Color-Coded Status (Limited)**: Mark events/sessions as needed (e.g., Published, Completed, Cancelled) for quick scanning.
- *(Note: Advanced scheduling and email reminders are planned for future releases.)*

## Roles: Polaris vs. Salesforce

### What Polaris Handles

- **Virtual & In-Person Session Data**: Captures and consolidates attendance details and volunteer involvement that SF cannot easily track from multiple sources.
- **Volunteer Search & Matching**: Identifies suitable volunteers for specific events or roles based on stored skills, availability, and engagement data.
- **On-Demand Reporting**: Generates quick metrics and visualizations tailored to program needs.
- **Future Growth**: Serves as a testing ground for new features before potential Salesforce integration.

### What Salesforce Handles (In Person Sessions)

- **Full CRM Functions**: Manages contacts, donor relationships, and advanced workflow automations.
- **Automated Communications**: Sends volunteers reminders, calendar invites, and emails related to upcoming events or program updates.

```python
                               +---------------------+
                               |   Salesforce API    |
                               +----------+----------+
                                          |
+-----------------------------------------v------------------------------------------+
|                                PythonAnywhere Host                                 |
|                                                                                    |
|  +-----------------------------+      +-----------------------------------------+  |
|  |   Your Flask Application    |      |         Reconciliation & DQ Job         |  |
|  |  (Backend with SQLite DB)   |----->| (Scheduled with APScheduler)            |  |
|  +-----------------------------+      |                                         |  |
|                                       | 1. Pull Incremental Data (you have this)  |  |
|                                       | 2. Validate with Great Expectations     |  |
|                                       | 3. Run Reconciliation Checks            |  |
|                                       | 4. Log Metrics to SQLite                |  |
|                                       | 5. Send Email Alert on Failure          |  |
|                                       +------------------+------------------------+  |
|                                                          |                          |
|                               +--------------------------v------------------------+ |
|                               |                     SQLite Database                 | |
|                               | +------------------+   +------------------------+ | |
|                               | | Application Data |   | data_quality_metrics | | |
|                               | +------------------+   +------------------------+ | |
|                               +---------------------------------------------------+ |
+------------------------------------------------------------------------------------+
```

1. **Reconciliation Checks**:
    - **Row-Count Diffs**: The simplest check. Compare `COUNT(*)` from a Salesforce report/query with `COUNT(*)` in your local table for the same data segment.
    - **Hash Checksums**: For a more granular check, create a checksum for each row by concatenating key fields (e.g., `f"{row.Id}{row.Name}{row.Amount}"`) and hashing the result. Compare the set of hashes between Salesforce and your local data.
    - **Field-Level Tolerances**: For numeric fields like revenue, don't look for an exact match. Instead, check if the value is within an acceptable tolerance (e.g., `abs(sfdc_revenue - local_revenue) <= 0.005 * sfdc_revenue`).

```python
Data Sources (Salesforce + Google Sheets)
    ↓
Ingestion Layer (Flask API + Bulk API 2.0)
    ↓  
Processing Layer (SQLAlchemy + Great Expectations)
    ↓
Database Layer (SQLite → PostgreSQL migration path)
    ↓
Monitoring Layer (Prometheus + Grafana + Slack)
```

### **Sample Code Snippets**

Here are some examples to bring these concepts to life.

Optimized Schema for Reconciliation:

```python

CREATE TABLE salesforce_contacts (
    id INTEGER PRIMARY KEY,
    salesforce_id TEXT UNIQUE NOT NULL,
    email TEXT,
    first_name TEXT,
    last_name TEXT,
    account_id TEXT,
    created_date TEXT,
    modified_date TEXT,
    sync_timestamp TEXT,
    sync_batch_id TEXT,
    record_hash TEXT, -- SHA-256 for change detection
    
    -- Reconciliation-optimized indexes
    INDEX idx_reconciliation (salesforce_id, record_hash),
    INDEX idx_sync_batch (sync_batch_id, modified_date),
    INDEX idx_email_lookup (email)
);

-- Events table with relationship tracking
CREATE TABLE salesforce_events (
    id INTEGER PRIMARY KEY,
    salesforce_id TEXT UNIQUE NOT NULL,
    subject TEXT,
    start_datetime TEXT,
    end_datetime TEXT,
    who_id TEXT, -- References Contact
    what_id TEXT, -- Related Account/Opportunity
    created_date TEXT,
    modified_date TEXT,
    sync_timestamp TEXT,
    sync_batch_id TEXT,
    record_hash TEXT,
    
    INDEX idx_event_reconciliation (salesforce_id, record_hash),
    INDEX idx_contact_events (who_id, start_datetime)
);
```

### Primary Key Alignment and Hash-Based Change Detection

The reconciliation system employs **multi-layered validation** combining row-count differentials, field-level hash checksums, and configurable tolerance checks:

```python
class DataReconciliationEngine:
    def __init__(self, sf_client, db_connection):
        self.sf = sf_client
        self.db = db_connection
        self.tolerance_config = {
            'revenue_variance': 0.005,  # 0.5% tolerance
            'date_variance_days': 0,
            'string_similarity_threshold': 0.95
        }
    
    def perform_reconciliation(self, object_type='Contact'):
        """Execute comprehensive reconciliation with detailed reporting"""
        
        # 1. Row count validation
        source_count = self.get_source_count(object_type)
        target_count = self.get_target_count(object_type)
        
        count_diff = abs(source_count - target_count)
        count_variance = count_diff / max(source_count, 1)
        
        # 2. Hash-based change detection
        hash_mismatches = self.detect_hash_mismatches(object_type)
        
        # 3. Field-level tolerance checks
        field_discrepancies = self.validate_field_tolerances(object_type)
        
        # 4. Schema drift detection
        schema_changes = self.detect_schema_changes(object_type)
        
        return self.generate_reconciliation_report({
            'row_count_variance': count_variance,
            'hash_mismatches': hash_mismatches,
            'field_discrepancies': field_discrepancies,
            'schema_changes': schema_changes
        })
    
    def detect_hash_mismatches(self, object_type):
        """Compare record hashes between source and target"""
        query = f"""
        WITH source_hashes AS (
            SELECT salesforce_id, record_hash 
            FROM {object_type.lower()}_staging
        ),
        target_hashes AS (
            SELECT salesforce_id, record_hash 
            FROM salesforce_{object_type.lower()}s
        )
        SELECT s.salesforce_id, s.record_hash as source_hash, 
               t.record_hash as target_hash
        FROM source_hashes s
        LEFT JOIN target_hashes t ON s.salesforce_id = t.salesforce_id
        WHERE s.record_hash != t.record_hash OR t.record_hash IS NULL
        """
        
        return self.db.execute(query).fetchall()
```

### **1. Reading Data and Validating with Great Expectations**

First, install the necessary libraries:
`pip install great-expectations sqlalchemy pandas`

This function shows how to wrap your data (from CSV or a Salesforce pull) in a Great Expectations validator.

```python
import great_expectations as gx
import pandas as pd

def validate_salesforce_data(data_as_dict_list):
    """
    Validates a list of dictionaries (from Salesforce) using Great Expectations.
    """
    df = pd.DataFrame(data_as_dict_list)

    # Convert to a GX DataFrame
    validator = gx.from_pandas(df)

    # --- Define Expectations ---
    # 1. Completeness: Critical fields should not be null.
    validator.expect_column_values_to_not_be_null("Id")
    validator.expect_column_values_to_not_be_null("Amount")

    # 2. Uniqueness: The Salesforce ID must be unique.
    validator.expect_column_values_to_be_unique("Id")

    # 3. Validity: Amount should be a positive number.
    validator.expect_column_values_to_be_of_type("Amount", "float")
    validator.expect_column_values_to_be_between("Amount", min_value=0)
    
    # 4. Consistency: Stage should be one of the predefined values.
    validator.expect_column_values_to_be_in_set("StageName", ["Prospecting", "Closed Won", "Closed Lost"])

    # --- Run Validation ---
    results = validator.validate()

    if not results["success"]:
        print("Data validation failed!")
        # You can inspect results["results"] for details
        
    return results["success"], results
```

### **2. Writing to SQLite with Upserts (SQLAlchemy)**

This function demonstrates an idempotent upsert into a SQLite database.

### **3. A Simple Reconciliation Job**

This function ties everything together into a single job you can schedule.

```python
import hashlib
import json

def get_row_checksum(row, fields):
    """Creates a SHA256 hash for a given row."""
    m = hashlib.sha256()
    # Concatenate sorted fields to ensure consistent hash
    concat_str = "".join(str(row.get(field, '')) for field in sorted(fields))
    m.update(concat_str.encode('utf-8'))
    return m.hexdigest()

def run_reconciliation():
    """
    A full reconciliation job.
    """
    # 1. Fetch data from Salesforce (your existing logic)
    # sfdc_data = your_salesforce_pull_logic()
    sfdc_data = [
        {'Id': '0068c00001AbCdEf', 'Name': 'Test Opp 1', 'Amount': 5000.0, 'StageName': 'Closed Won'},
        {'Id': '0068c00001AbCdEg', 'Name': 'Test Opp 2', 'Amount': 12000.0, 'StageName': 'Prospecting'}
    ] # Example data
    
    # 2. Validate it
    is_valid, validation_results = validate_salesforce_data(sfdc_data)
    if not is_valid:
        # Log results and send an alert
        log_dq_metrics(sfdc_data, validation_results)
        send_alert("Data Quality Validation Failed", json.dumps(validation_results, indent=2))
        return # Stop processing if data quality is poor

    # 3. Fetch corresponding data from local DB
    # local_data = your_db_read_logic()
    local_data = sfdc_data # Assume they match for this example

    # 4. Perform reconciliation checks
    sfdc_count = len(sfdc_data)
    local_count = len(local_data)
    
    if sfdc_count != local_count:
        send_alert("Row Count Mismatch", f"Salesforce has {sfdc_count} rows, local DB has {local_count}.")

    # Checksum comparison
    fields_to_hash = ['Id', 'Name', 'Amount', 'StageName']
    sfdc_checksums = {get_row_checksum(row, fields_to_hash) for row in sfdc_data}
    local_checksums = {get_row_checksum(row, fields_to_hash) for row in local_data}

    if sfdc_checksums != local_checksums:
        send_alert("Checksum Mismatch", "Row-level data does not match.")
        
    # 5. If all checks pass, perform the upsert
    upsert_data(sfdc_data)
    
    print("Reconciliation job completed successfully.")
```

### **Monitoring & Alerting Design**

We'll use a simple SQLite table for metrics and email for alerts.

**Metrics Table (`data_quality_metrics`)**

Create a table to store the results of each job run.

```python
CREATE TABLE data_quality_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    job_name TEXT NOT NULL,
    metric_name TEXT NOT NULL, -- e.g., 'row_count', 'validation_success_percent'
    metric_value REAL NOT NULL,
    is_success INTEGER NOT NULL, -- 1 for success, 0 for failure
    details TEXT -- Store JSON details for failures
);
```

**Alerting Function**

This function sends an email. You'll need to configure your email credentials as environment variables on PythonAnywhere.

```python
import smtplib
import os

def send_alert(subject, body):
    """Sends an email alert."""
    sender_email = os.environ.get("SENDER_EMAIL")
    receiver_email = os.environ.get("RECEIVER_EMAIL")
    password = os.environ.get("EMAIL_PASSWORD")

    message = f"Subject: {subject}\n\n{body}"
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server: # Example for Gmail
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
        print("Alert email sent.")
    except Exception as e:
        print(f"Failed to send email: {e}")
```

[Replicate From Zero Process](https://www.notion.so/Replicate-From-Zero-Process-234055d6ef7180e48369c78b33b05b90?pvs=21)

- [ ]  Company Reports
    - [ ]  In Person Per Student Numbers (from spreadhseet)
        
        [https://docs.google.com/spreadsheets/d/10V31qXxe99J7OOtvCHNu9G3G-O6krq8nOadXlcrRF2g/edit?gid=1722227486#gid=1722227486](https://docs.google.com/spreadsheets/d/10V31qXxe99J7OOtvCHNu9G3G-O6krq8nOadXlcrRF2g/edit?gid=1722227486#gid=1722227486)
        
        [https://docs.google.com/spreadsheets/d/12RSd5AqDzpYVpiT6O6sd4CHDgSbOY1txTIMJdbVBd6Y/edit?gid=0#gid=0](https://docs.google.com/spreadsheets/d/12RSd5AqDzpYVpiT6O6sd4CHDgSbOY1txTIMJdbVBd6Y/edit?gid=0#gid=0)
        
        https://docs.google.com/spreadsheets/d/16qEwzCNxS_5gEex3PDQIv-87XBNYv5qD/edit?gid=240271802#gid=240271802
        
- [ ]  pull data twice a week and automate it

Virtual Sessions

- Schools by session (is the count unique or total experiences?)
- Need documentation around how to exclude people form the virtual report
- feed social analytics into Polaris and google analytics

- work on report / feature to do voluntere mathcing for connector pathful events
- polaris: know who owns the upcoming pathful events
    - who has been emailed
    - assign who should be in charge of task
- view to see recent volunteres  and connector volunteers
- compbine org repot and org thank you report

- report for pathway - filter by types (stem)
- search by company in org report
- “student interactions” / impressions
- select more than one year
- report on a calendar year / build in timeperioids

teacher - page link

percentages

local volunteer in the glance

have teacher breakdown in the district

kck teachers

make sure topic/theme - ready for pathway

numbers reached per volunteer:

career speakers = total no fo students(underestimate)/(no of classrooms/no of toblesa)*# of rotations

number of roations and number of studnets per roation

total nno of studnets under estaimte - fall back number

pathways is the pull down list in salesforce need to be related

stem should be checkbox

duplciate in volunter report due to former orgs and such

export compnay report for that company

- [ ]  salesforce duplicate check and clean data
- [ ]  feature to manage quick links for users (and specific documntation)
- [ ]  Look at how local status is applied to volunteers
- [ ]  pull in data from forms
- [ ]  actual database
- [ ]  Plan and increase skills feature for tagging manually and automaticlaly
- [ ]  virtual duplicate title fixed
- [ ]  backup and restore system
- [ ]  pathway reports
- [ ]  hide anything not needed

### Polaris

- manage duplicates features in the future
- earch skills in depth along with bettter skill and skill matching
- fix local issue

events: better event type filter

Orgs: better table with better info and filter with better details

brittany reporting by district

- check the numbers and data

voluntold turn to voldteach

### Keva Polaris

- How she adds confirmed visits/ number of students etc. to [this BFI/HSA Events spreadsheet](https://docs.google.com/spreadsheets/d/1iNVtccYhRF9jktho4lClzBuBNLfBtzDvq_tkE_Y5pX4/edit?gid=592344467#gid=592344467) and schools add their names and the number of students they'd like to bring to each
- And tracks students that are signed up/ attended on [this Pathway Roster spreadsheet](https://docs.google.com/spreadsheets/d/1WLOUjSUy2jHqHFRuR02E4kthhuqyUtIIqcoApqecPT0/edit?gid=483295627#gid=483295627)

### To Do

check sync voluntold is working

polaris: need to vilter by more than on event in end of year erport, as well as add a exlude virtual

Mimic end of year reports for virtual sessions before meeting with brittany

- focus on kck

Visual of the systems (with documentation for each)

When to use: vms, volunt0old, website

need to show unique students reached + total students reached

remove sestiamted coutn of students for connector in end of year report

makre sure everyhhting in reports has a sort and possible fillter

connect survey monkey and salesforce survey data

paseo middle and stoney point elemntary not assocaited with a district in salesforce

way to merge contacts in polaris

use https://docs.google.com/spreadsheets/d/12RSd5AqDzpYVpiT6O6sd4CHDgSbOY1txTIMJdbVBd6Y/edit?gid=0#gid=0

- crate a way for them to aclacualte attendance based on rotiaotns, groups and voluntters/students

way to have connector sessions on district web pages (maybe setup them up via voluntold?)

One of the things I regularly run are reports related to numbers of students that were exposed to different career pathways.  For example, here's the [Business report](https://prep-kc.lightning.force.com/lightning/r/Report/00OUV000002mYZJ2A2/view?queryScope=userFolders) I run for State Street.  I tried to edit the filters to be for Construction/ Trades but it shows up with just one event and I'm not sure why.

This is the [spreadsheet](https://docs.google.com/spreadsheets/d/12RSd5AqDzpYVpiT6O6sd4CHDgSbOY1txTIMJdbVBd6Y/edit?gid=0#gid=0) Linda uses to mark what pathways are represented (though ideally in the future it would also pull from volunteers that mark pathways as one of their skills).  Let me know if you're able to figure out a way for me to currently run the report.

I added these two EOY reports to the overall google doc to track Polaris priorities:

- EOY district reports- be able to easily pull much of the info represented on these [EOY reports](https://drive.google.com/drive/folders/1Ui1E4TuC78mwHTpmgHkAIi7kwiC1sAC4) (and list what we need to track separately)
- EOY collective reports- need to make the following statements:
    - X number of unique volunteers, engaged in x Connector sessions & x in-person sessions reaching x number of unique students (just in-person for unique student count) and approximately x number virtually

Our meeting tomorrow with Andra will walk her through how she can access the district EOY reports. The other one is new but would be great to have to just be able to easily see where we are with overall numbers of volunteers/ students reached.

### Notes

Pathway Data

```html
SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c, 
       End_Date_and_Time__c, Session_Status__c, Location_Information__c, 
       Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c, 
       District__c, School__c, Legacy_Skill_Covered_for_the_Session__c, 
       Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
       Total_Requested_Volunteer_Jobs__c, Available_Slots__c
FROM Session__c
WHERE School__c = null
  AND Session_Status__c = 'Completed'
  AND Start_Date_and_Time__c >= 2024-06-01T00:00:00Z
ORDER BY Start_Date_and_Time__c DESC

```

- only does from june 24 onwards to make it simple and don’t have to filter connector sessions
- Need to figure out what events types to counts
- Virtual import: Now it correctly gets the presenter, but also adds someone not realted, but in the sign up it shows correctly
    - I need to look closer at the presnter/volunteer matching for online events because it needs to be robost so we arne’t doing duplicates
        - need a process for hadnling duplicates later
- old connecotr data in salesforce is a mess, looks like it goes up to 24 school year, so just note that it’s not 100% correct because it is wrong in salesforce

### To Do

- End of Year Report: Need to get the volunteer and hours reported.
- Importing data: show loader so they know it’s working
- optimize report get
- work on better studnet import method will need for pathway affiliation
- Estimate number of connector students based on classes (and estimate hours and volunteer)
- End of year report: have it downloadable into excel or google sheet?
- need to pull survey data and create reports
- Make sure all reports can be replicated: https://prep-kc.lightning.force.com/lightning/r/Folder/00l5f000002HmkOAAS/view?queryScope=userFolders
- See which volunteers are missing a primary affiliation and other duplicate check type stuff
- Student participation report [https://prep-kc.lightning.force.com/lightning/r/Report/00OUV000000sZ0o2AE/view?queryScope=userFolders](https://prep-kc.lightning.force.com/lightning/r/Report/00OUV000000sZ0o2AE/view?queryScope=userFolders)
- I regularly run pathway reports like this [BM Business Report](https://prep-kc.lightning.force.com/lightning/r/Report/00OUV000002mYZJ2A2/view?queryScope=userFolders) for funders to show how many students K-8 & 9-12 are engaged in exploration experiences related to Business, or Health, or construction/ trades, etc.  I need to combine the list of sessions it shows in the business report with the [Student participation report](https://prep-kc.lightning.force.com/lightning/r/Report/00OUV000000sZ0o2AE/view?queryScope=userFolders) to show unique numbers of students reached (as the numbers of students in the Business report have duplicates typically at the HS level.  So I cut/ paste students from the events listed then remove duplicates to get the unique count.  Example: [State Street report](https://docs.google.com/spreadsheets/d/16kTY7xsy2Vx1O21jfh4aIEYOZdo4kgLAaZL-hsZX3k8/edit?gid=561924064#gid=561924064)
- Show number of sessions, volunteers, students reached by company- I use this [main report](https://prep-kc.lightning.force.com/lightning/r/Report/00O5f000008nc7MEAQ/view?queryScope=userFoldersSharedWithMe) and edit the filters to change the timeframe or just see a particular company. For example, KU Med reached out this week to ask me how many sessions/ volunteers have been involved in over the last 3 years. So I edited that report to get [this info](https://docs.google.com/spreadsheets/d/1OI7Az1HajBx1LL_hbHNPwCi5QPrBd2fnPPNrtHc8fe0/edit?gid=995534133#gid=995534133) I shared with them. We also use this main report to determine at the end of each school year which companies were most engaged and therefore should get a special thank you from. The number of students reached is not always accurate so we have to manually update that as it depends on how many volunteers they had at an event if they actually talked with all students at a Career Jumping/ Career speaker event. Linda tracks numbers of students reached by volunteer on this spreadsheet [No. students reached](https://docs.google.com/spreadsheets/d/12RSd5AqDzpYVpiT6O6sd4CHDgSbOY1txTIMJdbVBd6Y/edit?gid=0#gid=0).
    - Here’s an example of the info I need to send to a company that does both in person and virtual: [Hill’s report](https://docs.google.com/spreadsheets/d/1K_B_FiYChpS7PMmzIot4ENKbVgkyrEuJR7XlxT8nOaY/edit?gid=0#gid=0)
- Seeing how active a company currently is, dates of when they last volunteered, etc. Within each company “account” on Salesforce, I regularly refer to the “related tab” to see the dashboard of how a company is involved. This dashboard includes volunteers that have cancelled (as shown by their status in the actual session, but we’ve never figured out a way to indicate that in this view).
- Need to process and a way to test the sync to automatically pull data
- And I don't see her [volunteering on the Connector from this school year](https://docs.google.com/spreadsheets/d/1nP58E3kYPUlY5Eg_wwbPwKucW4TitGPZottFDxKP42g/edit?gid=520481746#gid=520481746) showing up in either.
- find a way to get this data into salesforc eso we can serach it all: https://docs.google.com/spreadsheets/d/156-F6_Xl08JwZWM9RZoRWX-psjBCx5_zQQFOEoB7g50/edit?gid=273868617#gid=273868617

### Issues

- Doesn’t seem to handle multiple districts on one event and events like Health start and BFI missing
    - Currently adds district based on School on event
    - Need to add a way  so events are also associated by teachers or session participants
    - This is why so many sessions are missing they are BFI and healthstart
- Finish emergency report functions

### Pathway Data

Now Have import process

- pathway import imports both pathway data and session data (need to have events for it to populate)
- Pathway partipcaiton imports partipcation if student data is there.

Need to explore the pathway data to import it and work with it. Tied to three files

[Pathway__c.csv](Pathway__c.csv)

Defines Pathways

- Relevant Data: Salesforce ID / Name

[Pathway_Session__c.csv](Pathway_Session__c.csv)

Pathway Tied Session: 

- Relevant Data: Salesforce ID / Session Salesforce ID / Pathway Salesforce ID

[Pathway_Participant__c.csv](Pathway_Participant__c.csv)

Student Participation? Can’t tell if there are also volunteers or teachers

### Polaris

[report of primary affiliton](https://prep-kc.lightning.force.com/lightning/r/Report/00OUV000008dZu92AE/view?queryScope=userFolders) missing in sf

### Spreadsheets Useful for Polaris Connectivity

https://docs.google.com/spreadsheets/d/1WLOUjSUy2jHqHFRuR02E4kthhuqyUtIIqcoApqecPT0/edit?gid=1799747997#gid=1799747997

https://docs.google.com/spreadsheets/d/1uNZo8RqjSXiQeg--F9asTiSvDfbpqGlo7VH4aEb9GUY/edit?gid=2125137210#gid=2125137210

### Polaris Requests

[Here is an example of the](https://docs.google.com/spreadsheets/d/1kLNgxoPr2CYlmVT_DUkqLMH_1luY8Bgm_f6a_0FhATw/edit?usp=sharing) Diploma+ data that is tracked re: CCE beyond PREP-KC events. I am sure we can  ask to see the other middle schools' data. It looks like offsite visits  and PREP-KC events define CCE

BFI:

[https://mail.google.com/mail/u/1/#inbox/FMfcgzQZTVlkDbSlxzmKmCWgCwqBZjfm](https://mail.google.com/mail/u/1/#inbox/FMfcgzQZTVlkDbSlxzmKmCWgCwqBZjfm)
 I'd like to be able to run the report for the number/ list of BFI 
campus/ worksite visits and numbers of unique students that have been 
involved.  I'd also like to see how many K-8 students were engaged in an
 event that BF was represented (which you'll see Linda tags our Career 
Jumping/ Career Speaker events to indicate which "count" as business, or
 health, or trades, etc.  This is the [spreadsheet](https://docs.google.com/spreadsheets/d/12RSd5AqDzpYVpiT6O6sd4CHDgSbOY1txTIMJdbVBd6Y/edit?gid=0#gid=0) she uses to mark the pathways represented and then adds it to Salesforce (but it might be that not everything is in Salesforce 
Just so you know, the volunteer numbers are numbers of total volunteers at the event, but not number of volunteers discussing business/ finance careers.  That was the piece I mentioned I don't know how to run that report in Salesforce as I'm not sure where the info lives for volunteers when they sign up for an event and choose a pathway they are representing.  So ideally I could also run a report (not for my current needs but for future) to see how many volunteers we have talking with students about business/ finance and it would include more than just those that are at the events labeled as Business/ Finance if that makes sense?
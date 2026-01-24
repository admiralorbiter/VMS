# Test Pack 7: Data Integrity & Operations

Validation of system resilience, data integrity logic, and operational workflows.

> [!INFO]
> **Coverage**
> [FR-DATA-901](requirements#fr-data-901) (Duplicates), [FR-DATA-902](requirements#fr-data-902) (Profile Creation), [FR-DATA-903](requirements#fr-data-903) (Sync Dependencies), [FR-OPS-904](requirements#fr-ops-904) (Attendance), [FR-OPS-905](requirements#fr-ops-905) (Purge), [FR-OPS-907](requirements#fr-ops-907) (Auto-Admin)

---

## Test Data Setup

**Scenario 1: Duplicate Processing**
- **Existing Event A**: SalesforceID=`SF123`, Status=`Requested`
- **Incoming Event B**: SalesforceID=`SF123`, Status=`Confirmed` (Newer timestamp)

**Scenario 2: Profile Creation**
- **Incoming Participant**: "New Volunteer", Email=`new.vol@example.com`, Role=`Professional`
- **System State**: No existing Volunteer record for this email.

## Test Cases

### Data Integrity

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-901"></a>**TC-901** | **Duplicate Merge Strategy**<br>Import row with same SalesforceID as existing event | - Single event record remains<br>- Status updates to `Confirmed`<br>- Registered counts sum or take max based on logic |
| <a id="tc-902"></a>**TC-902** | **Profile Auto-Creation**<br>Import participant with unknown email | - New `Volunteer` record created<br>- Participation linked to new record<br>- No error returned |
| <a id="tc-903"></a>**TC-903** | **Sync Dependency Order**<br>Attempt to import Event for unknown School | - Import fails or creates placeholder (depending on config)<br>- Error logged specific to missing dependency |
| <a id="tc-904"></a>**TC-904** | **Partial Batch Success**<br>Import batch of 10 events, 1 invalid | - 9 Events created successfully<br>- 1 Error recorded in sync log<br>- Response indicates "Partial Success" |

### Operational Workflows

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-910"></a>**TC-910** | **Attendance Status Workflow**<br>Update attendance to 'In Progress' | - `EventAttendance.status` = `IN_PROGRESS`<br>- Event `status` remains unchanged (e.g. `COMPLETED`) |
| <a id="tc-911"></a>**TC-911** | **Admin Purge Action**<br>Execute purge endpoint as Admin | - Events table count = 0<br>- Audit Log contains "PURGE" entry<br>- Non-admin user receives 403 Forbidden |
| <a id="tc-912"></a>**TC-912** | **Auto-Admin Creation**<br>Start app with empty User table | - Default `admin` user created<br>- Default password hash set<br>- Log entry confirms creation |
| <a id="tc-913"></a>**TC-913** | **Event Categorization**<br>Create event with type 'Career Fair' | - Event saved with correct `EventType`<br>- Filtering by 'Career Fair' returns this event |

---

*Last updated: January 2026*
*Version: 1.0*

# Runbook

**Troubleshooting guides for common incidents**

## Reference

- **Severity levels and monitors**: [Monitoring and Alert](monitoring) - System health monitoring and alerting
- **Metric definitions**: [Metrics Bible](metrics_bible) - Canonical metric calculations
- **Import procedures**: [Import Playbook](import_playbook) - Step-by-step import guides
- **Magic link system**: [RBAC Matrix - Teacher Magic Link System](rbac_matrix#teacher-magic-link-system)
- **Incident response**: [Privacy & Data Handling - Incident Response](privacy_data_handling#incident-response)

## Quick Triage (60 seconds)

Before diving into specific runbooks, gather these basics:

### Who/Scope
- **District name**: Which district is affected?
- **Teacher email** (if applicable): Normalized email address

### What
- **Which page/report**: Dashboard, export, magic link, etc.
- **What looks wrong**: Specific discrepancy or error message

### When
- **Timestamp noticed**: When was the issue first observed?
- **Date range used**: What date range was selected in the report/dashboard?

### Check These Timestamps

Verify data freshness for these syncs. See [Monitoring and Alert - Sync Timestamp Monitoring](monitoring#sync-timestamp-monitoring) for detailed procedures.

1. **SF→VT Event Sync**: Check VolunTeach sync logs or last sync timestamp
   - Expected: Hourly sync
   - Reference: [Architecture - Sync Cadences](architecture#sync-cadences)

2. **Comms Sync**: Check history import logs
   - Expected: Daily sync
   - Route: `routes/salesforce/history_import.py` `/history/import-from-salesforce`

3. **Dashboard Refresh**: Check cache refresh timestamps
   - Expected: As configured in cache management

4. **Pathful Import**: Check last virtual session import timestamp
   - Expected: Daily or as needed
   - Route: `routes/virtual/routes.py` `/virtual/import-sheet`

5. **Roster Import**: Check last teacher roster import timestamp
   - Expected: Manual (2 week cadence)
   - Route: `routes/virtual/usage.py` teacher progress import

**If any stale beyond threshold → SEV2**

**Thresholds:**
- SF→VT Event Sync: > 2 hours stale
- Comms Sync: > 24 hours stale
- Pathful Import: > 24 hours stale (if daily expected)
- Roster Import: > 2 weeks stale (if expected to be current)

## Runbook 10.1: Dashboard Numbers Wrong

### Symptoms

- "Achieved count is too low/high"
- "School totals don't match"
- "Students/volunteers seem off"
- "Teacher progress status incorrect"

### Diagnose

**Step 1: Identify which metric**
- Teacher progress (Achieved/In Progress/Not Started)
- Student metrics (Unique Students Reached, attendance counts)
- Volunteer metrics (Unique Volunteers Reached, Total Volunteer Hours)
- Organization metrics (Unique Organizations Engaged)

**Step 2: Check freshness of relevant imports/syncs**
- Review Quick Triage timestamp checks above
- Verify data sources are up-to-date
- Check for failed imports in logs

**Step 3: Spot-check 3 records against source data**
- Pick 3 known records (teachers, students, volunteers)
- Verify counts match between dashboard and source system
- Check for data quality issues

**Reference:** [Metrics Bible](metrics_bible) for metric calculation definitions

### Teacher Progress Checklist

**Total teachers = active roster count?**
- Verify `TeacherProgress` table matches expected roster size
- Check for missing teachers in roster

**Progress logic correct?**
- **Achieved**: `count(TeacherSession WHERE attendance_status = Attended) ≥ 1`
- **In Progress**: `Attended = 0 AND count(SignedUp WHERE session_start > now()) ≥ 1`
- **Not Started**: `Attended = 0 AND no SignedUp rows`

**Pick 3 known teachers and verify status:**
1. Select 3 teachers with known status (e.g., one Achieved, one In Progress, one Not Started)
2. Check `EventTeacher` records for attendance
3. Verify `TeacherProgress.get_progress_status()` returns expected status
4. Compare to dashboard display

**Reference:**
- [Metrics Bible - Teacher Progress Statuses](metrics_bible#teacher-progress-statuses)
- Implementation: `models/teacher_progress.py` `get_progress_status()`

### Fix

**Stale data → rerun import/sync**
- If timestamps show stale data, trigger manual import/sync
- Wait for completion, then refresh dashboard
- Verify numbers update correctly

**Definition dispute → clarify with Metrics Bible**
- If numbers are fresh but still wrong, verify calculation matches Metrics Bible
- Check for filtering issues (date range, district scope, etc.)
- Verify aggregation logic matches documented definitions

**Data quality issue → investigate source**
- If spot-checks reveal data discrepancies, investigate source system
- Check for missing records, duplicates, or data entry errors
- Update source data and re-import

## Runbook 10.2: Teacher Magic Link Issues

### Symptoms

- "I didn't get the email"
- "It says I'm not found"
- "Link shows error"
- **SEV1**: "Link shows someone else's data"

### Case A: Email Not Received

**Check email send failures:**
- Review email delivery logs
- Check for bounce notifications
- Verify email provider status

**Check bounce rate:**
- Review email bounce reports
- Check if teacher email address is valid
- Verify email domain is not blocked

**Check request was logged:**
- Verify magic link request was logged in system
- Check audit logs for request timestamp
- Confirm email generation was attempted

**Fix:**
- If email failed to send, regenerate and resend
- If email bounced, verify teacher email address
- If request not logged, investigate request handling

### Case B: Not Found / Not Eligible

**Check teacher email in roster (normalized):**
- Verify teacher email exists in `TeacherProgress` table
- Check email normalization (lowercase, trimmed)
- Verify email matches exactly (case-insensitive)

**If missing → update roster, resend:**
1. Import/update teacher roster with correct email
2. Verify teacher appears in `TeacherProgress` table
3. Regenerate magic link
4. Resend email to teacher

**Reference:**
- [Import Playbook - Teacher Roster Import](import_playbook#playbook-b-teacher-roster-import)
- [RBAC Matrix - Teacher Magic Link System](rbac_matrix#teacher-magic-link-system)

### Case C: Link Error / Expired

**Check token TTL:**
- Verify token expiration time
- Check if token has expired
- Review token generation timestamp

**Regenerate and resend:**
1. Generate new magic link token
2. Verify token is time-limited and unguessable
3. Send new link to teacher
4. Confirm teacher can access dashboard

**Reference:**
- Token generation: `secrets.token_hex()` (cryptographically secure)
- Implementation: [RBAC Matrix - Teacher Magic Link System](rbac_matrix#teacher-magic-link-system)

### Case D: Wrong Data (SEV1)

> [!WARNING]
> **SEV1 Security Incident**: If teacher sees wrong data, treat as critical security incident.

**Immediately disable magic-link endpoint:**
1. Disable the magic link dashboard route if possible
2. Prevent further access while investigating
3. Document which endpoint was disabled

**Identify scope leak cause:**
- Check if token is properly bound to teacher email
- Verify token validation logic
- Check for SQL injection or query parameter issues
- Review access control decorators

**Notify Admin, treat as SEV1 security incident:**
1. **Treat as SEV1** - Highest priority security incident
2. **Document scope** - What data was exposed, to whom, when
3. **Notify leadership** - Escalate immediately
4. **Follow incident response procedures**

**Reference:**
- [Privacy & Data Handling - Incident Response](privacy_data_handling#incident-response)
- [Audit Requirements - Permission Changes (SEV1)](audit_requirements#f-permission-changes-sev1-worthy)
- [RBAC Matrix - Teacher Magic Link System](rbac_matrix#teacher-magic-link-system)

## Runbook 10.3: Pathful Schema Change

### Symptoms

- Import fails with "missing required columns"
- Spike in invalid rows
- Teachers suddenly all Not Started
- Import shows unexpected column errors

### Fix

**Step 1: Stop imports**
- Pause scheduled Pathful imports if automated
- Prevent further data corruption

**Step 2: Save sample export with new format**
- Export sample file from Pathful with new column structure
- Save for comparison

**Step 3: Compare headers to mapping contract**
- Review [Field Mappings - Pathful Export](field_mappings#6-pathful-export--polaris) for expected columns
- Compare new export headers to expected columns
- Identify missing, renamed, or new columns

**Step 4: Update alias mapping**
- If column names changed, update mapping code in `routes/virtual/routes.py`
- Update field mappings if column structure changed
- Ensure all required columns are mapped

**Step 5: Test on small file**
- Import test file with 5-10 rows
- Verify data imports correctly
- Check for any validation errors

**Step 6: Resume production**
- Once verified, resume normal import schedule
- Monitor first production import for errors

**Reference:**
- [Import Playbook - Column Change Procedure](import_playbook#column-change-procedure)
- [Field Mappings - Pathful Export](field_mappings#6-pathful-export--polaris)
- Implementation: `routes/virtual/routes.py` `/virtual/import-sheet`

## Runbook 10.4: Calendar Invites Not Sending

### Symptoms

- "Got confirmation but no calendar"
- "Got nothing"
- "Invite has wrong location"
- "Invite has wrong time"

### Case A: Generation Failures

**Check for missing SF event fields:**
- **Location**: Verify `Event.location` or `Event.venue_name` is populated
- **Timezone**: Verify timezone is set correctly (default: America/Chicago)
- **Start/End times**: Verify `Event.start_datetime` and `Event.end_datetime` are set
- **Date**: Verify event date is in the future (for upcoming events)

**Fix:**
- Update Salesforce event fields with missing data
- Verify timezone conversion is correct
- Regenerate calendar invite

**Reference:**
- [Architecture - System URLs](architecture#system-urls) for Salesforce system
- [Field Mappings - Normalization Rules](field_mappings#normalization-rules-apply-everywhere) for date/timezone handling

### Case B: Delivery Failures

**Check email provider errors:**
- Review email delivery logs
- Check for bounce notifications
- Verify email provider status (Mailjet integration)
- Check rate limits

**Check if ICS attachments blocked:**
- Verify ICS file is generated correctly
- Check if email client blocks .ics attachments
- Verify MIME type is correct (`text/calendar`)

**Fix:**
- If email provider down, queue invites and resend when fixed
- If ICS blocked, check email client settings
- Verify email provider configuration

### Case C: Content Wrong

**Verify SF event location fields:**
- Check `Event.location` or `Event.venue_name` in Salesforce
- Verify location is formatted correctly
- Check for special characters that might break ICS format

**Check timezone conversion:**
- Verify event timezone (default: America/Chicago)
- Check UTC conversion is correct
- Verify daylight saving time handling

**Fix:**
- Update Salesforce event fields with correct location/timezone
- Regenerate calendar invite
- Test with sample event to verify format

**Reference:**
- [Architecture - Timezone Normalization](architecture#r6--timezone-normalization)
- [Field Mappings - Normalization Rules](field_mappings#normalization-rules-apply-everywhere)

## Severity Levels

**SEV1**: Critical security incidents
- Wrong data shown (e.g., teacher sees another teacher's data)
- Data leakage
- Unauthorized access
- Immediate action required: Disable endpoint, notify leadership

**SEV2**: System degradation
- Stale data beyond threshold
- Import failures affecting multiple users
- Dashboard showing incorrect aggregates
- Action required: Investigate and fix within 24 hours

**Reference:**
- [Audit Requirements - Permission Changes (SEV1)](audit_requirements#f-permission-changes-sev1-worthy)
- [Privacy & Data Handling - Incident Response](privacy_data_handling#incident-response)

## Related Requirements

- [NFR-2](non_functional_requirements#nfr-2): Reliability - Clear failure feedback
- [NFR-5](non_functional_requirements#nfr-5): Auditability - Key actions logged
- [FR-INPERSON-124](requirements#fr-inperson-124): Distinguish "no events to sync" vs "sync failure"

---

*Last updated: January 2026*
*Version: 1.0*

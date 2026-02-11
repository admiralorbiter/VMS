# Monitoring and Alert

**System health monitoring and alerting**

## Reference

- **Troubleshooting procedures**: [Runbook](runbook) - Incident response guides
- **Metric definitions**: [Metrics Bible](metrics_bible) - Canonical metric calculations
- **Sync schedules**: [Architecture - Sync Cadences](architecture#sync-cadences) - Expected sync frequencies
- **Import procedures**: [Import Playbook](import_playbook) - Step-by-step import guides
- **Deployment procedures**: [Deployment Guide](deployment) - PythonAnywhere deployment and maintenance

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

**Reference:** [Runbook - Severity Levels](runbook#severity-levels) for detailed definitions

## Health Checks

### System Health Check

**Script:** `scripts/utilities/pythonanywhere_cache_manager.py` `health_check()`

**Command:**
```bash
python scripts/pythonanywhere_cache_manager.py health
```

**Components Checked:**
- **Flask App**: Application initialization and context
- **Database**: Connection and query execution
- **Cache System**: Cache status and functionality

**Output:**
- Health status report with timestamp
- Individual component status (OK/FAIL)
- Overall health status (HEALTHY/UNHEALTHY)

**Implementation:**
- Checks Flask app context
- Executes database query (`SELECT 1`)
- Verifies cache system status
- Returns structured health status dictionary

**Reference:** `scripts/utilities/pythonanywhere_cache_manager.py` lines 138-193

**Related:** [Smoke Tests](smoke_tests) for functional verification

### Import Health Monitoring

**Script:** `scripts/cli/monitor_import_health.py`

**Command:**
```bash
python scripts/cli/monitor_import_health.py
```

**Checks Performed:**
1. **Scheduled status on completed events**: Volunteers with "Scheduled" status on completed events
2. **Missing delivery hours**: Attended volunteers without delivery hours
3. **Events missing participation records**: Events with volunteers but no participation records
4. **Recent import activity**: Last 100 participation records
5. **Status distribution**: Participation status counts
6. **Recent completed events**: Events completed in last 30 days with proper status updates

**When to Run:**
- After each nightly import
- When investigating data integrity issues
- As part of regular health monitoring

**Output:**
- Health check report with issues found
- Status: PASSED (no issues) or FAILED (issues detected)
- Detailed issue descriptions

**Reference:** `scripts/cli/monitor_import_health.py`

## Monitoring Dashboards

### Cache Status Dashboard

**Route:** `/management/cache/status`

**Access:** Admin only

**Shows:**
- Cache refresh status (running/stopped)
- Refresh interval (hours)
- Last refresh timestamp
- Statistics:
  - Total refreshes
  - Successful refreshes
  - Failed refreshes

**Implementation:**
- Route: `routes/management/cache_management.py` `cache_status()`
- Template: `templates/management/cache_status.html`
- Uses `get_cache_status()` function

**Reference:** `routes/management/cache_management.py` lines 50-69

### Email Overview Dashboard

**Route:** `/management/email`

**Access:** Admin only

**Shows:**
- Delivery enabled/disabled status
- Allowlist active status
- Sender queue size
- Failures in last 24 hours
- Links to all email management sections

**Additional Sections:**
- Templates (`/management/email/templates`)
- Outbox / Messages (`/management/email/outbox`)
- Delivery Attempts (`/management/email/attempts`)
- Settings & Safety (`/management/email/settings`)

**Reference:** `docs/guides/email_system.md` - Email Overview Dashboard section

### Data Quality Dashboard

**Route:** `/data_quality/quality_dashboard`

**Shows:**
- Quality scores by entity (Volunteer, Organization, Event, Student, Teacher)
- Validation results across dimensions:
  - Business Rules
  - Field Completeness
  - Data Types
  - Relationships
- Overall quality scores
- Status indicators (Excellent, Good, Warning, Error)

**Features:**
- Real-time quality scoring
- Entity-specific validation
- Auto-refresh on entity type change
- Comprehensive metrics display

**Reference:** `templates/data_quality/README.md`

## Alert Configuration

### Alert Settings

**File:** `config/validation.py` `ALERT_CONFIG`

**Configuration Options:**
- `alert_on_critical`: Default `true` - Alert on critical validation issues
- `alert_on_error`: Default `true` - Alert on error-level issues
- `alert_on_warning`: Default `false` - Alert on warning-level issues
- `alert_emails`: List of email addresses for alerts
- `alert_slack_webhook`: Slack webhook URL for alerts
- `alert_threshold_critical`: Default `5` - Critical alert threshold
- `alert_threshold_error`: Default `20` - Error alert threshold

### Alert Channels

**Email Alerts:**
- Configured via `VALIDATION_ALERT_EMAILS` environment variable
- Comma-separated list of email addresses
- Sent when thresholds are exceeded

**Slack Webhook Alerts:**
- Configured via `VALIDATION_SLACK_WEBHOOK` environment variable
- Sends alerts to configured Slack channel
- Includes validation issue details

### Alert Triggers

**Critical Alerts:**
- Triggered when critical validation issues exceed threshold (default: 5)
- Always enabled (`alert_on_critical: true`)

**Error Alerts:**
- Triggered when error-level issues exceed threshold (default: 20)
- Always enabled (`alert_on_error: true`)

**Warning Alerts:**
- Triggered when warning-level issues occur
- Disabled by default (`alert_on_warning: false`)

**Reference:** `config/validation.py` lines 72-92

## Sync Timestamp Monitoring

Monitor data freshness by checking sync timestamps:

### SF→VT Event Sync

**Expected Cadence:** Hourly

**How to Check:**
- Check VolunTeach sync logs
- Verify last sync timestamp
- Check for sync failures

**Threshold:** > 2 hours stale → SEV2

**Reference:** [Architecture - Sync Cadences](architecture#sync-cadences)

### Comms Sync

**Expected Cadence:** Daily

**How to Check:**
- Check history import logs
- Route: `routes/salesforce/history_import.py` `/history/import-from-salesforce`
- Verify last import timestamp

**Threshold:** > 24 hours stale → SEV2

**Reference:** [Architecture - Salesforce → Polaris](architecture#salesforce--polaris)

### Dashboard Refresh

**Expected Cadence:** As configured in cache management

**How to Check:**
- Check cache refresh timestamps
- Route: `/management/cache/status`
- Verify last refresh time

**Reference:** [Cache Status Dashboard](#cache-status-dashboard)

### Pathful Import

**Expected Cadence:** Daily or as needed

**How to Check:**
- Check last virtual session import timestamp
- Route: `routes/virtual/routes.py` `/virtual/import-sheet`
- Verify import logs

**Threshold:** > 24 hours stale (if daily expected) → SEV2

**Reference:** [Architecture - Pathful → Polaris](architecture#pathful--polaris)

### Roster Import

**Expected Cadence:** Manual (2 week cadence)

**How to Check:**
- Check last teacher roster import timestamp
- Route: `routes/virtual/usage.py` teacher progress import
- Verify import logs

**Threshold:** > 2 weeks stale (if expected to be current) → SEV2

**Reference:** [Architecture - District Roster Import → Polaris](architecture#district-roster-import--polaris)

**Quick Reference:** [Runbook - Quick Triage](runbook#quick-triage-60-seconds) for threshold definitions

**Configuration:** [Deployment Guide - Scheduled Tasks Setup](deployment#scheduled-tasks-setup) for setting up scheduled syncs

## Log Monitoring

### Log Files

**Application Logs:**
- Location: `logs/app.log`
- Contains: Application-level events, errors, warnings
- Command: `tail -f logs/app.log`

**Cache Manager Logs:**
- Location: `logs/cache_manager.log`
- Contains: Cache refresh operations, scheduler events
- Command: `tail -f logs/cache_manager.log`

**Error Logs:**
- Location: `logs/error.log`
- Contains: Error-level events and exceptions
- Command: `tail -f logs/error.log`

**Import Logs:**
- Location: `logs/daily_imports.log`
- Contains: Daily import operations, completion status
- Command: `tail -f logs/daily_imports.log`

### Log Commands

**Monitor Logs:**
```bash
# Application logs
tail -f logs/app.log

# Cache manager logs
tail -f logs/cache_manager.log

# Error logs
tail -f logs/error.log
```

**Search Logs:**
```bash
# Find errors across all logs
grep "ERROR" logs/*.log

# Check import completion
grep "Import completed" logs/daily_imports.log

# Check for specific errors
grep "ERROR" logs/daily_imports.log | tail -20
```

**Reference:** [Deployment Guide - Monitoring & Maintenance](deployment#monitoring--maintenance)

## Database Monitoring

### Integrity Checks

**Check Database Integrity:**
```bash
sqlite3 instance/vms.db "PRAGMA integrity_check;"
```

**Check Database Size:**
```bash
sqlite3 instance/vms.db "PRAGMA page_count; PRAGMA page_size;"
```

**Optimize Database:**
```bash
sqlite3 instance/vms.db "VACUUM;"
```

### Database Health

**Regular Checks:**
- Run integrity check weekly
- Monitor database size growth
- Optimize database monthly or as needed

**Warning Signs:**
- Integrity check failures
- Rapid database size growth
- Slow query performance

**Reference:** [Deployment Guide - Monitoring & Maintenance](deployment#monitoring--maintenance)

## Key Metrics

### Cache Metrics

**Refresh Success Rate:**
- Target: >95%
- Calculation: (Successful refreshes / Total refreshes) × 100
- Monitor: Cache Status Dashboard

**Average Refresh Time:**
- Target: <5 minutes
- Monitor: Cache manager logs
- Check: `grep "took.*seconds" logs/cache_manager.log`

**Cache Hit Rate:**
- Target: >90%
- Monitor: Cache performance metrics

**Error Rate:**
- Target: <5%
- Calculation: (Failed refreshes / Total refreshes) × 100
- Monitor: Cache Status Dashboard

**Reference:** [Cache Management - Monitoring & Analytics](docs/living/Cache_Management.md#monitoring--analytics)

### Import Metrics

**Import Completion Rate:**
- Monitor: Daily import logs
- Check: `grep "Import completed" logs/daily_imports.log`
- Target: 100% completion

**Participation Status Consistency:**
- Monitor: Import Health Monitoring script
- Check: No "Scheduled" status on completed events
- Target: 0 inconsistencies

**Delivery Hours Completeness:**
- Monitor: Import Health Monitoring script
- Check: All attended volunteers have delivery hours
- Target: 100% completeness

**Reference:** [Import Health Monitoring](#import-health-monitoring)

## Monitoring Procedures

### Daily Monitoring

1. **Check System Health:**
   ```bash
   python scripts/pythonanywhere_cache_manager.py health
   ```

2. **Review Cache Status:**
   - Visit `/management/cache/status`
   - Verify last refresh time
   - Check refresh success rate

3. **Check Import Logs:**
   ```bash
   grep "Import completed" logs/daily_imports.log | tail -10
   ```

4. **Review Email Dashboard:**
   - Visit `/management/email`
   - Check queue size and failures

### Weekly Monitoring

1. **Run Import Health Check:**
   ```bash
   python scripts/cli/monitor_import_health.py
   ```

2. **Check Database Integrity:**
   ```bash
   sqlite3 instance/vms.db "PRAGMA integrity_check;"
   ```

3. **Review Data Quality Dashboard:**
   - Visit `/data_quality/quality_dashboard`
   - Check quality scores by entity

4. **Review Sync Timestamps:**
   - Verify all syncs are within thresholds
   - Check for stale data

### Incident Response

**When SEV1 Detected:**
1. Follow [Runbook - Severity Levels](runbook#severity-levels)
2. Disable affected endpoint if possible
3. Document scope and notify leadership
4. Follow [Privacy & Data Handling - Incident Response](privacy_data_handling#incident-response)

**When SEV2 Detected:**
1. Investigate root cause
2. Check relevant sync timestamps
3. Review logs for errors
4. Fix within 24 hours

**Reference:** [Runbook](runbook) for detailed troubleshooting procedures

**Related:** [Smoke Tests](smoke_tests) for functional verification after fixes

## Related Requirements

- [NFR-2](non_functional_requirements#nfr-2): Reliability - Clear failure feedback
- [NFR-5](non_functional_requirements#nfr-5): Auditability - Key actions logged
- [FR-INPERSON-124](requirements#fr-inperson-124): Distinguish "no events to sync" vs "sync failure" for monitoring

---

*Last updated: January 2026*
*Version: 1.0*

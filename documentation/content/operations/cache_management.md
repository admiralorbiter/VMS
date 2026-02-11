# Cache Management System

## Overview

The VMS cache management system provides automated 24-hour cache refresh for all report data. The system is designed for PythonAnywhere deployment with comprehensive monitoring and error handling.

**Key Components:**
- **Cache Refresh Scheduler**: `utils/cache_refresh_scheduler.py`
- **PythonAnywhere Manager**: `scripts/pythonanywhere_cache_manager.py`
- **Web Interface**: `/management/cache/status`
- **Database Models**: `models/reports.py`

---

## Cache Types

| Cache Type | Model | Refresh | Approx. Size |
|------------|-------|---------|--------------|
| **District Reports** | `DistrictYearEndReport`, `DistrictEngagementReport` | 24 hours | 50-100KB/district |
| **Organization Reports** | `OrganizationReport`, `OrganizationSummaryCache` | 24 hours | 20-50KB/org |
| **Virtual Sessions** | `VirtualSessionReportCache`, `VirtualSessionDistrictCache` | 24 hours | 100-500KB/year |
| **Volunteer Reports** | `RecentVolunteersReportCache`, `FirstTimeVolunteerReportCache` | 24 hours | 50-200KB/year |
| **Recruitment** | `RecruitmentCandidatesCache` | 24 hours | 10-50KB/event |

---

## Configuration

```python
REFRESH_INTERVAL_HOURS = 24
REFRESH_TIME = "02:00"  # 2 AM daily
MAX_CACHE_AGE_HOURS = 24
```

**Cache Validation Rules:**
- Last updated within 24 hours
- No errors during generation
- Data structure is complete

**Error Handling:**
- 3 retry attempts with exponential backoff
- Serve stale data if refresh fails
- Comprehensive error logging

---

## Management Commands

### PythonAnywhere

```bash
# Basic operations
python scripts/pythonanywhere_cache_manager.py refresh
python scripts/pythonanywhere_cache_manager.py status
python scripts/pythonanywhere_cache_manager.py health

# Force refresh
python scripts/pythonanywhere_cache_manager.py refresh --force
python scripts/pythonanywhere_cache_manager.py refresh --type district
```

### Local Development

```bash
# Cache management
python scripts/cache_management.py refresh-all
python scripts/cache_management.py refresh district
python scripts/cache_management.py status

# Scheduler control
python scripts/cache_management.py start-scheduler
python scripts/cache_management.py stop-scheduler
```

### Web Interface

| Endpoint | Description |
|----------|-------------|
| `/management/cache/status` | View cache status dashboard |
| `/management/cache/refresh` | Trigger manual refresh |
| `/management/cache/api/*` | API endpoints |

---

## PythonAnywhere Setup

Configure a scheduled task:

| Setting | Value |
|---------|-------|
| **Command** | `python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh` |
| **Hour** | 2 (runs at 2 AM daily) |
| **Minute** | 0 |

Test after setup:
```bash
python scripts/pythonanywhere_cache_manager.py status
python scripts/pythonanywhere_cache_manager.py refresh --force
```

---

## Monitoring

### Key Metrics

| Metric | Target |
|--------|--------|
| Refresh Success Rate | >95% |
| Average Refresh Time | <5 minutes |
| Cache Hit Rate | >90% |
| Error Rate | <5% |

### Log Commands

```bash
# View recent refreshes
grep "Cache refresh completed" logs/cache_manager.log

# Check for errors
grep "ERROR" logs/cache_manager.log

# Monitor performance
grep "took.*seconds" logs/cache_manager.log
```

---

## Troubleshooting

### Scheduled Task Not Running

```bash
# Verify task is enabled in PythonAnywhere
# Check command path matches your installation
# Test manually:
python scripts/pythonanywhere_cache_manager.py refresh
```

### Cache Refresh Failures

```bash
# Check logs
tail -f logs/cache_manager.log

# Verify database connectivity
python -c "from app import app; from models import db; app.app_context().push(); db.session.execute('SELECT 1')"

# Check disk space
df -h
```

### Performance Issues

```bash
# Check cache size
sqlite3 instance/vms.db "SELECT name, length(data) FROM sqlite_master WHERE type='table' AND name LIKE '%cache%';"

# Monitor refresh time
grep "took.*seconds" logs/cache_manager.log | tail -10
```

---

## Maintenance

### Daily
- Monitor scheduled task execution
- Check cache refresh logs
- Verify web app performance

### Weekly
- Analyze cache performance metrics
- Review error patterns
- Check disk space usage

### Monthly
- Review cache configuration
- Analyze refresh patterns
- Database optimization (VACUUM, REINDEX)

---

## Performance Optimization

### Database Maintenance

```bash
# Analyze database
sqlite3 instance/vms.db "ANALYZE;"

# Reindex cache tables
sqlite3 instance/vms.db "REINDEX;"

# Vacuum database
sqlite3 instance/vms.db "VACUUM;"
```

### Clean Old Cache Entries

```python
from app import app
from models.reports import *
from datetime import datetime, timedelta

with app.app_context():
    cutoff = datetime.now() - timedelta(days=7)
    VirtualSessionReportCache.query.filter(
        VirtualSessionReportCache.last_updated < cutoff
    ).delete()
    db.session.commit()
```

### Log Rotation

```bash
# Rotate logs
mv logs/cache_manager.log logs/cache_manager_$(date +%Y%m%d).log
touch logs/cache_manager.log

# Compress old logs
gzip logs/cache_manager_*.log

# Clean old logs (older than 30 days)
find logs/ -name "cache_manager_*.log.gz" -mtime +30 -delete
```

---

## Related Documentation

- [Monitoring and Alerts](monitoring) — Health checks and dashboards
- [Deployment Guide](deployment) — PythonAnywhere setup
- [Runbook](runbook) — Operational procedures

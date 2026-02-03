# Deployment Guide

**PythonAnywhere deployment and maintenance**

## Overview

This guide covers deploying the VMS application to PythonAnywhere with automated cache refresh scheduling and monitoring.

**Deployment Platform:** PythonAnywhere

**Requirements:**
- PythonAnywhere account (Hacker plan minimum for scheduled tasks)
- Python 3.10+
- Git access to repository

**Related Documentation:**
- [Monitoring and Alert](monitoring) - System health monitoring
- [Smoke Tests](smoke_tests) - Post-deployment verification
- [Import Playbook](import_playbook) - Import procedures
- [Architecture - Sync Cadences](architecture#sync-cadences) - Sync schedules
- [Cache Management](monitoring#cache-status-dashboard) - Cache system details

## Initial Setup

### 1. PythonAnywhere Account Setup

**Steps:**
1. Create PythonAnywhere account at [https://www.pythonanywhere.com/](https://www.pythonanywhere.com/)
2. Choose appropriate plan (Hacker plan minimum for scheduled tasks)
3. Note: Scheduled tasks require paid plan

### 2. Project Deployment

**SSH to PythonAnywhere:**
```bash
ssh yourusername@ssh.pythonanywhere.com
```

**Clone repository:**
```bash
git clone https://github.com/yourusername/VMS.git
cd VMS
```

**Set up virtual environment:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with production values
```

### 3. Database Setup

**Initialize database:**
```bash
flask db upgrade
```

**Create admin user:**
```bash
python scripts/create_admin.py
```

**Verify database:**
```bash
flask db current
```

**Reference:** [Import Playbook](import_playbook) for running initial imports after setup

## Web App Configuration

### 1. WSGI Configuration

**File:** `/var/www/yourusername_pythonanywhere_com_wsgi.py`

**Content:**
```python
import sys
import os

# Add your project directory to the Python path
path = '/home/yourusername/VMS'
if path not in sys.path:
    sys.path.append(path)

# Import your Flask app
from app import app as application

if __name__ == "__main__":
    application.run()
```

### 2. Static Files Configuration

**Static files:**
- Static files URL: `/static/`
- Static files directory: `/home/yourusername/VMS/static/`

**Media files:**
- Media files URL: `/media/`
- Media files directory: `/home/yourusername/VMS/instance/`

Configure these in PythonAnywhere Web tab > Static files section.

### 3. Environment Variables

**Set in PythonAnywhere Web tab > Environment variables:**

**Required variables:**
```bash
FLASK_ENV=production
DATABASE_URL=sqlite:///instance/vms.db
SECRET_KEY=your-secure-random-key-here  # REQUIRED - app will fail to start without this
```

> [!CAUTION]
> The application will **fail to start** in production if `SECRET_KEY` is not set or uses the default value. Generate a secure key with: `python -c "import secrets; print(secrets.token_hex(32))"`

**Security & CORS variables:**
```bash
# CORS - comma-separated list of allowed origins (optional)
# If not set, defaults to APP_BASE_URL
CORS_ALLOWED_ORIGINS=https://polaris-prepkc.pythonanywhere.com

# Application base URL (used for emails, redirects, CORS fallback)
APP_BASE_URL=https://polaris-prepkc.pythonanywhere.com
```

**Logging variables:**
```bash
# Log level: DEBUG, INFO, WARNING, ERROR (default: INFO in production)
LOG_LEVEL=INFO
```

**Salesforce Integration (optional):**
```bash
SF_USERNAME=your-salesforce-username
SF_PASSWORD=your-salesforce-password
SF_SECURITY_TOKEN=your-salesforce-security-token
```

**Email Configuration (optional):**
```bash
MJ_APIKEY_PUBLIC=your-mailjet-public-key
MJ_APIKEY_PRIVATE=your-mailjet-private-key
MAIL_FROM=your-email@domain.com
EMAIL_DELIVERY_ENABLED=true
EMAIL_ALLOWLIST=email1@domain.com,email2@domain.com
```

**Session Configuration (optional):**
```bash
SESSION_COOKIE_NAME=vms_session
REMEMBER_COOKIE_NAME=vms_remember
SESSION_LIFETIME_SECONDS=28800
```

**Reference:** `config/__init__.py` for all configuration options

## Health Check Endpoint

The application provides a `/health` endpoint for monitoring and load balancers:

**Endpoint:** `GET /health`

**Healthy Response (200):**
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "production"
}
```

**Unhealthy Response (503):**
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "error": "connection error details"
}
```

**Usage:** Configure your monitoring service to poll `/health` periodically.

## Scheduled Tasks Setup

### 1. Cache Refresh Task

**Task Configuration (in PythonAnywhere Tasks tab):**
- **Command:** `python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh`
- **Hour:** 2 (runs at 2 AM daily)
- **Minute:** 0
- **Enabled:** Yes

**Purpose:** Refresh all report caches to ensure data freshness

**Reference:** [Architecture - Sync Cadences](architecture#sync-cadences)

### 2. Daily Imports Task

**Task Configuration (in PythonAnywhere Tasks tab):**
- **Command:** `python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --daily`
- **Hour:** 3 (runs at 3 AM daily, after cache refresh)
- **Minute:** 0
- **Enabled:** Yes

**Purpose:** Import data from Salesforce (organizations, volunteers, events, history)

**Reference:** [Import Playbook - Salesforce Imports](import_playbook#playbook-d-salesforce-imports)

### 3. Task Monitoring

**Check cache refresh status:**
```bash
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py status
```

**View cache refresh logs:**
```bash
tail -f /home/yourusername/VMS/logs/cache_manager.log
```

**Manual cache refresh execution:**
```bash
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh --force
```

**Check daily imports status:**
```bash
python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --validate
```

**View daily imports logs:**
```bash
tail -f /home/yourusername/VMS/logs/daily_imports.log
```

**Manual daily imports execution:**
```bash
python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --daily
```

**Reference:** [Monitoring and Alert - Log Monitoring](monitoring#log-monitoring)

### 4. Health Monitoring

**Perform health check:**
```bash
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py health
```

**Check system resources:**
```bash
df -h
free -h
```

**Reference:** [Monitoring and Alert - Health Checks](monitoring#health-checks)

## Cache Management Commands

### Basic Operations

**Refresh all caches:**
```bash
python scripts/pythonanywhere_cache_manager.py refresh
```

**Force refresh (ignore timing):**
```bash
python scripts/pythonanywhere_cache_manager.py refresh --force
```

**Refresh specific cache type:**
```bash
python scripts/pythonanywhere_cache_manager.py refresh --type district
python scripts/pythonanywhere_cache_manager.py refresh --type organization
python scripts/pythonanywhere_cache_manager.py refresh --type virtual_session
python scripts/pythonanywhere_cache_manager.py refresh --type volunteer
python scripts/pythonanywhere_cache_manager.py refresh --type recruitment
```

### Monitoring & Status

**Check cache status:**
```bash
python scripts/pythonanywhere_cache_manager.py status
```

**Health check:**
```bash
python scripts/pythonanywhere_cache_manager.py health
```

**View logs:**
```bash
tail -f logs/cache_manager.log
```

**Reference:** [Monitoring and Alert - Cache Status Dashboard](monitoring#cache-status-dashboard)

## Daily Imports Commands

### Basic Operations

**Run daily imports (organizations, volunteers, affiliations, events, history):**
```bash
python scripts/daily_imports/daily_imports.py --daily
```

**Run full imports (all data including students, schools, classes, teachers):**
```bash
python scripts/daily_imports/daily_imports.py --full
```

**Run only specific imports:**
```bash
python scripts/daily_imports/daily_imports.py --only organizations
python scripts/daily_imports/daily_imports.py --only volunteers
python scripts/daily_imports/daily_imports.py --only events
```

**Exclude specific imports:**
```bash
python scripts/daily_imports/daily_imports.py --exclude students
python scripts/daily_imports/daily_imports.py --exclude teachers
```

### Testing & Validation

**Dry run (show what would be imported without actually importing):**
```bash
python scripts/daily_imports/daily_imports.py --dry-run
```

**Validate configuration and connections:**
```bash
python scripts/daily_imports/daily_imports.py --validate
```

**Run with verbose logging:**
```bash
python scripts/daily_imports/daily_imports.py --daily --verbose
```

**Reference:** [Import Playbook](import_playbook) for detailed import procedures

### Monitoring & Troubleshooting

**Check import logs:**
```bash
tail -f logs/daily_imports.log
```

**View recent import results:**
```bash
grep "Import completed" logs/daily_imports.log | tail -10
```

**Check for import errors:**
```bash
grep "ERROR" logs/daily_imports.log | tail -20
```

**Monitor import progress:**
```bash
tail -f logs/daily_imports.log | grep "Processing"
```

**Reference:** [Monitoring and Alert - Log Monitoring](monitoring#log-monitoring)

## Monitoring & Maintenance

### 1. Log Monitoring

**Application logs:**
```bash
tail -f logs/app.log
```

**Cache manager logs:**
```bash
tail -f logs/cache_manager.log
```

**Error logs:**
```bash
tail -f logs/error.log
```

**Reference:** [Monitoring and Alert - Log Monitoring](monitoring#log-monitoring)

### 2. Database Maintenance

**Check database size:**
```bash
sqlite3 instance/vms.db "PRAGMA page_count; PRAGMA page_size;"
```

**Optimize database:**
```bash
sqlite3 instance/vms.db "VACUUM;"
```

**Check database integrity:**
```bash
sqlite3 instance/vms.db "PRAGMA integrity_check;"
```

**Reference:** [Monitoring and Alert - Database Monitoring](monitoring#database-monitoring)

### 3. Cache Health Monitoring

**Check cache status:**
```bash
python scripts/pythonanywhere_cache_manager.py status
```

**Verify cache freshness:**
```bash
python -c "
from app import app
from utils.cache_refresh_scheduler import get_cache_status
with app.app_context():
    status = get_cache_status()
    print(f'Last refresh: {status[\"last_refresh\"]}')
    print(f'Total refreshes: {status[\"stats\"][\"total_refreshes\"]}')
    print(f'Successful: {status[\"stats\"][\"successful_refreshes\"]}')
    print(f'Failed: {status[\"stats\"][\"failed_refreshes\"]}')
"
```

**Reference:** [Monitoring and Alert - Key Metrics](monitoring#key-metrics)

## Troubleshooting

### Common Issues

#### 1. Scheduled Task Not Running

**Check task configuration:**
- Verify command path is correct
- Check if task is enabled
- Review task logs for errors

**Test task manually:**
```bash
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh
```

#### 2. Cache Refresh Failures

**Check logs for specific errors:**
```bash
tail -f logs/cache_manager.log
```

**Verify database connectivity:**
```bash
python -c "from app import app; from models import db; app.app_context().push(); db.session.execute('SELECT 1')"
```

**Check disk space:**
```bash
df -h
```

**Verify permissions:**
```bash
ls -la /home/yourusername/VMS/logs/
```

**Reference:** [Runbook - Dashboard Numbers Wrong](runbook#runbook-101-dashboard-numbers-wrong)

#### 3. Web App Issues

**Check web app status:**
- Visit PythonAnywhere Web tab
- Check for error messages

**Restart web app:**
```bash
touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

**Check error logs:**
```bash
tail -f /var/log/yourusername.pythonanywhere.com.error.log
```

**Verify static files:**
```bash
ls -la /home/yourusername/VMS/static/
```

### Emergency Procedures

#### 1. Manual Cache Refresh

**Force refresh all caches:**
```bash
python scripts/pythonanywhere_cache_manager.py refresh --force
```

**Refresh specific problematic cache:**
```bash
python scripts/pythonanywhere_cache_manager.py refresh --type district
```

#### 2. Database Recovery

**Backup current database:**
```bash
cp instance/vms.db instance/vms_backup_$(date +%Y%m%d_%H%M%S).db
```

**Restore from backup:**
```bash
cp instance/vms_backup_YYYYMMDD_HHMMSS.db instance/vms.db
```

**Recreate database:**
```bash
flask db upgrade
```

**Reference:** [Runbook](runbook) for detailed troubleshooting procedures

## Performance Optimization

### 1. Cache Optimization

**Monitor cache hit rates:**
```bash
python scripts/pythonanywhere_cache_manager.py status
```

**Adjust refresh frequency if needed:**
- Current: 24 hours
- Can be modified in scheduled task settings

**Reference:** [Monitoring and Alert - Key Metrics](monitoring#key-metrics)

### 2. Database Optimization

**Analyze database:**
```bash
sqlite3 instance/vms.db "ANALYZE;"
```

**Reindex database:**
```bash
sqlite3 instance/vms.db "REINDEX;"
```

**Vacuum database:**
```bash
sqlite3 instance/vms.db "VACUUM;"
```

**Reference:** [Monitoring and Alert - Database Monitoring](monitoring#database-monitoring)

### 3. Log Management

**Rotate logs:**
```bash
mv logs/cache_manager.log logs/cache_manager_$(date +%Y%m%d).log
touch logs/cache_manager.log
```

**Compress old logs:**
```bash
gzip logs/cache_manager_*.log
```

## Deployment Updates

### 1. Code Updates

**Pull latest changes:**
```bash
git pull origin main
```

**Update dependencies:**
```bash
pip install -r requirements.txt
```

**Run migrations:**
```bash
flask db upgrade
```

**Restart web app:**
```bash
touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

**Test cache refresh:**
```bash
python scripts/pythonanywhere_cache_manager.py refresh --force
```

**Run smoke tests:**
```bash
python -m pytest tests/smoke/
```

**Reference:** [Smoke Tests](smoke_tests) for post-deployment verification

### 2. Configuration Updates

**Update environment variables:**
- Edit in PythonAnywhere Web tab > Environment variables
- Restart web app after changes

**Restart web app:**
```bash
touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

**Verify changes:**
```bash
python scripts/pythonanywhere_cache_manager.py health
```

### 3. Database Schema Updates

**Backup database before migration:**
```bash
cp instance/your_database.db instance/your_database_backup_$(date +%Y%m%d_%H%M%S).db
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Verify migration success:**
```bash
alembic current
```

**Restart web app:**
```bash
touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

**Test application:**
- Visit: `https://yourusername.pythonanywhere.com/`
- Run smoke tests: `python -m pytest tests/smoke/`

## Checklists

### Initial Deployment

- [ ] PythonAnywhere account created
- [ ] Repository cloned
- [ ] Virtual environment set up
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Admin user created
- [ ] Web app configured
- [ ] Static files configured
- [ ] Cache refresh scheduled task created
- [ ] Daily imports scheduled task created
- [ ] Cache refresh tested
- [ ] Daily imports tested
- [ ] Health check passed
- [ ] Smoke tests passed

**Reference:** [Smoke Tests - Pre-Deployment](smoke_tests#pre-deployment)

### Regular Maintenance

- [ ] Monitor scheduled task execution
- [ ] Check cache refresh logs
- [ ] Verify web app status
- [ ] Monitor database size
- [ ] Review error logs
- [ ] Update dependencies
- [ ] Backup database
- [ ] Optimize database

**Reference:** [Monitoring and Alert - Monitoring Procedures](monitoring#monitoring-procedures)

### Troubleshooting

- [ ] Check task configuration
- [ ] Verify file permissions
- [ ] Review error logs
- [ ] Test manual operations
- [ ] Check system resources
- [ ] Verify network connectivity

**Reference:** [Runbook](runbook) for detailed troubleshooting procedures

## Related Documentation

- [Monitoring and Alert](monitoring) - System health monitoring and alerting
- [Smoke Tests](smoke_tests) - Post-deployment verification
- [Import Playbook](import_playbook) - Detailed import procedures
- [Architecture](architecture) - System architecture and sync cadences
- [Runbook](runbook) - Troubleshooting guides
- [Cache Management](monitoring#cache-status-dashboard) - Cache system details

## Support

For issues with PythonAnywhere deployment:

1. Check the troubleshooting section above
2. Review logs for specific error messages
3. Test manual operations to isolate issues
4. Contact PythonAnywhere support if needed
5. Check [Runbook](runbook) for application-specific issues

---

*Last updated: February 2026*
*Version: 1.1*

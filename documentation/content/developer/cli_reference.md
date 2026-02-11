# CLI Reference

Quick reference for CLI commands used in VMS development and operations.

---

## Development Setup

### Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Development Server

```bash
# Run Flask app
python app.py

# Run with Flask CLI
flask run --port 5050

# Run with debug mode
flask run --debug --port 5050
```

---

## Testing & Code Quality

### Run Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/unit/test_models.py

# Run with verbose output
python -m pytest -v

# Run tests in parallel
python -m pytest -n auto
```

### Code Quality

```bash
# Format code with Black
black .

# Check formatting without changing
black --check .

# Lint with Flake8
flake8 .

# Security checks with Bandit
bandit -r .

# Run all quality checks
black --check . && flake8 . && bandit -r .
```

---

## Database Operations

### Migrations

```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade

# Show migration history
flask db history

# Show current migration
flask db current

# Stamp database (mark as up-to-date)
flask db stamp head
```

### SQLite Direct Access

```bash
# SQLite CLI access
sqlite3 instance/vms.db

# Common SQLite commands
.tables                    # List all tables
.schema table_name         # Show table schema
SELECT * FROM volunteer LIMIT 5;  # Sample query
.quit                     # Exit SQLite
```

### Database Performance

```bash
# Analyze table statistics
sqlite3 instance/vms.db "ANALYZE;"

# Check index usage
sqlite3 instance/vms.db "PRAGMA index_list(volunteer);"

# Monitor database size
sqlite3 instance/vms.db "PRAGMA page_count; PRAGMA page_size;"
```

### Backup & Restore

```bash
# Backup database
cp instance/vms.db instance/vms_backup_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp instance/vms_backup_YYYYMMDD_HHMMSS.db instance/vms.db
```

---

## Data Synchronization

### Salesforce Sync

```bash
# Run Salesforce sync
python scripts/sync_script.py

# Check sync status
python scripts/sync_script.py --status

# Force full sync
python scripts/sync_script.py --force

# Sync specific entity
python scripts/sync_script.py --entity volunteer
```

### Daily Imports

```bash
# Run daily imports
python scripts/daily_imports/daily_imports.py --daily

# Run full imports
python scripts/daily_imports/daily_imports.py --full

# Run specific imports only
python scripts/daily_imports/daily_imports.py --only organizations
python scripts/daily_imports/daily_imports.py --only volunteers

# Dry run (no changes)
python scripts/daily_imports/daily_imports.py --dry-run
```

### Cache Management

```bash
# Refresh all caches
python scripts/pythonanywhere_cache_manager.py refresh

# Force refresh
python scripts/pythonanywhere_cache_manager.py refresh --force

# Refresh specific type
python scripts/pythonanywhere_cache_manager.py refresh --type district

# Check status
python scripts/pythonanywhere_cache_manager.py status

# Health check
python scripts/pythonanywhere_cache_manager.py health
```

---

## Deployment (PythonAnywhere)

### Deploy Updates

```bash
# SSH to PythonAnywhere
ssh yourusername@ssh.pythonanywhere.com

# Navigate and pull changes
cd VMS
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart web app
touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

### Scheduled Tasks

| Task | Command | Schedule |
|------|---------|----------|
| Cache Refresh | `python scripts/pythonanywhere_cache_manager.py refresh` | 2:00 AM |
| Daily Imports | `python scripts/daily_imports/daily_imports.py --daily` | 3:00 AM |

---

## Troubleshooting

### Common Issues

```bash
# Port already in use
lsof -i :5050
kill -9 <PID>

# Windows: check port
netstat -ano | findstr 5050

# Database locked
rm instance/vms.db-journal

# Virtual environment issues
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Logs & Monitoring

```bash
# View application logs
tail -f logs/app.log

# View error logs
tail -f logs/error.log

# Check system resources
htop
df -h
```

---

## Data Analysis

### Python Shell with Models

```python
from app import create_app, db
from models import Volunteer, Organization, Event

app = create_app()
with app.app_context():
    print(f'Volunteers: {Volunteer.query.count()}')
    print(f'Organizations: {Organization.query.count()}')
    print(f'Events: {Event.query.count()}')
```

---

## Validation & Data Quality

### Run Validation System

```bash
# Run comprehensive validation
python scripts/validation/run_validation.py

# Run specific validation type
python scripts/validation/run_validation.py --type count
python scripts/validation/run_validation.py --type completeness
python scripts/validation/run_validation.py --type data-type
python scripts/validation/run_validation.py --type relationship
python scripts/validation/run_validation.py --type business-rules

# Run for specific entity
python scripts/validation/run_validation.py --entity volunteer
python scripts/validation/run_validation.py --entity organization

# Run with time period
python scripts/validation/run_validation.py --period 30d
```

### Quality Dashboard

Access via browser: `http://localhost:5050/data_quality/quality_dashboard`

---

## Google Sheets Operations

```bash
# Copy Google Sheets data
python scripts/data/copy_google_sheets.py

# Copy specific sheet
python scripts/data/copy_google_sheets.py --sheet "Volunteer Data"

# Check sheet permissions
python scripts/data/copy_google_sheets.py --check-permissions
```

---

## Utility Scripts

### Data Management

```bash
# Copy users
python scripts/data/copy_users.py

# Copy students
python scripts/data/copy_students.py

# Mark excluded volunteers
python scripts/maintenance/mark_excluded_volunteers.py

# Scan for duplicates
python scripts/maintenance/scan_event_student_duplicates.py
```

### System Utilities

```bash
# Setup encryption key
python scripts/admin/setup_encryption_key.py

# Teacher progress matching
python scripts/utilities/match_teacher_progress.py 2025-2026
```

---

## Command Frequency

| Frequency | Commands |
|-----------|----------|
| **Daily** | Environment setup, tests, dev server, migrations |
| **Weekly** | Validation runs, Salesforce sync, performance monitoring |
| **Monthly** | Database backups, dependency updates, config reviews |
| **As Needed** | Troubleshooting, data recovery, system diagnostics |

---

## Related Documentation

- [Deployment Guide](deployment) — Full deployment instructions
- [Cache Management](cache-management) — Cache system details
- [Daily Import Scripts](daily-import-scripts) — Import pipeline
- [Monitoring](monitoring) — Health checks and alerts

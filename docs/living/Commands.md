---
title: "VMS CLI Commands & Operations"
status: active
doc_type: overview
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["commands", "cli", "operations", "vms"]
summary: "Quick reference for CLI commands and operations used in VMS development and operations. Development setup, testing, database operations, and system management."
canonical: "/docs/living/Commands.md"
---

# VMS CLI Commands & Operations

## 🎯 **Quick Reference**

This document provides quick access to common CLI commands and operations for VMS development and operations.

Keep this updated with commands you use frequently.

## 🚀 **Development Setup**

### **Environment Setup**
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

# Check Python version
python --version
```

### **Database Setup**
```bash
# Initialize database
flask db upgrade

# Create admin user
python scripts/create_admin.py

# Check database status
flask db current
flask db history

# Reset database (development only)
flask db downgrade base
flask db upgrade
```

### **Development Server**
```bash
# Run Flask app
python app.py

# Run with Flask CLI
flask run --port 5050

# Run with debug mode
flask run --debug --port 5050

# Check if port is in use
# Windows
netstat -ano | findstr 5050

# macOS/Linux
lsof -i :5050
```

## 🧪 **Testing & Code Quality**

### **Run Tests**
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/unit/test_models.py

# Run with verbose output
python -m pytest -v

# Run with print statements
python -m pytest -s

# Run tests in parallel
python -m pytest -n auto
```

### **Code Quality Checks**
```bash
# Format code with Black
black .

# Check formatting without changing
black --check .

# Lint with Flake8
flake8 .

# Security checks with Bandit
bandit -r .

# Type checking (if using mypy)
mypy .

# Run all quality checks
black --check . && flake8 . && bandit -r .
```

### **Test Database**
```bash
# Set up test database
export FLASK_ENV=testing
flask db upgrade --directory tests/migrations

# Run tests with test database
python -m pytest --db=test
```

## 🗄️ **Database Operations**

### **Migrations**
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

### **Database Queries**
```bash
# SQLite CLI access
sqlite3 instance/vms.db

# Common SQLite commands
.tables                    # List all tables
.schema table_name         # Show table schema
SELECT * FROM volunteer LIMIT 5;  # Sample query
.quit                     # Exit SQLite
```

### **Database Performance & Optimization**
```bash
# Check query performance
sqlite3 instance/vms.db "PRAGMA query_only = ON; EXPLAIN QUERY PLAN SELECT * FROM volunteer;"

# Analyze table statistics
sqlite3 instance/vms.db "ANALYZE;"

# Check index usage
sqlite3 instance/vms.db "PRAGMA index_list(volunteer);"

# Monitor database size
sqlite3 instance/vms.db "PRAGMA page_count; PRAGMA page_size;"
```

### **Migration Best Practices**
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

# Validate migrations in CI
alembic upgrade head --sql
```

### **Backup & Restore**
```bash
# Backup database
cp instance/vms.db instance/vms_backup_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp instance/vms_backup_YYYYMMDD_HHMMSS.db instance/vms.db

# Compress backup
gzip instance/vms_backup_*.db
```

## 🔍 **Validation & Data Quality**

### **Run Validation System**
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
python scripts/validation/run_validation.py --period 90d
```

### **Quality Dashboard**
```bash
# Access quality dashboard
# Open browser to: http://localhost:5050/data_quality/quality_dashboard

# Check validation logs
tail -f logs/validation.log

# View recent validation results
ls -la logs/validation_*.log
```

## 🔄 **Data Synchronization**

### **Salesforce Sync**
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

### **Google Sheets Operations**
```bash
# Copy Google Sheets data
python scripts/copy_google_sheets.py

# Copy specific sheet
python scripts/copy_google_sheets.py --sheet "Volunteer Data"

# Check sheet permissions
python scripts/copy_google_sheets.py --check-permissions
```

## 🚀 **Deployment & Operations**

### **Production Deployment**
```bash
# SSH to PythonAnywhere
ssh yourusername@ssh.pythonanywhere.com

# Navigate to project
cd VMS

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart web app
touch /var/www/yourusername_pythonanywhere_com_wsgi.py

# Check web app status
pythonanywhere.com/webapps/
```

### **Logs & Monitoring**
```bash
# View application logs
tail -f logs/app.log

# View error logs
tail -f logs/error.log

# Check system resources
htop
df -h
free -h

# Monitor Flask app
ps aux | grep python
```

## 🛠️ **Maintenance & Troubleshooting**

### **Common Issues**
```bash
# Port already in use
lsof -i :5050
kill -9 <PID>

# Database locked
rm instance/vms.db-journal

# Import errors
python -c "import sys; print(sys.path)"
which python

# Virtual environment issues
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **Performance Monitoring**
```bash
# Profile Flask app
python -m flask run --profiler

# Check database performance
sqlite3 instance/vms.db "PRAGMA query_only = ON; EXPLAIN QUERY PLAN SELECT * FROM volunteer;"

# Monitor memory usage
python -c "import psutil; print(psutil.virtual_memory())"
```

## 📊 **Reporting & Analytics**

### **Generate Reports**
```bash
# Run attendance report
python scripts/generate_attendance_report.py

# Export data to CSV
python scripts/export_data.py --entity volunteer --format csv

# Generate quality metrics
python scripts/validation/generate_quality_report.py
```

### **Data Analysis**
```bash
# Start Python shell with models
python -c "
from app import create_app, db
from models import Volunteer, Organization, Event
app = create_app()
with app.app_context():
    print(f'Volunteers: {Volunteer.query.count()}')
    print(f'Organizations: {Organization.query.count()}')
    print(f'Events: {Event.query.count()}')
"
```

## 🔧 **Utility Scripts**

### **Data Management**
```bash
# Copy users
python scripts/copy_users.py

# Copy students
python scripts/copy_students.py

# Mark excluded volunteers
python scripts/mark_excluded_volunteers.py

# Scan for duplicates
python scripts/scan_event_student_duplicates.py
```

### **System Utilities**
```bash
# Setup encryption key
python scripts/setup_encryption_key.py

# Check system health
python scripts/health_check.py

# Backup configuration
cp config/validation.py config/validation_backup.py
```

## 📝 **Command Categories**

### **Daily Development**
- Environment setup and activation
- Running tests and quality checks
- Starting development server
- Database migrations

### **Weekly Operations**
- Data validation runs
- Salesforce synchronization
- Google Sheets operations
- Performance monitoring

### **Monthly Maintenance**
- Database backups
- Log rotation
- Dependency updates
- Configuration reviews

### **As Needed**
- Troubleshooting commands
- Emergency procedures
- Data recovery
- System diagnostics

## 🔗 **Related Documents**

- **Development Setup**: `/docs/living/Onboarding.md`
- **Technology Stack**: `/docs/living/TechStack.md`
- **System Status**: `/docs/living/Status.md`
- **Validation System**: `/docs/old/planning/salesforce-validation-technical-spec.md`

## 📝 **Ask me (examples)**

- "How do I run the validation system for a specific entity?"
- "What commands do I need to set up the development environment?"
- "How do I troubleshoot database connection issues?"
- "What are the commands for deploying to production?"
- "How do I run tests with coverage and check code quality?"

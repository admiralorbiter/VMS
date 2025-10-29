# VMS Scripts Directory

This directory contains various utility scripts for the Volunteer Management System (VMS), organized by function.

## 📁 **Script Categories**

### **CLI Tools** (`cli/`)
Primary user-facing command-line tools:
- **`manage_imports.py`** - One-click sequential importer (moved from repo root)
- **`monitor_import_health.py`** - Post-import health checks (moved from repo root)

Usage examples:
```bash
# Sequential import
python scripts/cli/manage_imports.py --sequential --base-url http://localhost:5050

# Health check after imports
python scripts/cli/monitor_import_health.py
```

### **Administrative** (`admin/`)
Setup and administrative scripts:
- **`create_admin.py`** - Create initial admin user
- **`create_kck_viewer.py`** - Create KCK viewer user
- **`setup_encryption_key.py`** - Encryption key setup

### **Data Management** (`data/`)
Data import, copy, and synchronization utilities:
- **`copy_bugs.py`** - Bug report data import
- **`copy_google_sheets.py`** - Google Sheets data import utilities
- **`copy_students.py`** - Student data import and management
- **`copy_users.py`** - User data import and management
- **`copy_users_to_voluntold.py`** - User data export to Voluntold
- **`sync_script.py`** - Data synchronization utilities

### **Maintenance** (`maintenance/`)
Data quality, optimization, and scanning tools:
- **`mark_excluded_volunteers.py`** - Volunteer exclusion management
- **`optimize_recent_volunteers.py`** - Optimize recent volunteer records
- **`optimize_volunteers_by_event.py`** - Optimize volunteers by event
- **`scan_event_student_duplicates.py`** - Duplicate detection and scanning

### **Automation** (`automation/`)
Scheduled/cron scripts and wrappers:
- **`nightly_import_no_students.cmd`** - Windows nightly import wrapper
- **`nightly_import_no_students.sh`** - Unix/Linux/Mac nightly import wrapper

### **Daily Imports** (`daily_imports/`)
Critical nightly import scripts (paths preserved for cron/task schedulers):
- **`daily_imports.py --daily`** - Main daily Salesforce import script
  - ⚠️ **Critical nightly path**: `scripts/daily_imports/daily_imports.py --daily`
- **`run_virtual_import_2025_26_standalone.py`** - Virtual session import for 2025-2026 academic year
  - ⚠️ **Critical nightly path**: `scripts/daily_imports/run_virtual_import_2025_26_standalone.py`

### **Utilities** (`utilities/`)
General utility scripts:
- **`apply_sql.py`** - Apply SQL scripts
- **`pythonanywhere_cache_manager.py`** - PythonAnywhere cache management
- **`verify_sql_changes.py`** - Verify SQL changes

### **Validation System** (`validation/`)
Salesforce data validation tools:
- **`run_validation.py`** - Main CLI interface for Salesforce data validation
- **`test_validation_*.py`** - Test scripts for validation system
- **`run_validation.bat`** - Windows batch wrapper for validation commands
- **`run_validation.sh`** - Unix/Linux/Mac shell wrapper for validation commands

### **Other Directories**
- **`performance/`** - Performance testing and profiling
- **`sql/`** - SQL scripts and migrations

## 🚀 **Quick Start**

### **CLI Tools**
```bash
# Sequential import
python scripts/cli/manage_imports.py --sequential --base-url http://localhost:5050

# Health check
python scripts/cli/monitor_import_health.py
```

### **Admin Setup**
```bash
# Create admin user
python scripts/admin/create_admin.py

# Setup encryption
python scripts/admin/setup_encryption_key.py
```

### **Data Import**
```bash
# Import from Google Sheets
python scripts/data/copy_google_sheets.py

# Import students
python scripts/data/copy_students.py
```

### **Validation System**
```bash
# From project root
scripts\validation\run_validation.bat test          # Windows
./scripts/validation/run_validation.sh test        # Unix/Linux/Mac

# Or directly
python scripts/validation/run_validation.py --help
```

## 📝 **Notes**

- Most scripts should be run from the **project root directory**
- Scripts in subdirectories use proper sys.path adjustments to import app modules
- Critical nightly scripts:
  - `scripts/daily_imports/daily_imports.py --daily`
  - `scripts/daily_imports/run_virtual_import_2025_26_standalone.py`
- Use the wrapper scripts (`.bat`/`.sh`) for easier command execution
- Check individual script documentation for specific usage instructions
- See `daily_imports/DAILY_IMPORTS_README.md` for detailed daily import documentation

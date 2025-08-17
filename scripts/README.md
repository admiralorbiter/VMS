# VMS Scripts Directory

This directory contains various utility scripts for the Volunteer Management System (VMS).

## 📁 **Script Categories**

### **Validation System** (`validation/`)
- **`run_validation.py`** - Main CLI interface for Salesforce data validation
- **`test_validation_*.py`** - Test scripts for validation system
- **`run_validation.bat`** - Windows batch wrapper for validation commands
- **`run_validation.sh`** - Unix/Linux/Mac shell wrapper for validation commands

### **Data Management**
- **`copy_google_sheets.py`** - Google Sheets data import utilities
- **`copy_students.py`** - Student data import and management
- **`copy_users.py`** - User data import and management
- **`sync_script.py`** - Data synchronization utilities

### **Administrative**
- **`create_admin.py`** - Create initial admin user
- **`setup_encryption_key.py`** - Encryption key setup
- **`mark_excluded_volunteers.py`** - Volunteer exclusion management

### **Data Quality**
- **`scan_event_student_duplicates.py`** - Duplicate detection and scanning

### **Automation**
- **`nightly_import_no_students.cmd`** - Windows nightly import script
- **`nightly_import_no_students.sh`** - Unix/Linux/Mac nightly import script

## 🚀 **Quick Start**

### **Validation System**
```bash
# From project root
scripts\validation\run_validation.bat test          # Windows
./scripts/validation/run_validation.sh test        # Unix/Linux/Mac

# Or directly
python scripts/validation/run_validation.py --help
```

### **Admin Setup**
```bash
# Create admin user
python scripts/create_admin.py

# Setup encryption
python scripts/setup_encryption_key.py
```

### **Data Import**
```bash
# Import from Google Sheets
python scripts/copy_google_sheets.py

# Import students
python scripts/copy_students.py
```

## 📝 **Notes**

- Most scripts should be run from the **project root directory**
- Validation scripts are now organized in the `validation/` subdirectory
- Use the wrapper scripts (`.bat`/`.sh`) for easier command execution
- Check individual script documentation for specific usage instructions

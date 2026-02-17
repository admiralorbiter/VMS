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

### **Synthetic Data Generation** (`generate_synthetic_data.py`)
Generate realistic synthetic data for testing and demos:
- **`generate_synthetic_data.py`** - Main synthetic data generator script
  - Creates test data matching all SQLAlchemy models and relationships
  - Supports deterministic generation, size presets, and edge case modes
  - Uses SQLAlchemy ORM to ensure model defaults and validators run

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

### **Synthetic Data Generation**
```bash
# Generate medium-sized demo dataset
python scripts/generate_synthetic_data.py --size medium --mode demo

# Generate large dataset with specific seed (deterministic)
python scripts/generate_synthetic_data.py --seed 123 --size large --mode demo

# Generate edge case dataset (boundary conditions, NULLs, etc.)
python scripts/generate_synthetic_data.py --size medium --mode edge

# Custom counts per model
python scripts/generate_synthetic_data.py --counts volunteer=200 event=100 school=50

# Clear existing data and regenerate
python scripts/generate_synthetic_data.py --reset --size small --mode demo
```

## 📊 **Synthetic Data Generator**

The `generate_synthetic_data.py` script creates realistic synthetic data for testing and demos, matching all SQLAlchemy models and relationships in the system.

### **How to Run**

Run from the project root directory:

```bash
python scripts/generate_synthetic_data.py [options]
```

### **Options/Flags**

| Flag | Description | Example |
|------|-------------|---------|
| `--seed SEED` | Random seed for deterministic generation (default: random) | `--seed 123` |
| `--size SIZE` | Dataset size preset: `small`, `medium`, or `large` (default: `medium`) | `--size large` |
| `--mode MODE` | Generation mode: `demo` (happy path) or `edge` (boundary conditions) | `--mode edge` |
| `--counts MODEL=N` | Custom counts per model (can be used multiple times) | `--counts volunteer=200 event=100` |
| `--reset` | Clear existing data before generating (USE WITH CAUTION) | `--reset` |

### **Examples**

```bash
# Generate medium-sized demo dataset (happy path, realistic data)
python scripts/generate_synthetic_data.py --size medium --mode demo

# Generate large dataset with specific seed (deterministic - same seed = same data)
python scripts/generate_synthetic_data.py --seed 123 --size large --mode demo

# Generate edge case dataset (boundary conditions, NULLs, max-length strings, etc.)
python scripts/generate_synthetic_data.py --size medium --mode edge

# Custom counts per model
python scripts/generate_synthetic_data.py --counts volunteer=200 event=100 school=50

# Clear existing data and regenerate
python scripts/generate_synthetic_data.py --reset --size small --mode demo

# Combine options
python scripts/generate_synthetic_data.py --seed 42 --size large --mode edge --counts volunteer=500
```

### **What Data is Created**

The generator creates data for **core models** used in main user-facing features:

**Core Models (17 total):**
- **Skill** - Professional skills
- **District** - School districts
- **Organization** - Companies and organizations
- **School** - Schools assigned to districts
- **Class** - Academic classes/cohorts
- **Tenant** - Multi-tenant platform configuration
- **User** - User accounts with authentication
- **Volunteer** - Volunteer profiles (inherits from Contact)
- **Teacher** - Teacher profiles (inherits from Contact)
- **Student** - Student records (inherits from Contact)
- **Event** - Events and sessions
- **EventTeacher** - Teacher-event associations
- **EventParticipation** - Volunteer participation in events
- **EventAttendanceDetail** - Detailed attendance tracking
- **VolunteerSkill** - Volunteer-skill relationships
- **VolunteerOrganization** - Volunteer-organization relationships
- **Engagement** - Volunteer engagement activities
- **History** - Activity history and notes

**Size Presets:**

| Size | Districts | Schools | Classes | Teachers | Volunteers | Students | Events | Engagements | History |
|------|-----------|---------|---------|----------|------------|----------|--------|-------------|---------|
| `small` | 2 | 5 | 10 | 10 | 15 | 20 | 10 | 20 | 15 |
| `medium` | 5 | 15 | 30 | 30 | 50 | 100 | 30 | 50 | 40 |
| `large` | 10 | 50 | 100 | 100 | 200 | 500 | 100 | 200 | 150 |

**Note:** This covers core user-facing features. Admin/internal models (BugReport, AuditLog, SyncLog, etc.) are not included as they're not needed for demos.

### **How to Reset/Clean**

**Option 1: Use `--reset` flag (Recommended)**
```bash
python scripts/generate_synthetic_data.py --reset --size small --mode demo
```
This will prompt for confirmation before clearing data.

**Option 2: Manual database reset**
If you need to completely reset the database:
```bash
# Delete the database file (SQLite)
rm instance/vms.db  # Unix/Linux/Mac
del instance\vms.db  # Windows

# Then run migrations to recreate
flask db upgrade
```

**Option 4: Clear specific tables**
You can manually clear specific tables using SQL or the Flask shell:
```python
from app import create_app
from models import db
from models.volunteer import Skill
from models.district_model import District

app = create_app()
with app.app_context():
    Skill.query.delete()
    District.query.delete()
    # ... delete other models
    db.session.commit()
```

### **Features**

- ✅ **Deterministic Generation**: Same seed produces identical data
- ✅ **Size Presets**: Quick setup with small/medium/large datasets
- ✅ **Mode Switching**: Demo mode (clean data) vs Edge mode (boundary conditions)
- ✅ **Custom Counts**: Override presets with specific model counts
- ✅ **SQLAlchemy ORM**: Uses model classes so defaults and validators run
- ✅ **Flask App Context**: Proper Flask application context for database operations
- ✅ **Idempotent**: Can run multiple times (skips existing records)

### **Implementation Status**

**Completed:**
- ✅ Foundation (CLI, app context, seed handling)
- ✅ Core models (17 models covering main user flows)
- ✅ Relationships (many-to-many, one-to-many)
- ✅ Enum/status value coverage
- ✅ Summary output
- ✅ Reset functionality

**Note:** Database schema must be up-to-date. If you encounter missing column errors, run:
```bash
python scripts/fix_database_schema.py
```
This will add missing columns like `tenant_role`, `pathful_user_id`, etc.

## 📝 **Notes**

- Most scripts should be run from the **project root directory**
- Scripts in subdirectories use proper sys.path adjustments to import app modules
- Critical nightly scripts:
  - `scripts/daily_imports/daily_imports.py --daily`
  - `scripts/daily_imports/run_virtual_import_2025_26_standalone.py`
- Use the wrapper scripts (`.bat`/`.sh`) for easier command execution
- Check individual script documentation for specific usage instructions
- See `daily_imports/DAILY_IMPORTS_README.md` for detailed daily import documentation

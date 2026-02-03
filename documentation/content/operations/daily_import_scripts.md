# Daily Imports Scripts

Scripts for running daily imports on PythonAnywhere. These scripts directly call VMS import functions without needing HTTP requests.

## Scripts

- **`daily_imports.py`** - Main daily Salesforce import script
- **`run_virtual_import_2025_26_standalone.py`** - Virtual session import for 2025-2026 academic year

## Quick Start

### 1. Set up environment variables
Create a `.env` file in your project root:
```bash
# Required - Salesforce credentials
SF_USERNAME=your-salesforce-username
SF_PASSWORD=your-salesforce-password
SF_SECURITY_TOKEN=your-salesforce-security-token
SF_DOMAIN=login  # or 'test' for sandbox

# Optional
IMPORT_LOG_FILE=logs/daily_imports.log
LOG_LEVEL=INFO
STUDENTS_CHUNK_SIZE=2000
STUDENTS_SLEEP_MS=200
```

### 2. Run the scripts

#### Daily Salesforce Imports
```bash
# Daily imports (organizations, volunteers, affiliations, events, history)
python scripts/daily_imports/daily_imports.py --daily

# Full imports (everything)
python scripts/daily_imports/daily_imports.py --full

# Only specific imports
python scripts/daily_imports/daily_imports.py --only organizations,volunteers

# Test without running
python scripts/daily_imports/daily_imports.py --dry-run

# Validate configuration
python scripts/daily_imports/daily_imports.py --validate
```

#### Virtual Session Import
```bash
# Import virtual sessions for 2025-2026 academic year
python scripts/daily_imports/run_virtual_import_2025_26_standalone.py
```

## PythonAnywhere Setup

1. Upload both scripts to your project `scripts/daily_imports/` directory
2. Create scheduled tasks:

   **Daily Salesforce Imports:**
   - Command: `cd /home/yourusername/mysite && python scripts/daily_imports/daily_imports.py --daily`
   - Schedule: Daily at 2:00 AM

   **Virtual Session Import:**
   - Command: `cd /home/yourusername/mysite && python scripts/daily_imports/run_virtual_import_2025_26_standalone.py`
   - Schedule: As needed (often daily or weekly)

## Import Sequence

The script runs imports in this order:

1. **Organizations** - Import organization data
2. **Volunteers** - Import volunteer data
3. **Affiliations** - Import volunteer-organization relationships
4. **Events** - Import event data
5. **History** - Import activity history
6. **Schools** - Import school data
7. **Classes** - Import class data
8. **Teachers** - Import teacher data
9. **Student Participations** - Import student participation data
10. **Students** - Import student data (chunked)
11. **Sync Unaffiliated Events** - Sync events based on students

## Commands

- `--daily` - Run daily imports (organizations, volunteers, affiliations, events, history)
- `--weekly` - Run weekly imports (daily + schools, classes, teachers)
- `--full` - Run all imports
- `--students` - Run only student imports
- `--only STEPS` - Run only specific steps (comma-separated)
- `--exclude STEPS` - Skip specific steps
- `--dry-run` - Show what would be imported without running
- `--validate` - Validate configuration
- `--config` - Show current configuration

## Script Details

### daily_imports.py

Main daily Salesforce import script. Handles all entity imports (organizations, volunteers, events, etc.).

**Note:** This script requires proper authentication setup. Ensure the admin user has `scope_type="global"` set in the database.

### run_virtual_import_2025_26_standalone.py

Standalone virtual session import script for the 2025-2026 academic year. Imports virtual session data from Google Sheets configured in the VMS admin panel.

**Features:**
- Imports virtual session data from Google Sheets
- Works standalone without Flask app running
- Processes teachers, presenters, and events
- Creates or updates districts and schools
- Handles errors gracefully with rollback

**Requirements:**
- Valid Google Sheet configuration for 2025-2026 academic year (configured in admin panel)
- Database connection and models
- All required dependencies installed

## Troubleshooting

**Daily Imports Log:**
```bash
tail -f logs/daily_imports.log
```

**Debug mode:**
```bash
python scripts/daily_imports/daily_imports.py --daily --log-level DEBUG
```

**Virtual Import Issues:**
- Ensure Google Sheet is configured in admin panel for academic year "2025-2026"
- Check that the sheet has proper permissions and is publicly readable for CSV export
- Verify database connection is working

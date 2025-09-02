# Daily Imports Script

A single-file Python script for running daily Salesforce imports on PythonAnywhere. This script directly calls the VMS import functions without needing HTTP requests.

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

### 2. Run the script
```bash
# Daily imports (organizations, volunteers, affiliations, events, history)
python daily_imports.py --daily

# Full imports (everything)
python daily_imports.py --full

# Only specific imports
python daily_imports.py --only organizations,volunteers

# Test without running
python daily_imports.py --dry-run

# Validate configuration
python daily_imports.py --validate
```

## PythonAnywhere Setup

1. Upload `daily_imports.py` to your project directory
2. Create a scheduled task:
   - Command: `cd /home/yourusername/mysite && python daily_imports.py --daily`
   - Schedule: Daily at 2:00 AM

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

## Troubleshooting

Check logs: `tail -f logs/daily_imports.log`

Debug mode: `python daily_imports.py --daily --log-level DEBUG`

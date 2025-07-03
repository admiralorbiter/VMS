# Google Sheets Management Feature

## Overview

This feature allows administrators to manage Google Sheet IDs for different academic years, enabling the system to import virtual events from multiple Google Sheets based on the academic year. The sheet IDs are encrypted and stored securely in the database.

## Features

- **CRUD Operations**: Create, Read, Update, and Delete Google Sheet entries
- **Academic Year Management**: Associate sheets with specific academic years (e.g., "2023-2024")
- **Encryption**: Google Sheet IDs are encrypted using Fernet encryption
- **Active/Inactive Status**: Mark sheets as active or inactive
- **User Tracking**: Track who created each sheet entry
- **Backward Compatibility**: Falls back to environment variable if no database entry exists

## Setup

### 1. Install Dependencies

Add the cryptography library to your requirements:

```bash
pip install cryptography
```

### 2. Set Up Encryption Key

Generate an encryption key and add it to your environment variables:

```bash
# Generate a new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to your .env file
ENCRYPTION_KEY=your_generated_key_here
```

### 3. Create Database Table

Run the migration script to create the google_sheets table:

```bash
python create_google_sheets_table.py
```

## Usage

### Accessing the Management Interface

1. Log in as an administrator
2. Go to the Admin Dashboard
3. Click "Manage Google Sheets" in the System Management section

### Adding a New Google Sheet

1. Click "Add New Google Sheet"
2. Fill in the required fields:
   - **Academic Year**: Format as YYYY-YYYY (e.g., "2023-2024")
   - **Sheet Name**: Human-readable name for the sheet
   - **Google Sheet ID**: The ID from the Google Sheets URL
   - **Description**: Optional description
   - **Status**: Active or Inactive
3. Click "Save"

### Finding Your Google Sheet ID

The Google Sheet ID is the long string in your Google Sheets URL:

```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit
```

### Editing a Sheet

1. Click the "Edit" button on any sheet card
2. Modify the desired fields
3. Click "Save"

Note: For security reasons, the Google Sheet ID field is not populated when editing. You must re-enter it if you want to change it.

### Deleting a Sheet

1. Click the "Delete" button on any sheet card
2. Confirm the deletion

## API Endpoints

### GET /google-sheets
Display the Google Sheets management page

### POST /google-sheets
Create a new Google Sheet entry

**Request Body:**
```json
{
    "academic_year": "2023-2024",
    "sheet_id": "your_sheet_id_here",
    "sheet_name": "Virtual Events 2023-2024",
    "description": "Optional description",
    "is_active": true
}
```

### PUT /google-sheets/{id}
Update an existing Google Sheet entry

### DELETE /google-sheets/{id}
Delete a Google Sheet entry

### GET /google-sheets/{id}
Get a specific Google Sheet entry

## Virtual Event Import

The virtual event import now automatically uses the appropriate Google Sheet based on the academic year:

1. When importing virtual events, the system determines the current academic year
2. It looks for an active Google Sheet entry for that academic year
3. If found, it uses the decrypted sheet ID from the database
4. If not found, it falls back to the `GOOGLE_SHEET_ID` environment variable

## Academic Year Logic

Academic years run from July 1st to June 30th:
- July 2023 to June 2024 = "2023-2024"
- July 2024 to June 2025 = "2024-2025"

## Security

- Google Sheet IDs are encrypted using Fernet encryption
- The encryption key is stored in environment variables
- Sheet IDs are never displayed in plain text in the UI
- Access is restricted to administrators only

## Database Schema

```sql
CREATE TABLE google_sheets (
    id INTEGER PRIMARY KEY,
    academic_year VARCHAR(10) NOT NULL UNIQUE,
    sheet_id TEXT NOT NULL,  -- Encrypted
    sheet_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id)
);
```

## Troubleshooting

### Encryption Key Issues

If you see encryption errors:
1. Ensure `ENCRYPTION_KEY` is set in your environment
2. The key must be the same for encryption and decryption
3. If you change the key, existing encrypted data will not be readable

### Import Failures

If virtual event imports fail:
1. Check that a Google Sheet is configured for the current academic year
2. Verify the sheet ID is correct
3. Ensure the sheet is marked as active
4. Check that the sheet is publicly accessible or shared appropriately

### Database Issues

If the table creation fails:
1. Ensure you have database write permissions
2. Check that the migration script has access to your database
3. Verify that the `cryptography` library is installed 
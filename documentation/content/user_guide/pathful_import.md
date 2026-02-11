# Pathful Import Guide

This guide covers importing virtual session data from Pathful into Polaris, resolving unmatched records, and managing user profiles.

> [!NOTE]
> **Transition from Legacy Workflow**
> The Pathful direct import replaces the old Google Sheets workflow. You no longer need to manually reformat data—upload Pathful exports directly.

---

## Quick Navigation

<div class="qn-grid">
<div class="qn-card">
<div class="qn-icon"><i class="fas fa-file-import"></i></div>
<div class="qn-label"><a href="#import-types">Import Types</a></div>
</div>
<div class="qn-card">
<div class="qn-icon"><i class="fas fa-exclamation-triangle"></i></div>
<div class="qn-label"><a href="#unmatched-records">Unmatched Records</a></div>
</div>
<div class="qn-card">
<div class="qn-icon"><i class="fas fa-users"></i></div>
<div class="qn-label"><a href="#user-profiles">User Profiles</a></div>
</div>
</div>

---

## Getting Started

### Accessing Pathful Import

1. Navigate to **Virtual** in the main menu
2. Click **Pathful Imports** in the navigation

### Obtaining Pathful Exports

Download exports from the Pathful platform:

1. Log in to [Pathful](https://pathful.com) Admin
2. Go to **Reports** → **Export Data**
3. Select the report type:
   - **Session Report** — Session attendance
   - **Events List** — Event metadata
   - **User Report** — User profiles
4. Download as Excel (.xlsx)

---

## Weekly Workflow (Recommended)

The Pathful import is designed to work alongside manual event creation in Polaris. Here's the recommended workflow:

```
┌─────────────────────────────────────────────────────────────────┐
│  POLARIS (Manual)              │  PATHFUL (Source of Truth)    │
├────────────────────────────────┼────────────────────────────────┤
│  1. Staff creates event        │                                │
│     - Title, Date, Teachers    │                                │
│                                │  2. Session occurs on Pathful  │
│                                │     (attendance is recorded)   │
│                                │                                │
│  3. Weekly: Import Session     │                                │
│     Report from Pathful        │                                │
│     → Matches existing events  │                                │
│     → Updates attendance data  │                                │
│     → Links teachers/volunteers│                                │
└─────────────────────────────────────────────────────────────────┘
```

### How Session Matching Works

When importing, the system **automatically matches** to existing Polaris sessions:

| Priority | Match Method | Action |
|----------|--------------|--------|
| 1 | Pathful Session ID | Updates existing event |
| 2 | Title + Date | Links and updates existing event |
| 3 | No match | Creates new event |

> [!TIP]
> **Title Consistency**
> For best matching, ensure the session title in Polaris matches what will appear in Pathful. Matching is case-insensitive.

### Weekly Import Steps

1. **Download** Session Report from Pathful (weekly or bi-weekly)
2. **Upload** to Polaris via **Virtual → Pathful Imports**
3. **Review** unmatched records (if any)
4. Attendance data is now synced!

---

## Import Types

Polaris supports three Pathful export types. Import them in this recommended order:

| Order | Type | Purpose |
|-------|------|---------|
| 1 | Session Report | Sessions, teachers, volunteers, attendance |
| 2 | Events List | Event metadata updates |
| 3 | User Report | User profiles for matching |

### Session Report Import

**Route:** `/virtual/pathful/import`

The Session Report is the primary import—it creates sessions and tracks participation.

**Steps:**
1. Click **"Choose File"** and select your Session Report (.xlsx)
2. Click **"Upload & Process"**
3. Review the import summary showing:
   - Sessions created/updated
   - Teachers matched
   - Volunteers matched
   - Unmatched records

**What Gets Imported:**
- Session ID, title, date, status
- Teacher names (matched to TeacherProgress)
- Presenter names (matched to Volunteer)
- Student attendance counts

> [!TIP]
> Imports are **idempotent**—you can safely re-import the same file without duplicating data.

---

### Events List Import

**Route:** `/virtual/pathful/import-events`

Updates event metadata for previously imported sessions.

**Steps:**
1. Navigate to **Events List Import** tab
2. Upload your Events List export
3. System updates matching sessions by Session ID

---

### User Report Import

**Route:** `/virtual/pathful/import-users`

Imports user profile data (email, school, organization) used to enhance unmatched record resolution.

**Steps:**
1. Navigate to **User Profiles** tab
2. Click **"Import User Report"**
3. Upload the User Report export

**What Gets Imported:**
- User Auth ID (for linking)
- Login email
- School / District / Organization
- Role (Educator, Professional)

---

## Unmatched Records

**Route:** `/virtual/pathful/unmatched`

When imports can't automatically match a teacher or volunteer, records are queued for manual resolution.

### Understanding the Dashboard

**Summary Cards** show:
- **Pending** — Records awaiting resolution
- **Resolved** — Successfully matched records
- **Ignored** — Records marked as not applicable

**Filters:**
- Status: Pending / Resolved / Ignored / All
- Type: Teachers / Volunteers

### Resolving Individual Records

Each unmatched record shows:
- Name (from Pathful)
- Email (from User Profile, if available)
- School (from User Profile)
- Match Suggestions (auto-detected by email)

**To resolve a single record:**

1. **Use Match Suggestions** (if available):
   - Click the green **"X Found"** button
   - Select the matching teacher or volunteer
   - Record is automatically resolved

2. **Ignore** (if not applicable):
   - Click **Actions** → **Ignore**
   - Record is removed from pending queue

### Bulk Resolution

For processing multiple records at once:

1. Check the boxes next to records
2. The bulk action bar appears
3. Click **"Ignore Selected"**
4. Up to 100 records processed per action

> [!IMPORTANT]
> Bulk matching is not yet available—only bulk ignore is supported.

---

## User Profiles

**Route:** `/virtual/pathful/users`

View and manage imported user profiles.

### Features

- **Filter by Role:** Educator, Professional
- **Filter by Link Status:** Linked, Not Linked
- **Search:** Name, email, school, User Auth ID

### Auto-Linking

When a User Profile's `pathful_user_id` matches an existing TeacherProgress record, the system auto-links them during import.

---

## Troubleshooting

### Import Fails with "Invalid File"
- Ensure file is Excel format (.xlsx or .xls)
- Check that required columns exist (Session ID, Name, etc.)

### High Number of Unmatched Records
1. Import the **User Report** first
2. This enables email-based match suggestions
3. Use bulk ignore for known non-matches

### Duplicate Sessions
- This shouldn't happen—imports are idempotent
- If it does, check if Session IDs are missing from the export

---

## Technical Traceability

| Component | References |
|-----------|------------|
| **User Stories** | [US-304](user_stories#us-304), [US-306](user_stories#us-306) |
| **Requirements** | [FR-VIRTUAL-206](requirements#fr-virtual-206), [FR-VIRTUAL-207](requirements#fr-virtual-207) |
| **Dev Docs** | [Pathful Import Deployment](dev/pathful_import_deployment) |

---

*Last updated: January 30, 2026*

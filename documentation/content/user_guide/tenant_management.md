# Tenant Management Guide

**PrepKC Admin guide for managing district tenants**

> [!NOTE]
> This guide covers tenant lifecycle management for PrepKC administrators. Tenants are isolated district environments with their own databases and users.

## Tenant Overview

Each tenant represents a partner district with:
- **Isolated database** - Separate SQLite file
- **District users** - Staff with tenant-scoped access
- **API access** - Public event API for website integration
- **Feature flags** - Controlled feature rollout

---

## Creating a New Tenant

### Prerequisites

1. District partnership agreement finalized
2. District contact identified (initial admin)
3. Schools confirmed in reference data

### Step-by-Step

1. Navigate to **Admin** → **Tenants**
2. Click **Create Tenant**
3. Fill in required fields:
   - **Name** - District display name (e.g., "KCKPS")
   - **Slug** - URL identifier (e.g., "kckps") - lowercase, no spaces
   - **District** - Link to existing District record (optional)
4. Configure feature flags:
   - ☑️ Events enabled
   - ☑️ Volunteers enabled
   - ☐ Recruitment enabled (Phase 4)
   - ☐ PrepKC visibility enabled (Phase 5)
5. Click **Create Tenant**

**System will automatically:**
- Create new SQLite database (`polaris_{slug}.db`)
- Run migrations to create schema
- Copy reference data (schools, skills, career types)
- Generate initial API key

### Creating Initial Admin User

1. After tenant creation, click **Add User**
2. Enter district admin details:
   - Email (login identifier)
   - First Name, Last Name
   - Password (or generate temporary)
3. Set role to **District Admin**
4. Click **Create User**
5. System sends welcome email with login instructions

---

## Managing Existing Tenants

### Viewing Tenant List

1. Navigate to **Admin** → **Tenants**
2. See all tenants with status indicators

### Editing Tenant Settings

1. Click on tenant name
2. Update fields as needed:
   - Name
   - Feature flags
   - Allowed CORS origins
3. Click **Save**

### Deactivating a Tenant

1. Click on tenant name
2. Toggle **Active** to Off
3. Confirm deactivation

> [!WARNING]
> Deactivated tenants cannot be accessed. Users will see an error message.

### Reactivating a Tenant

1. Click on tenant name
2. Toggle **Active** to On
3. Confirm reactivation

---

## Cross-Tenant Support Access

### Switching Tenant Context

1. Click your username in the header
2. Select **Switch Tenant**
3. Choose target tenant from list
4. Confirm switch

You now operate within that tenant's context and see their data.

### Returning to PrepKC

1. Click your username in the header
2. Select **Return to PrepKC**

### Audit Trail

All actions while in a tenant context are logged:
- Your identity (PrepKC admin username)
- Target tenant
- Action performed
- Timestamp

---

## Teacher Roster Import

### Importing Teacher Lists

Tenant admins can import their district's teacher roster for progress tracking.

1. Navigate to **Teachers** → **Import Roster**
2. Choose import method:
   - **CSV Upload** - Upload a local CSV file
   - **Google Sheet** - Paste a Google Sheets URL
3. Required columns: **Building** (school), **Name**, **Email**
4. Optional columns: **Grade**
5. Click **Import**

**System will:**
- Match schools to existing Building records
- Create new teachers or update existing (by email)
- Display import summary with counts

### Import Troubleshooting

| Issue | Resolution |
|-------|------------|
| "School not found" | Verify school name matches exactly, or add missing school |
| Duplicate emails | System updates existing teacher record, no duplicates created |
| Permission denied (Google Sheet) | Share sheet with service account or make public |

---

## Teacher Usage Dashboard

### Viewing Session Counts

Track how many virtual sessions each teacher has attended.

1. Navigate to **Teachers** → **Usage Dashboard**
2. View data grouped by building with:
   - Teacher name
   - Session count
   - School name
3. Use **Semester Filter** to view Fall or Spring only
4. Click **Export Excel** for downloadable report

### Understanding the Data

- **Sessions Matched**: Teachers matched to Pathful import data by name
- **Grouped by Building**: Aggregated totals per school
- **Semester Filtering**: Fall (Aug-Dec), Spring (Jan-May)

---

## API Key Management

### Viewing Tenant API Key

1. Navigate to **Admin** → **Tenants**
2. Click on tenant
3. Scroll to **API Settings**
4. Click **Show Key** (one-time view)

### Rotating API Key

1. Click on tenant
2. Scroll to **API Settings**
3. Click **Rotate Key**
4. Confirm rotation

> [!CAUTION]
> The old key is immediately invalidated. Notify the district to update their integration.

---

## Troubleshooting

### Tenant Creation Failed

**Symptoms:** Error message during tenant creation

**Resolution:**
1. Check if slug is unique (not already used)
2. Verify database path is writable
3. Check logs for migration errors

### User Cannot Log In

**Symptoms:** District user reports login failure

**Resolution:**
1. Switch to tenant context
2. Navigate to **Settings** → **Users**
3. Verify user exists and is active
4. Reset password if needed

### API Returns 401 Unauthorized

**Symptoms:** District reports API not working

**Resolution:**
1. Verify API key is correct
2. Check if key was rotated
3. Verify tenant is active

---

## Related Documentation

- **Development Phases:** [District Suite Phases](district_suite_phases)
- **Requirements:** [Tenant Infrastructure](requirements#tenant-infrastructure)
- **Architecture:** [Multi-Tenancy Architecture](architecture#multi-tenancy-architecture-district-suite)

---

*Last updated: February 2026*
*Version: 1.1*

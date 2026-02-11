# District-Scoped User Management

Administrators can create users with access limited to specific districts or schools, providing fine-grained access control for external stakeholders.

## Scope Types

| Scope | Access | Use Case |
|-------|--------|----------|
| **Global** (Default) | All districts and schools | Internal staff, administrators |
| **District** | Specific assigned districts only | External stakeholders, auditors |
| **School** (Future) | Specific schools only | School-level stakeholders |

---

## Creating District-Scoped Users

### Via Admin Panel

1. **Navigate to Admin Panel** → `/admin`
2. **Access User Creation** → "Create New User" section
3. **Fill basic info**: Username, Email, Password, Security Level
4. **Configure District Scope**:
   - Set **Access Scope** to "District-Scoped"
   - Select districts from multi-select dropdown (Ctrl/Cmd for multiple)
5. **Create User** → Click "Add User"

### Example Configurations

| User Type | Scope | Districts | Result |
|-----------|-------|-----------|--------|
| External Partner | District | ["District A", "District B"] | Can view data for both districts |
| Single Auditor | District | ["Kansas City Kansas Public Schools"] | KCK data only |
| Regional Manager | District | ["District A", "B", "C"] | All three districts |

---

## User Experience

### Login Behavior

| Scope Type | Redirect After Login |
|------------|---------------------|
| District-scoped | First assigned district's teacher progress page |
| Global | Main dashboard |

### Navigation

| Scope Type | Visible Navigation |
|------------|-------------------|
| District-scoped | District Progress link, Logout |
| Global | Full navigation menu |

### Data Access

- District-scoped users can only access reports for their assigned districts
- Attempting other districts returns **403 Access Denied**
- Global users have full access

---

## Managing Existing Users

### Editing User Scope

1. Go to Admin panel
2. Find user in list → Click "Edit"
3. Update scope type and/or district list
4. Save changes

### KCK Viewer Migration

Existing KCK viewers (`security_level = -1`) are automatically migrated to district-scoped users with "Kansas City Kansas Public Schools" access.

---

## Security

### Access Control Mechanisms

| Mechanism | Description |
|-----------|-------------|
| Route decorator | `@district_scoped_required` enforces scoping |
| Query filtering | Database queries auto-filter by allowed districts |
| UI elements | Hidden/shown based on user scope |
| Admin override | Global users bypass all restrictions |

### API Integration

District scoping applies to API access:

```python
# District-scoped user accessing their district
GET /api/reports/district/Kansas%20City%20Kansas%20Public%20Schools
# Returns: 200 OK

# Same user accessing unauthorized district
GET /api/reports/district/Other%20District
# Returns: 403 Forbidden
```

---

## Troubleshooting

### User Cannot Access Expected Data

1. Verify user has correct scope type
2. Confirm user is assigned to correct districts
3. Check route has proper `@district_scoped_required` decorator

### Login Redirect Issues

1. User must have at least one district assigned
2. District names must match exactly (case-sensitive)
3. Verify `allowed_districts` contains valid JSON

### Admin Panel Issues

1. Check scope type dropdown JavaScript
2. Verify districts load in admin template
3. Confirm district selections are submitted

---

## Best Practices

### User Creation

- Assign minimum required districts for user's role
- Use descriptive usernames indicating organization
- Set appropriate security levels based on needs

### Scope Management

- Regularly review user access
- Remove access when partnerships end
- Document scope decisions for audits

### Security

- Never assign global scope unless necessary
- Regularly audit user access and permissions
- Use district scoping as a security boundary

---

## Technical Details

### Key Files

| Category | Files |
|----------|-------|
| **Decorator** | `utils/decorators.py` → `@district_scoped_required` |
| **User Model** | `models/user.py` → `scope_type`, `allowed_districts` |
| **Admin Routes** | `routes/admin.py` |

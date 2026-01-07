# District-Scoped User Management Guide

## Overview

The VMS system supports flexible district and school scoping for restricted-access users. This allows administrators to create users with access limited to specific districts or schools, providing fine-grained access control for external stakeholders, partner organizations, and auditors.

## Scope Types

### Global Scope (Default)
- **Access**: Full access to all districts and schools
- **Use Case**: Internal staff, administrators, managers
- **Default**: All new users are created with global scope

### District Scope
- **Access**: Limited to specific assigned districts
- **Use Case**: External stakeholders, partner organizations, district-specific auditors
- **Configuration**: Admin selects one or more districts during user creation

### School Scope (Future)
- **Access**: Limited to specific schools (not yet implemented)
- **Use Case**: School-level stakeholders, individual school auditors
- **Status**: Framework ready, implementation planned for future release

## Creating District-Scoped Users

### Via Admin Panel

1. **Navigate to Admin Panel**
   - Log in as an administrator
   - Go to `/admin`

2. **Access User Creation Form**
   - Scroll to "Create New User" section
   - Fill in basic user information:
     - Username (unique)
     - Email (unique)
     - Password
     - Security Level (role)

3. **Configure District Scope**
   - **Access Scope**: Select "District-Scoped" from dropdown
   - **Allowed Districts**: Multi-select dropdown will appear
   - Hold Ctrl/Cmd to select multiple districts
   - Select all districts the user should have access to

4. **Create User**
   - Click "Add User" button
   - User is created with district scope restrictions

### Example Scenarios

#### External Partner Access
```
User: partner@organization.org
Scope: District-Scoped
Districts: ["District A", "District B"]
Access: Can view data for District A and District B only
```

#### Single District Auditor
```
User: auditor@district.gov
Scope: District-Scoped
Districts: ["Kansas City Kansas Public Schools"]
Access: Can view KCK data only (equivalent to old KCK Viewer)
```

#### Multi-District Manager
```
User: regional.manager@org.org
Scope: District-Scoped
Districts: ["District A", "District B", "District C"]
Access: Can view data for all three districts
```

## User Experience for District-Scoped Users

### Login Behavior
- District-scoped users are automatically redirected to their first assigned district's teacher progress page
- Global users go to the main dashboard

### Navigation
- District-scoped users see simplified navigation with only:
  - District Progress link (to their assigned district)
  - Logout link
- Global users see full navigation menu

### Data Access
- District-scoped users can only access reports and data for their assigned districts
- Attempting to access other districts results in 403 Access Denied error
- Global users can access all districts

## Managing Existing Users

### Editing User Scope
1. **Access User Management**
   - Go to Admin panel
   - Find user in user list
   - Click "Edit" button

2. **Update Scope Settings**
   - Change scope type if needed
   - Add/remove districts from allowed list
   - Save changes

### Migration from KCK Viewers
Existing KCK viewers (security_level = -1) are automatically migrated to district-scoped users with access to "Kansas City Kansas Public Schools" only. No manual intervention required.

## Security Considerations

### Access Control
- District scoping is enforced at the route level using `@district_scoped_required` decorator
- Database queries are filtered based on user's allowed districts
- UI elements are hidden/shown based on user scope

### Data Isolation
- District-scoped users cannot access data from unassigned districts
- Query filtering ensures data isolation at the database level
- API endpoints respect district scoping

### Admin Override
- Global users (admins) have full access regardless of any scope restrictions
- Admins can manage all users and assign any scope configuration

## Troubleshooting

### User Cannot Access Expected Data
1. **Check User Scope**: Verify user has correct scope type
2. **Verify District Assignment**: Confirm user is assigned to the correct districts
3. **Check Route Protection**: Ensure route has proper `@district_scoped_required` decorator

### Login Redirect Issues
1. **Verify District Assignment**: User must have at least one district assigned
2. **Check District Names**: Ensure district names match exactly (case-sensitive)
3. **Test JSON Format**: Verify `allowed_districts` field contains valid JSON

### Admin Panel Issues
1. **JavaScript Errors**: Ensure scope type dropdown JavaScript is working
2. **District Loading**: Verify districts are loaded in admin template
3. **Form Submission**: Check that district selections are properly submitted

## Best Practices

### User Creation
- Always assign the minimum required districts for the user's role
- Use descriptive usernames that indicate the user's organization
- Set appropriate security levels based on actual needs

### Scope Management
- Regularly review user access to ensure it matches current requirements
- Remove access to districts when partnerships end
- Document scope decisions for audit purposes

### Security
- Never assign global scope unless absolutely necessary
- Regularly audit user access and permissions
- Use district scoping as a security boundary, not just convenience

## API Integration

### District-Scoped API Access
When using API tokens, district scoping is enforced automatically:
- Global users can access all districts via API
- District-scoped users can only access their assigned districts
- Invalid district access returns 403 Forbidden

### Example API Usage
```python
# District-scoped user accessing their district
GET /api/reports/district/Kansas%20City%20Kansas%20Public%20Schools
Authorization: Bearer <token>
# Returns: 200 OK with district data

# Same user trying to access different district
GET /api/reports/district/Other%20District
Authorization: Bearer <token>
# Returns: 403 Forbidden
```

## Future Enhancements

### School-Level Scoping
- Framework is ready for school-level access control
- Will allow users to be restricted to specific schools within districts
- Implementation planned for future release

### Advanced Permissions
- Granular permission system within districts
- Role-based access within district scope
- Time-limited access permissions

### Audit and Reporting
- Enhanced audit logs for district access
- Reports on user access patterns
- Compliance reporting for district scoping

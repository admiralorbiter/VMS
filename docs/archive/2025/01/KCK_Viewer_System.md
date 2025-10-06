# KCK Viewer User System

## Overview

The KCK Viewer system provides a restricted access user type that can only view the Kansas City Kansas Public Schools teacher progress tracking page. This system is designed for stakeholders who need access to specific district data without full system access.

## Features

### User Type: KCK Viewer (Security Level -1)
- **Restricted Access**: Can only access the KCK teacher progress page
- **Automatic Redirect**: Logs in directly to the KCK dashboard
- **Simplified Navigation**: Only shows KCK Teacher Progress and Logout options
- **Admin Management**: Can be created and managed by system administrators

### Access Control
- **Login Redirect**: KCK viewers are automatically redirected to the teacher progress page
- **Page Restrictions**: Access limited to `/reports/virtual/usage/district/Kansas City Kansas Public Schools/teacher-progress`
- **Export Access**: Can export data from the teacher progress page
- **Navigation**: Simplified navigation with only essential options

## Implementation Details

### Security Level
```python
SecurityLevel.KCK_VIEWER = -1  # Restricted access to KCK teacher progress page only
```

### Access Control Decorators
- `@kck_viewer_only`: Restricts access to KCK viewers and higher-level users
- `@kck_viewer_or_higher_required`: Allows KCK viewers and all higher security levels

### User Model Extensions
- `user.is_kck_viewer` property for easy role checking
- Updated `can_manage_user()` method to handle KCK viewer management
- Enhanced permission checking for hierarchical access

## Admin Management

### Creating KCK Viewer Users
1. Log in as an admin user
2. Navigate to the Admin panel (`/admin`)
3. In the "Create New User" section:
   - Enter username and email
   - Set password
   - Select "KCK Viewer (Restricted Access)" from the role dropdown
   - Click "Add User"

### Managing KCK Viewer Users
- **Edit**: Admins can edit KCK viewer accounts (username, email, password)
- **Delete**: Admins can delete KCK viewer accounts
- **Password Reset**: Admins can change KCK viewer passwords

## User Experience

### KCK Viewer Login Flow
1. User enters credentials on login page
2. System authenticates user
3. If user is KCK viewer, automatically redirects to:
   ```
   /reports/virtual/usage/district/Kansas City Kansas Public Schools/teacher-progress?year=2025-2026&date_from=2025-08-01&date_to=2026-07-31
   ```

### KCK Viewer Interface
- **Simplified Navigation**: Only shows "KCK Teacher Progress" and "Logout"
- **No Side Panel**: Additional admin functions are hidden
- **Focused Experience**: Direct access to district-specific data

## Technical Implementation

### Files Modified
- `models/user.py`: Added KCK_VIEWER security level and helper methods
- `routes/utils.py`: Added access control decorators
- `routes/auth/routes.py`: Updated login redirect and user creation
- `routes/reports/virtual_session.py`: Added access control to KCK routes
- `templates/management/admin.html`: Added KCK viewer option to admin panel
- `templates/nav.html`: Simplified navigation for KCK viewers

### Database Changes
- No schema changes required
- Uses existing `security_level` field with value `-1`
- Backward compatible with existing user system

## Security Considerations

### Access Restrictions
- KCK viewers cannot access any other system pages
- Navigation is limited to prevent exploration
- Export functionality is restricted to KCK data only

### Management Controls
- Only admins can create KCK viewer accounts
- Regular users cannot manage KCK viewers
- KCK viewers cannot escalate their own permissions

## Usage Examples

### Creating a KCK Viewer Account
```python
# Admin creates a new KCK viewer
from models.user import User, SecurityLevel
from werkzeug.security import generate_password_hash

kck_viewer = User(
    username='kck_viewer_1',
    email='viewer@kckps.org',
    password_hash=generate_password_hash('secure_password'),
    security_level=SecurityLevel.KCK_VIEWER,
    first_name='John',
    last_name='Doe'
)
db.session.add(kck_viewer)
db.session.commit()
```

### Checking User Type
```python
# In templates or routes
if current_user.is_kck_viewer:
    # Redirect to KCK dashboard
    return redirect(url_for('report.virtual_district_teacher_progress', ...))

# In Python code
if user.is_kck_viewer:
    # Handle KCK viewer specific logic
```

## Future Enhancements

The system is designed to be extensible for future requirements:

1. **Additional Restricted Pages**: Can add more pages accessible to KCK viewers
2. **District-Specific Views**: Can extend to other districts
3. **Custom Dashboards**: Can create specialized dashboards for different user types
4. **Reporting Access**: Can grant access to specific reports while maintaining restrictions

## Testing

To test the KCK viewer system:

1. Create a KCK viewer account through the admin panel
2. Log out and log in with the KCK viewer credentials
3. Verify automatic redirect to the KCK teacher progress page
4. Confirm limited navigation options
5. Test that other system pages are inaccessible
6. Verify export functionality works on the KCK page

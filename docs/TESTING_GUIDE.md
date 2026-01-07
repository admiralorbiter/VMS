# District Scoping Implementation - Testing Guide

## 🚀 **Quick Start Testing**

### **1. Start Your Application**
```bash
python app.py
```
Your Flask app should start on port 5050 (as configured in your system).

---

## 🧪 **Manual Testing Checklist**

### **2. Test Login Flow**

#### **District-Scoped User Login**
- **URL**: http://127.0.0.1:5050/login
- **Username**: `kcktest@gmail.com` (or any KCK viewer from the database)
- **Expected**: Should redirect to KCK teacher progress page automatically
- **Verify**: URL should contain `district/Kansas%20City%20Kansas%20Public%20Schools`

#### **Global User Login**
- **Username**: Any admin user
- **Expected**: Should redirect to main dashboard (not district page)
- **Verify**: URL should be the main index page

### **3. Test Navigation Display**

#### **District-Scoped User Navigation**
- **Login as**: District-scoped user (kcktest@gmail.com)
- **Expected Navigation**:
  - ✅ "District Progress" link
  - ✅ "Logout" link
  - ❌ Should NOT see: Volunteers, Teachers, Events, etc.
- **Verify**: Navigation is simplified and focused

#### **Global User Navigation**
- **Login as**: Admin user
- **Expected Navigation**:
  - ✅ Full navigation menu (Volunteers, Teachers, Events, etc.)
  - ✅ All admin options visible
- **Verify**: Complete navigation is available

### **4. Test Admin Panel**

#### **Access Admin Panel**
- **URL**: http://127.0.0.1:5050/admin
- **Login as**: Admin user
- **Verify**: Admin panel loads successfully

#### **Create District-Scoped User**
1. **Fill Form**:
   - Username: `test_district_user`
   - Email: `test@district.com`
   - Password: `test123`
   - Security Level: `User (0)`
   - **Access Scope**: Select `District-Scoped`

2. **District Selection**:
   - ✅ District selector should appear when "District-Scoped" is selected
   - Select one or more districts (e.g., "Kansas City Kansas Public Schools")
   - Click "Add User"

3. **Verify Creation**:
   - ✅ User created successfully
   - ✅ User appears in user list
   - ✅ Database contains correct `scope_type` and `allowed_districts`

#### **Test Created User**
1. **Logout** and login as the new district-scoped user
2. **Verify**: Should redirect to assigned district page
3. **Verify**: Navigation shows only district-specific options

### **5. Test Report Access Control**

#### **District-Scoped User Access**
- **Login as**: District-scoped user
- **Test Accessible District**:
  - Go to: `/reports/virtual/usage/district/Kansas%20City%20Kansas%20Public%20Schools/teacher-progress`
  - ✅ Should load successfully (200 OK)

#### **District-Scoped User - Access Denied**
- **Login as**: District-scoped user
- **Test Forbidden District**:
  - Go to: `/reports/virtual/usage/district/Other%20District/teacher-progress`
  - ✅ Should show 403 Access Denied error

#### **Global User Access**
- **Login as**: Admin user
- **Test Any District**:
  - ✅ Should access any district report successfully
  - ✅ No restrictions based on district

### **6. Test Backwards Compatibility**

#### **Existing KCK Viewers**
- **Login as**: Any existing KCK viewer (christopher.hamman@kckps.org, etc.)
- **Expected**: Should work exactly as before
- **Verify**:
  - ✅ Redirects to KCK district page
  - ✅ Navigation shows district-specific options
  - ✅ Can access KCK reports
  - ✅ Cannot access other districts

---

## 🔍 **Database Verification**

### **Check Migration Results**
```bash
python scripts/verify_sql_changes.py
```

**Expected Output**:
- ✅ New columns: `allowed_districts`, `scope_type`
- ✅ 7 users with `scope_type = 'district'`
- ✅ All KCK viewers migrated correctly

### **Verify User Creation**
```bash
python -c "
from app import create_app
from models.user import User
app = create_app()
with app.app_context():
    users = User.query.filter_by(scope_type='district').all()
    for user in users:
        print(f'{user.username}: {user.allowed_districts}')
"
```

---

## 🐛 **Troubleshooting Common Issues**

### **Login Redirect Not Working**
- **Check**: User has `allowed_districts` set correctly
- **Check**: JSON format is valid in database
- **Fix**: Re-run SQL migration if needed

### **Navigation Not Simplified**
- **Check**: User has `scope_type = 'district'`
- **Check**: Template is using new logic
- **Fix**: Clear browser cache and reload

### **403 Access Denied Errors**
- **Check**: Route has `@district_scoped_required` decorator
- **Check**: User is assigned to correct districts
- **Fix**: Verify district names match exactly (case-sensitive)

### **Admin Panel Issues**
- **Check**: JavaScript is enabled
- **Check**: Districts are loading in dropdown
- **Fix**: Check browser console for JavaScript errors

---

## ✅ **Success Criteria**

Your implementation is working correctly if:

- ✅ **Login Flow**: District users redirect to their district page
- ✅ **Navigation**: District users see simplified navigation
- ✅ **Access Control**: District users can only access assigned districts
- ✅ **Admin Panel**: Can create district-scoped users successfully
- ✅ **Backwards Compatibility**: Existing KCK viewers work unchanged
- ✅ **Global Users**: Can access all districts without restrictions
- ✅ **Database**: All migrations applied successfully

---

## 🚨 **If Something Goes Wrong**

### **Rollback Option**
```bash
# If you need to rollback the changes
python scripts/apply_sql.py scripts/sql/rollback_district_scoping.sql instance/your_database.db
```

### **Re-apply Migration**
```bash
# If you need to re-apply the migration
python scripts/apply_sql.py scripts/sql/add_district_scoping.sql instance/your_database.db
```

---

## 📞 **Need Help?**

If you encounter any issues during testing:

1. **Check the logs** in your Flask application output
2. **Verify database** with the verification script
3. **Test individual components** (login, navigation, admin panel separately)
4. **Check browser console** for JavaScript errors

The implementation is designed to be backwards compatible, so existing functionality should continue working while new district scoping features are available.

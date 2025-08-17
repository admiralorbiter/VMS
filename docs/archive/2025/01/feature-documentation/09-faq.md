---
title: "VMS FAQ"
description: "Frequently Asked Questions about the Volunteer Management System"
tags: [faq, troubleshooting, support, common-questions]
---

# VMS FAQ

## 🔧 General Questions

### What is VMS?

**VMS** (Volunteer Management System) is a web-based application designed to streamline volunteer data management, event tracking, and reporting for educational organizations. It serves as a centralized tool to track volunteer activities, events, attendance, and generate comprehensive reports.

### What are the main features of VMS?

The main features include:
- **Volunteer Management**: Track volunteers, their skills, and engagement history
- **Organization Management**: Manage partner organizations and relationships
- **Event Management**: Create and track events with attendance
- **Reporting System**: Generate comprehensive reports and analytics
- **Calendar System**: Visual event management and scheduling
- **Attendance Tracking**: Record and monitor participation
- **Salesforce Integration**: Sync data with Salesforce CRM

### What technology stack does VMS use?

- **Backend**: Python, Flask, SQLAlchemy
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Testing**: pytest

## 🚀 Getting Started

### How do I set up VMS for development?

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd VMS
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   python -c "from app import create_app; app = create_app(); app.app_context().push(); from models import db; db.create_all()"
   ```

6. **Create admin user**
   ```bash
   python scripts/create_admin.py
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

### What are the system requirements?

- **Python**: 3.8 or higher
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 1GB free space
- **Database**: SQLite (included) or PostgreSQL
- **Browser**: Modern web browser (Chrome, Firefox, Safari, Edge)

### How do I create the first admin user?

Run the admin creation script:
```bash
python scripts/create_admin.py
```

This will prompt you for admin credentials and create the first user with full administrative privileges.

## 📊 Data Management

### How does data synchronization work?

VMS uses a **single source of truth** approach:
- **Primary Source**: Salesforce CRM
- **Local Cache**: SQLite/PostgreSQL database
- **Sync Process**: Automated import processes update local data
- **Data Consistency**: Import processes ensure data integrity

### How do I import data from Salesforce?

1. **Configure Salesforce credentials** in your `.env` file
2. **Run the import script**:
   ```bash
   python scripts/sync_script.py
   ```
3. **Monitor the import process** through the admin interface

### Can I import data from other sources?

Yes, VMS supports multiple import sources:
- **CSV files**: Direct upload through the web interface
- **Excel files**: Supported for bulk data import
- **Google Sheets**: Integration available for specific data types
- **API endpoints**: For programmatic data import

### How do I backup my data?

**Automatic backups** (if configured):
```bash
python scripts/backup.py
```

**Manual backup**:
```bash
# SQLite
cp vms.db vms_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump vms_production > vms_backup_$(date +%Y%m%d).sql
```

## 🔐 Security & Access

### How is user authentication handled?

VMS uses **Flask-Login** for session management:
- **Session-based authentication**
- **Password hashing** with Werkzeug
- **Role-based access control** (User, Coordinator, Admin)
- **Secure session cookies**

### What are the different user roles?

- **User**: Read access to volunteers, organizations, events
- **Coordinator**: Read/write access to all data, can manage events
- **Admin**: Full system access, user management, data imports

### How do I change a user's password?

**Admin interface**:
1. Go to Admin → User Management
2. Select the user
3. Click "Change Password"
4. Enter new password

**Command line**:
```bash
python scripts/change_password.py --username <username>
```

### Is the data encrypted?

- **Passwords**: Hashed using Werkzeug's security functions
- **Sensitive data**: Can be encrypted at rest (configurable)
- **Transmission**: HTTPS encryption for all web traffic
- **Database**: Can be encrypted (PostgreSQL with encryption)

## 🐛 Troubleshooting

### The application won't start

**Common causes and solutions**:

1. **Port already in use**
   ```bash
   # Check what's using port 5000
   lsof -i :5000
   # Kill the process or change port
   ```

2. **Database issues**
   ```bash
   # Recreate database
   rm vms.db
   python -c "from app import create_app; app = create_app(); app.app_context().push(); from models import db; db.create_all()"
   ```

3. **Missing dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**
   ```bash
   # Check if .env exists and has required variables
   cat .env
   ```

### I can't log in

**Check these common issues**:

1. **User exists?**
   ```bash
   python scripts/create_admin.py
   ```

2. **Password correct?**
   ```bash
   python scripts/change_password.py --username <username>
   ```

3. **Database connection?**
   ```bash
   python -c "from app import create_app; app = create_app(); app.app_context().push(); from models import db; db.session.execute('SELECT 1')"
   ```

### Reports are not generating

**Troubleshooting steps**:

1. **Check data exists**
   - Verify volunteers, events, and organizations are in the database
   - Check date ranges in report filters

2. **Check permissions**
   - Ensure user has appropriate role for report access

3. **Check logs**
   ```bash
   tail -f logs/vms.log
   ```

4. **Test report generation**
   ```bash
   python -c "from app import create_app; app = create_app(); app.app_context().push(); from reports.volunteer_thankyou import generate_report; print(generate_report())"
   ```

### Import process is failing

**Common import issues**:

1. **Salesforce credentials**
   ```bash
   # Check credentials in .env
   grep SALESFORCE .env
   ```

2. **Network connectivity**
   ```bash
   # Test Salesforce connection
   python scripts/test_google_sheets.py
   ```

3. **Data format issues**
   - Check CSV/Excel file format
   - Verify required columns are present
   - Check for encoding issues

4. **Database constraints**
   ```bash
   # Check for duplicate entries
   python -c "from app import create_app; app = create_app(); app.app_context().push(); from models.volunteer import Volunteer; print(Volunteer.query.filter_by(email='duplicate@example.com').count())"
   ```

## 📈 Performance

### The application is slow

**Performance optimization steps**:

1. **Database optimization**
   ```sql
   -- Create indexes
   CREATE INDEX idx_volunteers_email ON volunteers(email);
   CREATE INDEX idx_events_date ON events(start_date);

   -- Analyze tables
   ANALYZE;
   ```

2. **Application optimization**
   ```python
   # Enable caching
   from flask_caching import Cache
   cache = Cache()
   ```

3. **System resources**
   ```bash
   # Check memory usage
   free -h

   # Check CPU usage
   top
   ```

### Reports are taking too long to generate

**Solutions**:

1. **Add caching**
   ```python
   @cache.memoize(timeout=300)
   def generate_report():
       # Report generation code
   ```

2. **Optimize queries**
   ```python
   # Use eager loading
   volunteers = Volunteer.query.options(db.joinedload(Volunteer.organization)).all()
   ```

3. **Background processing**
   - Consider using Celery for large reports
   - Implement async report generation

## 🔄 Updates & Maintenance

### How do I update VMS?

**Safe update process**:

1. **Backup current data**
   ```bash
   python scripts/backup.py
   ```

2. **Update code**
   ```bash
   git pull origin main
   ```

3. **Update dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python -c "from app import create_app; app = create_app(); app.app_context().push(); from models import db; db.create_all()"
   ```

5. **Restart application**
   ```bash
   sudo systemctl restart vms  # If using systemd
   ```

### How often should I backup data?

**Recommended backup schedule**:
- **Daily**: Automated backups for production
- **Weekly**: Manual verification of backup integrity
- **Before updates**: Always backup before major updates

### How do I monitor system health?

**Monitoring options**:

1. **Health check endpoint**
   ```bash
   curl http://localhost:5000/health
   ```

2. **System metrics**
   ```bash
   python scripts/monitor.py
   ```

3. **Log monitoring**
   ```bash
   tail -f logs/vms.log | grep ERROR
   ```

## 📞 Support

### Where can I get help?

**Support channels**:
- **Documentation**: Check the docs folder
- **Issues**: Create an issue on GitHub
- **Email**: Contact the development team
- **Bug Reports**: Use the bug report feature in the application

### How do I report a bug?

1. **Use the bug report feature** in the application
2. **Include details**:
   - Steps to reproduce
   - Expected vs actual behavior
   - Browser/OS information
   - Error messages

### How do I request a new feature?

1. **Create a feature request** on GitHub
2. **Describe the use case** and benefits
3. **Provide examples** of how it should work
4. **Consider implementation complexity**

## 🔗 Integration

### Can I integrate VMS with other systems?

**Available integrations**:
- **Salesforce**: Primary data source
- **Google Sheets**: Data import/export
- **Email systems**: SMTP configuration
- **APIs**: RESTful API endpoints available

### How do I set up Salesforce integration?

1. **Create Salesforce app**
   - Go to Salesforce Setup → App Manager
   - Create a new connected app
   - Note the Client ID and Secret

2. **Configure VMS**
   ```bash
   # Add to .env
   SALESFORCE_CLIENT_ID=your_client_id
   SALESFORCE_CLIENT_SECRET=your_client_secret
   SALESFORCE_USERNAME=your_username
   SALESFORCE_PASSWORD=your_password
   ```

3. **Test connection**
   ```bash
   python scripts/test_salesforce.py
   ```

### Can I export data to other formats?

**Export formats supported**:
- **Excel**: .xlsx files
- **CSV**: Comma-separated values
- **PDF**: For reports
- **JSON**: API responses

**Export methods**:
1. **Web interface**: Use export buttons in reports
2. **API**: Programmatic access
3. **Scripts**: Command-line tools

## 📋 Best Practices

### What are the recommended practices for using VMS?

**Data management**:
- Regular backups
- Data validation before import
- Consistent naming conventions
- Regular data cleanup

**User management**:
- Use role-based access
- Regular password updates
- Monitor user activity
- Remove inactive users

**System maintenance**:
- Regular updates
- Monitor system resources
- Review logs regularly
- Test backups

### How should I organize volunteer data?

**Best practices**:
- **Consistent naming**: Use full names consistently
- **Email addresses**: Use unique, valid email addresses
- **Organization relationships**: Link volunteers to organizations
- **Skills tracking**: Use standardized skill categories
- **Status management**: Keep volunteer status current

### What reporting practices are recommended?

**Reporting best practices**:
- **Regular reports**: Generate reports on a schedule
- **Data validation**: Verify report accuracy
- **Export formats**: Use appropriate formats for recipients
- **Documentation**: Document report generation processes

## 🔗 Related Documentation

- [System Overview](01-overview.md)
- [Architecture](02-architecture.md)
- [Development Guide](05-dev-guide.md)
- [Operations Guide](06-ops-guide.md)
- [Test Guide](07-test-guide.md)

---

*Last updated: August 2025*

---
title: "PythonAnywhere Deployment Guide"
status: active
doc_type: deployment
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["deployment", "pythonanywhere", "production", "cache", "scheduling"]
summary: "Complete guide for deploying VMS to PythonAnywhere with automated cache refresh scheduling and monitoring."
canonical: "/docs/living/PythonAnywhere_Deployment.md"
---

# PythonAnywhere Deployment Guide

## 🎯 **Overview**

This guide covers deploying the VMS application to PythonAnywhere with automated cache refresh scheduling and monitoring.

## 🚀 **Initial Setup**

### **1. PythonAnywhere Account Setup**
```bash
# Create PythonAnywhere account
# Visit: https://www.pythonanywhere.com/

# Choose appropriate plan (Hacker plan minimum for scheduled tasks)
# Note: Scheduled tasks require paid plan
```

### **2. Project Deployment**
```bash
# SSH to PythonAnywhere
ssh yourusername@ssh.pythonanywhere.com

# Clone repository
git clone https://github.com/yourusername/VMS.git
cd VMS

# Set up virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with production values
```

### **3. Database Setup**
```bash
# Initialize database
flask db upgrade

# Create admin user
python scripts/create_admin.py

# Verify database
flask db current
```

## ⚙️ **Web App Configuration**

### **1. WSGI Configuration**
```python
# File: /var/www/yourusername_pythonanywhere_com_wsgi.py
import sys
import os

# Add your project directory to the Python path
path = '/home/yourusername/VMS'
if path not in sys.path:
    sys.path.append(path)

# Import your Flask app
from app import app as application

if __name__ == "__main__":
    application.run()
```

### **2. Static Files Configuration**
```bash
# Static files URL: /static/
# Static files directory: /home/yourusername/VMS/static/

# Media files URL: /media/
# Media files directory: /home/yourusername/VMS/instance/
```

### **3. Environment Variables**
```bash
# Set in PythonAnywhere Web tab > Environment variables
FLASK_ENV=production
DATABASE_URL=sqlite:///instance/vms.db
SECRET_KEY=your-secret-key-here
```

## 📅 **Scheduled Tasks Setup**

### **1. Cache Refresh Task**
```bash
# Task Configuration (in PythonAnywhere Tasks tab):
# Command: python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh
# Hour: 2 (runs at 2 AM daily)
# Minute: 0
# Enabled: Yes
```

### **2. Daily Imports Task**
```bash
# Task Configuration (in PythonAnywhere Tasks tab):
# Command: python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --daily
# Hour: 3 (runs at 3 AM daily, after cache refresh)
# Minute: 0
# Enabled: Yes
```

### **3. Task Monitoring**
```bash
# Check cache refresh status
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py status

# View cache refresh logs
tail -f /home/yourusername/VMS/logs/cache_manager.log

# Manual cache refresh execution
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh --force

# Check daily imports status
python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --validate

# View daily imports logs
tail -f /home/yourusername/VMS/logs/daily_imports.log

# Manual daily imports execution
python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --daily
```

### **3. Health Monitoring**
```bash
# Perform health check
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py health

# Check system resources
df -h
free -h
```

## 🔧 **Cache Management Commands**

### **Basic Operations**
```bash
# Refresh all caches
python scripts/pythonanywhere_cache_manager.py refresh

# Force refresh (ignore timing)
python scripts/pythonanywhere_cache_manager.py refresh --force

# Refresh specific cache type
python scripts/pythonanywhere_cache_manager.py refresh --type district
python scripts/pythonanywhere_cache_manager.py refresh --type organization
python scripts/pythonanywhere_cache_manager.py refresh --type virtual_session
python scripts/pythonanywhere_cache_manager.py refresh --type volunteer
python scripts/pythonanywhere_cache_manager.py refresh --type recruitment
```

### **Monitoring & Status**
```bash
# Check cache status
python scripts/pythonanywhere_cache_manager.py status

# Health check
python scripts/pythonanywhere_cache_manager.py health

# View logs
tail -f logs/cache_manager.log
```

## 📥 **Daily Imports Commands**

### **Basic Operations**
```bash
# Run daily imports (organizations, volunteers, affiliations, events, history)
python scripts/daily_imports/daily_imports.py --daily

# Run full imports (all data including students, schools, classes, teachers)
python scripts/daily_imports/daily_imports.py --full

# Run only specific imports
python scripts/daily_imports/daily_imports.py --only organizations
python scripts/daily_imports/daily_imports.py --only volunteers
python scripts/daily_imports/daily_imports.py --only events

# Exclude specific imports
python scripts/daily_imports/daily_imports.py --exclude students
python scripts/daily_imports/daily_imports.py --exclude teachers
```

### **Testing & Validation**
```bash
# Dry run (show what would be imported without actually importing)
python scripts/daily_imports/daily_imports.py --dry-run

# Validate configuration and connections
python scripts/daily_imports/daily_imports.py --validate

# Run with verbose logging
python scripts/daily_imports/daily_imports.py --daily --verbose
```

### **Monitoring & Troubleshooting**
```bash
# Check import logs
tail -f logs/daily_imports.log

# View recent import results
grep "Import completed" logs/daily_imports.log | tail -10

# Check for import errors
grep "ERROR" logs/daily_imports.log | tail -20

# Monitor import progress
tail -f logs/daily_imports.log | grep "Processing"
```

## 📊 **Monitoring & Maintenance**

### **1. Log Monitoring**
```bash
# Application logs
tail -f logs/app.log

# Cache manager logs
tail -f logs/cache_manager.log

# Error logs
tail -f logs/error.log
```

### **2. Database Maintenance**
```bash
# Check database size
sqlite3 instance/vms.db "PRAGMA page_count; PRAGMA page_size;"

# Optimize database
sqlite3 instance/vms.db "VACUUM;"

# Check database integrity
sqlite3 instance/vms.db "PRAGMA integrity_check;"
```

### **3. Cache Health Monitoring**
```bash
# Check cache status
python scripts/pythonanywhere_cache_manager.py status

# Verify cache freshness
python -c "
from app import app
from utils.cache_refresh_scheduler import get_cache_status
with app.app_context():
    status = get_cache_status()
    print(f'Last refresh: {status[\"last_refresh\"]}')
    print(f'Total refreshes: {status[\"stats\"][\"total_refreshes\"]}')
    print(f'Successful: {status[\"stats\"][\"successful_refreshes\"]}')
    print(f'Failed: {status[\"stats\"][\"failed_refreshes\"]}')
"
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. Scheduled Task Not Running**
```bash
# Check task configuration
# Verify command path is correct
# Check if task is enabled
# Review task logs for errors

# Test task manually
python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh
```

#### **2. Cache Refresh Failures**
```bash
# Check logs for specific errors
tail -f logs/cache_manager.log

# Verify database connectivity
python -c "from app import app; from models import db; app.app_context().push(); db.session.execute('SELECT 1')"

# Check disk space
df -h

# Verify permissions
ls -la /home/yourusername/VMS/logs/
```

#### **3. Web App Issues**
```bash
# Check web app status
# Restart web app
touch /var/www/yourusername_pythonanywhere_com_wsgi.py

# Check error logs
tail -f /var/log/yourusername.pythonanywhere.com.error.log

# Verify static files
ls -la /home/yourusername/VMS/static/
```

### **Emergency Procedures**

#### **1. Manual Cache Refresh**
```bash
# Force refresh all caches
python scripts/pythonanywhere_cache_manager.py refresh --force

# Refresh specific problematic cache
python scripts/pythonanywhere_cache_manager.py refresh --type district
```

#### **2. Database Recovery**
```bash
# Backup current database
cp instance/vms.db instance/vms_backup_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp instance/vms_backup_YYYYMMDD_HHMMSS.db instance/vms.db

# Recreate database
flask db upgrade
```

## 📈 **Performance Optimization**

### **1. Cache Optimization**
```bash
# Monitor cache hit rates
python scripts/pythonanywhere_cache_manager.py status

# Adjust refresh frequency if needed
# Current: 24 hours
# Can be modified in scheduled task settings
```

### **2. Database Optimization**
```bash
# Analyze database
sqlite3 instance/vms.db "ANALYZE;"

# Reindex database
sqlite3 instance/vms.db "REINDEX;"

# Vacuum database
sqlite3 instance/vms.db "VACUUM;"
```

### **3. Log Management**
```bash
# Rotate logs
mv logs/cache_manager.log logs/cache_manager_$(date +%Y%m%d).log
touch logs/cache_manager.log

# Compress old logs
gzip logs/cache_manager_*.log
```

## 🔄 **Deployment Updates**

### **1. Code Updates**
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations
flask db upgrade

# Restart web app
touch /var/www/yourusername_pythonanywhere_com_wsgi.py

# Test cache refresh
python scripts/pythonanywhere_cache_manager.py refresh --force
```

### **2. Configuration Updates**
```bash
# Update environment variables
# Restart web app after changes
touch /var/www/yourusername_pythonanywhere_com_wsgi.py

# Verify changes
python scripts/pythonanywhere_cache_manager.py health
```

## 📋 **Checklist**

### **Initial Deployment**
- [ ] PythonAnywhere account created
- [ ] Repository cloned
- [ ] Virtual environment set up
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Admin user created
- [ ] Web app configured
- [ ] Static files configured
- [ ] Cache refresh scheduled task created
- [ ] Daily imports scheduled task created
- [ ] Cache refresh tested
- [ ] Daily imports tested
- [ ] Health check passed

### **Regular Maintenance**
- [ ] Monitor scheduled task execution
- [ ] Check cache refresh logs
- [ ] Verify web app status
- [ ] Monitor database size
- [ ] Review error logs
- [ ] Update dependencies
- [ ] Backup database
- [ ] Optimize database

### **Troubleshooting**
- [ ] Check task configuration
- [ ] Verify file permissions
- [ ] Review error logs
- [ ] Test manual operations
- [ ] Check system resources
- [ ] Verify network connectivity

## 🔗 **Related Documents**

- **Commands Reference**: `/docs/living/Commands.md`
- **Technology Stack**: `/docs/living/TechStack.md`
- **System Status**: `/docs/living/Status.md`
- **Cache Management**: `/docs/living/Cache_Management.md`

## 📝 **Support**

For issues with PythonAnywhere deployment:
1. Check the troubleshooting section above
2. Review logs for specific error messages
3. Test manual operations to isolate issues
4. Contact PythonAnywhere support if needed
5. Check VMS documentation for application-specific issues

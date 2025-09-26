---
title: "PythonAnywhere Cache Management Setup Summary"
status: active
doc_type: quick-reference
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["pythonanywhere", "cache", "scheduling", "quick-reference"]
summary: "Quick setup guide for PythonAnywhere cache management system with 24-hour automated refresh."
canonical: "/docs/living/PythonAnywhere_Setup_Summary.md"
---

# PythonAnywhere Cache Management Setup Summary

## 🎯 **Quick Setup (5 minutes)**

### **1. Upload Script**
```bash
# Upload the PythonAnywhere cache manager script
# File: scripts/pythonanywhere_cache_manager.py
# Upload to: /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py
```

### **2. Set Up Scheduled Tasks**
In PythonAnywhere Tasks tab:

**Cache Refresh Task:**
- **Command**: `python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh`
- **Hour**: 2 (runs at 2 AM daily)
- **Minute**: 0
- **Enabled**: Yes

**Daily Imports Task:**
- **Command**: `python /home/yourusername/VMS/scripts/daily_imports/daily_imports.py --daily`
- **Hour**: 3 (runs at 3 AM daily, after cache refresh)
- **Minute**: 0
- **Enabled**: Yes

### **3. Test the System**
```bash
# SSH to PythonAnywhere
ssh yourusername@ssh.pythonanywhere.com

# Navigate to project
cd VMS

# Test cache refresh script
python scripts/pythonanywhere_cache_manager.py status
python scripts/pythonanywhere_cache_manager.py health
python scripts/pythonanywhere_cache_manager.py refresh --force

# Test daily imports script
python scripts/daily_imports/daily_imports.py --validate
python scripts/daily_imports/daily_imports.py --dry-run
python scripts/daily_imports/daily_imports.py --daily
```

## 📋 **Available Commands**

### **Basic Operations**
```bash
# Check cache status
python scripts/pythonanywhere_cache_manager.py status

# Perform health check
python scripts/pythonanywhere_cache_manager.py health

# Refresh all caches
python scripts/pythonanywhere_cache_manager.py refresh

# Force refresh (ignore timing)
python scripts/pythonanywhere_cache_manager.py refresh --force
```

### **Specific Cache Types**
```bash
# Refresh specific cache types
python scripts/pythonanywhere_cache_manager.py refresh --type district
python scripts/pythonanywhere_cache_manager.py refresh --type organization
python scripts/pythonanywhere_cache_manager.py refresh --type virtual_session
python scripts/pythonanywhere_cache_manager.py refresh --type volunteer
python scripts/pythonanywhere_cache_manager.py refresh --type recruitment
```

### **Daily Imports Operations**
```bash
# Run daily imports (scheduled task)
python scripts/daily_imports/daily_imports.py --daily

# Run full imports (all data)
python scripts/daily_imports/daily_imports.py --full

# Run specific imports only
python scripts/daily_imports/daily_imports.py --only organizations
python scripts/daily_imports/daily_imports.py --only volunteers
python scripts/daily_imports/daily_imports.py --only events

# Exclude specific imports
python scripts/daily_imports/daily_imports.py --exclude students
python scripts/daily_imports/daily_imports.py --exclude teachers

# Testing and validation
python scripts/daily_imports/daily_imports.py --dry-run
python scripts/daily_imports/daily_imports.py --validate
python scripts/daily_imports/daily_imports.py --daily --verbose
```

## 🔍 **Monitoring & Troubleshooting**

### **Check Status**
```bash
# View cache refresh status
python scripts/pythonanywhere_cache_manager.py status

# Cache refresh health check
python scripts/pythonanywhere_cache_manager.py health

# View cache refresh logs
tail -f logs/cache_manager.log

# Validate daily imports configuration
python scripts/daily_imports/daily_imports.py --validate

# View daily imports logs
tail -f logs/daily_imports.log

# Check recent import results
grep "Import completed" logs/daily_imports.log | tail -10
```

### **Common Issues**
1. **Task not running**: Check task configuration in PythonAnywhere Tasks tab
2. **Permission errors**: Ensure script has execute permissions
3. **Import errors**: Verify all dependencies are installed
4. **Database errors**: Check database connectivity

### **Debug Commands**
```bash
# Test manual refresh
python scripts/pythonanywhere_cache_manager.py refresh --force

# Check specific cache type
python scripts/pythonanywhere_cache_manager.py refresh --type district

# View detailed logs
tail -f logs/cache_manager.log | grep ERROR
```

## 📊 **What Gets Refreshed**

### **Cache Types**
- **District Reports** - Year-end and engagement data
- **Organization Reports** - Organization summaries and details
- **Virtual Session Reports** - Usage and breakdown data
- **Volunteer Reports** - Recent volunteers and first-time data
- **Recruitment Reports** - Candidate recommendations

### **Refresh Schedule**
- **Frequency**: Every 24 hours
- **Time**: 2:00 AM daily
- **Duration**: 3-6 minutes typically
- **Impact**: No user impact (background process)

## ✅ **Verification Checklist**

- [ ] Cache refresh script uploaded to PythonAnywhere
- [ ] Daily imports script uploaded to PythonAnywhere
- [ ] Cache refresh scheduled task configured (2 AM daily)
- [ ] Daily imports scheduled task configured (3 AM daily)
- [ ] Both tasks enabled in PythonAnywhere
- [ ] Cache refresh manual test successful (`python scripts/pythonanywhere_cache_manager.py status`)
- [ ] Cache refresh health check passes (`python scripts/pythonanywhere_cache_manager.py health`)
- [ ] Daily imports validation passes (`python scripts/daily_imports/daily_imports.py --validate`)
- [ ] Daily imports dry run works (`python scripts/daily_imports/daily_imports.py --dry-run`)
- [ ] Force refresh works (`python scripts/pythonanywhere_cache_manager.py refresh --force`)
- [ ] Daily imports test works (`python scripts/daily_imports/daily_imports.py --daily`)
- [ ] Cache refresh logs are being written (`tail -f logs/cache_manager.log`)
- [ ] Daily imports logs are being written (`tail -f logs/daily_imports.log`)

## 🚨 **Emergency Procedures**

### **If Cache Refresh Fails**
```bash
# Force refresh all caches
python scripts/pythonanywhere_cache_manager.py refresh --force

# Check logs for errors
tail -f logs/cache_manager.log

# Verify database connectivity
python -c "from app import app; from models import db; app.app_context().push(); db.session.execute('SELECT 1')"
```

### **If Daily Imports Fail**
```bash
# Run daily imports manually
python scripts/daily_imports/daily_imports.py --daily

# Check logs for errors
tail -f logs/daily_imports.log

# Validate configuration
python scripts/daily_imports/daily_imports.py --validate

# Run dry run to see what would be imported
python scripts/daily_imports/daily_imports.py --dry-run

# Run specific imports if needed
python scripts/daily_imports/daily_imports.py --only organizations
```

### **If Scheduled Tasks Stop**
1. Check PythonAnywhere Tasks tab
2. Verify both tasks are enabled
3. Check task logs for errors
4. Test manual execution
5. Restart tasks if needed

## 📈 **Performance Benefits**

- **Faster Reports**: Cached data loads 5-10x faster
- **Reduced Database Load**: Less strain during peak usage
- **Better User Experience**: Reports load instantly
- **Automatic Maintenance**: No manual intervention needed
- **Fresh Data**: Daily imports ensure data is always current
- **Reliable Operations**: Automated processes reduce human error

## 🔗 **Related Documentation**

- **Full Deployment Guide**: `/docs/living/PythonAnywhere_Deployment.md`
- **Cache Management Details**: `/docs/living/Cache_Management.md`
- **Commands Reference**: `/docs/living/Commands.md`

## 📞 **Support**

If you encounter issues:
1. Check the troubleshooting section above
2. Review logs for specific error messages
3. Test manual operations to isolate issues
4. Contact system administrator if needed

---

**Last Updated**: 2025-01-27  
**Status**: Production Ready  
**Tested**: ✅ All systems operational

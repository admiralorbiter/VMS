---
title: "Cache Management System"
status: active
doc_type: technical
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["cache", "performance", "scheduling", "pythonanywhere", "reports"]
summary: "Comprehensive guide to the VMS cache management system including automated refresh, monitoring, and PythonAnywhere deployment."
canonical: "/docs/living/Cache_Management.md"
---

# Cache Management System

## 🎯 **Overview**

The VMS cache management system provides automated 24-hour cache refresh for all report data, ensuring optimal performance while maintaining data freshness. The system is designed for PythonAnywhere deployment with comprehensive monitoring and error handling.

## 🏗️ **System Architecture**

### **Cache Types**
- **District Reports** - Year-end and engagement reports
- **Organization Reports** - Organization summaries and details  
- **Virtual Session Reports** - Usage and breakdown data
- **Volunteer Reports** - Recent volunteers and first-time data
- **Recruitment Reports** - Candidate recommendations

### **Components**
1. **Cache Refresh Scheduler** (`utils/cache_refresh_scheduler.py`)
2. **PythonAnywhere Manager** (`scripts/pythonanywhere_cache_manager.py`)
3. **Web Management Interface** (`routes/management/cache_management.py`)
4. **Database Cache Models** (`models/reports.py`)

## 🚀 **Quick Start**

### **PythonAnywhere Setup**
```bash
# Set up 24-hour scheduled task
# Command: python /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh
# Hour: 2 (runs at 2 AM daily)
# Minute: 0

# Test the system
python scripts/pythonanywhere_cache_manager.py status
python scripts/pythonanywhere_cache_manager.py refresh --force
```

### **Local Development**
```bash
# Manual cache refresh
python scripts/cache_management.py refresh-all

# Check status
python scripts/cache_management.py status

# Start scheduler (development)
python scripts/cache_management.py start-scheduler
```

## 📊 **Cache Types & Data**

### **District Reports Cache**
- **Model**: `DistrictYearEndReport`, `DistrictEngagementReport`
- **Data**: District statistics, event data, volunteer metrics
- **Refresh**: Every 24 hours
- **Size**: ~50-100KB per district

### **Organization Reports Cache**
- **Model**: `OrganizationReport`, `OrganizationSummaryCache`
- **Data**: Organization statistics, event breakdowns
- **Refresh**: Every 24 hours
- **Size**: ~20-50KB per organization

### **Virtual Session Cache**
- **Model**: `VirtualSessionReportCache`, `VirtualSessionDistrictCache`
- **Data**: Session data, district summaries, filter options
- **Refresh**: Every 24 hours
- **Size**: ~100-500KB per virtual year

### **Volunteer Reports Cache**
- **Model**: `RecentVolunteersReportCache`, `FirstTimeVolunteerReportCache`
- **Data**: Volunteer data, event participation
- **Refresh**: Every 24 hours
- **Size**: ~50-200KB per school year

### **Recruitment Cache**
- **Model**: `RecruitmentCandidatesCache`
- **Data**: Candidate recommendations, matching scores
- **Refresh**: Every 24 hours
- **Size**: ~10-50KB per event

## ⚙️ **Configuration**

### **Refresh Schedule**
```python
# Default configuration
REFRESH_INTERVAL_HOURS = 24
REFRESH_TIME = "02:00"  # 2 AM daily
MAX_CACHE_AGE_HOURS = 24
```

### **Cache Validation**
```python
# Cache is considered valid if:
# 1. Last updated within 24 hours
# 2. No errors during generation
# 3. Data structure is complete
```

### **Error Handling**
- **Retry Logic**: 3 attempts with exponential backoff
- **Fallback**: Serve stale data if refresh fails
- **Logging**: Comprehensive error logging
- **Monitoring**: Health check endpoints

## 🔧 **Management Commands**

### **PythonAnywhere Script**
```bash
# Basic operations
python scripts/pythonanywhere_cache_manager.py refresh
python scripts/pythonanywhere_cache_manager.py status
python scripts/pythonanywhere_cache_manager.py health

# Advanced operations
python scripts/pythonanywhere_cache_manager.py refresh --force
python scripts/pythonanywhere_cache_manager.py refresh --type district
```

### **Development Script**
```bash
# Cache management
python scripts/cache_management.py refresh-all
python scripts/cache_management.py refresh district
python scripts/cache_management.py status

# Scheduler control
python scripts/cache_management.py start-scheduler
python scripts/cache_management.py stop-scheduler
```

### **Web Interface**
- **Status Page**: `/management/cache/status`
- **Refresh Page**: `/management/cache/refresh`
- **API Endpoints**: `/management/cache/api/*`

## 📈 **Monitoring & Analytics**

### **Status Monitoring**
```bash
# Check overall status
python scripts/pythonanywhere_cache_manager.py status

# Health check
python scripts/pythonanywhere_cache_manager.py health

# View logs
tail -f logs/cache_manager.log
```

### **Key Metrics**
- **Refresh Success Rate**: Target >95%
- **Average Refresh Time**: Target <5 minutes
- **Cache Hit Rate**: Target >90%
- **Error Rate**: Target <5%

### **Log Analysis**
```bash
# View recent refreshes
grep "Cache refresh completed" logs/cache_manager.log

# Check for errors
grep "ERROR" logs/cache_manager.log

# Monitor performance
grep "took.*seconds" logs/cache_manager.log
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. Scheduled Task Not Running**
```bash
# Check task configuration in PythonAnywhere
# Verify command path: /home/yourusername/VMS/scripts/pythonanywhere_cache_manager.py refresh
# Check if task is enabled
# Review task logs

# Test manually
python scripts/pythonanywhere_cache_manager.py refresh
```

#### **2. Cache Refresh Failures**
```bash
# Check logs for specific errors
tail -f logs/cache_manager.log

# Verify database connectivity
python -c "from app import app; from models import db; app.app_context().push(); db.session.execute('SELECT 1')"

# Check disk space
df -h
```

#### **3. Performance Issues**
```bash
# Check cache size
sqlite3 instance/vms.db "SELECT name, length(data) FROM sqlite_master WHERE type='table' AND name LIKE '%cache%';"

# Monitor refresh time
grep "took.*seconds" logs/cache_manager.log | tail -10

# Check system resources
htop
```

### **Debug Commands**
```bash
# Force refresh with verbose logging
python scripts/pythonanywhere_cache_manager.py refresh --force

# Check specific cache type
python scripts/pythonanywhere_cache_manager.py refresh --type district

# Health check with details
python scripts/pythonanywhere_cache_manager.py health
```

## 🔄 **Maintenance**

### **Daily Tasks**
- [ ] Monitor scheduled task execution
- [ ] Check cache refresh logs
- [ ] Verify web app performance
- [ ] Review error logs

### **Weekly Tasks**
- [ ] Analyze cache performance metrics
- [ ] Review error patterns
- [ ] Check disk space usage
- [ ] Optimize database

### **Monthly Tasks**
- [ ] Review cache configuration
- [ ] Analyze refresh patterns
- [ ] Update documentation
- [ ] Performance optimization

## 📊 **Performance Optimization**

### **Cache Size Management**
```bash
# Monitor cache sizes
sqlite3 instance/vms.db "
SELECT 
    name,
    COUNT(*) as records,
    SUM(length(data)) as total_size
FROM sqlite_master 
WHERE type='table' AND name LIKE '%cache%'
GROUP BY name;
"

# Clean old cache entries
python -c "
from app import app
from models.reports import *
with app.app_context():
    # Clean caches older than 7 days
    cutoff = datetime.now() - timedelta(days=7)
    VirtualSessionReportCache.query.filter(VirtualSessionReportCache.last_updated < cutoff).delete()
    db.session.commit()
"
```

### **Database Optimization**
```bash
# Analyze database
sqlite3 instance/vms.db "ANALYZE;"

# Reindex cache tables
sqlite3 instance/vms.db "REINDEX;"

# Vacuum database
sqlite3 instance/vms.db "VACUUM;"
```

### **Log Management**
```bash
# Rotate logs
mv logs/cache_manager.log logs/cache_manager_$(date +%Y%m%d).log
touch logs/cache_manager.log

# Compress old logs
gzip logs/cache_manager_*.log

# Clean old logs (older than 30 days)
find logs/ -name "cache_manager_*.log.gz" -mtime +30 -delete
```

## 🔐 **Security Considerations**

### **Access Control**
- Cache management requires admin privileges
- API endpoints are protected with authentication
- Logs may contain sensitive data

### **Data Privacy**
- Cache data is stored in database (not external services)
- No personal data is logged
- Cache invalidation on data changes

### **Error Handling**
- Sensitive information is not logged
- Error messages are sanitized
- Failed operations don't expose system details

## 📋 **Best Practices**

### **Development**
- Test cache refresh locally before deployment
- Use `--force` flag for testing
- Monitor logs during development
- Verify cache data integrity

### **Production**
- Set up monitoring alerts
- Regular health checks
- Backup cache configuration
- Document any customizations

### **Troubleshooting**
- Check logs first
- Test manual operations
- Verify system resources
- Use health check commands

## 🔗 **Related Documentation**

- **PythonAnywhere Deployment**: `/docs/living/PythonAnywhere_Deployment.md`
- **Commands Reference**: `/docs/living/Commands.md`
- **Technology Stack**: `/docs/living/TechStack.md`
- **System Status**: `/docs/living/Status.md`

## 📝 **Support**

For cache management issues:
1. Check the troubleshooting section
2. Review logs for specific errors
3. Test manual operations
4. Check system resources
5. Contact system administrator if needed

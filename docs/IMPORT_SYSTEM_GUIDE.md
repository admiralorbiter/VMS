# Import System Guide

## Overview

The VMS import system has been enhanced with robust reporting and monitoring capabilities to help you track what didn't get linked during imports and identify issues that need attention.

## Key Features

### 1. **Two-Phase Import Pipeline**
- **Phase 1**: Import student data without school assignments
- **Phase 2**: Assign schools to students based on affiliations

### 2. **Comprehensive Reporting**
- Real-time import status dashboard
- Detailed breakdown of unassigned students
- Missing schools analysis
- Export capabilities for manual review

### 3. **Robust Error Handling**
- Prevents incorrect school assignments
- Validates affiliations against existing schools
- Provides clear recommendations for fixing issues

## Import Status Dashboard

### Accessing the Dashboard
Navigate to `/students/import-dashboard` to view the real-time import status.

### Dashboard Features
- **Summary Cards**: Total students, assigned/unassigned counts, completion percentage
- **Progress Bar**: Visual representation of import completion
- **Top Schools**: Schools with the most student assignments
- **Missing Schools**: Affiliations that don't correspond to existing schools
- **Action Buttons**: Refresh, export, and detailed reporting

### Understanding the Data

#### Summary Statistics
- **Total Students**: All students in the database
- **Students with Schools**: Successfully assigned to schools
- **Students without Schools**: Need attention
- **Completion Percentage**: Overall import success rate

#### Detailed Breakdown
- **Students with affiliations but no school**: Have affiliation data but school doesn't exist in database
- **Students with no affiliation data**: Need affiliation data updated in Salesforce

## API Endpoints

### Import Status Report
```
GET /students/import-status-report
```
Returns comprehensive analysis of import status including:
- Summary statistics
- Detailed breakdown
- Missing schools analysis
- Sample students
- Recommendations

### Export Unassigned Students
```
GET /students/export-unassigned-students
```
Downloads a CSV file with all students without school assignments for manual review.

### Import Dashboard Data
```
GET /students/import-dashboard-data
```
Returns real-time data for the dashboard visualization.

## Common Issues and Solutions

### Issue: Students with affiliations but no school assignments
**Cause**: The affiliation ID doesn't correspond to a school in the database
**Solution**:
1. Import the missing school from Salesforce
2. Or update the affiliation in Salesforce to point to an existing school

### Issue: Students with no affiliation data
**Cause**: Missing `npsp__Primary_Affiliation__c` data in Salesforce
**Solution**: Update the student records in Salesforce to include affiliation data

### Issue: Incorrect school assignments
**Cause**: Bulk assignment logic assigned wrong schools
**Solution**: The system now prevents this by validating affiliations against existing schools

## Best Practices

### 1. **Run Phase 1 First**
Always run the student import (Phase 1) before school assignment (Phase 2).

### 2. **Monitor the Dashboard**
Check the import dashboard regularly to identify issues early.

### 3. **Export and Review**
Use the export feature to get detailed lists of unassigned students for manual review.

### 4. **Address Missing Schools**
Import missing schools or update affiliations in Salesforce before re-running Phase 2.

### 5. **Validate Data Quality**
Ensure Salesforce data is clean and complete before importing.

## Troubleshooting

### Dashboard Not Loading
- Check that the database is accessible
- Verify user permissions
- Check browser console for JavaScript errors

### Export Fails
- Ensure sufficient disk space
- Check file permissions
- Verify database connection

### Import Errors
- Check Salesforce connectivity
- Verify API credentials
- Review error logs for specific issues

## File Structure

```
routes/students/routes.py          # Import routes and logic
templates/students/import_dashboard.html  # Dashboard interface
models/student.py                  # Student import methods
IMPORT_SYSTEM_GUIDE.md            # This guide
```

## Monitoring and Maintenance

### Regular Checks
1. **Daily**: Review dashboard for new issues
2. **Weekly**: Export and review unassigned students
3. **Monthly**: Analyze missing schools and update Salesforce data

### Data Quality
- Monitor completion percentages
- Track missing school patterns
- Identify data quality issues in Salesforce

### Performance
- Large imports may take time
- Monitor database performance
- Consider batch sizes for optimal performance

## Support

For issues with the import system:
1. Check the dashboard for specific error messages
2. Review the detailed import report
3. Export unassigned students for manual analysis
4. Contact the development team with specific error details

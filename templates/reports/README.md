# Reports Template Structure

This directory contains all report templates organized into logical folders for better maintainability and easier navigation.

## Folder Structure

### `/virtual/`
Virtual session related reports
- `virtual_usage.html` - Main virtual session usage report
- `virtual_usage_district.html` - District-specific virtual usage
- `virtual_breakdown.html` - Detailed virtual session breakdown
- `virtual_google_sheets.html` - Google Sheets integration for virtual reports
- `virtual_teacher_breakdown.html` - Teacher-specific virtual session data
- `virtual_teacher_progress.html` - Teacher progress tracking
- `virtual_teacher_progress_google_sheets.html` - Google Sheets for teacher progress

### `/volunteers/`
Volunteer-focused reports
- `volunteer_thankyou.html` - Thank you report for volunteers
- `volunteer_thankyou_detail.html` - Detailed volunteer thank you report
- `volunteers_by_event.html` - Volunteers grouped by event
- `first_time_volunteer.html` - First-time volunteer tracking
- `recent_volunteers.html` - Recently active volunteers

### `/organizations/`
Organization reports
- `organization_report.html` - Main organization report
- `organization_report_detail.html` - Detailed organization report

### `/districts/`
District-level reports
- `district_year_end.html` - Year-end district summary
- `district_year_end_detail.html` - Detailed district year-end report

### `/recruitment/`
Recruitment and matching tools
- `recruitment_tools.html` - Main recruitment tools page
- `recruitment_report.html` - Recruitment activity report
- `recruitment_search.html` - Volunteer search interface
- `recruitment_candidates.html` - Event candidate matching

### `/events/`
Event management reports
- `dia_events.html` - Data in Action events report
- `contact_report.html` - Event contact report
- `contact_report_detail.html` - Detailed contact report

### `/attendance/`
Attendance tracking reports
- `attendance_report.html` - Main attendance report

### `/shared/`
Common/shared templates
- `google_sheets_management.html` - Google Sheets management interface
- `google_sheets_sidebar.html` - Google Sheets sidebar component

## Main Files
- `reports.html` - Main reports dashboard (stays in root)

## Benefits of This Structure

1. **Better Organization**: Related reports are grouped together
2. **Easier Maintenance**: Developers can quickly find and modify specific report types
3. **Cleaner Navigation**: Logical folder structure makes the codebase more intuitive
4. **Scalability**: Easy to add new reports to appropriate categories
5. **Reduced Clutter**: Main reports directory is no longer overwhelmed with files

## Migration Notes

All route files have been updated to reference the new template paths. The structure maintains backward compatibility while providing better organization for future development.

# Volunteer Recruitment Search

> **Audience:** All logged-in users

## Overview

The Advanced Volunteer Search lets you find volunteers using flexible keyword filters across names, organizations, skills, job titles, industries, and past event participation. Results can be exported to CSV for offline use and outreach.

**Access:** Reports → **Recruitment Tools** → **Advanced Volunteer Search**, or directly at `/reports/recruitment/search`

## Search Modes

| Mode | Behavior | Example |
|---|---|---|
| **Wide Search** (default) | Matches volunteers with **any** search term | `tech edu` → volunteers in technology **OR** education |
| **Narrow Search** | Matches volunteers with **all** search terms | `tech edu` → volunteers in **both** technology **AND** education |

## Searchable Fields

Your search terms are matched against:

- **Volunteer:** first name, last name, job title, industry
- **Organization:** company/school name
- **Skills:** skill tags (e.g., "Engineering", "Animation")
- **Events:** titles of past events the volunteer participated in
- **Event type:** event category (e.g., "Career Fair", "Data Viz")
- **Local status:** volunteer status classification

## Sorting

Click any column header to sort results:

- **Name** (default, A–Z)
- **Organization/Affiliation**
- **Last Non-Internal Email** — most recent non-internal email date
- **Last Volunteer Date** — most recent volunteering activity
- **# of Times Volunteered** — total attended/completed events

## Connector Filter

Click **Connector Only** to show only volunteers with a Pathful (Connector) profile. This is useful for identifying volunteers who are already set up for virtual sessions.

## CSV Export

When search results are displayed, an **Export CSV** button appears in the toolbar. Clicking it downloads all matching volunteers (not just the current page) as a CSV file with these columns:

| Column | Source |
|---|---|
| Name | Volunteer full name |
| Email | Primary email address |
| Title | Job title/position |
| Organization | All affiliated organizations |
| Skills | Semicolon-separated skill tags |
| Last Non-Internal Email Date | Most recent non-internal email |
| Last Volunteer Date | Most recent volunteering activity |
| Times Volunteered | Total attended/completed events |

> [!TIP]
> The CSV includes **all** matching volunteers regardless of pagination. Use the export for mail merges, outreach lists, or analysis in Excel/Google Sheets.

## Technical Reference

| Component | Location |
|---|---|
| **Search route** | `routes/reports/recruitment.py` → `recruitment_search()` |
| **CSV route** | `routes/reports/recruitment.py` → `recruitment_search_csv()` |
| **Template** | `templates/reports/recruitment/recruitment_search.html` |
| **Tests** | `tests/integration/test_recruitment_search.py` (TC-350–TC-353) |
| **FR** | FR-RECRUIT-307 |

---

*Last updated: March 2026*

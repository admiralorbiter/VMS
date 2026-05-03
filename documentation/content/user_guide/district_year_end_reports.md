# District Year-End Reports

This guide covers how to generate, review, and export the District Year-End Reports. These reports are designed to provide high-level and detailed metrics to our school district partners at the end of the academic year.

## 1. Accessing the Reports
1. Navigate to **Reports** → **District Year-End** from the main navigation menu.
2. The dashboard will automatically calculate the current academic year based on the date.
3. You will see a list of all district partners with their high-level metrics displayed in a compact, horizontal statistics strip.

## 2. Reviewing the District Data

### The District Summary Strip
![District Year-End Dashboard](content/user_guide/images/district_year_end_dashboard.png)

For each district, you will see a quick summary:
- **Events**: Total number of events the district participated in.
- **Students**: Total unique students reached.
- **Volunteers**: Total unique volunteers engaged.
- **Hours**: Total volunteer hours delivered.
- **Code**: The unique district identifier (useful for data analysts matching records against external datasets).

### Activity Breakdown
Click **View Full Report** on any district to expand the detailed Activity Breakdown table. This table provides a row-by-row breakdown of every event associated with the district for that academic year.

![Activity Breakdown Detail](content/user_guide/images/district_year_end_detail.png)

#### Breakdown Features:
- **Fast Scannability**: The horizontal layout ensures that the data is easy to scan without excessive scrolling.
- **Accuracy**: The numbers in the summary strip perfectly match the sum of the rows in the Activity Breakdown.
- **Sorting & Filtering**: You can sort by columns like Date, Time, Event, Type, Location, Students, and Volunteers. Use the top filters to narrow down events by specific Event Types.
- **View Toggles**: Switch between **All Events** (a chronological list of all activities) and **By School** (grouped by participating school) to analyze the data from different angles.

## 3. Exporting the Data

Once you have verified the data on the dashboard, you have two primary ways to export it for the district partner:

### Export to Excel
1. Click the **Export to Excel** button on the district's detail view.
2. This generates a professionally formatted `.xlsx` file containing the summary statistics and the full event breakdown.
3. The file is ready to be emailed directly to your district contact.

### Export to Google Sheets
If your district partner prefers Google Sheets (or you need a live link to share):
1. Click the **Push to Google Sheets** button.
2. The system will securely connect to the PrepKC Google Drive.
3. A new spreadsheet will be created (or updated if one already exists for this year).
4. A direct link to the Google Sheet will be provided on the screen, which you can easily copy and share.

## 4. Troubleshooting
- **Missing Events?** Ensure that the events in Salesforce or VolunTeach are properly tagged with the district name or school name. The system matches events using a combination of the district alias and school relationships.
- **Sync Issues?** If you know an event occurred recently but it isn't showing up, check the [Data Quality Dashboard](reporting#data-quality-dashboard) to ensure the Salesforce sync didn't encounter any errors.

---

*Last updated: May 3, 2026*
*Version: 1.0*

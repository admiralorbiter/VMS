# Volunteer Recruitment

This guide assists staff in finding, vetting, and managing volunteers for events using the Volunteer Directory and Advanced Recruitment Search.

## 1. Volunteer Directory

The Volunteer Directory is the primary interface for browsing and filtering the volunteer database.

![Volunteer Directory](content/images/vol_directory.png)

### Key Features
-   **Access**: Click `Volunteers` in the top navigation.
-   **Standard Filters**:
    -   **Name Search**: Search by first or last name.
    -   **Organization/Role**: Search by Organization Name, Job Title, Department, or Industry.
    -   **Local Status**: Filter by "Local" (in-person available) or "Non-Local".
    -   **Email**: Search by email address.
    -   **Skills**: Search for specific skills (e.g., "Python", "Public Speaking").
-   **Connector Only**: Check this box to filter for volunteers who are Connectors (Virtual).
-   **Actions**:
    -   **Apply Filters**: Updates the list based on criteria.
    -   **Reset**: Clears all filters.
    -   **Advanced Search**: Opens the specialized Recruitment Search tool.

## 2. Advanced Search & Matching

The Recruitment Search tool allows for powerful, multi-criteria searches to find the perfect candidates for specific opportunities.

![Advanced Search](content/images/adv_search.png)

### Search Fields & Capabilities

#### Volunteer Information
-   **First Name**: Exact or partial matches.
-   **Last Name**: Exact or partial matches.
-   **Title/Position**: Matches against job title or role.

#### Organization & Affiliation
-   **Organization Name**: Matches company, school, or institution names.

#### Skills & Expertise
-   **Skill Names**: Matches specific skills (e.g., Programming, Teaching, Mentoring).

#### Event Participation
-   **Event Titles**: Searches past events the volunteer participated in.

### Search Modes
-   **Wide Search (OR)**: Finds volunteers matching *any* of the entered terms. Good for broad discovery.
    -   *Example*: "tech edu" finds volunteers in Technology OR Education.
-   **Narrow Search (AND)**: Finds volunteers matching *all* entered terms. Good for specific requirements.
    -   *Example*: "tech edu" finds volunteers in BOTH Technology AND Education.

### Search Tips
-   **Partial Matches**: "prog" will find "programming", "programmer", etc.
-   **Multiple Terms**: Use spaces to separate different search concepts.
-   **Intelligent Matching**: Results are ranked by relevance score (keyword matches, availability, and history).

## 3. Managing Profiles

Click any volunteer name to view their **Profile**:
-   **Communication Log**: View emails sent/received (via Salesforce sync).
-   **Notes**: Add recruitment notes (e.g., "Interested in robotics events").
-   **History**: View all past event participation.

## 4. Logging Communication (Salesforce Gmail Integration)

To ensure all volunteer communication is tracked in Polaris, internal staff must log emails using the Salesforce Gmail integration. These logs sync to the volunteer's profile history.

### Setup
Ensure you have the [Salesforce Chrome Extension](https://chromewebstore.google.com/detail/salesforce/jjghhkepijgakdammjldcbnjehfkfmha?pli=1) installed.

### How to Log an Email
1.  Open the email you want to log in Gmail.
2.  Click the Salesforce icon in the browser extension bar (top right).
    ![Salesforce Extension Icon](content/user_guide/images/gmail_extension_bar.png)
3.  The Salesforce side panel will open. It attempts to match the email sender/recipient to a Salesforce record.
4.  If the record is found, click **Log Now**.
    ![Log Email Pane](content/user_guide/images/gmail_log_pane.png)
5.  If not found, use the search bar in the pane to find the correct contact.

> [!TIP]
> **Log Everything**: Log all emails related to volunteering, including those with potential volunteers, partners, and existing volunteers.

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-401](user_stories#us-401), [US-402](user_stories#us-402), [US-403](user_stories#us-403), [US-404](user_stories#us-404), [US-405](user_stories#us-405), [US-406](user_stories#us-406) |
| **Requirements** | [FR-RECRUIT-301](requirements#fr-recruit-301) through [FR-RECRUIT-311](requirements#fr-recruit-311) |

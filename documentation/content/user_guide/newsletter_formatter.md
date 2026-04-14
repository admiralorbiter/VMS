# Newsletter Formatter

The Newsletter Formatter is a productivity tool that generates formatted, hyperlinked text for newsletters. It supports two modes — **Virtual Connector** (grade-grouped virtual sessions) and **Career Exploration Events** (section-grouped in-person events) — and produces copy-paste-ready rich HTML with clickable sign-up links.

## Accessing the Tool

1. Log in to Polaris
2. Click the **More ›** button in the top navigation bar to open the side panel
3. Under the **Tools** section, click **Newsletter Formatter**

## Mode Toggle

At the top of the page, two tabs let you switch between modes:

| Mode | What it shows | Link source |
|------|--------------|-------------|
| **Virtual Connector** | Upcoming virtual sessions grouped by grade level | Configurable Google Forms URL (⚙ gear icon) |
| **Career Exploration Events** | Upcoming in-person events grouped by section | `Registration_Link__c` from Salesforce (per-event) |

## Virtual Connector Mode

### 1. Sessions Load Automatically

Fetches all upcoming virtual sessions that are **Confirmed** or **Published**. Sessions are grouped by grade level:

- **Kindergarten** — Titles starting with `K:` or `K-1:` / `K-2:`
- **First Grade** through **Fifth Grade** — Titles starting with grade prefixes like `1st Grade:`, `2nd Grade:`, etc.
- **General / KC Series** — Sessions without a recognized grade prefix (deselected by default)

> [!INFO]
> Multi-grade sessions (e.g., `2-5: The Museum of the American Revolution`) appear in **all** matching grade groups automatically.

### 2. Select Sessions

- Grade-specific sessions are **checked by default**; "General / KC Series" is **unchecked by default**
- Each grade section has **✓ All** / **✕ None** buttons and a group checkbox
- Use the global toolbar buttons: **✓ All** / **✕ None** / **Expand** / **Collapse**
- Use the **search/filter** box to quickly find sessions by name
- Deselected sessions appear dimmed with strikethrough text

### 3. Preview and Copy

1. Review the formatted output in the **Preview** panel on the right
2. Each session title appears as a **clickable hyperlink** to the Google Forms sign-up URL
3. Click the green **📋 Copy to Clipboard** button
4. Paste directly into your newsletter email — **links stay clickable** in Outlook, Gmail, etc.

### 4. Change the Sign-Up URL

Click the **⚙ gear icon** in the toolbar to open **Newsletter Settings**. The URL is saved in your browser and persists between sessions.

## Career Exploration Events Mode

### 1. Events Load Automatically

Fetches all upcoming in-person events that are **Confirmed** or **Published**, grouped by section:

| Section | Event Types | Default |
|---------|------------|---------|
| **Career Jumping** | Career Jumping | ✅ On |
| **Career Speakers** | Career Speaker | ✅ On |
| **Career Fair** | Career Fair | ✅ On |
| **Other Events** | Classroom Speaker, Workplace Visit | ⬜ Off |

### 2. Date/Time Format

Events display in the newsletter format: **Thursday, April 2nd, from 8:30-10:30 AM**

- Day name, month, ordinal day
- Time range with collapsed AM/PM when both times share the same period
- If the event is imported without a specific time, it defaults to a placeholder: `, from X:00-X:00 AM` (In-Person) or `at X:00 am` (Virtual).

### 3. Links from Salesforce

Each event's link comes from the `Registration_Link__c` field in Salesforce (imported during the event sync). The ⚙ gear icon is hidden in this mode since links are per-event rather than a single configurable URL.

> [!TIP]
> If an event is missing its sign-up link, check that `Registration_Link__c` is populated for that session in Salesforce, then re-run the event import.

### 4. Select, Preview, and Copy

Selection controls work identically to Virtual mode — checkboxes, **✓ All / ✕ None**, expand/collapse, and search/filter. The clipboard output adapts to the in-person format automatically.

## FAQ

**Q: Why is a session missing?**
A: The tool only shows sessions with a future date and a status of **Confirmed** or **Published**. Check the session's status in the Events page.

**Q: A session appears in the wrong grade group (Virtual).**
A: Grade grouping is based on the session title prefix. If a title doesn't follow the standard naming convention (e.g., `3rd Grade: Topic Name`), it will fall into "General / KC Series".

**Q: Why are General / KC Series or Other Events unchecked?**
A: These sections are deselected by default since they're typically not included in the main newsletter. You can opt in by checking the box.

**Q: An in-person event has no hyperlink.**
A: The link comes from Salesforce's `Registration_Link__c` field. Run a full event import to populate it, or check that the field has a value in Salesforce.

**Q: Why does a session show `X:00 AM` for its time?**
A: If a session was imported from Pathful or Salesforce without a specific time attached to it (i.e. just a date), the tool automatically displays an `X:00 AM` placeholder. This preserves the correct day without guessing the schedule, making it easy for you to type over it before sending the newsletter.

---

*Last updated: March 17, 2026*

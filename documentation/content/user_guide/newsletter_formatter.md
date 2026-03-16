# Newsletter Formatter

The Newsletter Formatter is a productivity tool that generates formatted, hyperlinked text for the Pathful virtual sessions newsletter. It pulls upcoming sessions from the database, lets you choose which sessions to include, and produces copy-paste-ready rich HTML organized by grade level — with each session title linked to the Google Forms sign-up page.

## Accessing the Tool

1. Log in to Polaris
2. Click the **More ›** button in the top navigation bar to open the side panel
3. Under the **Tools** section, click **Newsletter Formatter**

## How It Works

### 1. Sessions Load Automatically

When you open the tool, it fetches all upcoming virtual sessions that are **Confirmed** or **Published**. Sessions are automatically grouped by grade level:

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
- Each grade header shows a count (e.g., "5 of 7 selected")

### 3. Preview and Copy

1. Review the formatted output in the **Preview** panel on the right
2. Each session title appears as a **clickable hyperlink** to the Google Forms sign-up URL
3. Click the green **📋 Copy to Clipboard** button
4. Paste directly into your newsletter email — **links stay clickable** in Outlook, Gmail, etc.

> [!TIP]
> The copy uses rich HTML (`text/html` MIME type) so hyperlinks are preserved when pasted into email clients. A plain-text fallback is included for apps that don't support rich text.

### 4. Change the Sign-Up URL

Click the **⚙ gear icon** in the toolbar to open **Newsletter Settings**. From here you can update the Google Forms sign-up URL that session titles link to. The setting is saved in your browser and persists between sessions. Click **Reset Default** to restore the original URL.

## FAQ

**Q: Why is a session missing?**
A: The tool only shows sessions with a future date and a status of **Confirmed** or **Published**. Check the session's status in the Virtual Sessions page.

**Q: A session appears in the wrong grade group.**
A: Grade grouping is based on the session title prefix. If a title doesn't follow the standard naming convention (e.g., `3rd Grade: Topic Name`), it will fall into "General / KC Series". Edit the session title to include the correct prefix.

**Q: Why are General / KC Series sessions unchecked?**
A: These sessions are deselected by default since they're typically not included in grade-specific newsletter sections. You can opt in to any of them by checking the box.

---

*Last updated: March 16, 2026*

# Functional Requirements — Internal Tools

**Scope:** Internal productivity tools available to all authenticated users via the **Tools** sidebar section.

---

## Quick Navigation

| ID | Title | Related Use Cases |
|----|-------|-------------------|
| [FR-TOOLS-101](#fr-tools-101) | Newsletter Formatter Page | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-102](#fr-tools-102) | Session Data Endpoint | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-103](#fr-tools-103) | Grade-Level Parsing | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-104](#fr-tools-104) | Session Selection & Grouping | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-105](#fr-tools-105) | Default Deselection of General Sessions | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-106](#fr-tools-106) | Hyperlinked Preview | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-107](#fr-tools-107) | Rich HTML Clipboard Copy | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-108](#fr-tools-108) | Configurable Sign-Up Form URL | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-109](#fr-tools-109) | Search & Filter Sessions | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-110](#fr-tools-110) | Mode Toggle (Virtual / In-Person) | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-111](#fr-tools-111) | In-Person Session Data Endpoint | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-112](#fr-tools-112) | In-Person Section Grouping | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-113](#fr-tools-113) | In-Person Date/Time Formatting | [UC-22](use-cases#uc-22) |
| [FR-TOOLS-114](#fr-tools-114) | Registration Link Import | [UC-22](use-cases#uc-22) |

---

## Newsletter Formatter — Virtual Mode

---

### <a id="fr-tools-101"></a>FR-TOOLS-101: Newsletter Formatter Page

The system shall provide a **Newsletter Formatter** page at `/tools/newsletter-formatter`, accessible to all authenticated users via the Tools sidebar section.

**Acceptance:** Page renders with sessions panel (left) and preview panel (right).

---

### <a id="fr-tools-102"></a>FR-TOOLS-102: Session Data Endpoint

The system shall provide a JSON API at `/tools/newsletter-formatter/sessions` that returns all upcoming virtual sessions (`EventType.VIRTUAL_SESSION`) with status `CONFIRMED` or `PUBLISHED` and a `start_date` in the future, ordered by `start_date ASC`.

**Response fields per session:** `id`, `title`, `date`, `time`, `formatted_datetime`, `grade_levels`, `status`.

---

### <a id="fr-tools-103"></a>FR-TOOLS-103: Grade-Level Parsing

The system shall parse grade levels from session title prefixes using ordered pattern matching:

| Prefix | Mapped Grades |
|--------|---------------|
| `K:` | Kindergarten |
| `K-1:` | Kindergarten, First Grade |
| `K-2:` | Kindergarten, First Grade, Second Grade |
| `1st Grade:` | First Grade |
| `2nd Grade:` | Second Grade |
| `3rd Grade:` | Third Grade |
| `4th Grade:` | Fourth Grade |
| `5th Grade:` | Fifth Grade |
| `2-3:` | Second Grade, Third Grade |
| `2-5:` | Second Grade, Third Grade, Fourth Grade, Fifth Grade |
| `4-5 Grade` | Fourth Grade, Fifth Grade |
| *(no match)* | General / KC Series |

First regex match wins. Sessions with multi-grade spans appear in all matched groups.

---

### <a id="fr-tools-104"></a>FR-TOOLS-104: Session Selection & Grouping

The UI shall display sessions grouped by grade level in canonical order (Kindergarten → Fifth Grade → General / KC Series). Each grade group shall include:

- A **group checkbox** (checked / indeterminate / unchecked)
- **✓ All / ✕ None** inline buttons
- A **selected count** label (e.g., "5 of 7 selected")
- A **collapsible body** toggled by clicking the header

Deselected sessions shall appear dimmed with strikethrough text.

---

### <a id="fr-tools-105"></a>FR-TOOLS-105: Default Deselection of General Sessions

Sessions mapped **only** to "General / KC Series" shall be **unchecked by default** on page load. Sessions belonging to both a grade group and General / KC Series shall remain checked.

---

### <a id="fr-tools-106"></a>FR-TOOLS-106: Hyperlinked Preview

The preview panel shall render each session title as a **clickable hyperlink** pointing to the configured sign-up form URL ([FR-TOOLS-108](#fr-tools-108)).

---

### <a id="fr-tools-107"></a>FR-TOOLS-107: Rich HTML Clipboard Copy

The "Copy to Clipboard" button shall write to the clipboard using the Clipboard API with two MIME types:

- `text/html` — Rich HTML with inline styles and hyperlinked session titles (for email clients)
- `text/plain` — Aligned plain-text fallback (date padded to 22 chars + title)

---

### <a id="fr-tools-108"></a>FR-TOOLS-108: Configurable Sign-Up Form URL

The system shall allow the user to **view and edit** the sign-up form URL via a settings modal accessible from the toolbar (gear icon). The URL shall be persisted in `localStorage` (key: `nf_form_url`). A **Reset Default** button shall restore the original URL.

**Default URL:** `https://docs.google.com/forms/d/e/1FAIpQLSe_2_abnJzfrUuirq4oCr5L-vzeVYAKWS-1IfQtT8ROEr9DHw/viewform`

---

### <a id="fr-tools-109"></a>FR-TOOLS-109: Search & Filter Sessions

The toolbar shall include a search input that filters visible sessions in real time by title substring match (case-insensitive). Grade groups with no visible sessions after filtering shall be hidden. A clear button shall reset the filter.

---

## Newsletter Formatter — In-Person Mode

---

### <a id="fr-tools-110"></a>FR-TOOLS-110: Mode Toggle (Virtual / In-Person)

The Newsletter Formatter page shall provide a tabbed mode toggle with two options: **Virtual Connector** (default) and **Career Exploration Events**. Switching modes shall fetch the appropriate data endpoint and re-render the sessions panel. All toolbar actions (Select All, Deselect, Expand, Collapse, Search, Copy) shall be mode-aware.

**Acceptance:** Clicking tabs switches modes; settings gear hidden in in-person mode.

---

### <a id="fr-tools-111"></a>FR-TOOLS-111: In-Person Session Data Endpoint

The system shall provide a JSON API at `/tools/newsletter-formatter/in-person-sessions` that returns all upcoming in-person events with types `CAREER_JUMPING`, `CAREER_SPEAKER`, `CAREER_FAIR`, `CLASSROOM_SPEAKER`, or `WORKPLACE_VISIT`, status `CONFIRMED` or `PUBLISHED`, and `start_date` in the future, ordered by `start_date ASC`.

**Response fields per session:** `id`, `title`, `formatted_datetime`, `section`, `school_name`, `district`, `link`, `status`.

**Response also includes:** `section_order` (ordered list of section names) and `default_off_sections` (sections unchecked by default).

---

### <a id="fr-tools-112"></a>FR-TOOLS-112: In-Person Section Grouping

In-person events shall be grouped into four sections in this order:

| Section | Event Types |
|---------|------------|
| Career Jumping | `CAREER_JUMPING` |
| Career Speakers | `CAREER_SPEAKER` |
| Career Fair | `CAREER_FAIR` |
| Other Events | `CLASSROOM_SPEAKER`, `WORKPLACE_VISIT` |

"Other Events" shall be **unchecked by default** on page load.

---

### <a id="fr-tools-113"></a>FR-TOOLS-113: In-Person Date/Time Formatting

In-person event dates shall be formatted as: **Thursday, April 2nd, from 8:30-10:30 AM**

- Day name, month name, ordinal day suffix (1st, 2nd, 3rd, 4th…)
- When start and end share the same AM/PM period, show collapsed format (e.g., `8:30-10:30 AM`)
- When they differ, show full format (e.g., `11:00 AM to 1:00 PM`)
- If no end time, show only start time with AM/PM

---

### <a id="fr-tools-114"></a>FR-TOOLS-114: Registration Link Import

The Salesforce event import shall extract the `Registration_Link__c` field from Session records and store the clean URL in `Event.registration_link`. The field value in Salesforce is HTML (`<a href="url">Sign up</a>`); the import shall extract only the `href` URL.

**Acceptance:** After a full event import, all sessions with a `Registration_Link__c` value in Salesforce have a clean URL in `registration_link`.

---

## Related Documentation

- [User Stories — Epic 14: Internal Tools](user-stories#epic-14)
- [Use Cases — UC-22: Newsletter Formatter](use-cases#uc-22)
- [User Guide — Newsletter Formatter](../user_guide/newsletter_formatter)

---

*Last updated: March 17, 2026 · Version 1.1*

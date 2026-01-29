# VMS Documentation Content

This directory contains all markdown content for the VMS public documentation.

## File Organization

Each markdown file represents a single documentation page:

- `getting_started.md` - Welcome and overview page (default)
- `user_guide.md` - Comprehensive user instructions *(planned)*
- `reports.md` - Report documentation *(planned)*
- `architecture.md` - System architecture guide *(planned)*
- `api_reference.md` - API documentation *(planned)*
- `deployment.md` - Deployment instructions *(planned)*

## Adding New Content

### 1. Create a Markdown File

Create a new `.md` file in this directory:

```bash
# Example: creating a new page
touch content/new_page.md
```

### 2. Write Your Content

Use standard markdown syntax with these enhancements:

#### Callouts

Use blockquotes with special markers:

```markdown
> [!INFO]
> This is an informational callout.

> [!WARNING]
> This is a warning callout.

> [!DANGER]
> This is a danger/error callout.

> [!SUCCESS]
> This is a success callout.

> [!NOTE]
> This is a note (Source of Truth) callout.
```

#### Code Blocks

Use fenced code blocks with language specification:

```markdown
```python
def hello_world():
    print("Hello, VMS!")
```
```

#### Tables

Standard markdown tables work great:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
```

### 3. Update Navigation

Add your page to the navigation in `index.html`:

```html
<div class="nav-section">
    <div class="nav-section-title">Section Name</div>
    <a href="#new-page" class="nav-link" data-page="new_page">
        Page Title
    </a>
</div>
```

**Important Notes:**
- Use underscores (`_`) in the filename: `new_page.md`
- Use hyphens (`-`) in the URL hash: `#new-page`
- Set `data-page` attribute to match filename (without extension)

## Styling Guidelines

### Headings

- `# H1` - Page title (use once at top)
- `## H2` - Major sections
- `### H3` - Subsections
- `#### H4` - Minor subsections

### Emphasis

- `**bold**` - Important terms, UI elements
- `*italic*` - Emphasis, new concepts
- `` `code` `` - Inline code, filenames, commands

### Lists

Use bulleted lists for unordered items:

```markdown
- Item 1
- Item 2
  - Nested item
- Item 3
```

Use numbered lists for sequential steps:

```markdown
1. First step
2. Second step
3. Third step
```

### Links

```markdown
[Link text](https://example.com)
[Another page](#page-name)
```

## Content Best Practices

### Writing Style

- **Clear and Concise** - Use simple, direct language
- **User-Focused** - Write for your audience's level
- **Consistent Terminology** - Use the same terms throughout
- **Active Voice** - Prefer active over passive voice
- **Present Tense** - Use present tense for current features

### Structure

- **Start with Overview** - Begin each page with context
- **Logical Flow** - Organize content in a natural progression
- **Scannable** - Use headings and lists for easy scanning
- **Examples** - Include practical examples and use cases
- **Next Steps** - End with clear next actions

### Maintenance

- **Keep Updated** - Review and update regularly
- **Version Information** - Note when content was last updated
- **Remove Outdated** - Delete or archive old content
- **Cross-Reference** - Link to related pages

## Technical Details

### Markdown Rendering

Content is rendered using [marked.js](https://marked.js.org/), which supports:

- GitHub Flavored Markdown (GFM)
- Tables
- Task lists
- Strikethrough
- Automatic URL linking

### File Naming

- Use lowercase letters
- Use underscores for spaces: `user_guide.md`
- Use descriptive names: `api_reference.md`
- Keep names concise but clear

### Front Matter

Future enhancement: YAML front matter for metadata

```yaml
---
title: Page Title
description: Brief description
tags: [tag1, tag2]
last_updated: 2026-01-21
---
```

## Testing Your Content

1. **Preview Locally** - Open `index.html` in your browser
2. **Check Links** - Verify all internal and external links work
3. **Test Rendering** - Ensure markdown renders correctly
4. **Mobile Check** - View on mobile devices
5. **Proofread** - Check spelling and grammar

## Need Help?

- Review existing pages for examples
- Check the main documentation at `/docs/living/`
- Contact the documentation maintainer
- Submit issues or suggestions

---

*This documentation system is designed for easy expansion and maintenance. Add content freely!*

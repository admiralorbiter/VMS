# VMS Documentation Site

This is the documentation microsite for the Volunteer Management System (VMS). It provides comprehensive guides for users and administrators.

## Structure

```
documentation/
├── css/
│   └── style.css          # Shared styles for all pages
├── js/
│   └── nav.js            # Navigation functionality
├── nav.html              # Shared navigation template
├── index.html            # Main documentation page
├── reports.html          # Reports documentation
└── README.md           # This file
```

## Features

- **Responsive Design**: Works on desktop and mobile devices
- **Consistent Styling**: Shared CSS ensures uniform appearance
- **Dynamic Navigation**: Shared navigation template loaded via JavaScript
- **Interactive Navigation**: Active state management and smooth transitions
- **Expandable Sections**: Collapsible content for better organization
- **Step-by-step Guides**: Numbered steps for complex procedures
- **Callout Boxes**: Tips, warnings, and information highlights

## Development Guidelines

### Adding New Pages

1. Create a new HTML file in the root documentation directory
2. Use the standard template structure:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Page Title - VMS Documentation</title>
       <link rel="stylesheet" href="css/style.css">
   </head>
   <body>
       <div class="container">
           <nav class="sidebar">
               <!-- Navigation will be loaded dynamically -->
           </nav>
           <main class="main-content">
               <!-- Page content -->
           </main>
       </div>
       <script src="js/nav.js"></script>
   </body>
   </html>
   ```

3. Update the `nav.html` file to include the new page link
4. The active state will be set automatically based on the current page

### Adding New Navigation Items

To add a new section to the navigation:

1. Edit `nav.html` and add a new link:
   ```html
   <a class="nav-item" href="new-page.html">New Section</a>
   ```

2. Create the corresponding HTML file following the template structure

### CSS Classes

- **Layout**: `.container`, `.sidebar`, `.main-content`
- **Navigation**: `.nav-item`, `.nav-item.active`, `.nav-section-title`
- **Content**: `.section-header`, `.section-title`, `.section-description`
- **Interactive**: `.expandable`, `.expandable-header`, `.expandable-content`
- **Steps**: `.step-list`, `.step-item`
- **Callouts**: `.callout`, `.callout-tip`, `.callout-warning`, `.callout-info`
- **Cards**: `.feature-card`, `.task-card`

### JavaScript Features

- Dynamic navigation loading from `nav.html`
- Automatic active state management for navigation
- Expandable section toggling
- Feature card click handling
- Error handling for navigation loading

## Content Guidelines

- Use clear, concise language
- Include step-by-step instructions for complex tasks
- Add callout boxes for important information
- Use expandable sections to organize related content
- Include practical examples where helpful

## Future Enhancements

- Search functionality
- Table of contents for long pages
- Print-friendly styles
- Dark mode support
- Interactive demos
- Video tutorials integration

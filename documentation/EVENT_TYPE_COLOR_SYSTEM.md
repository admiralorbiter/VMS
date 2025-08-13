# Event Type Color Mapping System

## Overview

The VMS application now includes a comprehensive, centralized color mapping system for all event types. This system ensures consistent styling and visual identification of different event types across all templates and components.

## Files Included

### Core CSS File
- `static/css/event_type_colors.css` - Main color mapping definitions

### Updated Templates
- `templates/base.html` - Includes the color CSS globally
- `templates/reports/volunteer_thankyou_detail.html` - Updated event type display
- `templates/reports/organization_thankyou_detail.html` - Updated event type display
- `templates/events/events.html` - Updated event type badges
- `templates/events/view.html` - Updated event type badges
- `templates/volunteers/view.html` - Updated event type badges
- `templates/reports/district_year_end_detail.html` - Updated event type display
- `templates/reports/pathway_detail.html` - Updated event type display
- `templates/reports/recruitment_report.html` - Updated event type display

### Utility Functions
- `utils/__init__.py` - Added `format_event_type_for_badge()` function
- `app.py` - Registered Jinja2 filter for event type formatting

## Usage

### Basic HTML Structure
```html
<span class="event-type-badge {{ event.type|replace('_', '-') }}">
    {{ event.type|replace('_', ' ')|title }}
</span>
```

### With Table Cell Wrapper
```html
<td class="event-type-cell">
    <span class="event-type-badge {{ event.type|replace('_', '-') }}">
        {{ event.type|replace('_', ' ')|title }}
    </span>
</td>
```

### Using the Utility Filter (Alternative)
```html
<span class="event-type-badge {{ event.type|event_type_badge|first }}">
    {{ event.type|event_type_badge|last }}
</span>
```

## Color Categories

### Career Development Events
- **Primary Color**: Sea Green (#2E8B57)
- **Light Color**: Pale Green (#98FB98)
- **Event Types**:
  - `career_fair` - Primary background, white text
  - `career_speaker` - Light background, primary text
  - `career_jumping` - Primary background, white text
  - `employability_skills` - Light background, primary text

### Educational Events
- **Primary Color**: Royal Blue (#4169E1)
- **Light Color**: Light Blue (#ADD8E6)
- **Event Types**:
  - `classroom_speaker` - Primary background, white text
  - `classroom_activity` - Light background, primary text
  - `advisory_sessions` - Primary background, white text
  - `in_person` - Primary background, white text

### Virtual Events
- **Primary Color**: Blue Violet (#8A2BE2)
- **Light Color**: Lavender (#E6E6FA)
- **Event Types**:
  - `virtual_session` - Primary background, white text
  - `connector_session` - Light background, primary text

### Workplace Events
- **Primary Color**: Dark Orange (#FF8C00)
- **Light Color**: Moccasin (#FFE4B5)
- **Event Types**:
  - `workplace_visit` - Primary background, white text
  - `pathway_workplace_visits` - Light background, primary text

### College Preparation Events
- **Primary Color**: Crimson (#DC143C)
- **Light Color**: Light Pink (#FFB6C1)
- **Event Types**:
  - `college_options` - Primary background, white text
  - `college_application_fair` - Light background, primary text
  - `campus_visit` - Primary background, white text
  - `pathway_campus_visits` - Light background, primary text

### Special Programs
- **Primary Color**: Medium Purple (#9370DB)
- **Light Color**: Plum (#DDA0DD)
- **Event Types**:
  - `ignite` - Primary background, white text
  - `p2gd` - Primary background, white text
  - `p2t` - Primary background, white text
  - `sla` - Light background, primary text
  - `bfi` - Light background, primary text

### Financial Education
- **Primary Color**: Lime Green (#32CD32)
- **Light Color**: Honeydew (#F0FFF0)
- **Event Types**:
  - `financial_literacy` - Primary background, white text
  - `fafsa` - Primary background, white text

### Other Categories
- **Mentoring**: Light Sea Green (#20B2AA)
- **Volunteer Management**: Tomato (#FF6347)
- **Math Events**: Deep Pink (#FF1493)
- **DIA Events**: Orange Red (#FF4500)
- **Health Programs**: Dark Turquoise (#00CED1)
- **Internships**: Saddle Brown (#8B4513)
- **Historical/Data**: Dim Gray (#696969)

## CSS Classes and Modifiers

### Size Modifiers
```css
.event-type-badge.small    /* Smaller padding and font */
.event-type-badge.large    /* Larger padding and font */
```

### Interactive Modifiers
```css
.event-type-badge.clickable    /* Adds cursor pointer and enhanced hover */
```

### Utility Classes
```css
.event-type-cell    /* Centers badge in table cells */
```

## Responsive Behavior

The badges automatically adjust on mobile devices:
- Smaller font size (0.75rem)
- Reduced padding (0.3rem 0.8rem)
- Tighter letter spacing (0.3px)

## Accessibility Features

- High contrast color combinations
- Focus states with outline
- Semantic HTML structure
- Screen reader friendly text

## Adding New Event Types

To add a new event type:

1. **Add CSS Rule** in `static/css/event_type_colors.css`:
```css
.event-type-badge.new-event-type {
    background-color: var(--your-color);
    color: white;
    border-color: var(--your-color);
}
```

2. **Add Color Variable** (optional) at the top of the CSS file:
```css
:root {
    --your-color: #HEXCODE;
}
```

3. **Update Documentation** in this file with the new event type.

## Browser Support

- Modern browsers (Chrome 60+, Firefox 55+, Safari 12+, Edge 79+)
- CSS Custom Properties (CSS Variables) support required
- Flexbox support required

## Performance Notes

- CSS file is loaded globally for consistency
- Uses CSS custom properties for maintainable theming
- Minimal impact on page load times (~3KB gzipped)

## Troubleshooting

### Event Type Not Displaying Correctly
1. Check that the event type class matches the CSS selector
2. Ensure underscores are converted to dashes: `virtual_session` → `virtual-session`
3. Verify the CSS file is loaded in the template

### Colors Not Applying
1. Check browser developer tools for CSS conflicts
2. Ensure the base template includes the color CSS file
3. Verify CSS custom properties are supported

### Missing Event Types
1. Check if the event type has a defined CSS rule
2. Add new CSS rule following the pattern above
3. Unknown event types will use the default fallback styling

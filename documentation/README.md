# VMS Public Documentation

This directory contains the public-facing documentation system for the Volunteer Management System (VMS).

## 🚀 Quick Start

### Via Flask Server (Recommended)

The documentation is integrated with your Flask application:

```bash
# Start the Flask server
python app.py

# Then visit: http://localhost:5050/docs/
# (Port may vary - check your Flask server output)
```

The documentation is automatically served at the `/docs/` endpoint.

### Alternative: Standalone Python Server

If you want to test the documentation independently:

```bash
# From the documentation directory
cd documentation
python -m http.server 8000

# Then visit: http://localhost:8000
```

> **Note:** Opening `index.html` directly in your browser (file:// protocol) won't work due to CORS restrictions. Always use an HTTP server.

## 📁 Structure

```
documentation/
├── index.html              # Main entry point with navigation
├── css/
│   └── style.css          # Complete styling system
├── js/
│   └── nav.js             # Dynamic markdown loading & routing
├── content/
│   ├── getting_started.md # Welcome page (default)
│   └── README.md          # Content authoring guide
└── README.md              # This file
```

## ✨ Features

### Dynamic Content Loading
- Loads markdown files on-demand
- No page refresh required
- Smooth transitions between pages

### Navigation System
- Sidebar navigation with sections
- Active link highlighting
- URL hash routing for deep linking
- "Coming soon" badges for planned content

### Markdown Enhancement
- GitHub Flavored Markdown support
- Custom callout blocks (info, warning, danger, success)
- Automatic table wrapping with styled headers
- Code syntax highlighting
- Responsive tables
- Automatic Quick Navigation card transformation (emoji + title + description)

### Professional Styling
- Modern, clean design with sans-serif system fonts
- Two-column layout (260px sidebar + main content)
- Polaris-style card-based Quick Navigation grid
- Bold typography and blue accent colors
- Mobile responsive (< 900px)
- Print-friendly styles
- Dark navigation panel with brownish-orange active state

## 📝 Adding New Content

### 1. Create Content File

Create a new markdown file in `content/`:

```bash
# Example
echo "# My New Page" > content/my_new_page.md
```

### 2. Update Navigation

Edit `index.html` to add your page to the navigation:

```html
<div class="nav-section">
    <div class="nav-section-title">Section Name</div>
    <a href="#my-new-page" class="nav-link" data-page="my_new_page">
        My New Page
    </a>
</div>
```

**Important:**
- Filename uses underscores: `my_new_page.md`
- URL hash uses hyphens: `#my-new-page`
- `data-page` matches filename without extension

### 3. Test Your Page

Open the documentation and click your new link!

## 🎨 Content Styling

### Callouts

Use special blockquote markers:

```markdown
> [!INFO]
> Informational message

> [!WARNING]
> Warning message

> [!DANGER]
> Error or critical message

> [!SUCCESS]
> Success message

> [!NOTE]
> Source of Truth / Important note
```

### Code Blocks

```markdown
```python
def example():
    return "Hello VMS!"
```
```

### Tables

```markdown
| Header 1 | Header 2 |
|----------|----------|
| Data 1   | Data 2   |
```

## 🔧 Technical Details

### Dependencies

- **marked.js** - Markdown parser (loaded via CDN)
- **IBM Plex Mono** - Monospace font for code blocks (loaded via Google Fonts)
- **System Fonts** - Uses native system fonts for body text (no external font loading)

### Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

### No Build Required

This is a pure HTML/CSS/JS system:
- No compilation needed
- No package.json or dependencies
- Works on any static file server
- Easy to deploy and maintain

## 🚀 Deployment

### Option 1: Flask Integration (Current Setup)

The documentation is already integrated with your Flask application at `/docs/`:

```python
# In app.py - already configured
@app.route("/docs/")
@app.route("/docs")
def documentation_index():
    return send_from_directory("documentation", "index.html")

@app.route("/docs/<path:filename>")
def documentation(filename):
    return send_from_directory("documentation", filename)
```

When you deploy your Flask app (e.g., to PythonAnywhere), the documentation is automatically available at `/docs/`.

**Benefits:**
- No separate deployment needed
- Same authentication/security context as main app
- Easy to add access controls later
- Single deployment process

### Option 2: Static File Server

Copy the entire `documentation/` folder to any static web server:

```bash
# Example: Copy to web root
cp -r documentation /var/www/html/docs
```

### Option 3: GitHub Pages

Push to a GitHub repository and enable GitHub Pages:

1. Push `documentation/` folder to repo
2. Settings → Pages → Source: main branch / docs folder
3. Access at: `https://yourusername.github.io/vms/`

### Option 4: Netlify/Vercel

Deploy directly from your repository:

1. Connect your repo
2. Set build directory to `documentation/`
3. No build command needed
4. Deploy!

## 📊 File Sizes

- `index.html` - ~3 KB
- `style.css` - ~6.3 KB
- `nav.js` - ~10.5 KB
- `getting_started.md` - ~2.5 KB
- **Total:** ~22.3 KB (excluding external fonts)

Very lightweight and fast to load!

## 🧪 Testing Checklist

- [ ] Navigation loads correctly
- [ ] Default page (Getting Started) displays
- [ ] Markdown renders properly
- [ ] Code blocks have syntax highlighting
- [ ] Tables are scrollable
- [ ] Callouts render with colors
- [ ] Active nav link highlights
- [ ] Hash routing works (can refresh on any page)
- [ ] "Coming soon" pages show message
- [ ] Mobile view works (< 900px)
- [ ] Print styles work

## 🛠 Customization

### Change Color Theme

Edit CSS variables in `css/style.css`:

```css
:root {
  --accent: #c45d35;           /* Brownish-orange accent */
  --accent-blue: #007bff;      /* Blue for links */
  --bg: #ffffff;               /* Main background */
  --nav: #282c34;              /* Navigation background */
  --nav-active: #c45d35;       /* Active nav state */
  --text: #1f2328;             /* Primary text */
  --text-bold: #000000;        /* Bold text */
  --muted: #555555;            /* Muted text */
  /* ... more variables ... */
}
```

### Change Default Page

Edit `nav.js`:

```javascript
const CONFIG = {
    defaultPage: 'getting_started',  // Change this
    // ...
};
```

### Add Custom Styling

Add custom CSS at the end of `style.css` or create a new CSS file and link it in `index.html`.

## 📚 Content Guidelines

See `content/README.md` for detailed content authoring guidelines including:

- Writing style recommendations
- Markdown best practices
- Structure guidelines
- Maintenance tips

## 🐛 Troubleshooting

### Markdown Not Rendering

- Check browser console for errors
- Verify marked.js CDN is accessible
- Ensure markdown file exists in `content/`

### Navigation Not Working

- Verify `data-page` attribute matches filename
- Check that hash and filename conventions are correct
- Ensure JavaScript is enabled

### Styling Issues

- Clear browser cache (hard refresh: `Ctrl + Shift + R`)
- Check that CSS file loaded (Network tab)
- Verify IBM Plex Mono font loaded from Google Fonts (only needed for code blocks)

## 📞 Support

For issues or questions:

1. Check `content/README.md` for content guidelines
2. Review existing pages for examples
3. Contact the documentation team
4. Submit issues through proper channels

## 📜 License

Part of the VMS project. See main project LICENSE for details.

---

**Built:** January 2026
**Version:** 1.0
**Maintainer:** VMS Documentation Team

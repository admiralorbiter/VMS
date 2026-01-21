/**
 * VMS Documentation Navigation System
 * Handles dynamic markdown loading, routing, and rendering
 */

// Configuration
const CONFIG = {
    contentPath: '/docs/content/',
    defaultPage: 'getting_started',
    fileExtension: '.md'
};

/**
 * Initialize the documentation system
 */
function init() {
    // Configure marked.js options
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: true,
            mangle: false
        });
    }

    // Set up navigation event listeners
    setupNavigation();

    // Handle initial page load
    handleRouting();

    // Listen for hash changes
    window.addEventListener('hashchange', handleRouting);
}

/**
 * Set up navigation link event listeners
 */
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const page = link.getAttribute('data-page');

            // Check if page exists (not "coming soon")
            if (link.querySelector('.badge-ref')) {
                e.preventDefault();
                showComingSoon(link.textContent.trim());
                return;
            }

            // Let the hash change handler load the page
        });
    });
}

/**
 * Handle routing based on URL hash
 */
function handleRouting() {
    const hash = window.location.hash.slice(1); // Remove the '#'

    // Determine which page to load
    let pageName = CONFIG.defaultPage;

    if (hash) {
        // Convert hash to page name (e.g., 'getting-started' -> 'getting_started')
        pageName = hash.replace(/-/g, '_');
    }

    // Load the page
    loadPage(pageName);

    // Update active nav link
    updateActiveNavLink(pageName);
}

/**
 * Load and render a markdown page
 * @param {string} pageName - Name of the page to load (without extension)
 */
async function loadPage(pageName) {
    const contentDiv = document.getElementById('content');
    const filePath = `${CONFIG.contentPath}${pageName}${CONFIG.fileExtension}`;

    try {
        // Show loading state
        contentDiv.innerHTML = '<section class="loading"><h1>Loading...</h1><p>Please wait while the content loads.</p></section>';

        // Fetch the markdown file
        const response = await fetch(filePath);

        if (!response.ok) {
            throw new Error(`Failed to load ${filePath}: ${response.status} ${response.statusText}`);
        }

        const markdown = await response.text();

        // Convert markdown to HTML
        // Check if marked is available and use the correct API
        let html;
        if (typeof marked !== 'undefined') {
            if (typeof marked.parse === 'function') {
                html = marked.parse(markdown);
            } else if (typeof marked === 'function') {
                html = marked(markdown);
            } else {
                throw new Error('marked library loaded but API not recognized');
            }
        } else {
            throw new Error('marked library not loaded');
        }

        // Render the content
        contentDiv.innerHTML = `<section class="loaded">${html}</section>`;

        // Scroll to top
        window.scrollTo(0, 0);

        // Process rendered content
        processRenderedContent();

    } catch (error) {
        console.error('Error loading page:', error);
        showError(pageName, error.message);
    }
}

/**
 * Process rendered content (add classes, enhance elements)
 */
function processRenderedContent() {
    const contentDiv = document.getElementById('content');

    // Add class to Quick Navigation section for card styling
    const quickNavHeading = Array.from(contentDiv.querySelectorAll('h2')).find(h2 =>
        h2.textContent.trim() === 'Quick Navigation'
    );
    if (quickNavHeading) {
        const nextUl = quickNavHeading.nextElementSibling;
        if (nextUl && nextUl.tagName === 'UL') {
            nextUl.classList.add('quick-nav-grid');
            enhanceQuickNavCards(nextUl);
        }
    }

    // Wrap tables in a scrollable container
    const tables = contentDiv.querySelectorAll('table');
    tables.forEach(table => {
        if (!table.parentElement.classList.contains('table-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-wrapper';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });

    // Process blockquotes into callouts
    const blockquotes = contentDiv.querySelectorAll('blockquote');
    blockquotes.forEach(blockquote => {
        const firstChild = blockquote.firstElementChild;
        if (firstChild && firstChild.tagName === 'P') {
            const text = firstChild.textContent.trim();

            // Check for callout types
            const calloutTypes = {
                '[!INFO]': 'callout-info',
                '[!WARNING]': 'callout-warning',
                '[!DANGER]': 'callout-danger',
                '[!SUCCESS]': 'callout-success',
                '[!NOTE]': 'callout-sot'
            };

            for (const [marker, className] of Object.entries(calloutTypes)) {
                if (text.startsWith(marker)) {
                    blockquote.classList.add('callout', className);

                    // Create title
                    const title = document.createElement('div');
                    title.className = 'callout-title';
                    title.textContent = marker.replace('[!', '').replace(']', '');

                    // Remove marker from content
                    firstChild.textContent = text.substring(marker.length).trim();

                    // Insert title
                    blockquote.insertBefore(title, firstChild);
                    break;
                }
            }
        }
    });
}

/**
 * Convert a markdown list into Polaris-style cards.
 * Expects each <li> to start with an emoji icon and contain a <strong> title,
 * followed by a description on the next line.
 */
function enhanceQuickNavCards(ul) {
    const items = ul.querySelectorAll('li');
    items.forEach(li => {
        // Avoid double-processing
        if (li.dataset.enhanced === 'true') return;

        const strong = li.querySelector('strong');
        const title = strong?.textContent?.trim() ?? '';

        // Get raw text and extract icon (first character, usually emoji)
        const rawText = li.textContent?.trim() ?? '';
        const textNodes = Array.from(li.childNodes).filter(n => n.nodeType === 3);
        const firstText = textNodes[0]?.textContent?.trim() ?? '';
        const icon = firstText ? Array.from(firstText)[0] : '';

        // Build description: get all text after the strong element
        let desc = '';
        if (strong && strong.nextSibling) {
            // Get text after <strong>
            const afterStrong = Array.from(li.childNodes)
                .slice(Array.from(li.childNodes).indexOf(strong) + 1)
                .map(n => n.textContent)
                .join(' ')
                .trim();
            desc = afterStrong.replace(/^[-–—:]\s*/, '').trim();
        } else {
            // Fallback: extract from raw text
            desc = rawText;
            if (icon) desc = desc.replace(icon, '').trim();
            if (title) desc = desc.replace(title, '').trim();
            desc = desc.replace(/^[-–—:]\s*/, '').trim();
        }
        desc = desc.replace(/\s+/g, ' ');

        // Rebuild card markup with proper structure
        li.innerHTML = `
            <div class="qn-icon" aria-hidden="true">${escapeHtml(icon)}</div>
            <div class="qn-body">
                <div class="qn-title">${escapeHtml(title || rawText.replace(icon, '').trim())}</div>
                ${desc ? `<div class="qn-desc">${escapeHtml(desc)}</div>` : ''}
            </div>
        `;
        li.classList.add('qn-card');
        li.dataset.enhanced = 'true';
    });
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Update active navigation link
 * @param {string} pageName - Name of the active page
 */
function updateActiveNavLink(pageName) {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const linkPage = link.getAttribute('data-page');

        if (linkPage === pageName) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

/**
 * Show "coming soon" message
 * @param {string} pageName - Name of the page
 */
function showComingSoon(pageName) {
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = `
        <section class="loaded">
            <h1>Coming Soon</h1>
            <p class="section-subtitle">${pageName} documentation is currently being developed.</p>

            <div class="callout callout-info">
                <div class="callout-title">Under Construction</div>
                <p>This section will be available soon. Check back later for updates.</p>
            </div>

            <p>In the meantime, you can:</p>
            <ul>
                <li>Explore other available sections in the navigation</li>
                <li>Return to the <a href="#getting-started">Getting Started</a> page</li>
                <li>Contact the documentation team if you need specific information</li>
            </ul>
        </section>
    `;
}

/**
 * Show error message
 * @param {string} pageName - Name of the page that failed to load
 * @param {string} errorMessage - Error message
 */
function showError(pageName, errorMessage) {
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = `
        <section class="loaded">
            <h1>Error Loading Page</h1>
            <p class="section-subtitle">Failed to load ${pageName}</p>

            <div class="callout callout-danger">
                <div class="callout-title">Error Details</div>
                <p>${errorMessage}</p>
            </div>

            <p>Possible solutions:</p>
            <ul>
                <li>Check if the file <code>${pageName}.md</code> exists in the <code>content/</code> directory</li>
                <li>Verify that the file is properly formatted markdown</li>
                <li>Return to the <a href="#getting-started">Getting Started</a> page</li>
                <li>Contact the documentation team if the problem persists</li>
            </ul>
        </section>
    `;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

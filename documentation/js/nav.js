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
 * Map test case number to test pack
 * @param {string} tcId - Test case ID (e.g., 'tc-100' or '100')
 * @returns {string|null} - Test pack page name or null
 */
function getTestPackForTC(tcId) {
    // Extract number from TC ID
    const match = tcId.match(/(\d+)/);
    if (!match) return null;

    const tcNum = parseInt(match[1], 10);

    // Map TC ranges to test packs
    if (tcNum >= 1 && tcNum <= 31) return 'test_packs/test_pack_1';
    if (tcNum >= 100 && tcNum <= 152) return 'test_packs/test_pack_2';
    if (tcNum >= 200 && tcNum <= 299) return 'test_packs/test_pack_3';
    if (tcNum >= 300 && tcNum <= 381) return 'test_packs/test_pack_4';
    if (tcNum >= 600 && tcNum <= 691) return 'test_packs/test_pack_5';
    if (tcNum >= 700 && tcNum <= 822) return 'test_packs/test_pack_6';

    return null;
}

/**
 * Handle routing based on URL hash
 */
function handleRouting() {
    let hash = window.location.hash.slice(1); // Remove the '#'

    // If no hash but pathname indicates a specific page, convert pathname to hash
    if (!hash && window.location.pathname.startsWith('/docs/')) {
        const pathname = window.location.pathname.replace('/docs/', '').replace(/\/$/, '');
        if (pathname && pathname !== 'docs' && pathname !== '') {
            // Convert pathname to hash format (e.g., 'user_stories' -> 'user-stories')
            const hashFromPath = pathname.replace(/_/g, '-');
            // Update URL with hash without triggering navigation
            if (window.location.hash !== '#' + hashFromPath) {
                window.history.replaceState(null, '', window.location.pathname + '#' + hashFromPath);
                hash = hashFromPath;
            }
        }
    }

    // Check if hash is a test case anchor (tc-xxx)
    // If so, route to the appropriate test pack page
    if (hash && hash.match(/^tc-\d+$/i)) {
        const testPack = getTestPackForTC(hash);
        if (testPack) {
            // Check if we're already on the correct test pack page
            const currentPage = document.querySelector('.nav-link.active')?.getAttribute('data-page');
            if (currentPage === testPack) {
                // Already on the right page, just scroll to anchor
                setTimeout(() => {
                    const element = document.getElementById(hash.toLowerCase());
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 100);
                return;
            }

            // Load the test pack page, then scroll to anchor
            loadPage(testPack).then(() => {
                setTimeout(() => {
                    const element = document.getElementById(hash.toLowerCase());
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 200);
            }).catch(err => {
                console.error('Error loading test pack:', err);
            });
            updateActiveNavLink(testPack);
            return;
        }
    }

    // Check if hash is a requirement anchor (fr-xxx)
    // These should scroll on current page or load requirements page
    if (hash && hash.match(/^fr-\d+$/i)) {
        // Check if we're on requirements page
        const currentPage = document.querySelector('.nav-link.active')?.getAttribute('data-page');
        if (currentPage === 'requirements') {
            // Scroll to anchor on current page
            setTimeout(() => {
                const element = document.getElementById(hash.toLowerCase());
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
            return;
        } else {
            // Load requirements page with anchor
            loadPage('requirements').then(() => {
                setTimeout(() => {
                    const element = document.getElementById(hash.toLowerCase());
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 200);
            }).catch(err => {
                console.error('Error loading requirements page:', err);
            });
            updateActiveNavLink('requirements');
            return;
        }
    }

    // Check if hash contains both page and anchor (e.g., 'test-pack-2#tc-100')
    const hashParts = hash.split('#');
    const pageHash = hashParts[0];
    const anchorHash = hashParts[1];

    // Check if this is just an anchor on the current page (no page part, just #anchor)
    if (pageHash && !anchorHash) {
        // Check if there's an element with this ID on the current page
        const element = document.getElementById(pageHash);
        if (element) {
            // This is a same-page anchor link, just scroll to it
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }
    }

    // Determine which page to load
    let pageName = CONFIG.defaultPage;

    if (pageHash) {
        // Try to find nav link with matching hash to get data-page attribute
        const navLink = document.querySelector(`.nav-link[href="#${pageHash}"]`);
        if (navLink && navLink.getAttribute('data-page')) {
            // Use the data-page attribute which has the correct path (handles subfolders)
            pageName = navLink.getAttribute('data-page');
        } else {
            // Fallback: Convert hash to page name (e.g., 'getting-started' -> 'getting_updated')
            pageName = pageHash.replace(/-/g, '_');
        }
    }

    // Load the page
    loadPage(pageName).then(() => {
        // If there's an anchor, scroll to it after page loads
        if (anchorHash) {
            setTimeout(() => {
                const element = document.getElementById(anchorHash.toLowerCase());
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 200);
        }
    }).catch(err => {
        console.error('Error loading page:', err);
    });

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

    return new Promise(async (resolve, reject) => {
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

            resolve();

        } catch (error) {
            console.error('Error loading page:', error);
            showError(pageName, error.message);
            reject(error);
        }
    });
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
        // Get all paragraphs in the blockquote
        const paragraphs = blockquote.querySelectorAll('p');
        if (paragraphs.length === 0) return;

        const firstParagraph = paragraphs[0];
        const text = firstParagraph.textContent.trim();

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

                // Remove marker from content while preserving HTML structure
                // Find the first text node and remove the marker from it
                const walker = document.createTreeWalker(
                    firstParagraph,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                let textNode = walker.nextNode();
                if (textNode) {
                    const nodeText = textNode.textContent;
                    if (nodeText.trim().startsWith(marker)) {
                        // Remove the marker and any following whitespace
                        const escapedMarker = marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                        const newText = nodeText.replace(new RegExp('^\\s*' + escapedMarker + '\\s*'), '');
                        textNode.textContent = newText;
                    }
                }

                // If the first paragraph only contained the marker, remove it
                if (firstParagraph.textContent.trim() === '') {
                    firstParagraph.remove();
                }

                // Insert title at the beginning of the blockquote
                blockquote.insertBefore(title, blockquote.firstElementChild);
                break;
            }
        }
    });

    // Intercept cross-page anchor links (e.g., requirements#fr-501)
    // Also ensure card links work properly
    const links = contentDiv.querySelectorAll('a[href]');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (!href || href.startsWith('http')) return; // Skip external links

        // Handle cross-page links (e.g., requirements#fr-501 or test-pack-2#tc-100)
        // These need to be converted to hash navigation format
        if (href.includes('#') && !href.startsWith('#')) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                // Convert to hash navigation format: requirements#fr-501 -> #requirements#fr-501
                // Setting window.location.hash will trigger hashchange event, which calls handleRouting()
                window.location.hash = '#' + href;
            });
        }
        // Hash-only links (e.g., #requirements, #test-packs) - ensure they trigger routing
        else if (href.startsWith('#')) {
            link.addEventListener('click', (e) => {
                // Don't prevent default - let browser handle hash change
                // But ensure routing is triggered (in case hash doesn't change)
                const currentHash = window.location.hash;
                if (currentHash === href) {
                    // Hash is already set, manually trigger routing
                    e.preventDefault();
                    handleRouting();
                }
                // Otherwise, let browser handle it and hashchange will trigger routing
            });
        }
    });

    // Render Mermaid diagrams
    if (window.mermaid) {
        // Find code blocks with language-mermaid class (marked.js output)
        const mermaidBlocks = contentDiv.querySelectorAll('pre code.language-mermaid');
        mermaidBlocks.forEach((block, index) => {
            const pre = block.parentElement;
            const code = block.textContent;

            // Create a div for mermaid to render into
            const div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = code;

            // Replace pre with div
            pre.parentNode.replaceChild(div, pre);
        });

        // Run mermaid
        window.mermaid.run({
            nodes: contentDiv.querySelectorAll('.mermaid')
        }).catch(err => console.error('Mermaid rendering failed:', err));
    }
}

/**
 * Convert a markdown list into Polaris-style cards.
 * Expects each <li> to start with an emoji icon and contain a <strong> title,
 * followed by a description on the next line.
 * Preserves links and makes cards clickable.
 */
function enhanceQuickNavCards(ul) {
    const items = ul.querySelectorAll('li');
    items.forEach(li => {
        // Avoid double-processing
        if (li.dataset.enhanced === 'true') return;

        // Check if there's a link in the list item (might be inside strong tag)
        const link = li.querySelector('a');
        const href = link ? link.getAttribute('href') : null;
        const linkText = link ? link.textContent.trim() : '';

        const strong = li.querySelector('strong');
        // Get title from link text if available, otherwise from strong
        const title = linkText || (strong ? strong.textContent.trim() : '');

        // Get raw text and extract icon (first character, usually emoji)
        const rawText = li.textContent?.trim() ?? '';
        const textNodes = Array.from(li.childNodes).filter(n => n.nodeType === 3);
        const firstText = textNodes[0]?.textContent?.trim() ?? '';
        const icon = firstText ? Array.from(firstText)[0] : '';

        // Build description: get all text after the strong element or link
        let desc = '';
        const strongNode = strong || link;
        if (strongNode && strongNode.nextSibling) {
            // Get text after <strong> or <a>
            const afterNode = Array.from(li.childNodes)
                .slice(Array.from(li.childNodes).indexOf(strongNode) + 1)
                .map(n => n.textContent)
                .join(' ')
                .trim();
            desc = afterNode.replace(/^[-–—:]\s*/, '').trim();
        } else {
            // Fallback: extract from raw text
            desc = rawText;
            if (icon) desc = desc.replace(icon, '').trim();
            if (title) desc = desc.replace(title, '').trim();
            desc = desc.replace(/^[-–—:]\s*/, '').trim();
        }
        desc = desc.replace(/\s+/g, ' ');

        // Rebuild card markup with proper structure
        // If there's a link, make the entire card clickable
        if (href) {
            li.innerHTML = `
                <a href="${escapeHtml(href)}" class="qn-card-link">
                    <div class="qn-icon" aria-hidden="true">${escapeHtml(icon)}</div>
                    <div class="qn-body">
                        <div class="qn-title">${escapeHtml(title || rawText.replace(icon, '').trim())}</div>
                        ${desc ? `<div class="qn-desc">${escapeHtml(desc)}</div>` : ''}
                    </div>
                </a>
            `;
        } else {
            li.innerHTML = `
                <div class="qn-icon" aria-hidden="true">${escapeHtml(icon)}</div>
                <div class="qn-body">
                    <div class="qn-title">${escapeHtml(title || rawText.replace(icon, '').trim())}</div>
                    ${desc ? `<div class="qn-desc">${escapeHtml(desc)}</div>` : ''}
                </div>
            `;
        }
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
 * @param {string} pageName - Name of the active page (may include subfolder path)
 */
function updateActiveNavLink(pageName) {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const linkPage = link.getAttribute('data-page');

        // Match exact path or handle subfolder paths
        if (linkPage === pageName || linkPage === pageName.replace(/\//g, '/')) {
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

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

// Page manifest - maps hash names to file paths
// Only hashes in this list will trigger page loads; everything else is treated as an anchor
const PAGE_MANIFEST = {
    // Getting Started
    'getting-started': 'getting_started',
    'purpose-scope': 'purpose_scope',
    // Requirements
    'requirements': 'requirements',
    'user-stories': 'user_stories',
    'use-cases': 'use_cases',
    'non-functional-requirements': 'non_functional_requirements',
    // Testing
    'test-packs': 'test_packs/index',
    'test-pack-1': 'test_packs/test_pack_1',
    'test-pack-2': 'test_packs/test_pack_2',
    'test-pack-3': 'test_packs/test_pack_3',
    'test-pack-4': 'test_packs/test_pack_4',
    'test-pack-5': 'test_packs/test_pack_5',
    'test-pack-6': 'test_packs/test_pack_6',
    'test-pack-7': 'test_packs/test_pack_7',
    // User Guide
    'user-guide-index': 'user_guide/index',
    'user-guide-in-person-events': 'user_guide/in_person_events',
    'user-guide-virtual-events': 'user_guide/virtual_events',
    'user-guide-volunteer-recruitment': 'user_guide/volunteer_recruitment',
    'user-guide-district-teacher-progress': 'user_guide/district_teacher_progress',
    'user-guide-student-management': 'user_guide/student_management',
    'user-guide-reporting': 'user_guide/reporting',
    'user-guide-email-system': 'user_guide/email_system',
    'user-guide-data-tracker': 'user_guide/data_tracker',
    'import-playbook': 'import_playbook',
    // Reports
    'reports-index': 'reports/index',
    'reports-impact': 'reports/impact',
    'reports-volunteer-engagement': 'reports/volunteer_engagement',
    'reports-partner-match': 'reports/partner_match',
    'reports-ad-hoc': 'reports/ad_hoc',
    // Technical
    'architecture': 'architecture',
    'codebase-structure': 'codebase_structure',
    'data-dictionary': 'data_dictionary',
    'field-mappings': 'field_mappings',
    'field-mappings': 'field_mappings',
    'contracts': 'contracts',
    'contract-a': 'contract_a',
    'contract-b': 'contract_b',
    'contract-c': 'contract_c',
    'contract-d': 'contract_d',
    'metrics-bible': 'metrics_bible',
    'api-reference': 'api_reference',
    // Security
    'rbac-matrix': 'rbac_matrix',
    'privacy-data-handling': 'privacy_data_handling',
    'audit-requirements': 'audit_requirements',
    // Operations
    'deployment': 'deployment',
    'monitoring': 'monitoring',
    'smoke-tests': 'smoke_tests',
    'daily-import-scripts': 'daily_import_scripts',
    'runbook': 'runbook',
    'user-guide-public-signup': 'user_guide/public_signup'
};

// State - track current loaded page to distinguish page nav from anchor scrolling
let currentLoadedPage = null;

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
    if (tcNum >= 900 && tcNum <= 913) return 'test_packs/test_pack_7';

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

    // NOTE: Same-page anchor detection is handled in the pageHash block below
    // using currentLoadedPage to properly distinguish anchors from pages

    // Determine which page to load
    let pageName = CONFIG.defaultPage;

    if (pageHash) {
        // FIRST: Check if this hash is an anchor on the current page
        // If so, just scroll to it instead of trying to load a new page
        if (currentLoadedPage) {
            const anchorElement = document.getElementById(pageHash);
            if (anchorElement) {
                // This is a same-page anchor, just scroll to it
                anchorElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return; // Don't try to load a new page
            }
        }

        // Check if this hash is a known page in the manifest
        if (PAGE_MANIFEST[pageHash]) {
            // This is a valid page - use the manifest path
            pageName = PAGE_MANIFEST[pageHash];
        } else {
            // Hash is NOT a known page - it might be an anchor ID within a page
            // Try to scroll to it if it exists, otherwise stay on current page
            if (currentLoadedPage) {
                const anchorElement = document.getElementById(pageHash);
                if (anchorElement) {
                    anchorElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
            // Don't try to load an unknown page - just return
            return;
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
            let response = await fetch(filePath);

            // If not found, try common subdirectories
            if (!response.ok && response.status === 404) {
                const commonPaths = [
                    `user_guide/${pageName}`,
                    `test_packs/${pageName}`,
                    `reports/${pageName}`
                ];

                for (const altPath of commonPaths) {
                    const altFilePath = `${CONFIG.contentPath}${altPath}${CONFIG.fileExtension}`;
                    const altResponse = await fetch(altFilePath);
                    if (altResponse.ok) {
                        response = altResponse;
                        // Don't modify history - just load the correct page
                        break;
                    }
                }
            }

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

            // Track the current loaded page for anchor detection
            currentLoadedPage = pageName;

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
            '[!NOTE]': 'callout-sot',
            '[!TIP]': 'callout-success',
            '[!IMPORTANT]': 'callout-warning',
            '[!CAUTION]': 'callout-danger'
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

    // Intercept all internal documentation links
    // - Page links: change URL hash, add to browser history
    // - Same-page anchors: just scroll, don't modify URL or history
    const links = contentDiv.querySelectorAll('a[href]');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;

        // Skip external links (http/https) and special protocols
        if (href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('tel:')) return;

        // Skip file links (images, downloads, etc.)
        if (href.match(/\.(png|jpg|jpeg|gif|svg|pdf|zip|doc|docx)$/i)) return;

        // Handle cross-page links with anchors (e.g., requirements#fr-501 or test-pack-2#tc-100)
        if (href.includes('#') && !href.startsWith('#')) {
            const [pagePart, anchorPart] = href.split('#');
            const pageHash = pagePart.replace(/_/g, '-').replace(/\//g, '-');

            link.addEventListener('click', (e) => {
                e.preventDefault();
                if (PAGE_MANIFEST[pageHash]) {
                    // This is a cross-page link - navigate to page with anchor
                    window.location.hash = pageHash + '#' + anchorPart;
                } else {
                    // Unknown page, try to scroll to anchor on current page
                    const element = document.getElementById(anchorPart);
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        }
        // Handle hash-only links (e.g., #requirements, #in-person-event-management)
        else if (href.startsWith('#')) {
            const targetHash = href.slice(1); // Remove leading #

            link.addEventListener('click', (e) => {
                // Allow special anchors (TCs, FRs) to be handled by the global hashchange event
                if (targetHash.match(/^tc-\d+$/i) || targetHash.match(/^fr-\d+$/i)) {
                    return;
                }

                e.preventDefault();

                // Check if this is a page link (in manifest)
                if (PAGE_MANIFEST[targetHash]) {
                    // This is a page link - navigate and add to history
                    window.location.hash = targetHash;
                } else {
                    // This is a same-page anchor - just scroll, don't change URL
                    const element = document.getElementById(targetHash);
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        }
        // Handle relative page links without anchors (e.g., user_stories, requirements)
        // Allow paths with slashes but exclude absolute paths
        else if (!href.startsWith('/') && !href.startsWith('http')) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                let pageName = href.replace(/^\.\//, '').replace(/^\.\.\//, '');
                const pageHash = pageName.replace(/_/g, '-').replace(/\//g, '-');

                if (PAGE_MANIFEST[pageHash]) {
                    // Valid page - navigate
                    window.location.hash = pageHash;
                } else {
                    // Unknown - try as same-page anchor
                    const element = document.getElementById(pageName) || document.getElementById(pageHash);
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
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

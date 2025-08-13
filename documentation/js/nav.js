// Navigation functionality
function attachExpandableHandlers() {
    document.querySelectorAll('.expandable-header').forEach(function(header) {
        header.onclick = function() {
            var expandable = this.parentElement;
            expandable.classList.toggle('open');
        };
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Load shared navigation
    loadNavigation();
    // Attach expand/collapse handlers (for static content)
    attachExpandableHandlers();
});

// Load shared navigation template
async function loadNavigation() {
    try {
        const response = await fetch('nav.html');
        const navHtml = await response.text();
        // Insert navigation into sidebar
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.innerHTML = navHtml;
            // Set active navigation item based on current page
            setActiveNavigation();
        }
        // Attach expand/collapse handlers (for dynamic content)
        attachExpandableHandlers();
    } catch (error) {
        console.error('Error loading navigation:', error);
        // Fallback: set active state manually
        setActiveNavigation();
        attachExpandableHandlers();
    }
}

// Set active navigation item based on current page
function setActiveNavigation() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href === currentPage) {
            item.classList.add('active');
        }
    });
}

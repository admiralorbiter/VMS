// Navigation functionality
document.addEventListener('DOMContentLoaded', function() {
    // Load shared navigation
    loadNavigation();
    
    // Handle expandable sections
    const expandableHeaders = document.querySelectorAll('.expandable-header');
    expandableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const expandable = this.parentElement;
            expandable.classList.toggle('open');
        });
    });

    // Handle feature card clicks
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href) {
                window.location.href = href;
            }
        });
    });
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
    } catch (error) {
        console.error('Error loading navigation:', error);
        // Fallback: set active state manually
        setActiveNavigation();
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
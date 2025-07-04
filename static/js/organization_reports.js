/**
 * Organization Reports JavaScript Module
 * ====================================
 * 
 * This module provides sorting functionality for organization reports,
 * including table column sorting with visual indicators and URL state management.
 * 
 * Key Features:
 * - Clickable column sorting
 * - Visual sort direction indicators
 * - URL parameter management
 * - Toggle between ascending/descending
 * - Active sort highlighting
 * - Helper function for sort URL generation
 * 
 * Sorting System:
 * - Clickable table headers with data-sort attributes
 * - Toggle between ascending and descending order
 * - URL state preservation
 * - Visual feedback for active sorting
 * - Automatic page reload with new sort parameters
 * 
 * URL Parameters:
 * - sort_by: Column to sort by
 * - sort_order: Sort direction ('asc' or 'desc')
 * - Preserves other URL parameters during sorting
 * 
 * Visual Indicators:
 * - .active: Applied to currently sorted column
 * - .asc/.desc: Applied to indicate sort direction
 * - Hover effects for sortable columns
 * 
 * Dependencies:
 * - Bootstrap 5.3.3 CSS for table styling
 * - Custom CSS for sort indicators
 * - FontAwesome icons (if used for sort indicators)
 * 
 * CSS Classes:
 * - .sortable: Sortable column headers
 * - .active: Active sort column
 * - .asc/.desc: Sort direction indicators
 * 
 * Data Attributes:
 * - data-sort: Column identifier for sorting
 * 
 * Usage:
 * - Automatically initializes on DOM content loaded
 * - Requires sortable headers with data-sort attributes
 * - Works with existing table structure
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeSorting();
});

/**
 * Initialize sorting functionality for organization reports
 * Sets up click handlers and visual indicators
 */
function initializeSorting() {
    const sortableHeaders = document.querySelectorAll('.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const sortBy = this.getAttribute('data-sort');
            const currentSort = new URLSearchParams(window.location.search).get('sort_by');
            const currentOrder = new URLSearchParams(window.location.search).get('sort_order') || 'desc';
            
            let newOrder = 'desc';
            if (currentSort === sortBy && currentOrder === 'desc') {
                newOrder = 'asc';
            }
            
            // Update URL with new sorting parameters
            const url = new URL(window.location);
            url.searchParams.set('sort_by', sortBy);
            url.searchParams.set('sort_order', newOrder);
            
            // Redirect to sorted page
            window.location.href = url.toString();
        });
    });
    
    // Set active sorting indicators
    const currentSort = new URLSearchParams(window.location.search).get('sort_by');
    const currentOrder = new URLSearchParams(window.location.search).get('sort_order') || 'desc';
    
    if (currentSort) {
        const activeHeader = document.querySelector(`[data-sort="${currentSort}"]`);
        if (activeHeader) {
            activeHeader.classList.add('active', currentOrder);
        }
    }
}

/**
 * Helper function to generate sorting URLs
 * @param {string} sortBy - Column to sort by
 * @param {string} currentSort - Currently active sort column
 * @param {string} currentOrder - Current sort order
 * @returns {string} URL with updated sort parameters
 */
function getSortUrl(sortBy, currentSort, currentOrder) {
    const url = new URL(window.location);
    
    let newOrder = 'desc';
    if (currentSort === sortBy && currentOrder === 'desc') {
        newOrder = 'asc';
    }
    
    url.searchParams.set('sort_by', sortBy);
    url.searchParams.set('sort_order', newOrder);
    
    return url.toString();
} 
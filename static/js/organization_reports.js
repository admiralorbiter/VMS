/**
 * Organization Reports - Sorting functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeSorting();
});

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
 * Helper function to get sorting URL
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
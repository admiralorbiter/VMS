/**
 * Recruitment Report JavaScript Module
 * ===================================
 * 
 * This module provides client-side sorting functionality for recruitment reports,
 * allowing users to sort table data by various columns without page reloads.
 * 
 * Key Features:
 * - Client-side table sorting
 * - Multiple table support
 * - Visual sort direction indicators
 * - Date-aware sorting
 * - Text-based sorting with case insensitivity
 * - Toggle between ascending/descending order
 * 
 * Sorting System:
 * - Clickable table headers with data-sort attributes
 * - Client-side sorting without server requests
 * - Visual feedback for sort direction
 * - Support for multiple tables on same page
 * - Automatic row reordering
 * 
 * Column Mapping:
 * - title: Event/volunteer title (column 1)
 * - date: Date information (column 2)
 * - type: Event type (column 3)
 * - slots: Available slots (column 4)
 * - name: Volunteer name (column 1)
 * - organization: Organization name (column 2)
 * - last_activity: Last activity date (column 4)
 * 
 * Data Handling:
 * - Text extraction from complex cell content
 * - Date parsing for chronological sorting
 * - Case-insensitive text comparison
 * - Support for multi-line cell content
 * 
 * Visual Feedback:
 * - .asc/.desc classes for sort direction
 * - Automatic class removal from other headers
 * - Visual indicators for active sorting
 * 
 * Dependencies:
 * - Bootstrap 5.3.3 CSS for table styling
 * - Custom CSS for sort indicators
 * - FontAwesome icons (if used for sort indicators)
 * 
 * CSS Classes:
 * - .recruitment-table: Main table container
 * - .sortable: Sortable column headers
 * - .asc/.desc: Sort direction indicators
 * 
 * Data Attributes:
 * - data-sort: Column identifier for sorting
 * 
 * Usage:
 * - Automatically initializes on DOM content loaded
 * - Requires tables with .recruitment-table class
 * - Requires sortable headers with data-sort attributes
 * - Works with existing table structure
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get all tables with sortable headers
    const tables = document.querySelectorAll('.recruitment-table');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const sortBy = this.getAttribute('data-sort');
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                
                // Toggle sort direction
                const isAscending = !this.classList.contains('asc');
                
                // Remove sorting classes from all headers
                headers.forEach(h => {
                    h.classList.remove('asc', 'desc');
                });
                
                // Add appropriate sorting class
                this.classList.add(isAscending ? 'asc' : 'desc');
                
                // Sort the rows
                rows.sort((a, b) => {
                    let aVal = getCellValue(a, sortBy);
                    let bVal = getCellValue(b, sortBy);
                    
                    if (sortBy === 'date') {
                        aVal = new Date(aVal);
                        bVal = new Date(bVal);
                    }
                    
                    if (aVal < bVal) return isAscending ? -1 : 1;
                    if (aVal > bVal) return isAscending ? 1 : -1;
                    return 0;
                });
                
                // Re-append rows in sorted order
                rows.forEach(row => tbody.appendChild(row));
            });
        });
    });
});

/**
 * Extract cell value for sorting
 * @param {HTMLElement} row - Table row element
 * @param {string} sortBy - Column identifier for sorting
 * @returns {string} Extracted cell value
 */
function getCellValue(row, sortBy) {
    const cell = row.querySelector(`td:nth-child(${getColumnIndex(sortBy)})`);
    if (!cell) return '';
    
    // For cells with multiple lines, get the first line
    const firstLine = cell.querySelector('strong') || cell;
    return firstLine.textContent.trim().toLowerCase();
}

/**
 * Get column index based on sort identifier
 * @param {string} sortBy - Column identifier
 * @returns {number} Column index (1-based)
 */
function getColumnIndex(sortBy) {
    const columnMap = {
        'title': 1,
        'date': 2,
        'type': 3,
        'slots': 4,
        'name': 1,
        'organization': 2,
        'last_activity': 4
    };
    return columnMap[sortBy] || 1;
}
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

function getCellValue(row, sortBy) {
    const cell = row.querySelector(`td:nth-child(${getColumnIndex(sortBy)})`);
    if (!cell) return '';
    
    // For cells with multiple lines, get the first line
    const firstLine = cell.querySelector('strong') || cell;
    return firstLine.textContent.trim().toLowerCase();
}

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
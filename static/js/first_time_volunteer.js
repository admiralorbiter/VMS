// Function to update per_page and reload
function updatePerPage(perPage) {
    const url = new URL(window.location);
    url.searchParams.set('per_page', perPage);
    url.searchParams.set('page', '1'); // Reset to first page when changing per_page
    window.location.href = url.toString();
}
document.addEventListener('DOMContentLoaded', function() {
    const table = document.querySelector('.volunteer-table table');
    const tbody = table.querySelector('tbody');
    const headers = table.querySelectorAll('th.sortable');

    let currentSort = {
        column: null,
        direction: 'asc'
    };

    // Store original data for sorting
    const originalRows = Array.from(tbody.querySelectorAll('tr'));

    headers.forEach(header => {
        header.addEventListener('click', function() {
            const sortKey = this.dataset.sort;

            // Update sort direction
            if (currentSort.column === sortKey) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = sortKey;
                currentSort.direction = 'asc';
            }

            // Update header classes
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            this.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');

            // Sort the data
            sortTable(sortKey, currentSort.direction);
        });
    });

    function sortTable(sortKey, direction) {
        const rows = Array.from(tbody.querySelectorAll('tr'));

        rows.sort((a, b) => {
            let aValue, bValue;

            switch(sortKey) {
                case 'name':
                    aValue = a.querySelector('.volunteer-name').textContent.trim();
                    bValue = b.querySelector('.volunteer-name').textContent.trim();
                    break;
                case 'events':
                    aValue = parseInt(a.querySelector('.events-count').textContent.match(/\d+/)[0]);
                    bValue = parseInt(b.querySelector('.events-count').textContent.match(/\d+/)[0]);
                    break;
                case 'organization':
                    aValue = a.cells[2].textContent.trim();
                    bValue = b.cells[2].textContent.trim();
                    break;
                case 'title':
                    aValue = a.querySelector('.title-cell').textContent.trim();
                    bValue = b.querySelector('.title-cell').textContent.trim();
                    break;
                case 'events_participated':
                    const aEvents = a.querySelectorAll('.event-item').length;
                    const bEvents = b.querySelectorAll('.event-item').length;
                    aValue = aEvents;
                    bValue = bEvents;
                    break;
                default:
                    return 0;
            }

            // Handle string comparison
            if (typeof aValue === 'string') {
                aValue = aValue.toLowerCase();
                bValue = bValue.toLowerCase();
            }

            if (direction === 'asc') {
                return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
            } else {
                return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
            }
        });

        // Clear and re-append sorted rows
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
    }
});

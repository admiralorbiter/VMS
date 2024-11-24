document.addEventListener('DOMContentLoaded', function() {
    // Initialize sorting
    document.querySelectorAll('th.sortable').forEach(header => {
        header.addEventListener('click', () => handleSort(header));
    });

    // Initialize search with debouncing
    const searchInputs = document.querySelectorAll('.filter-group input[type="text"]');
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(handleSearch, 300));
    });

    // Initialize purge button
    const purgeButton = document.querySelector('.purge-volunteers-btn');
    if (purgeButton) {
        purgeButton.addEventListener('click', confirmPurge);
    }

    // Initialize per-page select
    const perPageSelect = document.querySelector('.per-page-select');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', handlePerPageChange);
    }
});

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function handleSort(header) {
    const sortField = header.dataset.sort;
    const currentSort = header.classList.contains('sort-asc') ? 'desc' : 'asc';
    
    // Update URL with sort parameters
    const url = new URL(window.location);
    url.searchParams.set('sort_by', sortField);
    url.searchParams.set('sort_direction', currentSort);
    window.location = url;
}

function handleSearch(event) {
    const form = event.target.closest('form');
    form.submit();
}

function confirmPurge() {
    if (confirm('Are you sure you want to purge all volunteer data? This action cannot be undone.')) {
        fetch('/volunteers/purge', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Volunteers purged successfully');
                window.location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error: ' + error);
        });
    }
}

function confirmSync() {
    if (confirm('Are you sure you want to sync volunteer data? This may take a few minutes.')) {
        fetch('/volunteers/sync', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Volunteers synced successfully');
                window.location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error: ' + error);
        });
    }
}

function handlePerPageChange(event) {
    const url = new URL(window.location);
    url.searchParams.set('per_page', event.target.value);
    url.searchParams.set('page', 1); // Reset to first page when changing items per page
    window.location = url;
} 
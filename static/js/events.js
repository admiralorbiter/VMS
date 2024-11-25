document.addEventListener('DOMContentLoaded', function() {
    // Initialize sorting
    const url = new URL(window.location);
    const currentSortBy = url.searchParams.get('sort_by');
    const currentSortDirection = url.searchParams.get('sort_direction');

    // Set initial sort indicators
    document.querySelectorAll('th.sortable').forEach(header => {
        const sortField = header.dataset.sort;
        if (sortField === currentSortBy) {
            header.classList.add(`sort-${currentSortDirection}`);
            updateSortIcon(header, currentSortDirection);
        }
        
        header.addEventListener('click', () => handleSort(header));
    });

    // Initialize search with debouncing
    const searchInputs = document.querySelectorAll('.filter-group input[type="text"]');
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(handleSearch, 600));
    });

    // Initialize purge button
    const purgeButton = document.querySelector('.purge-events-btn');
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
    const url = new URL(window.location);
    
    // Determine new sort direction
    let newDirection = 'asc';
    if (url.searchParams.get('sort_by') === sortField) {
        newDirection = url.searchParams.get('sort_direction') === 'asc' ? 'desc' : 'asc';
    }
    
    // Update URL with sort parameters
    url.searchParams.set('sort_by', sortField);
    url.searchParams.set('sort_direction', newDirection);
    
    // Preserve existing filters
    url.searchParams.set('page', '1'); // Reset to first page when sorting
    
    window.location = url.toString();
}

function updateSortIcon(header, direction) {
    const icon = header.querySelector('i.fa-sort');
    if (icon) {
        icon.classList.remove('fa-sort');
        icon.classList.add(direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
    }
}

function handleSearch(event) {
    const form = event.target.closest('form');
    form.submit();
}

function confirmPurge() {
    if (confirm('Are you sure you want to purge all event data? This action cannot be undone.')) {
        fetch('/events/purge', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Events purged successfully');
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
    
    // Update per_page parameter
    url.searchParams.set('per_page', event.target.value);
    
    // Reset to first page when changing items per page
    url.searchParams.set('page', '1');
    
    // Maintain other existing parameters (sort, filters, etc)
    window.location = url.toString();
}

let eventToDelete = null;

function deleteEvent(eventId) {
    eventToDelete = eventId;
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'block';
    
    // Add event listeners
    document.getElementById('cancelDelete').onclick = closeDeleteModal;
    document.getElementById('confirmDelete').onclick = confirmDelete;
    
    // Close on background click
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeDeleteModal();
        }
    };
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'none';
    eventToDelete = null;
}

function confirmDelete() {
    if (!eventToDelete) return;
    
    fetch(`/events/delete/${eventToDelete}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert('Error deleting event: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error deleting event');
    })
    .finally(() => {
        closeDeleteModal();
    });
}

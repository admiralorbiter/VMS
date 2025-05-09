document.addEventListener('DOMContentLoaded', function() {
    // Initialize search with debouncing
    const searchInputs = document.querySelectorAll('.filter-group input[type="text"]');
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(handleSearch, 600));
    });

    // Initialize per-page select
    const perPageSelect = document.querySelector('.per-page-select');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', handlePerPageChange);
    }

    // Initialize sorting
    const sortableHeaders = document.querySelectorAll('th.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', handleSort);
        // Add initial sort direction indicator
        const currentSort = getCurrentSort();
        if (currentSort.sort === header.dataset.sort) {
            updateSortIcon(header, currentSort.direction);
        }
    });
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

function handleSearch(event) {
    const form = event.target.closest('form');
    form.submit();
}

function handlePerPageChange(event) {
    const url = new URL(window.location);
    url.searchParams.set('per_page', event.target.value);
    url.searchParams.set('page', 1); // Reset to first page when changing items per page
    window.location = url;
}

let organizationToDelete = null;

function deleteOrganization(organizationId) {
    organizationToDelete = organizationId;
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'block';
}

document.getElementById('cancelDelete').addEventListener('click', function() {
    document.getElementById('deleteModal').style.display = 'none';
    organizationToDelete = null;
});

document.getElementById('confirmDelete').addEventListener('click', async function() {
    if (organizationToDelete) {
        try {
            const response = await fetch(`/organizations/delete/${organizationToDelete}`, {
                method: 'DELETE',
            });
            
            if (response.ok) {
                window.location.reload();
            } else {
                const data = await response.json();
                alert(data.error || 'Error deleting organization');
            }
        } catch (error) {
            alert('Error deleting organization');
        }
    }
    document.getElementById('deleteModal').style.display = 'none';
});

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        modal.style.display = 'none';
        organizationToDelete = null;
    }
});

function purgeOrganizations() {
    if (confirm('Are you sure you want to purge ALL organizations? This will delete all organizations and their affiliations. This action cannot be undone.')) {
        fetch('/organizations/purge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('success', data.message);
                // Reload the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification('error', data.error || 'An error occurred while purging organizations');
            }
        })
        .catch(error => {
            showNotification('error', 'An error occurred while purging organizations');
        });
    }
}

// Add this if you don't already have a showNotification function
function showNotification(type, message) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fa-solid ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Fade in
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function getCurrentSort() {
    const url = new URL(window.location);
    return {
        sort: url.searchParams.get('sort') || 'name',
        direction: url.searchParams.get('direction') || 'asc'
    };
}

function updateSortIcon(header, direction) {
    // Remove all existing sort icons
    header.querySelectorAll('i').forEach(icon => {
        icon.classList.remove('fa-sort', 'fa-sort-up', 'fa-sort-down');
    });

    // Add the appropriate icon
    const icon = header.querySelector('i');
    if (direction === 'asc') {
        icon.classList.add('fa-sort-up');
    } else {
        icon.classList.add('fa-sort-down');
    }
}

function handleSort(event) {
    const header = event.currentTarget;
    const sortField = header.dataset.sort;
    const currentSort = getCurrentSort();
    
    let newDirection = 'asc';
    if (currentSort.sort === sortField) {
        // Toggle direction if clicking the same column
        newDirection = currentSort.direction === 'asc' ? 'desc' : 'asc';
    }

    const url = new URL(window.location);
    url.searchParams.set('sort', sortField);
    url.searchParams.set('direction', newDirection);
    url.searchParams.set('page', 1); // Reset to first page when sorting
    window.location = url;
}

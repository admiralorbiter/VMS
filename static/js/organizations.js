/**
 * Organizations Management JavaScript Module
 * ========================================
 *
 * This module provides comprehensive functionality for managing organizations
 * in the VMS, including search, sorting, pagination, deletion, and purge operations.
 *
 * Key Features:
 * - Debounced search functionality
 * - Sortable table columns with visual indicators
 * - Pagination with per-page selection
 * - Organization deletion with confirmation modal
 * - Purge functionality for bulk operations
 * - Notification system for user feedback
 * - URL parameter management
 *
 * Search Functionality:
 * - Debounced input handling (600ms delay)
 * - Real-time form submission
 * - Multiple search field support
 * - URL parameter preservation
 *
 * Sorting System:
 * - Clickable column headers
 * - Visual sort direction indicators
 * - Toggle between ascending/descending
 * - URL state management
 * - Reset to first page on sort
 *
 * Pagination:
 * - Per-page selection (10, 25, 50, 100)
 * - URL parameter management
 * - Reset to first page on change
 *
 * Delete Operations:
 * - Confirmation modal for safety
 * - AJAX delete requests
 * - Error handling and user feedback
 * - Page reload after successful deletion
 *
 * Purge Operations:
 * - Confirmation dialog for bulk deletion
 * - AJAX purge requests
 * - Success/error notifications
 * - Automatic page reload
 *
 * Dependencies:
 * - Bootstrap 5.3.3 CSS/JS for modal functionality
 * - FontAwesome icons for visual indicators
 * - Custom CSS for notification styling
 *
 * API Endpoints:
 * - DELETE /organizations/delete/{id}: Delete specific organization
 * - POST /organizations/purge: Purge all organizations
 *
 * CSS Classes:
 * - .sortable: Sortable column headers
 * - .notification: Notification styling
 * - .show: Show notification
 * - .success/.error: Notification types
 */

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

/**
 * Debounce function to limit function execution frequency
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
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

/**
 * Handle search input changes
 * @param {Event} event - Input event
 */
function handleSearch(event) {
    const form = event.target.closest('form');
    form.submit();
}

/**
 * Handle per-page selection changes
 * @param {Event} event - Change event
 */
function handlePerPageChange(event) {
    const url = new URL(window.location);
    url.searchParams.set('per_page', event.target.value);
    url.searchParams.set('page', 1); // Reset to first page when changing items per page
    window.location = url;
}

// Global variable to store organization ID for deletion
let organizationToDelete = null;

/**
 * Initiate organization deletion process
 * @param {number} organizationId - ID of organization to delete
 */
function deleteOrganization(organizationId) {
    organizationToDelete = organizationId;
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'block';
}

// Cancel delete button event handler
document.getElementById('cancelDelete').addEventListener('click', function() {
    document.getElementById('deleteModal').style.display = 'none';
    organizationToDelete = null;
});

// Confirm delete button event handler
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

/**
 * Purge all organizations with confirmation
 * Performs bulk deletion of all organizations and their affiliations
 */
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

/**
 * Show notification to user
 * @param {string} type - Notification type ('success' or 'error')
 * @param {string} message - Notification message
 */
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

/**
 * Get current sort parameters from URL
 * @returns {Object} Object with sort field and direction
 */
function getCurrentSort() {
    const url = new URL(window.location);
    return {
        sort: url.searchParams.get('sort') || 'name',
        direction: url.searchParams.get('direction') || 'asc'
    };
}

/**
 * Update sort icon in table header
 * @param {HTMLElement} header - Table header element
 * @param {string} direction - Sort direction ('asc' or 'desc')
 */
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

/**
 * Handle table column sorting
 * @param {Event} event - Click event on sortable header
 */
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

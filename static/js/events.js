/**
 * Events Management JavaScript Module
 * ==================================
 * 
 * This module provides comprehensive functionality for managing events
 * in the VMS, including search, sorting, pagination, deletion, purge
 * operations, and dynamic skills management.
 * 
 * Key Features:
 * - Advanced search with debouncing
 * - Sortable table columns with visual indicators
 * - Pagination with per-page selection
 * - Event deletion with confirmation modal
 * - Purge functionality for bulk operations
 * - Dynamic skills management with API integration
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
 * - Clickable column headers with data-sort attributes
 * - Visual sort direction indicators
 * - Toggle between ascending/descending
 * - URL state management
 * - Reset to first page on sort
 * 
 * Pagination:
 * - Per-page selection (10, 25, 50, 100)
 * - URL parameter management
 * - Reset to first page on change
 * - Preserve existing filters and sort
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
 * Skills Management:
 * - Dynamic skill addition via API
 * - Duplicate skill prevention
 * - Visual skill tags with remove functionality
 * - Real-time skill creation and association
 * 
 * Dependencies:
 * - Bootstrap 5.3.3 CSS/JS for modal functionality
 * - FontAwesome icons for visual indicators
 * - Custom CSS for skill tag styling
 * 
 * API Endpoints:
 * - DELETE /events/delete/{id}: Delete specific event
 * - POST /events/purge: Purge all events
 * - POST /api/skills/find-or-create: Create or find skill
 * 
 * CSS Classes:
 * - .sortable: Sortable column headers
 * - .skill-tag: Skill tag styling
 * - .notification: Notification styling
 * - .show: Show notification
 * - .success/.error: Notification types
 * 
 * Data Attributes:
 * - data-sort: Column identifier for sorting
 * - data-skill-id: Skill ID for API operations
 */

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
 * Handle table column sorting
 * @param {HTMLElement} header - Table header element
 */
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

/**
 * Update sort icon in table header
 * @param {HTMLElement} header - Table header element
 * @param {string} direction - Sort direction ('asc' or 'desc')
 */
function updateSortIcon(header, direction) {
    const icon = header.querySelector('i.fa-sort');
    if (icon) {
        icon.classList.remove('fa-sort');
        icon.classList.add(direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
    }
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
 * Confirm and execute purge operations
 * Performs bulk deletion of all events with confirmation
 */
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

/**
 * Handle per-page selection changes
 * @param {Event} event - Change event
 */
function handlePerPageChange(event) {
    const url = new URL(window.location);
    
    // Update per_page parameter
    url.searchParams.set('per_page', event.target.value);
    
    // Reset to first page when changing items per page
    url.searchParams.set('page', '1');
    
    // Maintain other existing parameters (sort, filters, etc)
    window.location = url.toString();
}

// Global variable to store event ID for deletion
let eventToDelete = null;

/**
 * Initiate event deletion process
 * @param {number} eventId - ID of event to delete
 */
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

/**
 * Close the delete confirmation modal
 */
function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'none';
    eventToDelete = null;
}

/**
 * Execute event deletion via AJAX
 */
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

/**
 * Add a new skill to the event
 * Creates skill via API and adds visual tag
 */
function addSkill() {
    const input = document.getElementById('skill-input');
    const skillName = input.value.trim();
    
    if (!skillName) return;
    
    // Check if skill already exists
    const existingSkills = document.querySelectorAll('.skill-tag span');
    for (let skill of existingSkills) {
        if (skill.textContent.toLowerCase() === skillName.toLowerCase()) {
            alert('This skill has already been added.');
            return;
        }
    }
    
    // Create new skill tag
    fetch('/api/skills/find-or-create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: skillName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const skillsContainer = document.getElementById('skills-container');
            const skillTag = document.createElement('div');
            skillTag.className = 'skill-tag';
            skillTag.dataset.skillId = data.skill.id;
            skillTag.innerHTML = `
                <span>${skillName}</span>
                <button type="button" class="remove-skill" onclick="removeSkill(this)">
                    <i class="fa-solid fa-times"></i>
                </button>
            `;
            
            skillsContainer.appendChild(skillTag);
            input.value = '';
            showNotification('success', 'Skill added successfully');
        } else {
            showNotification('error', data.error || 'Error adding skill');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('error', 'Error adding skill');
    });
}

/**
 * Remove skill tag from event
 * @param {HTMLElement} button - Remove button element
 */
function removeSkill(button) {
    const skillTag = button.closest('.skill-tag');
    skillTag.remove();
    showNotification('success', 'Skill removed');
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

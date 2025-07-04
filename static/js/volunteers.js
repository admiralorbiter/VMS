/**
 * Volunteers Management JavaScript Module
 * ======================================
 * 
 * This module provides comprehensive functionality for managing volunteers
 * in the VMS, including search, sorting, pagination, deletion, and
 * dynamic form management for contact information.
 * 
 * Key Features:
 * - Advanced search with debouncing
 * - Sortable table columns with visual indicators
 * - Pagination with per-page selection
 * - Volunteer deletion with confirmation modal
 * - Purge functionality for bulk operations
 * - Dynamic phone and address management
 * - Participation tab system
 * - Event expansion/collapse functionality
 * - History section toggle
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
 * Dynamic Form Management:
 * - Add/remove phone number groups
 * - Add/remove address groups
 * - Primary contact selection
 * - Form data collection and submission
 * 
 * Participation System:
 * - Tab-based event participation display
 * - Event expansion/collapse
 * - Status-based filtering
 * - Dynamic content loading
 * 
 * Dependencies:
 * - Bootstrap 5.3.3 CSS/JS for modal functionality
 * - FontAwesome icons for visual indicators
 * - Custom CSS for form styling
 * 
 * API Endpoints:
 * - DELETE /volunteers/delete/{id}: Delete specific volunteer
 * - POST /volunteers/purge: Purge all volunteers
 * - POST /volunteers/sync: Sync volunteer data
 * 
 * CSS Classes:
 * - .sortable: Sortable column headers
 * - .phone-group/.address-group: Dynamic form groups
 * - .participation-tab: Participation tab styling
 * - .event-list: Event list containers
 * - .active: Active tab/selection styling
 * 
 * Data Attributes:
 * - data-volunteer-id: Volunteer ID for deletion
 * - data-volunteer-name: Volunteer name for confirmation
 * - data-status: Event status for filtering
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize sorting
    document.querySelectorAll('th.sortable').forEach(header => {
        header.addEventListener('click', () => handleSort(header));
        
        // Set initial sort indicators
        const url = new URL(window.location);
        const currentSortField = url.searchParams.get('sort_by');
        const currentSortDirection = url.searchParams.get('sort_direction');
        
        if (currentSortField === header.dataset.sort) {
            header.classList.add(`sort-${currentSortDirection}`);
            updateSortIcon(header, currentSortDirection);
        }
    });

    // Initialize search with debouncing
    const searchInputs = document.querySelectorAll('.filter-group input[type="text"]');
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(handleSearch, 600));
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

    // Initialize delete buttons
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', () => {
            const volunteerId = button.dataset.volunteerId;
            const volunteerName = button.dataset.volunteerName;
            confirmDelete(volunteerId, volunteerName);
        });
    });

    // Initialize modal cancel button
    const cancelButton = document.querySelector('.cancel-delete');
    if (cancelButton) {
        cancelButton.addEventListener('click', cancelDelete);
    }

    // Initialize modal confirm button
    const confirmButton = document.querySelector('.confirm-delete');
    if (confirmButton) {
        confirmButton.addEventListener('click', executeDelete);
    }

    // Initialize phone and address management
    document.addEventListener('DOMContentLoaded', function() {
        // ... existing code ...

        // Initialize add buttons
        document.getElementById('add-phone-btn')?.addEventListener('click', addPhoneGroup);
        document.getElementById('add-address-btn')?.addEventListener('click', addAddressGroup);
    });

    /**
     * Add new phone number input group
     * Creates dynamic form elements for phone number entry
     */
    function addPhoneGroup() {
        const container = document.getElementById('phones-container');
        const phoneGroup = document.createElement('div');
        phoneGroup.className = 'phone-group';
        phoneGroup.innerHTML = `
            <input type="tel" class="form-control phone-input" placeholder="Phone Number" required>
            <select class="form-select type-select">
                <option value="personal">Personal</option>
                <option value="professional">Professional</option>
            </select>
            <div class="form-check">
                <input type="radio" name="primary_phone" class="form-check-input primary-check">
                <label class="form-check-label">Primary</label>
            </div>
            <button type="button" class="btn btn-danger remove-btn" onclick="removeGroup(this)">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(phoneGroup);
    }

    /**
     * Add new address input group
     * Creates dynamic form elements for address entry
     */
    function addAddressGroup() {
        const container = document.getElementById('addresses-container');
        const addressGroup = document.createElement('div');
        addressGroup.className = 'address-group';
        addressGroup.innerHTML = `
            <input type="text" class="form-control" placeholder="Address Line 1" required>
            <input type="text" class="form-control" placeholder="Address Line 2">
            <input type="text" class="form-control" placeholder="City" required>
            <input type="text" class="form-control" placeholder="State" required>
            <input type="text" class="form-control" placeholder="ZIP Code" required>
            <input type="text" class="form-control" placeholder="Country" value="USA">
            <div class="address-actions">
                <select class="form-select type-select">
                    <option value="personal">Personal</option>
                    <option value="professional">Professional</option>
                </select>
                <div class="form-check">
                    <input type="radio" name="primary_address" class="form-check-input primary-check">
                    <label class="form-check-label">Primary</label>
                </div>
                <button type="button" class="btn btn-danger remove-btn" onclick="removeGroup(this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        container.appendChild(addressGroup);
    }

    /**
     * Remove phone or address group
     * @param {HTMLElement} button - Remove button element
     */
    function removeGroup(button) {
        button.closest('.phone-group, .address-group').remove();
    }

    // Update the form submission to include phones and addresses
    document.querySelector('form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // ... existing email collection code ...

        // Collect phone data
        const phones = [];
        document.querySelectorAll('.phone-group').forEach(group => {
            phones.push({
                number: group.querySelector('.phone-input').value,
                type: group.querySelector('.type-select').value,
                primary: group.querySelector('.primary-check').checked
            });
        });
        
        // Collect address data
        const addresses = [];
        document.querySelectorAll('.address-group').forEach(group => {
            const inputs = group.querySelectorAll('.form-control');
            addresses.push({
                address_line1: inputs[0].value,
                address_line2: inputs[1].value,
                city: inputs[2].value,
                state: inputs[3].value,
                zip_code: inputs[4].value,
                country: inputs[5].value,
                type: group.querySelector('.type-select').value,
                primary: group.querySelector('.primary-check').checked
            });
        });

        // Add to form data
        const phonesInput = document.createElement('input');
        phonesInput.type = 'hidden';
        phonesInput.name = 'phones';
        phonesInput.value = JSON.stringify(phones);
        this.appendChild(phonesInput);

        const addressesInput = document.createElement('input');
        addressesInput.type = 'hidden';
        addressesInput.name = 'addresses';
        addressesInput.value = JSON.stringify(addresses);
        this.appendChild(addressesInput);

        this.submit();
    });

    // Initialize participation tabs
    document.querySelectorAll('.participation-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs
            document.querySelectorAll('.participation-tab').forEach(t => {
                t.classList.remove('active');
            });
            
            // Add active class to clicked tab
            tab.classList.add('active');
            
            // Hide all event lists
            document.querySelectorAll('.event-list').forEach(list => {
                list.style.display = 'none';
            });
            
            // Show the selected event list
            // Get the text content of the span that contains just the status (not the count)
            const statusSpan = tab.querySelector('span:not(.participation-tab-count)');
            const status = statusSpan.textContent.trim();
            
            // Find the matching event list
            const targetList = document.querySelector(`.event-list[data-status="${status}"]`);
            if (targetList) {
                targetList.style.display = 'block';
            }
        });
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

function handleSort(header) {
    const sortField = header.dataset.sort;
    const currentSort = header.classList.contains('sort-asc') ? 'desc' : 'asc';
    
    // Remove sort classes from all headers
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add sort class to clicked header
    header.classList.add(`sort-${currentSort}`);
    
    // Update sort icon
    updateSortIcon(header, currentSort);
    
    // Update URL with sort parameters
    const url = new URL(window.location);
    url.searchParams.set('sort_by', sortField);
    url.searchParams.set('sort_direction', currentSort);
    window.location = url;
}

function updateSortIcon(header, direction) {
    const icon = header.querySelector('i.fa-sort, i.fa-sort-up, i.fa-sort-down');
    if (icon) {
        icon.classList.remove('fa-sort', 'fa-sort-up', 'fa-sort-down');
        icon.classList.add(direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
    }
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

let deleteVolunteerId = null;

function confirmDelete(id, name) {
    deleteVolunteerId = id;
    document.getElementById('volunteerName').textContent = name;
    document.getElementById('deleteModal').style.display = 'block';
    document.getElementById('modalOverlay').style.display = 'block';
}

function cancelDelete() {
    document.getElementById('deleteModal').style.display = 'none';
    document.getElementById('modalOverlay').style.display = 'none';
    deleteVolunteerId = null;
}

function executeDelete() {
    if (!deleteVolunteerId) return;
    
    fetch(`/volunteers/delete/${deleteVolunteerId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert('Error deleting volunteer: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error deleting volunteer: ' + error);
    })
    .finally(() => {
        cancelDelete();
    });
}

// Volunteer view page functionality
function toggleHistorySection() {
    const content = document.getElementById('history-content');
    const icon = document.getElementById('history-toggle-icon');
    
    if (content && icon) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.className = 'fa-solid fa-chevron-up';
        } else {
            content.style.display = 'none';
            icon.className = 'fa-solid fa-chevron-down';
        }
    }
}

// Event expansion functionality
function toggleEventExpansion(status, button) {
    const eventList = document.querySelector(`[data-status="${status}"]`);
    if (!eventList || !button) return;
    
    const hiddenEvents = eventList.querySelector('.event-items-hidden');
    const icon = button.querySelector('i');
    
    if (hiddenEvents && icon) {
        if (hiddenEvents.style.display === 'none') {
            // Show more events
            hiddenEvents.style.display = 'block';
            icon.className = 'fa-solid fa-chevron-up';
            button.innerHTML = '<i class="fa-solid fa-chevron-up"></i> Show less';
        } else {
            // Hide additional events
            hiddenEvents.style.display = 'none';
            icon.className = 'fa-solid fa-chevron-down';
            const count = hiddenEvents.querySelectorAll('.event-item').length;
            button.innerHTML = `<i class="fa-solid fa-chevron-down"></i> Show ${count} more events`;
        }
    }
}

// Initialize volunteer view page functionality
function initializeVolunteerView() {
    // Participation tabs functionality
    const participationTabs = document.querySelectorAll('.participation-tab');
    const eventLists = document.querySelectorAll('.event-list');
    
    participationTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabText = this.textContent.trim();
            let status;
            
            if (tabText.includes('Attended')) {
                status = 'Attended';
            } else if (tabText.includes('No-Shows')) {
                status = 'No-Show';
            } else if (tabText.includes('Cancelled')) {
                status = 'Cancelled';
            }
            
            // Update active tab
            participationTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide event lists
            eventLists.forEach(list => {
                if (list.dataset.status === status) {
                    list.style.display = 'block';
                } else {
                    list.style.display = 'none';
                }
            });
        });
    });
    
    // History filter functionality
    const filters = document.querySelectorAll('.history-filter');
    const historyItems = document.querySelectorAll('.history-item');
    
    filters.forEach(filter => {
        filter.addEventListener('click', function() {
            const filterType = this.dataset.type;
            
            // Update active filter
            filters.forEach(f => f.classList.remove('active'));
            this.classList.add('active');
            
            // Filter history items
            historyItems.forEach(item => {
                if (filterType === 'all' || item.dataset.type === filterType) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

// Initialize all functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize existing functionality
    // ... existing code ...

    // Initialize volunteer view page functionality
    initializeVolunteerView();
}); 
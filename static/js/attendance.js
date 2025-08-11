/**
 * Attendance Management JavaScript Module
 * ======================================
 *
 * This module provides functionality for the attendance management interface,
 * including tab switching, pagination, purge operations, and navigation.
 *
 * Key Features:
 * - Tab switching between students and teachers
 * - Pagination controls with page size selection
 * - Purge functionality with confirmation dialogs
 * - Dropdown menu management
 * - Navigation to detailed views
 * - URL parameter management
 *
 * Tab Management:
 * - Switch between students and teachers tables
 * - Maintain active tab state
 * - Hide/show table wrappers
 *
 * Pagination System:
 * - Page navigation with URL parameters
 * - Per-page selection (10, 25, 50, 100)
 * - URL state preservation
 * - Reset to first page on per-page change
 *
 * Purge Operations:
 * - Confirmation dialogs for safety
 * - AJAX requests to server
 * - Success/error notifications
 * - Page reload after successful purge
 *
 * Dependencies:
 * - Bootstrap 5.3.3 CSS/JS
 * - Custom attendance.css for styling
 * - showNotification function (global)
 *
 * API Endpoints:
 * - POST /attendance/purge: Purge attendance data
 * - GET /attendance/view/{type}/{id}: View attendance details
 *
 * CSS Classes:
 * - .hidden: Hide table wrappers
 * - .active: Active tab styling
 * - .show: Show dropdown menus
 * - .dropdown-content: Dropdown styling
 */

/**
 * Toggle the purge dropdown menu visibility
 */
function togglePurgeMenu() {
    document.getElementById("purgeMenu").classList.toggle("show");
}

/**
 * Close dropdown menus when clicking outside
 * Handles global click events for dropdown management
 */
window.onclick = function(event) {
    if (!event.target.matches('.purge-btn')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        for (var i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}

/**
 * Confirm and execute purge operations
 * @param {string} type - Type of data to purge ('all', 'students', 'teachers')
 */
function confirmPurge(type) {
    let message = '';
    switch(type) {
        case 'all':
            message = 'Are you sure you want to purge ALL student and teacher data? This action cannot be undone.';
            break;
        case 'students':
            message = 'Are you sure you want to purge all student data? This action cannot be undone.';
            break;
        case 'teachers':
            message = 'Are you sure you want to purge all teacher data? This action cannot be undone.';
            break;
    }

    if (confirm(message)) {
        fetch('/attendance/purge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: type })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification(data.message, 'success');
                location.reload();
            } else {
                showNotification('Error: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showNotification('Error: ' + error, 'error');
        });
    }
}

/**
 * Switch between students and teachers tabs
 * @param {string} tabName - Name of tab to switch to ('students' or 'teachers')
 */
function switchTab(tabName) {
    const tables = document.querySelectorAll('.attendance-table-wrapper');
    const tabs = document.querySelectorAll('.tab-btn');

    // Hide all tables and remove active class from tabs
    tables.forEach(table => table.classList.add('hidden'));
    tabs.forEach(tab => tab.classList.remove('active'));

    // Show selected table and activate corresponding tab
    document.getElementById(`${tabName}TableWrapper`).classList.remove('hidden');
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
}

/**
 * Navigate to detailed view for specific attendance record
 * @param {string} type - Type of record ('student' or 'teacher')
 * @param {number} id - Record ID
 */
function viewDetails(type, id) {
    window.location.href = `/attendance/view/${type}/${id}`;
}

/**
 * Change page in pagination
 * @param {number} page - Page number to navigate to
 * @param {string} type - Type of data ('students' or 'teachers')
 */
function changePage(page, type) {
    const perPage = document.getElementById('perPageSelect').value;
    const currentUrl = new URL(window.location.href);

    currentUrl.searchParams.set('page', page);
    currentUrl.searchParams.set('per_page', perPage);

    window.location.href = currentUrl.toString();
}

/**
 * Change items per page in pagination
 * Resets to first page when changing page size
 */
function changePerPage() {
    const perPage = document.getElementById('perPageSelect').value;
    const currentUrl = new URL(window.location.href);

    currentUrl.searchParams.set('page', 1); // Reset to first page
    currentUrl.searchParams.set('per_page', perPage);

    window.location.href = currentUrl.toString();
}

/**
 * Search teachers by name in the teachers table
 * Filters table rows based on search input
 */
function searchTeachers() {
    const searchInput = document.getElementById('teacherSearch');
    const searchTerm = searchInput.value.toLowerCase();
    const table = document.getElementById('teachersTable');
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const nameCell = rows[i].getElementsByTagName('td')[0]; // Name is first column
        if (nameCell) {
            const name = nameCell.textContent || nameCell.innerText;
            if (name.toLowerCase().indexOf(searchTerm) > -1) {
                rows[i].style.display = '';
            } else {
                rows[i].style.display = 'none';
            }
        }
    }
}

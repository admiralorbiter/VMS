/**
 * District Year End Detail JavaScript Module
 * ========================================
 *
 * This module provides interactive filtering and statistics calculation
 * for the district year-end report detail page, allowing users to
 * filter events by type and view dynamic statistics.
 *
 * Key Features:
 * - Event type filtering with visual selection
 * - Dynamic statistics calculation
 * - Real-time count updates
 * - Month-by-month statistics
 * - Total summary statistics
 * - Interactive card-based interface
 *
 * Filtering System:
 * - Click to filter by event type
 * - Toggle to show all events
 * - Visual feedback for selected type
 * - Automatic statistics recalculation
 * - Support for multiple event types
 *
 * Statistics Calculation:
 * - Event count per month
 * - Student count per month
 * - Volunteer count per month
 * - Hours calculation per month
 * - Total summary statistics
 * - Real-time updates on filter changes
 *
 * Data Structure:
 * - Event rows with type in column 4
 * - Student count in column 6
 * - Volunteer count in column 7
 * - Hours in column 8
 * - Month cards with individual statistics
 * - Summary stats at page top
 *
 * Visual Feedback:
 * - .selected class for active event type
 * - Dynamic statistics display
 * - Real-time count updates
 * - Clear visual hierarchy
 *
 * Dependencies:
 * - Bootstrap 5.3.3 CSS for card styling
 * - Custom CSS for event type cards
 * - FontAwesome icons (if used)
 *
 * CSS Classes:
 * - .event-type-card: Event type selection cards
 * - .selected: Active event type selection
 * - .month-card: Month-specific data containers
 * - .month-stats: Month statistics display
 * - .summary-stats: Overall summary statistics
 * - .stat-card: Individual statistic cards
 *
 * Usage:
 * - Automatically initializes on DOM content loaded
 * - Requires event type cards with .event-type-card class
 * - Requires month cards with .month-card class
 * - Requires summary stats container
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get all event type cards
    const eventTypeCards = document.querySelectorAll('.event-type-card');

    // Track currently selected event type
    let selectedEventType = null;

    // Add click handlers to event type cards
    eventTypeCards.forEach(card => {
        card.addEventListener('click', function() {
            const eventType = this.querySelector('.type-name').textContent;

            // Toggle selection
            if (selectedEventType === eventType) {
                // If clicking the same type again, show all events
                selectedEventType = null;
                showAllEvents();
                eventTypeCards.forEach(c => c.classList.remove('selected'));
            } else {
                // Select new event type
                selectedEventType = eventType;
                filterEventsByType(eventType);
                eventTypeCards.forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
            }

            // Update the visible event count
            updateEventCounts();
        });
    });

    /**
     * Filter events by specific event type
     * @param {string} eventType - Type of events to show
     */
    function filterEventsByType(eventType) {
        // Get all event rows across all months
        const eventRows = document.querySelectorAll('.events-table tbody tr');

        eventRows.forEach(row => {
            const rowType = row.querySelector('td:nth-child(4)').textContent;
            if (rowType === eventType) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    /**
     * Show all events (remove filtering)
     */
    function showAllEvents() {
        const eventRows = document.querySelectorAll('.events-table tbody tr');
        eventRows.forEach(row => {
            row.style.display = '';
        });
    }

    /**
     * Update event counts and statistics for all months
     * Recalculates totals based on currently visible events
     */
    function updateEventCounts() {
        // Update counts for each month
        const monthCards = document.querySelectorAll('.month-card');

        monthCards.forEach(monthCard => {
            const visibleRows = monthCard.querySelectorAll('tbody tr:not([style*="display: none"])');

            // Calculate totals for visible rows
            let students = 0;
            let volunteers = 0;
            let hours = 0;

            visibleRows.forEach(row => {
                students += parseInt(row.querySelector('td:nth-child(6)').textContent) || 0;
                volunteers += parseInt(row.querySelector('td:nth-child(7)').textContent) || 0;
                hours += parseFloat(row.querySelector('td:nth-child(8)').textContent) || 0;
            });

            // Update the month stats
            const monthStats = monthCard.querySelector('.month-stats');
            monthStats.innerHTML = `
                <span>${visibleRows.length} Events</span>
                <span>${students} Students</span>
                <span>${volunteers} Volunteers</span>
                <span>${hours.toFixed(1)} Hours</span>
            `;
        });

        // Update total stats at the top
        updateTotalStats();
    }

    /**
     * Update total summary statistics
     * Calculates overall totals across all visible events
     */
    function updateTotalStats() {
        const visibleRows = document.querySelectorAll('.events-table tbody tr:not([style*="display: none"])');
        let totalStudents = 0;
        let totalVolunteers = 0;
        let totalHours = 0;

        visibleRows.forEach(row => {
            totalStudents += parseInt(row.querySelector('td:nth-child(6)').textContent) || 0;
            totalVolunteers += parseInt(row.querySelector('td:nth-child(7)').textContent) || 0;
            totalHours += parseFloat(row.querySelector('td:nth-child(8)').textContent) || 0;
        });

        // Update summary stats
        document.querySelector('.summary-stats .stat-card:nth-child(1) .stat-value').textContent = visibleRows.length;
        document.querySelector('.summary-stats .stat-card:nth-child(2) .stat-value').textContent = totalStudents;
        document.querySelector('.summary-stats .stat-card:nth-child(3) .stat-value').textContent = totalVolunteers;
        document.querySelector('.summary-stats .stat-card:nth-child(4) .stat-value').textContent = totalHours.toFixed(1);
    }
});

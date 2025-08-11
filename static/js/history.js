/**
 * History Management JavaScript Module
 * ====================================
 *
 * This module provides advanced functionality for managing and displaying
 * activity history with grouping, filtering, and collapsible sections.
 *
 * Key Features:
 * - Automatic grouping of history items by month/year
 * - Collapsible group sections with icons
 * - Filter system for different activity types
 * - Timeline-based layout
 * - Dynamic content management
 * - Responsive design support
 *
 * History Grouping:
 * - Groups items by month and year
 * - Sorts groups in reverse chronological order
 * - Creates collapsible headers with icons
 * - Maintains original item structure
 *
 * Filter System:
 * - Filter by activity type (Email, Call, Meeting, Other)
 * - Toggle filters on/off
 * - Show/hide groups based on visible items
 * - Maintain filter state
 *
 * Collapse Functionality:
 * - Click to expand/collapse groups
 * - Icon rotation for visual feedback
 * - Smooth transitions
 * - State preservation
 *
 * Activity Type Detection:
 * - Automatic detection based on summary content
 * - Email detection via keywords or email-header class
 * - Call detection via phone-related keywords
 * - Meeting detection via meeting-related keywords
 * - Default to "Other" for unrecognized types
 *
 * Dependencies:
 * - FontAwesome icons for chevron indicators
 * - Custom history.css for styling
 * - Bootstrap 5.3.3 for layout support
 *
 * CSS Classes:
 * - .history-timeline: Main timeline container
 * - .history-group: Group container
 * - .history-group-header: Collapsible header
 * - .history-group-content: Group content area
 * - .history-item: Individual history item
 * - .history-filter: Filter button
 * - .active: Active filter state
 *
 * Data Attributes:
 * - data-date: Date string for grouping
 * - data-type: Filter type for buttons
 */

/**
 * HistoryManager Class
 * Manages the history display, grouping, filtering, and interaction
 */
class HistoryManager {
    /**
     * Initialize the HistoryManager
     * Sets up filters, grouping, and event handlers
     */
    constructor() {
        this.page = 1;
        this.loading = false;
        this.activeFilters = new Set();
        this.initialize();
    }

    /**
     * Initialize the history manager
     * Sets up event listeners and initial grouping
     */
    initialize() {
        // Initialize filters
        document.querySelectorAll('.history-filter').forEach(filter => {
            filter.addEventListener('click', () => this.toggleFilter(filter));
        });

        // Group histories by month initially
        this.groupHistories();

        // Initialize collapse functionality after grouping
        this.initializeCollapseButtons();
    }

    /**
     * Initialize collapse button functionality
     * Sets up click handlers for group headers
     */
    initializeCollapseButtons() {
        document.querySelectorAll('.history-group-header').forEach(header => {
            header.addEventListener('click', (e) => this.handleCollapse(e));
        });
    }

    /**
     * Handle collapse/expand functionality for history groups
     * @param {Event} e - Click event on group header
     */
    handleCollapse(e) {
        const header = e.currentTarget;
        const group = header.closest('.history-group');
        const content = group.querySelector('.history-group-content');
        const icon = header.querySelector('.fa-chevron-down, .fa-chevron-right');

        if (!content || !icon) return;

        const isCollapsed = content.style.display === 'none';

        // Toggle content visibility
        content.style.display = isCollapsed ? 'block' : 'none';

        // Toggle icon
        icon.classList.toggle('fa-chevron-down', isCollapsed);
        icon.classList.toggle('fa-chevron-right', !isCollapsed);
    }

    /**
     * Group history items by month and year
     * Creates collapsible sections with headers
     */
    groupHistories() {
        const timeline = document.querySelector('.history-timeline');
        const items = Array.from(document.querySelectorAll('.history-item'));

        // Clear timeline
        timeline.innerHTML = '';

        // Group items by month/year
        const groups = items.reduce((acc, item) => {
            const dateStr = item.dataset.date;
            const date = dateStr ? new Date(dateStr) : new Date();

            if (isNaN(date.getTime())) {
                console.warn('Invalid date found:', dateStr);
                return acc;
            }

            const key = `${date.getFullYear()}-${date.getMonth()}`;
            if (!acc[key]) {
                acc[key] = {
                    date,
                    items: []
                };
            }
            acc[key].items.push(item);
            return acc;
        }, {});

        // Create and append group elements
        Object.values(groups)
            .sort((a, b) => b.date - a.date)
            .forEach(group => {
                const groupEl = document.createElement('div');
                groupEl.className = 'history-group';

                const header = document.createElement('div');
                header.className = 'history-group-header';
                header.innerHTML = `
                    <span>${group.date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</span>
                    <i class="fa-solid fa-chevron-down"></i>
                `;

                const content = document.createElement('div');
                content.className = 'history-group-content';
                group.items.forEach(item => content.appendChild(item.cloneNode(true)));

                groupEl.appendChild(header);
                groupEl.appendChild(content);
                timeline.appendChild(groupEl);
            });
    }

    /**
     * Toggle filter for history items
     * @param {HTMLElement} filter - Filter button element
     */
    toggleFilter(filter) {
        const filterType = filter.dataset.type;
        filter.classList.toggle('active');

        if (this.activeFilters.has(filterType)) {
            this.activeFilters.delete(filterType);
        } else {
            this.activeFilters.add(filterType);
        }

        // Filter items within their groups
        document.querySelectorAll('.history-group').forEach(group => {
            const items = group.querySelectorAll('.history-item');
            let hasVisibleItems = false;

            items.forEach(item => {
                // Get the summary text
                const summary = item.querySelector('.history-summary')?.textContent ||
                              item.querySelector('.email-header')?.textContent || '';

                // Determine type based on summary content
                let type = 'Other';
                if (summary.toLowerCase().includes('email') || item.querySelector('.email-header')) {
                    type = 'Email';
                } else if (summary.toLowerCase().includes('call') || summary.toLowerCase().includes('phone')) {
                    type = 'Call';
                } else if (summary.toLowerCase().includes('meeting') || summary.toLowerCase().includes('met with')) {
                    type = 'Meeting';
                }

                const shouldShow = this.activeFilters.size === 0 || this.activeFilters.has(type);
                item.style.display = shouldShow ? 'block' : 'none';

                if (shouldShow) {
                    hasVisibleItems = true;
                }
            });

            // Show/hide the group based on whether it has visible items
            group.style.display = hasVisibleItems ? 'block' : 'none';

            // Handle the content visibility
            const content = group.querySelector('.history-group-content');
            if (content) {
                content.style.display = hasVisibleItems ? 'block' : 'none';
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new HistoryManager();
});

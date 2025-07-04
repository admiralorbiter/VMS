/**
 * Calendar JavaScript functionality
 * Handles FullCalendar initialization, event interactions, and modal management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize calendar elements
    const calendarEl = document.getElementById('calendar');
    const eventModal = new bootstrap.Modal(document.getElementById('eventModal'));

    // Initialize FullCalendar with configuration
    const calendar = new FullCalendar.Calendar(calendarEl, {
        // Set initial view to month grid
        initialView: 'dayGridMonth',
        
        // Configure header toolbar with navigation and view options
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay,listMonth'
        },
        
        // API endpoint for fetching events
        events: '/calendar/events',
        
        // Handle event click to show details modal
        eventClick: function(info) {
            populateEventModal(info.event);
            setupViewDetailsButton(info.event.id);
            eventModal.show();
        },
        
        // Customize event rendering with styling and tooltips
        eventDidMount: function(info) {
            applyEventStyling(info);
            addEventTooltip(info);
        }
    });

    // Render the calendar
    calendar.render();
});

/**
 * Populate the event modal with event details
 * @param {Object} event - FullCalendar event object
 */
function populateEventModal(event) {
    document.getElementById('eventTitle').textContent = event.title;
    document.getElementById('eventDate').textContent = event.start.toLocaleDateString();
    document.getElementById('eventTime').textContent = event.start.toLocaleTimeString();
    document.getElementById('eventLocation').textContent = event.extendedProps.location || 'N/A';
    document.getElementById('eventType').textContent = event.extendedProps.type || 'N/A';
    document.getElementById('eventStatus').textContent = event.extendedProps.status || 'N/A';
    document.getElementById('eventDescription').textContent = event.extendedProps.description || 'N/A';
}

/**
 * Set up the view details button with correct event URL
 * @param {string} eventId - The event ID
 */
function setupViewDetailsButton(eventId) {
    const viewEventBtn = document.getElementById('viewEventBtn');
    viewEventBtn.href = `/events/view/${eventId}`;
}

/**
 * Apply custom styling to events based on their properties
 * @param {Object} info - Event mount information from FullCalendar
 */
function applyEventStyling(info) {
    // Add cancelled event styling
    if (info.event.extendedProps.status === 'Cancelled') {
        info.el.classList.add('cancelled-event');
    }
    
    // Add past event styling
    if (info.event.extendedProps.is_past) {
        info.el.classList.add('past-event');
    }
}

/**
 * Add tooltip to event with detailed information
 * @param {Object} info - Event mount information from FullCalendar
 */
function addEventTooltip(info) {
    const tooltipContent = `
        ${info.event.title}
        <br>
        Status: ${info.event.extendedProps.status}
        <br>
        Type: ${info.event.extendedProps.type}
        <br>
        Volunteers: ${info.event.extendedProps.volunteer_count}/${info.event.extendedProps.volunteers_needed || 'N/A'}
    `;
    
    new bootstrap.Tooltip(info.el, {
        title: tooltipContent,
        html: true,
        placement: 'top',
        trigger: 'hover',
        container: 'body'
    });
} 
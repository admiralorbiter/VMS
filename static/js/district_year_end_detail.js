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

    function showAllEvents() {
        const eventRows = document.querySelectorAll('.events-table tbody tr');
        eventRows.forEach(row => {
            row.style.display = '';
        });
    }

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
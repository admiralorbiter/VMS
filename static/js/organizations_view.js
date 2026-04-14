function filterVolunteers(query) {
    query = query.toLowerCase();
    const cards = document.querySelectorAll('#volunteersGrid .participant-card');
    cards.forEach(card => {
        const name = card.querySelector('.participant-name').textContent.toLowerCase();
        card.style.display = name.includes(query) ? '' : 'none';
    });
}

function toggleVolunteerExpansion() {
    const allVolunteers = document.querySelectorAll('#volunteersGrid .participant-card.volunteer');
    const showMoreBtn = document.querySelector('.show-more-volunteers-btn');
    const isExpanded = showMoreBtn.classList.contains('expanded');

    console.log('Toggle clicked. Total volunteers found:', allVolunteers.length);
    console.log('Is expanded:', isExpanded);

    if (isExpanded) {
        // Collapse - hide all volunteers beyond the first 4
        allVolunteers.forEach((volunteer, index) => {
            if (index >= 4) {
                volunteer.style.display = 'none';
                volunteer.classList.add('volunteer-hidden');
                console.log('Hiding volunteer:', index, volunteer);
            }
        });
        showMoreBtn.classList.remove('expanded');
        const hiddenCount = allVolunteers.length - 4;
        showMoreBtn.innerHTML = '<i class="fa-solid fa-chevron-down"></i> Show ' + hiddenCount + ' more volunteers';
    } else {
        // Expand - show all volunteers
        allVolunteers.forEach((volunteer, index) => {
            if (index >= 4) {
                volunteer.style.display = 'block';
                volunteer.classList.remove('volunteer-hidden');
                console.log('Showing volunteer:', index, volunteer);
            }
        });
        showMoreBtn.classList.add('expanded');
        showMoreBtn.innerHTML = '<i class="fa-solid fa-chevron-up"></i> Show Less';
    }
}

// Organization Communication History Functions
function toggleOrgHistorySection() {
    const content = document.getElementById('org-history-content');
    const icon = document.getElementById('org-history-toggle-icon');

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

function toggleEmailContent(element) {
    const historyItem = element.closest('.history-item');
    const fullContent = historyItem.querySelector('.full-email-content');
    const preview = historyItem.querySelector('.email-preview');
    const toggleButton = historyItem.querySelector('.email-toggle-btn:not(.secondary)');
    const showLessButton = historyItem.querySelector('.email-toggle-btn.secondary');

    if (fullContent && fullContent.style.display === 'none' || fullContent.style.display === '') {
        // Show full content
        fullContent.style.display = 'block';
        preview.style.display = 'none';
        if (toggleButton) toggleButton.style.display = 'none';
        if (showLessButton) showLessButton.style.display = 'inline-flex';

        // Add smooth animation
        fullContent.style.opacity = '0';
        fullContent.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            fullContent.style.transition = 'all 0.3s ease';
            fullContent.style.opacity = '1';
            fullContent.style.transform = 'translateY(0)';
        }, 10);
    } else {
        // Hide full content
        if (fullContent) {
            fullContent.style.transition = 'all 0.3s ease';
            fullContent.style.opacity = '0';
            fullContent.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                fullContent.style.display = 'none';
                preview.style.display = 'block';
                if (toggleButton) toggleButton.style.display = 'inline-flex';
                if (showLessButton) showLessButton.style.display = 'none';
            }, 300);
        }
    }
}

function updateOrgFilterCounts(activeFilter = 'all') {
    console.log('updateOrgFilterCounts called with filter:', activeFilter);
    const historyItems = document.querySelectorAll('.history-item');
    const filters = document.querySelectorAll('.history-filter');

    console.log('Found history items:', historyItems.length);
    console.log('Found filters:', filters.length);

    // Count visible items for each type
    const counts = {
        'all': historyItems.length,
        'Email': 0,
        'Call': 0,
        'Meeting': 0,
        'Note': 0
    };

    historyItems.forEach(item => {
        const type = item.dataset.type;
        console.log('History item type:', type);
        // Handle both exact matches and inferred types
        if (counts.hasOwnProperty(type)) {
            counts[type]++;
        } else if (type && type.includes('Email')) {
            counts['Email']++;
        } else if (type && type.includes('Call')) {
            counts['Call']++;
        } else if (type && type.includes('Meeting')) {
            counts['Meeting']++;
        } else if (type && type.includes('Note')) {
            counts['Note']++;
        }
    });

    console.log('Counts:', counts);

    // Update filter labels
    filters.forEach(filter => {
        const type = filter.dataset.type;
        const count = counts[type] || 0;
        const span = filter.querySelector('span');
        if (span) {
            if (type === 'all') {
                span.textContent = `All (${count})`;
            } else {
                span.textContent = `${type} (${count})`;
            }
        }
    });
}

// Initialize volunteer expansion state
function initializeVolunteerExpansion() {
    const allVolunteers = document.querySelectorAll('#volunteersGrid .participant-card.volunteer');
    const showMoreBtn = document.getElementById('showMoreVolunteersBtn');

    if (showMoreBtn && allVolunteers.length > 4) {
        // Ensure initial state is collapsed (only first 4 visible)
        allVolunteers.forEach((volunteer, index) => {
            if (index >= 4) {
                volunteer.style.display = 'none';
                volunteer.classList.add('volunteer-hidden');
            }
        });

        // Ensure button is in collapsed state
        showMoreBtn.classList.remove('expanded');
        const hiddenCount = allVolunteers.length - 4;
        showMoreBtn.innerHTML = '<i class="fa-solid fa-chevron-down"></i> Show ' + hiddenCount + ' more volunteers';

        console.log('Initialized volunteer expansion. Total volunteers:', allVolunteers.length, 'Hidden:', hiddenCount);
    }
}

// Initialize organization history filters when the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing organization history filters...');

    // Initialize volunteer expansion first
    initializeVolunteerExpansion();

    const filters = document.querySelectorAll('.history-filter');
    const historyItems = document.querySelectorAll('.history-item');

    console.log('Found filters:', filters.length);
    console.log('Found history items:', historyItems.length);

    // Initialize filter counts
    updateOrgFilterCounts();

    filters.forEach(filter => {
        filter.addEventListener('click', function() {
            const filterType = this.dataset.type;
            console.log('Filter clicked:', filterType);

            // Update active filter
            filters.forEach(f => f.classList.remove('active'));
            this.classList.add('active');

            // Filter history items
            historyItems.forEach(item => {
                const itemType = item.dataset.type;
                let shouldShow = false;

                if (filterType === 'all') {
                    shouldShow = true;
                } else if (filterType === 'Email' && (itemType === 'Email' || itemType.includes('Email'))) {
                    shouldShow = true;
                } else if (filterType === 'Call' && (itemType === 'Call' || itemType.includes('Call'))) {
                    shouldShow = true;
                } else if (filterType === 'Meeting' && (itemType === 'Meeting' || itemType.includes('Meeting'))) {
                    shouldShow = true;
                } else if (filterType === 'Note' && (itemType === 'Note' || itemType.includes('Note'))) {
                    shouldShow = true;
                } else if (itemType === filterType) {
                    shouldShow = true;
                }

                item.style.display = shouldShow ? 'block' : 'none';
            });

            // Update filter counts
            updateOrgFilterCounts(filterType);
        });
    });
});

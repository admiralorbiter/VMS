class HistoryManager {
    constructor() {
        this.page = 1;
        this.loading = false;
        this.activeFilters = new Set();
        this.initialize();
    }

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

    initializeCollapseButtons() {
        document.querySelectorAll('.history-group-header').forEach(header => {
            header.addEventListener('click', (e) => this.handleCollapse(e));
        });
    }

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
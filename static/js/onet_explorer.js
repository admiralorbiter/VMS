document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const searchResultsList = document.getElementById('searchResultsList');
    const detailView = document.getElementById('detailView');
    const backToList = document.getElementById('backToList');
    const jobList = document.getElementById('jobList');
    const searchTypeInputs = document.getElementsByName('searchType');
    
    // Function to get the current search type
    function getSearchType() {
        return document.querySelector('input[name="searchType"]:checked').value;
    }
    
    // Function to perform the search
    async function performSearch() {
        const keyword = searchInput.value.trim();
        if (!keyword) return;
        
        try {
            const searchType = getSearchType();
            const response = await fetch(`/playground/search-onet?keyword=${encodeURIComponent(keyword)}&type=${searchType}`);
            const data = await response.json();
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            displaySearchResults(data);
        } catch (error) {
            showError('An error occurred while searching. Please try again.');
        }
    }
    
    // Function to display search results list
    function displaySearchResults(data) {
        detailView.style.display = 'none';
        searchResultsList.style.display = 'block';
        
        if (!data || !data.length) {
            jobList.innerHTML = '<div class="alert alert-info">No results found</div>';
            return;
        }
        
        const resultsHtml = data.map(job => `
            <button class="list-group-item list-group-item-action" data-code="${job.code}">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${job.title}</h5>
                </div>
                <p class="mb-1">${job.description || ''}</p>
            </button>
        `).join('');
        
        jobList.innerHTML = resultsHtml;
        
        // Add click handlers to job items
        jobList.querySelectorAll('.list-group-item').forEach(item => {
            item.addEventListener('click', () => loadJobDetails(item.dataset.code));
        });
    }
    
    // Function to load job details
    async function loadJobDetails(code) {
        try {
            const response = await fetch(`/playground/job-details/${code}`);
            const data = await response.json();
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            displayJobDetails(data);
        } catch (error) {
            showError('An error occurred while loading job details. Please try again.');
        }
    }
    
    // Function to display job details
    function displayJobDetails(data) {
        searchResultsList.style.display = 'none';
        detailView.style.display = 'block';
        
        // Set job title
        document.getElementById('jobTitle').textContent = data.title;
        
        // Overview tab
        document.getElementById('overviewContent').innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Description</h5>
                    <p class="card-text">${data.description || 'No description available'}</p>
                </div>
            </div>
        `;
        
        // Skills tab
        if (data.skills && data.skills.length) {
            const skillsHtml = data.skills.map(skill => {
                const level = skill.level || 0;
                const levelPercent = level; // The value is already a percentage (0-100)
                const importanceClass = skill.importance ? 'bg-primary' : 'bg-secondary';
                return `
                    <div class="card mb-2">
                        <div class="card-body">
                            <h5 class="card-title">${skill.name}</h5>
                            <p class="card-text">${skill.description || ''}</p>
                            <div class="progress">
                                <div class="progress-bar ${importanceClass}" role="progressbar" 
                                    style="width: ${levelPercent}%" 
                                    aria-valuenow="${level}" 
                                    aria-valuemin="0" 
                                    aria-valuemax="100">
                                    Score: ${level}%
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            document.getElementById('skillsContent').innerHTML = skillsHtml;
        }
        
        // Knowledge tab
        if (data.knowledge && data.knowledge.length) {
            const knowledgeHtml = data.knowledge.map(item => {
                const level = item.level || 0;
                const levelPercent = level; // The value is already a percentage (0-100)
                const importanceClass = item.importance ? 'bg-primary' : 'bg-secondary';
                return `
                    <div class="card mb-2">
                        <div class="card-body">
                            <h5 class="card-title">${item.name}</h5>
                            <p class="card-text">${item.description || ''}</p>
                            <div class="progress">
                                <div class="progress-bar ${importanceClass}" role="progressbar" 
                                    style="width: ${levelPercent}%" 
                                    aria-valuenow="${level}" 
                                    aria-valuemin="0" 
                                    aria-valuemax="100">
                                    Score: ${level}%
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            document.getElementById('knowledgeContent').innerHTML = knowledgeHtml;
        }
        
        // Interests tab
        if (data.interests && data.interests.length) {
            const interestsHtml = data.interests.map(item => `
                <div class="card mb-2">
                    <div class="card-body">
                        <h5 class="card-title">${item.name}</h5>
                        <p class="card-text">${item.description || ''}</p>
                    </div>
                </div>
            `).join('');
            document.getElementById('interestsContent').innerHTML = interestsHtml;
        }
        
        // Related Jobs tab - Updated to match the search results style
        const relatedContent = document.getElementById('relatedContent');
        if (data.related && data.related.length) {
            const relatedHtml = data.related.map(job => `
                <button class="list-group-item list-group-item-action" data-code="${job.code}" onclick="loadJobDetails('${job.code}')">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${job.title}</h5>
                    </div>
                    <p class="mb-1">${job.description || ''}</p>
                </button>
            `).join('');
            relatedContent.innerHTML = `<div class="list-group">${relatedHtml}</div>`;
        } else {
            relatedContent.innerHTML = '<div class="alert alert-info">No related jobs found</div>';
        }
    }
    
    // Function to show errors
    function showError(message) {
        jobList.innerHTML = `
            <div class="alert alert-danger" role="alert">
                ${message}
            </div>
        `;
    }
    
    // Event listeners
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    backToList.addEventListener('click', function() {
        detailView.style.display = 'none';
        searchResultsList.style.display = 'block';
    });
    
    // Update placeholder text based on search type
    searchTypeInputs.forEach(input => {
        input.addEventListener('change', function() {
            searchInput.placeholder = `Enter ${this.value} title or keyword...`;
        });
    });
});
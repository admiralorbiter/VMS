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
        const query = searchInput.value.trim();
        const searchType = getSearchType();
        
        if (query === '') return;
        
        // Show loading state
        searchResultsList.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        searchResultsList.style.display = 'block';
        detailView.style.display = 'none';
        
        try {
            const url = `/playground/search?query=${encodeURIComponent(query)}&type=${searchType}`;
            const response = await fetch(url);
            const results = await response.json();
            
            if (results.error) {
                throw new Error(results.error);
            }
            
            if (!results || results.length === 0) {
                searchResultsList.innerHTML = '<div class="alert alert-info">No results found.</div>';
                return;
            }
            
            const resultsHtml = results.map(result => {
                if (searchType === 'skill') {
                    return `
                        <button class="list-group-item list-group-item-action" data-skill-id="${result.code}">
                            <h5 class="mb-1">${result.title}</h5>
                            <p class="mb-1">${result.description || ''}</p>
                            <small class="text-muted">Skill ID: ${result.code}</small>
                        </button>
                    `;
                } else {
                    return `
                        <button class="list-group-item list-group-item-action" data-code="${result.code}">
                            <h5 class="mb-1">${result.title}</h5>
                            <p class="mb-1">${result.description || ''}</p>
                            <small class="text-muted">Code: ${result.code}</small>
                        </button>
                    `;
                }
            }).join('');
            
            searchResultsList.innerHTML = resultsHtml;
            
            // Add click handlers to items
            if (searchType === 'skill') {
                searchResultsList.querySelectorAll('.list-group-item-action').forEach(item => {
                    item.addEventListener('click', () => {
                        const skillId = item.dataset.skillId;
                        if (skillId) {
                            loadSkillDetails(skillId);
                        }
                    });
                });
            } else {
                searchResultsList.querySelectorAll('.list-group-item-action').forEach(item => {
                    item.addEventListener('click', () => {
                        const code = item.dataset.code;
                        if (code) {
                            loadJobDetails(code);
                        }
                    });
                });
            }
        } catch (error) {
            console.error('Error:', error);  
            searchResultsList.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        }
    }
    
    // Function to load job details
    async function loadJobDetails(code) {
        try {
            // Show loading state in detail view while preserving structure
            detailView.style.display = 'block';
            searchResultsList.style.display = 'none';
            
            // Reset all tab contents to loading state
            ['overviewContent', 'skillsContent', 'knowledgeContent', 'interestsContent', 'relatedContent'].forEach(id => {
                document.getElementById(id).innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            });
            
            const response = await fetch(`/playground/job-details/${code}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            displayJobDetails(data);
        } catch (error) {
            console.error('Error:', error);  
            // Show error in overview tab instead of wiping the entire view
            document.getElementById('overviewContent').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        }
    }
    
    // Function to load skill details
    async function loadSkillDetails(skillId) {
        try {
            detailView.style.display = 'block';
            searchResultsList.style.display = 'none';
            
            const response = await fetch(`/playground/skill/${skillId}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            displaySkillDetails(data);
        } catch (error) {
            console.error('Error:', error);
            document.getElementById('overviewContent').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
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
                const levelPercent = level;
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
                const levelPercent = level;
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
        const interestsContent = document.getElementById('interestsContent');
        if (data.interests && data.interests.length) {
            const interestsHtml = data.interests.map(interest => `
                <div class="card mb-2">
                    <div class="card-body">
                        <h5 class="card-title">${interest.name}</h5>
                        <p class="card-text">${interest.description || ''}</p>
                    </div>
                </div>
            `).join('');
            interestsContent.innerHTML = interestsHtml;
        } else {
            interestsContent.innerHTML = '<div class="alert alert-info">No interests information available.</div>';
        }
        
        // Related Jobs tab
        const relatedContent = document.getElementById('relatedContent');
        if (data.related && data.related.length) {
            const relatedHtml = data.related.map(job => `
                <button class="list-group-item list-group-item-action" data-code="${job.code}">
                    <h5 class="mb-1">${job.title}</h5>
                    <p class="mb-1">${job.description || ''}</p>
                    <small class="text-muted">Code: ${job.code}</small>
                </button>
            `).join('');
            relatedContent.innerHTML = `<div class="list-group">${relatedHtml}</div>`;
            
            // Add click handlers to related job items
            relatedContent.querySelectorAll('.list-group-item-action').forEach(item => {
                item.addEventListener('click', () => {
                    const code = item.dataset.code;
                    if (code) {
                        loadJobDetails(code);
                    }
                });
            });
        } else {
            relatedContent.innerHTML = '<div class="alert alert-info">No related jobs found.</div>';
        }
    }
    
    // Function to display skill details
    function displaySkillDetails(data) {
        // Update overview tab
        const overviewHtml = `
            <h3>${data.title}</h3>
            <p class="lead">${data.description}</p>
            ${data.tags ? `<p><strong>Tags:</strong> ${data.tags.join(', ')}</p>` : ''}
        `;
        document.getElementById('overviewContent').innerHTML = overviewHtml;
        
        // Update related occupations tab
        let occupationsHtml = '<div class="list-group">';
        if (data.related_occupations && data.related_occupations.length > 0) {
            occupationsHtml += data.related_occupations.map(occ => `
                <button class="list-group-item list-group-item-action" data-code="${occ.code}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-1">${occ.title}</h5>
                            <p class="mb-1">${occ.description || ''}</p>
                        </div>
                        <div class="text-end">
                            <div class="progress" style="width: 100px;">
                                <div class="progress-bar ${occ.importance ? 'bg-success' : 'bg-info'}" 
                                     role="progressbar" 
                                     style="width: ${occ.score}%"
                                     aria-valuenow="${occ.score}" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100">
                                    ${Math.round(occ.score)}%
                                </div>
                            </div>
                        </div>
                    </div>
                </button>
            `).join('');
        } else {
            occupationsHtml += '<div class="alert alert-info">No related occupations found.</div>';
        }
        occupationsHtml += '</div>';
        document.getElementById('relatedContent').innerHTML = occupationsHtml;
        
        // Update related skills tab
        let skillsHtml = '<div class="list-group">';
        if (data.related_skills && data.related_skills.length > 0) {
            skillsHtml += data.related_skills.map(skill => `
                <button class="list-group-item list-group-item-action" data-skill-id="${skill.code}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-1">${skill.title}</h5>
                            <p class="mb-1">${skill.description || ''}</p>
                        </div>
                        <div class="text-end">
                            <div class="progress" style="width: 100px;">
                                <div class="progress-bar bg-info" 
                                     role="progressbar" 
                                     style="width: ${skill.score}%"
                                     aria-valuenow="${skill.score}" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100">
                                    ${Math.round(skill.score)}%
                                </div>
                            </div>
                        </div>
                    </div>
                </button>
            `).join('');
        } else {
            skillsHtml += '<div class="alert alert-info">No related skills found.</div>';
        }
        skillsHtml += '</div>';
        document.getElementById('skillsContent').innerHTML = skillsHtml;
        
        // Add click handlers
        document.querySelectorAll('#relatedContent .list-group-item-action').forEach(item => {
            item.addEventListener('click', () => {
                const code = item.dataset.code;
                if (code) {
                    loadJobDetails(code);
                }
            });
        });
        
        document.querySelectorAll('#skillsContent .list-group-item-action').forEach(item => {
            item.addEventListener('click', () => {
                const skillId = item.dataset.skillId;
                if (skillId) {
                    loadSkillDetails(skillId);
                }
            });
        });
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
            searchInput.placeholder = this.value === 'skill' ? 'Search for a skill...' : 'Search for a job...';
            // Clear previous results when switching search type
            searchResultsList.innerHTML = '';
        });
    });
});
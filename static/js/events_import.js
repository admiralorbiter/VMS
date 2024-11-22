document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const eventSyncBtn = document.getElementById('eventSyncBtn');
    const participantSyncBtn = document.getElementById('participantSyncBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importTypeSelect = document.getElementById('importType');

    // Quick Sync button handler
    quickSyncBtn.addEventListener('click', function() {
        handleQuickSync();
    });

    // Event Sync button handler
    eventSyncBtn.addEventListener('click', function() {
        handleEventSync();
    });

    // Participant Sync button handler
    participantSyncBtn.addEventListener('click', function() {
        handleParticipantSync();
    });

    // File input change handler
    fileInput.addEventListener('change', function(e) {
        handleFileUpload(e.target.files[0]);
    });

    // Drag and drop handlers
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFileUpload(e.dataTransfer.files[0]);
    });

    function handleQuickSync() {
        showProgress();
        
        fetch('/events/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                quickSync: true,
                importType: importTypeSelect.value 
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResults(data);
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            showError(error);
        });
    }

    function handleEventSync() {
        showProgress();
        
        fetch('/sync/events', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Extract numbers from message string
                const messageMatch = data.message.match(/Successfully processed (\d+) events with (\d+) errors/);
                const successCount = messageMatch ? parseInt(messageMatch[1]) : 0;
                const errorCount = messageMatch ? parseInt(messageMatch[2]) : 0;

                showResults({
                    success: true,
                    successCount: successCount,
                    errorCount: errorCount,
                    warningCount: 0,
                    errors: data.errors || [],
                    message: data.message
                });
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            showError(error);
        });
    }

    function handleParticipantSync() {
        showProgress();
        
        fetch('/sync/participants', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Extract numbers from message string
                const messageMatch = data.message.match(/Successfully processed (\d+) participants with (\d+) errors/);
                const successCount = messageMatch ? parseInt(messageMatch[1]) : 0;
                const errorCount = messageMatch ? parseInt(messageMatch[2]) : 0;

                showResults({
                    success: true,
                    successCount: successCount,
                    errorCount: errorCount,
                    warningCount: 0,
                    errors: data.errors || [],
                    message: data.message
                });
                
                // Log for debugging
                console.log('Sync response:', data);
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            showError(error);
            console.error('Sync error:', error);
        });
    }

    function handleFileUpload(file) {
        if (!file || !file.name.endsWith('.csv')) {
            showError('Please select a valid CSV file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('importType', importTypeSelect.value);

        showProgress();

        fetch('/events/import', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResults(data);
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            showError(error);
        });
    }

    function showProgress() {
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
    }

    function showResults(data) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        
        // Update counts
        document.getElementById('successCount').textContent = data.successCount || 0;
        document.getElementById('errorCount').textContent = data.errorCount || 0;
        
        // Update error list
        const errorList = document.getElementById('errorList');
        errorList.innerHTML = '';
        
        // Add message if exists
        if (data.message) {
            const messageItem = document.createElement('div');
            messageItem.className = 'success-item';
            messageItem.textContent = data.message;
            errorList.appendChild(messageItem);
        }
        
        // Add errors if they exist
        if (data.errors && data.errors.length > 0) {
            data.errors.forEach(error => {
                const errorItem = document.createElement('div');
                errorItem.className = 'error-item';
                errorItem.textContent = error;
                errorList.appendChild(errorItem);
            });
        }
    }

    function showError(error) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        
        const errorList = document.getElementById('errorList');
        errorList.innerHTML = `<div class="error-item">${error}</div>`;
    }
});
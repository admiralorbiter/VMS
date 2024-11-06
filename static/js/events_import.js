document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');

    // Quick Sync button handler
    quickSyncBtn.addEventListener('click', function() {
        handleQuickSync();
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
});

function handleQuickSync() {
    showProgress();
    
    fetch('/events/import', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ quickSync: true })
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

function handleFileUpload(file) {
    if (!file || !file.name.endsWith('.csv')) {
        showError('Please select a valid CSV file');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

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
    
    document.getElementById('successCount').textContent = data.successCount;
    document.getElementById('errorCount').textContent = data.errorCount;
    
    const errorList = document.getElementById('errorList');
    errorList.innerHTML = '';
    
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
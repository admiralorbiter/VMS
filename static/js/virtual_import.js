document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('uploadContainer');
    const fileInput = document.getElementById('fileInput');
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importProgress = document.getElementById('importProgress');
    const processedCount = document.getElementById('processedCount');
    const successCount = document.getElementById('successCount');
    const warningCount = document.getElementById('warningCount');
    const errorCount = document.getElementById('errorCount');
    const errorList = document.getElementById('errorList');

    // Drag and drop handlers
    uploadContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadContainer.classList.add('drag-over');
    });

    uploadContainer.addEventListener('dragleave', () => {
        uploadContainer.classList.remove('drag-over');
    });

    uploadContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadContainer.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length) {
            handleFileUpload(files[0]);
        }
    });

    // File input handler
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Quick sync button handler
    quickSyncBtn.addEventListener('click', () => {
        const importType = document.querySelector('input[name="importType"]:checked').value;
        quickSyncBtn.disabled = true;
        showProgress();
        
        fetch('/virtual/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                quickSync: true,
                importType: importType
            })
        })
        .then(handleResponse)
        .catch(handleError)
        .finally(() => {
            quickSyncBtn.disabled = false;
        });
    });

    function handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            showError('Please upload a CSV file');
            return;
        }

        const importType = document.querySelector('input[name="importType"]:checked').value;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('importType', importType);

        showProgress();

        fetch('/virtual/import', {
            method: 'POST',
            body: formData
        })
        .then(handleResponse)
        .catch(handleError);
    }

    function handleResponse(response) {
        if (!response.ok) {
            throw new Error(response.statusText);
        }
        return response.json().then(data => {
            importProgress.style.width = '100%';
            setTimeout(() => {
                if (data.success) {
                    showResults(data);
                } else {
                    showError(data.error || 'Import failed');
                }
            }, 500);
        });
    }

    function handleError(error) {
        showError(error.message || 'An error occurred during import');
    }

    function showProgress() {
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
        importProgress.style.width = '0%';
        processedCount.textContent = '0';
    }

    function showResults(data) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        
        successCount.textContent = data.successCount || 0;
        warningCount.textContent = data.warningCount || 0;
        errorCount.textContent = data.errorCount || 0;
        
        errorList.innerHTML = '';
        if (data.errors && data.errors.length) {
            data.errors.forEach(error => {
                const errorItem = document.createElement('div');
                errorItem.className = 'error-item';
                errorItem.innerHTML = `<i class="fa-solid fa-times-circle"></i>${error}`;
                errorList.appendChild(errorItem);
            });
        }
    }

    function showError(message) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        errorList.innerHTML = `
            <div class="error-item">
                <i class="fa-solid fa-times-circle"></i>${message}
            </div>
        `;
    }
}); 
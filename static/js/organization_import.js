document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('uploadContainer');
    const fileInput = document.getElementById('fileInput');
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importProgress = document.getElementById('importProgress');
    const successCount = document.getElementById('successCount');
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
        
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith('.csv')) {
            handleFileUpload(file);
        } else {
            showError('Please upload a CSV file');
        }
    });

    // File input handler
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // Quick sync button handler
    quickSyncBtn.addEventListener('click', () => {
        quickSyncBtn.disabled = true;
        showProgress();
        importProgress.style.width = '50%';
        
        fetch('/organizations/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                quickSync: true
            })
        })
        .then(response => response.json())
        .then(data => {
            importProgress.style.width = '100%';
            setTimeout(() => {
                quickSyncBtn.disabled = false;
                if (data.error) {
                    showError(data.error);
                } else {
                    showResults(data);
                }
            }, 500);
        })
        .catch(error => {
            quickSyncBtn.disabled = false;
            showError('An error occurred during import');
        });
    });

    function handleFileUpload(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        showProgress();
        importProgress.style.width = '50%';
        
        fetch('/organizations/import', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            importProgress.style.width = '100%';
            setTimeout(() => {
                if (data.error) {
                    showError(data.error);
                } else {
                    showResults(data);
                }
            }, 500);
        })
        .catch(error => {
            showError('An error occurred during import');
        });
    }

    function showProgress() {
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
        importProgress.style.width = '0%';
        importProgress.style.transition = 'width 0.5s ease-in-out';
    }

    function showResults(data) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        
        successCount.textContent = data.successCount;
        errorCount.textContent = data.errorCount;
        
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
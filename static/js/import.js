document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importProgress = document.getElementById('importProgress');
    const processedCount = document.getElementById('processedCount');
    const totalCount = document.getElementById('totalCount');
    const successCount = document.getElementById('successCount');
    const errorCount = document.getElementById('errorCount');
    const errorList = document.getElementById('errorList');

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
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
        quickSyncBtn.disabled = true;
        showProgress();
        importProgress.style.width = '50%';
        
        fetch('/volunteers/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                quickSync: true
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(response.statusText);
            }
            return response.json();
        })
        .then(data => {
            importProgress.style.width = '100%';
            setTimeout(() => {
                if (data.success) {
                    showResults(data);
                } else {
                    showError(data.error || 'Import failed');
                }
            }, 500);
        })
        .catch(error => {
            showError(error.message || 'An error occurred during sync');
        })
        .finally(() => {
            quickSyncBtn.disabled = false;
        });
    });

    function handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            alert('Please upload a CSV file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showProgress();

        fetch('/volunteers/import', {
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
            showError('An error occurred during upload');
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

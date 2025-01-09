document.addEventListener('DOMContentLoaded', function() {
    let currentType = 'students';
    const typeButtons = document.querySelectorAll('.type-btn');
    const quickImportBtn = document.getElementById('quickImportBtn');
    const fileInput = document.getElementById('fileInput');
    const uploadContainer = document.getElementById('uploadContainer');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importProgress = document.getElementById('importProgress');

    // Type selection handling
    typeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Update active state
            typeButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Update current type
            currentType = this.dataset.type;
            
            // Update quick import button text
            quickImportBtn.innerHTML = `
                <i class="fas fa-file-import"></i>
                Quick Import ${currentType === 'students' ? 'Students.csv' : 'Teachers.csv'}
            `;
        });
    });

    // Quick import handling
    quickImportBtn.addEventListener('click', async function() {
        quickImportBtn.disabled = true;
        showProgress();
        
        try {
            const response = await fetch(`/attendance/quick-import/${currentType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });
            await handleResponse(response);
        } catch (error) {
            handleError(error);
        } finally {
            quickImportBtn.disabled = false;
        }
    });

    // File upload handling
    async function handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            showError('Please upload a CSV file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', currentType);

        showProgress();

        try {
            const response = await fetch('/attendance/upload', {
                method: 'POST',
                body: formData
            });
            await handleResponse(response);
        } catch (error) {
            handleError(error);
        }
    }

    // Response handler
    async function handleResponse(response) {
        if (!response.ok) {
            throw new Error(response.statusText);
        }
        const data = await response.json();
        
        // Update progress bar to 100%
        importProgress.style.width = '100%';
        
        setTimeout(() => {
            if (data.status === 'success') {
                showResults(data);
            } else {
                showError(data.message || 'Import failed');
            }
        }, 500);
    }

    // Error handler
    function handleError(error) {
        showError(error.message || 'An error occurred during import');
    }

    // Progress display
    function showProgress() {
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
        importProgress.style.width = '0%';
    }

    // Results display
    function showResults(data) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        
        document.getElementById('successCount').textContent = data.success || 0;
        document.getElementById('errorCount').textContent = data.errors?.length || 0;
        
        const errorList = document.getElementById('errorList');
        errorList.innerHTML = '';
        
        if (data.errors && data.errors.length > 0) {
            data.errors.forEach(error => {
                const errorItem = document.createElement('div');
                errorItem.className = 'error-item';
                errorItem.innerHTML = `<i class="fa-solid fa-times-circle"></i>${error}`;
                errorList.appendChild(errorItem);
            });
        }
    }

    // Error display
    function showError(message) {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        const errorList = document.getElementById('errorList');
        errorList.innerHTML = `
            <div class="error-item">
                <i class="fa-solid fa-times-circle"></i>${message}
            </div>
        `;
    }

    // Drag and drop handlers
    uploadContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadContainer.classList.add('dragover');
    });

    uploadContainer.addEventListener('dragleave', () => {
        uploadContainer.classList.remove('dragover');
    });

    uploadContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadContainer.classList.remove('dragover');
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
});

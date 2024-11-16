document.addEventListener('DOMContentLoaded', function() {
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const quickSyncEntryBtn = document.getElementById('quickSyncEntryBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importProgress = document.getElementById('importProgress');
    const processedCount = document.getElementById('processedCount');
    const successCount = document.getElementById('successCount');
    const errorCount = document.getElementById('errorCount');
    const fileInput = document.getElementById('fileInput');
    const uploadContainer = document.getElementById('uploadContainer');

    function updateProgress(processed, total) {
        const percentage = (processed / total) * 100;
        importProgress.style.width = `${percentage}%`;
        processedCount.textContent = processed;
    }

    async function performImport(type) {
        try {
            progressSection.style.display = 'block';
            resultsSection.style.display = 'none';
            
            const response = await fetch(`/tech_jobs/import/quick?type=${type}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                successCount.textContent = data.successCount;
                errorCount.textContent = data.errorCount;
                
                if (data.errors && data.errors.length > 0) {
                    console.error('Import errors:', data.errors);
                }
            } else {
                throw new Error(data.error || 'Import failed');
            }
            
        } catch (error) {
            console.error('Import error:', error);
            errorCount.textContent = '!';
        } finally {
            progressSection.style.display = 'none';
            resultsSection.style.display = 'block';
        }
    }

    quickSyncBtn.addEventListener('click', () => performImport('tech_jobs'));
    quickSyncEntryBtn.addEventListener('click', () => performImport('entry_level'));

    // Add drag and drop handlers
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
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });

    // Handle file input change
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFileUpload(file);
    });

    async function handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            alert('Please upload a CSV file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            progressSection.style.display = 'block';
            resultsSection.style.display = 'none';

            const response = await fetch('/tech_jobs/import', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                successCount.textContent = data.successCount;
                errorCount.textContent = data.errorCount;

                if (data.errors && data.errors.length > 0) {
                    console.error('Import errors:', data.errors);
                }
            } else {
                throw new Error(data.error || 'Import failed');
            }

        } catch (error) {
            console.error('Import error:', error);
            errorCount.textContent = '!';
        } finally {
            progressSection.style.display = 'none';
            resultsSection.style.display = 'block';
        }
    }
}); 
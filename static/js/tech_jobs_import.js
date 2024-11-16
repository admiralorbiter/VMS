document.addEventListener('DOMContentLoaded', function() {
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const quickSyncEntryBtn = document.getElementById('quickSyncEntryBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const importProgress = document.getElementById('importProgress');
    const processedCount = document.getElementById('processedCount');
    const successCount = document.getElementById('successCount');
    const errorCount = document.getElementById('errorCount');

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
}); 
document.addEventListener('DOMContentLoaded', function() {
    const quickSyncBtn = document.getElementById('quickSyncBtn');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const processedCount = document.getElementById('processedCount');
    const successCount = document.getElementById('successCount');
    const errorCount = document.getElementById('errorCount');
    const importProgress = document.getElementById('importProgress');

    quickSyncBtn.addEventListener('click', async function() {
        try {
            // Show progress section
            progressSection.style.display = 'block';
            resultsSection.style.display = 'none';
            quickSyncBtn.disabled = true;

            const response = await fetch('/tech_jobs/import/quick', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                // Update results
                successCount.textContent = data.successCount;
                errorCount.textContent = data.errorCount;
                
                // Hide progress, show results
                progressSection.style.display = 'none';
                resultsSection.style.display = 'block';
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            alert('Error during import: ' + error.message);
        } finally {
            quickSyncBtn.disabled = false;
        }
    });
}); 
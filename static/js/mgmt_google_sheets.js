let isEditMode = false;
let currentSheetId = null;

function openAddModal() {
    isEditMode = false;
    currentSheetId = null;
    document.getElementById('modalTitle').textContent = 'Add Google Sheet';
    document.getElementById('sheetForm').reset();
    document.getElementById('sheetModal').style.display = 'block';
}

function openEditModal(sheetId) {
    isEditMode = true;
    currentSheetId = sheetId;
    document.getElementById('modalTitle').textContent = 'Edit Google Sheet';
    fetch(`/google-sheets/${sheetId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const sheet = data.sheet;
                const academicYearSelect = document.getElementById('academicYear');
                // If the academic year is not in the options, add it
                if (![...academicYearSelect.options].some(opt => opt.value === sheet.academic_year)) {
                    const opt = document.createElement('option');
                    opt.value = sheet.academic_year;
                    opt.text = sheet.academic_year;
                    academicYearSelect.add(opt, academicYearSelect.options[1]); // after the placeholder
                }
                academicYearSelect.value = sheet.academic_year;
                document.getElementById('sheetIdInput').value = sheet.sheet_id || '';
                document.getElementById('sheetModal').style.display = 'block';
            } else {
                showToast('Error', 'Failed to load sheet data', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error', 'Failed to load sheet data', 'error');
        });
}

function closeModal() {
    document.getElementById('sheetModal').style.display = 'none';
    document.getElementById('sheetForm').reset();
}

function deleteSheet(sheetId, academicYear) {
    if (confirm(`Are you sure you want to delete the Google Sheet for ${academicYear}? This action cannot be undone.`)) {
        fetch(`/google-sheets/${sheetId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', data.message, 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showToast('Error', data.error || 'Failed to delete sheet', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error', 'Failed to delete sheet', 'error');
        });
    }
}

document.getElementById('sheetForm').addEventListener('submit', function(e) {
    e.preventDefault();

    // Validate form
    const academicYear = document.getElementById('academicYear').value;
    const sheetIdInput = document.getElementById('sheetIdInput').value;

    if (!academicYear || !sheetIdInput) {
        showToast('Error', 'Please fill in all required fields', 'error');
        return;
    }

    const formData = {
        academic_year: academicYear,
        sheet_id: sheetIdInput
    };

    const url = isEditMode ? `/google-sheets/${currentSheetId}` : '/google-sheets';
    const method = isEditMode ? 'PUT' : 'POST';

    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Saving...';
    submitBtn.disabled = true;

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast('Success', data.message, 'success');
            closeModal();
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast('Error', data.error || 'Failed to save sheet', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Failed to save sheet: ' + error.message, 'error');
    })
    .finally(() => {
        // Reset button state
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    });
});

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('sheetModal');
    if (event.target === modal) {
        closeModal();
    }
}

function showToast(title, message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        <div>
            <strong>${title}</strong>
            <div>${message}</div>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Remove toast after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function importVirtualForYear(academicYear, btn) {
    if (!confirm(`Import virtual events for ${academicYear}?`)) return;
    btn.disabled = true;
    const statusId = `importStatus-${academicYear.replace(/-/g, '')}`;
    const statusDiv = document.getElementById(statusId);
    statusDiv.textContent = 'Importing...';
    fetch('/virtual/import-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ academic_year: academicYear })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            statusDiv.textContent = `Import completed: ${data.successCount} successful, ${data.warningCount} warnings, ${data.errorCount} errors.`;
            if (data.errors && data.errors.length > 0) {
                statusDiv.innerHTML += `<br><small class='text-danger'>${data.errors.join('<br>')}</small>`;
            }
            showToast('Success', `Import completed for ${academicYear}`, 'success');
        } else {
            statusDiv.textContent = data.error || 'Import failed.';
            showToast('Error', data.error || 'Import failed', 'error');
        }
    })
    .catch(e => {
        statusDiv.textContent = 'Import failed: ' + e.message;
        showToast('Error', 'Import failed: ' + e.message, 'error');
    })
    .finally(() => { btn.disabled = false; });
}

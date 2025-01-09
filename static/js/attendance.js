function togglePurgeMenu() {
    document.getElementById("purgeMenu").classList.toggle("show");
}

// Close the dropdown if the user clicks outside of it
window.onclick = function(event) {
    if (!event.target.matches('.purge-btn')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        for (var i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}

function confirmPurge(type) {
    let message = '';
    switch(type) {
        case 'all':
            message = 'Are you sure you want to purge ALL student and teacher data? This action cannot be undone.';
            break;
        case 'students':
            message = 'Are you sure you want to purge all student data? This action cannot be undone.';
            break;
        case 'teachers':
            message = 'Are you sure you want to purge all teacher data? This action cannot be undone.';
            break;
    }

    if (confirm(message)) {
        fetch('/attendance/purge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: type })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification(data.message, 'success');
                location.reload();
            } else {
                showNotification('Error: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showNotification('Error: ' + error, 'error');
        });
    }
}

function switchTab(tabName) {
    const tables = document.querySelectorAll('.attendance-table-wrapper');
    const tabs = document.querySelectorAll('.tab-btn');
    
    tables.forEach(table => table.classList.add('hidden'));
    tabs.forEach(tab => tab.classList.remove('active'));
    
    document.getElementById(`${tabName}TableWrapper`).classList.remove('hidden');
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
}

function viewDetails(type, id) {
    // Implement view details functionality
    console.log(`Viewing ${type} details for ID: ${id}`);
}

function changePage(page, type) {
    const perPage = document.getElementById('perPageSelect').value;
    const currentUrl = new URL(window.location.href);
    
    currentUrl.searchParams.set('page', page);
    currentUrl.searchParams.set('per_page', perPage);
    
    window.location.href = currentUrl.toString();
}

function changePerPage() {
    const perPage = document.getElementById('perPageSelect').value;
    const currentUrl = new URL(window.location.href);
    
    currentUrl.searchParams.set('page', 1); // Reset to first page
    currentUrl.searchParams.set('per_page', perPage);
    
    window.location.href = currentUrl.toString();
}

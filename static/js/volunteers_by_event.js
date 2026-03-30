document.addEventListener('DOMContentLoaded', function() {
  // Handle date range options (mutually exclusive)
  const allPastDataCheckbox = document.getElementById('allPastData');
  const last2YearsCheckbox = document.getElementById('last2Years');
  const dateFromInput = document.querySelector('input[name="date_from"]');
  const dateToInput = document.querySelector('input[name="date_to"]');

  if (allPastDataCheckbox && last2YearsCheckbox && dateFromInput && dateToInput) {
    function updateDateFields() {
      const allPastChecked = allPastDataCheckbox.checked;
      const last2YearsChecked = last2YearsCheckbox.checked;

      // Disable date fields if either option is checked
      const shouldDisable = allPastChecked || last2YearsChecked;
      dateFromInput.disabled = shouldDisable;
      dateToInput.disabled = shouldDisable;

      // Clear date values when either option is checked
      if (shouldDisable) {
        dateFromInput.value = '';
        dateToInput.value = '';
      }
    }

    function handleAllPastDataChange() {
      if (allPastDataCheckbox.checked) {
        last2YearsCheckbox.checked = false;
      }
      updateDateFields();
    }

    function handleLast2YearsChange() {
      if (last2YearsCheckbox.checked) {
        allPastDataCheckbox.checked = false;
      }
      updateDateFields();
    }

    // Ensure mutual exclusivity on page load
    if (allPastDataCheckbox.checked && last2YearsCheckbox.checked) {
      // If both are checked, default to last_2_years
      allPastDataCheckbox.checked = false;
    }

    // Set initial state
    updateDateFields();

    // Add event listeners
    allPastDataCheckbox.addEventListener('change', handleAllPastDataChange);
    last2YearsCheckbox.addEventListener('change', handleLast2YearsChange);
  }

  // Handle search help toggle
  const toggleButton = document.getElementById('toggleSearchFields');
  const searchFieldsInfo = document.getElementById('searchFieldsInfo');

  if (toggleButton && searchFieldsInfo) {
    // Initially hide the section
    searchFieldsInfo.classList.add('d-none');

    toggleButton.addEventListener('click', function() {
      if (searchFieldsInfo.classList.contains('d-none')) {
        // Show the section
        searchFieldsInfo.classList.remove('d-none');
        // Add a small delay to ensure the element is visible before adding the show class
        setTimeout(() => {
          searchFieldsInfo.classList.add('show');
        }, 10);

        toggleButton.innerHTML = '<i class="fas fa-times-circle"></i> Hide Help';
        toggleButton.classList.remove('btn-outline-info');
        toggleButton.classList.add('btn-info');
      } else {
        // Hide the section
        searchFieldsInfo.classList.remove('show');
        // Wait for the transition to complete before hiding
        setTimeout(() => {
          searchFieldsInfo.classList.add('d-none');
        }, 300);

        toggleButton.innerHTML = '<i class="fas fa-info-circle"></i> Search Help';
        toggleButton.classList.remove('btn-info');
        toggleButton.classList.add('btn-outline-info');
      }
    });
  }

  // Event type pills behavior
  const btnSelectAll = document.getElementById('btnSelectAll');
  const btnClearAll = document.getElementById('btnClearAll');
  const btnDefaults = document.getElementById('btnDefaults');
  const container = document.getElementById('eventTypePills');

  function allInputs(){ return Array.from(container.querySelectorAll('input.btn-check')); }
  if (btnSelectAll) btnSelectAll.addEventListener('click', () => { allInputs().forEach(i => i.checked = true); });
  if (btnClearAll) btnClearAll.addEventListener('click', () => { allInputs().forEach(i => i.checked = false); });
  if (btnDefaults) btnDefaults.addEventListener('click', () => {
    // Select all event types as default
    allInputs().forEach(i => { i.checked = true; });
  });

  // Server-side sorting logic for table
  const table = document.querySelector('.table');
  if (!table) return;
  const headers = table.querySelectorAll('th.sortable');

  // Get current sort parameters from URL
  const urlParams = new URLSearchParams(window.location.search);
  const currentSort = urlParams.get('sort') || 'name';
  const currentOrder = urlParams.get('order') || 'asc';

  headers.forEach(h => {
    h.addEventListener('click', () => {
      const key = h.dataset.sort;
      let newOrder = 'asc';

      // If clicking the same column, toggle order
      if (currentSort === key) {
        newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
      }

      // Build new URL with sort parameters
      const newUrlParams = new URLSearchParams(window.location.search);
      newUrlParams.set('sort', key);
      newUrlParams.set('order', newOrder);
      newUrlParams.set('page', '1'); // Reset to first page when sorting

      // Navigate to new URL
      window.location.href = window.location.pathname + '?' + newUrlParams.toString();
    });
  });

  // Set visual indicators for current sort
  headers.forEach(h => {
    const key = h.dataset.sort;
    if (currentSort === key) {
      h.classList.add(currentOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    }
  });

});

document.addEventListener('DOMContentLoaded', function() {
    // Initialize add buttons with direct function assignments
    const addPhoneBtn = document.getElementById('add-phone-btn');
    const addAddressBtn = document.getElementById('add-address-btn');

    if (addPhoneBtn) {
        addPhoneBtn.addEventListener('click', function() {
            const container = document.getElementById('phones-container');
            const phoneGroup = document.createElement('div');
            phoneGroup.className = 'phone-group';
            phoneGroup.innerHTML = `
                <input type="tel" class="form-control phone-input" placeholder="Phone Number" required>
                <select class="form-select type-select">
                    <option value="personal">Personal</option>
                    <option value="professional">Professional</option>
                </select>
                <div class="form-check">
                    <input type="radio" name="primary_phone" class="form-check-input primary-check">
                    <label class="form-check-label">Primary</label>
                </div>
                <button type="button" class="btn btn-danger remove-btn">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            
            // Add click handler for the remove button
            const removeBtn = phoneGroup.querySelector('.remove-btn');
            removeBtn.addEventListener('click', function() {
                phoneGroup.remove();
            });
            
            container.appendChild(phoneGroup);
        });
    }

    if (addAddressBtn) {
        addAddressBtn.addEventListener('click', function() {
            const container = document.getElementById('addresses-container');
            const addressGroup = document.createElement('div');
            addressGroup.className = 'address-group';
            addressGroup.innerHTML = `
                <input type="text" class="form-control" placeholder="Address Line 1" required>
                <input type="text" class="form-control" placeholder="Address Line 2">
                <input type="text" class="form-control" placeholder="City" required>
                <input type="text" class="form-control" placeholder="State" required>
                <input type="text" class="form-control" placeholder="ZIP Code" required>
                <input type="text" class="form-control" placeholder="Country" value="USA">
                <div class="address-actions">
                    <select class="form-select type-select">
                        <option value="personal">Personal</option>
                        <option value="professional">Professional</option>
                    </select>
                    <div class="form-check">
                        <input type="radio" name="primary_address" class="form-check-input primary-check">
                        <label class="form-check-label">Primary</label>
                    </div>
                    <button type="button" class="btn btn-danger remove-btn">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            // Add click handler for the remove button
            const removeBtn = addressGroup.querySelector('.remove-btn');
            removeBtn.addEventListener('click', function() {
                addressGroup.remove();
            });
            
            container.appendChild(addressGroup);
        });
    }

    // Form submission handler
    const form = document.querySelector('.volunteer-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Collect phone data
            const phones = [];
            document.querySelectorAll('.phone-group').forEach(group => {
                phones.push({
                    number: group.querySelector('input[type="tel"]').value,
                    type: group.querySelector('select').value,
                    primary: group.querySelector('input[type="radio"]').checked
                });
            });
            
            // Collect address data
            const addresses = [];
            document.querySelectorAll('.address-group').forEach(group => {
                addresses.push({
                    address_line1: group.querySelector('input[placeholder="Address Line 1"]').value,
                    address_line2: group.querySelector('input[placeholder="Address Line 2"]').value,
                    city: group.querySelector('input[placeholder="City"]').value,
                    state: group.querySelector('input[placeholder="State"]').value,
                    zip_code: group.querySelector('input[placeholder="ZIP Code"]').value,
                    country: group.querySelector('input[placeholder="Country"]').value || 'USA',
                    type: group.querySelector('select').value,
                    primary: group.querySelector('input[type="radio"]').checked
                });
            });

            // Create FormData object
            const formData = new FormData(form);
            
            // Add the collected data
            formData.append('phones', JSON.stringify(phones));
            formData.append('addresses', JSON.stringify(addresses));

            // Submit the form using fetch
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Redirect to the volunteer's view page
                    window.location.href = data.redirect_url;
                } else {
                    // Handle errors
                    alert(data.error || 'An error occurred while saving changes.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while saving changes.');
            });
        });
    }
});

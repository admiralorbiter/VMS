/**
 * Edit Volunteer Form JavaScript Module
 * ====================================
 * 
 * This module provides functionality for the volunteer editing form,
 * including dynamic phone and address management, form data collection,
 * and AJAX form submission with error handling.
 * 
 * Key Features:
 * - Dynamic phone number management
 * - Dynamic address management
 * - Form data collection and validation
 * - AJAX form submission
 * - Error handling and user feedback
 * - Redirect on successful update
 * 
 * Dynamic Form Management:
 * - Add/remove phone number groups
 * - Add/remove address groups
 * - Primary contact selection
 * - Form validation
 * - Real-time form updates
 * 
 * Phone Management:
 * - Phone number input with validation
 * - Type selection (personal/professional)
 * - Primary phone designation
 * - Remove functionality
 * - Required field validation
 * 
 * Address Management:
 * - Multi-line address input
 * - Type selection (personal/professional)
 * - Primary address designation
 * - Remove functionality
 * - Required field validation
 * 
 * Form Submission:
 * - AJAX submission with FormData
 * - JSON serialization of complex data
 * - Server response handling
 * - Error display and user feedback
 * - Automatic redirect on success
 * 
 * Data Structure:
 * - Phone objects with number, type, and primary flag
 * - Address objects with all address fields and metadata
 * - FormData for multipart form submission
 * - JSON serialization for complex data
 * 
 * Dependencies:
 * - Bootstrap 5.3.3 CSS/JS for form styling
 * - FontAwesome icons for remove buttons
 * - Custom CSS for form group styling
 * 
 * CSS Classes:
 * - .phone-group/.address-group: Dynamic form groups
 * - .remove-btn: Remove button styling
 * - .form-control: Input field styling
 * - .form-select: Select dropdown styling
 * - .form-check: Checkbox/radio styling
 * 
 * Form Structure:
 * - #phones-container: Container for phone groups
 * - #addresses-container: Container for address groups
 * - .volunteer-form: Main form element
 * - .phone-input: Phone number input field
 * - .type-select: Type selection dropdown
 * - .primary-check: Primary selection radio button
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize add buttons with direct function assignments
    const addPhoneBtn = document.getElementById('add-phone-btn');
    const addAddressBtn = document.getElementById('add-address-btn');

    /**
     * Initialize phone number management
     * Sets up add button functionality for phone groups
     */
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

    /**
     * Initialize address management
     * Sets up add button functionality for address groups
     */
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

    /**
     * Initialize form submission handler
     * Collects form data and submits via AJAX
     */
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

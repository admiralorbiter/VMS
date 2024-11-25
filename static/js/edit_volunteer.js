document.addEventListener('DOMContentLoaded', function() {
    const emailContainer = document.querySelector('.email-container');
    const addEmailBtn = document.querySelector('.add-email-btn');
    
    function createEmailInput(emailData = {}) {
        const {
            id = Date.now(),
            email = '',
            type = 'personal',
            primary = false
        } = emailData;

        const emailGroup = document.createElement('div');
        emailGroup.className = 'email-group input-group';
        
        emailGroup.innerHTML = `
            <input type="email" 
                   class="form-control email-input" 
                   value="${email || ''}" 
                   data-email-id="${id}"
                   placeholder="Email Address"
                   style="min-width: 300px;">
            <div class="contact-type-toggle">
                <div class="btn-group" role="group">
                    <input type="radio" 
                           class="btn-check" 
                           name="email_type_${id}" 
                           id="personal_${id}" 
                           value="personal" 
                           ${type === 'personal' ? 'checked' : ''}>
                    <label class="btn" for="personal_${id}">Personal</label>
                    
                    <input type="radio" 
                           class="btn-check" 
                           name="email_type_${id}" 
                           id="professional_${id}" 
                           value="professional" 
                           ${type === 'professional' ? 'checked' : ''}>
                    <label class="btn" for="professional_${id}">Professional</label>
                </div>
            </div>
            <div class="primary-toggle">
                <input type="radio" 
                       name="primary_email" 
                       id="primary_${id}"
                       ${primary ? 'checked' : ''}>
                <label for="primary_${id}">Primary</label>
            </div>
            <button type="button" class="btn remove-email-btn">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;

        // Add event listeners
        const typeInputs = emailGroup.querySelectorAll('input[name^="email_type_"]');
        typeInputs.forEach(input => {
            input.addEventListener('change', function() {
                const labels = this.parentElement.querySelectorAll('label');
                labels.forEach(label => label.classList.remove('active'));
                if (this.checked) {
                    this.nextElementSibling.classList.add('active');
                }
            });
        });

        const primaryRadio = emailGroup.querySelector('input[name="primary_email"]');
        primaryRadio.addEventListener('change', function() {
            if (this.checked) {
                document.querySelectorAll('input[name="primary_email"]').forEach(radio => {
                    if (radio !== this) radio.checked = false;
                });
            }
        });

        const removeBtn = emailGroup.querySelector('.remove-email-btn');
        removeBtn.addEventListener('click', () => {
            if (emailContainer.querySelectorAll('.email-group').length > 1) {
                emailGroup.remove();
            } else {
                alert('At least one email address is required.');
            }
        });
        
        return emailGroup;
    }
    
    // Add new email button handler
    addEmailBtn.addEventListener('click', () => {
        emailContainer.appendChild(createEmailInput());
    });
    
    // Form submission handling
    const form = document.querySelector('.volunteer-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const emails = [];
        document.querySelectorAll('.email-group').forEach(group => {
            const emailInput = group.querySelector('.email-input');
            const email = emailInput.value;
            const emailId = emailInput.dataset.emailId;
            const type = group.querySelector('input[type="radio"][name^="email_type_"]:checked').value;
            const primary = group.querySelector('input[name="primary_email"]').checked;
            
            if (email) {
                emails.push({
                    id: emailId,
                    email,
                    type,
                    primary
                });
            }
        });
        
        const emailsInput = document.createElement('input');
        emailsInput.type = 'hidden';
        emailsInput.name = 'emails';
        emailsInput.value = JSON.stringify(emails);
        form.appendChild(emailsInput);
        
        form.submit();
    });
});

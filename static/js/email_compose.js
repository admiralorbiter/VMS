document.addEventListener('DOMContentLoaded', function () {
        const templateSelect = document.getElementById('template_id');
        const placeholderContainer = document.getElementById('placeholder-container');
        const subjectPreview = document.getElementById('subject-preview');
        const templateSubject = document.getElementById('template-subject');

        templateSelect.addEventListener('change', function () {
            const templateId = this.value;
            if (!templateId) {
                placeholderContainer.innerHTML = '<p class="no-placeholders">Select a template to see its placeholder fields.</p>';
                templateSubject.style.display = 'none';
                return;
            }

            placeholderContainer.innerHTML = '<p class="loading">Loading placeholders...</p>';

            fetch(`/management/email/templates/${templateId}/placeholders`)
                .then(response => response.json())
                .then(data => {
                    // Show subject preview
                    if (data.subject) {
                        subjectPreview.textContent = data.subject;
                        templateSubject.style.display = 'block';
                    } else {
                        templateSubject.style.display = 'none';
                    }

                    // Build placeholder fields
                    const required = data.required || [];
                    const optional = data.optional || [];

                    if (required.length === 0 && optional.length === 0) {
                        placeholderContainer.innerHTML = '<p class="no-placeholders">This template has no placeholders — it will be sent as-is.</p>';
                        return;
                    }

                    let html = '<div class="placeholder-fields">';

                    required.forEach(function (name) {
                        html += `
                        <div class="placeholder-field">
                            <label for="placeholder_${name}">
                                ${name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                <span class="badge badge-required">Required</span>
                            </label>
                            <input type="text" id="placeholder_${name}" name="placeholder_${name}"
                                   required placeholder="Enter ${name.replace(/_/g, ' ')}">
                        </div>
                    `;
                    });

                    optional.forEach(function (name) {
                        html += `
                        <div class="placeholder-field">
                            <label for="placeholder_${name}">
                                ${name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                <span class="badge badge-optional">Optional</span>
                            </label>
                            <input type="text" id="placeholder_${name}" name="placeholder_${name}"
                                   placeholder="Enter ${name.replace(/_/g, ' ')} (optional)">
                        </div>
                    `;
                    });

                    html += '</div>';
                    placeholderContainer.innerHTML = html;
                })
                .catch(function (error) {
                    placeholderContainer.innerHTML = '<p style="color: #dc2626;">Error loading placeholders. Please try again.</p>';
                });
        });
    });

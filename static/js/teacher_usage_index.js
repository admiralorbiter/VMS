let currentFlagTeacherId = null;

    function toggleSchoolDetail(schoolId) {
        const detail = document.getElementById('school-detail-' + schoolId);
        if (detail) {
            if (detail.style.display === 'none') {
                document.querySelectorAll('.school-detail').forEach(d => d.style.display = 'none');
                detail.style.display = 'block';
                detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                detail.style.display = 'none';
            }
        }
    }

    function openFlagModal(teacherId, teacherName) {
        currentFlagTeacherId = teacherId;
        document.getElementById('flagTeacherName').textContent = teacherName;
        document.getElementById('flagType').value = '';
        document.getElementById('flagDetailsSection').style.display = 'none';
        document.getElementById('flagDetailsInput').value = '';
        document.getElementById('flagDetailsTextarea').value = '';
        document.getElementById('flagModalBackdrop').classList.add('show');

        // Load existing flags
        loadExistingFlags(teacherId);
    }

    function closeFlagModal() {
        document.getElementById('flagModalBackdrop').classList.remove('show');
        currentFlagTeacherId = null;
    }

    function toggleFlagDetails() {
        const type = document.getElementById('flagType').value;
        const section = document.getElementById('flagDetailsSection');
        const input = document.getElementById('flagDetailsInput');
        const textarea = document.getElementById('flagDetailsTextarea');
        const label = document.getElementById('flagDetailsLabel');

        if (type === 'missing_session') {
            section.style.display = 'block';
            input.style.display = 'block';
            textarea.style.display = 'none';
            label.textContent = 'Session Name';
            input.placeholder = 'e.g. Career Day – March 2026';
        } else if (type === 'other') {
            section.style.display = 'block';
            input.style.display = 'none';
            textarea.style.display = 'block';
            label.textContent = 'Describe the Issue';
        } else {
            section.style.display = 'none';
        }
    }

    async function submitFlag() {
        const flagType = document.getElementById('flagType').value;
        if (!flagType) {
            alert('Please select an issue type.');
            return;
        }

        let details = '';
        if (flagType === 'missing_session') {
            details = document.getElementById('flagDetailsInput').value.trim();
        } else if (flagType === 'other') {
            details = document.getElementById('flagDetailsTextarea').value.trim();
        }

        try {
            const resp = await fetch(`/district/teacher-usage/flags/${currentFlagTeacherId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ flag_type: flagType, details: details })
            });

            if (resp.ok) {
                // Update the flag icon to red
                const btns = document.querySelectorAll(`.flag-btn`);
                btns.forEach(btn => {
                    const onclick = btn.getAttribute('onclick');
                    if (onclick && onclick.includes(`(${currentFlagTeacherId},`)) {
                        btn.classList.remove('unflagged');
                        btn.classList.add('flagged');
                        // Add or update badge
                        let badge = btn.querySelector('.flag-badge');
                        if (badge) {
                            badge.textContent = parseInt(badge.textContent) + 1;
                        } else {
                            badge = document.createElement('span');
                            badge.className = 'flag-badge';
                            badge.textContent = '1';
                            btn.appendChild(badge);
                        }
                    }
                });
                closeFlagModal();
            } else {
                const data = await resp.json();
                alert(data.error || 'Failed to create flag.');
            }
        } catch (e) {
            console.error(e);
            alert('Network error.');
        }
    }

    async function loadExistingFlags(teacherId) {
        const container = document.getElementById('existingFlagsContainer');
        container.style.display = 'none';
        container.innerHTML = '';

        try {
            const resp = await fetch(`/district/teacher-usage/flags/${teacherId}`);
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.flags.length === 0) return;

            let html = '<div class="existing-flags"><h4><i class="fas fa-exclamation-triangle"></i> Open Flags</h4>';
            data.flags.forEach(flag => {
                html += `<div class="existing-flag-item">
                    <span><strong>${flag.flag_type_display}</strong>${flag.details ? ': ' + flag.details : ''}</span>
                    <button class="resolve-flag-btn" onclick="resolveFlag(${flag.id}, this)">✓ Resolve</button>
                </div>`;
            });
            html += '</div>';
            container.innerHTML = html;
            container.style.display = 'block';
        } catch (e) {
            console.error(e);
        }
    }

    async function resolveFlag(flagId, btn) {
        try {
            const resp = await fetch(`/district/teacher-usage/flags/${flagId}/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: '' })
            });
            if (resp.ok) {
                btn.closest('.existing-flag-item').remove();
                // If no more flags, hide the container
                const container = document.getElementById('existingFlagsContainer');
                if (!container.querySelector('.existing-flag-item')) {
                    container.style.display = 'none';
                }
            }
        } catch (e) {
            console.error(e);
        }
    }

function toggleSection(sectionId) {
        const section = document.getElementById(sectionId);
        section.classList.toggle('collapsed');
    }

    function toggleTeacher(teacherId) {
        const row = document.getElementById(teacherId);
        row.classList.toggle('collapsed');
    }

    // ── Revise Modal ─────────────────────────────────────────────────
    function openReviseModal(tpId, eventId, sessionTitle, sessionDate, teacherName) {
        document.getElementById('reviseTeacherProgressId').value = tpId;
        document.getElementById('reviseEventId').value = eventId;
        document.getElementById('reviseTeacherName').textContent = teacherName;
        document.getElementById('reviseSessionTitle').textContent = sessionTitle;
        document.getElementById('reviseSessionDate').textContent = sessionDate;
        document.getElementById('reviseReason').value = '';
        updateSubmitButton();
        document.getElementById('reviseModal').classList.add('active');
    }

    function closeModal() {
        document.getElementById('reviseModal').classList.remove('active');
    }

    function updateSubmitButton() {
        const reason = document.getElementById('reviseReason').value.trim();
        document.getElementById('reviseSubmitBtn').disabled = !reason;
    }

    document.addEventListener('DOMContentLoaded', function () {
        const reasonField = document.getElementById('reviseReason');
        if (reasonField) {
            reasonField.addEventListener('input', updateSubmitButton);
        }
    });

    // ── Submit Override ──────────────────────────────────────────────
    async function submitRevise() {
        const tpId = document.getElementById('reviseTeacherProgressId').value;
        const eventId = document.getElementById('reviseEventId').value;
        const reason = document.getElementById('reviseReason').value.trim();
        if (!tpId || !eventId || !reason) return;

        const btn = document.getElementById('reviseSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            const resp = await fetch('/district/teacher-usage/overrides/' + tpId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'add',
                    event_id: parseInt(eventId),
                    reason: reason,
                }),
            });
            const data = await resp.json();
            if (resp.ok) {
                showToast('No-show revised — teacher marked as attended.', 'success');
                closeModal();
                // Update the session row in-place to show "Revised" badge
                const row = document.getElementById('session-' + tpId + '-' + eventId);
                if (row) {
                    row.classList.add('overridden');
                    // Replace the button with the overridden badge
                    const btn = row.querySelector('.btn-revise');
                    if (btn) {
                        btn.outerHTML = '<span class="overridden-badge"><i class="fas fa-check-circle"></i> Revised</span>';
                    }
                }
            } else {
                showToast(data.error || 'Failed to revise no-show.', 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Mark as Attended';
            }
        } catch (err) {
            showToast('Network error. Please try again.', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Mark as Attended';
        }
    }

    // ── Toast ────────────────────────────────────────────────────────
    function showToast(message, type) {
        const toast = document.getElementById('overrideToast');
        toast.textContent = message;
        toast.className = 'override-toast ' + type;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }

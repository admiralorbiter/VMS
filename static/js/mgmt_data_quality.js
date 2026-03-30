async function dismissFlag(flagId) {
        const notes = prompt('Resolution notes (optional):');
        if (notes === null) return;

        try {
            const resp = await fetch(`/admin/data-quality/${flagId}/dismiss`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: notes, status: 'dismissed' })
            });
            if (resp.ok) {
                const card = document.getElementById('flag-card-' + flagId);
                if (card) {
                    card.classList.add('dismissed');
                    const btn = card.querySelector('.dismiss-btn');
                    if (btn) btn.remove();
                    const info = card.querySelector('.flag-info');
                    const resolved = document.createElement('div');
                    resolved.className = 'flag-details';
                    resolved.style.color = '#28a745';
                    resolved.innerHTML = '<i class="fas fa-check-circle"></i> Dismissed just now' +
                        (notes ? ' — ' + notes : '');
                    info.appendChild(resolved);

                    // Update status badge
                    const badge = card.querySelector('.badge');
                    if (badge) {
                        badge.className = 'badge bg-secondary';
                        badge.textContent = 'dismissed';
                    }
                }
                const openStat = document.getElementById('stat-open');
                if (openStat) {
                    openStat.textContent = Math.max(0, parseInt(openStat.textContent) - 1);
                }
            } else {
                alert('Failed to dismiss flag.');
            }
        } catch (e) {
            console.error(e);
            alert('Network error.');
        }
    }

    async function bulkDismiss(issueType) {
        const count = document.querySelectorAll(`.flag-card.type-${issueType}:not(.dismissed)`).length;
        if (!confirm(`Dismiss all open "${issueType}" flags? This will affect all matching flags, not just the ones on this page.`)) return;

        const notes = prompt('Resolution notes for bulk dismiss (optional):');
        if (notes === null) return;

        try {
            const resp = await fetch('/admin/data-quality/bulk-dismiss', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ issue_type: issueType, notes: notes, status: 'dismissed' })
            });
            if (resp.ok) {
                const data = await resp.json();
                alert(`Dismissed ${data.count} flags. Page will reload.`);
                window.location.reload();
            } else {
                alert('Failed to bulk dismiss.');
            }
        } catch (e) {
            console.error(e);
            alert('Network error.');
        }
    }

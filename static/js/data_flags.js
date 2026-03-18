async function resolveFlag(flagId) {
        const notes = prompt('Resolution notes (optional):');
        if (notes === null) return; // cancelled

        try {
            const resp = await fetch(`/district/teacher-usage/flags/${flagId}/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: notes })
            });
            if (resp.ok) {
                const card = document.getElementById('flag-card-' + flagId);
                if (card) {
                    card.style.opacity = '0.5';
                    card.querySelector('.resolve-btn').remove();
                    const info = card.querySelector('.flag-info');
                    const resolved = document.createElement('div');
                    resolved.className = 'flag-details';
                    resolved.style.color = '#28a745';
                    resolved.innerHTML = '<i class="fas fa-check-circle"></i> Resolved just now' +
                        (notes ? ' — ' + notes : '');
                    info.appendChild(resolved);
                }
                // Update stats
                const openStat = document.querySelector('.stat-pill.open .stat-num');
                if (openStat) {
                    openStat.textContent = Math.max(0, parseInt(openStat.textContent) - 1);
                }
            } else {
                alert('Failed to resolve flag.');
            }
        } catch (e) {
            console.error(e);
            alert('Network error.');
        }
    }

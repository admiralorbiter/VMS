(function() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const slotA = document.getElementById('slotA');
    const slotB = document.getElementById('slotB');
    const swapBtn = document.getElementById('swapBtn');
    const compareSection = document.getElementById('compareSection');
    const compareDetails = document.getElementById('compareDetails');
    const mergeSection = document.getElementById('mergeSection');
    const mergeBtn = document.getElementById('mergeBtn');

    let debounceTimer;
    let teacherA = null, teacherB = null;

    // Load flagged candidates on page load
    fetch('/teachers/merge/candidates')
        .then(r => r.json())
        .then(candidates => {
            const list = document.getElementById('candidatesList');
            if (!candidates.length) {
                list.innerHTML = '<div class="candidates-empty"><i class="fas fa-check-circle me-2"></i>No flagged duplicates found!</div>';
                return;
            }
            list.innerHTML = candidates.map((c, i) => {
                const conf = c.shared_events >= 10 ? 'high' : c.shared_events >= 4 ? 'med' : 'low';
                return `
                <div class="col-md-4">
                    <div class="candidate-card confidence-${conf}" data-pair='${JSON.stringify(c).replace(/'/g, "&#39;")}'>
                        <div class="pair-names">
                            ${c.teacher_a.first_name} ${c.teacher_a.last_name}
                            <i class="fas fa-arrows-alt-h text-muted mx-1" style="font-size:0.7rem;"></i>
                            ${c.teacher_b.first_name} ${c.teacher_b.last_name}
                        </div>
                        <div class="pair-meta">
                            <span class="shared-badge">${c.shared_events} shared (${c.overlap_pct}%)</span>
                            &nbsp; ${c.teacher_a.school} / ${c.teacher_b.school}
                        </div>
                    </div>
                </div>`;
            }).join('');

            // Click to load pair
            list.addEventListener('click', function(e) {
                const card = e.target.closest('.candidate-card');
                if (!card) return;
                const pair = JSON.parse(card.dataset.pair);
                clearSlot('A'); clearSlot('B');
                setSlot('A', {...pair.teacher_a, email: '--', import_source: '--'});
                setSlot('B', {...pair.teacher_b, email: '--', import_source: '--'});
                // Scroll down to compare
                document.getElementById('compareSection').scrollIntoView({behavior: 'smooth', block: 'start'});
            });
        })
        .catch(() => {
            document.getElementById('candidatesList').innerHTML = '<div class="text-danger">Error loading candidates</div>';
        });

    // Search
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const q = this.value.trim();
        if (q.length < 2) { searchResults.style.display = 'none'; return; }
        debounceTimer = setTimeout(() => {
            fetch(`/teachers/merge/search?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.length) { searchResults.innerHTML = '<div class="search-result-item"><em>No results</em></div>'; }
                    else {
                        searchResults.innerHTML = data.map(t => `
                            <div class="search-result-item" data-id="${t.id}" data-teacher='${JSON.stringify(t).replace(/'/g, "&#39;")}'>
                                <div class="name">${t.first_name} ${t.last_name} <small class="text-muted">#${t.id}</small></div>
                                <div class="meta">School: ${t.school} | Events: ${t.event_count} | TP: ${t.tp_count}</div>
                            </div>
                        `).join('');
                    }
                    searchResults.style.display = 'block';
                });
        }, 250);
    });

    // Click result
    searchResults.addEventListener('click', function(e) {
        const item = e.target.closest('.search-result-item');
        if (!item || !item.dataset.teacher) return;
        const t = JSON.parse(item.dataset.teacher);
        if (!teacherA) { setSlot('A', t); }
        else if (!teacherB && t.id !== teacherA.id) { setSlot('B', t); }
        searchResults.style.display = 'none';
        searchInput.value = '';
    });

    // Close dropdown on click outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-box')) searchResults.style.display = 'none';
    });

    function setSlot(slot, t) {
        const el = slot === 'A' ? slotA : slotB;
        if (slot === 'A') teacherA = t; else teacherB = t;
        el.dataset.teacherId = t.id;
        const label = slot === 'A' ? 'keep' : 'merge-away';
        const labelText = slot === 'A' ? '✓ KEEP this record' : '⤏ MERGE into left';
        el.className = `slot-card filled ${label}`;
        el.innerHTML = `
            <div class="slot-label ${label}">${labelText}</div>
            <div class="teacher-name">${t.first_name} ${t.last_name} <small class="text-muted">#${t.id}</small></div>
            <div class="teacher-detail">School: ${t.school}</div>
            <div class="teacher-detail">Email: ${t.email} | Source: ${t.import_source}</div>
            <div class="teacher-detail">Events: ${t.event_count} | TP links: ${t.tp_count}</div>
            <button class="clear-btn" onclick="clearSlot('${slot}')"><i class="fas fa-times"></i> Remove</button>
        `;
        swapBtn.disabled = !(teacherA && teacherB);
        if (teacherA && teacherB) loadComparison();
    }

    window.clearSlot = function(slot) {
        const el = slot === 'A' ? slotA : slotB;
        if (slot === 'A') teacherA = null; else teacherB = null;
        el.className = 'slot-card';
        el.dataset.teacherId = '';
        el.innerHTML = `<span class="slot-placeholder"><i class="fas fa-user-plus me-2"></i>Select ${slot === 'A' ? 'first' : 'second'} teacher</span>`;
        compareSection.style.display = 'none';
        mergeSection.style.display = 'none';
        swapBtn.disabled = true;
    };

    // Swap
    swapBtn.addEventListener('click', function() {
        if (!teacherA || !teacherB) return;
        const tmp = teacherA;
        setSlot('A', teacherB);
        setSlot('B', tmp);
    });

    // Compare
    function loadComparison() {
        fetch(`/teachers/merge/compare?id_a=${teacherA.id}&id_b=${teacherB.id}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) { compareDetails.innerHTML = `<p class="text-danger">${data.error}</p>`; return; }

                let html = `<div class="row">
                    <div class="col-md-6"><strong>Shared events:</strong> <span class="shared-badge">${data.shared_events}</span></div>
                </div>`;

                if (data.shared_event_details.length) {
                    html += `<table class="table table-sm mt-2"><thead><tr><th>Event</th><th>Left Status</th><th>Right Status</th><th>After Merge</th></tr></thead><tbody>`;
                    const priority = {attended: 3, no_show: 2, registered: 1};
                    data.shared_event_details.forEach(e => {
                        const winner = (priority[e.status_a] || 0) >= (priority[e.status_b] || 0) ? e.status_a : e.status_b;
                        const upgraded = winner !== e.status_a;
                        html += `<tr>
                            <td>#${e.event_id}</td>
                            <td><span class="status-badge ${e.status_a}">${e.status_a}</span></td>
                            <td><span class="status-badge ${e.status_b}">${e.status_b}</span></td>
                            <td><span class="status-badge ${winner}">${winner}</span>${upgraded ? ' <small class="text-success">↑ upgraded</small>' : ''}</td>
                        </tr>`;
                    });
                    html += `</tbody></table>`;
                }

                const onlyA = data.teacher_a.event_count - data.shared_events;
                const onlyB = data.teacher_b.event_count - data.shared_events;
                html += `<div class="mt-2 text-muted">
                    <small>Events only on left: ${onlyA} | Only on right (will move): ${onlyB} | Shared (will dedup): ${data.shared_events}</small>
                </div>`;

                compareDetails.innerHTML = html;
                compareSection.style.display = 'block';
                mergeSection.style.display = 'block';
                mergeBtn.disabled = false;
            });
    }

    // Merge
    mergeBtn.addEventListener('click', function() {
        if (!teacherA || !teacherB) return;
        const keepName = `${teacherA.first_name} ${teacherA.last_name}`;
        const mergeName = `${teacherB.first_name} ${teacherB.last_name}`;
        if (!confirm(`Merge "${mergeName}" (#${teacherB.id}) INTO "${keepName}" (#${teacherA.id})?\n\nThis cannot be easily undone.`)) return;

        mergeBtn.disabled = true;
        mergeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Merging...';

        fetch('/teachers/merge/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({keep_id: teacherA.id, merge_id: teacherB.id})
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const toast = document.createElement('div');
                toast.className = 'success-toast';
                toast.innerHTML = `<i class="fas fa-check-circle me-2"></i>${data.message}`;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 5000);

                clearSlot('B');
                // Refresh slot A with updated data
                fetch(`/teachers/merge/search?q=${encodeURIComponent(keepName)}`)
                    .then(r => r.json())
                    .then(results => {
                        const updated = results.find(t => t.id === teacherA.id);
                        if (updated) setSlot('A', updated);
                    });
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
                mergeBtn.disabled = false;
                mergeBtn.innerHTML = '<i class="fas fa-code-branch me-2"></i>Merge Right Into Left';
            }
        })
        .catch(err => {
            alert('Error: ' + err.message);
            mergeBtn.disabled = false;
            mergeBtn.innerHTML = '<i class="fas fa-code-branch me-2"></i>Merge Right Into Left';
        });
    });
})();

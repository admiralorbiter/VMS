// Load health metrics on page load
    document.addEventListener('DOMContentLoaded', loadHealthMetrics);

    async function loadHealthMetrics() {
        const container = document.getElementById('metrics-content');
        try {
            const response = await fetch('/admin/salesforce/health-metrics');
            const data = await response.json();

            if (!data.success) {
                container.innerHTML = '<div class="text-danger">Failed to load metrics</div>';
                return;
            }

            // Build metrics grid HTML
            let html = '<div class="health-metrics-grid">';

            // 7-Day Trend Chart
            html += '<div class="metric-card">';
            html += '<h4><i class="fas fa-chart-bar"></i> 7-Day Success Rate</h4>';
            html += '<div class="trend-chart">';
            for (const day of data.daily_trend) {
                const height = Math.max(10, day.success_rate);
                const statusClass = day.failed_runs > 0 ? 'partial' : 'success';
                html += `<div class="trend-bar" title="${day.date}: ${day.total_runs} runs, ${day.success_rate}% success">`;
                html += `<div class="trend-bar-fill ${statusClass}" style="height: ${height}%"></div>`;
                html += `<span class="trend-bar-label">${day.day_name}</span>`;
                html += '</div>';
            }
            html += '</div></div>';

            // Stale Sync Warnings
            html += '<div class="metric-card">';
            html += '<h4><i class="fas fa-exclamation-triangle"></i> Stale Sync Warnings</h4>';
            html += '<div class="stale-warnings">';
            if (data.stale_syncs.length === 0) {
                html += '<div class="no-warnings"><i class="fas fa-check-circle"></i> All syncs up to date</div>';
            } else {
                for (const stale of data.stale_syncs) {
                    const itemClass = stale.hours_since === null ? 'never-synced' : '';
                    const message = stale.hours_since === null
                        ? `${stale.sync_type} has never been synced`
                        : `${stale.sync_type} - ${Math.round(stale.hours_since)}h since last sync`;
                    html += `<div class="stale-warning-item ${itemClass}">`;
                    html += `<i class="fas fa-${stale.hours_since === null ? 'times-circle' : 'clock'}"></i>`;
                    html += `<span>${message}</span>`;
                    html += '</div>';
                }
            }
            html += '</div></div>';

            // Duration Table
            html += '<div class="metric-card">';
            html += '<h4><i class="fas fa-stopwatch"></i> Avg Duration by Type</h4>';
            html += '<table class="duration-table"><thead><tr><th>Type</th><th>Avg</th><th>Runs</th></tr></thead><tbody>';
            for (const [type, m] of Object.entries(data.metrics)) {
                if (m.total_runs > 0) {
                    const duration = m.avg_duration_seconds !== null
                        ? (m.avg_duration_seconds < 60 ? `${m.avg_duration_seconds}s` : `${Math.round(m.avg_duration_seconds / 60)}m`)
                        : '-';
                    html += `<tr><td class="sync-type">${type}</td><td class="duration">${duration}</td><td>${m.total_runs}</td></tr>`;
                }
            }
            html += '</tbody></table></div>';

            html += '</div>';
            container.innerHTML = html;
        } catch (error) {
            console.error('Error loading health metrics:', error);
            container.innerHTML = '<div class="text-danger">Failed to load metrics</div>';
        }
    }

    // Import URL mapping
    const IMPORT_URLS = {
        'organizations': '/organizations/import-from-salesforce',
        'volunteers': '/volunteers/import-from-salesforce',
        'affiliations': '/organizations/import-affiliations-from-salesforce',
        'events': '/events/import-from-salesforce',
        'history': '/history/import-from-salesforce',
        'schools': '/management/import-schools',
        'classes': '/management/import-classes',
        'teachers': '/teachers/import-from-salesforce',
        'students': '/students/import-from-salesforce',
        'student_participations': '/events/sync-student-participants',
        'unaffiliated_events': '/pathway-events/sync-unaffiliated-events'
    };

    // Run an import
    async function runImport(importType) {
        const card = document.querySelector(`[data-import-type="${importType}"]`);
        const btn = card.querySelector('.import-btn');
        const status = card.querySelector('.import-status');
        const progress = card.querySelector('.import-progress');
        const progressBar = progress?.querySelector('.progress-bar');
        const deltaCheckbox = card.querySelector('.delta-checkbox');
        const isDelta = deltaCheckbox?.checked ?? true;

        // Confirmation
        if (!confirm(`Are you sure you want to import ${importType} from Salesforce?`)) {
            return;
        }

        btn.disabled = true;
        if (progress) progress.classList.add('active');
        if (progressBar) progressBar.style.width = '10%';
        status.textContent = `Starting ${importType} import...`;
        status.className = 'import-status';

        try {
            const url = IMPORT_URLS[importType];
            const params = isDelta ? '?delta=true' : '';

            // For chunked imports (students), loop until complete
            const chunkedImports = ['students'];
            if (chunkedImports.includes(importType)) {
                let totalProcessed = 0;
                let totalErrors = 0;
                let nextId = null;
                let chunkNumber = 0;
                let isComplete = false;

                while (!isComplete) {
                    chunkNumber++;
                    status.textContent = `Processing ${importType} chunk ${chunkNumber}... (${totalProcessed} so far)`;

                    // Use same params (including delta) for all chunks
                    // Backend only updates watermark on final chunk
                    const body = nextId ? { last_id: nextId } : {};
                    const response = await fetch(url + params, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });

                    const data = await response.json();

                    if (!data.success) {
                        throw new Error(data.message || data.error || 'Import failed');
                    }

                    totalProcessed += data.processed_count || 0;
                    totalErrors += data.error_count || 0;
                    nextId = data.next_id;
                    isComplete = data.is_complete || !nextId;

                    // Update progress bar based on chunks
                    const progressPercent = Math.min(90, 10 + (chunkNumber * 20));
                    if (progressBar) progressBar.style.width = `${progressPercent}%`;
                }

                if (progressBar) progressBar.style.width = '100%';
                status.textContent = `Imported ${totalProcessed} ${importType} (${totalErrors} errors)`;
                status.classList.add('success');
                showToast('Success', `Imported ${totalProcessed} ${importType}`, 'success');
            } else {
                // Standard single-call import for other types
                const response = await fetch(url + params, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (progressBar) progressBar.style.width = '90%';

                const data = await response.json();

                if (progressBar) progressBar.style.width = '100%';

                if (data.success) {
                    status.textContent = data.message || `${importType} import completed successfully`;
                    status.classList.add('success');
                    showToast('Success', data.message || `${importType} import completed`, 'success');
                } else {
                    throw new Error(data.message || data.error || 'Import failed');
                }
            }
        } catch (error) {
            status.textContent = `Error: ${error.message}`;
            status.classList.add('error');
            showToast('Error', `Failed to import ${importType}: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            // Keep progress bar visible for a moment
            setTimeout(() => {
                if (progress) progress.classList.remove('active');
                if (progressBar) progressBar.style.width = '0%';
            }, 2000);
        }
    }

    // Show toast notification
    function showToast(title, message, type = 'success') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <div>
                <strong>${title}</strong>
                <div style="font-size: 0.85rem;">${message}</div>
            </div>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // History modal
    async function openHistoryModal() {
        document.getElementById('historyModal').classList.add('show');
        document.getElementById('historyTableBody').innerHTML = '<tr><td colspan="7" class="text-center">Loading...</td></tr>';

        try {
            const response = await fetch('/admin/salesforce/sync-history');
            const data = await response.json();

            if (data.success && data.logs.length > 0) {
                let rows = '';
                for (const log of data.logs) {
                    // Main row
                    rows += `
                    <tr>
                        <td><strong>${log.sync_type}</strong></td>
                        <td>${log.started_at ? new Date(log.started_at).toLocaleString() : '-'}</td>
                        <td>${log.completed_at ? new Date(log.completed_at).toLocaleString() : '-'}</td>
                        <td><span class="sync-status ${log.status}">${log.status}</span></td>
                        <td>${log.records_processed || 0}</td>
                        <td>${log.records_failed || 0}</td>
                        <td>${log.is_delta_sync ? '✓' : '-'}</td>
                    </tr>`;

                    // Expandable error detail row — only shown when there are failures and stored detail
                    if (log.records_failed > 0 && log.error_message) {
                        let errors = [];
                        try { errors = JSON.parse(log.error_message); } catch(e) { errors = []; }

                        if (errors.length > 0) {
                            const errorRows = errors.map(e => {
                                const sfId   = e.record_id   || '—';
                                const name   = e.record_name || '—';
                                const msg    = e.message     || (typeof e === 'string' ? e : JSON.stringify(e));
                                return `<tr>
                                    <td class="font-monospace small" style="white-space:nowrap">${sfId}</td>
                                    <td class="small">${name}</td>
                                    <td class="small text-danger">${msg}</td>
                                </tr>`;
                            }).join('');

                            rows += `
                            <tr class="table-warning">
                                <td colspan="7" style="padding: 0 1rem 0.75rem 2rem;">
                                    <details>
                                        <summary style="cursor:pointer; font-size:0.82rem; color:#6c757d; padding:0.4rem 0;">
                                            ▶ ${errors.length} failed record${errors.length !== 1 ? 's' : ''} — click to expand
                                        </summary>
                                        <div style="margin-top:0.5rem; overflow-x:auto;">
                                            <table class="table table-sm table-bordered mb-0" style="font-size:0.82rem;">
                                                <thead class="table-light">
                                                    <tr>
                                                        <th>Salesforce ID</th>
                                                        <th>Record Name</th>
                                                        <th>Error</th>
                                                    </tr>
                                                </thead>
                                                <tbody>${errorRows}</tbody>
                                            </table>
                                        </div>
                                    </details>
                                </td>
                            </tr>`;
                        }
                    }
                }
                document.getElementById('historyTableBody').innerHTML = rows;
            } else {
                document.getElementById('historyTableBody').innerHTML = '<tr><td colspan="7" class="text-center text-muted">No sync history found</td></tr>';
            }
        } catch (error) {
            document.getElementById('historyTableBody').innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error loading history: ${error.message}</td></tr>`;
        }
    }

    function closeHistoryModal(event) {
        if (!event || event.target === document.getElementById('historyModal')) {
            document.getElementById('historyModal').classList.remove('show');
        }
    }

        // Global variables
        let currentData = null;
        let currentSettings = null;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            updateCurrentTime();
            setInterval(updateCurrentTime, 1000);

            // Set up event listeners
            document.getElementById('thresholdValue').textContent = document.getElementById('qualityThreshold').value;
            document.getElementById('qualityThreshold').addEventListener('input', function() {
                document.getElementById('thresholdValue').textContent = this.value;
            });

            // Auto-refresh when entity type changes
            document.getElementById('entityType').addEventListener('change', function() {
                console.log('Entity type changed to:', this.value);
                // Automatically refresh the quality data for the new entity
                calculateQualityScore();
            });

            // Auto-refresh when time period changes
            document.getElementById('timePeriod').addEventListener('change', function() {
                console.log('Time period changed to:', this.value);
                // Automatically refresh the quality data for the new time period
                calculateQualityScore();
            });

            // Load initial data
            calculateQualityScore();
        });

        // Update current time
        function updateCurrentTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleString();
        }

        // Toggle advanced filters
        function toggleAdvancedFilters() {
            const filters = document.getElementById('advancedFilters');
            filters.style.display = filters.style.display === 'none' ? 'block' : 'none';
        }

        // Show advanced settings modal
        function showAdvancedSettings() {
            loadAdvancedSettings();
            new bootstrap.Modal(document.getElementById('advancedSettingsModal')).show();
        }

        // Load advanced settings
        function loadAdvancedSettings() {
            fetch('/api/quality-settings', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(settings => {
                currentSettings = settings;
                displaySettings(settings);
            })
            .catch(error => {
                console.error('Error loading settings:', error);
                // Fallback to default settings
                displayDefaultSettings();
            });
        }

        // Display settings in the modal
        function displaySettings(settings) {
            // Display entity weights
            let entityWeightsHtml = '';
            if (settings.default_weights) {
                Object.entries(settings.default_weights).forEach(([entity, weights]) => {
                    if (entity !== 'default') {
                        entityWeightsHtml += `<h6>${formatEntityName(entity)} Weights</h6>`;
                        Object.entries(weights).forEach(([type, weight]) => {
                            entityWeightsHtml += `
                                <div class="mb-2">
                                    <div class="input-group">
                                        <input type="number" class="form-control"
                                               value="${weight}" step="0.01" min="0" max="1"
                                               data-entity="${entity}" data-type="${type}">
                                        <span class="input-group-text">${formatDimensionName(type)}</span>
                                    </div>
                                </div>
                            `;
                        });
                    }
                });
            }
            document.getElementById('entityWeights').innerHTML = entityWeightsHtml;

            // Display quality thresholds
            let thresholdsHtml = '';
            if (settings.default_thresholds) {
                Object.entries(settings.default_thresholds).forEach(([entity, threshold]) => {
                    if (entity !== 'default') {
                        thresholdsHtml += `
                            <div class="mb-2">
                                <label class="form-label">${formatEntityName(entity)} Threshold</label>
                                <div class="input-group">
                                    <input type="number" class="form-control"
                                           value="${threshold}" min="0" max="100"
                                           data-entity="${entity}">
                                    <span class="input-group-text">%</span>
                                </div>
                            </div>
                        `;
                    }
                });
            }
            document.getElementById('qualityThresholds').innerHTML = thresholdsHtml;
        }

        // Display default settings if loading fails
        function displayDefaultSettings() {
            document.getElementById('entityWeights').innerHTML = `
                <div class="mb-2">
                    <label class="form-label">Volunteer Weights</label>
                    <div class="input-group">
                        <input type="number" class="form-control" value="0.30" step="0.01" min="0" max="1">
                        <span class="input-group-text">Field Completeness</span>
                    </div>
                </div>
            `;
            document.getElementById('qualityThresholds').innerHTML = `
                <div class="mb-2">
                    <label class="form-label">Volunteer Threshold</label>
                    <div class="input-group">
                        <input type="number" class="form-control" value="80" min="0" max="100">
                        <span class="input-group-text">%</span>
                    </div>
                </div>
            `;
        }

        // Save advanced settings
        function saveAdvancedSettings() {
            // Collect all the settings from the form
            const settings = {
                weights: {},
                thresholds: {}
            };

            // Collect entity weights
            const weightInputs = document.querySelectorAll('#entityWeights input[data-entity]');
            weightInputs.forEach(input => {
                const entity = input.dataset.entity;
                const type = input.dataset.type;
                const weight = parseFloat(input.value);

                if (!settings.weights[entity]) {
                    settings.weights[entity] = {};
                }
                settings.weights[entity][type] = weight;
            });

            // Collect thresholds
            const thresholdInputs = document.querySelectorAll('#qualityThresholds input[data-entity]');
            thresholdInputs.forEach(input => {
                const entity = input.dataset.entity;
                const threshold = parseFloat(input.value);
                settings.thresholds[entity] = threshold;
            });

            // Save settings to backend
            fetch('/api/quality-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(result => {
                if (result.error) {
                    alert('Error saving settings: ' + result.error);
                } else {
                    alert('Settings saved successfully!');
                    bootstrap.Modal.getInstance(document.getElementById('advancedSettingsModal')).hide();
                    // Refresh the current data with new settings
                    calculateQualityScore();
                }
            })
            .catch(error => {
                console.error('Error saving settings:', error);
                alert('Error saving settings. Please try again.');
            });
        }

        // Export report
        function exportReport(format) {
            if (!currentData) {
                alert('No data to export. Please calculate quality scores first.');
                return;
            }

            let content, filename;
            if (format === 'json') {
                content = JSON.stringify(currentData, null, 2);
                filename = `quality_report_${new Date().toISOString().split('T')[0]}.json`;
            } else if (format === 'csv') {
                content = convertToCSV(currentData);
                filename = `quality_report_${new Date().toISOString().split('T')[0]}.csv`;
            }

            downloadFile(content, filename, format === 'json' ? 'application/json' : 'text/csv');
        }

        // Convert data to CSV
        function convertToCSV(data) {
            // Simple CSV conversion - can be enhanced
            let csv = 'Entity Type,Quality Score,Status,Total Checks,Passed Checks,Failed Checks\n';
            if (data.entity_scores) {
                Object.entries(data.entity_scores).forEach(([entity, score]) => {
                    csv += `${entity},${score.quality_score || 0},${score.quality_status || 'unknown'},${score.total_checks || 0},${score.passed_checks || 0},${score.failed_checks || 0}\n`;
                });
            }
            return csv;
        }

        // Download file
        function downloadFile(content, filename, contentType) {
            const blob = new Blob([content], { type: contentType });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            window.URL.revokeObjectURL(url);
        }

        // Calculate quality score
        function calculateQualityScore() {
            const entityType = document.getElementById('entityType').value;
            const timePeriod = document.getElementById('timePeriod').value;
            const includeTrends = document.getElementById('includeTrends').checked;
            const validationType = document.getElementById('validationType').value;
            const severityLevel = document.getElementById('severityLevel').value;
            const qualityThreshold = document.getElementById('qualityThreshold').value;
            const includeAnomalies = document.getElementById('includeAnomalies').checked;

            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('qualityScoreDisplay').style.display = 'none';
            document.getElementById('errorDisplay').style.display = 'none';

            // Prepare request data
            const requestData = {
                entity_type: entityType,
                days: parseInt(timePeriod),
                include_trends: includeTrends,
                validation_type: validationType || null,
                severity_level: severityLevel || null,
                quality_threshold: parseInt(qualityThreshold),
                include_anomalies: includeAnomalies
            };

            // Make API call
            fetch('/api/quality-score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(data => {
                currentData = data;
                displayQualityScore(data);
                document.getElementById('loading').style.display = 'none';
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('errorMessage').textContent = error.message;
                document.getElementById('errorDisplay').style.display = 'block';
                document.getElementById('loading').style.display = 'none';
            });
        }

        // Clear validation data
        function clearValidationData() {
            if (!confirm('Are you sure you want to clear ALL validation data? This will remove all validation results and scores.')) {
                return;
            }

            // Show loading indicator
            const clearButton = document.querySelector('button[onclick="clearValidationData()"]');
            const originalText = clearButton.textContent;
            clearButton.textContent = 'Clearing...';
            clearButton.disabled = true;

            // Clear data with more aggressive settings
            fetch('/api/clear-validation-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    entity_type: 'all',  // Clear all entity types
                    older_than_days: 0,  // Clear data from any age (including today)
                    user_id: null         // Clear data from all users
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`Clear Data Result:\n${data.message}\n\nRecords deleted: ${data.records_deleted}\n\nDetails:\n- Validation Runs: ${data.details.validation_runs}\n- Validation Results: ${data.details.validation_results}\n- Validation History: ${data.details.validation_history}\n- Validation Metrics: ${data.details.validation_metrics}`);

                    // Refresh the page to show cleared state
                    location.reload();
                } else {
                    alert('Error clearing validation data: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error clearing validation data: ' + error.message);
            })
            .finally(() => {
                // Restore button
                clearButton.textContent = originalText;
                clearButton.disabled = false;
            });
        }

        function runValidation() {
            // Show loading indicator
            const runButton = document.querySelector('button[onclick="runValidation()"]');
            const originalText = runButton.textContent;
            runButton.textContent = 'Running...';
            runButton.disabled = true;

            const entityType = document.getElementById('entityType').value;

            fetch('/api/run-validation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    entity_type: entityType,
                    validation_type: 'count'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`Validation completed successfully!\n\nRun ID: ${data.run_id}\nStatus: ${data.status}\nTotal Checks: ${data.total_checks}\n\nNow you can click Calculate to see quality scores.`);

                    // Refresh debug data to show new records
                    setTimeout(() => {
                        debugValidationData();
                    }, 1000);
                } else {
                    alert('Error running validation: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error running validation: ' + error.message);
            })
            .finally(() => {
                // Restore button
                runButton.textContent = originalText;
                runButton.disabled = false;
            });
        }

        function runAllValidations() {
            // Show loading indicator
            const runAllButton = document.querySelector('button[onclick="runAllValidations()"]');
            const originalText = runAllButton.textContent;
            runAllButton.textContent = 'Running All...';
            runAllButton.disabled = true;

            // Show progress message
            alert('Running validations for all entity types...\n\nThis will validate: Volunteer, Organization, Event, Student, Teacher, School, and District data.\n\nPlease wait for completion.');

            // Use the more efficient multiple validation endpoint
            fetch('/api/run-multiple-validations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    entity_types: ['volunteer', 'organization', 'event', 'student', 'teacher', 'school', 'district'],
                    validation_type: 'comprehensive'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show final results
                    let resultMessage = `All validations completed!\n\n`;
                    resultMessage += `Total Runs: ${data.total_runs}\n`;
                    resultMessage += `Successful: ${data.successful_runs}\n`;
                    resultMessage += `Failed: ${data.total_runs - data.successful_runs}\n\n`;
                    resultMessage += `Results:\n`;

                    data.results.forEach(result => {
                        if (result.success) {
                            resultMessage += `✅ ${result.entity_type}: Run ID ${result.run_id}, ${result.total_checks} checks\n`;
                        } else {
                            resultMessage += `❌ ${result.entity_type}: ${result.error}\n`;
                        }
                    });

                    resultMessage += `\nNow you can click Calculate to see quality scores for all entities.`;
                    alert(resultMessage);

                    // Refresh debug data to show new records
                    setTimeout(() => {
                        debugValidationData();
                    }, 1000);
                } else {
                    alert('Error running multiple validations: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error running multiple validations: ' + error.message);
            })
            .finally(() => {
                // Restore button
                runAllButton.textContent = originalText;
                runAllButton.disabled = false;
            });
        }

        function debugValidationData() {
            // Show loading indicator
            const debugButton = document.querySelector('button[onclick="debugValidationData()"]');
            const originalText = debugButton.textContent;
            debugButton.textContent = 'Loading...';
            debugButton.disabled = true;

            fetch('/api/debug-validation-data')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    let message = 'Current Validation Data in Database:\n\n';
                    message += `Total Records:\n`;
                    message += `- Validation Runs: ${data.total_counts.validation_runs}\n`;
                    message += `- Validation Results: ${data.total_counts.validation_results}\n`;
                    message += `- Validation History: ${data.total_counts.validation_history}\n`;
                    message += `- Validation Metrics: ${data.total_counts.validation_metrics}\n\n`;

                    if (data.entity_breakdown && Object.keys(data.entity_breakdown).length > 0) {
                        message += `Entity Type Breakdown:\n`;
                        for (const [entity, count] of Object.entries(data.entity_breakdown)) {
                            message += `- ${entity}: ${count} results\n`;
                        }
                        message += '\n';
                    }

                    if (data.recent_runs && data.recent_runs.length > 0) {
                        message += `Recent Validation Runs:\n`;
                        data.recent_runs.forEach(run => {
                            message += `- Run ${run.id}: ${run.name} (${run.status}) - ${run.total_checks} checks\n`;
                        });
                    }

                    alert(message);
                } else {
                    alert('Error getting debug data: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error getting debug data: ' + error.message);
            })
            .finally(() => {
                // Restore button
                debugButton.textContent = originalText;
                debugButton.disabled = false;
            });
        }

        // Display quality score
        function displayQualityScore(data) {
            if (data.error) {
                document.getElementById('errorMessage').textContent = data.error;
                document.getElementById('errorDisplay').style.display = 'block';
                return;
            }

            // Overall score
            if (data.quality_score !== undefined) {
                document.getElementById('overallScore').textContent = data.quality_score.toFixed(1);
                document.getElementById('overallScore').className = `quality-score ${getQualityClass(data.quality_score)}`;
                document.getElementById('qualityStatus').textContent = data.quality_status || 'Unknown';
                document.getElementById('qualityDescription').textContent = getQualityDescription(data.quality_score);
            }

            // Dimension scores
            if (data.dimension_scores) {
                displayDimensionScores(data.dimension_scores);
            } else if (data.entity_scores) {
                displayEntityScores(data.entity_scores);
            }

            // Statistics
            if (data.total_checks !== undefined) {
                displayEntityStatistics(data);
            } else if (data.overall_summary) {
                displayStatistics(data.overall_summary);
            }

            // Trends
            if (data.trend) {
                displayEntityTrend(data.trend);
            }

            // Detailed results
            if (data.validation_results) {
                displayValidationResults(data.validation_results);
            }

            // Performance metrics
            if (data.performance_metrics) {
                displayPerformanceMetrics(data.performance_metrics);
            }

            // Anomalies
            if (data.anomalies) {
                displayAnomalies(data.anomalies);
            }

            // Show display
            document.getElementById('qualityScoreDisplay').style.display = 'block';
        }

        // Display dimension scores with entity breakdown
        function displayDimensionScores(dimensionScores) {
            const container = document.getElementById('dimensionScores');
            container.innerHTML = '';

            // Add header for entity breakdown
            const headerElement = document.createElement('div');
            headerElement.className = 'dimension-header mb-3';
            headerElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">
                        <i class="fas fa-chart-pie me-2"></i>Overall Dimension Scores
                    </h5>
                    <button class="btn btn-sm btn-outline-info" onclick="toggleEntityBreakdown()">
                        <i class="fas fa-list me-1"></i>Show Entity Breakdown
                    </button>
                </div>
            `;
            container.appendChild(headerElement);

            // Display overall dimension scores
            Object.entries(dimensionScores).forEach(([dimension, score]) => {
                const scoreElement = document.createElement('div');
                scoreElement.className = 'metric-card mb-3';
                scoreElement.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">${formatDimensionName(dimension)}</h6>
                        <span class="badge bg-primary">${score.toFixed(1)}%</span>
                    </div>
                    <div class="progress mt-2">
                        <div class="progress-bar ${getProgressBarClass(score)}"
                             style="width: ${score}%"
                             role="progressbar">
                            ${score.toFixed(1)}%
                        </div>
                    </div>
                `;
                container.appendChild(scoreElement);
            });

            // Add entity breakdown section (initially hidden)
            const breakdownElement = document.createElement('div');
            breakdownElement.id = 'entityBreakdown';
            breakdownElement.className = 'entity-breakdown mt-4';
            breakdownElement.style.display = 'none';
            breakdownElement.innerHTML = `
                <div class="card">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">
                            <i class="fas fa-sitemap me-2"></i>Entity-by-Entity Breakdown
                        </h6>
                    </div>
                    <div class="card-body">
                        <div id="entityBreakdownContent">
                            <div class="text-center py-3">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading entity breakdown...</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(breakdownElement);

            // Load entity breakdown data
            loadEntityBreakdown();
        }

        // Toggle entity breakdown visibility
        function toggleEntityBreakdown() {
            const breakdown = document.getElementById('entityBreakdown');
            const button = document.querySelector('button[onclick="toggleEntityBreakdown()"]');

            if (breakdown.style.display === 'none') {
                breakdown.style.display = 'block';
                button.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Entity Breakdown';
            } else {
                breakdown.style.display = 'none';
                button.innerHTML = '<i class="fas fa-list me-1"></i>Show Entity Breakdown';
            }
        }

        // Load entity breakdown data
        function loadEntityBreakdown() {
            const entityTypes = ['volunteer', 'organization', 'event', 'student', 'teacher', 'school', 'district'];
            const breakdownContent = document.getElementById('entityBreakdownContent');

            // Create entity breakdown table
            let tableHTML = `
                <div class="table-responsive">
                    <table class="table table-sm table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Entity Type</th>
                                <th>Business Rules</th>
                                <th>Count Validation</th>
                                <th>Field Completeness</th>
                                <th>Data Types</th>
                                <th>Relationships</th>
                                <th>Overall Score</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            // Add rows for each entity type
            entityTypes.forEach(entityType => {
                tableHTML += `
                    <tr>
                        <td>
                            <strong>${formatEntityName(entityType)}</strong>
                            <br><small class="text-muted">${getEntityDescription(entityType)}</small>
                        </td>
                        <td id="br-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                        <td id="count-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                        <td id="fc-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                        <td id="dt-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                        <td id="rel-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                        <td id="overall-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                        <td id="status-${entityType}">
                            <span class="badge bg-secondary">Loading...</span>
                        </td>
                    </tr>
                `;
            });

            tableHTML += `
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Legend:</strong>
                        <span class="badge bg-success">Available</span> = Validation implemented and running,
                        <span class="badge bg-warning">Limited</span> = Some validations available,
                        <span class="badge bg-danger">Missing</span> = No validations implemented,
                        <span class="badge bg-secondary">N/A</span> = Not applicable for this entity
                    </div>
                    <div class="alert alert-warning">
                        <i class="fas fa-lightbulb me-2"></i>
                        <strong>Next Steps:</strong> Business Rules validation is currently limited to required field validation.
                        Consider implementing more complex business logic rules for better data quality assessment.
                    </div>
                </div>
            `;

            breakdownContent.innerHTML = tableHTML;

            // Load individual entity scores
            entityTypes.forEach(entityType => {
                loadEntityScore(entityType);
            });
        }

        // Load individual entity score
        function loadEntityScore(entityType) {
            fetch('/api/quality-score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    entity_type: entityType,
                    days: 7
                })
            })
                .then(response => response.json())
                .then(data => {
                    console.log(`Received data for ${entityType}:`, data);
                    if (data.error) {
                        console.error(`Error in response for ${entityType}:`, data.error);
                        updateEntityBreakdownRow(entityType, { error: true });
                    } else {
                        updateEntityBreakdownRow(entityType, data);
                    }
                })
                .catch(error => {
                    console.error(`Error loading ${entityType} score:`, error);
                    updateEntityBreakdownRow(entityType, { error: true });
                });
        }

        // Update entity breakdown row
        function updateEntityBreakdownRow(entityType, data) {
            if (data.error) {
                // Show error state
                document.getElementById(`br-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                document.getElementById(`count-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                document.getElementById(`fc-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                document.getElementById(`dt-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                document.getElementById(`rel-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                document.getElementById(`overall-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                document.getElementById(`status-${entityType}`).innerHTML = '<span class="badge bg-danger">Error</span>';
                return;
            }

            const dimensionScores = data.dimension_scores || {};
            const overallScore = data.quality_score || 0;

            // Update each dimension
            updateDimensionBadge(`br-${entityType}`, dimensionScores.business_rules, 'Business Rules');
            updateDimensionBadge(`count-${entityType}`, dimensionScores.count_validation, 'Count Validation');
            updateDimensionBadge(`fc-${entityType}`, dimensionScores.field_completeness, 'Field Completeness');
            updateDimensionBadge(`dt-${entityType}`, dimensionScores.data_types, 'Data Types');
            updateDimensionBadge(`rel-${entityType}`, dimensionScores.relationships, 'Relationships');

            // Update overall score
            document.getElementById(`overall-${entityType}`).innerHTML =
                `<span class="badge ${getBadgeClass(overallScore)}">${overallScore.toFixed(1)}%</span>`;

            // Update status
            document.getElementById(`status-${entityType}`).innerHTML =
                `<span class="badge ${getStatusBadgeClass(overallScore)}">${getQualityStatus(overallScore)}</span>`;
        }

        // Get entity description
        function getEntityDescription(entityType) {
            const descriptions = {
                'volunteer': 'Contact records with volunteer activities',
                'organization': 'Companies, schools, and institutions',
                'event': 'Volunteer events and activities',
                'student': 'Contact records for students',
                'teacher': 'Contact records for teachers',
                'school': 'Educational institutions',
                'district': 'School districts'
            };
            return descriptions[entityType] || 'Data entity';
        }

        // Update dimension badge with availability indicator
        function updateDimensionBadge(elementId, score, dimensionName) {
            const element = document.getElementById(elementId);
            if (score !== undefined && score !== null) {
                // Score available - show the score
                element.innerHTML = `<span class="badge ${getBadgeClass(score)}">${score.toFixed(1)}%</span>`;
            } else {
                // No score - check if this dimension should be available for this entity
                const availability = getDimensionAvailability(dimensionName);
                element.innerHTML = `<span class="badge ${availability.badge}">${availability.text}</span>`;
            }
        }

        // Get dimension availability for different entity types
        function getDimensionAvailability(dimensionName) {
            // Enhanced availability based on actual configuration
            const availability = {
                'Business Rules': {
                    badge: 'bg-warning',
                    text: 'Limited',
                    description: 'Basic required field validation implemented'
                },
                'Count Validation': {
                    badge: 'bg-success',
                    text: 'Available',
                    description: 'Full count validation with context-aware scoring'
                },
                'Field Completeness': {
                    badge: 'bg-success',
                    text: 'Available',
                    description: 'Complete field completeness validation'
                },
                'Data Types': {
                    badge: 'bg-success',
                    text: 'Available',
                    description: 'Full data type validation with severity scoring'
                },
                'Relationships': {
                    badge: 'bg-success',
                    text: 'Available',
                    description: 'Complete relationship validation including orphaned records'
                }
            };
            return availability[dimensionName] || { badge: 'bg-secondary', text: 'N/A', description: 'Not implemented' };
        }

        // Get quality status text
        function getQualityStatus(score) {
            if (score >= 95) return 'Excellent';
            if (score >= 85) return 'Good';
            if (score >= 70) return 'Fair';
            if (score >= 50) return 'Poor';
            return 'Critical';
        }

        // Get status badge class
        function getStatusBadgeClass(score) {
            if (score >= 95) return 'bg-success';
            if (score >= 85) return 'bg-info';
            if (score >= 70) return 'bg-warning';
            if (score >= 50) return 'bg-warning';
            return 'bg-danger';
        }

        // Display entity scores grid
        function displayEntityScores(entityScores) {
            const container = document.getElementById('dimensionScores');
            container.innerHTML = '';

            Object.entries(entityScores).forEach(([entity, data]) => {
                const scoreElement = document.createElement('div');
                scoreElement.className = 'metric-card';
                scoreElement.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">${formatEntityName(entity)}</h6>
                        <span class="badge ${getBadgeClass(data.quality_score)}">${data.quality_score.toFixed(1)}%</span>
                    </div>
                    <div class="progress mt-2">
                        <div class="progress-bar ${getProgressBarClass(data.quality_score)}"
                             style="width: ${data.quality_score}%"
                             role="progressbar">
                            ${data.quality_score.toFixed(1)}%
                        </div>
                    </div>
                    <small class="text-muted">${data.total_checks} checks, ${data.passed_checks} passed</small>
                `;
                container.appendChild(scoreElement);
            });
        }

        // Display validation results
        function displayValidationResults(results) {
            const container = document.getElementById('validationResultsDetails');
            container.innerHTML = '';

            if (!results || results.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                        <h5 class="text-success">No Validation Issues Found!</h5>
                        <p class="text-muted">Your data quality is excellent. No validation problems were detected.</p>
                    </div>`;
                document.getElementById('resultsSummary').style.display = 'none';
                return;
            }

            // Show results summary
            document.getElementById('resultsSummary').style.display = 'block';

            // Count results by severity
            const counts = { critical: 0, error: 0, warning: 0, info: 0 };
            results.forEach(result => {
                const severity = result.severity?.toLowerCase() || 'info';
                if (counts.hasOwnProperty(severity)) {
                    counts[severity]++;
                }
            });

            // Update summary counts
            document.getElementById('criticalCount').textContent = counts.critical;
            document.getElementById('errorCount').textContent = counts.error;
            document.getElementById('warningCount').textContent = counts.warning;
            document.getElementById('infoCount').textContent = counts.info;

            // Display business rule insights if available
            displayBusinessRuleInsights(results);

            // Display results with enhanced information
            results.forEach(result => {
                const resultElement = document.createElement('div');
                resultElement.className = `validation-result-item ${result.severity}`;

                // Enhanced content for business rules with percentages and field requirements
                let enhancedContent = '';

                if (result.validation_type === 'business_rules' && result.metadata) {
                    enhancedContent = getBusinessRuleEnhancedContent(result);
                } else {
                    enhancedContent = getStandardValidationContent(result);
                }

                resultElement.innerHTML = `
                    <div class="result-header mb-2">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">
                                    <i class="fas fa-${getSeverityIcon(result.severity)} me-2"></i>
                                    ${result.field_name || 'Field Validation'}
                                </h6>
                                <span class="badge bg-${getSeverityColor(result.severity)} me-2">${result.severity}</span>
                                <span class="badge bg-secondary">${result.validation_type || 'Unknown'}</span>
                            </div>
                            <small class="text-muted">
                                ${result.timestamp ? new Date(result.timestamp).toLocaleDateString() : 'Recent'}
                            </small>
                        </div>
                    </div>

                    <div class="result-content">
                        ${enhancedContent}
                    </div>
                `;
                container.appendChild(resultElement);
            });
        }

        // Get enhanced content for business rule validations
        function getBusinessRuleEnhancedContent(result) {
            const metadata = result.metadata;
            let content = '';

            // Basic issue description
            content += `<p class="mb-2"><strong>Issue:</strong> ${result.message || 'No description available'}</p>`;

            // Show statistics if available (for cross-field validation)
            if (metadata.statistics) {
                const stats = metadata.statistics;
                content += `
                    <div class="statistics-section mb-3 p-3 bg-light rounded">
                        <h6 class="mb-2"><i class="fas fa-chart-bar me-2"></i>Data Statistics</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <strong>Total Records:</strong> ${stats.total_records || 0}<br>
                                <strong>Condition Met:</strong> ${stats.condition_met || 0}<br>
                                <strong>Field Populated:</strong> ${stats.field_populated || 0}
                            </div>
                            <div class="col-md-6">
                                <strong>Field Missing:</strong> ${stats.field_missing || 0}<br>
                                <strong>Populated %:</strong> <span class="text-success">${(stats.populated_percentage || 0).toFixed(1)}%</span><br>
                                <strong>Missing %:</strong> <span class="text-danger">${(stats.missing_percentage || 0).toFixed(1)}%</span>
                            </div>
                        </div>
                    </div>
                `;
            }

            // Show field requirement insights if available
            if (metadata.field_requirements) {
                const req = metadata.field_requirements;
                content += `
                    <div class="field-requirements-section mb-3 p-3 bg-info bg-opacity-10 rounded">
                        <h6 class="mb-2"><i class="fas fa-info-circle me-2"></i>Field Requirement Analysis</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <strong>Requirement Level:</strong>
                                <span class="badge bg-${getRequirementLevelColor(req.requirement_level)}">${req.requirement_level}</span><br>
                                <strong>Business Rule Required:</strong> ${req.business_rule_required ? 'Yes' : 'No'}<br>
                                <strong>Salesforce Required:</strong> ${req.salesforce_required ? 'Yes' : 'No'}
                            </div>
                            <div class="col-md-6">
                                <strong>Recommendation:</strong><br>
                                <small class="text-muted">${req.recommendation || 'N/A'}</small>
                            </div>
                        </div>
                        <div class="mt-2">
                            <strong>Explanation:</strong><br>
                            <small class="text-muted">${req.explanation || 'N/A'}</small>
                        </div>
                    </div>
                `;
            }

            // Standard validation details
            content += `
                <div class="result-details row mb-2">
                    <div class="col-md-6">
                        <strong>Expected:</strong>
                        <span class="text-success">${result.expected_value || 'N/A'}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Actual:</strong>
                        <span class="text-danger">${result.actual_value || 'N/A'}</span>
                    </div>
                </div>

                <div class="impact-section mb-2">
                    <strong>Impact:</strong>
                    <span class="text-${getImpactColor(result.severity)}">${getImpactDescription(result.severity)}</span>
                </div>

                <div class="action-items">
                    <strong>Recommended Actions:</strong>
                    <ul class="mb-0 mt-1">
                        ${getActionItems(result.validation_type, result.severity)}
                    </ul>
                </div>
            `;

            return content;
        }

        // Get standard validation content for non-business rule validations
        function getStandardValidationContent(result) {
            return `
                <p class="mb-2"><strong>Issue:</strong> ${result.message || 'No description available'}</p>

                <div class="result-details row mb-2">
                    <div class="col-md-6">
                        <strong>Expected:</strong>
                        <span class="text-success">${result.expected_value || 'N/A'}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Actual:</strong>
                        <span class="text-danger">${result.actual_value || 'N/A'}</span>
                    </div>
                </div>

                <div class="impact-section mb-2">
                    <strong>Impact:</strong>
                    <span class="text-${getImpactColor(result.severity)}">${getImpactDescription(result.severity)}</span>
                </div>

                <div class="action-items">
                    <strong>Recommended Actions:</strong>
                    <ul class="mb-0 mt-1">
                        ${getActionItems(result.validation_type, result.severity)}
                    </ul>
                </div>
            `;
        }

        // Display business rule validation insights
        function displayBusinessRuleInsights(results) {
            const businessRuleResults = results.filter(r => r.validation_type === 'business_rules');

            if (businessRuleResults.length === 0) {
                return;
            }

            // Create insights section if it doesn't exist
            let insightsContainer = document.getElementById('businessRuleInsights');
            if (!insightsContainer) {
                const resultsSummary = document.getElementById('resultsSummary');
                const insightsDiv = document.createElement('div');
                insightsDiv.className = 'business-rule-insights mb-3';
                insightsDiv.id = 'businessRuleInsights';
                insightsDiv.innerHTML = `
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h6 class="mb-0">
                                <i class="fas fa-chart-pie me-2"></i>
                                Business Rule Validation Insights
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="row" id="businessRuleStats">
                                <!-- Business rule statistics will be populated here -->
                            </div>
                        </div>
                    </div>
                `;
                resultsSummary.parentNode.insertBefore(insightsDiv, resultsSummary.nextSibling);
                insightsContainer = insightsDiv;
            }

            // Show business rule insights
            insightsContainer.style.display = 'block';

            const container = document.getElementById('businessRuleStats');
            container.innerHTML = '';

            // Extract cross-field validation statistics
            const crossFieldStats = {};
            businessRuleResults.forEach(result => {
                if (result.metadata && result.metadata.statistics) {
                    const stats = result.metadata.statistics;
                    const fieldName = result.field_name.replace('_summary', '');

                    if (!crossFieldStats[fieldName]) {
                        crossFieldStats[fieldName] = {
                            field_name: fieldName,
                            total_records: stats.total_records || 0,
                            condition_met: stats.condition_met || 0,
                            field_populated: stats.field_populated || 0,
                            field_missing: stats.field_missing || 0,
                            populated_percentage: stats.populated_percentage || 0,
                            missing_percentage: stats.missing_percentage || 0,
                            field_required: stats.field_required || false
                        };
                    }
                }
            });

            // Display cross-field validation insights
            if (Object.keys(crossFieldStats).length > 0) {
                Object.values(crossFieldStats).forEach(stats => {
                    const insightElement = document.createElement('div');
                    insightElement.className = 'col-md-6 mb-3';

                    const severityClass = stats.missing_percentage >= 50 ? 'danger' :
                                        stats.missing_percentage >= 25 ? 'warning' :
                                        stats.missing_percentage >= 10 ? 'info' : 'success';

                    insightElement.innerHTML = `
                        <div class="card h-100">
                            <div class="card-body">
                                <h6 class="card-title text-${severityClass}">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    ${stats.field_name}
                                </h6>
                                <div class="row">
                                    <div class="col-6">
                                        <small class="text-muted">Total Records</small><br>
                                        <strong>${stats.total_records}</strong>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Condition Met</small><br>
                                        <strong>${stats.condition_met}</strong>
                                    </div>
                                </div>
                                <div class="row mt-2">
                                    <div class="col-6">
                                        <small class="text-muted">Populated</small><br>
                                        <span class="text-success">${stats.field_populated} (${stats.populated_percentage.toFixed(1)}%)</span>
                                    </div>
                                    <div class="col-6">
                                        <small class="text-muted">Missing</small><br>
                                        <span class="text-${severityClass}">${stats.field_missing} (${stats.missing_percentage.toFixed(1)}%)</span>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    <small class="text-muted">Field Required:</small>
                                    <span class="badge bg-${stats.field_required ? 'danger' : 'success'} ms-1">
                                        ${stats.field_required ? 'Yes' : 'No'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    `;
                    container.appendChild(insightElement);
                });
            } else {
                // Show general business rule summary
                container.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Business rule validation completed with ${businessRuleResults.length} results.
                            Check the detailed results below for specific insights.
                        </div>
                    </div>
                `;
            }
        }

        // Get color for requirement level badges
        function getRequirementLevelColor(level) {
            const colors = {
                'strictly_required': 'danger',
                'business_required': 'warning',
                'salesforce_required': 'info',
                'optional': 'success',
                'unknown': 'secondary'
            };
            return colors[level] || 'secondary';
        }

        // Display performance metrics
        function displayPerformanceMetrics(metrics) {
            const container = document.getElementById('performanceMetrics');
            container.innerHTML = '';

            const performanceItems = [
                { label: 'Execution Time', value: `${metrics.execution_time_seconds || 0}s`, icon: 'fas fa-clock', color: 'primary' },
                { label: 'Memory Usage', value: `${metrics.memory_usage_mb || 0} MB`, icon: 'fas fa-memory', color: 'info' },
                { label: 'CPU Usage', value: `${metrics.cpu_usage_percent || 0}%`, icon: 'fas fa-microchip', color: 'warning' },
                { label: 'Records Processed', value: metrics.records_processed || 0, icon: 'fas fa-database', color: 'success' }
            ];

            performanceItems.forEach(item => {
                const metricElement = document.createElement('div');
                metricElement.className = 'performance-metric';
                metricElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="${item.icon} fa-2x text-${item.color} me-3"></i>
                        <div>
                            <h6 class="mb-0">${item.label}</h6>
                            <h4 class="mb-0">${item.value}</h4>
                        </div>
                    </div>
                `;
                container.appendChild(metricElement);
            });
        }

        // Display anomalies
        function displayAnomalies(anomalies) {
            const container = document.getElementById('anomalyDetection');
            container.innerHTML = '';

            if (!anomalies || anomalies.length === 0) {
                container.innerHTML = '<p class="text-muted">No anomalies detected.</p>';
                return;
            }

            anomalies.forEach(anomaly => {
                const anomalyElement = document.createElement('div');
                anomalyElement.className = 'anomaly-indicator';
                anomalyElement.innerHTML = `
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Anomaly Detected</h6>
                    <p class="mb-1"><strong>Type:</strong> ${anomaly.anomaly_type || 'Unknown'}</p>
                    <p class="mb-1"><strong>Score:</strong> ${anomaly.anomaly_score || 'N/A'}</p>
                    <p class="mb-0"><strong>Description:</strong> ${anomaly.description || 'Statistical anomaly detected'}</p>
                `;
                container.appendChild(anomalyElement);
            });
        }

        // Display statistics
        function displayStatistics(summary) {
            const container = document.getElementById('statsGrid');
            container.innerHTML = '';

            const stats = [
                { label: 'Total Entities', value: summary.total_entities, icon: 'fas fa-database', color: 'primary' },
                { label: 'Quality Distribution', value: formatQualityDistribution(summary.quality_distribution), icon: 'fas fa-chart-pie', color: 'info' },
                { label: 'Top Performers', value: formatTopPerformers(summary.top_performers), icon: 'fas fa-trophy', color: 'success' },
                { label: 'Improvement Opportunities', value: summary.improvement_opportunities.length, icon: 'fas fa-exclamation-triangle', color: 'warning' }
            ];

            stats.forEach(stat => {
                const statElement = document.createElement('div');
                statElement.className = 'card';
                statElement.innerHTML = `
                    <div class="card-body text-center">
                        <i class="fas ${stat.icon} fa-2x text-${stat.color} mb-2"></i>
                        <h5 class="card-title">${stat.label}</h5>
                        <p class="card-text">${stat.value}</p>
                    </div>
                `;
                container.appendChild(statElement);
            });
        }

        // Display entity statistics
        function displayEntityStatistics(data) {
            const container = document.getElementById('statsGrid');
            container.innerHTML = '';

            const stats = [
                { label: 'Total Checks', value: data.total_checks, icon: 'fas fa-clipboard-check', color: 'primary' },
                { label: 'Passed Checks', value: data.passed_checks, icon: 'fas fa-check-circle', color: 'success' },
                { label: 'Failed Checks', value: data.failed_checks, icon: 'fas fa-times-circle', color: 'danger' },
                { label: 'Threshold', value: data.threshold + '%', icon: 'fas fa-bullseye', color: 'info' }
            ];

            stats.forEach(stat => {
                const statElement = document.createElement('div');
                statElement.className = 'card';
                statElement.innerHTML = `
                    <div class="card-body text-center">
                        <i class="fas ${stat.icon} fa-2x text-${stat.color} mb-2"></i>
                        <h5 class="card-title">${stat.label}</h5>
                        <p class="card-text">${stat.value}</p>
                    </div>
                `;
                container.appendChild(statElement);
            });
        }

        // Display entity trend
        function displayEntityTrend(trend) {
            const container = document.getElementById('trendAnalysis');
            container.innerHTML = '';

            if (!trend || trend.trend === 'insufficient_data') {
                container.innerHTML = '<p class="text-muted">Insufficient data for trend analysis.</p>';
                return;
            }

            const trendElement = document.createElement('div');
            trendElement.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>Trend Direction</h6>
                        <p class="mb-2">
                            <span class="trend-indicator ${getTrendClass(trend.trend)}">
                                <i class="fas fa-arrow-${trend.trend === 'improving' ? 'up' : trend.trend === 'declining' ? 'down' : 'right'}"></i>
                                ${trend.trend}
                            </span>
                        </p>
                        <p><strong>Data Points:</strong> ${trend.data_points}</p>
                        <p><strong>Average Score:</strong> ${trend.average_score}%</p>
                    </div>
                    <div class="col-md-6">
                        <h6>Score Range</h6>
                        <p><strong>Minimum:</strong> ${trend.score_range?.min || 'N/A'}%</p>
                        <p><strong>Maximum:</strong> ${trend.score_range?.max || 'N/A'}%</p>
                        <p><strong>Variance:</strong> ${trend.score_variance || 'N/A'}</p>
                    </div>
                </div>
            `;
            container.appendChild(trendElement);
        }

        // Helper functions
        function formatDimensionName(dimension) {
            return dimension.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }

        function formatEntityName(entity) {
            return entity.charAt(0).toUpperCase() + entity.slice(1);
        }

        function getQualityClass(score) {
            if (score >= 90) return 'quality-excellent';
            if (score >= 80) return 'quality-good';
            if (score >= 70) return 'quality-fair';
            return 'quality-poor';
        }

        function getProgressBarClass(score) {
            if (score >= 90) return 'bg-success';
            if (score >= 80) return 'bg-info';
            if (score >= 70) return 'bg-warning';
            return 'bg-danger';
        }

        function getBadgeClass(score) {
            if (score >= 90) return 'bg-success';
            if (score >= 80) return 'bg-info';
            if (score >= 70) return 'bg-warning';
            return 'bg-danger';
        }

        function getSeverityColor(severity) {
            switch (severity) {
                case 'critical': return 'danger';
                case 'error': return 'warning';
                case 'warning': return 'warning';
                case 'info': return 'info';
                default: return 'secondary';
            }
        }

        function getTrendClass(trend) {
            switch (trend) {
                case 'improving': return 'trend-up';
                case 'declining': return 'trend-down';
                default: return 'trend-stable';
            }
        }

        function getQualityDescription(score) {
            if (score >= 90) return 'Excellent data quality';
            if (score >= 80) return 'Good data quality';
            if (score >= 70) return 'Fair data quality - needs attention';
            return 'Poor data quality - immediate action required';
        }

        function formatQualityDistribution(distribution) {
            if (!distribution) return 'N/A';
            return Object.entries(distribution)
                .map(([status, count]) => `${status}: ${count}`)
                .join(', ');
        }

        function formatTopPerformers(performers) {
            if (!performers || performers.length === 0) return 'None';
            return performers.map(p => `${p.entity_type}: ${p.quality_score}%`).join(', ');
        }

        // Helper functions for enhanced validation results display
        function getSeverityIcon(severity) {
            switch (severity?.toLowerCase()) {
                case 'critical': return 'exclamation-triangle';
                case 'error': return 'times-circle';
                case 'warning': return 'exclamation-circle';
                case 'info': return 'info-circle';
                default: return 'question-circle';
            }
        }

        function getImpactColor(severity) {
            switch (severity?.toLowerCase()) {
                case 'critical': return 'danger';
                case 'error': return 'warning';
                case 'warning': return 'info';
                case 'info': return 'secondary';
                default: return 'secondary';
            }
        }

        function getImpactDescription(severity) {
            switch (severity?.toLowerCase()) {
                case 'critical': return 'High - May cause system failures or data corruption';
                case 'error': return 'Medium - Affects data accuracy and reporting';
                case 'warning': return 'Low - Minor issues that should be addressed';
                case 'info': return 'Minimal - Informational items for awareness';
                default: return 'Unknown - Severity level not specified';
            }
        }

        function getActionItems(validationType, severity) {
            const actions = [];

            // Add severity-based actions
            if (severity?.toLowerCase() === 'critical') {
                actions.push('Address immediately to prevent system issues');
                actions.push('Review data entry processes');
                actions.push('Implement validation rules');
            } else if (severity?.toLowerCase() === 'error') {
                actions.push('Fix within 24-48 hours');
                actions.push('Update data quality procedures');
                actions.push('Train users on proper data entry');
            } else if (severity?.toLowerCase() === 'warning') {
                actions.push('Address within the week');
                actions.push('Monitor for patterns');
                actions.push('Consider process improvements');
            }

            // Add validation type-specific actions
            if (validationType === 'field_completeness') {
                actions.push('Ensure required fields are populated');
                actions.push('Review field requirements');
                actions.push('Update data entry forms');
            } else if (validationType === 'data_types') {
                actions.push('Verify data format requirements');
                actions.push('Check field type definitions');
                actions.push('Update data validation rules');
            } else if (validationType === 'business_rules') {
                actions.push('Review business logic requirements');
                actions.push('Update validation rules');
                actions.push('Train users on business processes');
            } else if (validationType === 'relationships') {
                actions.push('Verify foreign key connections');
                actions.push('Check reference data integrity');
                actions.push('Update relationship mappings');
            }

            return actions.length > 0 ? actions.map(action => `<li>${action}</li>`).join('') : '<li>Review and address based on business impact</li>';
        }

                 // Toggle help panel visibility functions
         function toggleDetailsHelp() {
             const helpPanel = document.getElementById('detailsHelpPanel');
             const button = helpPanel.querySelector('button');
             const icon = button.querySelector('i');

             if (helpPanel.style.display === 'none') {
                 helpPanel.style.display = 'block';
                 icon.className = 'fas fa-eye me-1';
                 button.innerHTML = '<i class="fas fa-eye me-1"></i>Show Help';
             } else {
                 helpPanel.style.display = 'none';
                 icon.className = 'fas fa-eye-slash me-1';
                 button.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Help';
             }
         }

         function toggleOverviewHelp() {
             const helpPanel = document.getElementById('overviewHelpPanel');
             const button = helpPanel.querySelector('button');
             const icon = button.querySelector('i');

             if (helpPanel.style.display === 'none') {
                 helpPanel.style.display = 'block';
                 icon.className = 'fas fa-eye me-1';
                 button.innerHTML = '<i class="fas fa-eye me-1"></i>Show Help';
             } else {
                 helpPanel.style.display = 'none';
                 icon.className = 'fas fa-eye-slash me-1';
                 button.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Help';
             }
         }

         function togglePerformanceHelp() {
             const helpPanel = document.getElementById('performanceHelpPanel');
             const button = helpPanel.querySelector('button');
             const icon = button.querySelector('i');

             if (helpPanel.style.display === 'none') {
                 helpPanel.style.display = 'block';
                 icon.className = 'fas fa-eye me-1';
                 button.innerHTML = '<i class="fas fa-eye me-1"></i>Show Help';
             } else {
                 helpPanel.style.display = 'none';
                 icon.className = 'fas fa-eye-slash me-1';
                 button.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Help';
             }
         }

         function toggleTrendsHelp() {
             const helpPanel = document.getElementById('trendsHelpPanel');
             const button = helpPanel.querySelector('button');
             const icon = button.querySelector('i');

             if (helpPanel.style.display === 'none') {
                 helpPanel.style.display = 'block';
                 icon.className = 'fas fa-eye me-1';
                 button.innerHTML = '<i class="fas fa-eye me-1"></i>Show Help';
             } else {
                 helpPanel.style.display = 'none';
                 icon.className = 'fas fa-eye-slash me-1';
                 button.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Help';
             }
         }

         function toggleSettingsHelp() {
             const helpPanel = document.getElementById('settingsHelpPanel');
             const button = helpPanel.querySelector('button');
             const icon = button.querySelector('i');

             if (helpPanel.style.display === 'none') {
                 helpPanel.style.display = 'block';
                 icon.className = 'fas fa-eye me-1';
                 button.innerHTML = '<i class="fas fa-eye me-1"></i>Show Help';
             } else {
                 helpPanel.style.display = 'none';
                 icon.className = 'fas fa-eye-slash me-1';
                 button.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Help';
             }
         }

        // Initialize tooltips when page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize Bootstrap tooltips
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        });

        // Get entity description
        function getEntityDescription(entityType) {
            const descriptions = {
                'volunteer': 'Contact records with volunteer activities',
                'organization': 'Companies, schools, and institutions',
                'event': 'Volunteer events and activities',
                'student': 'Contact records for students',
                'teacher': 'Contact records for teachers',
                'school': 'Educational institutions',
                'district': 'School districts'
            };
            return descriptions[entityType] || 'Data entity';
        }

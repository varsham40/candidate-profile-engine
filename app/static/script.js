document.addEventListener('DOMContentLoaded', () => {
    
    // --- File State Storage ---
    const files = {
        pdf: null,
        csv: null,
        config: null
    };

    // --- File Drop Zones & Inputs ---
    const zones = [
        { id: 'pdfZone', inputId: 'pdf_file', type: 'pdf', acceptName: 'Resume PDF' },
        { id: 'csvZone', inputId: 'csv_file', type: 'csv', acceptName: 'Recruiter CSV' },
        { id: 'configZone', inputId: 'config_file', type: 'config', acceptName: 'Config JSON' }
    ];

    function formatBytes(bytes, decimals = 1) {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }

    zones.forEach(zoneObj => {
        const zone = document.getElementById(zoneObj.id);
        const input = document.getElementById(zoneObj.inputId);
        const nameSpan = zone.querySelector('.file-name');
        const statusSpan = zone.querySelector('.file-status');

        function handleFile(file) {
            if (file) {
                files[zoneObj.type] = file;
                nameSpan.textContent = file.name;
                statusSpan.textContent = `Verified ${formatBytes(file.size)}`;
                nameSpan.style.color = 'var(--accent-blue)';
            } else {
                files[zoneObj.type] = null;
                nameSpan.textContent = `Click to Attach ${zoneObj.acceptName}`;
                statusSpan.textContent = '';
                nameSpan.style.color = '';
            }
        }

        // Update name when file selected
        input.addEventListener('change', (e) => {
            handleFile(e.target.files[0]);
        });

        // Drag and drop events
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });

        zone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                input.files = e.dataTransfer.files;
                handleFile(e.dataTransfer.files[0]);
            }
        });
    });

    // --- Sidebar File Previews ---
    const modal = document.getElementById('previewModal');
    const closeBtn = document.getElementById('closePreviewBtn');
    const previewTitle = document.getElementById('previewTitle');
    const previewContainer = document.getElementById('previewContainer');

    // --- Toast Notification ---
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toastMsg');
    let toastTimeout;

    function showToast(msg) {
        toastMsg.textContent = msg;
        toast.classList.add('show');
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const type = item.getAttribute('data-preview');
            const file = files[type];

            if (!file) {
                showToast(`Please attach a ${type.toUpperCase()} file first to preview it.`);
                return;
            }

            previewTitle.textContent = `Preview: ${file.name}`;
            previewContainer.innerHTML = '';
            modal.style.display = 'flex';

            if (type === 'pdf') {
                const url = URL.createObjectURL(file);
                const iframe = document.createElement('iframe');
                iframe.src = url;
                previewContainer.appendChild(iframe);
            } else if (type === 'csv') {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const text = e.target.result;
                    const rows = text.split('\n');
                    let tableHTML = '<table class="csv-table">';
                    
                    function parseCSVLine(line) {
                        let result = [];
                        let current = '';
                        let inQuotes = false;
                        for (let i = 0; i < line.length; i++) {
                            const char = line[i];
                            if (char === '"') {
                                inQuotes = !inQuotes;
                            } else if (char === ',' && !inQuotes) {
                                result.push(current.trim());
                                current = '';
                            } else {
                                current += char;
                            }
                        }
                        result.push(current.trim());
                        return result;
                    }

                    rows.forEach((row, i) => {
                        if (!row.trim()) return;
                        const cols = parseCSVLine(row);
                        tableHTML += '<tr>';
                        cols.forEach(col => {
                            if (i === 0) tableHTML += `<th>${col}</th>`;
                            else tableHTML += `<td>${col}</td>`;
                        });
                        tableHTML += '</tr>';
                    });
                    tableHTML += '</table>';
                    previewContainer.innerHTML = tableHTML;
                };
                reader.readAsText(file);
            } else if (type === 'config') {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const text = e.target.result;
                    try {
                        const json = JSON.parse(text);
                        previewContainer.innerHTML = `<pre><code>${syntaxHighlight(JSON.stringify(json, null, 2))}</code></pre>`;
                    } catch (err) {
                        previewContainer.innerHTML = `<pre><code>${text}</code></pre>`;
                    }
                };
                reader.readAsText(file);
            }
        });
    });

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        previewContainer.innerHTML = '';
    });

    // --- Form Submission ---
    const form = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('span');
    const spinner = document.getElementById('spinner');
    const errorBox = document.getElementById('errorBox');
    const jsonOutput = document.getElementById('jsonOutput');
    let lastProfileData = null; // store last result for summary view

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const pdfFile = files.pdf;
        const csvFile = files.csv;
        const configFile = files.config;

        if (!pdfFile || !csvFile) {
            showError("Please upload both the Resume PDF and the Recruiter CSV.");
            return;
        }

        const formData = new FormData();
        formData.append('pdf_file', pdfFile);
        formData.append('csv_file', csvFile);
        if (configFile) {
            formData.append('config_file', configFile);
        }

        // Set Loading State
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        spinner.style.display = 'block';
        errorBox.style.display = 'none';
        jsonOutput.innerHTML = '<span style="color:#94A3B8;">Processing documents through engine...</span>';

        try {
            const response = await fetch('/transform-profile', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Server error occurred");
            }

            // Render Output
            lastProfileData = data;
            jsonOutput.innerHTML = syntaxHighlight(JSON.stringify(data, null, 2));

        } catch (err) {
            showError(`Engine Error: ${err.message}`);
            jsonOutput.innerHTML = '<span style="color:#EF4444;">Process failed.</span>';
        } finally {
            // Restore UI State
            submitBtn.disabled = false;
            btnText.style.display = 'block';
            spinner.style.display = 'none';
        }
    });

    function showError(msg) {
        errorBox.textContent = msg;
        errorBox.style.display = 'block';
    }

    // --- Simple JSON Syntax Highlighter ---
    function syntaxHighlight(json) {
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
    }

    // --- Copy JSON Functionality ---
    const copyBtn = document.querySelector('.copy-btn');
    copyBtn.addEventListener('click', () => {
        // We get the raw text content from the pre/code block
        const textToCopy = jsonOutput.innerText || jsonOutput.textContent;
        if (textToCopy && !textToCopy.includes("Processing documents")) {
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'COPIED!';
                copyBtn.style.color = 'var(--success)';
                copyBtn.style.borderColor = 'var(--success)';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.style.color = '';
                    copyBtn.style.borderColor = '';
                }, 2000);
            }).catch(err => {
                showToast("Failed to copy text: " + err);
            });
        }
    });

    // --- Summary View ---
    const summaryModal = document.getElementById('summaryModal');
    const summaryContainer = document.getElementById('summaryContainer');
    const closeSummaryBtn = document.getElementById('closeSummaryBtn');
    const summaryViewBtn = document.getElementById('summaryViewBtn');

    summaryViewBtn.addEventListener('click', () => {
        if (!lastProfileData) {
            showToast('Please compile a profile first before viewing the summary.');
            return;
        }
        renderSummary(lastProfileData);
        summaryModal.style.display = 'flex';
    });

    closeSummaryBtn.addEventListener('click', () => {
        summaryModal.style.display = 'none';
    });

    function renderSummary(data) {
        // Handle both standard output (canonical_profile) and projected config output (root data)
        const profile = data?.data?.canonical_profile || data?.data;
        if (!profile) {
            summaryContainer.innerHTML = '<p style="color:#94A3B8;">No profile data found.</p>';
            return;
        }

        const getValue = (field) => {
            if (!field) return null;
            if (typeof field === 'object' && 'value' in field) return field.value;
            return field;
        };

        const getConf = (field) => {
            if (field && typeof field === 'object' && 'confidence' in field)
                return Math.round(field.confidence * 100);
            return null;
        };

        const confBadge = (field) => {
            const c = getConf(field);
            if (c === null) return '';
            const color = c >= 85 ? '#22C55E' : c >= 70 ? '#F59E0B' : '#EF4444';
            return `<span class="summary-conf-badge" style="background:${color}22;color:${color};border:1px solid ${color}55;">${c}% confidence</span>`;
        };

        const renderList = (val) => {
            if (!val || !Array.isArray(val) || val.length === 0) return '<em style="color:#64748B">—</em>';
            return val.map(v => `<span class="summary-tag">${v}</span>`).join(' ');
        };

        const renderExpEdu = (items) => {
            if (!items || !Array.isArray(items) || items.length === 0)
                return '<em style="color:#64748B">—</em>';
            return items.map(item => {
                const title = item.title || item.degree || item.institution || 'Entry';
                const sub = item.company || item.institution || '';
                const dates = [item.start_date, item.end_date].filter(Boolean).join(' → ');
                return `<div class="summary-exp-item">
                    <div class="summary-exp-header">
                        <strong>${title}</strong>
                        ${dates ? `<span class="summary-date">${dates}</span>` : ''}
                    </div>
                    ${sub ? `<div class="summary-exp-sub">@ ${sub}</div>` : ''}
                </div>`;
            }).join('');
        };

        const name = getValue(profile.full_name) || getValue(profile.name) || getValue(profile.candidate_name) || 'Unknown Candidate';
        const emails = getValue(profile.emails) || getValue(profile.email) || getValue(profile.candidate_email);
        const phones = getValue(profile.phones) || getValue(profile.phone);
        const location = getValue(profile.location);
        const primarySkills = getValue(profile.primary_skills) || getValue(profile.skills);
        const secondarySkills = getValue(profile.secondary_skills);
        const experience = getValue(profile.experience);
        const education = getValue(profile.education);
        const warnings = data?.data?.metadata?.warnings || profile.metadata?.warnings || [];

        summaryContainer.innerHTML = `
            <div style="width: 100%; display: flex; flex-direction: column;">
                <div class="summary-hero">
                    <div class="summary-avatar">${name.charAt(0).toUpperCase()}</div>
                    <div class="summary-hero-info">
                        <h2 class="summary-name">${name}</h2>
                        ${confBadge(profile.full_name || profile.name || profile.candidate_name)}
                    </div>
                </div>

                <div class="summary-grid">
                    <div class="summary-card">
                        <h3 class="summary-card-title">📞 Contact Information</h3>
                        <div class="summary-row">
                            <span class="summary-label">Email</span>
                            <span class="summary-value">${Array.isArray(emails) ? emails.join(', ') : (emails || '—')}</span>
                            ${confBadge(profile.emails || profile.email || profile.candidate_email)}
                        </div>
                        <div class="summary-row">
                            <span class="summary-label">Phone</span>
                            <span class="summary-value">${Array.isArray(phones) ? phones.join(', ') : (phones || '—')}</span>
                            ${confBadge(profile.phones || profile.phone)}
                        </div>
                        <div class="summary-row">
                            <span class="summary-label">Location</span>
                            <span class="summary-value">${location || '—'}</span>
                            ${confBadge(profile.location)}
                        </div>
                    </div>

                    <div class="summary-card">
                        <div class="summary-card-header">
                            <h3 class="summary-card-title">💡 Primary Skills</h3>
                            ${confBadge(profile.primary_skills || profile.skills)}
                        </div>
                        <div class="summary-tags">${renderList(primarySkills)}</div>
                    </div>

                    <div class="summary-card">
                        <div class="summary-card-header">
                            <h3 class="summary-card-title">🔧 Secondary Skills</h3>
                            ${confBadge(profile.secondary_skills)}
                        </div>
                        <div class="summary-tags">${renderList(secondarySkills)}</div>
                    </div>

                    <div class="summary-card full-width">
                        <div class="summary-card-header">
                            <h3 class="summary-card-title">💼 Work Experience</h3>
                            ${confBadge(profile.experience)}
                        </div>
                        <div class="summary-list-container">
                            ${renderExpEdu(experience)}
                        </div>
                    </div>

                    <div class="summary-card full-width">
                        <div class="summary-card-header">
                            <h3 class="summary-card-title">🎓 Education</h3>
                            ${confBadge(profile.education)}
                        </div>
                        <div class="summary-list-container">
                            ${renderExpEdu(education)}
                        </div>
                    </div>

                    ${warnings.length > 0 ? `
                    <div class="summary-card full-width summary-warnings">
                        <h3 class="summary-card-title">⚠️ Validation Warnings</h3>
                        <div class="summary-list-container">
                            ${warnings.map(w => `<div class="summary-warning-item">${w}</div>`).join('')}
                        </div>
                    </div>` : ''}
                </div>
            </div>
        `;
    }

});

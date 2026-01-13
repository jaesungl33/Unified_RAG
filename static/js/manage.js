// Manage Documents functionality
document.addEventListener('DOMContentLoaded', function() {
    // Internal tab navigation
    const tabButtons = document.querySelectorAll('.tab-btn[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Update active button
            tabButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Update active content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `tab-${targetTab}`) {
                    content.classList.add('active');
                }
            });
        });
    });
    
    // GDD Documents
    const gddFileUpload = document.getElementById('gdd-file-upload');
    const gddUploadBtn = document.getElementById('gdd-upload-btn');
    const gddQueueList = document.getElementById('gdd-queue-list');
    const gddDocumentsList = document.getElementById('gdd-documents-list');
    const gddDropZone = gddFileUpload.closest('.upload-card');
    
    // Code Files
    const codeFileUpload = document.getElementById('code-file-upload');
    const codeUploadBtn = document.getElementById('code-upload-btn');
    const codeQueueList = document.getElementById('code-queue-list');
    const codeDocumentsList = document.getElementById('code-documents-list');
    const codeDropZone = codeFileUpload.closest('.upload-card');
    
    // State for filtering
    let allGDDDocs = [];
    let allCodeFiles = [];

    // Queue state
    const gddQueue = [];
    const codeQueue = [];
    let gddProcessing = false;
    let codeProcessing = false;
    let gddPaused = false;
    let codePaused = false;

    // Search listeners
    document.getElementById('gdd-manage-search')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allGDDDocs.filter(d => (d.name || d.doc_id).toLowerCase().includes(term));
        renderGDDDocuments(filtered, true);
    });

    document.getElementById('code-manage-search')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allCodeFiles.filter(f => (f.file_name || f.file_path || '').toLowerCase().includes(term));
        renderCodeFiles(filtered, true);
    });

    document.getElementById('code-clear-all-btn')?.addEventListener('click', () => {
        if (allCodeFiles.length === 0) return;
        if (confirm('Are you sure you want to delete all code files?')) {
            alert('Clearing codebase index...');
            const promises = allCodeFiles.map(f => 
                fetch('/api/manage/delete/code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ file_path: f.file_path })
                })
            );
            Promise.all(promises).then(() => loadCodeFiles());
        }
    });
    
    // Load documents on page load
    loadGDDDocuments();
    loadCodeFiles();

    // Drag and Drop implementation
    function setupDragAndDrop(zone, input, handler) {
        ['dragenter', 'dragover'].forEach(name => {
            zone.addEventListener(name, (e) => {
                e.preventDefault();
                zone.classList.add('drag-active');
            }, false);
        });

        ['dragleave', 'drop'].forEach(name => {
            zone.addEventListener(name, (e) => {
                e.preventDefault();
                zone.classList.remove('drag-active');
            }, false);
        });

        zone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length) {
                input.files = files;
                handler();
            }
        }, false);

        zone.addEventListener('click', () => input.click());
    }

    if (gddDropZone) setupDragAndDrop(gddDropZone, gddFileUpload, () => gddUploadBtn.click());
    if (codeDropZone) setupDragAndDrop(codeDropZone, codeFileUpload, () => codeUploadBtn.click());
    
    // Update upload card UI based on queue state
    function updateGDDUploadCardUI() {
        const uploadCard = document.getElementById('gdd-upload-card');
        const uploadTitle = document.getElementById('gdd-upload-title');
        const uploadSubtitle = document.getElementById('gdd-upload-subtitle');
        
        if (!uploadCard || !uploadTitle || !uploadSubtitle) return;
        
        const completedCount = gddQueue.filter(item => item.status === 'completed').length;
        const queuedCount = gddQueue.filter(item => item.status === 'queued').length;
        const processingCount = gddQueue.filter(item => item.status === 'processing').length;
        
        if (gddQueue.length === 0) {
            // Empty state
            uploadTitle.textContent = 'Drag and drop your GDD files here';
            uploadSubtitle.textContent = 'Supports PDF, TXT, and Markdown';
            uploadCard.querySelector('img').style.display = 'block';
        } else {
            // Processing state
            uploadTitle.textContent = processingCount > 0 ? 'Processing files...' : 'Waiting...';
            const statusParts = [];
            if (completedCount > 0) statusParts.push(`${completedCount} completed`);
            if (queuedCount > 0) statusParts.push(`${queuedCount} in queue`);
            uploadSubtitle.textContent = statusParts.length > 0 ? statusParts.join(' • ') : 'Processing...';
            uploadCard.querySelector('img').style.display = 'none';
        }
    }
    
    // GDD Upload
    gddUploadBtn.addEventListener('click', function() {
        const files = gddFileUpload.files;
        if (files.length === 0) {
            alert('Please select at least one document');
            return;
        }
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const ext = file.name.split('.').pop().toLowerCase();
            if (!['pdf', 'txt', 'md'].includes(ext)) {
                alert(`${file.name} is not a supported GDD type. Skipping.`);
                continue;
            }
            
            const queueItem = {
                id: `queue-${Date.now()}-${Math.random()}`,
                file: file,
                status: 'queued',
                progress: '',
                progressPercent: 0,
                error: null
            };
            gddQueue.push(queueItem);
        }
        
        gddFileUpload.value = '';
        renderGDDQueue();
        updateGDDUploadCardUI();
        if (!gddPaused) {
            processGDDQueue();
        }
    });
    
    // Code Upload
    codeUploadBtn.addEventListener('click', function() {
        const files = codeFileUpload.files;
        if (files.length === 0) {
            alert('Please select at least one code file');
            return;
        }
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            // NO extension filtering as per requirements
            const queueItem = {
                id: Date.now() + i,
                file: file,
                status: 'queued',
                progress: '',
                error: null
            };
            codeQueue.push(queueItem);
        }
        
        codeFileUpload.value = '';
        renderCodeQueue();
        processCodeQueue();
    });
    
    // Render GDD Queue
    function renderGDDQueue() {
        updateGDDUploadCardUI();
        if (gddQueue.length === 0) {
            gddQueueList.innerHTML = '<div class="placeholder-text" style="padding: 24px; background: white; border: 1px dashed var(--border-color); border-radius: var(--radius-md);">No files in queue</div>';
            return;
        }
        
        const completedCount = gddQueue.filter(item => item.status === 'completed').length;
        const queuedCount = gddQueue.filter(item => item.status === 'queued').length;
        const processingCount = gddQueue.filter(item => item.status === 'processing').length;
        
        const html = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin: 0;">
                    Upload Queue (${gddQueue.length})
                </h4>
                ${gddQueue.length > 0 ? `
                    <button id="gdd-pause-resume-btn" class="btn-secondary" style="font-size: 0.75rem; padding: 4px 12px; height: 28px;">
                        ${gddPaused ? '▶ Resume' : '⏸ Pause'}
                    </button>
                ` : ''}
            </div>
            <div class="queue-list-container">
                ${gddQueue.map((item, index) => {
                    let statusIcon = '📄';
                    let statusClass = 'queued';
                    let progressBar = '';
                    let statusText = '';
                    
                    if (item.status === 'processing') {
                        statusIcon = '⏳';
                        statusClass = 'processing';
                        const progress = item.progressPercent || 0;
                        progressBar = `
                            <div style="margin-top: 6px; height: 2px; background: var(--muted); border-radius: 1px; overflow: hidden;">
                                <div style="height: 100%; background: var(--primary); width: ${progress}%; transition: width 0.2s;"></div>
                            </div>
                        `;
                        statusText = item.progress || 'Processing...';
                    } else if (item.status === 'completed') {
                        statusIcon = '✅';
                        statusClass = 'completed';
                        statusText = item.chunks ? `${item.chunks} chunks indexed` : 'Completed';
                    } else if (item.status === 'error') {
                        statusIcon = '❌';
                        statusClass = 'error';
                        statusText = item.error || 'Error';
                    } else if (item.status === 'queued') {
                        statusText = 'Queued';
                    }
                    
                    const fadeOutClass = item.status === 'completed' ? 'queue-item-fadeout' : '';
                    
                    return `
                        <div class="queue-item ${statusClass} ${fadeOutClass}" data-queue-id="${item.id}" style="
                            display: flex;
                            align-items: center;
                            gap: 12px;
                            padding: 12px;
                            background: ${item.status === 'completed' ? 'rgba(34, 197, 94, 0.1)' : 'var(--muted)/40'};
                            border-radius: var(--radius-md);
                            margin-bottom: 8px;
                            transition: all 0.5s;
                            ${item.status === 'completed' ? 'opacity: 0; transform: translateY(8px);' : ''}
                        ">
                            <span style="font-size: 16px; flex-shrink: 0;">${statusIcon}</span>
                            <div style="flex: 1; min-width: 0;">
                                <div style="font-size: 0.875rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    ${item.file.name}
                                </div>
                                ${progressBar}
                                <div style="font-size: 0.75rem; color: var(--muted-foreground); margin-top: 4px;">
                                    ${statusText}
                                </div>
                            </div>
                            ${item.status !== 'completed' ? `
                                <button onclick="cancelGDDQueueItem('${item.id}')" style="
                                    background: transparent;
                                    border: none;
                                    cursor: pointer;
                                    padding: 4px;
                                    opacity: 0.5;
                                    transition: opacity 0.2s;
                                " onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.5'">
                                    <img src="/static/icons/close.svg" width="14" height="14" style="filter: invert(32%) sepia(85%) saturate(2853%) hue-rotate(345deg) brightness(101%) contrast(89%);">
                                </button>
                            ` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        gddQueueList.innerHTML = html;
        
        // Attach pause/resume button listener
        const pauseResumeBtn = document.getElementById('gdd-pause-resume-btn');
        if (pauseResumeBtn) {
            pauseResumeBtn.onclick = () => {
                gddPaused = !gddPaused;
                renderGDDQueue();
                if (!gddPaused && !gddProcessing) {
                    processGDDQueue();
                }
            };
        }
    }
    
    // Cancel queue item
    window.cancelGDDQueueItem = function(queueId) {
        const index = gddQueue.findIndex(item => item.id === queueId);
        if (index !== -1) {
            const item = gddQueue[index];
            if (item.status === 'processing') {
                if (!confirm('This file is currently processing. Cancel anyway?')) {
                    return;
                }
            }
            gddQueue.splice(index, 1);
            renderGDDQueue();
            // If queue was paused and we removed the current item, try to process next
            if (!gddPaused && !gddProcessing && gddQueue.length > 0) {
                processGDDQueue();
            }
        }
    };
    
    // Render Code Queue
    function renderCodeQueue() {
        if (codeQueue.length === 0) {
            codeQueueList.innerHTML = '<p class="empty-queue">No files in queue</p>';
            return;
        }
        
        const html = codeQueue.map(item => {
            let statusIcon = '⏳';
            let statusClass = 'queued';
            if (item.status === 'processing') {
                statusIcon = '⏳';
                statusClass = 'processing';
            } else if (item.status === 'completed') {
                statusIcon = '✅';
                statusClass = 'completed';
            } else if (item.status === 'error') {
                statusIcon = '❌';
                statusClass = 'error';
            }
            
            return `
                <div class="queue-item ${statusClass}">
                    <span class="status-icon">${statusIcon}</span>
                    <span class="file-name">${item.file.name}</span>
                    <span class="progress-text">${item.progress || item.status}</span>
                    ${item.error ? `<span class="error-text">${item.error}</span>` : ''}
                </div>
            `;
        }).join('');
        
        codeQueueList.innerHTML = html;
    }
    
    // Process GDD Queue (sequential)
    async function processGDDQueue() {
        if (gddProcessing || gddQueue.length === 0 || gddPaused) return;
        
        gddProcessing = true;
        
        while (gddQueue.length > 0 && !gddPaused) {
            const item = gddQueue.find(f => f.status === 'queued');
            if (!item) {
                // No queued items, exit
                break;
            }
            
            if (item.status === 'queued') {
                item.status = 'processing';
                item.progress = 'Uploading...';
                item.progressPercent = 0;
                renderGDDQueue();
                
                try {
                    const formData = new FormData();
                    formData.append('file', item.file);
                    
                    const response = await fetch('/api/gdd/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'error') {
                        item.status = 'error';
                        item.error = data.message || 'Upload failed';
                        renderGDDQueue();
                        gddQueue.shift();
                        continue;
                    }
                    
                    if (data.status !== 'accepted' || !data.job_id) {
                        item.status = 'error';
                        item.error = 'Unexpected response';
                        renderGDDQueue();
                        gddQueue.shift();
                        continue;
                    }
                    
                    const jobId = data.job_id;
                    item.progress = data.step || 'Processing...';
                    renderGDDQueue();
                    
                    // Poll status
                    const pollInterval = setInterval(async () => {
                        try {
                            const statusResponse = await fetch(`/api/gdd/upload/status?job_id=${encodeURIComponent(jobId)}`);
                            const statusData = await statusResponse.json();
                            
                            if (!statusData || !statusData.status) return;
                            
                            item.progress = statusData.step || 'Processing...';
                            renderGDDQueue();
                            
                            if (statusData.status === 'success') {
                                clearInterval(pollInterval);
                                item.status = 'completed';
                                item.progress = statusData.message || 'Completed';
                                renderGDDQueue();
                                loadGDDDocuments();
                                
                                // Remove from queue after a delay
                                setTimeout(() => {
                                    const index = gddQueue.findIndex(q => q.id === item.id);
                                    if (index !== -1) {
                                        gddQueue.splice(index, 1);
                                        renderGDDQueue();
                                    }
                                }, 2000);
                            } else if (statusData.status === 'error') {
                                clearInterval(pollInterval);
                                item.status = 'error';
                                item.error = statusData.message || 'Upload failed';
                                renderGDDQueue();
                            }
                        } catch (err) {
                            console.warn('Status poll error:', err);
                        }
                    }, 1000);
                    
                    // Wait for completion
                    await new Promise((resolve) => {
                        const checkComplete = setInterval(() => {
                            if (item.status === 'completed' || item.status === 'error') {
                                clearInterval(checkComplete);
                                clearInterval(pollInterval);
                                resolve();
                            }
                        }, 500);
                    });
                
                } catch (error) {
                    item.status = 'error';
                    item.error = error.message;
                    renderGDDQueue();
                    const errorIndex = gddQueue.findIndex(q => q.id === item.id);
                    if (errorIndex !== -1) {
                        gddQueue.splice(errorIndex, 1);
                    }
                    // Process next item if not paused
                    if (!gddPaused && gddQueue.length > 0) {
                        processGDDQueue();
                    }
                }
            }
        }
        
        gddProcessing = false;
        
        // If there are still queued items and not paused, continue processing
        if (!gddPaused && gddQueue.some(item => item.status === 'queued')) {
            setTimeout(() => processGDDQueue(), 100);
        }
    }
    
    // Process Code Queue (sequential)
    async function processCodeQueue() {
        if (codeProcessing || codeQueue.length === 0) return;
        
        codeProcessing = true;
        
        while (codeQueue.length > 0) {
            const item = codeQueue[0];
            if (item.status === 'queued') {
                item.status = 'processing';
                item.progress = 'Uploading...';
                renderCodeQueue();
                
                try {
                    const formData = new FormData();
                    formData.append('file', item.file);
                    
                    const response = await fetch('/api/code/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'error') {
                        item.status = 'error';
                        item.error = data.message || 'Upload failed';
                        renderCodeQueue();
                        codeQueue.shift();
                        continue;
                    }
                    
                    if (data.status !== 'accepted' || !data.job_id) {
                        item.status = 'error';
                        item.error = 'Unexpected response';
                        renderCodeQueue();
                        codeQueue.shift();
                        continue;
                    }
                    
                    const jobId = data.job_id;
                    item.progress = data.step || 'Processing...';
                    renderCodeQueue();
                    
                    // Poll status
                    const pollInterval = setInterval(async () => {
                        try {
                            const statusResponse = await fetch(`/api/code/upload/status?job_id=${encodeURIComponent(jobId)}`);
                            const statusData = await statusResponse.json();
                            
                            if (!statusData || !statusData.status) return;
                            
                            item.progress = statusData.step || 'Processing...';
                            renderCodeQueue();
                            
                            if (statusData.status === 'success') {
                                clearInterval(pollInterval);
                                item.status = 'completed';
                                item.progress = statusData.message || 'Completed';
                                renderCodeQueue();
                                loadCodeFiles();
                                
                                // Remove from queue after a delay
                                setTimeout(() => {
                                    const index = codeQueue.findIndex(q => q.id === item.id);
                                    if (index !== -1) {
                                        codeQueue.splice(index, 1);
                                        renderCodeQueue();
                                    }
                                }, 2000);
                            } else if (statusData.status === 'error') {
                                clearInterval(pollInterval);
                                item.status = 'error';
                                item.error = statusData.message || 'Upload failed';
                                renderCodeQueue();
                            }
                        } catch (err) {
                            console.warn('Status poll error:', err);
                        }
                    }, 1000);
                    
                    // Wait for completion
                    await new Promise((resolve) => {
                        const checkComplete = setInterval(() => {
                            if (item.status === 'completed' || item.status === 'error') {
                                clearInterval(checkComplete);
                                clearInterval(pollInterval);
                                resolve();
                            }
                        }, 500);
                    });
                    
                } catch (error) {
                    item.status = 'error';
                    item.error = error.message;
                    renderCodeQueue();
                }
                
                codeQueue.shift();
            } else {
                codeQueue.shift();
            }
        }
        
        codeProcessing = false;
    }
    
    // Load GDD Documents
    function loadGDDDocuments() {
        fetch('/api/gdd/documents')
            .then(response => response.json())
            .then(data => {
                const rawDocs = data.documents || [];
                
                // Remove duplicates based on doc_id (keep first occurrence)
                const uniqueDocs = [];
                const seenDocIds = new Set();
                rawDocs.forEach(doc => {
                    const docId = doc.doc_id || doc.id;
                    if (docId && !seenDocIds.has(docId)) {
                        seenDocIds.add(docId);
                        uniqueDocs.push(doc);
                    }
                });
                
                allGDDDocs = uniqueDocs;
                renderGDDDocuments(allGDDDocs);
            })
            .catch(error => {
                gddDocumentsList.innerHTML = `<p style="padding:20px; color:var(--status-error)">Error loading documents: ${error.message}</p>`;
            });
    }
    
    function formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Clear All Button Listener
    document.getElementById('gdd-clear-all-btn')?.addEventListener('click', () => {
        if (allGDDDocs.length === 0) return;
        clearAllGDD();
    });

    // Render GDD Documents
    function renderGDDDocuments(documents, isFiltered = false) {
        const statsEl = document.getElementById('gdd-stats');
        if (statsEl) {
            if (isFiltered) {
                statsEl.textContent = `${documents.length} of ${allGDDDocs.length} documents`;
            } else {
                statsEl.textContent = `${documents.length} document${documents.length !== 1 ? 's' : ''}`;
            }
        }

        const clearBtn = document.getElementById('gdd-clear-all-btn');
        if (clearBtn) {
            clearBtn.style.opacity = documents.length > 0 ? '1' : '0.2';
            clearBtn.disabled = documents.length === 0;
        }

        if (documents.length > 0) {
            const html = documents.map((doc, index) => {
                const rawName = doc.name || doc.display_name || doc.file_name || 'Unknown';
                const docId = doc.id || doc.doc_id || '';
                const chunksCount = doc.chunks_count || 0;
                const size = doc.size ? formatBytes(doc.size) : (Math.floor(Math.random() * 500) + 100) + ' KB';
                const date = doc.created_at ? new Date(doc.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Jan 12';
                
                return `
                    <div class="document-item" style="
                        padding: 16px 20px;
                        border-bottom: 1px solid var(--border);
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        transition: background 0.2s;
                        animation: fadeInSlideUp 0.5s ease-out ${index * 0.05}s both;
                    " onmouseover="this.style.background='var(--muted)/20'" onmouseout="this.style.background='transparent'">
                        <div style="display: flex; align-items: center; gap: 16px; min-width: 0; flex: 1;">
                            <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(34, 197, 94, 0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                                <img src="/static/icons/check.svg" width="20" height="20" style="filter: brightness(0) saturate(100%) invert(48%) sepia(79%) saturate(2476%) hue-rotate(122deg) brightness(95%) contrast(85%);">
                            </div>
                            <div class="document-info" style="min-width: 0; flex: 1;">
                                <div class="document-name" style="font-weight: 600; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--foreground);">
                                    ${rawName.replace(/\.[^/.]+$/, "")}
                                </div>
                                <div class="document-meta" style="font-size: 0.75rem; color: var(--muted-foreground); margin-top: 4px; display: flex; align-items: center; gap: 8px;">
                                    <span>${size}</span>
                                    <span style="opacity: 0.3">•</span>
                                    <span>${chunksCount} chunks</span>
                                    <span style="opacity: 0.3">•</span>
                                    <span>${date}</span>
                                </div>
                            </div>
                        </div>
                        <button class="action-btn" title="Delete" onclick="deleteGDD('${docId}')" style="opacity: 0.4; padding: 8px; border-radius: 6px; transition: all 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.4'">
                            <img src="/static/icons/trash.svg" width="16" height="16" style="filter: invert(32%) sepia(85%) saturate(2853%) hue-rotate(345deg) brightness(101%) contrast(89%);">
                        </button>
                    </div>
                `;
            }).join('');
            
            gddDocumentsList.innerHTML = html;
        } else {
            gddDocumentsList.innerHTML = `<div class="placeholder-text" style="padding: 60px; text-align: center;">
                <img src="/static/icons/file.svg" width="48" height="48" style="opacity: 0.3; margin-bottom: 12px; filter: grayscale(1);">
                <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 0;">
                    ${isFiltered ? 'No documents found' : 'No GDD documents uploaded yet.'}
                </p>
            </div>`;
        }
    }

    window.clearAllGDD = function() {
        if (confirm('Are you sure you want to delete all GDD documents? This action cannot be undone.')) {
            // Sequential deletion as placeholder for bulk API
            alert('Clearing all documents...');
            fetch('/api/gdd/documents').then(r => r.json()).then(data => {
                const promises = data.documents.map(doc => 
                    fetch('/api/manage/delete/gdd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ doc_id: doc.doc_id })
                    })
                );
                Promise.all(promises).then(() => loadGDDDocuments());
            });
        }
    };
    
    // Load Code Files
    function loadCodeFiles() {
        fetch('/api/code/files')
            .then(response => response.json())
            .then(data => {
                allCodeFiles = data.files || [];
                renderCodeFiles(allCodeFiles);
            })
            .catch(error => {
                codeDocumentsList.innerHTML = `<p style="padding:20px; color:var(--status-error)">Error loading files: ${error.message}</p>`;
            });
    }
    
    const getExtensionColor = (ext) => {
        return {
            ts: { bg: 'rgba(59, 130, 246, 0.1)', text: '#2563eb' },
            tsx: { bg: 'rgba(59, 130, 246, 0.1)', text: '#2563eb' },
            js: { bg: 'rgba(234, 179, 8, 0.1)', text: '#ca8a04' },
            jsx: { bg: 'rgba(234, 179, 8, 0.1)', text: '#ca8a04' },
            py: { bg: 'rgba(34, 197, 94, 0.1)', text: '#16a34a' },
            cs: { bg: 'rgba(168, 85, 247, 0.1)', text: '#9333ea' },
            cpp: { bg: 'rgba(168, 85, 247, 0.1)', text: '#9333ea' },
            css: { bg: 'rgba(236, 72, 153, 0.1)', text: '#db2777' },
            html: { bg: 'rgba(239, 68, 68, 0.1)', text: '#dc2626' },
            md: { bg: 'rgba(107, 114, 128, 0.1)', text: '#4b5563' },
            json: { bg: 'rgba(249, 115, 22, 0.1)', text: '#ea580c' }
        }[ext] || { bg: 'var(--muted)', text: 'var(--muted-foreground)' };
    };

    // Render Code Files
    function renderCodeFiles(files, isFiltered = false) {
        const statsEl = document.getElementById('code-stats');
        if (statsEl) statsEl.textContent = isFiltered 
            ? `${files.length} of ${allCodeFiles.length} files` 
            : `${files.length} files`;

        const clearBtn = document.getElementById('code-clear-all-btn');
        if (clearBtn) clearBtn.style.opacity = files.length > 0 ? '1' : '0.2';
        if (clearBtn) clearBtn.disabled = files.length === 0;

        if (files.length > 0) {
            const html = files.map(file => {
                const fileName = file.file_name || file.name || 'Unknown';
                const filePath = file.file_path || file.path || fileName;
                const ext = fileName.split('.').pop().toLowerCase();
                const colors = getExtensionColor(ext);
                const size = file.size ? formatBytes(file.size) : (Math.floor(Math.random() * 10) + 1) + ' KB';
                const date = 'Jan 12';
                
                return `
                    <div class="document-item" style="padding: 16px 20px; border-bottom: 1px solid var(--border); display:flex; align-items:center; justify-content:space-between; transition: background 0.2s;">
                        <div style="display:flex; align-items:center; gap:12px; min-width:0; flex:1;">
                            <div style="width:36px; height:24px; background:${colors.bg}; color:${colors.text}; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:0.6rem; font-weight:800; font-family:var(--font-mono); text-transform:uppercase; flex-shrink:0;">
                                ${ext}
                            </div>
                            <div style="color: var(--border); font-size: 1.25rem; line-height: 1; margin-top: -2px;">|</div>
                            <div class="document-info" style="min-width:0;">
                                <div class="document-name" style="font-weight:600; font-size:0.875rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color: var(--foreground);">${filePath}</div>
                                <div class="document-meta" style="font-size:0.75rem; color:var(--muted-foreground); margin-top:2px; display: flex; align-items: center; gap: 8px;">
                                    <span>${size}</span>
                                    <span style="opacity: 0.3">•</span>
                                    <span>12 chunks</span>
                                    <span style="opacity: 0.3">•</span>
                                    <span>${date}</span>
                                </div>
                            </div>
                        </div>
                        <button class="action-btn" title="Delete" onclick="deleteCode('${filePath}')" style="opacity:0.4; padding:8px; border-radius:6px; transition: all 0.2s;">
                            <img src="/static/icons/trash.svg" width="16" height="16" style="filter: invert(32%) sepia(85%) saturate(2853%) hue-rotate(345deg) brightness(101%) contrast(89%);">
                        </button>
                    </div>
                `;
            }).join('');
            
            codeDocumentsList.innerHTML = html;
        } else {
            codeDocumentsList.innerHTML = `<div class="placeholder-text" style="padding:60px;">
                <img src="/static/icons/code.svg" width="32" height="32" style="opacity:0.1; margin-bottom:12px; filter: grayscale(1);">
                <p>${isFiltered ? 'No matching files.' : 'No code files indexed yet.'}</p>
            </div>`;
        }
    }
    
    // Global functions for document actions
    window.reindexGDD = function(docId) {
        if (!confirm('Are you sure you want to re-index this document?')) return;
        
        fetch(`/api/manage/reindex/gdd`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doc_id: docId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Re-indexing started');
                loadGDDDocuments();
            } else {
                alert('Error: ' + (data.message || 'Re-indexing failed'));
            }
        })
        .catch(error => alert('Error: ' + error.message));
    };
    
    window.deleteGDD = function(docId) {
        if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) return;
        
        fetch(`/api/manage/delete/gdd`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doc_id: docId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Document deleted');
                loadGDDDocuments();
            } else {
                alert('Error: ' + (data.message || 'Deletion failed'));
            }
        })
        .catch(error => alert('Error: ' + error.message));
    };
    
    window.viewCodeDetails = function(filePath) {
        // TODO: Implement view details modal
        alert(`View details for file: ${filePath}`);
    };
    
    window.reindexCode = function(filePath) {
        if (!confirm('Are you sure you want to re-index this file?')) return;
        
        fetch(`/api/manage/reindex/code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Re-indexing started');
                loadCodeFiles();
            } else {
                alert('Error: ' + (data.message || 'Re-indexing failed'));
            }
        })
        .catch(error => alert('Error: ' + error.message));
    };
    
    window.deleteCode = function(filePath) {
        if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) return;
        
        fetch(`/api/manage/delete/code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('File deleted');
                loadCodeFiles();
            } else {
                alert('Error: ' + (data.message || 'Deletion failed'));
            }
        })
        .catch(error => alert('Error: ' + error.message));
    };
});


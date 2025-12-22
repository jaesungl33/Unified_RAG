// GDD RAG functionality
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const queryInput = document.getElementById('query-input');
    const sendBtn = document.getElementById('send-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const fileUpload = document.getElementById('file-upload');
    const uploadStatus = document.getElementById('upload-status');
    const documentsList = document.getElementById('documents-list');
    const documentSearch = document.getElementById('document-search');
    
    let selectedDocument = null; // Track selected document
    let allDocumentsData = null; // Store all documents data for filtering
    const CHAT_STORAGE_KEY = 'gdd_chat_history';
    
    // If this page load is a hard refresh, clear any persisted chat history
    try {
        const navEntries = performance.getEntriesByType('navigation');
        const navType = navEntries && navEntries.length > 0 ? navEntries[0].type : null;
        if (navType === 'reload') {
            localStorage.removeItem(CHAT_STORAGE_KEY);
        }
    } catch (e) {
        console.warn('Navigation type detection failed:', e);
    }
    
    // Load documents on page load
    loadDocuments();
    // Restore chat history
    loadChatHistory();
    
    // Search functionality
    documentSearch.addEventListener('input', function() {
        filterDocuments(this.value);
    });
    
    // Send query
    sendBtn.addEventListener('click', sendQuery);
    queryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendQuery();
        }
    });
    
    // Upload file
    uploadBtn.addEventListener('click', uploadFile);
    
    function sendQuery() {
        const query = queryInput.value.trim();
        if (!query) return;
        
        // Add user message
        addMessage(query, 'user');
        queryInput.value = '';
        
        // Show typing indicator
        const typingIndicator = addTypingIndicator();
        
        // Send to API with selected document
        fetch('/api/gdd/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                selected_doc: selectedDocument
            })
        })
        .then(response => response.json())
        .then(data => {
            removeTypingIndicator(typingIndicator);
            if (data.status === 'error') {
                addMessage('Error: ' + (data.response || data.error || 'Query failed'), 'bot');
            } else {
                // Support markdown-like formatting in response
                const response = data.response || 'No response received';
                addMessage(response, 'bot');
            }
        })
        .catch(error => {
            removeTypingIndicator(typingIndicator);
            addMessage('Error: ' + error.message, 'bot');
        });
    }
    
    function uploadFile() {
        const file = fileUpload.files[0];
        if (!file) {
            alert('Please select a file');
            return;
        }
        
        uploadStatus.style.display = 'block';
        uploadStatus.textContent = 'Uploading...';
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/api/gdd/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'error') {
                uploadStatus.textContent = 'Error: ' + (data.message || data.error || 'Upload failed');
                uploadStatus.style.color = '#d32f2f';
                uploadStatus.style.display = 'block';
            } else {
                uploadStatus.textContent = data.message || 'Upload successful';
                uploadStatus.style.color = '#2e7d32';
                uploadStatus.style.display = 'block';
                loadDocuments();
                // Clear file input
                fileUpload.value = '';
            }
        })
        .catch(error => {
            uploadStatus.textContent = 'Error: ' + error.message;
        });
    }
    
    function loadDocuments() {
        fetch('/api/gdd/documents')
            .then(response => response.json())
            .then(data => {
                // Store all documents data for filtering
                allDocumentsData = data;
                
                // Render documents (will apply current search filter)
                renderDocuments(data);
            })
            .catch(error => {
                console.error('Error loading documents:', error);
                documentsList.innerHTML = '<p style="font-size:0.85rem;color:#d32f2f;">Error loading documents.</p>';
            });
    }
    
    function renderDocuments(data) {
        documentsList.innerHTML = '';
        
        if (!data.documents || data.documents.length === 0) {
            documentsList.innerHTML = '<p style="font-size:0.85rem;color:#666;">No documents indexed yet. Upload a document to get started.</p>';
            return;
        }
        
        // Get current search term
        const searchTerm = documentSearch.value.toLowerCase().trim();
        
        // Create "All Documents" option (always show if no search or matches)
        if (!searchTerm || 'all documents'.includes(searchTerm)) {
            const allDocsItem = document.createElement('div');
            allDocsItem.className = 'document-item';
            if (!selectedDocument || selectedDocument === 'All Documents') {
                allDocsItem.classList.add('selected');
            }
            allDocsItem.innerHTML = '<span class="name">All Documents</span>';
            allDocsItem.addEventListener('click', function() {
                selectDocument('All Documents', allDocsItem);
            });
            documentsList.appendChild(allDocsItem);
        }
        
        // Filter documents based on search term
        const filteredDocs = data.documents.filter(doc => {
            if (!searchTerm) return true;
            const displayName = (doc.name || doc.doc_id).toLowerCase();
            const docId = doc.doc_id.toLowerCase();
            return displayName.includes(searchTerm) || docId.includes(searchTerm);
        });
        
        if (filteredDocs.length === 0 && searchTerm) {
            documentsList.innerHTML = '<p style="font-size:0.85rem;color:#666;">No documents match your search.</p>';
            return;
        }
        
        // Group documents by derived category for nicer headings
        const groups = {};
        
        filteredDocs.forEach(doc => {
            const rawName = doc.name || doc.doc_id || 'Unknown';
            const info = parseDocumentName(rawName);
            const groupKey = info.groupLabel || '[Other]';
            
            if (!groups[groupKey]) {
                groups[groupKey] = [];
            }
            groups[groupKey].push({
                doc,
                displayName: info.displayTitle,
                rawName,
            });
        });
        
        // Sort group keys alphabetically
        const sortedGroupKeys = Object.keys(groups).sort((a, b) => a.localeCompare(b));
        
        sortedGroupKeys.forEach(groupKey => {
            const groupWrapper = document.createElement('div');
            groupWrapper.className = 'document-group';
            
            const heading = document.createElement('div');
            heading.className = 'document-group-title';
            heading.textContent = groupKey;
            groupWrapper.appendChild(heading);
            
            const docList = document.createElement('ul');
            docList.className = 'document-list';
            
            // Sort documents within group by display title
            groups[groupKey].sort((a, b) => a.displayName.localeCompare(b.displayName));
            
            groups[groupKey].forEach(entry => {
                const { doc, displayName, rawName } = entry;
                
                const docItem = document.createElement('li');
                docItem.className = 'document-item';
                
                const optionValue = data.options ? 
                    data.options.find(opt => opt.includes(rawName) || opt.includes(doc.doc_id)) : 
                    `${rawName} (${doc.doc_id})`;
                
                if (selectedDocument === optionValue) {
                    docItem.classList.add('selected');
                }
                
            docItem.innerHTML = `
                <span class="name">${displayName}</span>
            `;
                
                docItem.addEventListener('click', function() {
                    selectDocument(optionValue, docItem);
                });
                
                docList.appendChild(docItem);
            });
            
            groupWrapper.appendChild(docList);
            documentsList.appendChild(groupWrapper);
        });
    }
    
    function filterDocuments(searchTerm) {
        // Use cached data if available, otherwise reload
        if (allDocumentsData) {
            renderDocuments(allDocumentsData);
        } else {
            loadDocuments();
        }
    }
    
    function selectDocument(docValue, element) {
        // Remove selected class from all items
        document.querySelectorAll('.document-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Add selected class to clicked item
        element.classList.add('selected');
        
        // Update selected document
        selectedDocument = docValue === 'All Documents' ? null : docValue;
        
        // Update query input placeholder to show selected document
        if (docValue === 'All Documents' || !docValue) {
            queryInput.placeholder = 'Ask a question about the game design documents...';
        } else {
            const docName = docValue.split(' (')[0]; // Extract document name
            queryInput.placeholder = `Ask a question about "${docName}"...`;
        }
    }
    
    function addMessage(text, type, fromHistory) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        // Format text with code block support
        const formattedText = formatMessage(text);
        messageDiv.innerHTML = formattedText;
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Persist to localStorage unless loading from history
        if (!fromHistory) {
            saveMessageToHistory(text, type);
        }
    }
    
    function formatMessage(text) {
        if (!text) return '';
        
        // Escape HTML first
        let escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // Handle code blocks (```language\ncode\n``` or ```\ncode\n```)
        // Match with or without language specifier, with or without leading newline
        escaped = escaped.replace(/```(\w+)?\n?([\s\S]*?)```/g, function(match, lang, code) {
            // Preserve whitespace in code blocks - unescape for code content
            const codeContent = code
                .replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>');
            return `<pre><code class="code-block">${codeContent}</code></pre>`;
        });
        
        // Handle inline code (`code`) - but not inside code blocks
        // Split by code blocks first, then process each part
        const parts = escaped.split(/(<pre><code class="code-block">[\s\S]*?<\/code><\/pre>)/);
        for (let i = 0; i < parts.length; i++) {
            // Skip code blocks themselves
            if (parts[i].includes('<pre><code class="code-block">')) {
                continue;
            }
            // Process inline code in regular text
            parts[i] = parts[i].replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
        }
        escaped = parts.join('');
        
        // Handle bold (**text**)
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Skip italic formatting for now to avoid conflicts with bold
        
        // Convert newlines to <br> (but not inside code blocks)
        const parts2 = escaped.split(/(<pre><code class="code-block">[\s\S]*?<\/code><\/pre>)/);
        for (let i = 0; i < parts2.length; i++) {
            if (parts2[i].includes('<pre><code class="code-block">')) {
                continue;
            }
            parts2[i] = parts2[i].replace(/\n/g, '<br>');
        }
        escaped = parts2.join('');
        
        return escaped;
    }

    function saveMessageToHistory(text, type) {
        try {
            const existing = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || '[]');
            existing.push({
                type,
                text,
                ts: Date.now()
            });
            if (existing.length > 200) {
                existing.splice(0, existing.length - 200);
            }
            localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(existing));
        } catch (e) {
            console.error('Failed to save GDD chat history:', e);
        }
    }

    function loadChatHistory() {
        try {
            const raw = localStorage.getItem(CHAT_STORAGE_KEY);
            if (!raw) {
                return; // No history; keep default welcome message
            }
            const history = JSON.parse(raw);
            if (!Array.isArray(history) || history.length === 0) {
                return;
            }
            // Clear existing messages (including welcome)
            chatContainer.innerHTML = '';
            history.forEach(msg => {
                if (msg && typeof msg.text === 'string' && msg.type) {
                    addMessage(msg.text, msg.type, true);
                }
            });
        } catch (e) {
            console.error('Failed to load GDD chat history:', e);
        }
    }

    // Clear chat button
    const clearChatBtn = document.getElementById('clear-chat-btn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', function() {
            try {
                localStorage.removeItem(CHAT_STORAGE_KEY);
            } catch (e) {
                console.error('Failed to clear GDD chat history:', e);
            }
            // Restore welcome message
            chatContainer.innerHTML = '';
            const welcome = document.createElement('div');
            welcome.className = 'message bot-message';
            welcome.textContent = 'Welcome! Upload a document or select one from the sidebar to start querying.';
            chatContainer.appendChild(welcome);
        });
    }

    function parseDocumentName(rawName) {
        // Remove extension
        let base = rawName.replace(/\.[^/.]+$/, '');
        const parts = base.split('_').filter(p => p);
        
        let groupLabel = '[Other]';
        let displayTitle = base.replace(/_/g, ' ');
        
        if (parts.length >= 2) {
            const groupPart = toTitleCase(parts[0].replace(/-/g, ' '));
            
            // Tokens that belong to the second bracket (Tank War, UI, Module, Mode, etc.)
            const secondBracketTokens = ['ui', 'module', 'mode', 'tank', 'war'];
            const subTokens = [];
            
            for (let i = 1; i < parts.length; i++) {
                const token = parts[i];
                const lower = token.toLowerCase();
                if (secondBracketTokens.includes(lower)) {
                    subTokens.push(token);
                } else {
                    break;
                }
            }
            
            if (subTokens.length > 0) {
                const secondLabel = toTitleCase(subTokens.join(' ').replace(/-/g, ' '));
                groupLabel = `[${groupPart}][${secondLabel}]`;
                const remainder = parts.slice(1 + subTokens.length);
                if (remainder.length > 0) {
                    displayTitle = toTitleCase(remainder.join(' ').replace(/_/g, ' '));
                } else {
                    displayTitle = toTitleCase(base.replace(/_/g, ' '));
                }
            } else {
                groupLabel = `[${groupPart}]`;
                displayTitle = toTitleCase(parts.slice(1).join(' ').replace(/_/g, ' '));
            }
        } else {
            displayTitle = toTitleCase(displayTitle.replace(/_/g, ' '));
        }
        
        return { groupLabel, displayTitle };
    }

    function toTitleCase(str) {
        return str
            .split(' ')
            .filter(Boolean)
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    
    function addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        typingDiv.textContent = 'Thinking...';
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return typingDiv;
    }
    
    function removeTypingIndicator(indicator) {
        indicator.remove();
    }
});


// Code Q&A functionality
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const queryInput = document.getElementById('query-input');
    const sendBtn = document.getElementById('send-btn');
    const filesList = document.getElementById('files-list');
    const fileSearch = document.getElementById('file-search');
    
    let selectedFiles = []; // Track selected files
    let allFilesData = null; // Store all files for filtering
    const CHAT_STORAGE_KEY = 'code_chat_history';
    
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
    
    // Load files on page load
    loadFiles();
    // Restore chat history
    loadChatHistory();
    
    // Search functionality
    fileSearch.addEventListener('input', function() {
        filterFiles(this.value);
    });
    
    // Send query
    sendBtn.addEventListener('click', sendQuery);
    queryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendQuery();
        }
    });
    
    function sendQuery() {
        const query = queryInput.value.trim();
        if (!query) return;
        
        // Add user message
        addMessage(query, 'user');
        queryInput.value = '';
        
        // Show typing indicator
        const typingIndicator = addTypingIndicator();
        
        // Send to API
        fetch('/api/code/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                file_filters: selectedFiles.length > 0 ? selectedFiles : null,
                rerank: false  // Reranking disabled
            })
        })
        .then(response => response.json())
        .then(data => {
            removeTypingIndicator(typingIndicator);
            if (data.status === 'error') {
                addMessage('Error: ' + (data.response || data.error || 'Query failed'), 'bot');
            } else {
                addMessage(data.response || 'No response received', 'bot');
            }
        })
        .catch(error => {
            removeTypingIndicator(typingIndicator);
            addMessage('Error: ' + error.message, 'bot');
        });
    }
    
    function loadFiles() {
        fetch('/api/code/files')
            .then(response => response.json())
            .then(data => {
                // Handle both formats: {files: [...]} or just [...]
                allFilesData = data.files || data || [];
                console.log(`Loaded ${allFilesData.length} files`);
                renderFiles(allFilesData);
            })
            .catch(error => {
                console.error('Error loading files:', error);
                filesList.innerHTML = '<p style="font-size:0.85rem;color:#d32f2f;">Error loading files: ' + error.message + '</p>';
            });
    }
    
    function renderFiles(files) {
        filesList.innerHTML = '';
        
        if (!files || files.length === 0) {
            filesList.innerHTML = '<p style="font-size:0.85rem;color:#666;">No files indexed yet.</p>';
            return;
        }
        
        // Get current search term
        const searchTerm = fileSearch.value.toLowerCase().trim();
        
        // Filter files based on search term
        const filteredFiles = files.filter(file => {
            if (!searchTerm) return true;
            const fileName = (file.file_name || file.name || '').toLowerCase();
            const filePath = (file.file_path || file.path || '').toLowerCase();
            return fileName.includes(searchTerm) || filePath.includes(searchTerm);
        });
        
        if (filteredFiles.length === 0 && searchTerm) {
            filesList.innerHTML = '<p style="font-size:0.85rem;color:#666;">No files match your search.</p>';
            return;
        }
        
        // Create file list
        const fileList = document.createElement('ul');
        fileList.className = 'document-list';
        
        filteredFiles.forEach(file => {
            const fileItem = document.createElement('li');
            fileItem.className = 'document-item';
            
            const fileName = file.file_name || file.name || 'Unknown';
            const filePath = file.file_path || file.path || file.normalized_path || '';
            
            // Check if this file is selected
            if (selectedFiles.includes(filePath)) {
                fileItem.classList.add('selected');
            }
            
            // Show just filename, not full path
            fileItem.innerHTML = `<span class="name">${fileName}</span>`;
            fileItem.title = filePath; // Show full path on hover
            
            fileItem.addEventListener('click', function() {
                toggleFileSelection(filePath, fileItem);
            });
            
            fileList.appendChild(fileItem);
        });
        
        filesList.appendChild(fileList);
    }
    
    function filterFiles(searchTerm) {
        if (allFilesData) {
            renderFiles(allFilesData);
        } else {
            loadFiles();
        }
    }
    
    function toggleFileSelection(filePath, element) {
        if (selectedFiles.includes(filePath)) {
            // Deselect
            selectedFiles = selectedFiles.filter(f => f !== filePath);
            element.classList.remove('selected');
        } else {
            // Select
            selectedFiles.push(filePath);
            element.classList.add('selected');
        }
        
        // Update query input placeholder
        if (selectedFiles.length > 0) {
            const fileNames = selectedFiles.map(p => {
                const file = allFilesData.find(f => (f.file_path || f.path) === p);
                return file ? (file.file_name || file.name) : p.split('/').pop();
            });
            queryInput.placeholder = `Querying ${fileNames.length} file(s): ${fileNames[0]}${fileNames.length > 1 ? '...' : ''}`;
        } else {
            queryInput.placeholder = 'Ask a question about the codebase (e.g., @DatabaseManager.cs what methods are defined?)...';
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
            // Optional: cap history length
            if (existing.length > 200) {
                existing.splice(0, existing.length - 200);
            }
            localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(existing));
        } catch (e) {
            console.error('Failed to save chat history:', e);
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
            console.error('Failed to load chat history:', e);
        }
    }

    // Clear chat button
    const clearChatBtn = document.getElementById('clear-chat-btn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', function() {
            try {
                localStorage.removeItem(CHAT_STORAGE_KEY);
            } catch (e) {
                console.error('Failed to clear chat history:', e);
            }
            // Restore welcome message
            chatContainer.innerHTML = '';
            const welcome = document.createElement('div');
            welcome.className = 'message bot-message';
            welcome.textContent = 'Welcome! Ask questions about your C# codebase. Use @filename.cs to filter to specific files.';
            chatContainer.appendChild(welcome);
        });
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


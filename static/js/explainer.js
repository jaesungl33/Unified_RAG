// Document Explainer functionality (Tab 2)
// Exact replication of keyword_extractor Gradio app behavior using vanilla JS

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the Explainer page
    // Check for unique explainer elements instead of a tab-specific ID
    const explainerKeyword = document.getElementById('explainer-keyword');
    if (!explainerKeyword) {
        return;
    }
    
    // Document Explainer elements
    const explainerSearchBtn = document.getElementById('explainer-search-btn');
    const explainerResultsContainer = document.getElementById('explainer-results-container');
    const explainerResultsCheckboxes = document.getElementById('explainer-results-checkboxes');
    const resultsCount = document.getElementById('results-count');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const selectNoneCheckbox = document.getElementById('select-none-checkbox');
    const explainBtn = document.getElementById('explain-btn');
    const explanationOutput = document.getElementById('explanation-output');
    const sourceChunksOutput = document.getElementById('source-chunks-output');
    const metadataOutput = document.getElementById('metadata-output');
    
    // State management (replaces Gradio State)
    let storedResults = []; // Replaces explainer_search_results_store
    let lastSearchKeyword = null; // Replaces last_search_keyword
    
    // Event handlers
    explainerSearchBtn.addEventListener('click', searchForExplainer);
    explainerKeyword.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchForExplainer();
        }
    });
    explainerKeyword.addEventListener('input', updateGenerateButtonState);
    selectAllCheckbox.addEventListener('change', handleSelectAll);
    selectNoneCheckbox.addEventListener('change', handleSelectNone);
    explainBtn.addEventListener('click', generateExplanation);

    // Collapsible Logic
    const selectionHeader = document.getElementById('selection-header');
    const selectionContent = document.getElementById('selection-content');
    const chevron = selectionHeader?.querySelector('.chevron-toggle');

    selectionHeader?.addEventListener('click', () => {
        selectionContent.classList.toggle('collapsed');
        if (chevron) {
            chevron.style.transform = selectionContent.classList.contains('collapsed') 
                ? 'rotate(-90deg)' : 'rotate(0deg)';
        }
    });
    
    // Initialize button state
    updateGenerateButtonState();
    
    // Initialize empty state - show results container with count 0
    const resultsCountNumber = document.getElementById('results-count-number');
    const selectedCountBadge = document.getElementById('selected-count-badge');
    if (resultsCountNumber) resultsCountNumber.textContent = '0';
    if (selectedCountBadge) selectedCountBadge.textContent = '0';
    explainerResultsContainer.style.display = 'flex';
    const emptyLeft = document.getElementById('explainer-empty-left');
    if (emptyLeft) emptyLeft.style.display = 'none';
    
    async function searchForExplainer() {
        const keyword = explainerKeyword.value.trim();
        const emptyLeft = document.getElementById('explainer-empty-left');
        const resultsCountNumber = document.getElementById('results-count-number');
        const selectedCountBadge = document.getElementById('selected-count-badge');
        
        if (!keyword) {
            // Always show results container, even when empty
            explainerResultsContainer.style.display = 'flex';
            if (emptyLeft) emptyLeft.style.display = 'none';
            resultsCount.style.display = 'none';
            storedResults = [];
            renderCheckboxes([]);
            if (resultsCountNumber) resultsCountNumber.textContent = '0';
            if (selectedCountBadge) selectedCountBadge.textContent = '0';
            updateGenerateButtonState();
            return;
        }
        
        try {
            explainerSearchBtn.disabled = true;
            resultsCount.style.display = 'block';
            resultsCount.innerHTML = '<div style="display:flex;align-items:center;gap:8px;"><div class="spinner" style="width:14px;height:14px;"></div> <span>Searching...</span></div>';
            
            const response = await fetch('/api/gdd/explainer/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword: keyword })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                resultsCount.textContent = result.status_msg || "Search failed.";
                resultsCount.style.color = "var(--status-error)";
                explainerResultsContainer.style.display = 'flex';
                if (emptyLeft) emptyLeft.style.display = 'none';
                renderCheckboxes([]);
                if (resultsCountNumber) resultsCountNumber.textContent = '0';
                if (selectedCountBadge) selectedCountBadge.textContent = '0';
                return;
            }
            
            storedResults = result.store_data || [];
            lastSearchKeyword = keyword;
            
            const choices = result.choices || [];
            renderCheckboxes(choices);
            
            // Always show results container
            explainerResultsContainer.style.display = 'flex';
            if (emptyLeft) emptyLeft.style.display = 'none';
            
            // Update count display
            const count = choices.length;
            if (resultsCountNumber) resultsCountNumber.textContent = count.toString();
            // Note: selectedCountBadge is updated by updateSelectAllNoneState, not here
            
            if (count > 0) {
                resultsCount.textContent = `Found ${count} result(s)`;
                resultsCount.style.color = "var(--muted-foreground)";
            } else {
                resultsCount.textContent = "No results found.";
                resultsCount.style.color = "var(--muted-foreground)";
            }
            
        } catch (error) {
            resultsCount.textContent = "Error: " + error.message;
            resultsCount.style.color = "var(--status-error)";
            explainerResultsContainer.style.display = 'flex';
            if (emptyLeft) emptyLeft.style.display = 'none';
            renderCheckboxes([]);
            if (resultsCountNumber) resultsCountNumber.textContent = '0';
            if (selectedCountBadge) selectedCountBadge.textContent = '0';
        } finally {
            explainerSearchBtn.disabled = false;
            updateGenerateButtonState();
        }
    }
    
    function renderCheckboxes(choices) {
        explainerResultsCheckboxes.innerHTML = '';
        
        if (!choices || choices.length === 0) {
            return;
        }
        
        choices.forEach((choice, index) => {
            const documentItem = document.createElement('div');
            documentItem.className = 'document-item explainer-item';
            documentItem.style.padding = '10px 12px';
            documentItem.style.cursor = 'pointer';
            
            const checkboxContainer = document.createElement('div');
            checkboxContainer.className = 'custom-checkbox';
            checkboxContainer.style.marginRight = '12px';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `checkbox-${index}`;
            checkbox.value = choice;
            checkbox.name = 'explainer-choice';
            checkbox.style.display = 'none'; // Hidden, used for state
            
            // Visual Square icon
            const icon = document.createElement('div');
            icon.className = 'checkbox-icon';
            icon.innerHTML = `<img src="/static/icons/file.svg" width="16" height="16" style="opacity:0.3;">`; // Default empty state
            
            const label = document.createElement('span');
            label.style.fontSize = '0.8125rem';
            label.style.fontWeight = '500';
            label.textContent = choice;
            
            documentItem.appendChild(checkbox);
            documentItem.appendChild(icon);
            documentItem.appendChild(label);
            
            documentItem.addEventListener('click', () => {
                checkbox.checked = !checkbox.checked;
                updateItemVisualState(documentItem, checkbox.checked);
                updateGenerateButtonState();
                updateSelectAllNoneState();
            });

            documentItem.addEventListener('mouseenter', () => {
                documentItem.style.background = 'var(--muted)';
            });
            documentItem.addEventListener('mouseleave', () => {
                if (!checkbox.checked) documentItem.style.background = 'transparent';
            });
            
            explainerResultsCheckboxes.appendChild(documentItem);
        });
        
        // Reset select all/none checkboxes
        selectAllCheckbox.checked = false;
        selectNoneCheckbox.checked = false;
    }

    function updateItemVisualState(element, isChecked) {
        const icon = element.querySelector('.checkbox-icon');
        if (isChecked) {
            element.style.background = 'rgba(239, 68, 68, 0.05)';
            element.style.color = 'var(--primary)';
            icon.innerHTML = `<img src="/static/icons/success.svg" width="16" height="16" style="filter: invert(32%) sepia(85%) saturate(2853%) hue-rotate(345deg) brightness(101%) contrast(89%);">`;
        } else {
            element.style.background = 'transparent';
            element.style.color = 'inherit';
            icon.innerHTML = `<img src="/static/icons/file.svg" width="16" height="16" style="opacity:0.3;">`;
        }
    }

    function handleSelectAll() {
        if (selectAllCheckbox.checked) {
            selectNoneCheckbox.checked = false;
            const items = explainerResultsCheckboxes.querySelectorAll('.document-item');
            items.forEach(item => {
                const cb = item.querySelector('input');
                cb.checked = true;
                updateItemVisualState(item, true);
            });
            updateGenerateButtonState();
        }
    }

    function handleSelectNone() {
        if (selectNoneCheckbox.checked) {
            selectAllCheckbox.checked = false;
            const items = explainerResultsCheckboxes.querySelectorAll('.document-item');
            items.forEach(item => {
                const cb = item.querySelector('input');
                cb.checked = false;
                updateItemVisualState(item, false);
            });
            updateGenerateButtonState();
        }
    }
    
    function getSelectedChoices() {
        const checkboxes = explainerResultsCheckboxes.querySelectorAll('input[type="checkbox"][name="explainer-choice"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    async function generateExplanation() {
        const keyword = explainerKeyword.value.trim();
        const selectedChoices = getSelectedChoices();
        const genStatus = document.getElementById('gen-status');
        const chunksOutput = document.getElementById('source-chunks-output');
        const chunksLabel = document.getElementById('chunks-count-label');
        
        try {
            explainBtn.disabled = true;
            genStatus.innerHTML = '<div style="display:flex;align-items:center;gap:8px;color:var(--status-info)"><div class="spinner" style="width:12px;height:12px;"></div> Thinking...</div>';
            // Restore flex centering for placeholder state
            explanationOutput.style.display = 'flex';
            explanationOutput.style.alignItems = 'center';
            explanationOutput.style.justifyContent = 'center';
            explanationOutput.innerHTML = '<div class="placeholder-text" style="padding-top:100px;"><p>Synthesizing context from selected documents...</p></div>';
            chunksOutput.innerHTML = '<p class="placeholder-text">Retrieving relevant chunks...</p>';
            
            const response = await fetch('/api/gdd/explainer/explain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keyword,
                    selected_choices: selectedChoices,
                    stored_results: storedResults
                })
            });
            
            const result = await response.json();
            genStatus.textContent = result.success ? "✓ Completed" : "✕ Generation Failed";
            genStatus.style.color = result.success ? "var(--status-success)" : "var(--status-error)";
            
            if (!result.success) {
                // Keep block display for error message
                explanationOutput.style.display = 'block';
                explanationOutput.style.alignItems = 'stretch';
                explanationOutput.style.justifyContent = 'flex-start';
                explanationOutput.innerHTML = `<div class="placeholder-text"><p style="color:var(--status-error)">${result.explanation || 'Generation failed'}</p></div>`;
                return;
            }
            
            // Explanation formatting
            // Remove flex centering styles when content is present
            explanationOutput.style.display = 'block';
            explanationOutput.style.alignItems = 'stretch';
            explanationOutput.style.justifyContent = 'flex-start';
            explanationOutput.innerHTML = `<div class="generated-explanation" style="color: var(--foreground)">${renderMarkdown(result.explanation || '', 'Explanation', keyword)}</div>`;
            
            // Source Chunks formatting
            const chunks = result.source_chunks ? result.source_chunks.split('\n\n').filter(c => c.trim()) : [];
            if (chunksLabel) chunksLabel.textContent = `${chunks.length} chunks used`;
            
            chunksOutput.innerHTML = chunks.map((chunk, idx) => `
                <div class="source-chunk-card">
                    <div style="font-family: var(--font-mono); font-size: 11px; color: var(--muted-foreground); opacity: 0.8; margin-bottom: 6px;">CHUNK ${idx + 1}</div>
                    <div style="font-size: 12px; line-height: 1.5; color: rgba(0,0,0,0.7);">${chunk.replace(/^Chunk \d+:?\s*/i, '')}</div>
                </div>
            `).join('');

            // Metadata formatting
            const metaLines = result.metadata ? result.metadata.split('\n').filter(l => l.includes(': ')) : [];
            metadataOutput.innerHTML = `
                <div class="metadata-list">
                    ${metaLines.map(line => {
                        const [label, ...valParts] = line.split(': ');
                        return `
                            <div class="metadata-item">
                                <span class="metadata-label">${label}</span>
                                <span class="metadata-value">${valParts.join(': ')}</span>
                            </div>
                        `;
                    }).join('')}
                    <div class="metadata-item">
                        <span class="metadata-label">Timestamp</span>
                        <span class="metadata-value">${new Date().toLocaleString()}</span>
                    </div>
                </div>
            `;
            
        } catch (error) {
            genStatus.textContent = "Network Error";
            genStatus.style.color = "var(--status-error)";
            explanationOutput.innerHTML = `<p>Error: ${error.message}</p>`;
        } finally {
            explainBtn.disabled = false;
            updateGenerateButtonState();
        }
    }
    
    
    function updateSelectAllNoneState() {
        const checkboxes = explainerResultsCheckboxes.querySelectorAll('input[type="checkbox"][name="explainer-choice"]');
        const checkedCount = explainerResultsCheckboxes.querySelectorAll('input[type="checkbox"][name="explainer-choice"]:checked').length;
        const totalCount = checkboxes.length;

        // Update sticky badge
        const badge = document.getElementById('selected-count-badge');
        if (badge) badge.textContent = checkedCount;
        
        if (checkedCount === 0) {
            selectAllCheckbox.checked = false;
            selectNoneCheckbox.checked = false;
        } else if (checkedCount === totalCount) {
            selectAllCheckbox.checked = true;
            selectNoneCheckbox.checked = false;
        } else {
            selectAllCheckbox.checked = false;
            selectNoneCheckbox.checked = false;
        }
    }
    
    function updateGenerateButtonState() {
        const selectedChoices = getSelectedChoices();
        const keyword = explainerKeyword.value.trim();
        
        if (keyword && selectedChoices && selectedChoices.length > 0) {
            explainBtn.disabled = false;
        } else {
            explainBtn.disabled = true;
        }
    }
    
    function renderMarkdown(text, stripHeading, keyword = '') {
        if (!text) return '';
        
        // RENDERING ORDER: Process on plain text BEFORE markdown conversion
        let processedText = text;
        
        // Step 1: Process *word* syntax from LLM (highlight important keywords/phrases)
        // Use a temporary marker to avoid conflicts with markdown **bold** syntax
        // Replace *word* with a temporary marker, then convert to HTML after markdown processing
        const highlightMarkers = [];
        let markerIndex = 0;
        processedText = processedText.replace(/\*([^*]+?)\*/g, (match, content) => {
            const marker = `__HIGHLIGHT_MARKER_${markerIndex}__`;
            highlightMarkers.push(`<span class="keyword-highlight">${content}</span>`);
            markerIndex++;
            return marker;
        });
        
        // Step 2: Highlight search keyword in plain text (case-insensitive, whole words only)
        // This must happen BEFORE markdown rendering, but after *word* processing
        if (keyword && keyword.trim()) {
            const keywordEscaped = keyword.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const keywordRegex = new RegExp(`\\b(${keywordEscaped})\\b`, 'gi');
            
            // Find all existing markers to avoid overlapping highlights
            const markerPattern = /__HIGHLIGHT_MARKER_(\d+)__/g;
            const existingMarkers = [];
            let markerMatch;
            while ((markerMatch = markerPattern.exec(processedText)) !== null) {
                existingMarkers.push({
                    start: markerMatch.index,
                    end: markerMatch.index + markerMatch[0].length,
                    index: parseInt(markerMatch[1])
                });
            }
            
            // Only highlight if not overlapping with existing markers
            processedText = processedText.replace(keywordRegex, (match, offset, string) => {
                const matchStart = offset;
                const matchEnd = offset + match.length;
                
                // Check if this match overlaps with any existing marker
                for (const marker of existingMarkers) {
                    // If match is inside or overlaps with a marker, skip
                    if ((matchStart >= marker.start && matchStart < marker.end) ||
                        (matchEnd > marker.start && matchEnd <= marker.end) ||
                        (matchStart <= marker.start && matchEnd >= marker.end)) {
                        return match; // Skip, already highlighted via *word* syntax
                    }
                }
                
                // Add as a new highlight marker
                const marker = `__HIGHLIGHT_MARKER_${markerIndex}__`;
                highlightMarkers.push(`<span class="keyword-highlight">${match}</span>`);
                markerIndex++;
                return marker;
            });
        }
        
        // Step 3: Strip duplicate headings that match the bubble title
        if (stripHeading) {
            // Remove headings that exactly match the bubble title (case-insensitive)
            const headingPatterns = [
                new RegExp(`^#+\\s*${stripHeading}\\s*$`, 'gim'),
                new RegExp(`^#+\\s*${stripHeading.replace(/\s+/g, '\\s+')}\\s*$`, 'gim')
            ];
            
            headingPatterns.forEach(pattern => {
                processedText = processedText.replace(pattern, '');
            });
            
            // Also remove if it's the first line and matches
            const lines = processedText.split('\n');
            if (lines.length > 0) {
                const firstLine = lines[0].trim();
                const headingMatch = firstLine.match(/^#+\s*(.+)$/i);
                if (headingMatch && headingMatch[1].trim().toLowerCase() === stripHeading.toLowerCase()) {
                    lines.shift();
                    processedText = lines.join('\n');
                }
            }
        }
        
        // Step 4: Convert markdown to HTML
        let html = processedText;
        
        // Headers - NO <strong> wrapping, CSS will handle bold
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Markdown bold (**text**) - ONLY source of <strong> tags
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Lists
        html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Line breaks
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        
        // Fix nested lists
        html = html.replace(/<p><ul>/g, '<ul>');
        html = html.replace(/<\/ul><\/p>/g, '</ul>');
        html = html.replace(/<p><li>/g, '<li>');
        html = html.replace(/<\/li><\/p>/g, '</li>');
        html = html.replace(/<p><\/p>/g, '');
        
        // Step 5: Replace temporary highlight markers with actual HTML
        highlightMarkers.forEach((markerHtml, index) => {
            html = html.replace(`__HIGHLIGHT_MARKER_${index}__`, markerHtml);
        });
        
        return html;
    }
});



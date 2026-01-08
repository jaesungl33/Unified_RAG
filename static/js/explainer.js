// Document Explainer functionality (Tab 2)
// Exact replication of keyword_extractor Gradio app behavior using vanilla JS

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the GDD tab page
    const explainerTab = document.getElementById('tab-explainer');
    if (!explainerTab) {
        return;
    }
    
    // Tab switching logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            // Update active tab button
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Update active tab content
            tabContents.forEach(content => {
                content.classList.remove('active');
                content.style.display = 'none';
            });
            
            const targetTab = document.getElementById(`tab-${tabName}`);
            if (targetTab) {
                targetTab.classList.add('active');
                targetTab.style.display = 'block';
            }
        });
    });
    
    // Document Explainer elements
    const explainerKeyword = document.getElementById('explainer-keyword');
    const explainerSearchBtn = document.getElementById('explainer-search-btn');
    const explainerResultsContainer = document.getElementById('explainer-results-container');
    const explainerResultsCheckboxes = document.getElementById('explainer-results-checkboxes');
    const searchStatus = document.getElementById('search-status');
    const selectAllBtn = document.getElementById('select-all-btn');
    const selectNoneBtn = document.getElementById('select-none-btn');
    const explainBtn = document.getElementById('explain-btn');
    const explanationOutput = document.getElementById('explanation-output');
    const sourceChunksOutput = document.getElementById('source-chunks-output');
    const metadataOutput = document.getElementById('metadata-output');
    
    // State management (replaces Gradio State)
    let storedResults = []; // Replaces explainer_search_results_store
    let lastSearchKeyword = null; // Replaces last_search_keyword
    
    // Event handlers (exact behavior replication)
    explainerSearchBtn.addEventListener('click', searchForExplainer);
    explainerKeyword.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchForExplainer();
        }
    });
    selectAllBtn.addEventListener('click', selectAllItems);
    selectNoneBtn.addEventListener('click', selectNoneItems);
    explainBtn.addEventListener('click', generateExplanation);
    
    async function searchForExplainer() {
        const keyword = explainerKeyword.value.trim();
        
        if (!keyword) {
            showStatus("Please enter a keyword to search.", false);
            explainerResultsContainer.style.display = 'none';
            storedResults = [];
            return;
        }
        
        try {
            explainerSearchBtn.disabled = true;
            explainerSearchBtn.textContent = 'Searching...';
            showStatus("Searching...", true);
            
            const response = await fetch('/api/gdd/explainer/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ keyword: keyword })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                showStatus(result.status_msg || "Error occurred.", false);
                explainerResultsContainer.style.display = 'none';
                storedResults = [];
                lastSearchKeyword = null;
                return;
            }
            
            // Update stored results
            storedResults = result.store_data || [];
            lastSearchKeyword = keyword;
            
            // Clear previous checkboxes and render new ones
            renderCheckboxes(result.choices || []);
            
            // Show results container
            if (result.choices && result.choices.length > 0) {
                explainerResultsContainer.style.display = 'block';
                showStatus(result.status_msg || "Search completed.", true);
            } else {
                explainerResultsContainer.style.display = 'none';
                showStatus("No results found.", false);
            }
            
        } catch (error) {
            console.error('Error in search:', error);
            showStatus(`❌ Error: ${error.message}`, false);
            explainerResultsContainer.style.display = 'none';
            storedResults = [];
        } finally {
            explainerSearchBtn.disabled = false;
            explainerSearchBtn.textContent = 'Search';
        }
    }
    
    function renderCheckboxes(choices) {
        explainerResultsCheckboxes.innerHTML = '';
        
        if (!choices || choices.length === 0) {
            return;
        }
        
        choices.forEach((choice, index) => {
            const checkboxItem = document.createElement('div');
            checkboxItem.className = 'checkbox-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `checkbox-${index}`;
            checkbox.value = choice;
            checkbox.name = 'explainer-choice';
            
            const label = document.createElement('label');
            label.htmlFor = `checkbox-${index}`;
            label.textContent = choice;
            
            checkboxItem.appendChild(checkbox);
            checkboxItem.appendChild(label);
            explainerResultsCheckboxes.appendChild(checkboxItem);
        });
    }
    
    function getSelectedChoices() {
        const checkboxes = explainerResultsCheckboxes.querySelectorAll('input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    async function generateExplanation() {
        const keyword = explainerKeyword.value.trim();
        
        if (!keyword) {
            explanationOutput.innerHTML = "<p>Please enter a keyword first.</p>";
            sourceChunksOutput.innerHTML = '';
            metadataOutput.innerHTML = '';
            return;
        }
        
        if (!storedResults || storedResults.length === 0) {
            explanationOutput.innerHTML = "<p>Please search for a keyword first.</p>";
            sourceChunksOutput.innerHTML = '';
            metadataOutput.innerHTML = '';
            return;
        }
        
        const selectedChoices = getSelectedChoices();
        
        if (!selectedChoices || selectedChoices.length === 0) {
            explanationOutput.innerHTML = "<p>Please select at least one document/section to explain.</p>";
            sourceChunksOutput.innerHTML = '';
            metadataOutput.innerHTML = '';
            return;
        }
        
        try {
            explainBtn.disabled = true;
            explainBtn.textContent = 'Generating...';
            explanationOutput.innerHTML = "<p>Generating explanation...</p>";
            sourceChunksOutput.innerHTML = '';
            metadataOutput.innerHTML = '';
            
            const response = await fetch('/api/gdd/explainer/explain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    keyword: keyword,
                    selected_choices: selectedChoices,
                    stored_results: storedResults
                })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                explanationOutput.innerHTML = `<p>${result.explanation || 'Error occurred.'}</p>`;
                sourceChunksOutput.innerHTML = '';
                metadataOutput.innerHTML = '';
                return;
            }
            
            // Render markdown outputs
            explanationOutput.innerHTML = renderMarkdown(result.explanation || '');
            sourceChunksOutput.innerHTML = renderMarkdown(result.source_chunks || '');
            metadataOutput.innerHTML = renderMarkdown(result.metadata || '');
            
        } catch (error) {
            console.error('Error generating explanation:', error);
            explanationOutput.innerHTML = `<p>❌ Error: ${error.message}</p>`;
            sourceChunksOutput.innerHTML = '';
            metadataOutput.innerHTML = '';
        } finally {
            explainBtn.disabled = false;
            explainBtn.textContent = 'Generate Explanation';
        }
    }
    
    async function selectAllItems() {
        if (!storedResults || storedResults.length === 0) {
            return;
        }
        
        try {
            const response = await fetch('/api/gdd/explainer/select-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    stored_results: storedResults
                })
            });
            
            const result = await response.json();
            
            // Check all checkboxes
            const checkboxes = explainerResultsCheckboxes.querySelectorAll('input[type="checkbox"]');
            const choices = result.choices || [];
            
            checkboxes.forEach(checkbox => {
                if (choices.includes(checkbox.value)) {
                    checkbox.checked = true;
                }
            });
            
        } catch (error) {
            console.error('Error selecting all:', error);
        }
    }
    
    function selectNoneItems() {
        const checkboxes = explainerResultsCheckboxes.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
    }
    
    function showStatus(message, isSuccess) {
        searchStatus.textContent = message;
        searchStatus.style.display = 'block';
        searchStatus.style.backgroundColor = isSuccess ? '#f0f9f0' : '#f9f0f0';
        searchStatus.style.borderColor = isSuccess ? '#4caf50' : '#f44336';
    }
    
    function renderMarkdown(text) {
        if (!text) return '';
        
        // Simple markdown rendering (for better results, consider using marked.js)
        let html = text;
        
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Bold
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
        
        return html;
    }
});


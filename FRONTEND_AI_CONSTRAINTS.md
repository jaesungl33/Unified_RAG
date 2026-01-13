# Frontend UI Redesign - Complete Constraints & Requirements

You are refactoring the **FRONTEND UI ONLY** of an existing web application. Your task is to **COMPLETELY REDESIGN the FRONTEND LAYOUT AND VISUAL STYLE** while preserving **100% of existing functionality and behavior**.

---

## 🚫 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

### 1. Backend Contract (READ-ONLY)
- **DO NOT** modify, remove, or rename ANY backend API endpoints
- **DO NOT** change request payloads, response formats, or API URLs
- **DO NOT** alter query parameters, headers, or HTTP methods
- **DO NOT** modify response parsing logic in JavaScript

### 2. JavaScript Logic (BLACK BOX)
- **DO NOT** modify application logic in any JavaScript files:
  - `static/js/gdd.js`
  - `static/js/code.js`
  - `static/js/explainer.js`
  - `static/js/manage.js`
  - `static/js/tabs.js`
- **DO NOT** change event handler implementations
- **DO NOT** modify state management, data structures, or variable names
- **DO NOT** alter localStorage keys or storage logic
- **DO NOT** change how messages are formatted, rendered, or stored

### 3. DOM Contract (MANDATORY PRESERVATION)
- **ALL DOM IDs listed below MUST exist exactly as specified**
- **ALL CSS classes used by JavaScript MUST remain functional**
- **ALL data attributes MUST be preserved**
- **ALL event bindings MUST continue to work**

---

## 📋 REQUIRED DOM ELEMENTS (MUST PRESERVE)

### Base Template (`base.html`)
- `app-container` (class)
- `header` (element)
- `tabs` (class on nav)
- `tab-link` (class) with `data-tab` attribute
- `main` (element)

### GDD RAG Tab (`gdd_tab.html`)
**Tab Navigation:**
- `.tab-navigation` (class)
- `.tab-btn` (class) with `data-tab` attribute
- `#tab-rag` (ID)
- `#tab-explainer` (ID)
- `.tab-content` (class)
- `.active` (class for active state)

**GDD RAG Tab Content:**
- `#document-search` (ID) - Search input
- `#documents-list` (ID) - Document list container
- `.document-item` (class) - Individual document items
- `.document-group` (class) - Document group wrapper
- `.document-group-title` (class) - Group header
- `.document-list` (class) - List within group
- `.selected` (class) - Selected document state
- `.name` (class) - Document name span
- `data-doc-value` (attribute) - Document value
- `data-doc-id` (attribute) - Document ID
- `#chat-container` (ID) - Chat messages container
- `#gdd-welcome-message` (ID) - Welcome message
- `.message` (class) - Message wrapper
- `.bot-message` (class) - Bot message
- `.user-message` (class) - User message
- `#query-input` (ID) - Query input field
- `#send-btn` (ID) - Send button
- `#clear-chat-btn` (ID) - Clear chat button
- `#section-dropdown` (ID) - Section dropdown (dynamically created)
- `.section-item` (class) - Section dropdown item
- `.highlighted` (class) - Highlighted dropdown item
- `data-section-name` (attribute) - Section name
- `data-section-path` (attribute) - Section path

**Document Explainer Tab:**
- `#explainer-keyword` (ID) - Keyword input
- `#explainer-search-btn` (ID) - Search button
- `#results-count` (ID) - Results count display
- `#explainer-results-container` (ID) - Results container
- `#explainer-results-checkboxes` (ID) - Checkboxes container
- `#select-all-checkbox` (ID) - Select all checkbox
- `#select-none-checkbox` (ID) - Select none checkbox
- `#explain-btn` (ID) - Generate explanation button
- `#explanation-output` (ID) - Explanation output
- `#source-chunks-output` (ID) - Source chunks output
- `#metadata-output` (ID) - Metadata output
- `.explainer-bubble` (class) - Bubble container
- `.bubble-title` (class) - Bubble title
- `.bubble-content` (class) - Bubble content area
- `.document-list` (class) - Document list in explainer
- `.placeholder-text` (class) - Placeholder text
- `input[name="explainer-choice"]` - Checkbox inputs for document selection

### Code Q&A Tab (`code_tab.html`)
- `#file-search` (ID) - File search input
- `#files-list` (ID) - Files list container
- `.document-item` (class) - File item
- `.selected` (class) - Selected file state
- `.name` (class) - File name span
- `data-file-path` (attribute) - File path
- `#chat-container` (ID) - Chat container
- `#code-welcome-message` (ID) - Welcome message
- `#query-input` (ID) - Query input
- `#send-btn` (ID) - Send button
- `#clear-chat-btn` (ID) - Clear chat button
- `.method-checkboxes` (class) - Method selection container (dynamically created)
- `.method-checkbox` (class) - Method checkbox
- `.method-checkbox-label` (class) - Method checkbox label
- `.method-submit-btn` (class) - Method submit button
- `.method-cancel-btn` (class) - Method cancel button
- `data-type` (attribute) - Type (method/global)
- `data-line` (attribute) - Line number

### Manage Documents Tab (`manage_documents.html`)
**Tab Navigation:**
- `.tab-navigation` (class)
- `.tab-btn` (class) with `data-tab` attribute
- `#tab-gdd-docs` (ID)
- `#tab-code-files` (ID)
- `.tab-content` (class)
- `.active` (class)

**GDD Documents Section:**
- `#gdd-file-upload` (ID) - File upload input
- `#gdd-upload-btn` (ID) - Upload button
- `#gdd-queue-list` (ID) - Queue list
- `#gdd-documents-list` (ID) - Documents list
- `.queue-item` (class) - Queue item
- `.queued` (class) - Queued state
- `.processing` (class) - Processing state
- `.completed` (class) - Completed state
- `.error` (class) - Error state
- `.status-icon` (class) - Status icon
- `.file-name` (class) - File name
- `.progress-text` (class) - Progress text
- `.error-text` (class) - Error text
- `.document-item` (class) - Document item
- `.document-info` (class) - Document info
- `.document-name` (class) - Document name
- `.document-meta` (class) - Document metadata
- `.document-actions` (class) - Document actions
- `.btn-small` (class) - Small button
- `.btn-danger` (class) - Danger button
- `.empty-queue` (class) - Empty queue message

**Code Files Section:**
- `#code-file-upload` (ID) - File upload input
- `#code-upload-btn` (ID) - Upload button
- `#code-queue-list` (ID) - Queue list
- `#code-documents-list` (ID) - Documents list
- (Same classes as GDD Documents section)

---

## 🔌 BACKEND API ENDPOINTS (READ-ONLY CONTRACT)

**GDD RAG:**
- `GET /api/gdd/documents` - List documents
- `POST /api/gdd/query` - Query documents
- `GET /api/gdd/sections?doc_id={id}` - Get document sections
- `POST /api/gdd/upload` - Upload document
- `GET /api/gdd/upload/status?job_id={id}` - Upload status
- `POST /api/gdd/explainer/search` - Search for keyword
- `POST /api/gdd/explainer/explain` - Generate explanation
- `POST /api/gdd/explainer/select-all` - Select all items
- `POST /api/gdd/explainer/select-none` - Select none items

**Code Q&A:**
- `GET /api/code/files` - List code files
- `POST /api/code/query` - Query codebase

**Manage Documents:**
- `POST /api/code/upload` - Upload code file
- `GET /api/code/upload/status?job_id={id}` - Code upload status
- `POST /api/manage/delete/gdd` - Delete GDD document
- `POST /api/manage/delete/code` - Delete code file
- `POST /api/manage/reindex/gdd` - Re-index GDD document
- `POST /api/manage/reindex/code` - Re-index code file

**DO NOT modify request/response formats for these endpoints.**

---

## ⚙️ CORE FEATURES (MUST PRESERVE EXACTLY)

### GDD RAG Tab Features:
1. **Document Sidebar:**
   - Left sidebar listing indexed documents
   - Document grouping by derived group label (e.g., "[Asset, UI]", "[Character Module]")
   - Group headers with document lists beneath them
   - Document selection highlighting (`.selected` class)
   - Search filtering in sidebar (real-time as user types)
   - "All Documents" option at top when no document selected
   - Selected document appears first in its group
   - Click handler on `.document-item` elements

2. **Chat Interface:**
   - Chat container with message history
   - User messages and bot messages with distinct styling
   - Markdown rendering (code blocks, inline code, bold, lists)
   - Typing indicator support
   - LocalStorage persistence (`gdd_chat_history` key)
   - Fixed input area at bottom
   - Enter key to send
   - Clear chat functionality

3. **Query Input Behavior:**
   - `@documentname` pattern support (auto-completes from sidebar)
   - `@section` pattern support (dropdown appears on `@`)
   - Section dropdown with keyboard navigation (Arrow keys, Enter)
   - Input syncs with document selection
   - Selected document name auto-inserted into input
   - Query text extraction (removes `@documentname` before sending)

4. **Document Explainer Tab:**
   - Keyword search input with search button
   - Results count display
   - Document selection with checkboxes
   - "All" and "None" checkbox controls
   - Generate explanation button (disabled until valid selection)
   - Explanation output with markdown rendering
   - Source chunks output with consistent font
   - Metadata output
   - Internal scrolling in all bubbles
   - Duplicate heading removal (strips "Explanation", "Source Chunks", "Metadata" headings)

### Code Q&A Tab Features:
1. **File Sidebar:**
   - Left sidebar listing indexed code files
   - File selection (multiple files can be selected)
   - Selected files highlighted (`.selected` class)
   - Search filtering in sidebar
   - Selected files appear first in list
   - Click handler toggles selection

2. **Chat Interface:**
   - Same as GDD RAG chat features
   - LocalStorage persistence (`code_chat_history` key)

3. **Query Input Behavior:**
   - `@filename.cs` pattern support
   - Input syncs with file selection
   - Multiple `@filename.cs` patterns supported
   - Method selection UI (dynamically created when needed)
   - Global variables checkbox option
   - Method checkboxes with line numbers

### Manage Documents Tab Features:
1. **Internal Tab Navigation:**
   - Two tabs: "GDD Documents" and "Code Files"
   - Tab switching with `.active` class management

2. **Upload Queue System:**
   - Multiple file selection support
   - Queue display with status indicators
   - Sequential processing (one at a time)
   - Auto-start processing when items added
   - Status: queued, processing, completed, error
   - Progress text updates
   - Auto-remove completed items after 2 seconds
   - Separate queues for GDD and Code

3. **Document Management:**
   - Document list with metadata (chunks count, file path)
   - Delete button (with confirmation)
   - Re-index button (with confirmation)
   - View Details button (Code Files only)

---

## 🎨 CSS CLASSES USED BY JAVASCRIPT (MUST PRESERVE)

**Selection & State:**
- `.selected` - Selected document/file state
- `.active` - Active tab/button state
- `.highlighted` - Highlighted dropdown item
- `.queued`, `.processing`, `.completed`, `.error` - Queue item states

**Structure:**
- `.document-item` - Document/file list item
- `.document-group` - Document group wrapper
- `.document-group-title` - Group header
- `.document-list` - List container
- `.message` - Message wrapper
- `.bot-message` - Bot message
- `.user-message` - User message
- `.tab-content` - Tab content container
- `.tab-btn` - Tab button
- `.queue-item` - Queue item

**Content:**
- `.name` - Name span
- `.bubble-content` - Bubble content area
- `.placeholder-text` - Placeholder text
- `.code-block` - Code block (for markdown rendering)
- `.inline-code` - Inline code (for markdown rendering)

**YOU MAY add new CSS classes, but DO NOT remove or rename the above classes.**

---

## 📝 DATA ATTRIBUTES (MUST PRESERVE)

- `data-tab` - Tab identifier
- `data-doc-value` - Document value string
- `data-doc-id` - Document ID
- `data-file-path` - File path
- `data-section-name` - Section name
- `data-section-path` - Section path
- `data-type` - Type (method/global)
- `data-line` - Line number

---

## ✅ WHAT YOU MAY DO

- **Fully redesign layout:** Grid, flexbox, cards, panels, split views, tabs, etc.
- **Replace all CSS styling:** Colors, fonts, spacing, borders, shadows, etc.
- **Improve visual hierarchy:** Typography, sizing, spacing, contrast
- **Add modern UI components:** Cards, accordions, collapsible sections, tooltips
- **Improve usability:** Better spacing, clearer labels, improved feedback
- **Enhance accessibility:** Better contrast, focus states, hover states, ARIA labels
- **Add animations/transitions:** CSS-only animations and transitions
- **Reorganize HTML structure:** As long as all IDs, classes, and data attributes remain accessible
- **Add new CSS classes:** For styling purposes (but preserve JS-used classes)

---

## ❌ WHAT YOU MUST NOT DO

- Modify JavaScript files
- Change DOM IDs
- Remove or rename CSS classes used by JavaScript
- Remove or rename data attributes
- Change event handler bindings
- Modify API request/response handling
- Change localStorage keys
- Alter message rendering logic
- Change document grouping logic
- Modify selection behavior
- Change filtering behavior
- Alter query input parsing
- Modify markdown rendering
- Change upload queue logic

---

## 📖 DETAILED FEATURE BEHAVIOR

### Document Explainer Tab - Complete Flow

**Step 1: Keyword Search**
- User types keyword in `#explainer-keyword` input
- User clicks `#explainer-search-btn` or presses Enter
- JavaScript calls `POST /api/gdd/explainer/search` with `{ keyword: string }`
- Response: `{ success: boolean, choices: string[], store_data: any[] }`
- `#results-count` displays "Found X result(s)."
- `#explainer-results-container` becomes visible
- `renderCheckboxes()` creates checkboxes for each choice

**Step 2: Document Selection**
- User can check/uncheck individual checkboxes (`input[name="explainer-choice"]`)
- `#select-all-checkbox` selects all items
- `#select-none-checkbox` deselects all items
- `#explain-btn` enabled only when keyword exists AND at least one checkbox checked
- Checkbox state tracked via `getSelectedChoices()` function

**Step 3: Generate Explanation**
- User clicks `#explain-btn`
- JavaScript calls `POST /api/gdd/explainer/explain` with:
  ```json
  {
    "keyword": "string",
    "selected_choices": ["choice1", "choice2"],
    "stored_results": [...]
  }
  ```
- Response: `{ success: boolean, explanation: string, source_chunks: string, metadata: string }`
- `#explanation-output` displays markdown-rendered explanation
- `#source-chunks-output` displays source chunks (monospace font)
- `#metadata-output` displays metadata
- Markdown rendering strips duplicate headings matching bubble titles

**Layout Structure:**
- Left column: Keyword search, results count, document selection, generate button
- Right column: Explanation (large), Source Chunks (bottom-left), Metadata (bottom-right)
- All bubbles have internal scrolling
- Document selection bubble: min-height 400px, max-height 600px
- Explanation bubble: min-height 400px, max-height 600px
- Source chunks & metadata: min-height 200px, max-height 300px

### Manage Documents Tab - Complete Flow

**GDD Documents Section:**

**Step 1: Upload Files**
- User selects multiple PDF files via `#gdd-file-upload` input
- User clicks `#gdd-upload-btn`
- JavaScript adds files to `gddQueue` array
- Each queue item: `{ id: number, file: File, status: 'queued', progress: '', error: null }`
- `renderGDDQueue()` displays queue items
- `processGDDQueue()` auto-starts (sequential processing)

**Step 2: Queue Processing**
- First queued item status changes to 'processing'
- JavaScript calls `POST /api/gdd/upload` with FormData
- Response: `{ status: 'accepted', job_id: string, step: string }`
- JavaScript polls `GET /api/gdd/upload/status?job_id={id}` every 1 second
- Queue item shows progress text from status updates
- On success: status changes to 'completed', checkmark icon shown
- On error: status changes to 'error', error icon shown
- Completed items auto-removed after 2 seconds
- Next item in queue starts processing automatically

**Step 3: Document List**
- `loadGDDDocuments()` calls `GET /api/gdd/documents`
- Response: `{ documents: [{ id, name, chunks_count, ... }] }`
- `renderGDDDocuments()` creates document items with:
  - Document name
  - Chunks count
  - Re-index button (calls `POST /api/manage/reindex/gdd`)
  - Delete button (calls `POST /api/manage/delete/gdd`)

**Code Files Section:**
- Identical flow to GDD Documents
- Uses `#code-file-upload`, `#code-upload-btn`, `#code-queue-list`, `#code-documents-list`
- Accepts `.cs` files only
- Uses `POST /api/code/upload` and `GET /api/code/upload/status`
- Document list shows file name and file path
- Includes "View Details" button (Code Files only)

**Queue Item States:**
- `queued`: ⏳ icon, gray background
- `processing`: ⏳ icon, yellow background
- `completed`: ✅ icon, green background
- `error`: ❌ icon, red background

---

## 🎯 DELIVERABLE

Provide:
1. **Updated HTML templates** with new layout/structure (all IDs/classes/data attributes preserved)
2. **Complete CSS file** with new visual design
3. **Verification checklist** confirming all features work identically

**Test Requirements:**
- All document/file selection works
- All search filtering works
- All chat functionality works
- All upload queues work
- All tab switching works
- All API calls succeed
- All dynamic content renders correctly

---

## 📌 TECHNICAL NOTES

- JavaScript uses `getElementById()`, `querySelector()`, `querySelectorAll()`
- Event listeners are attached via `addEventListener()`
- State is managed in JavaScript variables (don't change variable names)
- LocalStorage keys: `gdd_chat_history`, `code_chat_history`
- Markdown rendering happens in JavaScript (code blocks, inline code)
- Dynamic content is created via `innerHTML` and `createElement()`
- CSS classes are toggled via `classList.add()`, `classList.remove()`, `classList.contains()`
- Queue processing uses async/await with sequential processing
- File uploads use FormData with `multipart/form-data`

**Think of this as a UI skin + layout overhaul, NOT a rewrite. The JavaScript is a black box that expects specific DOM structure and classes.**

---

## 🔍 VERIFICATION CHECKLIST

Before submitting, verify:
- [ ] All DOM IDs exist and are accessible
- [ ] All CSS classes used by JS are present
- [ ] All data attributes are preserved
- [ ] Document selection works (GDD RAG)
- [ ] File selection works (Code Q&A)
- [ ] Search filtering works in both sidebars
- [ ] Chat messages render correctly
- [ ] Markdown rendering works (code blocks, inline code)
- [ ] Query input with @patterns works
- [ ] Section dropdown appears and navigates with keyboard
- [ ] Document Explainer keyword search works
- [ ] Document Explainer checkbox selection works
- [ ] Document Explainer generate button enables/disables correctly
- [ ] Upload queue displays correctly
- [ ] Upload queue processes sequentially
- [ ] Upload queue shows correct status icons
- [ ] Document list displays correctly
- [ ] Delete and Re-index buttons work
- [ ] Tab switching works (both main tabs and internal tabs)
- [ ] All API calls use correct endpoints
- [ ] No JavaScript errors in console
- [ ] LocalStorage persistence works


"""
GDD Document Explainer backend functions.
EXACT COPY of logic from keyword_extractor - only adapted for Flask JSON responses.
"""
import json
import logging
import traceback
from typing import List, Dict, Optional, Any, Generator
from backend.services.search_service import keyword_search
from backend.services.explainer_service import explain_keyword
from backend.storage.keyword_storage import list_keyword_documents, find_keyword_by_alias

logger = logging.getLogger(__name__)


def _process_search_results(results: List[Dict], keyword: str, progress_messages: List[str] = None) -> Dict[str, Any]:
    """Process search results into the expected format."""
    doc_sections = {}
    
    for result in results:
        try:
            doc_id = result.get('doc_id')
            doc_name = result.get('doc_name', 'Unknown Document')
            section = result.get('section_heading')
            
            if not section or not section.strip():
                continue
            
            key = (doc_id, doc_name, section)
            if key not in doc_sections:
                doc_sections[key] = {
                    'doc_id': doc_id,
                    'doc_name': doc_name,
                    'section_heading': section,
                    'relevance': result.get('relevance', 0.0)
                }
        except Exception as e:
            logger.error(f"Error processing result: {e}", exc_info=True)
            continue
    
    sorted_items = sorted(
        doc_sections.values(),
        key=lambda x: x['relevance'],
        reverse=True
    )
    
    choices = []
    store_data = []
    
    for item in sorted_items:
        try:
            display_name = _extract_display_name(item['doc_name'])
            section_display = item['section_heading'] or "(No section)"
            choice_label = f"{display_name} → {section_display}"
            
            choices.append(choice_label)
            store_data.append({
                'doc_id': item['doc_id'],
                'section_heading': item['section_heading']
            })
        except Exception as e:
            logger.error(f"Error creating choice: {e}", exc_info=True)
            continue
    
    if progress_messages is not None:
        progress_messages.append(f"✅ Found {len(sorted_items)} document/section combinations!")
    
    return {
        'choices': choices,
        'store_data': store_data,
        'status_msg': f"✅ Found {len(sorted_items)} document/section combinations. Select which ones to explain.",
        'success': True,
        'keyword': keyword,
        'progress_messages': progress_messages or []
    }


def search_for_explainer(keyword: str) -> Dict[str, Any]:
    """
    Search for keyword and return results as checkboxes for selection.
    Includes automatic translation and synonym finding before falling back to LLM.
    
    Args:
        keyword: Search keyword
    
    Returns:
        Dict with 'choices', 'store_data', 'status_msg', 'keyword', 'progress_messages'
    """
    keyword_stripped = keyword.strip() if keyword else ""
    
    if not keyword_stripped:
        return {
            'choices': [],
            'store_data': [],
            'status_msg': "Please enter a keyword to search.",
            'success': False,
            'progress_messages': []
        }
    
    try:
        progress_messages = []
        
        # Step 1: Search database for original keyword AND its translation immediately
        results = _search_with_translation(keyword_stripped, progress_messages)
        if results:
            return _process_search_results(results, keyword_stripped, progress_messages)
        
        # Step 2: Search aliases for both original and translated keywords
        results = _search_aliases(keyword_stripped, progress_messages)
        if results:
            return _process_search_results(results, keyword_stripped, progress_messages)
        
        # Also check aliases for translated keyword
        try:
            from backend.services.translation_synonym_service import translate_with_google, detect_language_local
            trans_result = translate_with_google(keyword_stripped)
            if trans_result.get('success'):
                translation = trans_result.get('translated_text', '')
                if translation and translation.lower() != keyword_stripped.lower():
                    results = _search_aliases(translation, progress_messages)
                    if results:
                        return _process_search_results(results, keyword_stripped, progress_messages)
        except Exception:
            pass
        
        # Step 3: Try synonyms (if translation already done, reuse it)
        progress_messages.append("Not found.. Creating synonyms..")
        results = _try_translation_and_synonyms(keyword_stripped, progress_messages)
        if results:
            return _process_search_results(results, keyword_stripped, progress_messages)
        
        # Step 4: Try LLM deep search as final fallback
        results = _try_llm_deep_search(keyword_stripped, progress_messages)
        if results:
            return _process_search_results(results, keyword_stripped, progress_messages)
        
        # Step 5: No results found
        progress_messages.append("No results found after all search attempts")
        return {
            'choices': [],
            'store_data': [],
            'status_msg': "No results found even after trying translation, synonyms, and LLM search.",
            'success': True,
            'keyword': keyword_stripped,
            'progress_messages': progress_messages
        }
        
    except Exception as e:
        logger.error(f"Exception in search_for_explainer: {e}", exc_info=True)
        return {
            'choices': [],
            'store_data': [],
            'status_msg': f"❌ Error: {str(e)}",
            'success': False,
            'keyword': keyword_stripped,
            'progress_messages': []
        }


def generate_explanation(keyword: str, selected_choices: List[str], stored_results: List[Dict]) -> Dict[str, Any]:
    """
    Generate explanation from selected items.
    EXACT COPY from keyword_extractor - adapted to return dict instead of Gradio components.
    
    Args:
        keyword: Search keyword
        selected_choices: List of selected choice labels
        stored_results: Stored search results data
    
    Returns:
        Dict with 'explanation', 'source_chunks', 'metadata', 'success'
    """
    if not keyword or not keyword.strip():
        return {
            'explanation': "Please enter a keyword first.",
            'source_chunks': '',
            'metadata': '',
            'success': False
        }
    
    if not stored_results or len(stored_results) == 0:
        return {
            'explanation': "Please search for a keyword first.",
            'source_chunks': '',
            'metadata': '',
            'success': False
        }
    
    try:
        # Get selected items based on checkbox selection
        selected_items = []
        
        # Handle None or empty selected_choices
        if not selected_choices:
            selected_choices = []
        
        # Build choice label to item mapping from stored_results
        # This creates the valid choices set for validation
        choice_to_item = {}
        valid_choices = set()
        
        docs = list_keyword_documents()
        docs_dict = {doc.get('doc_id'): doc.get('name', 'Unknown') for doc in docs}
        
        for item in stored_results:
            doc_id = item.get('doc_id')
            section = item.get('section_heading')
            
            # Get doc_name from database for display
            doc_name = docs_dict.get(doc_id, 'Unknown')
            
            # Extract filename (same logic as search_for_explainer)
            display_name = doc_name
            if '\\' in display_name:
                display_name = display_name.split('\\')[-1]
            elif '/' in display_name:
                display_name = display_name.split('/')[-1]
            
            # Remove .pdf extension for cleaner display (must match search_for_explainer)
            if display_name.lower().endswith('.pdf'):
                display_name = display_name[:-4]
            
            section_display = section if section else "(No section)"
            choice_label = f"{display_name} → {section_display}"
            choice_to_item[choice_label] = {
                'doc_id': doc_id,
                'section_heading': section
            }
            valid_choices.add(choice_label)
        
        # Filter selected_choices to only include valid ones
        # This prevents errors when search results change between searches
        valid_selected_choices = [c for c in selected_choices if c in valid_choices]
        
        if not valid_selected_choices:
            return {
                'explanation': "Please select at least one document/section to explain. (Note: Previous selections were cleared due to new search results.)",
                'source_chunks': '',
                'metadata': '',
                'success': False
            }
        
        # Map valid selected choices to items
        for choice in valid_selected_choices:
            if choice in choice_to_item:
                selected_items.append(choice_to_item[choice])
        
        if not selected_items:
            return {
                'explanation': "Please select at least one document/section to explain.",
                'source_chunks': '',
                'metadata': '',
                'success': False
            }
        
        # Generate explanation
        result = explain_keyword(keyword.strip(), selected_items, use_hyde=True)
        
        if result.get('error'):
            return {
                'explanation': f"❌ Error: {result['error']}",
                'source_chunks': '',
                'metadata': '',
                'success': False
            }
        
        # Build explanation output
        explanation_text = f"## Explanation\n\n{result.get('explanation', 'No explanation generated.')}"
        
        # Build source chunks output
        source_chunks = result.get('source_chunks', [])
        chunks_text = f"### Source Chunks ({len(source_chunks)} chunks used)\n\n"
        for i, chunk in enumerate(source_chunks, 1):  # Show all chunks (no limit)
            section = chunk.get('section_heading') or 'No section'
            content = chunk.get('content') or ''
            content_preview = content[:200] if content else '(Empty chunk)'
            chunks_text += f"**Chunk {i}** (Section: {section})\n"
            chunks_text += f"{content_preview}...\n\n"
        
        # Build metadata output
        metadata_text = "### Metadata\n\n"
        metadata_text += f"- **HYDE Query:** {result.get('hyde_query', keyword)}\n"
        metadata_text += f"- **Language Detected:** {result.get('language', 'english')}\n"
        metadata_text += f"- **Chunks Used:** {result.get('chunks_used', 0)}\n"
        if result.get('hyde_timing'):
            timing = result['hyde_timing']
            if 'total_time' in timing:
                metadata_text += f"- **HYDE Timing:** {timing['total_time']}s\n"
        
        return {
            'explanation': explanation_text,
            'source_chunks': chunks_text,
            'metadata': metadata_text,
            'success': True
        }
        
    except Exception as e:
        import traceback
        return {
            'explanation': f"❌ Error generating explanation: {str(e)}\n\n{traceback.format_exc()}",
            'source_chunks': '',
            'metadata': '',
            'success': False
        }


def select_all_items(stored_results: List[Dict]) -> Dict[str, Any]:
    """
    Select all items - return all choice labels.
    EXACT COPY from keyword_extractor - adapted to return dict instead of Gradio components.
    
    Args:
        stored_results: Stored search results data
    
    Returns:
        Dict with 'choices' list
    """
    if not stored_results or len(stored_results) == 0:
        return {'choices': []}
    
    # Get document names from database
    docs = list_keyword_documents()
    docs_dict = {doc.get('doc_id'): doc.get('name', 'Unknown') for doc in docs}
    
    choices = []
    for item in stored_results:
        doc_id = item.get('doc_id')
        section = item.get('section_heading')
        
        doc_name = docs_dict.get(doc_id, 'Unknown')
        
        # Extract filename (same logic as search_for_explainer)
        display_name = doc_name
        if '\\' in display_name:
            display_name = display_name.split('\\')[-1]
        elif '/' in display_name:
            display_name = display_name.split('/')[-1]
        
        # Remove .pdf extension for cleaner display (must match search_for_explainer)
        if display_name.lower().endswith('.pdf'):
            display_name = display_name[:-4]
        
        section_display = section if section else "(No section)"
        choice_label = f"{display_name} → {section_display}"
        choices.append(choice_label)
    
    return {'choices': choices}


def select_none_items() -> Dict[str, Any]:
    """
    Deselect all items - return empty list.
    EXACT COPY from keyword_extractor - adapted to return dict instead of Gradio components.
    
    Returns:
        Dict with empty 'choices' list
    """
    return {'choices': []}


def _extract_display_name(doc_name: str) -> str:
    """Extract and clean display name from document path."""
    if '\\' in doc_name:
        display_name = doc_name.split('\\')[-1]
    elif '/' in doc_name:
        display_name = doc_name.split('/')[-1]
    else:
        display_name = doc_name
    
    if display_name.lower().endswith('.pdf'):
        display_name = display_name[:-4]
    
    return display_name


def _search_aliases(keyword: str, progress_messages: List[str] = None, emit: Optional[callable] = None) -> List[Dict]:
    """Search using alias dictionary. Returns results if found, empty list otherwise."""
    msg = f"Searching aliases for {keyword}"
    if emit:
        emit(msg)
    if progress_messages is not None:
        progress_messages.append(msg)
    
    alias_matches = find_keyword_by_alias(keyword.lower())
    
    if not alias_matches:
        return []
    
    # Search database for each base keyword from alias matches
    for match in alias_matches:
        base_keyword = match.get('keyword', '')
        if base_keyword and base_keyword != keyword.lower():  # Skip if already searched
            msg = f"Searching database for {base_keyword}"
            if emit:
                emit(msg)
            if progress_messages is not None:
                progress_messages.append(msg)
            
            results = keyword_search(base_keyword, limit=100)
            if results:
                msg = f"Found for {base_keyword}"
                if emit:
                    emit(msg)
                if progress_messages is not None:
                    progress_messages.append(msg)
                return results
    
    return []


def _search_database(keyword: str, progress_messages: List[str] = None, emit: Optional[callable] = None) -> List[Dict]:
    """Search database directly. Returns results if found, empty list otherwise."""
    msg = f"Searching database for {keyword}"
    if emit:
        emit(msg)
    if progress_messages is not None:
        progress_messages.append(msg)
    
    results = keyword_search(keyword, limit=100)
    if results:
        msg = f"Found for {keyword}"
        if emit:
            emit(msg)
        if progress_messages is not None:
            progress_messages.append(msg)
        return results
    return []


def _search_with_translation(keyword: str, progress_messages: List[str] = None, emit: Optional[callable] = None) -> List[Dict]:
    """Search for both original keyword and its translation. Returns combined results."""
    all_results = []
    seen_keys = set()
    
    # Step 1: Search for original keyword
    results = _search_database(keyword, progress_messages, emit)
    if results:
        for r in results:
            key = (r.get('doc_id'), r.get('section_heading'))
            if key not in seen_keys:
                all_results.append(r)
                seen_keys.add(key)
    
    # Step 2: Translate and search for translated keyword
    try:
        from backend.services.translation_synonym_service import translate_with_google, detect_language_local
        
        detected_lang = detect_language_local(keyword)
        msg = f"Translating {keyword} ({'Vietnamese' if detected_lang == 'vi' else 'English'} → {'English' if detected_lang == 'vi' else 'Vietnamese'})"
        if emit:
            emit(msg)
        if progress_messages is not None:
            progress_messages.append(msg)
        
        trans_result = translate_with_google(keyword)
        
        if trans_result.get('success'):
            translation = trans_result.get('translated_text', '')
            if translation and translation.lower() != keyword.lower():
                msg = f"Translation: {translation}"
                if emit:
                    emit(msg)
                if progress_messages is not None:
                    progress_messages.append(msg)
                
                # Search for translated keyword
                results = _search_database(translation, progress_messages, emit)
                if results:
                    for r in results:
                        key = (r.get('doc_id'), r.get('section_heading'))
                        if key not in seen_keys:
                            all_results.append(r)
                            seen_keys.add(key)
        
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
    
    return all_results


def _try_translation_and_synonyms(keyword: str, progress_messages: List[str] = None, emit: Optional[callable] = None) -> List[Dict]:
    """Try searching with synonyms (translation already done earlier). Returns results if found, empty list otherwise."""
    try:
        from backend.services.translation_synonym_service import auto_translate_and_find_synonyms
        
        trans_result = auto_translate_and_find_synonyms(keyword)
        
        if not trans_result.get('success'):
            logger.warning(f"Translation/synonym service failed: {trans_result.get('error', 'Translation failed')}")
            return []
        
        translation = trans_result.get('translation', '')
        synonyms_original = trans_result.get('synonyms_original', [])
        synonyms_translated = trans_result.get('synonyms_translated', [])
        
        # Try synonyms (translation already searched in _search_with_translation)
        all_synonyms = synonyms_original + synonyms_translated
        if all_synonyms:
            msg = f"Creating synonyms for {keyword} and for {translation}"
            if emit:
                emit(msg)
            if progress_messages is not None:
                progress_messages.append(msg)
            
            for synonym in all_synonyms:
                if not synonym or synonym == keyword or synonym == translation:
                    continue
                
                results = _search_aliases(synonym, progress_messages, emit)
                if results:
                    return results
                
                results = _search_database(synonym, progress_messages, emit)
                if results:
                    return results
        
        return []
        
    except Exception as e:
        logger.error(f"Error in synonym step: {e}", exc_info=True)
        return []


def _try_llm_deep_search(keyword: str, progress_messages: List[str] = None, emit: Optional[callable] = None) -> List[Dict]:
    """Try LLM-based deep search as final fallback. Returns results if found, empty list otherwise."""
    try:
        from backend.services.deep_search_service import deep_search_keyword
        
        msg = "Not found... Searching deeper with LLM"
        if emit:
            emit(msg)
        if progress_messages is not None:
            progress_messages.append(msg)
        
        # Deep search uses LLM to generate translations and synonyms
        result = deep_search_keyword(keyword)
        
        if result.get('found'):
            selected_keyword = result.get('selected_keyword', '')
            if selected_keyword:
                msg = f"LLM found potential match: {selected_keyword}"
                if emit:
                    emit(msg)
                if progress_messages is not None:
                    progress_messages.append(msg)
                
                # Search with the LLM-suggested keyword
                search_results = _search_aliases(selected_keyword, progress_messages, emit)
                if search_results:
                    return search_results
                
                search_results = _search_database(selected_keyword, progress_messages, emit)
                if search_results:
                    return search_results
        
        return []
        
    except Exception as e:
        logger.error(f"Error in LLM deep search: {e}", exc_info=True)
        return []


def search_for_explainer_stream(keyword: str) -> Generator[str, None, None]:
    """
    Stream search progress using Server-Sent Events (SSE).
    Yields messages one at a time as the search progresses.
    
    Args:
        keyword: Search keyword
    
    Yields:
        SSE-formatted messages
    """
    def emit(msg: str):
        """Emit a message in SSE format."""
        yield f"data: {json.dumps({'message': msg})}\n\n"
    
    keyword_stripped = keyword.strip() if keyword else ""
    
    if not keyword_stripped:
        yield from emit("Please enter a keyword.")
        yield from emit("__DONE__")
        return
    
    try:
        # Use a list to collect messages for emit callback
        message_list = []
        
        def emit_callback(msg: str):
            """Callback that collects messages for immediate yielding."""
            message_list.append(msg)
        
        # Step 1: Search database for original keyword AND its translation immediately
        results = _search_with_translation(keyword_stripped, emit=emit_callback)
        while message_list:
            yield from emit(message_list.pop(0))
        
        if results:
            yield from emit("__DONE__")
            return
        
        # Step 2: Search aliases for both original and translated keywords
        results = _search_aliases(keyword_stripped, emit=emit_callback)
        while message_list:
            yield from emit(message_list.pop(0))
        
        if results:
            yield from emit("__DONE__")
            return
        
        # Also check aliases for translated keyword
        try:
            from backend.services.translation_synonym_service import translate_with_google, detect_language_local
            trans_result = translate_with_google(keyword_stripped)
            if trans_result.get('success'):
                translation = trans_result.get('translated_text', '')
                if translation and translation.lower() != keyword_stripped.lower():
                    results = _search_aliases(translation, emit=emit_callback)
                    while message_list:
                        yield from emit(message_list.pop(0))
                    if results:
                        yield from emit("__DONE__")
                        return
        except Exception:
            pass
        
        # Step 3: Try automatic translation and synonyms
        yield from emit("Not found.. Translating..")
        
        results = _try_translation_and_synonyms(keyword_stripped, emit=emit_callback)
        while message_list:
            yield from emit(message_list.pop(0))
        
        if results:
            yield from emit("__DONE__")
            return
        
        # Step 4: Try LLM deep search as final fallback
        results = _try_llm_deep_search(keyword_stripped, emit=emit_callback)
        while message_list:
            yield from emit(message_list.pop(0))
        
        if results:
            yield from emit("__DONE__")
            return
        
        # Step 5: No results found
        yield from emit("No results found after all search attempts")
        yield from emit("__DONE__")
        
    except Exception as e:
        logger.error(f"Exception in search_for_explainer_stream: {e}", exc_info=True)
        yield from emit(f"❌ Error: {str(e)}")
        yield from emit("__DONE__")





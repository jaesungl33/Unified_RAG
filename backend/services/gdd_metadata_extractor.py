"""
GDD Metadata Extraction Service
Extracts version, author, and date from GDD document chunks.
"""

import re
from typing import Dict, Optional, List, Any


def extract_metadata_from_text(text: str) -> Dict[str, Optional[str]]:
    """
    Extract Version, Author (Người viết/Người tạo), and Date (Ngày tạo/Ngày cập nhật) from text using regex.
    Handles cases where fields may be on separate lines.
    
    Args:
        text: The chunk content text
        
    Returns:
        Dict with keys: 'version', 'author', 'date'
    """
    metadata = {
        'version': None,
        'author': None,
        'date': None
    }
    
    if not text:
        return metadata
    
    # Pattern for Version: "Version: v1.1" or "Phiên bản: v1.1"
    version_patterns = [
        r'Version\s*:\s*(v?\d+\.?\d*(?:\.\d+)?)',
        r'Version\s+(v?\d+\.?\d*(?:\.\d+)?)',
        r'Phiên\s+bản\s*:\s*(v?\d+\.?\d*(?:\.\d+)?)',
        r'Phiên\s+bản\s+(v?\d+\.?\d*(?:\.\d+)?)',
    ]
    
    for pattern in version_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            metadata['version'] = match.group(1).strip()
            break
    
    # Pattern for Author: "Người viết:", "Người tạo:", or "Người tạo file:"
    author_patterns = [
        r'Người\s+tạo\s+file\s*:\s*([^\n\r]*?)(?=\s+Ngày\s+(tạo|cập\s+nhật)|\s*\||\s*$)',
        r'Người\s+viết\s*:\s*(?:[^\w]*\s*)?([a-zA-Z0-9_]+)',
        r'Người\s+tạo\s*:\s*([^\n\r]*?)(?=\s+Ngày\s+(tạo|cập\s+nhật)|\s*\||\s*$)',
        r'Người\s+viết\s*:\s*([^\n\r]{0,100}?)(?:\s*\([^)]+\))?',
        r'Người\s+viết\s*:\s*\s*([a-zA-Z0-9_]+)',
        r'Người\s+tạo\s*:\s*\s*([a-zA-Z0-9_]+)',
    ]
    
    for pattern in author_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            author_text = match.group(1).strip()
            
            # First, try to extract from parentheses if present
            paren_match = re.search(r'\(([a-zA-Z0-9_]+)\)', author_text)
            if paren_match:
                metadata['author'] = paren_match.group(1).strip()
                break
            
            # Otherwise, extract username pattern
            author_clean = re.sub(r'\([^)]+\)', '', author_text).strip()
            username_match = re.search(r'\b([a-zA-Z0-9_]{3,20})\b', author_clean)
            if username_match:
                metadata['author'] = username_match.group(1).strip()
            else:
                fallback_match = re.search(r'([a-zA-Z0-9_]+)', author_clean)
                if fallback_match:
                    metadata['author'] = fallback_match.group(1).strip()
            if metadata['author']:
                break
    
    # Pattern for Date: "Ngày tạo:", "Ngày tạo file:", or "Ngày cập nhật:"
    date_patterns = [
        r'Ngày\s+tạo\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        r'Ngày\s+tạo\s+file\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        r'Ngày\s+cập\s+nhật\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        r'Ngày\s+tạo\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Ngày\s+tạo\s+file\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Ngày\s+cập\s+nhật\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Ngày\s+tạo\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'Ngày\s+tạo\s+file\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'Ngày\s+cập\s+nhật\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'Ngày\s+tạo\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
        r'Ngày\s+tạo\s+file\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
        r'Ngày\s+cập\s+nhật\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            date_text = match.group(1).strip()
            date_text = re.sub(r'\s+', ' ', date_text)
            metadata['date'] = date_text
            break
    
    return metadata


def extract_metadata_from_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Extract metadata from a list of chunks (typically first 3 chunks).
    Handles cases where metadata is split across chunk boundaries.
    
    Args:
        chunks: List of chunk dicts with 'content' and optionally 'chunk_index'
        
    Returns:
        Dict with keys: 'version', 'author', 'date'
    """
    metadata = {
        'version': None,
        'author': None,
        'date': None
    }
    
    if not chunks:
        return metadata
    
    # Strategy 1: Combine all chunks first for context-aware extraction
    combined_content = ' '.join([chunk.get('content', '').strip() for chunk in chunks])
    if combined_content:
        combined_metadata = extract_metadata_from_text(combined_content)
        metadata.update(combined_metadata)
    
    # Strategy 2: Try each chunk individually and handle cross-chunk splits
    for chunk_idx, chunk in enumerate(chunks):
        chunk_content = chunk.get('content', '')
        if not chunk_content:
            continue
        
        # Fill in missing fields
        chunk_metadata = extract_metadata_from_text(chunk_content)
        
        if not metadata['version'] and chunk_metadata['version']:
            metadata['version'] = chunk_metadata['version']
        
        if not metadata['author'] and chunk_metadata['author']:
            metadata['author'] = chunk_metadata['author']
        
        if not metadata['date'] and chunk_metadata['date']:
            metadata['date'] = chunk_metadata['date']
        
        # Handle cross-chunk splits
        if chunk_idx < len(chunks) - 1:
            next_chunk = chunks[chunk_idx + 1]
            next_chunk_content = next_chunk.get('content', '')
            
            # Check for author split
            if not metadata['author']:
                chunk_end = chunk_content.rstrip()[-100:] if len(chunk_content) > 100 else chunk_content.rstrip()
                if re.search(r'Người\s+(tạo|viết)(\s+file)?\s*:\s*$', chunk_end, re.IGNORECASE | re.MULTILINE):
                    next_start = next_chunk_content[:200].strip()
                    username_match = re.search(r'^([a-zA-Z0-9_]{3,30})(?:\s|$|\n|Ngày)', next_start, re.IGNORECASE | re.MULTILINE)
                    if username_match:
                        metadata['author'] = username_match.group(1).strip()
                    else:
                        combined = chunk_content.rstrip() + '\n' + next_chunk_content.lstrip()
                        combined_metadata = extract_metadata_from_text(combined)
                        if combined_metadata['author']:
                            metadata['author'] = combined_metadata['author']
            
            # Check for date split
            if not metadata['date']:
                chunk_end = chunk_content.rstrip()[-100:] if len(chunk_content) > 100 else chunk_content.rstrip()
                if re.search(r'Ngày\s+(tạo|cập\s+nhật)(\s+file)?\s*:\s*$', chunk_end, re.IGNORECASE | re.MULTILINE):
                    next_start = next_chunk_content[:200].strip()
                    date_match = re.search(r'^(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})', next_start, re.IGNORECASE | re.MULTILINE)
                    if date_match:
                        date_text = date_match.group(1).strip()
                        date_text = re.sub(r'\s+', ' ', date_text)
                        metadata['date'] = date_text
                    else:
                        combined = chunk_content.rstrip() + '\n' + next_chunk_content.lstrip()
                        combined_metadata = extract_metadata_from_text(combined)
                        if combined_metadata['date']:
                            metadata['date'] = combined_metadata['date']
        
        # If all fields found, we can stop early
        if all([metadata['version'], metadata['author'], metadata['date']]):
            break
    
    return metadata

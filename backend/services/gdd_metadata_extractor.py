"""
GDD Metadata Extraction Service
Extracts version, author, and date from GDD document chunks.
"""

import re
from typing import Dict, Optional, List, Any


def extract_metadata_from_version_table(text: str) -> Dict[str, Optional[str]]:
    """
    Extract version and author from version history table.
    Looks for tables with headers like "Phiên bản", "Ngày", "Mô tả", "Người viết"
    and extracts the latest version and author from the bottom row.
    
    Args:
        text: The chunk content text
        
    Returns:
        Dict with keys: 'version', 'author', 'date' (may be None)
    """
    metadata = {
        'version': None,
        'author': None,
        'date': None
    }
    
    if not text:
        return metadata
    
    # Pattern to detect version history table header
    # Look for "Phiên bản" (version) and "Người viết" (author) in the same line/area
    # This could be in markdown table format or plain text format
    
    # Try markdown table format first
    # Pattern: | Phiên bản | Ngày | Mô tả | Người viết | ...
    # More flexible: just check if header contains both "Phiên bản" and "Người viết"
    markdown_table_pattern = r'\|.*?Phiên\s*bản.*?Người\s*viết.*?\|'
    
    # Try plain text table format (tab or space separated)
    # Pattern: Phiên bản Ngày Mô tả Người viết
    # More flexible: allow header to span multiple lines
    plain_table_header_pattern = r'Phiên\s*bản.*?Ngày.*?Người\s*viết'
    
    # Check if we have a version history table
    has_table = False
    table_start = -1
    
    # Try markdown table
    markdown_match = re.search(markdown_table_pattern, text, re.IGNORECASE | re.DOTALL)
    if markdown_match:
        has_table = True
        table_start = markdown_match.start()
        # Extract table rows
        # Find all rows after the header
        table_section = text[table_start:]
        # Match markdown table rows: each line that starts and ends with |
        # Split by newlines and filter for table rows
        lines = table_section.split('\n')
        rows = []
        for line in lines:
            line = line.strip()
            if line.startswith('|') and line.endswith('|'):
                # Skip separator rows (|---|---|)
                if not re.match(r'^\|\s*[-:]+\s*\|', line):
                    rows.append(line)
                # Stop if we hit a non-table line after finding rows
            elif rows and line and not line.startswith('|'):
                break
        
        if len(rows) > 1:  # Header + at least one data row
            # Get the last row (latest version)
            last_row = rows[-1]
            # Extract version (first column after |)
            version_match = re.search(r'\|\s*(v?\d+\.?\d*(?:\.\d+)?)\s*\|', last_row, re.IGNORECASE)
            if version_match:
                metadata['version'] = version_match.group(1).strip()
            
            # Extract author (column with "Người viết" header)
            # Find column index of "Người viết" from header
            header_row = rows[0]
            header_cols = [col.strip() for col in header_row.split('|')[1:-1]]  # Remove first/last empty
            author_col_idx = None
            for idx, col in enumerate(header_cols):
                if re.search(r'Người\s*viết', col, re.IGNORECASE):
                    author_col_idx = idx
                    break
            
            if author_col_idx is not None:
                last_row_cols = [col.strip() for col in last_row.split('|')[1:-1]]
                if len(last_row_cols) > author_col_idx:
                    author_text = last_row_cols[author_col_idx]
                    # Extract username from author text
                    author_match = re.search(r'\b([a-zA-Z0-9_]{3,30})\b', author_text)
                    if author_match:
                        metadata['author'] = author_match.group(1).strip()
            
            # Extract date (column with "Ngày" header)
            date_col_idx = None
            for idx, col in enumerate(header_cols):
                if re.search(r'Ngày', col, re.IGNORECASE):
                    date_col_idx = idx
                    break
            
            if date_col_idx is not None:
                last_row_cols = [col.strip() for col in last_row.split('|')[1:-1]]
                if len(last_row_cols) > date_col_idx:
                    date_text = last_row_cols[date_col_idx]
                    # Extract date in format DD-MM-YYYY or DD/MM/YYYY
                    date_match = re.search(r'(\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4})', date_text)
                    if date_match:
                        date_text = date_match.group(1).strip()
                        date_text = re.sub(r'\s+', ' ', date_text)
                        metadata['date'] = date_text
    
    # Try plain text table format if markdown table not found
    if not has_table:
        # Try to find version history table header (may span multiple lines)
        # Look for "Phiên bản" followed by "Người viết" within reasonable distance
        plain_match = re.search(plain_table_header_pattern, text, re.IGNORECASE | re.DOTALL)
        if plain_match:
            has_table = True
            table_start = plain_match.start()
            
            # Extract the table section (first 2000 chars should be enough for version table)
            table_section = text[table_start:table_start + 2000]
            # Split into lines
            lines = table_section.split('\n')
            
            # Find data rows - rows might span multiple lines
            # Look for lines that start with version pattern, then collect following lines
            # until we hit another version pattern or end of table
            data_rows = []
            current_row_lines = []
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    # Empty line might be part of a multi-line row, continue collecting
                    if current_row_lines:
                        current_row_lines.append(line)
                    continue
                
                # Check if line starts with version pattern
                version_match = re.match(r'^\s*(v?\d+\.?\d*(?:\.\d+)?)', line_stripped, re.IGNORECASE)
                if version_match:
                    # If we have a previous row being collected, save it
                    if current_row_lines:
                        data_rows.append('\n'.join(current_row_lines))
                    # Start new row
                    current_row_lines = [line]
                elif current_row_lines:
                    # Check if this line looks like it belongs to the current row
                    # (contains date pattern, author pattern, or is continuation of description)
                    has_date = re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}', line_stripped)
                    has_author = re.search(r'\b([a-zA-Z0-9_]{3,30})\b', line_stripped)
                    # If line has date or author, or is short (likely continuation), add to current row
                    if has_date or has_author or len(line_stripped) < 50:
                        current_row_lines.append(line)
                    else:
                        # This looks like a new section, save current row and stop
                        if current_row_lines:
                            data_rows.append('\n'.join(current_row_lines))
                        current_row_lines = []
                        # Check if we've moved past the table (hit a section header or long text)
                        if len(line_stripped) > 50 and not re.search(r'^\d+\.', line_stripped):
                            break
            
            # Don't forget the last row
            if current_row_lines:
                data_rows.append('\n'.join(current_row_lines))
            
            if data_rows:
                # Extract all versions and find the latest one
                # Sometimes rows might be out of order, so we'll extract all and pick the highest version
                all_versions = []
                for row in data_rows:
                    row_text = row.replace('\n', ' ').strip()
                    version_match = re.search(r'\b(v?\d+\.?\d*(?:\.\d+)?)\b', row_text, re.IGNORECASE)
                    if version_match:
                        version_str = version_match.group(1).strip()
                        # Parse version number for comparison
                        version_num = version_str.lstrip('vV')
                        try:
                            # Try to parse as float for comparison
                            version_float = float(version_num)
                            all_versions.append((version_float, version_str, row_text))
                        except ValueError:
                            # If can't parse, just use the last one found
                            all_versions.append((0, version_str, row_text))
                
                # Initialize last_row
                last_row = None
                if all_versions:
                    # Sort by version number (descending) and get the latest
                    all_versions.sort(key=lambda x: x[0], reverse=True)
                    latest_version_str = all_versions[0][1]
                    last_row = all_versions[0][2]  # Use the row with the latest version
                    metadata['version'] = latest_version_str
                    
                    # Debug logging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"[Version Extraction] Found {len(all_versions)} versions: {[v[1] for v in all_versions]}, selected latest: {latest_version_str}")
                
                # Fallback: if no versions found or last_row not set, use the last row
                if not last_row:
                    last_row = data_rows[-1].replace('\n', ' ').strip()
                    # Extract version (first token) if not already extracted
                    if not metadata['version']:
                        version_match = re.match(r'^\s*(v?\d+\.?\d*(?:\.\d+)?)', last_row, re.IGNORECASE)
                        if version_match:
                            metadata['version'] = version_match.group(1).strip()
                
                # Try to parse as tab-separated or space-separated columns
                # Split by tabs first, then by multiple spaces
                if '\t' in last_row:
                    cols = [col.strip() for col in last_row.split('\t')]
                else:
                    # Split by 2+ spaces (table-like spacing)
                    cols = re.split(r'\s{2,}', last_row.strip())
                
                # If we have columns, try to identify them
                if len(cols) >= 3:
                    # Column 0: version (already extracted)
                    # Column 1: date
                    if len(cols) > 1:
                        date_match = re.search(r'(\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4})', cols[1])
                        if date_match:
                            date_text = date_match.group(1).strip()
                            date_text = re.sub(r'\s+', ' ', date_text)
                            metadata['date'] = date_text
                    
                    # Last column: author (typically)
                    if len(cols) > 2:
                        author_col = cols[-1].strip()
                        # Extract username from author column
                        author_match = re.search(r'\b([a-zA-Z0-9_]{3,30})\b', author_col)
                        if author_match:
                            metadata['author'] = author_match.group(1).strip()
                else:
                    # Fallback: extract date and author using regex patterns
                    date_match = re.search(r'(\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4})', last_row)
                    if date_match:
                        date_text = date_match.group(1).strip()
                        date_text = re.sub(r'\s+', ' ', date_text)
                        metadata['date'] = date_text
                    
                    # Extract author (last username-like token in the row)
                    username_matches = re.findall(r'\b([a-zA-Z0-9_]{3,30})\b', last_row)
                    if username_matches:
                        # The last username-like token is likely the author
                        # Skip common words that might appear
                        skip_words = {'file', 'tạo', 'hoàn', 'thành', 'mô', 'tả', 'người', 'review', 'viết'}
                        for username in reversed(username_matches):
                            if username.lower() not in skip_words:
                                metadata['author'] = username.strip()
                                break
    
    return metadata


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
    
    # Strategy 1: Try to extract from version history table first (most reliable)
    # This handles tables with version history where we want the latest version from the bottom row
    table_metadata = extract_metadata_from_version_table(text)
    if table_metadata['version'] or table_metadata['author'] or table_metadata['date']:
        # Use table metadata if found, but don't override existing values
        if table_metadata['version']:
            metadata['version'] = table_metadata['version']
        if table_metadata['author']:
            metadata['author'] = table_metadata['author']
        if table_metadata['date']:
            metadata['date'] = table_metadata['date']
        
        # If we got all fields from table, return early
        if all([metadata['version'], metadata['author'], metadata['date']]):
            return metadata
    
    # Strategy 2: Pattern-based extraction for non-table formats
    # If we didn't find version from table, try pattern-based extraction
    # Only look for versions in specific contexts (not random decimal numbers)
    if not metadata['version']:
        # More specific patterns - only match versions in context
        version_patterns = [
            r'Version\s*:\s*(v?\d+\.?\d*(?:\.\d+)?)',
            r'Version\s+(v?\d+\.?\d*(?:\.\d+)?)',
            r'Phiên\s*bản\s*mới\s*nhất\s*:\s*(v?\d+\.?\d*(?:\.\d+)?)',
            r'Phiên\s*bản\s*mới\s*nhất\s+(v?\d+\.?\d*(?:\.\d+)?)',
            r'Phiên\s*bản\s*:\s*(v?\d+\.?\d*(?:\.\d+)?)',
            r'Phiên\s*bản\s+(v?\d+\.?\d*(?:\.\d+)?)',
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                version_str = match.group(1).strip() if match.groups() else match.group(0).strip()
                if version_str:
                    metadata['version'] = version_str
                    break
    
    # Pattern for Author: "Người viết:", "Người tạo:", "Người tạo file:", or "Người soạn:"
    # Handle cases with/without spaces: "Người viết:" or "Ngườiviết:"
    # Extract ALL authors from the content between author title and date title
    # Handles list format: "- [x] phucth12\nthanhdv2\nlinhttd"
    author_patterns = [
        # "Người soạn:" - capture everything until date title (with or without spaces)
        r'Người\s*soạn\s*:\s*([\s\S]*?)(?=\s*Ngày\s*(tạo|cập\s*nhật|khởi\s*tạo)|\s*\||\s*$)',
        # "Người viết:" - capture everything until date title (with or without spaces)
        r'Người\s*viết\s*:\s*([\s\S]*?)(?=\s*Ngày\s*(tạo|cập\s*nhật|khởi\s*tạo)|\s*\||\s*$)',
        # "Người tạo file:" - capture everything until date title
        r'Người\s*tạo\s*file\s*:\s*([\s\S]*?)(?=\s*Ngày\s*(tạo|cập\s*nhật|khởi\s*tạo)|\s*\||\s*$)',
        # "Người tạo:" - capture everything until date title
        r'Người\s*tạo\s*:\s*([\s\S]*?)(?=\s*Ngày\s*(tạo|cập\s*nhật|khởi\s*tạo)|\s*\||\s*$)',
    ]
    
    for pattern in author_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            author_text = match.group(1).strip()
            
            if not author_text:
                continue
            
            # Extract all usernames from the author section
            # Handle multiple formats:
            # 1. List format: "- [x] phucth12\nthanhdv2\nlinhttd"
            # 2. Plain text: "phucth12\nthanhdv2\nlinhttd"
            # 3. With parentheses: "Kent (QuocTA)"
            
            authors = []
            
            # Split by newlines and process each line
            lines = author_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip if it's just a checkbox marker without username
                if re.match(r'^-\s*\[[x\s]\]\s*$', line):
                    continue
                
                # Extract username from list item: "- [x] phucth12" -> "phucth12"
                list_match = re.search(r'(?:-\s*\[[x\s]\]\s*)?([a-zA-Z0-9_]{3,30})', line)
                if list_match:
                    username = list_match.group(1).strip()
                    if username and username not in authors:
                        authors.append(username)
                    continue
                
                # Extract from parentheses first (preferred): "Kent (QuocTA)" -> "QuocTA"
                paren_match = re.search(r'\(([a-zA-Z0-9_]+)\)', line)
                if paren_match:
                    username = paren_match.group(1).strip()
                    if username and username not in authors:
                        authors.append(username)
                    # Also check for main name before parentheses
                    main_match = re.search(r'([a-zA-Z0-9_]{3,30})(?=\s*\()', line)
                    if main_match:
                        main_username = main_match.group(1).strip()
                        if main_username and main_username not in authors:
                            authors.append(main_username)
                    continue
                
                # Extract plain username from line
                username_match = re.search(r'\b([a-zA-Z0-9_]{3,30})\b', line)
                if username_match:
                    username = username_match.group(1).strip()
                    if username and username not in authors:
                        authors.append(username)
            
            # If we found authors, join them with comma and space
            if authors:
                metadata['author'] = ', '.join(authors)
                break
    
    # Pattern for Date: "Ngày tạo:", "Ngày tạo file:", "Ngày cập nhật:", or "Ngày khởi tạo:"
    # Handle cases with/without spaces: "Ngày tạo:" or "Ngàytạo:"
    # Handle newlines between label and colon: "Ngàytạo\n\n:07-09-2025"
    date_patterns = [
        # "Ngày khởi tạo:" - with or without spaces, handle "21 - 08 - 2025" format
        r'Ngày\s*khởi\s*tạo\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        # "Ngày tạo:" - with or without spaces, handle "09-09-2025" format
        r'Ngày\s*tạo\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        # "Ngày tạo file:" - with or without spaces
        r'Ngày\s*tạo\s*file\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        # "Ngày cập nhật:" - with or without spaces
        r'Ngày\s*cập\s*nhật\s*:\s*(\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{4})',
        # "Ngày khởi tạo:" - handle "21/08/2025" or "21-08-2025" format (no spaces in date)
        r'Ngày\s*khởi\s*tạo\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        # "Ngày tạo:" - handle "09/09/2025" or "09-09-2025" format (no spaces in date)
        r'Ngày\s*tạo\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Ngày\s*tạo\s*file\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Ngày\s*cập\s*nhật\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        # "Ngày khởi tạo:" - handle "21.08.2025" format
        r'Ngày\s*khởi\s*tạo\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        # "Ngày tạo:" - handle "09.09.2025" format
        r'Ngày\s*tạo\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'Ngày\s*tạo\s*file\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'Ngày\s*cập\s*nhật\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        # More flexible: any date format after colon
        r'Ngày\s*khởi\s*tạo\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
        r'Ngày\s*tạo\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
        r'Ngày\s*tạo\s*file\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
        r'Ngày\s*cập\s*nhật\s*:\s*(\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{4})',
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
    
    # Strategy 1: Try version table extraction first (most reliable for new format)
    # Combine all chunks with newlines to preserve table structure
    combined_content = '\n'.join([chunk.get('content', '').strip() for chunk in chunks])
    if combined_content:
        # Try version table extraction first - this should find the latest version
        table_metadata = extract_metadata_from_version_table(combined_content)
        if table_metadata['version'] or table_metadata['author'] or table_metadata['date']:
            # Table extraction found something - use it (it already picks the latest version)
            if table_metadata['version']:
                metadata['version'] = table_metadata['version']
            if table_metadata['author']:
                metadata['author'] = table_metadata['author']
            if table_metadata['date']:
                metadata['date'] = table_metadata['date']
            
            # If we got all fields from table, return early
            if all([metadata['version'], metadata['author'], metadata['date']]):
                return metadata
        
        # Fall back to pattern-based extraction (which also finds latest version)
        combined_metadata = extract_metadata_from_text(combined_content)
        # Only update if we don't already have values from table
        if not metadata['version'] and combined_metadata['version']:
            metadata['version'] = combined_metadata['version']
        if not metadata['author'] and combined_metadata['author']:
            metadata['author'] = combined_metadata['author']
        if not metadata['date'] and combined_metadata['date']:
            metadata['date'] = combined_metadata['date']
    
    # Strategy 2: Try each chunk individually and handle cross-chunk splits
    # Only do this if we haven't found all metadata yet
    # This is a fallback for cases where table extraction didn't work
    if not all([metadata['version'], metadata['author'], metadata['date']]):
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
                
                # Check for author split (handle both with/without spaces)
                if not metadata['author']:
                    chunk_end = chunk_content.rstrip()[-100:] if len(chunk_content) > 100 else chunk_content.rstrip()
                    if re.search(r'Người\s*(tạo|viết)(\s*file)?\s*:\s*$', chunk_end, re.IGNORECASE | re.MULTILINE):
                        # Combine chunks to extract all authors
                        combined = chunk_content.rstrip() + '\n' + next_chunk_content.lstrip()
                        combined_metadata = extract_metadata_from_text(combined)
                        if combined_metadata['author']:
                            metadata['author'] = combined_metadata['author']
                
                # Check for date split (handle both with/without spaces)
                if not metadata['date']:
                    chunk_end = chunk_content.rstrip()[-100:] if len(chunk_content) > 100 else chunk_content.rstrip()
                    if re.search(r'Ngày\s*(tạo|cập\s*nhật)(\s*file)?\s*:\s*$', chunk_end, re.IGNORECASE | re.MULTILINE):
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

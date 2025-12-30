"""
Complete reindexing script for C# codebase.
Scans Assets folder, extracts methods and classes, and indexes to Supabase.
Uses relative paths like Assets/scripts/foo.cs
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client
from backend.storage.code_supabase_storage import index_code_chunks_to_supabase
from backend.code_service import _analyze_csharp_file_symbols
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func

# Pattern to find type declarations (class, struct, interface, enum)
# Must be at start of line (after optional whitespace and attributes)
TYPE_DECL_PATTERN = re.compile(
    r'^[ \t]*(?:\[[^\]]+\]\s*)*'  # Optional whitespace and attributes at line start
    r'(?:public|private|protected|internal|abstract|sealed|static|partial)?\s*'
    r'(?P<kind>class|struct|interface|enum)\s+'
    r'(?P<name>\w+)',
    re.MULTILINE | re.IGNORECASE
)

def convert_to_relative_path(full_path: Path, project_root: Path) -> str:
    """
    Convert full Windows path to relative Assets/... path.
    
    Example:
        C:/Users/.../unified_rag_app/Assets/Scripts/Foo.cs
        -> Assets/Scripts/Foo.cs
    """
    try:
        # Get relative path from project root
        rel_path = full_path.relative_to(project_root)
        # Convert to forward slashes and ensure it starts with Assets/
        rel_str = str(rel_path).replace('\\', '/')
        
        # Ensure it starts with Assets/ (case-insensitive check)
        if not rel_str.lower().startswith('assets/'):
            # If it doesn't start with Assets/, try to find it
            parts = rel_str.split('/')
            if 'Assets' in parts or 'assets' in parts:
                idx = next(i for i, p in enumerate(parts) if p.lower() == 'assets')
                rel_str = '/'.join(parts[idx:])
            else:
                # Fallback: just use the path as-is
                pass
        
        return rel_str
    except Exception as e:
        print(f"   [!] Error converting path {full_path}: {e}")
        # Fallback: extract Assets/... portion
        path_str = str(full_path).replace('\\', '/')
        if 'Assets/' in path_str or 'assets/' in path_str:
            idx = path_str.lower().find('assets/')
            return path_str[idx:]
        return str(full_path)

def find_type_declarations(code_text: str) -> List[Dict[str, Any]]:
    """
    Find all type declarations (class, struct, interface, enum) in C# code.
    Returns list of dicts with 'kind', 'name', 'start', 'end' positions.
    Only matches at the start of lines (after optional whitespace/attributes).
    """
    types = []
    
    for match in TYPE_DECL_PATTERN.finditer(code_text):
        kind = match.group("kind").lower()
        name = match.group("name")
        start_pos = match.start()
        
        # The regex already requires ^ (start of line) with MULTILINE flag,
        # so matches should only occur at line starts. We trust the regex anchor.
        # The main protection against false matches (like in strings) is the ^ anchor.
        
        # Find the opening brace (or semicolon for enum without body)
        search_start = match.end()
        brace_pos = code_text.find("{", search_start)
        semicolon_pos = code_text.find(";", search_start)
        
        # Handle enum without body
        if kind == "enum":
            if semicolon_pos != -1 and (brace_pos == -1 or semicolon_pos < brace_pos):
                end_pos = semicolon_pos + 1
                types.append({
                    "kind": kind,
                    "name": name,
                    "start": start_pos,
                    "end": end_pos,
                    "is_partial": "partial" in match.group(0).lower(),
                })
                continue
        
        # For types with body, find matching closing brace
        if brace_pos == -1:
            continue
        
        # Find matching closing brace
        brace_count = 1
        pos = brace_pos + 1
        
        while pos < len(code_text) and brace_count > 0:
            char = code_text[pos]
            
            # Handle string literals (skip braces inside strings)
            if char == '"':
                # Check for verbatim string @"..."
                if pos > 0 and code_text[pos - 1] == '@':
                    # Verbatim string - skip to next unescaped "
                    pos += 1
                    while pos < len(code_text):
                        if code_text[pos] == '"' and (pos + 1 >= len(code_text) or code_text[pos + 1] != '"'):
                            # Found closing quote (not escaped "")
                            break
                        pos += 1
                else:
                    # Regular string - skip to next unescaped "
                    pos += 1
                    while pos < len(code_text) and code_text[pos] != '"':
                        if code_text[pos] == '\\':
                            pos += 1  # Skip escaped character
                        pos += 1
            elif char == "'":
                # Character literal - skip to next unescaped '
                pos += 1
                while pos < len(code_text) and code_text[pos] != "'":
                    if code_text[pos] == '\\':
                        pos += 1  # Skip escaped character
                    pos += 1
            elif char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            
            pos += 1
        
        if brace_count == 0:
            end_pos = pos
            types.append({
                "kind": kind,
                "name": name,
                "start": start_pos,
                "end": end_pos,
                "is_partial": "partial" in match.group(0).lower(),
            })
        elif pos >= len(code_text):
            # Reached end of file without finding matching brace
            # This can happen if file is incomplete or has braces in strings
            # Try to find the last closing brace that would close this type
            # (usually the second-to-last closing brace, before namespace closes)
            last_closing_brace = code_text.rfind('}')
            if last_closing_brace > brace_pos:
                # Use the last closing brace as fallback
                end_pos = last_closing_brace + 1
                types.append({
                    "kind": kind,
                    "name": name,
                    "start": start_pos,
                    "end": end_pos,
                    "is_partial": "partial" in match.group(0).lower(),
                })
                print(f"   ⚠️  Warning: Could not find exact matching brace for {kind} {name}, using fallback (end of file)")
    
    return types

def extract_method_code(code_text: str, method: Dict[str, Any]) -> str:
    """
    Extract the full method code including body.
    """
    signature = method.get('signature', '')
    if not signature:
        return ''
    
    # Find signature in code
    sig_start = code_text.find(signature)
    if sig_start == -1:
        return signature  # Return signature only if body not found
    
    # Find opening brace after signature
    brace_start = code_text.find('{', sig_start + len(signature))
    if brace_start == -1:
        # Expression-bodied method (=>)
        arrow_pos = code_text.find('=>', sig_start + len(signature))
        if arrow_pos != -1:
            # Find end of expression (semicolon or newline)
            end_pos = code_text.find(';', arrow_pos)
            if end_pos != -1:
                return code_text[sig_start:end_pos + 1]
        return signature
    
    # Find matching closing brace
    brace_count = 1
    pos = brace_start + 1
    
    while pos < len(code_text) and brace_count > 0:
        char = code_text[pos]
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        elif char == '"' or char == "'":
            quote_char = char
            pos += 1
            while pos < len(code_text) and code_text[pos] != quote_char:
                if code_text[pos] == '\\':
                    pos += 1
                pos += 1
        pos += 1
    
    if brace_count == 0:
        return code_text[sig_start:pos]
    
    return signature

def build_method_chunks(code_text: str, file_path: str, file_name: str) -> List[Dict[str, Any]]:
    """
    Build method chunks from parsed methods.
    """
    methods, fields, properties = _analyze_csharp_file_symbols(code_text)
    chunks = []
    
    for method in methods:
        method_code = extract_method_code(code_text, method)
        
        # Find class name (look for class declaration before this method)
        class_name = None
        method_pos = code_text.find(method.get('signature', ''))
        if method_pos != -1:
            # Search backwards for class declaration
            before_code = code_text[:method_pos]
            class_match = re.search(r'class\s+(\w+)', before_code)
            if class_match:
                class_name = class_match.group(1)
        
        chunk = {
            'chunk_type': 'method',
            'name': method.get('name'),
            'class_name': class_name,
            'code': method_code,
            'source_code': method_code,
            'signature': method.get('signature', ''),
            'doc_comment': method.get('doc_comment', ''),
            'metadata': {
                'line': method.get('line', 1)
            }
        }
        chunks.append(chunk)
    
    return chunks

def build_class_like_chunks(code_text: str, file_path: str, file_name: str) -> List[Dict[str, Any]]:
    """
    Build chunks for classes, structs, interfaces, and enums.
    """
    types = find_type_declarations(code_text)
    methods, fields, properties = _analyze_csharp_file_symbols(code_text)
    chunks = []
    
    for type_info in types:
        kind = type_info['kind']
        name = type_info['name']
        start = type_info['start']
        end = type_info['end']
        
        # Extract type source code
        type_code = code_text[start:end]
        
        # Extract methods that belong to this type
        type_methods = []
        for method in methods:
            method_pos = code_text.find(method.get('signature', ''))
            if method_pos is not None and start <= method_pos < end:
                type_methods.append(method.get('signature', ''))
        
        # Format source code with context
        formatted_code = f"File: {file_path}\n\n{type_code}"
        
        chunk = {
            'chunk_type': kind,  # 'class', 'struct', 'interface', 'enum'
            'class_name': name,
            'source_code': formatted_code,
            'code': None,  # Only methods have 'code'
            'method_declarations': '\n'.join(type_methods) if type_methods else '',
            'metadata': {
                'is_partial': type_info.get('is_partial', False),
                'kind': kind
            }
        }
        chunks.append(chunk)
    
    return chunks

def walk_cs_files(root: Path) -> List[Path]:
    """Recursively find all .cs files in Assets folder."""
    cs_files = []
    assets_path = root / 'Assets'
    
    if not assets_path.exists():
        print(f"[!] Assets folder not found at {assets_path}")
        return []
    
    for cs_file in assets_path.rglob('*.cs'):
        cs_files.append(cs_file)
    
    return sorted(cs_files)

def main():
    print("=" * 80)
    print("Complete Codebase Reindexing")
    print("=" * 80)
    print("\nThis script will:")
    print("  1. Scan Assets folder for all .cs files")
    print("  2. Extract methods and classes/structs/interfaces/enums")
    print("  3. Index everything to Supabase with relative paths (Assets/...)")
    print("\n[!] Make sure you have a fresh Supabase database!")
    print("=" * 80)
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    try:
        client = get_supabase_client(use_service_key=True)
        provider = QwenProvider()
        
        # Find all .cs files
        print("\n[1/4] Scanning Assets folder...")
        cs_files = walk_cs_files(PROJECT_ROOT)
        print(f"   Found {len(cs_files)} .cs files")
        
        if not cs_files:
            print("   [!] No .cs files found!")
            return
        
        # Process files
        print("\n[2/4] Processing files...")
        total_method_chunks = 0
        total_class_chunks = 0
        processed = 0
        failed = 0
        
        for i, cs_file in enumerate(cs_files, 1):
            try:
                # Convert to relative path
                relative_path = convert_to_relative_path(cs_file, PROJECT_ROOT)
                
                print(f"\n[{i}/{len(cs_files)}] Processing: {cs_file.name}")
                print(f"   Path: {relative_path}")
                
                # Read file
                code_text = cs_file.read_text(encoding='utf-8', errors='ignore')
                
                # Extract methods
                method_chunks = build_method_chunks(code_text, relative_path, cs_file.name)
                print(f"   Found {len(method_chunks)} method(s)")
                
                # Extract classes/structs/interfaces/enums
                class_chunks = build_class_like_chunks(code_text, relative_path, cs_file.name)
                print(f"   Found {len(class_chunks)} class-like type(s)")
                
                # Index methods
                if method_chunks:
                    success = index_code_chunks_to_supabase(
                        file_path=relative_path,
                        file_name=cs_file.name,
                        chunks=method_chunks,
                        provider=provider
                    )
                    if success:
                        total_method_chunks += len(method_chunks)
                
                # Index classes
                if class_chunks:
                    success = index_code_chunks_to_supabase(
                        file_path=relative_path,
                        file_name=cs_file.name,
                        chunks=class_chunks,
                        provider=provider
                    )
                    if success:
                        total_class_chunks += len(class_chunks)
                
                processed += 1
                
                # Progress update every 50 files
                if i % 50 == 0:
                    print(f"\n   Progress: {i}/{len(cs_files)} files processed")
                    print(f"   Methods indexed: {total_method_chunks}, Classes indexed: {total_class_chunks}")
                
            except Exception as e:
                print(f"   [!] Error processing {cs_file.name}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("[3/4] Indexing Complete!")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"   Files processed: {processed}")
        print(f"   Files failed: {failed}")
        print(f"   Total method chunks indexed: {total_method_chunks}")
        print(f"   Total class-like chunks indexed: {total_class_chunks}")
        print(f"   Total chunks: {total_method_chunks + total_class_chunks}")
        
        # Verify
        print("\n[4/4] Verifying...")
        result = client.table('code_chunks').select('chunk_type').execute()
        if result.data:
            type_counts = {}
            for row in result.data:
                chunk_type = row['chunk_type']
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            
            print("\n   Chunk type counts in Supabase:")
            for chunk_type, count in sorted(type_counts.items()):
                print(f"      {chunk_type}: {count}")
        
        print("\n[OK] Reindexing complete!")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


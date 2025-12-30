"""
Reindex ONLY class chunks for files that are missing them.

This script:
1. Checks all files in code_files table
2. Identifies files with 0 class chunks
3. Reindexes ONLY class chunks for those files (method chunks are left untouched)
4. Uses regex-based parsing (self-contained, no external dependencies)

Usage:
    cd unified_rag_app
    python -m scripts.reindex_class_chunks_only
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client, insert_code_chunks
from backend.storage.code_supabase_storage import normalize_path_consistent
from backend.code_service import _analyze_csharp_file_symbols
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func


def get_files_missing_class_chunks() -> List[Dict[str, Any]]:
    """Get all files that have 0 class chunks in Supabase"""
    client = get_supabase_client()
    
    # Get all files
    files_result = client.table("code_files").select("file_path,file_name").execute()
    all_files = files_result.data if files_result.data else []
    
    files_missing_class_chunks = []
    
    print(f"Checking {len(all_files)} files for missing class chunks...")
    
    for file_info in all_files:
        file_path = file_info.get("file_path")
        
        # Check if this file has any class chunks
        chunks_result = (
            client.table("code_chunks")
            .select("id")
            .eq("file_path", file_path)
            .eq("chunk_type", "class")
            .limit(1)
            .execute()
        )
        
        class_chunk_count = len(chunks_result.data) if chunks_result.data else 0
        
        if class_chunk_count == 0:
            files_missing_class_chunks.append(file_info)
    
    return files_missing_class_chunks


def get_file_source_from_supabase(file_path: str) -> Optional[str]:
    """
    Get the full source code for a file from Supabase chunks.
    On Render, we can't read from local disk, so we reconstruct from existing chunks.
    
    Note: If a file has 0 chunks, we can't get the source code. This is expected for
    files that were never indexed. Those files will be skipped.
    """
    client = get_supabase_client()
    
    # Get all chunks for this file (both method and class chunks)
    chunks_result = (
        client.table("code_chunks")
        .select("source_code,code,chunk_type")
        .eq("file_path", file_path)
        .execute()
    )
    
    chunks = chunks_result.data if chunks_result.data else []
    
    if not chunks:
        # File has no chunks at all - can't reconstruct source code
        return None
    
    # Try to reconstruct full file from method chunks
    # Method chunks should have enough context to extract class definitions
    method_chunks = [c for c in chunks if c.get("chunk_type") == "method"]
    
    if method_chunks:
        # Method chunks have 'source_code' which may contain class context
        # Collect all unique source_code snippets
        source_parts = []
        seen_sources = set()
        
        for chunk in method_chunks:
            source_code = chunk.get("source_code", "") or chunk.get("code", "")
            if source_code and source_code not in seen_sources:
                source_parts.append(source_code)
                seen_sources.add(source_code)
        
        if source_parts:
            # Combine method source codes - this should contain class definitions
            # The source_code field in method chunks often includes the class context
            combined = "\n\n".join(source_parts)
            
            # If the combined source is substantial, use it
            if len(combined) > 100:  # At least 100 characters
                return combined
    
    return None


def extract_class_source_code(code_text: str, class_name: str) -> Optional[str]:
    """
    Extract the full source code for a class using regex.
    Finds the class declaration and extracts everything until the matching closing brace.
    """
    import re
    
    # Pattern to find class declaration
    # Matches: public class ClassName { ... }
    class_pattern = re.compile(
        r'(?:^|\n)\s*(?:\[[^\]]+\]\s*)*'  # Optional attributes
        r'(?:public|private|protected|internal|abstract|sealed|static)?\s*'
        r'(?:partial\s+)?'
        r'class\s+' + re.escape(class_name) + r'\s*'
        r'(?:[^{]*\{)',
        re.MULTILINE | re.IGNORECASE
    )
    
    match = class_pattern.search(code_text)
    if not match:
        return None
    
    # Find the opening brace
    start_pos = match.end() - 1  # Position of opening brace
    brace_count = 1
    pos = start_pos + 1
    
    # Find matching closing brace
    while pos < len(code_text) and brace_count > 0:
        if code_text[pos] == '{':
            brace_count += 1
        elif code_text[pos] == '}':
            brace_count -= 1
        pos += 1
    
    if brace_count == 0:
        # Extract from class declaration start to closing brace
        class_start = match.start()
        return code_text[class_start:pos]
    
    return None


def parse_file_for_class_chunks(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a C# file and extract class chunks using regex (self-contained, no external files).
    Gets source code from Supabase chunks (works on Render where local files aren't available).
    Returns list of class chunk dictionaries ready for Supabase.
    """
    # Get source code from Supabase (no local disk reads)
    code_text = get_file_source_from_supabase(file_path)
    
    if not code_text:
        print(f"  ⚠️  Could not get source code from Supabase for: {file_path}")
        print(f"      This file has no chunks in Supabase, so we can't extract class definitions.")
        print(f"      Files with no chunks at all cannot be reindexed (they need to be indexed first).")
        return []
    
    try:
        
        # Use existing regex parser to find classes, methods, fields, properties
        methods, fields, properties = _analyze_csharp_file_symbols(code_text)
        
        # Extract class names from methods (methods belong to classes)
        # Also look for class declarations directly
        import re
        class_names = set()
        
        # Find all class declarations in the file
        class_decl_pattern = re.compile(
            r'(?:^|\n)\s*(?:\[[^\]]+\]\s*)*'
            r'(?:public|private|protected|internal|abstract|sealed|static|partial)?\s*'
            r'class\s+(\w+)',
            re.MULTILINE | re.IGNORECASE
        )
        
        for match in class_decl_pattern.finditer(code_text):
            class_name = match.group(1)
            class_names.add(class_name)
        
        if not class_names:
            print(f"  ⚠️  No classes found in source code")
            return []
        
        # Create class chunks - one per class
        class_chunks = []
        for class_name in class_names:
            # Extract full class source code
            class_source = extract_class_source_code(code_text, class_name)
            
            if not class_source:
                # Fallback: use a larger context around the class declaration
                class_match = class_decl_pattern.search(code_text)
                if class_match:
                    # Extract from class declaration to end of file (or next class)
                    start_pos = class_match.start()
                    # Find next class or end of file
                    next_class_match = class_decl_pattern.search(code_text, start_pos + 1)
                    end_pos = next_class_match.start() if next_class_match else len(code_text)
                    class_source = code_text[start_pos:end_pos]
                else:
                    class_source = ""  # Empty if we can't find it
            
            # Extract method declarations for this class
            # Methods that belong to this class (we can infer from context)
            method_declarations = []
            for method in methods:
                # Simple heuristic: if method appears after class declaration, it might belong to it
                # For now, we'll include all methods in the file
                method_declarations.append(method.get('signature', method.get('name', '')))
            
            chunk = {
                "file_path": file_path,  # Keep original Supabase path for consistency
                "chunk_type": "class",
                "class_name": class_name,
                "method_name": None,
                "source_code": class_source,
                "code": None,  # Class chunks don't have separate 'code' field
                "doc_comment": None,
                "constructor_declaration": "",  # Could extract if needed
                "method_declarations": "\n-----\n".join(method_declarations) if method_declarations else "",
                "references": "",
                "metadata": {
                    "indexed_from": "class_reindex_regex",
                    "reindexed_at": str(Path(__file__).stat().st_mtime)
                }
            }
            
            class_chunks.append(chunk)
        
        return class_chunks
    
    except Exception as e:
        print(f"  ❌ Error parsing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return []


def reindex_class_chunks_for_file(file_info: Dict[str, Any], provider) -> int:
    """
    Reindex class chunks for a single file.
    Returns number of class chunks inserted.
    """
    file_path = file_info.get("file_path")
    file_name = file_info.get("file_name")
    
    print(f"\n📄 Processing: {file_name}")
    print(f"   Path: {file_path}")
    
    # Parse file to get class chunks
    class_chunks = parse_file_for_class_chunks(file_path)
    
    if not class_chunks:
        print(f"   ⚠️  No class chunks extracted")
        return 0
    
    print(f"   ✅ Extracted {len(class_chunks)} class chunk(s)")
    
    # Normalize paths
    normalized_path = normalize_path_consistent(file_path)
    
    # Generate embeddings and prepare for Supabase
    embedding_func = make_embedding_func(provider)
    supabase_chunks = []
    
    for chunk in class_chunks:
        source_code = chunk.get("source_code", "")
        if not source_code:
            continue
        
        # Generate embedding
        try:
            embedding = embedding_func([source_code])[0]
        except Exception as e:
            print(f"   ⚠️  Failed to embed class {chunk.get('class_name')}: {e}")
            continue
        
        # Update chunk with normalized path and embedding
        supabase_chunk = {
            **chunk,
            "file_path": normalized_path or file_path,
            "embedding": embedding
        }
        
        supabase_chunks.append(supabase_chunk)
    
    if not supabase_chunks:
        print(f"   ⚠️  No valid chunks to insert (embedding generation failed)")
        return 0
    
    # Insert chunks
    try:
        inserted_count = insert_code_chunks(supabase_chunks)
        print(f"   ✅ Inserted {inserted_count} class chunk(s)")
        return inserted_count
    except Exception as e:
        print(f"   ❌ Error inserting chunks: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main reindexing function"""
    print("=" * 80)
    print("🔄 Reindex Class Chunks Only")
    print("=" * 80)
    print("\nThis script will:")
    print("  1. Find all files with 0 class chunks")
    print("  2. Reindex ONLY class chunks for those files")
    print("  3. Leave method chunks untouched")
    print()
    
    # Get files missing class chunks
    files_missing = get_files_missing_class_chunks()
    
    if not files_missing:
        print("✅ All files already have class chunks!")
        return
    
    print(f"\n📊 Found {len(files_missing)} files missing class chunks")
    print(f"\nFirst 10 files:")
    for i, file_info in enumerate(files_missing[:10], 1):
        print(f"  {i}. {file_info.get('file_name')} ({file_info.get('file_path')})")
    if len(files_missing) > 10:
        print(f"  ... and {len(files_missing) - 10} more")
    
    # Confirm
    print(f"\n⚠️  This will reindex class chunks for {len(files_missing)} files")
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Reindexing cancelled")
        return
    
    # Initialize provider
    provider = QwenProvider()
    
    # Reindex each file
    print(f"\n🔄 Starting reindexing...")
    total_inserted = 0
    successful = 0
    failed = 0
    
    for idx, file_info in enumerate(files_missing, 1):
        print(f"\n[{idx}/{len(files_missing)}] ", end="")
        try:
            inserted = reindex_class_chunks_for_file(file_info, provider)
            if inserted > 0:
                total_inserted += inserted
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ Reindexing Complete!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Files processed: {len(files_missing)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Total class chunks inserted: {total_inserted}")
    print(f"\n💡 Next steps:")
    print(f"   1. Run check_supabase_code_files_retrieval.py to verify")
    print(f"   2. Test 'list all variables' queries to ensure global variables work")


if __name__ == "__main__":
    main()


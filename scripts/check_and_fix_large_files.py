"""
Check large C# files for correct class chunking.
Fix if possible, otherwise remove from Supabase and record in JSON.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client
from backend.storage.code_supabase_storage import index_code_chunks_to_supabase
from gdd_rag_backbone.llm_providers import QwenProvider
from scripts.reindex_complete_codebase import find_type_declarations, build_class_like_chunks

# Pattern to find type declarations
TYPE_DECL_PATTERN = re.compile(
    r'^[ \t]*(?:\[[^\]]+\]\s*)*'  # Optional whitespace and attributes at line start
    r'(?:public|private|protected|internal|abstract|sealed|static|partial)?\s*'
    r'(?P<kind>class|struct|interface|enum)\s+'
    r'(?P<name>\w+)',
    re.MULTILINE | re.IGNORECASE
)

def find_classes_in_file(file_path: str) -> List[Dict[str, str]]:
    """Find all class declarations in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code_text = f.read()
    except Exception as e:
        return []
    
    classes = []
    for match in TYPE_DECL_PATTERN.finditer(code_text):
        kind = match.group("kind").lower()
        if kind == "class":  # Only classes
            name = match.group("name")
            classes.append({"kind": kind, "name": name})
    
    return classes

def get_class_chunks_from_supabase(file_path: str) -> List[Dict[str, Any]]:
    """Get all class chunks from Supabase for a file."""
    client = get_supabase_client(use_service_key=True)
    
    try:
        response = client.table('code_chunks').select(
            'chunk_type, class_name'
        ).eq('file_path', file_path).eq('chunk_type', 'class').execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"     Error querying Supabase: {e}")
        return []

def check_file_chunking(file_path: str, full_path: str) -> Dict[str, Any]:
    """
    Check if a file's class chunks are correct.
    Returns dict with status and details.
    """
    result = {
        "file_path": file_path,
        "status": "unknown",
        "classes_in_file": [],
        "classes_in_supabase": [],
        "missing": [],
        "extra": [],
        "is_correct": False,
        "error": None
    }
    
    if not os.path.exists(full_path):
        result["status"] = "file_not_found"
        result["error"] = f"File not found: {full_path}"
        return result
    
    # Find classes in actual file
    try:
        result["classes_in_file"] = find_classes_in_file(full_path)
    except Exception as e:
        result["status"] = "error_reading"
        result["error"] = f"Error reading file: {e}"
        return result
    
    # Get classes from Supabase
    try:
        supabase_chunks = get_class_chunks_from_supabase(file_path)
        result["classes_in_supabase"] = [c.get('class_name') for c in supabase_chunks]
    except Exception as e:
        result["status"] = "error_querying"
        result["error"] = f"Error querying Supabase: {e}"
        return result
    
    # Compare
    file_class_names = {c["name"] for c in result["classes_in_file"]}
    supabase_class_names = set(result["classes_in_supabase"])
    
    result["missing"] = list(file_class_names - supabase_class_names)
    result["extra"] = list(supabase_class_names - file_class_names)
    
    if not result["missing"] and not result["extra"]:
        result["status"] = "correct"
        result["is_correct"] = True
    else:
        result["status"] = "incorrect"
        result["is_correct"] = False
    
    return result

def attempt_fix(file_path: str, full_path: str) -> Dict[str, Any]:
    """
    Attempt to fix chunking for a file by reindexing.
    Returns dict with success status and details.
    """
    result = {
        "success": False,
        "error": None,
        "chunks_indexed": 0
    }
    
    if not os.path.exists(full_path):
        result["error"] = "File not found"
        return result
    
    try:
        # Read file
        with open(full_path, 'r', encoding='utf-8') as f:
            code_text = f.read()
        
        file_name = Path(full_path).name
        
        # Find all type declarations
        types = find_type_declarations(code_text)
        class_types = [t for t in types if t['kind'] == 'class']
        
        if not class_types:
            result["error"] = "No classes found in file"
            return result
        
        # Build class chunks (only classes)
        chunks = []
        for type_info in class_types:
            type_code = code_text[type_info['start']:type_info['end']]
            chunk = {
                'chunk_type': 'class',
                'class_name': type_info['name'],
                'source_code': f"File: {file_path}\n\n{type_code}",
                'code': type_code,
                'metadata': {
                    'is_partial': type_info.get('is_partial', False)
                }
            }
            chunks.append(chunk)
        
        # Initialize provider
        try:
            provider = QwenProvider()
        except Exception as e:
            result["error"] = f"Error initializing QwenProvider: {e}"
            return result
        
        # Test embedding with first chunk to see if file is too big
        # If embedding fails immediately, assume file is too large
        first_chunk_size = len(chunks[0].get('source_code', ''))
        print(f"     Testing embedding with first chunk ({first_chunk_size:,} chars)...")
        try:
            # Test with actual first chunk (not truncated) to see if it's too large
            test_text = chunks[0].get('source_code', '')
            test_embedding = provider.embed([test_text])
            print(f"     ✓ Embedding test successful")
        except Exception as e:
            error_msg = str(e)
            print(f"     ❌ Embedding test failed (file too large): {error_msg}")
            result["error"] = f"File too large for embedding: {error_msg}"
            return result
        
        # Delete existing class chunks first
        client = get_supabase_client(use_service_key=True)
        try:
            client.table('code_chunks').delete().eq('file_path', file_path).eq('chunk_type', 'class').execute()
        except Exception as e:
            print(f"     Warning: Error deleting old chunks: {e}")
        
        # Index to Supabase (with single attempt, no retries for large files)
        try:
            # Temporarily disable retries by modifying the embedding function
            # We'll catch embedding errors and stop immediately
            success = index_code_chunks_to_supabase(
                file_path=file_path,
                file_name=file_name,
                chunks=chunks,
                provider=provider
            )
            
            if success:
                result["success"] = True
                result["chunks_indexed"] = len(chunks)
            else:
                result["error"] = "index_code_chunks_to_supabase returned False"
        except Exception as e:
            result["error"] = f"Error indexing: {str(e)}"
            # Check if it's an embedding error
            if "embedding" in str(e).lower() or "api" in str(e).lower() or "connection" in str(e).lower():
                result["error"] = f"File too large for embedding: {str(e)}"
    
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        import traceback
        result["error"] += f"\n{traceback.format_exc()}"
    
    return result

def remove_file_from_supabase(file_path: str) -> Dict[str, Any]:
    """Remove all chunks and file entry for a file from Supabase."""
    client = get_supabase_client(use_service_key=True)
    
    result = {
        "chunks_deleted": 0,
        "file_entry_deleted": 0,
        "error": None
    }
    
    try:
        # Delete all chunks
        chunks_response = client.table('code_chunks').delete().eq('file_path', file_path).execute()
        result["chunks_deleted"] = len(chunks_response.data) if chunks_response.data else 0
        
        # Delete file entry
        try:
            file_response = client.table('code_files').delete().eq('file_path', file_path).execute()
            result["file_entry_deleted"] = len(file_response.data) if file_response.data else 0
        except Exception as e:
            result["error"] = f"Error deleting file entry: {e}"
    
    except Exception as e:
        result["error"] = f"Error removing file: {e}"
    
    return result

def main():
    # Read large files list
    json_path = PROJECT_ROOT / "large_cs_files.json"
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        large_files = json.load(f)
    
    print("=" * 80)
    print("Check and Fix Large C# Files")
    print("=" * 80)
    print(f"\nTotal files to check: {len(large_files)}\n")
    
    removed_files = []
    fixed_files = []
    correct_files = []
    error_files = []
    
    for i, file_info in enumerate(large_files, 1):
        rel_path = file_info.get("path", "")
        full_path = file_info.get("full_path", "")
        lines = file_info.get("lines", 0)
        
        # Convert to Assets/... format if needed
        if not rel_path.startswith("Assets/"):
            rel_path = f"Assets/{rel_path}"
        
        print(f"\n[{i}/{len(large_files)}] {rel_path} ({lines} lines)")
        print("-" * 80)
        
        # Check chunking
        check_result = check_file_chunking(rel_path, full_path)
        
        if check_result["status"] == "file_not_found":
            print(f"  ❌ File not found: {full_path}")
            error_files.append({
                "path": rel_path,
                "full_path": full_path,
                "lines": lines,
                "reason": "file_not_found"
            })
            continue
        
        if check_result["status"] == "error_reading" or check_result["status"] == "error_querying":
            print(f"  ❌ Error: {check_result.get('error', 'Unknown error')}")
            error_files.append({
                "path": rel_path,
                "full_path": full_path,
                "lines": lines,
                "reason": check_result["status"],
                "error": check_result.get("error")
            })
            continue
        
        if check_result["is_correct"]:
            print(f"  ✅ Correct: {len(check_result['classes_in_file'])} class(es) correctly chunked")
            correct_files.append({
                "path": rel_path,
                "full_path": full_path,
                "lines": lines,
                "class_count": len(check_result['classes_in_file'])
            })
            continue
        
        # Incorrect - show details
        print(f"  ⚠️  Incorrect chunking:")
        print(f"     Classes in file: {len(check_result['classes_in_file'])}")
        print(f"     Classes in Supabase: {len(check_result['classes_in_supabase'])}")
        if check_result["missing"]:
            print(f"     Missing: {check_result['missing']}")
        if check_result["extra"]:
            print(f"     Extra: {check_result['extra']}")
        
        # Attempt to fix
        print(f"  🔧 Attempting to fix...")
        fix_result = attempt_fix(rel_path, full_path)
        
        if fix_result["success"]:
            print(f"  ✅ Fixed: Indexed {fix_result['chunks_indexed']} class chunk(s)")
            fixed_files.append({
                "path": rel_path,
                "full_path": full_path,
                "lines": lines,
                "chunks_indexed": fix_result["chunks_indexed"]
            })
            
            # Verify fix
            verify_result = check_file_chunking(rel_path, full_path)
            if verify_result["is_correct"]:
                print(f"  ✅ Verification: Chunking is now correct")
            else:
                print(f"  ⚠️  Verification: Still has issues (may be embedding failure)")
        else:
            error_msg = fix_result.get("error", "Unknown error")
            print(f"  ❌ Fix failed: {error_msg}")
            
            # Check if it's an embedding error (including connection errors for large files)
            is_embedding_error = (
                "embedding" in error_msg.lower() or 
                "api" in error_msg.lower() or
                "connection" in error_msg.lower() or
                "too large" in error_msg.lower() or
                "ConnectionResetError" in error_msg or
                "10054" in error_msg
            )
            
            if is_embedding_error:
                print(f"  🗑️  Removing file from Supabase (file too large for embedding)...")
                remove_result = remove_file_from_supabase(rel_path)
                print(f"     Deleted {remove_result['chunks_deleted']} chunk(s), {remove_result['file_entry_deleted']} file entry/entries")
                
                removed_files.append({
                    "path": rel_path,
                    "full_path": full_path,
                    "lines": lines,
                    "reason": "file_too_large_for_embedding",
                    "error": error_msg,
                    "chunks_deleted": remove_result["chunks_deleted"],
                    "file_entry_deleted": remove_result["file_entry_deleted"]
                })
            else:
                error_files.append({
                    "path": rel_path,
                    "full_path": full_path,
                    "lines": lines,
                    "reason": "fix_failed",
                    "error": error_msg
                })
    
    # Summary
    print(f"\n{'=' * 80}")
    print("Summary")
    print(f"{'=' * 80}\n")
    
    print(f"✅ Correct: {len(correct_files)} file(s)")
    print(f"🔧 Fixed: {len(fixed_files)} file(s)")
    print(f"❌ Errors: {len(error_files)} file(s)")
    print(f"🗑️  Removed: {len(removed_files)} file(s)")
    
    # Write removed files to JSON
    if removed_files:
        removed_json_path = PROJECT_ROOT / "removed_large_files.json"
        with open(removed_json_path, 'w', encoding='utf-8') as f:
            json.dump(removed_files, f, indent=2, ensure_ascii=False)
        print(f"\n📝 Removed files written to: {removed_json_path}")
    
    print(f"\n{'=' * 80}")

if __name__ == "__main__":
    main()


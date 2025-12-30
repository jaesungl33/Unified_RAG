"""
Continue reindexing - process files that haven't been indexed yet.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Set

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

# Import functions from reindex script
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))
from reindex_complete_codebase import (
    convert_to_relative_path,
    find_type_declarations,
    extract_method_code,
    build_method_chunks,
    build_class_like_chunks,
    walk_cs_files,
    TYPE_DECL_PATTERN
)

def get_indexed_files(client) -> Set[str]:
    """Get set of file paths that are already indexed."""
    try:
        result = client.table('code_files').select('file_path').execute()
        if result.data:
            return set(row['file_path'] for row in result.data)
        return set()
    except Exception as e:
        print(f"   [!] Error getting indexed files: {e}")
        return set()

def main():
    print("=" * 80)
    print("Continue Reindexing - Process Missing Files")
    print("=" * 80)
    
    try:
        client = get_supabase_client(use_service_key=True)
        provider = QwenProvider()
        
        # Get already indexed files
        print("\n[1/3] Checking already indexed files...")
        indexed_files = get_indexed_files(client)
        print(f"   Found {len(indexed_files)} already indexed files")
        
        # Find all .cs files
        print("\n[2/3] Scanning Assets folder...")
        all_cs_files = walk_cs_files(PROJECT_ROOT)
        print(f"   Found {len(all_cs_files)} total .cs files")
        
        # Find missing files
        missing_files = []
        for cs_file in all_cs_files:
            relative_path = convert_to_relative_path(cs_file, PROJECT_ROOT)
            if relative_path not in indexed_files:
                missing_files.append(cs_file)
        
        print(f"\n   Missing files: {len(missing_files)}")
        
        if not missing_files:
            print("\n[OK] All files are already indexed!")
            return
        
        # Process missing files
        print(f"\n[3/3] Processing {len(missing_files)} missing files...")
        total_method_chunks = 0
        total_class_chunks = 0
        processed = 0
        failed = 0
        
        for i, cs_file in enumerate(missing_files, 1):
            try:
                relative_path = convert_to_relative_path(cs_file, PROJECT_ROOT)
                
                print(f"\n[{i}/{len(missing_files)}] Processing: {cs_file.name}")
                print(f"   Path: {relative_path}")
                
                # Read file
                code_text = cs_file.read_text(encoding='utf-8', errors='ignore')
                
                # Extract methods
                method_chunks = build_method_chunks(code_text, relative_path, cs_file.name)
                print(f"   Found {len(method_chunks)} method(s)")
                
                # Extract classes
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
                
                if i % 20 == 0:
                    print(f"\n   Progress: {i}/{len(missing_files)} files processed")
                
            except Exception as e:
                print(f"   [!] Error processing {cs_file.name}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("[OK] Processing Complete!")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"   Files processed: {processed}")
        print(f"   Files failed: {failed}")
        print(f"   Method chunks indexed: {total_method_chunks}")
        print(f"   Class-like chunks indexed: {total_class_chunks}")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


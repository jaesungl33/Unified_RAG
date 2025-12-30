"""
Delete incorrect class chunks for a specific file and reindex it.
Used to test the fixed chunking logic before reindexing everything.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client
from backend.storage.code_supabase_storage import index_code_chunks_to_supabase, normalize_path_consistent
from backend.code_service import _analyze_csharp_file_symbols
from gdd_rag_backbone.llm_providers import QwenProvider

# Import the fixed chunking functions
from scripts.reindex_complete_codebase import find_type_declarations, build_class_like_chunks

def delete_class_chunks_for_file(file_path: str) -> int:
    """
    Delete all class chunks for a specific file from Supabase.
    Returns number of chunks deleted.
    """
    client = get_supabase_client(use_service_key=True)
    
    # Try different path formats
    path_variants = [
        file_path,
        file_path.replace('\\', '/'),
        file_path.replace('/', '\\'),
    ]
    
    deleted_count = 0
    
    for path_variant in path_variants:
        try:
            # Delete all class chunks for this file
            response = client.table('code_chunks').delete().eq('file_path', path_variant).eq('chunk_type', 'class').execute()
            
            if response.data:
                deleted_count = len(response.data)
                print(f"✓ Deleted {deleted_count} class chunk(s) with path: {path_variant}")
                break
        except Exception as e:
            print(f"✗ Error deleting with path {path_variant}: {e}")
    
    return deleted_count

def reindex_single_file(file_path: str, supabase_path: str = None) -> bool:
    """
    Reindex class chunks for a single file using the fixed chunking logic.
    """
    print(f"\n{'=' * 80}")
    print(f"Reindexing: {file_path}")
    print(f"{'=' * 80}\n")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code_text = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    file_name = Path(file_path).name
    
    # Determine Supabase path if not provided
    if supabase_path is None:
        path_str = file_path.replace('\\', '/')
        if 'Assets/' in path_str or 'assets/' in path_str:
            idx = path_str.lower().find('assets/')
            supabase_path = path_str[idx:]
        else:
            supabase_path = file_path
    
    # Find all type declarations using fixed logic
    print("🔍 Finding type declarations...")
    types = find_type_declarations(code_text)
    print(f"   Found {len(types)} type declaration(s):")
    for type_info in types:
        print(f"   - {type_info['kind']} {type_info['name']}")
    
    if not types:
        print("⚠️  No types found in file!")
        return False
    
    # Build class chunks (use Supabase path format for storage)
    print("\n📦 Building class chunks...")
    chunks = build_class_like_chunks(code_text, supabase_path, file_name)
    print(f"   Built {len(chunks)} chunk(s)")
    
    # Show what will be indexed
    print("\n📋 Chunks to index:")
    for i, chunk in enumerate(chunks, 1):
        class_name = chunk.get('class_name', 'N/A')
        chunk_type = chunk.get('chunk_type', 'N/A')
        source_len = len(chunk.get('source_code', ''))
        print(f"   {i}. {chunk_type} '{class_name}' ({source_len} chars)")
    
    # Initialize provider
    try:
        provider = QwenProvider()
    except Exception as e:
        print(f"❌ Error initializing QwenProvider: {e}")
        return False
    
    # Index to Supabase (use Supabase path format)
    print(f"\n💾 Indexing to Supabase...")
    try:
        success = index_code_chunks_to_supabase(
            file_path=supabase_path,
            file_name=file_name,
            chunks=chunks,
            provider=provider
        )
        
        if success:
            print(f"✅ Successfully indexed {len(chunks)} class chunk(s)")
            return True
        else:
            print(f"❌ Failed to index chunks")
            return False
    except Exception as e:
        print(f"❌ Error indexing: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_chunks(file_path: str):
    """
    Verify the chunks in Supabase after reindexing.
    """
    client = get_supabase_client(use_service_key=True)
    
    print(f"\n{'=' * 80}")
    print("Verification: Checking chunks in Supabase")
    print(f"{'=' * 80}\n")
    
    # Try different path formats
    path_variants = [
        file_path,
        file_path.replace('\\', '/'),
        file_path.replace('/', '\\'),
    ]
    
    all_chunks = []
    
    for path_variant in path_variants:
        try:
            # Get all chunk types (class, struct, interface, enum)
            response = client.table('code_chunks').select(
                'id, file_path, chunk_type, class_name, source_code'
            ).eq('file_path', path_variant).in_('chunk_type', ['class', 'struct', 'interface', 'enum']).execute()
            
            if response.data:
                all_chunks = response.data
                print(f"✓ Found {len(all_chunks)} class chunk(s) in Supabase\n")
                break
        except Exception as e:
            print(f"✗ Error querying: {e}")
    
    if not all_chunks:
        print("❌ No chunks found in Supabase!")
        return
    
    print("Chunks in Supabase:")
    for i, chunk in enumerate(all_chunks, 1):
        class_name = chunk.get('class_name', 'N/A')
        source_code = chunk.get('source_code', '')
        source_len = len(source_code)
        
        print(f"\n  {i}. Class Name: {class_name}")
        print(f"     Source Code Length: {source_len} chars")
        
        # Show first 200 chars
        if source_code:
            preview = source_code[:200].replace('\n', ' ')
            print(f"     Preview: {preview}...")

def main():
    # File to fix - use full path from user's request
    file_path = r"c:\Users\CPU12391\Desktop\GDD_RAG_Gradio\codebase_RAG\tank_online_1-dev\Assets\_GameModules\Editor\NamingConventionScanner.cs"
    
    # Also accept command line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    # Convert to normalized path for Supabase (Assets/... format)
    # Extract Assets/... portion from full path
    path_str = file_path.replace('\\', '/')
    if 'Assets/' in path_str or 'assets/' in path_str:
        idx = path_str.lower().find('assets/')
        supabase_path = path_str[idx:]
    else:
        supabase_path = file_path
    
    print("=" * 80)
    print("Fix and Reindex Single File")
    print("=" * 80)
    print(f"\nFile: {file_path}")
    print(f"Supabase Path: {supabase_path}\n")
    
    # Step 1: Delete existing class chunks (use Supabase path format)
    print("Step 1: Deleting existing class chunks...")
    deleted = delete_class_chunks_for_file(supabase_path)
    print(f"   Deleted {deleted} chunk(s)\n")
    
    # Step 2: Reindex the file (use full path for reading, supabase_path for indexing)
    print("Step 2: Reindexing file with fixed chunking logic...")
    success = reindex_single_file(file_path, supabase_path)
    
    if not success:
        print("\n❌ Reindexing failed!")
        return
    
    # Step 3: Verify (use Supabase path format)
    verify_chunks(supabase_path)
    
    print(f"\n{'=' * 80}")
    print("✅ Done! Check the results above.")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()


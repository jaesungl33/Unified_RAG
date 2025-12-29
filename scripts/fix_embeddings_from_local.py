"""
Fix Supabase embeddings by reading correct embeddings from local storage
and updating Supabase with proper vector format.

This is faster than re-migrating because embeddings are already computed.
"""

import os
import sys
import json
from pathlib import Path

# Add project directories to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PARENT_ROOT) not in sys.path:
    sys.path.insert(0, str(PARENT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client

print("=" * 60)
print("Fixing Supabase Embeddings from Local Storage")
print("=" * 60)

# Local storage paths
MARKDOWN_WORKING_DIR = PARENT_ROOT / "rag_storage_md_indexed"
VDB_CHUNKS_PATH = MARKDOWN_WORKING_DIR / "vdb_chunks.json"

# Check if Supabase is configured
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
    print("\n✗ Error: Supabase not configured")
    sys.exit(1)

# Check if local storage exists
if not VDB_CHUNKS_PATH.exists():
    print(f"\n✗ Error: Local storage not found at {VDB_CHUNKS_PATH}")
    print("   Cannot fix embeddings without local storage data")
    sys.exit(1)

try:
    # Load correct embeddings from local storage
    print("\n1. Loading embeddings from local storage...")
    with open(VDB_CHUNKS_PATH, 'r', encoding='utf-8') as f:
        vectors_data = json.load(f)
    
    # Create vector lookup - embeddings are already arrays here
    vector_lookup = {}
    for entry in vectors_data.get("data", []):
        chunk_id = entry.get("__id__") or entry.get("id")
        vector = entry.get("vector") or entry.get("embedding")
        if chunk_id and vector:
            # Ensure it's a list of floats
            if isinstance(vector, list):
                try:
                    vector_lookup[chunk_id] = [float(x) for x in vector]
                except (ValueError, TypeError):
                    print(f"   ⚠ Skipping chunk {chunk_id}: Invalid embedding format")
                    continue
            else:
                print(f"   ⚠ Skipping chunk {chunk_id}: Embedding is not a list")
                continue
    
    print(f"   ✓ Loaded {len(vector_lookup)} embeddings from local storage")
    
    if not vector_lookup:
        print("   ✗ No valid embeddings found in local storage")
        sys.exit(1)
    
    # Connect to Supabase
    print("\n2. Connecting to Supabase...")
    client = get_supabase_client(use_service_key=True)
    print("   ✓ Connected")
    
    # Get all chunks from Supabase
    print("\n3. Fetching chunks from Supabase...")
    all_chunks = []
    batch_size = 1000
    offset = 0
    
    while True:
        result = client.table('gdd_chunks').select('id, chunk_id, embedding').range(offset, offset + batch_size - 1).execute()
        
        if not result.data:
            break
        
        all_chunks.extend(result.data)
        offset += batch_size
        
        if len(result.data) < batch_size:
            break
    
    print(f"   ✓ Found {len(all_chunks)} chunks in Supabase")
    
    # Update chunks with correct embeddings
    print("\n4. Updating embeddings...")
    updated_count = 0
    not_found_count = 0
    already_correct_count = 0
    error_count = 0
    
    batch_updates = []
    
    for chunk in all_chunks:
        chunk_id = chunk.get('chunk_id')
        record_id = chunk.get('id')
        current_embedding = chunk.get('embedding')
        
        # Check if embedding is already correct (list type)
        if isinstance(current_embedding, list):
            already_correct_count += 1
            continue
        
        # Get correct embedding from local storage
        if chunk_id not in vector_lookup:
            not_found_count += 1
            if not_found_count <= 5:  # Only print first few
                print(f"   ⚠ Chunk {chunk_id}: Not found in local storage")
            continue
        
        correct_embedding = vector_lookup[chunk_id]
        
        # Prepare update
        batch_updates.append({
            'id': record_id,
            'embedding': correct_embedding
        })
        
        # Update in batches
        if len(batch_updates) >= 100:
            try:
                # Update batch
                for update in batch_updates:
                    client.table('gdd_chunks').update({
                        'embedding': update['embedding']
                    }).eq('id', update['id']).execute()
                
                updated_count += len(batch_updates)
                print(f"   Updated {updated_count} chunks...")
                batch_updates = []
            except Exception as e:
                error_count += len(batch_updates)
                print(f"   ✗ Error updating batch: {e}")
                batch_updates = []
    
    # Update remaining batch
    if batch_updates:
        try:
            for update in batch_updates:
                client.table('gdd_chunks').update({
                    'embedding': update['embedding']
                }).eq('id', update['id']).execute()
            
            updated_count += len(batch_updates)
        except Exception as e:
            error_count += len(batch_updates)
            print(f"   ✗ Error updating final batch: {e}")
    
    print(f"\n✓ Update Summary:")
    print(f"   Updated: {updated_count} chunks")
    print(f"   Already correct: {already_correct_count} chunks")
    print(f"   Not found in local storage: {not_found_count} chunks")
    print(f"   Errors: {error_count} chunks")
    
    # Verify fix
    print("\n5. Verifying fix...")
    result = client.table('gdd_chunks').select('chunk_id, embedding').limit(5).execute()
    correct_count = 0
    for chunk in result.data:
        embedding = chunk.get('embedding')
        if isinstance(embedding, list):
            correct_count += 1
            print(f"   ✓ {chunk.get('chunk_id')}: Embedding is now a list (dim: {len(embedding)})")
        else:
            print(f"   ✗ {chunk.get('chunk_id')}: Still not a list (type: {type(embedding)})")
    
    if correct_count == len(result.data):
        print("\n✓ All sample chunks have correct embedding format!")
    else:
        print(f"\n⚠ {len(result.data) - correct_count} sample chunks still need fixing")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Fix completed!")
print("=" * 60)
print("\nNext step: Test vector search with:")
print("  python scripts/test_supabase_query.py")


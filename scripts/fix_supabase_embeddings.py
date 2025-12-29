"""
Fix embeddings in Supabase - convert string embeddings to arrays
"""

import os
import sys
import json
from pathlib import Path

# Add project directories to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client

print("=" * 60)
print("Fixing Supabase Embeddings")
print("=" * 60)

# Check if Supabase is configured
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
    print("\n✗ Error: Supabase not configured")
    sys.exit(1)

try:
    client = get_supabase_client(use_service_key=True)
    
    # Get all chunks - process in batches
    print("\n1. Finding chunks with string embeddings...")
    
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    batch_size = 100
    offset = 0
    
    while True:
        result = client.table('gdd_chunks').select('id, chunk_id, embedding').range(offset, offset + batch_size - 1).execute()
        
        if not result.data:
            break
        
        print(f"   Processing chunks {offset} to {offset + len(result.data) - 1}...")
        
        for chunk in result.data:
            chunk_id = chunk.get('chunk_id')
        embedding = chunk.get('embedding')
        record_id = chunk.get('id')
        
        if embedding is None:
            skipped_count += 1
            continue
        
        # Check if it's a string
        if isinstance(embedding, str):
            try:
                # Try to parse as JSON
                embedding_list = json.loads(embedding)
                
                # Ensure it's a list of numbers
                if isinstance(embedding_list, list):
                    embedding_list = [float(x) for x in embedding_list]
                    
                    # Update the record
                    client.table('gdd_chunks').update({
                        'embedding': embedding_list
                    }).eq('id', record_id).execute()
                    
                    fixed_count += 1
                    if fixed_count % 100 == 0:
                        print(f"   Fixed {fixed_count} chunks so far...")
                else:
                    error_count += 1
                    print(f"   ⚠ Chunk {chunk_id}: Embedding is not a list after parsing")
            except json.JSONDecodeError:
                error_count += 1
                print(f"   ✗ Chunk {chunk_id}: Could not parse embedding as JSON")
            except Exception as e:
                error_count += 1
                print(f"   ✗ Chunk {chunk_id}: Error - {e}")
        elif isinstance(embedding, list):
            # Already correct format
            skipped_count += 1
        else:
            error_count += 1
            print(f"   ⚠ Chunk {chunk_id}: Unknown embedding type: {type(embedding)}")
        
        offset += batch_size
        if len(result.data) < batch_size:
            break
    
    print(f"\n✓ Fixed {fixed_count} chunks")
    print(f"  Skipped {skipped_count} chunks (already correct or null)")
    print(f"  Errors: {error_count}")
    
    # Verify fix
    print("\n2. Verifying fix...")
    result = client.table('gdd_chunks').select('chunk_id, embedding').limit(5).execute()
    for chunk in result.data:
        embedding = chunk.get('embedding')
        if embedding:
            if isinstance(embedding, list):
                print(f"   ✓ {chunk.get('chunk_id')}: Embedding is now a list (dim: {len(embedding)})")
            else:
                print(f"   ✗ {chunk.get('chunk_id')}: Still not a list (type: {type(embedding)})")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Fix completed")
print("=" * 60)


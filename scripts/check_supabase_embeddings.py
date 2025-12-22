"""
Check if embeddings are stored correctly in Supabase
"""

import os
import sys
from pathlib import Path

# Add project directories to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client

print("=" * 60)
print("Checking Supabase Embeddings")
print("=" * 60)

# Check if Supabase is configured
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
    print("\n✗ Error: Supabase not configured")
    sys.exit(1)

try:
    client = get_supabase_client()
    
    # Check chunks table
    print("\n1. Checking gdd_chunks table...")
    result = client.table('gdd_chunks').select('chunk_id, doc_id, embedding').limit(5).execute()
    
    if result.data:
        print(f"   ✓ Found {len(result.data)} sample chunks")
        for i, chunk in enumerate(result.data[:3], 1):
            chunk_id = chunk.get('chunk_id', 'N/A')
            doc_id = chunk.get('doc_id', 'N/A')
            embedding = chunk.get('embedding')
            
            print(f"\n   Chunk {i}:")
            print(f"      ID: {chunk_id}")
            print(f"      Doc ID: {doc_id}")
            if embedding:
                if isinstance(embedding, list):
                    print(f"      Embedding: ✓ Present (dimension: {len(embedding)})")
                else:
                    print(f"      Embedding: ⚠ Present but not a list (type: {type(embedding)})")
            else:
                print(f"      Embedding: ✗ MISSING!")
    else:
        print("   ✗ No chunks found in table")
    
    # Count total chunks
    print("\n2. Counting total chunks...")
    count_result = client.table('gdd_chunks').select('chunk_id', count='exact').execute()
    print(f"   Total chunks: {count_result.count if hasattr(count_result, 'count') else 'N/A'}")
    
    # Count chunks with embeddings
    print("\n3. Checking chunks with embeddings...")
    # Query to count non-null embeddings
    result = client.table('gdd_chunks').select('chunk_id').not_.is_('embedding', 'null').limit(1).execute()
    print(f"   Chunks with embeddings: {len(result.data) if result.data else 0} (sample check)")
    
    # Test the RPC function directly
    print("\n4. Testing match_gdd_chunks RPC function...")
    # Create a dummy embedding (1024 dimensions)
    dummy_embedding = [0.0] * 1024
    try:
        rpc_result = client.rpc(
            'match_gdd_chunks',
            {
                'query_embedding': dummy_embedding,
                'match_threshold': 0.0,  # Very low threshold
                'match_count': 5,
                'doc_id_filter': None
            }
        ).execute()
        
        if rpc_result.data:
            print(f"   ✓ RPC function works - found {len(rpc_result.data)} results")
        else:
            print("   ⚠ RPC function works but returned 0 results")
            print("   This might mean embeddings are NULL or in wrong format")
    except Exception as e:
        print(f"   ✗ RPC function error: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Check completed")
print("=" * 60)


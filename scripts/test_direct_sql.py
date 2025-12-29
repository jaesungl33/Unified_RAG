"""
Test direct SQL query to check vector search
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
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func

print("=" * 60)
print("Testing Direct SQL Vector Search")
print("=" * 60)

try:
    client = get_supabase_client()
    
    # Test query
    provider = QwenProvider()
    embedding_func = make_embedding_func(provider)
    test_query = "joystick"
    query_embedding = embedding_func([test_query])[0]
    
    print(f"Query: '{test_query}'")
    print(f"Embedding dimension: {len(query_embedding)}")
    
    # Try direct SQL query
    print("\n1. Testing direct SQL query...")
    sql_query = """
    SELECT 
        chunk_id,
        doc_id,
        content,
        1 - (embedding <=> %s::vector) as similarity
    FROM gdd_chunks
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT 5
    """
    
    # Use RPC with lower threshold
    print("\n2. Testing RPC with threshold 0.0...")
    result = client.rpc(
        'match_gdd_chunks',
        {
            'query_embedding': query_embedding,
            'match_threshold': 0.0,  # Very low threshold
            'match_count': 10,
            'doc_id_filter': None
        }
    ).execute()
    
    print(f"   Results: {len(result.data) if result.data else 0}")
    if result.data:
        for i, r in enumerate(result.data[:3], 1):
            print(f"   {i}. Doc: {r.get('doc_id')}, Similarity: {r.get('similarity', 0):.3f}")
            print(f"      Content: {r.get('content', '')[:80]}...")
    else:
        print("   ⚠ No results - checking if embeddings exist...")
        
        # Check if any chunks have embeddings
        check_result = client.table('gdd_chunks').select('chunk_id, embedding').not_.is_('embedding', 'null').limit(1).execute()
        if check_result.data:
            print(f"   ✓ Found chunks with embeddings")
            # Check the type
            emb = check_result.data[0].get('embedding')
            print(f"   Embedding type: {type(emb)}")
            if isinstance(emb, str):
                print(f"   ⚠ Embedding is still a string! This is the problem.")
        else:
            print("   ✗ No chunks with embeddings found")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)


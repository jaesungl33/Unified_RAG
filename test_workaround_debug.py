"""
Debug script to test the workaround and see what's happening
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client, vector_search_gdd_chunks
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func

print("=" * 80)
print("Testing Workaround Debug")
print("=" * 80)

try:
    client = get_supabase_client()
    provider = QwenProvider()
    embedding_func = make_embedding_func(provider)
    
    # Test query
    test_query = "tank selection"
    query_embedding = embedding_func([test_query])[0]
    
    print(f"\n1. Testing table query directly...")
    print(f"   Query: '{test_query}'")
    print(f"   Embedding dimension: {len(query_embedding)}")
    
    # Try to query table directly
    result = client.table('gdd_chunks').select('chunk_id,doc_id,content,embedding,metadata').limit(5).execute()
    
    print(f"\n   Found {len(result.data) if result.data else 0} chunks")
    
    if result.data:
        sample = result.data[0]
        print(f"\n   Sample chunk keys: {list(sample.keys())}")
        print(f"   Has embedding: {'embedding' in sample}")
        if 'embedding' in sample:
            emb = sample['embedding']
            print(f"   Embedding type: {type(emb)}")
            if isinstance(emb, list):
                print(f"   Embedding length: {len(emb)}")
            else:
                print(f"   Embedding value: {str(emb)[:100]}...")
    
    # Test with a specific doc_id
    print(f"\n2. Testing with doc_id filter...")
    test_doc_id = "Asset_UI_Tank_War_Mode_Selection_Design"
    result2 = client.table('gdd_chunks').select('chunk_id,doc_id,content,embedding,metadata').eq('doc_id', test_doc_id).limit(5).execute()
    
    print(f"   Found {len(result2.data) if result2.data else 0} chunks for doc_id: {test_doc_id}")
    
    # Test vector search with workaround
    print(f"\n3. Testing vector_search_gdd_chunks with workaround...")
    search_results = vector_search_gdd_chunks(
        query_embedding=query_embedding,
        limit=10,
        threshold=0.1,  # Low threshold
        doc_id=test_doc_id
    )
    
    print(f"   Found {len(search_results)} results")
    if search_results:
        for i, r in enumerate(search_results[:3], 1):
            print(f"   {i}. Similarity: {r.get('similarity', 0):.3f}, Doc: {r.get('doc_id', 'unknown')}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()



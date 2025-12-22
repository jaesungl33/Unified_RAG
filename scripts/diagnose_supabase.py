"""
Diagnostic script to check Supabase vector search issues
"""

import os
import sys
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
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func

print("=" * 60)
print("Supabase Vector Search Diagnostics")
print("=" * 60)

try:
    client = get_supabase_client()
    
    # 1. Check if chunks have embeddings
    print("\n1. Checking chunks with embeddings...")
    result = client.table('gdd_chunks').select('chunk_id, embedding').not_.is_('embedding', 'null').limit(5).execute()
    
    if result.data:
        print(f"   ✓ Found {len(result.data)} chunks with embeddings")
        for chunk in result.data:
            emb = chunk.get('embedding')
            print(f"   - {chunk.get('chunk_id')}: Type={type(emb).__name__}")
            if isinstance(emb, list):
                print(f"     ✓ List format, dimension: {len(emb)}")
            elif isinstance(emb, str):
                print(f"     ✗ String format (needs fixing)")
            else:
                print(f"     ⚠ Unknown format: {type(emb)}")
    else:
        print("   ✗ No chunks with embeddings found!")
        sys.exit(1)
    
    # 2. Test RPC function directly with a dummy vector
    print("\n2. Testing RPC function with threshold 0.0...")
    dummy_vector = [0.1] * 1024  # Simple test vector
    
    try:
        rpc_result = client.rpc(
            'match_gdd_chunks',
            {
                'query_embedding': dummy_vector,
                'match_threshold': 0.0,  # Very low threshold
                'match_count': 10,
                'doc_id_filter': None
            }
        ).execute()
        
        print(f"   RPC call successful")
        print(f"   Results: {len(rpc_result.data) if rpc_result.data else 0}")
        
        if rpc_result.data:
            print("   ✓ RPC function is working!")
            for i, r in enumerate(rpc_result.data[:3], 1):
                print(f"   {i}. Doc: {r.get('doc_id')}, Similarity: {r.get('similarity', 0):.3f}")
        else:
            print("   ⚠ RPC returned 0 results even with threshold 0.0")
            print("   This suggests embeddings might not be in vector format")
            
    except Exception as e:
        print(f"   ✗ RPC error: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Test with actual query embedding
    print("\n3. Testing with actual query embedding...")
    try:
        provider = QwenProvider()
        embedding_func = make_embedding_func(provider)
        test_query = "joystick"
        query_embedding = embedding_func([test_query])[0]
        
        print(f"   Query: '{test_query}'")
        print(f"   Embedding dimension: {len(query_embedding)}")
        print(f"   Embedding sample (first 5): {query_embedding[:5]}")
        
        # Try with very low threshold
        result = client.rpc(
            'match_gdd_chunks',
            {
                'query_embedding': query_embedding,
                'match_threshold': 0.0,  # Accept any similarity
                'match_count': 10,
                'doc_id_filter': None
            }
        ).execute()
        
        print(f"   Results: {len(result.data) if result.data else 0}")
        
        if result.data:
            print("   ✓ Vector search is working!")
            for i, r in enumerate(result.data[:3], 1):
                print(f"   {i}. Doc: {r.get('doc_id')}")
                print(f"      Similarity: {r.get('similarity', 0):.4f}")
                print(f"      Content: {r.get('content', '')[:60]}...")
        else:
            print("   ✗ Still no results")
            print("\n   Possible issues:")
            print("   1. Embeddings are stored as strings, not vectors")
            print("   2. SQL fix script didn't run correctly")
            print("   3. RPC function has an issue")
            print("\n   Recommendation: Check Supabase SQL Editor and verify:")
            print("   SELECT pg_typeof(embedding) FROM gdd_chunks WHERE embedding IS NOT NULL LIMIT 1;")
            print("   Should return: 'vector'")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Check a specific document
    print("\n4. Checking specific document...")
    doc_result = client.table('gdd_documents').select('doc_id, chunks_count').limit(1).execute()
    if doc_result.data:
        doc_id = doc_result.data[0].get('doc_id')
        print(f"   Testing document: {doc_id}")
        
        # Get chunks for this document
        chunks_result = client.table('gdd_chunks').select('chunk_id, embedding').eq('doc_id', doc_id).limit(1).execute()
        if chunks_result.data:
            chunk = chunks_result.data[0]
            emb = chunk.get('embedding')
            print(f"   Chunk: {chunk.get('chunk_id')}")
            print(f"   Embedding type: {type(emb).__name__}")
            if isinstance(emb, list):
                print(f"   ✓ Embedding is a list (correct format)")
            else:
                print(f"   ✗ Embedding is {type(emb).__name__} (wrong format)")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)


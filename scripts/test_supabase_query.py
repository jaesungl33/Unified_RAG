"""
Test script to verify Supabase queries are working correctly
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

from backend.storage.supabase_client import get_gdd_documents, vector_search_gdd_chunks
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func

print("=" * 60)
print("Testing Supabase GDD Queries")
print("=" * 60)

# Check if Supabase is configured
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
    print("\n✗ Error: Supabase not configured")
    print("Please set SUPABASE_URL and SUPABASE_KEY in .env file")
    sys.exit(1)

# Test 1: List documents
print("\n1. Testing document listing...")
try:
    docs = get_gdd_documents()
    print(f"   ✓ Found {len(docs)} documents in Supabase")
    if docs:
        print(f"   Sample document: {docs[0].get('name', 'N/A')} (ID: {docs[0].get('doc_id', 'N/A')})")
        print(f"   Chunks count: {docs[0].get('chunks_count', 0)}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: Test vector search with a specific document
print("\n2. Testing vector search...")
try:
    provider = QwenProvider()
    embedding_func = make_embedding_func(provider)
    
    # Test query
    test_query = "what does move joystick do"
    print(f"   Query: '{test_query}'")
    
    # Get embedding
    query_embedding = embedding_func([test_query])[0]
    print(f"   ✓ Generated embedding (dimension: {len(query_embedding)})")
    
    # Search all documents
    print("\n   Searching all documents...")
    results = vector_search_gdd_chunks(
        query_embedding=query_embedding,
        limit=5,
        threshold=0.0,  # Very low threshold for testing
        doc_id=None  # Search all
    )
    print(f"   ✓ Found {len(results)} chunks")
    
    if results:
        print("\n   Top results:")
        for i, result in enumerate(results[:3], 1):
            print(f"   {i}. Doc: {result.get('doc_id', 'N/A')}")
            print(f"      Similarity: {result.get('similarity', 0):.3f}")
            print(f"      Content preview: {result.get('content', '')[:100]}...")
    else:
        print("   ⚠ No results found. This might indicate:")
        print("      - Embeddings are not in Supabase")
        print("      - Threshold is too high")
        print("      - Query doesn't match any content")
    
    # Test with specific document
    if docs:
        test_doc_id = docs[0].get('doc_id')
        print(f"\n   Searching document: {test_doc_id}...")
        results = vector_search_gdd_chunks(
            query_embedding=query_embedding,
            limit=5,
            threshold=0.0,  # Very low threshold for testing
            doc_id=test_doc_id
        )
        print(f"   ✓ Found {len(results)} chunks in this document")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ Tests completed")
print("=" * 60)


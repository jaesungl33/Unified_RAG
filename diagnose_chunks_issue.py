"""
Diagnostic script to understand why chunks aren't being found
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client

print("=" * 80)
print("DIAGNOSING CHUNKS ISSUE")
print("=" * 80)

client = get_supabase_client()

# Test 1: Check if table exists and has any chunks
print("\n1. Checking if gdd_chunks table has any data...")
try:
    result = client.table('gdd_chunks').select('chunk_id', count='exact').limit(1).execute()
    total = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
    print(f"   Total chunks in database: {total}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Check specific doc_id
print("\n2. Checking chunks for a specific doc_id...")
test_doc_id = "Asset_UI_Tank_War_Mode_Selection_Design"
try:
    result = client.table('gdd_chunks').select('chunk_id,doc_id', count='exact').eq('doc_id', test_doc_id).limit(5).execute()
    count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
    print(f"   Chunks for '{test_doc_id}': {count}")
    if result.data:
        print(f"   Sample chunk_ids:")
        for chunk in result.data[:3]:
            print(f"     - {chunk.get('chunk_id', 'unknown')}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Check if embeddings are returned
print("\n3. Checking if embeddings are returned by PostgREST...")
try:
    result = client.table('gdd_chunks').select('chunk_id,embedding').limit(1).execute()
    if result.data:
        sample = result.data[0]
        print(f"   Sample chunk keys: {list(sample.keys())}")
        print(f"   Has 'embedding' key: {'embedding' in sample}")
        if 'embedding' in sample:
            emb = sample['embedding']
            print(f"   Embedding type: {type(emb)}")
            if emb:
                print(f"   Embedding value: {str(emb)[:100]}...")
            else:
                print(f"   Embedding value: None")
        else:
            print(f"   WARNING: 'embedding' key not in response!")
            print(f"   This means PostgREST is filtering out vector columns.")
    else:
        print(f"   No chunks found to test")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: List all unique doc_ids
print("\n4. Listing all unique doc_ids in database...")
try:
    # Get distinct doc_ids
    result = client.table('gdd_chunks').select('doc_id').limit(100).execute()
    if result.data:
        doc_ids = list(set(chunk.get('doc_id') for chunk in result.data if chunk.get('doc_id')))
        print(f"   Found {len(doc_ids)} unique doc_ids:")
        for doc_id in sorted(doc_ids)[:10]:
            count_result = client.table('gdd_chunks').select('chunk_id', count='exact').eq('doc_id', doc_id).limit(1).execute()
            count = count_result.count if hasattr(count_result, 'count') else 0
            print(f"     - {doc_id}: {count} chunks")
    else:
        print(f"   No chunks found in database")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 80)
print("Diagnosis Complete!")
print("=" * 80)


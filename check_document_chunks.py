"""
Check which documents have chunks indexed in Supabase.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.gdd_service import list_documents
from backend.storage.supabase_client import get_supabase_client

def check_chunks_for_documents():
    """Check which documents have chunks in Supabase"""
    print("=" * 80)
    print("Checking Document Chunks in Supabase")
    print("=" * 80)
    
    # Get all documents
    documents = list_documents()
    print(f"\nFound {len(documents)} documents\n")
    
    client = get_supabase_client()
    
    results = []
    for doc in documents:
        doc_id = doc.get('doc_id') or doc.get('id') or doc.get('name', 'unknown')
        name = doc.get('name', 'Unknown')
        
        # Check if chunks exist for this doc_id
        try:
            chunk_count = client.table('gdd_chunks').select('id', count='exact').eq('doc_id', doc_id).execute()
            count = chunk_count.count if hasattr(chunk_count, 'count') else len(chunk_count.data) if chunk_count.data else 0
            
            status = "HAS CHUNKS" if count > 0 else "NO CHUNKS"
            results.append({
                'doc_id': doc_id,
                'name': name,
                'chunk_count': count,
                'status': status
            })
            
            print(f"{status:15} | {count:4} chunks | {name}")
        except Exception as e:
            print(f"ERROR       | {name}: {e}")
            results.append({
                'doc_id': doc_id,
                'name': name,
                'chunk_count': 0,
                'status': 'ERROR',
                'error': str(e)
            })
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    has_chunks = [r for r in results if r['chunk_count'] > 0]
    no_chunks = [r for r in results if r['chunk_count'] == 0]
    
    print(f"\nDocuments with chunks: {len(has_chunks)}")
    print(f"Documents without chunks: {len(no_chunks)}")
    
    if no_chunks:
        print("\nDocuments that need indexing:")
        for doc in no_chunks:
            print(f"  - {doc['name']} (doc_id: {doc['doc_id']})")
    
    return results

if __name__ == '__main__':
    check_chunks_for_documents()



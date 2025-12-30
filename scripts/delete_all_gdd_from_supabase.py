"""
Script to delete all GDD data from Supabase.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client, get_gdd_documents

def delete_all_gdd_data():
    """Delete all GDD documents and chunks from Supabase."""
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Get all documents
        docs = get_gdd_documents()
        print(f"Found {len(docs)} GDD documents in Supabase")
        
        if not docs:
            print("No GDD documents to delete.")
            return
        
        # Delete all chunks first (cascade should handle this, but let's be explicit)
        print("Deleting all GDD chunks...")
        result = client.table('gdd_chunks').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"Deleted chunks (result: {len(result.data) if result.data else 0} rows)")
        
        # Delete all documents
        print("Deleting all GDD documents...")
        for doc in docs:
            doc_id = doc.get('doc_id', '')
            if doc_id:
                result = client.table('gdd_documents').delete().eq('doc_id', doc_id).execute()
                print(f"  Deleted document: {doc_id}")
        
        print(f"\n[SUCCESS] Deleted all {len(docs)} GDD documents and their chunks from Supabase")
        
    except Exception as e:
        print(f"[ERROR] Failed to delete GDD data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("DELETE ALL GDD DATA FROM SUPABASE")
    print("=" * 70)
    print()
    
    confirm = input("Are you sure you want to delete ALL GDD data from Supabase? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
    success = delete_all_gdd_data()
    sys.exit(0 if success else 1)

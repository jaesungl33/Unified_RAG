"""
Cleanup GDD Data from Supabase Before V2 Testing
================================================
Removes existing GDD documents and chunks from Supabase to prepare for v2 indexing.

Use this before testing the new v2 pipeline to avoid conflicts.
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

try:
    from backend.storage.supabase_client import (
        get_supabase_client,
        get_gdd_documents,
        delete_gdd_document
    )
except ImportError as e:
    print(f"ERROR: Failed to import supabase_client: {e}")
    sys.exit(1)

def cleanup_all_gdd_data():
    """Delete all GDD documents and chunks from Supabase."""
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Get all documents
        print("Fetching GDD documents from Supabase...")
        docs = get_gdd_documents()
        print(f"Found {len(docs)} GDD documents in Supabase")
        
        if not docs:
            print("No GDD documents to delete.")
            return True
        
        # Show what will be deleted
        print("\nDocuments to be deleted:")
        for doc in docs:
            doc_id = doc.get('doc_id', 'N/A')
            name = doc.get('name', 'N/A')
            chunks_count = doc.get('chunks_count', 0)
            # Safe encoding for Windows console
            try:
                safe_doc_id = doc_id.encode('ascii', 'ignore').decode('ascii') if doc_id else 'N/A'
                safe_name = name.encode('ascii', 'ignore').decode('ascii') if name else 'N/A'
                print(f"  - {safe_doc_id}: {safe_name} ({chunks_count} chunks)")
            except Exception:
                print(f"  - Document {chunks_count} chunks")
        
        # Delete all chunks first (cascade should handle this, but let's be explicit)
        print("\nDeleting all GDD chunks...")
        result = client.table('gdd_chunks').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        deleted_chunks = len(result.data) if result.data else 0
        print(f"  [OK] Deleted {deleted_chunks} chunks")
        
        # Delete all documents
        print("\nDeleting all GDD documents...")
        deleted_count = 0
        for doc in docs:
            doc_id = doc.get('doc_id', '')
            if doc_id:
                try:
                    result = client.table('gdd_documents').delete().eq('doc_id', doc_id).execute()
                    deleted_count += 1
                    try:
                        safe_doc_id = doc_id.encode('ascii', 'ignore').decode('ascii')
                        print(f"  [OK] Deleted document: {safe_doc_id}")
                    except:
                        print(f"  [OK] Deleted document (ID contains non-ASCII)")
                except Exception as e:
                    try:
                        safe_doc_id = doc_id.encode('ascii', 'ignore').decode('ascii')
                        print(f"  [ERROR] Failed to delete {safe_doc_id}: {e}")
                    except:
                        print(f"  [ERROR] Failed to delete document: {e}")
        
        print(f"\n[SUCCESS] Deleted {deleted_count} documents and {deleted_chunks} chunks from Supabase")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to cleanup GDD data: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_specific_doc_ids(doc_ids: list):
    """Delete specific documents by doc_id."""
    try:
        client = get_supabase_client(use_service_key=True)
        
        print(f"Deleting {len(doc_ids)} specific documents...")
        
        deleted_count = 0
        for doc_id in doc_ids:
            try:
                # Delete chunks first (cascade should handle this)
                chunks_result = client.table('gdd_chunks').delete().eq('doc_id', doc_id).execute()
                chunks_deleted = len(chunks_result.data) if chunks_result.data else 0
                
                # Delete document
                result = client.table('gdd_documents').delete().eq('doc_id', doc_id).execute()
                deleted_count += 1
                try:
                    safe_doc_id = doc_id.encode('ascii', 'ignore').decode('ascii')
                    print(f"  [OK] Deleted {safe_doc_id} ({chunks_deleted} chunks)")
                except:
                    print(f"  [OK] Deleted document ({chunks_deleted} chunks)")
            except Exception as e:
                try:
                    safe_doc_id = doc_id.encode('ascii', 'ignore').decode('ascii')
                    print(f"  [ERROR] Failed to delete {safe_doc_id}: {e}")
                except:
                    print(f"  [ERROR] Failed to delete document: {e}")
        
        print(f"\n[SUCCESS] Deleted {deleted_count} documents")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cleanup GDD data from Supabase before v2 testing"
    )
    parser.add_argument(
        "--doc-ids",
        nargs="+",
        help="Specific document IDs to delete (if not provided, deletes all)"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("CLEANUP GDD DATA FROM SUPABASE")
    print("=" * 70)
    print()
    
    if args.doc_ids:
        print(f"Will delete {len(args.doc_ids)} specific documents:")
        for doc_id in args.doc_ids:
            print(f"  - {doc_id}")
    else:
        print("Will delete ALL GDD documents and chunks from Supabase")
    
    print()
    
    if not args.yes:
        confirm = input("Are you sure? This cannot be undone! (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    if args.doc_ids:
        success = cleanup_specific_doc_ids(args.doc_ids)
    else:
        success = cleanup_all_gdd_data()
    
    sys.exit(0 if success else 1)

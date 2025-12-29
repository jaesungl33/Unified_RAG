"""
Script to migrate 10 documents from local storage to Supabase.
Stores data exactly as it's stored locally.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client, insert_gdd_document, insert_gdd_chunks

# Local storage paths (from GDD_RAG_Gradio)
LOCAL_STORAGE_ROOT = Path(r"C:\Users\CPU12391\Desktop\GDD_RAG_Gradio\rag_storage_md_indexed")
LOCAL_CHUNKS_PATH = LOCAL_STORAGE_ROOT / "kv_store_text_chunks.json"
LOCAL_VDB_PATH = LOCAL_STORAGE_ROOT / "vdb_chunks.json"
LOCAL_STATUS_PATH = LOCAL_STORAGE_ROOT / "kv_store_doc_status.json"

def load_local_data():
    """Load all data from local storage files."""
    chunks_data = {}
    vectors_data = {"data": []}
    status_data = {}
    
    if LOCAL_CHUNKS_PATH.exists():
        with open(LOCAL_CHUNKS_PATH, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        print(f"Loaded {len(chunks_data)} chunks from local storage")
    
    if LOCAL_VDB_PATH.exists():
        with open(LOCAL_VDB_PATH, 'r', encoding='utf-8') as f:
            vectors_data = json.load(f)
        print(f"Loaded {len(vectors_data.get('data', []))} vectors from local storage")
    
    if LOCAL_STATUS_PATH.exists():
        with open(LOCAL_STATUS_PATH, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        print(f"Loaded {len(status_data)} documents from local storage")
    
    return chunks_data, vectors_data, status_data

def migrate_documents_to_supabase(doc_ids: List[str], limit: int = 10):
    """
    Migrate documents from local storage to Supabase.
    Stores data exactly as it's stored locally.
    
    Args:
        doc_ids: List of document IDs to migrate (if empty, migrates first N)
        limit: Maximum number of documents to migrate
    """
    print("=" * 70)
    print("MIGRATE LOCAL STORAGE TO SUPABASE")
    print("=" * 70)
    print()
    
    # Load local data
    print("Loading local storage data...")
    chunks_data, vectors_data, status_data = load_local_data()
    
    # Determine which documents to migrate
    if not doc_ids:
        # Get first N documents from status
        all_doc_ids = list(status_data.keys())[:limit]
    else:
        all_doc_ids = doc_ids[:limit]
    
    print(f"\nMigrating {len(all_doc_ids)} documents:")
    for doc_id in all_doc_ids:
        print(f"  - {doc_id}")
    print()
    
    # Create vectors lookup by chunk_id
    vectors_by_chunk_id = {}
    for entry in vectors_data.get("data", []):
        chunk_id = entry.get("__id__") or entry.get("id")
        if chunk_id:
            vectors_by_chunk_id[chunk_id] = entry.get("vector") or entry.get("embedding")
    
    print(f"Created vector lookup with {len(vectors_by_chunk_id)} vectors")
    print()
    
    # Migrate each document
    client = get_supabase_client(use_service_key=True)
    total_chunks_migrated = 0
    
    for i, doc_id in enumerate(all_doc_ids, 1):
        print(f"[{i}/{len(all_doc_ids)}] Migrating: {doc_id}")
        
        # Get document status
        doc_status = status_data.get(doc_id, {})
        if not doc_status:
            print(f"  [SKIP] Document {doc_id} not found in status")
            continue
        
        # Get all chunks for this document
        doc_chunks = []
        for chunk_key, chunk_data in chunks_data.items():
            if isinstance(chunk_data, dict) and chunk_data.get("full_doc_id") == doc_id:
                # Extract chunk_id from key (format: {doc_id}_{chunk_id})
                chunk_id = chunk_key.replace(f"{doc_id}_", "")
                
                # Get vector for this chunk
                vector = vectors_by_chunk_id.get(chunk_key)
                
                if vector:
                    doc_chunks.append({
                        "chunk_id": chunk_id,  # Store as chunk_001, not full_chunk_id
                        "full_chunk_id": chunk_key,  # Keep full ID for reference
                        "content": chunk_data.get("content", ""),
                        "metadata": chunk_data.get("metadata", {}),
                        "vector": vector
                    })
        
        if not doc_chunks:
            print(f"  [SKIP] No chunks found for {doc_id}")
            continue
        
        print(f"  Found {len(doc_chunks)} chunks")
        
        # Insert document metadata
        file_path = doc_status.get("file_path", "")
        file_name = Path(file_path).name if file_path else f"{doc_id}.md"
        
        try:
            insert_gdd_document(
                doc_id=doc_id,
                name=file_name,
                file_path=file_path,
                file_size=None
            )
            print(f"  [OK] Inserted document metadata")
        except Exception as e:
            print(f"  [ERROR] Failed to insert document: {e}")
            continue
        
        # Prepare chunks for Supabase
        # IMPORTANT: Use full_chunk_id format ({doc_id}_{chunk_id}) to match local storage
        supabase_chunks = []
        for chunk in doc_chunks:
            full_chunk_id = chunk["full_chunk_id"]  # e.g., "Asset_UI_Tank_War_Garage_Design_UI_UX_chunk_001"
            chunk_id = chunk["chunk_id"]  # e.g., "chunk_001"
            content = chunk["content"]
            vector = chunk["vector"]
            metadata = chunk.get("metadata", {})
            
            # Store chunk_id as full_chunk_id to match local storage format
            supabase_chunks.append({
                "chunk_id": full_chunk_id,  # Use full format to match local
                "doc_id": doc_id,
                "content": content,
                "embedding": vector,
                "metadata": {
                    **metadata,
                    "original_chunk_id": chunk_id,  # Store original chunk_id in metadata
                    "full_chunk_id": full_chunk_id
                }
            })
        
        # Insert chunks
        try:
            inserted_count = insert_gdd_chunks(supabase_chunks)
            print(f"  [OK] Inserted {inserted_count} chunks")
            total_chunks_migrated += inserted_count
        except Exception as e:
            print(f"  [ERROR] Failed to insert chunks: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        print()
    
    print("=" * 70)
    print(f"COMPLETE: Migrated {len(all_doc_ids)} documents, {total_chunks_migrated} total chunks")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate documents from local storage to Supabase")
    parser.add_argument(
        "--doc-ids",
        nargs="+",
        help="Specific document IDs to migrate (if not provided, migrates first 10)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of documents to migrate (default: 10)"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    if not args.yes:
        confirm = input(f"Migrate {args.limit} documents from local storage to Supabase? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    success = migrate_documents_to_supabase(args.doc_ids or [], limit=args.limit)
    sys.exit(0 if success else 1)

"""
Migration script to move data from local storage to Supabase
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add project directories to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PARENT_ROOT) not in sys.path:
    sys.path.insert(0, str(PARENT_ROOT))

from backend.storage.supabase_client import (
    insert_gdd_document,
    insert_gdd_chunks,
    get_supabase_client
)
from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func
from gdd_rag_backbone.config import PROJECT_ROOT

# Local storage paths
MARKDOWN_WORKING_DIR = PARENT_ROOT / "rag_storage_md_indexed"
MARKDOWN_CHUNKS_DIR = PARENT_ROOT / "rag_storage_md"
CHUNKS_PATH = MARKDOWN_WORKING_DIR / "kv_store_text_chunks.json"
VDB_CHUNKS_PATH = MARKDOWN_WORKING_DIR / "vdb_chunks.json"
STATUS_PATH = MARKDOWN_WORKING_DIR / "kv_store_doc_status.json"


def load_local_documents():
    """Load document status from local storage"""
    if not STATUS_PATH.exists():
        return {}
    
    try:
        with open(STATUS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def load_local_chunks():
    """Load chunks from local storage"""
    if not CHUNKS_PATH.exists():
        return {}
    
    try:
        with open(CHUNKS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def load_local_vectors():
    """Load vectors from local storage"""
    if not VDB_CHUNKS_PATH.exists():
        return {"data": []}
    
    try:
        with open(VDB_CHUNKS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if "data" in data else {"data": []}
    except Exception:
        return {"data": []}


def migrate_gdd_to_supabase():
    """Migrate GDD documents and chunks from local storage to Supabase"""
    print("Starting GDD migration to Supabase...")
    
    # Check Supabase connection
    try:
        client = get_supabase_client()
        print("✓ Supabase connection successful")
    except Exception as e:
        print(f"✗ Supabase connection failed: {e}")
        print("Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")
        return False
    
    # Load local data
    print("\nLoading local data...")
    doc_status = load_local_documents()
    chunks_data = load_local_chunks()
    vectors_data = load_local_vectors()
    
    if not doc_status:
        print("No documents found in local storage")
        return False
    
    print(f"Found {len(doc_status)} documents to migrate")
    
    # Create vector lookup
    vector_lookup = {}
    for entry in vectors_data.get("data", []):
        chunk_id = entry.get("__id__") or entry.get("id")
        vector = entry.get("vector") or entry.get("embedding")
        if chunk_id and vector:
            vector_lookup[chunk_id] = vector
    
    # Migrate each document
    migrated_count = 0
    for doc_id, status in doc_status.items():
        print(f"\nMigrating document: {doc_id}")
        
        try:
            # Insert document metadata
            file_path = status.get("file_path", "")
            file_name = Path(file_path).name if file_path else doc_id
            
            insert_gdd_document(
                doc_id=doc_id,
                name=file_name,
                file_path=file_path
            )
            print(f"  ✓ Document metadata inserted")
            
            # Find chunks for this document
            doc_chunks = []
            for chunk_id, chunk_data in chunks_data.items():
                if isinstance(chunk_data, dict) and chunk_data.get("full_doc_id") == doc_id:
                    content = chunk_data.get("content", "")
                    embedding = vector_lookup.get(chunk_id)
                    
                    if content:
                        doc_chunks.append({
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "content": content,
                            "embedding": embedding,
                            "metadata": {
                                "migrated_from": "local_storage",
                                "original_metadata": chunk_data.get("metadata", {})
                            }
                        })
            
            if doc_chunks:
                # Insert chunks
                inserted = insert_gdd_chunks(doc_chunks)
                print(f"  ✓ Inserted {inserted} chunks")
                migrated_count += 1
            else:
                print(f"  ⚠ No chunks found for this document")
                
        except Exception as e:
            print(f"  ✗ Error migrating {doc_id}: {e}")
            continue
    
    print(f"\n✓ Migration complete! Migrated {migrated_count} documents")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("GDD RAG → Supabase Migration Script")
    print("=" * 60)
    
    # Check if Supabase is configured
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
        print("\n✗ Error: Supabase not configured")
        print("Please set SUPABASE_URL and SUPABASE_KEY in .env file")
        sys.exit(1)
    
    success = migrate_gdd_to_supabase()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration successful! You can now use Supabase for storage.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Migration failed. Check errors above.")
        print("=" * 60)
        sys.exit(1)


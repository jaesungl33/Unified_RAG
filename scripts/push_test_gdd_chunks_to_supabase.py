#!/usr/bin/env python3
"""
Script to push 10 indexed GDD chunks to Supabase for testing.

This script:
1. Loads chunks from gdd_data/summarised_chunks/kv_store_text_chunks.json
2. Loads corresponding vectors from gdd_data/summarised_chunks/vdb_chunks.json
3. Selects 10 chunks (from different documents for variety)
4. Pushes them to Supabase for testing accuracy and performance
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import insert_gdd_document, insert_gdd_chunks
from gdd_rag_backbone.llm_providers import QwenProvider

# Paths
CHUNKS_FILE = PROJECT_ROOT / "gdd_data" / "summarised_chunks" / "kv_store_text_chunks.json"
VDB_FILE = PROJECT_ROOT / "gdd_data" / "summarised_chunks" / "vdb_chunks.json"
STATUS_FILE = PROJECT_ROOT / "gdd_data" / "summarised_chunks" / "kv_store_doc_status.json"

# Number of test chunks
TEST_CHUNK_COUNT = 10


def load_chunks() -> Dict[str, Dict]:
    """Load chunks from kv_store_text_chunks.json."""
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(f"Chunks file not found: {CHUNKS_FILE}")
    
    with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_vectors() -> Dict[str, List[float]]:
    """Load vectors from vdb_chunks.json."""
    if not VDB_FILE.exists():
        raise FileNotFoundError(f"Vectors file not found: {VDB_FILE}")
    
    with open(VDB_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract vectors into a dict keyed by chunk ID
    vectors = {}
    for entry in data.get("data", []):
        chunk_id = entry.get("__id__")
        vector = entry.get("vector")
        if chunk_id and vector:
            # Ensure vector is a list of floats
            try:
                vectors[chunk_id] = [float(v) for v in vector]
            except (ValueError, TypeError):
                print(f"Warning: Skipping invalid vector for {chunk_id}")
                continue
    
    return vectors


def load_doc_status() -> Dict[str, Dict]:
    """Load document status."""
    if not STATUS_FILE.exists():
        return {}
    
    with open(STATUS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def select_test_chunks(chunks: Dict[str, Dict], vectors: Dict[str, List[float]], count: int = 10) -> List[Dict[str, Any]]:
    """
    Select test chunks from different documents.
    
    Args:
        chunks: Dictionary of chunks keyed by chunk_id
        vectors: Dictionary of vectors keyed by chunk_id
        count: Number of chunks to select
    
    Returns:
        List of chunk dictionaries ready for Supabase insertion
    """
    # Group chunks by document
    chunks_by_doc: Dict[str, List[str]] = {}
    for chunk_id, chunk_data in chunks.items():
        doc_id = chunk_data.get("full_doc_id")
        if doc_id and chunk_id in vectors:
            if doc_id not in chunks_by_doc:
                chunks_by_doc[doc_id] = []
            chunks_by_doc[doc_id].append(chunk_id)
    
    # Select chunks from different documents
    selected_chunks = []
    doc_ids = list(chunks_by_doc.keys())
    random.seed(42)  # For reproducibility
    random.shuffle(doc_ids)
    
    chunks_per_doc = max(1, count // len(doc_ids)) if doc_ids else 0
    remaining = count
    
    for doc_id in doc_ids:
        if remaining <= 0:
            break
        
        doc_chunks = chunks_by_doc[doc_id]
        random.shuffle(doc_chunks)
        
        # Take up to chunks_per_doc from this document
        take_count = min(chunks_per_doc, len(doc_chunks), remaining)
        for chunk_id in doc_chunks[:take_count]:
            chunk_data = chunks[chunk_id]
            vector = vectors[chunk_id]
            
            # Extract chunk_id without doc_id prefix
            base_chunk_id = chunk_data.get("chunk_id") or chunk_id.split("_chunk_")[-1] if "_chunk_" in chunk_id else chunk_id
            
            selected_chunks.append({
                "chunk_id": f"{doc_id}_{base_chunk_id}",
                "doc_id": doc_id,
                "content": chunk_data.get("content", ""),
                "embedding": vector,
                "metadata": chunk_data.get("metadata", {})
            })
            
            remaining -= 1
            if remaining <= 0:
                break
    
    return selected_chunks


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Push test GDD chunks to Supabase")
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt and push immediately"
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("PUSH TEST GDD CHUNKS TO SUPABASE")
    print("=" * 70)
    print()
    
    # Check if Supabase is configured
    import os
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_KEY'):
        print("[ERROR] Supabase not configured!")
        print("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env file")
        return 1
    
    # Load data
    print("Loading chunks and vectors...")
    try:
        chunks = load_chunks()
        vectors = load_vectors()
        doc_status = load_doc_status()
        print(f"  Loaded {len(chunks)} chunks")
        print(f"  Loaded {len(vectors)} vectors")
        print(f"  Found {len(doc_status)} documents")
    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        return 1
    
    # Select test chunks
    print(f"\nSelecting {TEST_CHUNK_COUNT} test chunks...")
    try:
        test_chunks = select_test_chunks(chunks, vectors, TEST_CHUNK_COUNT)
        print(f"  Selected {len(test_chunks)} chunks from {len(set(c['doc_id'] for c in test_chunks))} documents")
    except Exception as e:
        print(f"[ERROR] Failed to select chunks: {e}")
        return 1
    
    # Show selected chunks
    print("\nSelected chunks:")
    print("-" * 70)
    for i, chunk in enumerate(test_chunks, 1):
        doc_id = chunk['doc_id']
        chunk_id = chunk['chunk_id']
        try:
            content_preview = chunk['content'][:60].replace('\n', ' ')
            print(f"  {i:2d}. {doc_id}")
            print(f"      Chunk: {chunk_id}")
            print(f"      Preview: {content_preview}...")
        except UnicodeEncodeError:
            # Handle encoding errors for special characters
            print(f"  {i:2d}. {doc_id}")
            print(f"      Chunk: {chunk_id}")
            print(f"      Preview: [Content contains special characters]")
        print()
    
    # Confirm before proceeding
    if not args.yes:
        print("=" * 70)
        try:
            response = input(f"Push {len(test_chunks)} chunks to Supabase? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Cancelled.")
                return 0
        except EOFError:
            print("\n[ERROR] Cannot read input. Use --yes flag for non-interactive mode.")
            return 1
    else:
        print("=" * 70)
        print(f"Pushing {len(test_chunks)} chunks to Supabase (--yes flag set)...")
        print("=" * 70)
    
    # Insert document metadata for any new documents
    print("\nInserting document metadata...")
    doc_ids = set(c['doc_id'] for c in test_chunks)
    for doc_id in doc_ids:
        doc_info = doc_status.get(doc_id, {})
        doc_name = doc_info.get("file_name", doc_id).replace("_chunks.json", "")
        file_path = doc_info.get("file_path", "")
        
        try:
            insert_gdd_document(
                doc_id=doc_id,
                name=doc_name,
                file_path=file_path
            )
            print(f"  [OK] Document: {doc_id}")
        except Exception as e:
            print(f"  [WARNING] Failed to insert document {doc_id}: {e}")
    
    # Insert chunks
    print(f"\nInserting {len(test_chunks)} chunks to Supabase...")
    try:
        inserted_count = insert_gdd_chunks(test_chunks)
        print(f"\n[SUCCESS] Inserted {inserted_count} chunks to Supabase")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Chunks inserted: {inserted_count}")
        print(f"Documents: {len(doc_ids)}")
        print("\nYou can now test:")
        print("  1. Query accuracy using the GDD RAG interface")
        print("  2. Response time for vector searches")
        print("  3. Verify embeddings are working correctly")
        print("=" * 70)
        
        return 0
    except Exception as e:
        print(f"\n[ERROR] Failed to insert chunks: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

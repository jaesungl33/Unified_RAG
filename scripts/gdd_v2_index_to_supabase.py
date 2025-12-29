"""
Script 2: Re-index Enhanced GDD Chunks to Supabase (v2)
=======================================================
Indexes chunks from gdd_data_v2/chunks/ to Supabase with enhanced metadata.

Key features:
- Stores section_path, section_title, content_type, doc_category, tags
- Generates embeddings using Qwen text-embedding-v4
- Stores in Supabase with all new metadata columns
- Preserves original chunks (doesn't modify them)

Output: Indexed chunks in Supabase with full metadata
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# Import Supabase functions
try:
    from backend.storage.supabase_client import (
        get_supabase_client,
        SUPABASE_URL,
        SUPABASE_KEY,
        SUPABASE_SERVICE_KEY
    )
    # Check if Supabase is configured
    SUPABASE_AVAILABLE = bool(SUPABASE_URL and SUPABASE_KEY)
    if not SUPABASE_AVAILABLE:
        print("Warning: SUPABASE_URL or SUPABASE_KEY not set in environment")
        print(f"  SUPABASE_URL: {bool(SUPABASE_URL)}")
        print(f"  SUPABASE_KEY: {bool(SUPABASE_KEY)}")
except ImportError as e:
    SUPABASE_AVAILABLE = False
    print(f"Warning: Failed to import supabase_client: {e}")
    import traceback
    traceback.print_exc()

# Import embedding provider
try:
    from gdd_rag_backbone.llm_providers import QwenProvider, make_embedding_func
except ImportError:
    sys.path.insert(0, str(PROJECT_ROOT / "gdd_rag_backbone"))
    from llm_providers import QwenProvider, make_embedding_func

# Paths
CHUNKS_DIR = PROJECT_ROOT / "gdd_data_v2" / "chunks"
INDEXED_DIR = PROJECT_ROOT / "gdd_data_v2" / "indexed"


def load_v2_chunks(doc_id: str) -> List[Dict]:
    """
    Load enhanced chunks from v2 chunks directory.
    
    Args:
        doc_id: Document ID
    
    Returns:
        List of chunk dictionaries with enhanced metadata
    """
    chunks_file = CHUNKS_DIR / doc_id / f"{doc_id}_chunks.json"
    
    if not chunks_file.exists():
        return []
    
    try:
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        return chunks
    except Exception as e:
        print(f"  [ERROR] loading chunks from {chunks_file}: {e}")
        return []


def find_v2_doc_ids() -> List[str]:
    """Find all document IDs that have been chunked in v2."""
    if not CHUNKS_DIR.exists():
        return []
    
    doc_ids = []
    for doc_dir in CHUNKS_DIR.iterdir():
        if doc_dir.is_dir():
            chunks_file = doc_dir / f"{doc_dir.name}_chunks.json"
            if chunks_file.exists():
                doc_ids.append(doc_dir.name)
    
    return sorted(doc_ids)


async def index_v2_chunks_for_doc(
    doc_id: str,
    embedding_func,
    dry_run: bool = False
) -> tuple[bool, str]:
    """
    Index enhanced chunks for a single document to Supabase.
    
    Args:
        doc_id: Document ID
        embedding_func: Embedding function
        dry_run: If True, don't actually index
    
    Returns:
        (success, message) tuple
    """
    if not SUPABASE_AVAILABLE:
        return False, "Supabase is not configured"
    
    # Load v2 chunks
    chunks = load_v2_chunks(doc_id)
    
    if not chunks:
        return False, f"No v2 chunks found for {doc_id}"
    
    if dry_run:
        return True, f"[DRY RUN] Would index {len(chunks)} chunks for {doc_id}"
    
    print(f"  Processing {len(chunks)} chunks...")
    
    # Generate embeddings
    chunk_contents = [chunk["content"] for chunk in chunks]
    
    try:
        print(f"  Generating embeddings for {len(chunk_contents)} chunks...")
        
        # Generate embeddings (handle both sync and async)
        if hasattr(embedding_func, '__call__'):
            try:
                embeddings = await embedding_func(chunk_contents)
            except TypeError:
                embeddings = embedding_func(chunk_contents)
        else:
            embeddings = embedding_func(chunk_contents)
        
        if len(embeddings) != len(chunks):
            raise ValueError(f"Expected {len(chunks)} embeddings, got {len(embeddings)}")
        
        # Prepare chunks for Supabase with enhanced metadata
        supabase_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            # Use full chunk_id format: {doc_id}_{chunk_id}
            full_chunk_id = f"{doc_id}_{chunk['chunk_id']}"
            
            # Extract metadata
            section_path = chunk.get("section_path", "")
            section_title = chunk.get("section_title", "")
            subsection_title = chunk.get("subsection_title")
            section_index = chunk.get("section_index")
            paragraph_index = chunk.get("paragraph_index")
            content_type = chunk.get("content_type", "ui")
            doc_category = chunk.get("doc_category", "General")
            tags = chunk.get("tags", [])
            numbered_header = chunk.get("numbered_header")  # Key field for retrieval
            
            supabase_chunk = {
                "chunk_id": full_chunk_id,  # Full format to match local storage
                "doc_id": doc_id,
                "content": chunk["content"],
                "embedding": embedding,
                # New metadata columns
                "section_path": section_path,
                "section_title": section_title,
                "subsection_title": subsection_title,
                "section_index": section_index,
                "paragraph_index": paragraph_index,
                "content_type": content_type,
                "doc_category": doc_category,
                "tags": tags if tags else None,  # PostgreSQL array
                # Keep original metadata in JSONB (including numbered_header for easy retrieval)
                "metadata": {
                    **chunk.get("metadata", {}),
                    "numbered_header": numbered_header,  # Store in metadata for retrieval
                    "parent_header": chunk.get("parent_header"),
                    "part_number": chunk.get("part_number"),
                    "token_count": chunk.get("token_count", 0),
                    "original_chunk_id": chunk["chunk_id"]
                }
            }
            supabase_chunks.append(supabase_chunk)
        
        # Insert document metadata
        # Extract doc_category from first chunk or use default
        doc_category = supabase_chunks[0].get("doc_category", "General") if supabase_chunks else "General"
        
        # Try to get file path from markdown directory
        markdown_dir = PROJECT_ROOT / "gdd_data" / "markdown"
        file_path = None
        if markdown_dir.exists():
            for md_file in markdown_dir.glob("*.md"):
                if md_file.stem.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "_").replace(",", "_") == doc_id:
                    file_path = str(md_file)
                    break
        
        file_name = Path(file_path).name if file_path else f"{doc_id}.md"
        
        try:
            client = get_supabase_client(use_service_key=True)
            # Insert/update document with doc_category
            result = client.table('gdd_documents').upsert({
                'doc_id': doc_id,
                'name': file_name,
                'file_path': file_path,
                'doc_category': doc_category
            }, on_conflict='doc_id').execute()
            print(f"  [OK] Inserted document metadata (category: {doc_category})")
        except Exception as e:
            print(f"  [WARN] Failed to insert document: {e}")
            # Continue anyway - chunks might still work
        
        # Insert chunks with enhanced metadata
        # Note: We need to update insert_gdd_chunks to handle new columns
        # For now, we'll insert directly
        try:
            client = get_supabase_client(use_service_key=True)
            
            # Insert in batches
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(supabase_chunks), batch_size):
                batch = supabase_chunks[i:i + batch_size]
                result = client.table('gdd_chunks').upsert(
                    batch,
                    on_conflict='chunk_id'
                ).execute()
                total_inserted += len(result.data) if result.data else 0
            
            print(f"  [OK] Inserted {total_inserted} chunks with enhanced metadata")
            return True, f"[OK] Indexed {total_inserted} chunks for {doc_id}"
        except Exception as e:
            import traceback
            print(f"  [ERROR] Failed to insert chunks: {e}")
            traceback.print_exc()
            return False, f"[ERROR] Failed to index {doc_id}: {e}"
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"[ERROR] Failed to index {doc_id}: {e}"


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Index enhanced GDD chunks (v2) to Supabase"
    )
    parser.add_argument(
        "--doc-id",
        type=str,
        help="Document ID to index (if not provided, indexes all found documents)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip documents that are already indexed in Supabase"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to index (for testing, e.g., --limit 10)"
    )
    args = parser.parse_args()
    
    if not SUPABASE_AVAILABLE:
        print("ERROR: Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
        print()
        print("Troubleshooting:")
        print("1. Check that .env file exists in project root")
        print("2. Verify SUPABASE_URL and SUPABASE_KEY are set")
        print("3. Run: python scripts/test_supabase_config.py")
        return 1
    
    print("=" * 70)
    print("ENHANCED GDD CHUNKS INDEXING (v2) TO SUPABASE")
    print("=" * 70)
    print(f"Chunks directory: {CHUNKS_DIR}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)
    print()
    
    # Find documents to index
    if args.doc_id:
        doc_ids = [args.doc_id]
    else:
        doc_ids = find_v2_doc_ids()
        
        # Apply limit if specified
        if args.limit and args.limit > 0:
            doc_ids = doc_ids[:args.limit]
            print(f"[LIMIT MODE] Indexing only first {args.limit} documents for testing")
    
    if not doc_ids:
        print("No v2 chunks found to index!")
        print(f"Make sure you've run gdd_v2_chunk_markdown.py first")
        return 1
    
    print(f"Found {len(doc_ids)} document(s) to index")
    print()
    
    # Check existing documents in Supabase
    if args.skip_existing:
        try:
            from backend.storage.supabase_client import get_gdd_documents
            existing_docs = get_gdd_documents()
            existing_doc_ids = {doc.get('doc_id') for doc in existing_docs}
            doc_ids = [doc_id for doc_id in doc_ids if doc_id not in existing_doc_ids]
            if not doc_ids:
                print("All documents are already indexed. Use --skip-existing=false to re-index anyway.")
                return 0
            print(f"After filtering, {len(doc_ids)} document(s) need indexing")
            print()
        except Exception as e:
            print(f"Warning: Could not check existing documents: {e}")
    
    # Initialize embedding function
    print("Initializing embedding provider...")
    try:
        provider = QwenProvider()
        embedding_func = make_embedding_func(provider)
        print("[OK] Embedding provider ready")
        print()
    except Exception as e:
        print(f"[ERROR] Failed to initialize embedding provider: {e}")
        return 1
    
    # Process each document
    print("STARTING INDEXING")
    print("=" * 70)
    
    success_count = 0
    fail_count = 0
    
    for i, doc_id in enumerate(doc_ids, 1):
        try:
            print(f"[{i}/{len(doc_ids)}] {doc_id}")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(f"[{i}/{len(doc_ids)}] {doc_id.encode('ascii', 'ignore').decode('ascii')}")
        
        success, message = await index_v2_chunks_for_doc(
            doc_id=doc_id,
            embedding_func=embedding_func,
            dry_run=args.dry_run
        )
        
        try:
            print(f"  {message}")
        except UnicodeEncodeError:
            print(f"  {message.encode('ascii', 'ignore').decode('ascii')}")
        
        if success:
            success_count += 1
        else:
            fail_count += 1
        
        print()
    
    print("=" * 70)
    try:
        print(f"COMPLETE: {success_count} succeeded, {fail_count} failed")
    except UnicodeEncodeError:
        print(f"COMPLETE: {success_count} succeeded, {fail_count} failed")
    print("=" * 70)
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

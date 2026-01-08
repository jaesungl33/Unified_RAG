#!/usr/bin/env python3
"""
Build dictionary for GDD documents.

Usage:
    # List available documents
    python scripts/build_dictionary.py --list

    # Build dictionary for one document
    python scripts/build_dictionary.py --doc_id <doc_id>

    # Build dictionary for all documents
    python scripts/build_dictionary.py --all
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client
from gdd_dictionary.dictionary_builder import build_dictionary_for_doc

def list_documents():
    """List all available GDD documents."""
    client = get_supabase_client()
    print("\n" + "=" * 70)
    print("Available GDD Documents")
    print("=" * 70)
    
    try:
        res = client.table("gdd_documents").select("doc_id, name, chunks_count").order("name").execute()
        docs = res.data or []
        
        if not docs:
            print("⚠️  No documents found in database")
            print("   Make sure you've indexed GDD documents first.")
            return []
        
        print(f"\nFound {len(docs)} document(s):\n")
        for i, doc in enumerate(docs, 1):
            chunks = doc.get("chunks_count", 0)
            print(f"  {i}. {doc.get('name', 'Unknown')}")
            print(f"     doc_id: {doc.get('doc_id', 'N/A')}")
            print(f"     chunks: {chunks}")
            print()
        
        return docs
    except Exception as e:
        print(f"❌ Error listing documents: {e}")
        import traceback
        traceback.print_exc()
        return []

def build_for_doc(doc_id: str):
    """Build dictionary for a specific document."""
    print(f"\n{'=' * 70}")
    print(f"Building dictionary for doc_id: {doc_id}")
    print("=" * 70)
    
    result = build_dictionary_for_doc(doc_id)
    
    if result.get("status") == "success":
        print(f"\n✅ Success!")
        print(f"   Components: {result.get('components', 0)}")
        print(f"   References: {result.get('references', 0)}")
    else:
        print(f"\n❌ Error: {result.get('message', 'Unknown error')}")
    
    return result

def build_for_all():
    """Build dictionary for all documents."""
    docs = list_documents()
    
    if not docs:
        print("❌ No documents available to process")
        return
    
    print(f"\n{'=' * 70}")
    print(f"Building dictionary for ALL documents ({len(docs)} total)")
    print("=" * 70)
    
    response = input("\n⚠️  This will rebuild dictionaries for all documents. Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    total_components = 0
    total_references = 0
    success_count = 0
    error_count = 0
    
    for i, doc in enumerate(docs, 1):
        doc_id = doc.get("doc_id")
        doc_name = doc.get("name", "Unknown")
        
        print(f"\n[{i}/{len(docs)}] Processing: {doc_name} ({doc_id})")
        print("-" * 70)
        
        result = build_dictionary_for_doc(doc_id)
        
        if result.get("status") == "success":
            components = result.get("components", 0)
            references = result.get("references", 0)
            total_components += components
            total_references += references
            success_count += 1
            print(f"✅ {components} components, {references} references")
        else:
            error_count += 1
            print(f"❌ Failed: {result.get('message', 'Unknown error')}")
    
    print(f"\n{'=' * 70}")
    print("Summary")
    print("=" * 70)
    print(f"✅ Success: {success_count}/{len(docs)} documents")
    print(f"❌ Errors: {error_count}/{len(docs)} documents")
    print(f"📊 Total components: {total_components}")
    print(f"📊 Total references: {total_references}")

def main():
    parser = argparse.ArgumentParser(
        description="Build dictionary for GDD documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available documents
  python scripts/build_dictionary.py --list

  # Build for one document
  python scripts/build_dictionary.py --doc_id "tank_design_doc"

  # Build for all documents
  python scripts/build_dictionary.py --all
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List available documents")
    group.add_argument("--doc_id", type=str, help="Build dictionary for specific document ID")
    group.add_argument("--all", action="store_true", help="Build dictionary for all documents")
    
    args = parser.parse_args()
    
    if args.list:
        list_documents()
    elif args.doc_id:
        build_for_doc(args.doc_id)
    elif args.all:
        build_for_all()

if __name__ == "__main__":
    main()



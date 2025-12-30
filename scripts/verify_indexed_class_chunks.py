"""
Verify that indexed class chunks can be retrieved from Supabase.
Fetches all class chunks and displays their file paths to verify correctness.
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

from backend.storage.supabase_client import get_supabase_client


def main():
    """Fetch and display all class chunks from Supabase."""
    print("=" * 80)
    print("🔍 Verifying Indexed Class Chunks in Supabase")
    print("=" * 80)
    print()
    
    try:
        client = get_supabase_client()
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return
    
    # Fetch all class chunks
    print("📊 Fetching all class chunks from Supabase...")
    try:
        result = (
            client.table("code_chunks")
            .select("file_path, class_name, chunk_type, created_at, source_code")
            .eq("chunk_type", "class")
            .order("created_at", desc=True)
            .execute()
        )
        
        chunks = result.data if result.data else []
        
        print(f"✅ Found {len(chunks)} class chunk(s) in Supabase\n")
        
        if not chunks:
            print("⚠️  No class chunks found!")
            return
        
        # Display all chunks
        print("📋 All Class Chunks:")
        print("-" * 80)
        for i, chunk in enumerate(chunks, 1):
            file_path = chunk.get("file_path", "N/A")
            class_name = chunk.get("class_name", "N/A")
            source_code = chunk.get("source_code", "")
            source_length = len(source_code) if source_code else 0
            created_at = chunk.get("created_at", "N/A")
            
            print(f"\n[{i}/{len(chunks)}]")
            print(f"   File Path: {file_path}")
            print(f"   Class Name: {class_name}")
            print(f"   Source Code Length: {source_length:,} characters")
            print(f"   Created At: {created_at}")
        
        # Group by file path
        print("\n" + "=" * 80)
        print("📁 Grouped by File Path:")
        print("=" * 80)
        
        files_dict = {}
        for chunk in chunks:
            file_path = chunk.get("file_path", "N/A")
            class_name = chunk.get("class_name", "N/A")
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append(class_name)
        
        for file_path, class_names in sorted(files_dict.items()):
            print(f"\n📄 {file_path}")
            print(f"   Classes: {', '.join(class_names)} ({len(class_names)} class chunk(s))")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 Summary:")
        print("=" * 80)
        print(f"   Total class chunks: {len(chunks)}")
        print(f"   Unique files: {len(files_dict)}")
        print(f"   Average chunks per file: {len(chunks) / len(files_dict):.2f}")
        
        # Check if paths match expected format
        print("\n🔍 Path Format Analysis:")
        print("-" * 80)
        assets_paths = [fp for fp in files_dict.keys() if "assets" in fp.lower()]
        non_assets_paths = [fp for fp in files_dict.keys() if "assets" not in fp.lower()]
        
        print(f"   Paths containing 'assets': {len(assets_paths)}")
        print(f"   Paths NOT containing 'assets': {len(non_assets_paths)}")
        
        if non_assets_paths:
            print("\n   ⚠️  Paths without 'assets':")
            for path in non_assets_paths[:5]:
                print(f"      - {path}")
            if len(non_assets_paths) > 5:
                print(f"      ... and {len(non_assets_paths) - 5} more")
        
    except Exception as e:
        print(f"❌ Error fetching class chunks: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


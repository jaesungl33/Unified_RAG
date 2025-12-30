"""
Check that ALL indexed code files can have their chunks retrieved from Supabase,
using the SAME lookup logic that Render uses (no local disk, Supabase only).

This script specifically verifies that the path format stored in Supabase
matches what Render's lookup logic can find.

Usage (locally or on Render shell):
    cd unified_rag_app
    python -m scripts.check_supabase_code_files_retrieval [--all]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from backend.storage.supabase_client import get_supabase_client
from backend.storage.code_supabase_storage import get_code_chunks_for_files


def analyze_path_format(file_path: str) -> Dict[str, str]:
    """Analyze the format of a file path"""
    return {
        "original": file_path,
        "filename": os.path.basename(file_path),
        "normalized_slashes": file_path.replace('\\', '/'),
        "lowercase": file_path.lower(),
        "uppercase": file_path.upper(),
    }


def check_all_code_files_retrieval(test_all: bool = False) -> None:
    """
    For every row in code_files:
      - Use the EXACT file_path from Supabase to test retrieval
      - Also test with simulated frontend paths (different formats)
      - Report any files where chunks exist but can't be retrieved
    """
    print("=" * 80)
    print("Supabase Code Files Retrieval Check - Path Format Verification")
    print("=" * 80)

    client = get_supabase_client()

    # 1) Fetch ALL code_files
    print("\nFetching code_files from Supabase...")
    files_result = client.table("code_files").select("file_path,file_name").execute()
    code_files: List[Dict] = files_result.data if files_result.data else []
    total_files = len(code_files)
    print(f"Total files in code_files: {total_files}")

    if not code_files:
        print("No code_files found in Supabase. Nothing to check.")
        return

    # Analyze path formats in Supabase
    print("\n" + "=" * 80)
    print("Analyzing path formats stored in Supabase...")
    print("=" * 80)
    
    sample_paths = code_files[:5]  # Analyze first 5 as samples
    for file_row in sample_paths:
        file_path = file_row.get("file_path")
        path_info = analyze_path_format(file_path)
        print(f"\nFile: {file_row.get('file_name')}")
        print(f"  Stored path format: {path_info['original']}")
        print(f"  Filename extracted: {path_info['filename']}")
        print(f"  Uses backslashes: {'\\' in path_info['original']}")
        print(f"  Is lowercase: {path_info['original'].islower()}")

    # 2) Test retrieval for all files
    print("\n" + "=" * 80)
    print("Testing chunk retrieval for all files...")
    print("=" * 80)

    missing_chunks_via_helper: List[Dict] = []
    missing_chunks_in_db: List[Dict] = []
    successful_retrievals = 0
    class_chunk_counts: List[Dict] = []  # Track class chunk counts for all files

    # Test with a sample first (to avoid too much output)
    if test_all:
        test_files = code_files
        test_sample_size = total_files
        print(f"\nTesting ALL {test_sample_size} files...")
    else:
        test_files = code_files  # Test all files by default to show class chunk counts
        test_sample_size = len(test_files)
        print(f"\nTesting all {test_sample_size} files to show class chunk counts...")

    for idx, file_row in enumerate(test_files, start=1):
        file_path = file_row.get("file_path")
        file_name = file_row.get("file_name")
        
        if idx <= 5:  # Detailed output for first 5
            print(f"\n[{idx}/{test_sample_size}] Checking: {file_name}")
            print(f"    Supabase file_path: {file_path}")
        else:
            print(f"[{idx}/{test_sample_size}] {file_name}...", end=" ", flush=True)

        # A) Use the EXACT file_path from Supabase (what Render should receive)
        helper_chunks_class = get_code_chunks_for_files([file_path], chunk_type="class")
        helper_chunks_method = get_code_chunks_for_files([file_path], chunk_type="method")
        helper_total = len(helper_chunks_class) + len(helper_chunks_method)
        class_count = len(helper_chunks_class)
        method_count = len(helper_chunks_method)
        
        if idx <= 5:
            print(f"    Helper retrieval: {class_count} class, {method_count} method (total {helper_total})")

        # B) Direct DB check: are there any chunks at all for this exact file_path?
        direct_result = (
            client.table("code_chunks")
            .select("id,chunk_type")
            .eq("file_path", file_path)  # Exact match with Supabase path
            .execute()
        )
        direct_chunks = direct_result.data if direct_result.data else []
        direct_total = len(direct_chunks)
        direct_types = {c.get("chunk_type") for c in direct_chunks} if direct_chunks else set()
        
        if idx <= 5:
            print(f"    Direct DB (exact file_path): {direct_total} chunks, types={direct_types}")

        # C) Test with different path formats (simulating frontend input)
        if idx <= 3:  # Only test first 3 with format variations
            print(f"\n    Testing path format variations:")
            
            # Variation 1: Forward slashes instead of backslashes
            path_forward_slash = file_path.replace('\\', '/')
            chunks_fs = get_code_chunks_for_files([path_forward_slash], chunk_type=None)
            print(f"      Forward slashes: {len(chunks_fs)} chunks")
            
            # Variation 2: Uppercase
            path_upper = file_path.upper()
            chunks_upper = get_code_chunks_for_files([path_upper], chunk_type=None)
            print(f"      Uppercase: {len(chunks_upper)} chunks")
            
            # Variation 3: Just filename
            filename_only = os.path.basename(file_path)
            chunks_filename = get_code_chunks_for_files([filename_only], chunk_type=None)
            print(f"      Filename only: {len(chunks_filename)} chunks")

        # D) Diagnose mismatches
        if direct_total == 0:
            missing_chunks_in_db.append({
                "file_path": file_path,
                "file_name": file_name,
            })
            if idx > 5:
                print("❌ No chunks in DB")
        elif direct_total > 0 and helper_total == 0:
            missing_chunks_via_helper.append({
                "file_path": file_path,
                "file_name": file_name,
                "direct_chunk_count": direct_total,
                "direct_types": list(direct_types),
            })
            if idx > 5:
                print(f"⚠️  {direct_total} chunks in DB but helper returned 0")
        else:
            successful_retrievals += 1
            # Store class chunk count for summary
            class_chunk_counts.append({
                "file_name": file_name,
                "file_path": file_path,
                "class_count": class_count,
                "method_count": method_count,
                "total": helper_total
            })
            if idx > 5:
                # Show class chunk count prominently
                print(f"✅ {class_count} class, {method_count} method chunks")

    # 3) Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    print(f"\n✅ Successful retrievals: {successful_retrievals}/{test_sample_size}")
    
    # Show class chunk statistics
    if class_chunk_counts:
        total_class_chunks = sum(c["class_count"] for c in class_chunk_counts)
        total_method_chunks = sum(c["method_count"] for c in class_chunk_counts)
        files_with_class_chunks = sum(1 for c in class_chunk_counts if c["class_count"] > 0)
        files_without_class_chunks = sum(1 for c in class_chunk_counts if c["class_count"] == 0)
        
        print(f"\n📊 Class Chunk Statistics:")
        print(f"   Total class chunks across all files: {total_class_chunks}")
        print(f"   Total method chunks across all files: {total_method_chunks}")
        print(f"   Files WITH class chunks: {files_with_class_chunks}")
        print(f"   Files WITHOUT class chunks: {files_without_class_chunks}")
        
        # Show files without class chunks (these might be problematic)
        if files_without_class_chunks > 0:
            print(f"\n⚠️  Files without class chunks ({files_without_class_chunks} files):")
            for file_info in [c for c in class_chunk_counts if c["class_count"] == 0][:20]:
                print(f"   - {file_info['file_name']} (has {file_info['method_count']} method chunks)")
            if files_without_class_chunks > 20:
                print(f"   ... and {files_without_class_chunks - 20} more")
    
    if not missing_chunks_in_db and not missing_chunks_via_helper:
        print("\n✅ All tested files have chunks and are retrievable via helper logic.")
    else:
        if missing_chunks_in_db:
            print(
                f"\n❌ Files with NO chunks in code_chunks (indexed in code_files but no chunks): "
                f"{len(missing_chunks_in_db)}"
            )
            for row in missing_chunks_in_db[:10]:
                print(f"   - {row['file_name']}  ({row['file_path']})")
            if len(missing_chunks_in_db) > 10:
                print(f"   ... and {len(missing_chunks_in_db) - 10} more")

        if missing_chunks_via_helper:
            print(
                f"\n⚠️ Files where chunks exist in DB but helper lookup returns 0: "
                f"{len(missing_chunks_via_helper)}"
            )
            print("   This indicates a PATH FORMAT MISMATCH issue!")
            print("   The chunks exist in Supabase but the lookup logic can't find them.")
            for row in missing_chunks_via_helper[:10]:
                print(
                    f"   - {row['file_name']}"
                    f"\n     Path: {row['file_path']}"
                    f"\n     Direct DB chunks: {row['direct_chunk_count']}, types={row['direct_types']}"
                )
            if len(missing_chunks_via_helper) > 10:
                print(f"   ... and {len(missing_chunks_via_helper) - 10} more")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Supabase code file retrieval")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all files instead of just the first 20"
    )
    args = parser.parse_args()
    check_all_code_files_retrieval(test_all=args.all)



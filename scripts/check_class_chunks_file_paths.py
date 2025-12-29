"""
Check how many distinct file paths are indexed for class chunks in Supabase.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client


def main():
    print("=" * 80)
    print("🔍 Checking Class Chunks File Paths in Supabase")
    print("=" * 80)

    try:
        client = get_supabase_client()
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return
    
    # Fetch all class-like chunks
    print("\n📊 Fetching all class-like chunks from Supabase...")
    try:
        result = (
            client.table("code_chunks")
            .select("file_path, chunk_type, class_name")
            .in_("chunk_type", ["class", "struct", "interface", "enum"])
            .execute()
        )
        
        chunks = result.data if result.data else []
        
        print(f"✅ Found {len(chunks)} class-like chunk(s) in Supabase\n")
        
        if not chunks:
            print("⚠️  No class-like chunks found.")
            return
        
        # Count distinct file paths
        distinct_paths = set()
        path_counts = {}
        path_type_counts = {}
        
        for chunk in chunks:
            file_path = chunk.get("file_path", "UNKNOWN_FILE")
            chunk_type = chunk.get("chunk_type", "unknown")
            
            distinct_paths.add(file_path)
            
            # Count chunks per file
            if file_path not in path_counts:
                path_counts[file_path] = 0
            path_counts[file_path] += 1
            
            # Count by chunk type per file
            key = (file_path, chunk_type)
            if key not in path_type_counts:
                path_type_counts[key] = 0
            path_type_counts[key] += 1
        
        # Summary
        print("=" * 80)
        print("📊 Summary:")
        print("=" * 80)
        print(f"   Total class-like chunks: {len(chunks)}")
        print(f"   Distinct file paths: {len(distinct_paths)}")
        print(f"   Average chunks per file: {len(chunks) / len(distinct_paths):.2f}" if distinct_paths else "N/A")
        
        # Breakdown by chunk type
        print("\n📋 Breakdown by Chunk Type:")
        print("-" * 80)
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.get("chunk_type", "unknown")
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        for chunk_type, count in sorted(type_counts.items()):
            print(f"   {chunk_type}: {count} chunk(s)")
        
        # Path format analysis
        print("\n🔍 Path Format Analysis:")
        print("-" * 80)
        path_formats = {
            "New Format (Assets/...)": 0,
            "Old Format (Windows path)": 0,
            "Other Format": 0
        }
        
        for path in distinct_paths:
            path_lower = path.lower()
            if path_lower.startswith("assets/"):
                path_formats["New Format (Assets/...)"] += 1
            elif path_lower.startswith("c:\\") or path_lower.startswith("c:/"):
                path_formats["Old Format (Windows path)"] += 1
            else:
                path_formats["Other Format"] += 1
        
        for fmt, count in path_formats.items():
            print(f"   {fmt}: {count} file(s)")
        
        # Show files with most chunks
        print("\n📁 Top 20 Files by Chunk Count:")
        print("-" * 80)
        sorted_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (file_path, count) in enumerate(sorted_paths[:20], 1):
            # Get chunk types for this file
            file_types = [chunk_type for (fp, chunk_type), cnt in path_type_counts.items() if fp == file_path]
            type_summary = ", ".join(f"{t}:{file_types.count(t)}" for t in set(file_types))
            print(f"   {i:2d}. {file_path}")
            print(f"       Chunks: {count} ({type_summary})")
        
        if len(sorted_paths) > 20:
            print(f"\n   ... and {len(sorted_paths) - 20} more files")
        
        # Show sample paths
        print("\n📄 Sample File Paths (first 10):")
        print("-" * 80)
        for i, path in enumerate(list(distinct_paths)[:10], 1):
            chunk_count = path_counts[path]
            print(f"   {i:2d}. {path} ({chunk_count} chunk(s))")

    except Exception as e:
        print(f"❌ Error fetching class chunks: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()


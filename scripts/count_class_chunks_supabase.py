"""
Count and display all class chunks in Supabase.
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
    print("🔍 Count Class Chunks in Supabase")
    print("=" * 80)

    try:
        client = get_supabase_client()
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return
    
    # Fetch all class chunks
    print("\n📊 Fetching all class chunks from Supabase...")
    try:
        result = (
            client.table("code_chunks")
            .select("id, file_path, class_name, chunk_type, created_at, metadata")
            .eq("chunk_type", "class")
            .order("created_at", desc=True)
            .execute()
        )
        
        chunks = result.data if result.data else []
        
        print(f"\n✅ Found {len(chunks)} class chunk(s) in Supabase\n")
        
        if not chunks:
            print("⚠️  No class chunks found.")
            return
        
        # Group by file path
        files_grouped: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in chunks:
            file_path = chunk.get("file_path", "UNKNOWN_FILE")
            if file_path not in files_grouped:
                files_grouped[file_path] = []
            files_grouped[file_path].append(chunk)
        
        # Display summary
        print("=" * 80)
        print("📊 Summary:")
        print("=" * 80)
        print(f"   Total class chunks: {len(chunks)}")
        print(f"   Unique files: {len(files_grouped)}")
        print(f"   Average chunks per file: {len(chunks) / len(files_grouped):.2f}" if files_grouped else "N/A")
        
        # Show path format breakdown
        print("\n🔍 Path Format Analysis:")
        print("-" * 80)
        path_formats = {
            "Windows path (c:\\... or c:/...)": 0,
            "Assets/... format": 0,
            "Other format": 0
        }
        
        for file_path in files_grouped.keys():
            path_lower = file_path.lower()
            if path_lower.startswith("c:\\") or path_lower.startswith("c:/"):
                path_formats["Windows path (c:\\... or c:/...)"] += 1
            elif path_lower.startswith("assets/"):
                path_formats["Assets/... format"] += 1
            else:
                path_formats["Other format"] += 1
        
        for fmt, count in path_formats.items():
            print(f"   {fmt}: {count} file(s)")
        
        # Show recent chunks
        print("\n📋 Recent Class Chunks (last 20):")
        print("-" * 80)
        for i, chunk in enumerate(chunks[:20], 1):
            file_path = chunk.get("file_path", "UNKNOWN")
            class_name = chunk.get("class_name", "UNKNOWN")
            created_at = chunk.get("created_at", "UNKNOWN")
            indexed_from = chunk.get("metadata", {}).get("indexed_from", "unknown")
            
            # Truncate long paths
            if len(file_path) > 80:
                file_path_display = "..." + file_path[-77:]
            else:
                file_path_display = file_path
            
            print(f"   {i:2d}. {class_name:30s} | {file_path_display:80s} | {created_at[:19]} | {indexed_from}")
        
        if len(chunks) > 20:
            print(f"\n   ... and {len(chunks) - 20} more chunks")
        
        # Show files with most chunks
        print("\n📁 Files with Class Chunks:")
        print("-" * 80)
        sorted_files = sorted(files_grouped.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (file_path, file_chunks) in enumerate(sorted_files[:20], 1):
            class_names = [c.get("class_name", "unknown") for c in file_chunks]
            unique_classes = list(set(class_names))
            
            # Truncate long paths
            if len(file_path) > 70:
                file_path_display = "..." + file_path[-67:]
            else:
                file_path_display = file_path
            
            print(f"   {i:2d}. {file_path_display:70s} | {len(file_chunks)} chunk(s) | Classes: {', '.join(unique_classes[:3])}")
            if len(unique_classes) > 3:
                print(f"       ... and {len(unique_classes) - 3} more class(es)")
        
        if len(sorted_files) > 20:
            print(f"\n   ... and {len(sorted_files) - 20} more files")
        
        # Check for chunks created in last hour
        from datetime import datetime, timedelta
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        recent_chunks = [c for c in chunks if c.get("created_at", "") > one_hour_ago]
        
        if recent_chunks:
            print(f"\n🕐 Chunks created in last hour: {len(recent_chunks)}")
            print("-" * 80)
            for chunk in recent_chunks[:10]:
                print(f"   - {chunk.get('class_name', 'unknown')} in {chunk.get('file_path', 'unknown')[:60]}")
        else:
            print(f"\n🕐 No chunks created in the last hour")

    except Exception as e:
        print(f"❌ Error fetching class chunks: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()



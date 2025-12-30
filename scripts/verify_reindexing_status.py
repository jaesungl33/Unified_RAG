"""
Verify the reindexing status by checking Supabase.
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
    print("=" * 80)
    print("Reindexing Status Verification")
    print("=" * 80)
    
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Count chunks by type
        print("\n[1/3] Counting chunks by type...")
        result = client.table('code_chunks').select('chunk_type').execute()
        
        if result.data:
            type_counts = {}
            for row in result.data:
                chunk_type = row['chunk_type']
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            
            print("\n   Chunk type counts:")
            total = 0
            for chunk_type, count in sorted(type_counts.items()):
                print(f"      {chunk_type}: {count}")
                total += count
            print(f"\n   Total chunks: {total}")
        else:
            print("   No chunks found in database")
        
        # Count unique files
        print("\n[2/3] Counting unique files...")
        files_result = client.table('code_files').select('file_path').execute()
        if files_result.data:
            unique_files = set()
            for row in files_result.data:
                unique_files.add(row['file_path'])
            print(f"   Total unique files: {len(unique_files)}")
            
            # Show sample paths
            print("\n   Sample file paths (first 10):")
            for i, path in enumerate(sorted(list(unique_files))[:10], 1):
                print(f"      {i}. {path}")
        else:
            print("   No files found in database")
        
        # Check path format
        print("\n[3/3] Checking path format...")
        if files_result.data:
            relative_paths = 0
            windows_paths = 0
            for row in files_result.data:
                path = row['file_path']
                if path.startswith('Assets/') or path.startswith('assets/'):
                    relative_paths += 1
                elif '\\' in path or (path[1:3] == ':\\' if len(path) > 2 else False):
                    windows_paths += 1
            
            print(f"   Relative paths (Assets/...): {relative_paths}")
            print(f"   Windows paths (C:\\...): {windows_paths}")
        
        print("\n[OK] Verification complete!")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


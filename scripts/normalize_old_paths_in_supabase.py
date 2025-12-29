"""
Normalize old Windows path format to new Assets/... format in Supabase.
Updates both code_chunks and code_files tables.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client
from backend.storage.code_supabase_storage import normalize_path_consistent


def extract_assets_path(windows_path: str) -> Optional[str]:
    """
    Extract Assets/... portion from a Windows path.
    Example: c:/users/.../assets/_gameplay/scripts/file.cs -> Assets/_Gameplay/Scripts/file.cs
    """
    # Normalize to forward slashes and lowercase for searching
    path_normalized = windows_path.replace("\\", "/").lower()
    
    # Find "assets/" in the path
    assets_idx = path_normalized.find("assets/")
    if assets_idx == -1:
        return None
    
    # Extract from assets/ onwards (use original path, not normalized)
    # Find the index in the original path (case-insensitive)
    original_lower = windows_path.lower().replace("\\", "/")
    assets_idx_original = original_lower.find("assets/")
    if assets_idx_original == -1:
        return None
    
    assets_portion = windows_path[assets_idx_original:]
    
    # Normalize to forward slashes and preserve case
    assets_path = assets_portion.replace("\\", "/")
    
    # Try to match common case patterns
    # If path has _GameAssets, preserve that case
    if "_gameassets" in assets_path.lower():
        # Try to find the correct case
        original_lower = assets_path.lower()
        if "_gameassets" in original_lower:
            idx = original_lower.find("_gameassets")
            assets_path = assets_path[:idx] + "_GameAssets" + assets_path[idx+11:]
        if "_gamemodules" in original_lower:
            idx = original_lower.find("_gamemodules")
            assets_path = assets_path[:idx] + "_GameModules" + assets_path[idx+12:]
        if "_externalassets" in original_lower:
            idx = original_lower.find("_externalassets")
            assets_path = assets_path[:idx] + "_ExternalAssets" + assets_path[idx+15:]
        if "_externalpackages" in original_lower:
            idx = original_lower.find("_externalpackages")
            assets_path = assets_path[:idx] + "_ExternalPackages" + assets_path[idx+17:]
        if "_gameplay" in original_lower:
            idx = original_lower.find("_gameplay")
            assets_path = assets_path[:idx] + "_Gameplay" + assets_path[idx+9:]
    
    # Capitalize Assets/ at the start
    if assets_path.lower().startswith("assets/"):
        assets_path = "Assets/" + assets_path[7:]
    
    return assets_path


def find_old_format_paths(client) -> List[Dict[str, Any]]:
    """Find all chunks with old Windows path format."""
    try:
        # Get all chunks
        result = (
            client.table("code_chunks")
            .select("file_path, chunk_type, class_name, method_name")
            .execute()
        )
        
        chunks = result.data if result.data else []
        
        # Filter for old Windows paths
        old_path_chunks = []
        for chunk in chunks:
            file_path = chunk.get("file_path", "")
            if file_path and (file_path.startswith("c:\\") or file_path.startswith("C:\\") or 
                            file_path.startswith("c:/") or file_path.startswith("C:/")):
                old_path_chunks.append(chunk)
        
        return old_path_chunks
    except Exception as e:
        print(f"❌ Error finding old paths: {e}")
        import traceback
        traceback.print_exc()
        return []


def normalize_path_mapping(old_paths: List[str]) -> Dict[str, str]:
    """
    Create a mapping from old paths to new normalized paths.
    Returns dict: {old_path: new_path}
    """
    path_mapping = {}
    
    for old_path in old_paths:
        # Try using normalize_path_consistent first
        normalized = normalize_path_consistent(old_path)
        
        if normalized and (normalized.startswith("Assets/") or normalized.startswith("assets/")):
            # Ensure it starts with Assets/ (capitalized)
            if normalized.startswith("assets/"):
                normalized = "Assets/" + normalized[7:]
            path_mapping[old_path] = normalized
        else:
            # Fallback to extract_assets_path
            assets_path = extract_assets_path(old_path)
            if assets_path:
                # Ensure it starts with Assets/ (capitalized)
                if assets_path.lower().startswith("assets/"):
                    assets_path = "Assets/" + assets_path[7:]
                path_mapping[old_path] = assets_path
            else:
                print(f"⚠️  Could not normalize path: {old_path}")
                # Still create a mapping to avoid breaking foreign keys
                # Use the last portion of the path
                path_parts = old_path.replace("\\", "/").split("/")
                if len(path_parts) >= 2:
                    # Take last 2-3 parts
                    short_path = "/".join(path_parts[-3:])
                    if not short_path.startswith("Assets/"):
                        short_path = "Assets/" + short_path
                    path_mapping[old_path] = short_path
    
    return path_mapping


def update_code_files_table(client, path_mapping: Dict[str, str]) -> int:
    """Update code_files table with new paths."""
    updated_count = 0
    
    for old_path, new_path in path_mapping.items():
        try:
            # Check if new path already exists
            existing = (
                client.table("code_files")
                .select("file_path")
                .eq("file_path", new_path)
                .execute()
            )
            
            if existing.data and len(existing.data) > 0:
                # New path already exists, delete the old one
                result = (
                    client.table("code_files")
                    .delete()
                    .eq("file_path", old_path)
                    .execute()
                )
                print(f"   ✅ Deleted old code_file entry: {old_path}")
            else:
                # Update the old path to new path
                result = (
                    client.table("code_files")
                    .update({
                        "file_path": new_path,
                        "normalized_path": new_path
                    })
                    .eq("file_path", old_path)
                    .execute()
                )
                
                if result.data and len(result.data) > 0:
                    updated_count += 1
                    print(f"   ✅ Updated code_file: {old_path} -> {new_path}")
        except Exception as e:
            print(f"   ❌ Error updating code_file {old_path}: {e}")
    
    return updated_count


def update_code_chunks_table(client, path_mapping: Dict[str, str]) -> int:
    """Update code_chunks table with new paths."""
    updated_count = 0
    
    for old_path, new_path in path_mapping.items():
        try:
            # Update all chunks with this old path
            result = (
                client.table("code_chunks")
                .update({"file_path": new_path})
                .eq("file_path", old_path)
                .execute()
            )
            
            if result.data:
                chunk_count = len(result.data)
                updated_count += chunk_count
                print(f"   ✅ Updated {chunk_count} chunk(s): {old_path} -> {new_path}")
        except Exception as e:
            print(f"   ❌ Error updating chunks for {old_path}: {e}")
            import traceback
            traceback.print_exc()
    
    return updated_count


def main():
    print("=" * 80)
    print("🔄 Normalize Old Windows Paths to Assets/... Format")
    print("=" * 80)
    
    try:
        client = get_supabase_client(use_service_key=True)
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return
    
    # Find all old-format paths
    print("\n📊 Finding chunks with old Windows path format...")
    old_path_chunks = find_old_format_paths(client)
    
    if not old_path_chunks:
        print("✅ No old-format paths found. All paths are already normalized.")
        return
    
    # Get unique old paths
    old_paths = list(set(chunk.get("file_path", "") for chunk in old_path_chunks))
    old_paths = [p for p in old_paths if p]  # Filter empty
    
    print(f"✅ Found {len(old_paths)} unique old-format path(s)")
    print(f"   Affecting {len(old_path_chunks)} chunk(s)")
    
    # Show what we found
    print("\n📋 Old Paths Found:")
    print("-" * 80)
    for i, old_path in enumerate(old_paths, 1):
        chunk_count = sum(1 for c in old_path_chunks if c.get("file_path") == old_path)
        print(f"   {i:2d}. {old_path} ({chunk_count} chunk(s))")
    
    # Create path mapping
    print("\n🔄 Creating path mappings...")
    path_mapping = normalize_path_mapping(old_paths)
    
    print(f"✅ Created {len(path_mapping)} path mapping(s)")
    print("\n📋 Path Mappings:")
    print("-" * 80)
    for old_path, new_path in path_mapping.items():
        print(f"   {old_path}")
        print(f"   -> {new_path}")
        print()
    
    # Confirm
    print(f"\n⚠️  This will update {len(old_paths)} file path(s) and {len(old_path_chunks)} chunk(s)")
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Normalization cancelled")
        return
    
    # Update code_chunks table FIRST (to avoid foreign key constraint issues)
    print("\n🔄 Updating code_chunks table...")
    chunks_updated = update_code_chunks_table(client, path_mapping)
    print(f"✅ Updated {chunks_updated} chunk(s)")
    
    # Update code_files table after chunks (to maintain foreign key integrity)
    print("\n🔄 Updating code_files table...")
    files_updated = update_code_files_table(client, path_mapping)
    print(f"✅ Updated {files_updated} code_file entry/entries")
    
    # Verify
    print("\n🔍 Verifying updates...")
    remaining_old = find_old_format_paths(client)
    if remaining_old:
        print(f"⚠️  Warning: {len(remaining_old)} chunk(s) still have old-format paths")
        for chunk in remaining_old[:5]:
            print(f"   - {chunk.get('file_path')}")
    else:
        print("✅ All paths have been normalized!")
    
    print("\n" + "=" * 80)
    print("✅ Normalization Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()


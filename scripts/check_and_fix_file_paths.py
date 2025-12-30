"""
Check and fix file paths in Supabase code_chunks and code_files tables.

This script:
1. Fetches all file paths from Supabase
2. Identifies paths that need fixing (old project locations)
3. Updates them to match the current project structure
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client

def normalize_path_to_current_project(file_path: str) -> str:
    """
    Convert old project paths or relative paths to current full Windows paths.
    
    Old formats:
    - c:\\users\\cpu12391\\desktop\\gdd_rag_gradio\\tank_online_1-dev\\assets\\...
    - c:\\users\\cpu12391\\desktop\\gdd_rag_gradio\\codebase_rag\\tank_online_1-dev\\assets\\...
    - Assets/... (relative path)
    
    New format:
    - C:\\Users\\CPU12391\\Desktop\\unified_rag_app\\Assets\\... (full Windows path)
    """
    if not file_path:
        return file_path
    
    # Normalize to lowercase for comparison
    path_lower = file_path.lower()
    
    # Check if it's a relative Assets/... path
    if file_path.startswith('Assets/') or file_path.startswith('Assets\\'):
        # Convert relative path to full Windows path
        # Preserve case from Assets onwards
        assets_path = file_path[7:]  # Remove 'Assets/' or 'Assets\'
        # Normalize path separators and use Path to join
        assets_parts = assets_path.replace('\\', '/').split('/')
        new_path = str(PROJECT_ROOT / 'Assets' / Path(*assets_parts))
        return new_path
    
    # Check if it's an old path format with gdd_rag_gradio
    if 'gdd_rag_gradio' in path_lower:
        # Extract the Assets/... portion
        if '\\assets\\' in path_lower:
            assets_idx = path_lower.find('\\assets\\')
            # Keep original case from Assets onwards
            assets_path = file_path[assets_idx + 1:]  # +1 to skip the backslash
            # Replace backslashes with path separator and build new path
            new_path = str(PROJECT_ROOT / assets_path.replace('\\', '/'))
            return new_path
        elif path_lower.endswith('\\assets') or path_lower.endswith('/assets'):
            # Just Assets folder
            return str(PROJECT_ROOT / 'Assets')
    
    # Check if it's already in the current project format
    current_project_lower = str(PROJECT_ROOT).lower()
    if current_project_lower in path_lower:
        # Already in current project, but might need case normalization
        # For now, return as-is since it's already correct
        return file_path
    
    # If it doesn't match any known format, return as-is
    return file_path

def fetch_all_file_paths(client) -> List[Dict[str, Any]]:
    """Fetch all unique file paths from code_chunks table"""
    print("Fetching all file paths from code_chunks...")
    
    try:
        # Get all unique file paths
        result = client.table('code_chunks').select('file_path').execute()
        
        if not result.data:
            print("   No chunks found")
            return []
        
        # Get unique paths
        unique_paths = {}
        for row in result.data:
            path = row.get('file_path')
            if path:
                unique_paths[path] = True
        
        paths = list(unique_paths.keys())
        print(f"   Found {len(paths)} unique file paths")
        return [{'file_path': p} for p in paths]
        
    except Exception as e:
        print(f"   [ERROR] Error fetching paths: {e}")
        import traceback
        traceback.print_exc()
        return []

def analyze_paths(paths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze paths and identify what needs fixing"""
    print("\n" + "=" * 80)
    print("Analyzing file paths...")
    print("=" * 80)
    
    analysis = {
        'total': len(paths),
        'old_format': [],
        'current_format': [],
        'other': [],
        'needs_fixing': []
    }
    
    current_project_root = str(PROJECT_ROOT).lower()
    
    for path_data in paths:
        file_path = path_data['file_path']
        path_lower = file_path.lower()
        
        # Check if it's old format (gdd_rag_gradio)
        if 'gdd_rag_gradio' in path_lower:
            analysis['old_format'].append(file_path)
            new_path = normalize_path_to_current_project(file_path)
            analysis['needs_fixing'].append({
                'old_path': file_path,
                'new_path': new_path
            })
        # Check if it's relative Assets/... format
        elif file_path.startswith('Assets/') or file_path.startswith('Assets\\'):
            analysis['old_format'].append(file_path)  # Also needs fixing to full path
            new_path = normalize_path_to_current_project(file_path)
            analysis['needs_fixing'].append({
                'old_path': file_path,
                'new_path': new_path
            })
        # Check if it's already in current project format (full Windows path)
        elif current_project_root in path_lower and 'unified_rag_app' in path_lower:
            analysis['current_format'].append(file_path)
        else:
            analysis['other'].append(file_path)
    
    return analysis

def print_analysis(analysis: Dict[str, Any]):
    """Print the analysis results"""
    print(f"\nPath Analysis Results:")
    print(f"   Total paths: {analysis['total']}")
    print(f"   Old format (needs fixing): {len(analysis['old_format'])}")
    print(f"   Current format (OK): {len(analysis['current_format'])}")
    print(f"   Other format: {len(analysis['other'])}")
    
    if analysis['old_format']:
        print(f"\n[!] Found {len(analysis['old_format'])} paths with old format:")
        for i, old_path in enumerate(analysis['old_format'][:10], 1):  # Show first 10
            print(f"   {i}. {old_path}")
        if len(analysis['old_format']) > 10:
            print(f"   ... and {len(analysis['old_format']) - 10} more")
    
    if analysis['other']:
        print(f"\n[?] Found {len(analysis['other'])} paths with unexpected format:")
        for i, other_path in enumerate(analysis['other'][:5], 1):  # Show first 5
            print(f"   {i}. {other_path}")
        if len(analysis['other']) > 5:
            print(f"   ... and {len(analysis['other']) - 5} more")

def fix_paths(client, fixes: List[Dict[str, str]], dry_run: bool = True):
    """Update file paths in Supabase"""
    if not fixes:
        print("\n[OK] No paths need fixing!")
        return
    
    print(f"\n{'[DRY RUN]' if dry_run else '[FIXING]'} Preparing to update {len(fixes)} file paths...")
    
    if dry_run:
        print("\nWould update the following paths:")
        for i, fix in enumerate(fixes[:20], 1):  # Show first 20
            print(f"\n   {i}. OLD: {fix['old_path']}")
            print(f"      NEW: {fix['new_path']}")
        if len(fixes) > 20:
            print(f"\n   ... and {len(fixes) - 20} more")
        print("\n[!] This is a DRY RUN. No changes were made.")
        print("   Run with --apply to actually update the paths.")
        return
    
    # Actually update the paths
    print("\n[FIXING] Updating paths in Supabase...")
    print("   Processing in batches of 10 to avoid network issues...")
    
    updated_chunks = 0
    updated_files = 0
    failed = []
    batch_size = 10
    
    try:
        # Process each path: update code_files first, then code_chunks (due to foreign key)
        print("   Processing paths (updating code_files then code_chunks for each)...")
        for i, fix in enumerate(fixes, 1):
            old_path = fix['old_path']
            new_path = fix['new_path']
            
            try:
                # Step 1: Ensure code_files has the new path (create if needed)
                check_new = client.table('code_files').select('file_path').eq('file_path', new_path).execute()
                
                if not check_new.data:
                    # New path doesn't exist - create it
                    # Check if old path exists (to get metadata)
                    check_old = client.table('code_files').select('*').eq('file_path', old_path).execute()
                    
                    if check_old.data:
                        # Use metadata from old entry
                        old_entry = check_old.data[0]
                        new_entry = {
                            'file_path': new_path,
                            'file_name': old_entry.get('file_name', Path(new_path).name),
                            'normalized_path': new_path
                        }
                        # Copy other fields if they exist
                        for key in ['file_type', 'language', 'metadata']:
                            if key in old_entry:
                                new_entry[key] = old_entry[key]
                    else:
                        # No old entry - create minimal entry
                        new_entry = {
                            'file_path': new_path,
                            'file_name': Path(new_path).name,
                            'normalized_path': new_path
                        }
                    
                    file_result = client.table('code_files').insert(new_entry).execute()
                    if file_result.data:
                        updated_files += 1
                
                # Step 2: Update code_chunks to point to new_path
                # This is safe because we've already ensured new_path exists in code_files
                chunk_result = client.table('code_chunks').update({
                    'file_path': new_path
                }).eq('file_path', old_path).execute()
                
                if chunk_result.data:
                    updated_chunks += len(chunk_result.data)
                
                # Note: We leave the old_path entry in code_files as-is
                # It won't cause issues since all chunks now point to new_path
                # We can clean up old entries later if needed
                
                # Progress indicator
                if i % batch_size == 0:
                    print(f"      Processed {i}/{len(fixes)} paths... ({updated_files} files, {updated_chunks} chunks updated)")
                    time.sleep(0.5)  # Small delay to avoid overwhelming the API
                
            except Exception as e:
                error_msg = str(e)
                print(f"      [!] Failed to update {old_path}: {error_msg[:100]}")
                failed.append({'old_path': old_path, 'new_path': new_path, 'error': error_msg})
                # Continue with next path
        
        print(f"\n[OK] Update complete!")
        print(f"   Updated {updated_chunks} chunks in code_chunks table")
        print(f"   Updated {updated_files} entries in code_files table")
        
        if failed:
            print(f"\n[!] {len(failed)} paths failed to update:")
            for fail in failed[:10]:
                print(f"      - {fail['old_path']}")
            if len(failed) > 10:
                print(f"      ... and {len(failed) - 10} more")
        
    except Exception as e:
        print(f"\n[ERROR] Error updating paths: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("=" * 80)
    print("File Path Checker and Fixer")
    print("=" * 80)
    
    # Check if --apply flag is provided
    dry_run = '--apply' not in sys.argv
    
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Fetch all paths
        paths = fetch_all_file_paths(client)
        
        if not paths:
            print("\n[!] No file paths found in Supabase")
            return
        
        # Analyze paths
        analysis = analyze_paths(paths)
        print_analysis(analysis)
        
        # Fix paths if needed
        if analysis['needs_fixing']:
            fix_paths(client, analysis['needs_fixing'], dry_run=dry_run)
        else:
            print("\n[OK] All paths are in the correct format!")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


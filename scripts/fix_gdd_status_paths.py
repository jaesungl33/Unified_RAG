#!/usr/bin/env python3
"""
Script to fix file paths in gdd_data/summarised_chunks/kv_store_doc_status.json

Updates old paths pointing to GDD_RAG_Gradio/rag_storage_md/ to point to
the new unified_rag_app/gdd_data/chunks/ location.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
STATUS_FILE = PROJECT_ROOT / "gdd_data" / "summarised_chunks" / "kv_store_doc_status.json"


def fix_status_paths():
    """Fix file paths in the status JSON file."""
    if not STATUS_FILE.exists():
        print(f"[ERROR] Status file not found: {STATUS_FILE}")
        return False
    
    print(f"Reading status file: {STATUS_FILE}")
    with open(STATUS_FILE, 'r', encoding='utf-8') as f:
        status_data = json.load(f)
    
    updated_count = 0
    for doc_id, doc_info in status_data.items():
        old_path = doc_info.get("file_path", "")
        if not old_path:
            continue
        
        # Check if path needs updating
        if "rag_storage_md" in old_path or "GDD_RAG_Gradio" in old_path:
            # Construct new path
            new_path = str(PROJECT_ROOT / "gdd_data" / "chunks" / doc_id / f"{doc_id}_chunks.json")
            doc_info["file_path"] = new_path
            updated_count += 1
            try:
                print(f"  [OK] Updated {doc_id}")
                print(f"    Old: {old_path[:80]}...")
                print(f"    New: {new_path}")
            except UnicodeEncodeError:
                # Handle encoding errors for special characters
                print(f"  [OK] Updated document (ID contains special characters)")
                print(f"    Old path updated")
                print(f"    New path: {new_path[:80]}...")
    
    if updated_count > 0:
        # Backup original file
        backup_file = STATUS_FILE.with_suffix('.json.backup')
        print(f"\nCreating backup: {backup_file}")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        
        # Write updated data
        print(f"Writing updated status file...")
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SUCCESS] Updated {updated_count} file paths")
        return True
    else:
        print("\n[OK] No paths needed updating")
        return True


if __name__ == "__main__":
    print("=" * 70)
    print("FIX GDD STATUS FILE PATHS")
    print("=" * 70)
    print()
    
    success = fix_status_paths()
    
    print()
    print("=" * 70)
    if success:
        print("[SUCCESS] COMPLETE")
    else:
        print("[ERROR] FAILED")
    print("=" * 70)

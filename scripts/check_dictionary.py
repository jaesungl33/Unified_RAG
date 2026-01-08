#!/usr/bin/env python3
"""
Diagnostic script to check dictionary contents and status.

Usage:
    python scripts/check_dictionary.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client

def main():
    client = get_supabase_client()
    
    print("=" * 70)
    print("Dictionary Diagnostic Check")
    print("=" * 70)
    
    # Check components
    print("\n📦 Components:")
    comps = client.table("dictionary_components").select("*").execute().data or []
    print(f"  Total components: {len(comps)}")
    
    if comps:
        print(f"\n  First 10 components:")
        for i, c in enumerate(comps[:10], 1):
            has_emb = "✅" if c.get("embedding") else "❌"
            aliases_count = len(c.get("aliases_vi", []))
            comp_type = c.get("component_type", "NULL")
            print(f"    {i}. {has_emb} [{comp_type}] {c.get('component_key')}: {c.get('display_name_vi')}")
            print(f"       Aliases: {aliases_count}")
            if aliases_count > 0:
                print(f"       {c.get('aliases_vi', [])[:3]}")
    else:
        print("  ⚠️  No components found!")
    
    # Check references
    print("\n📚 References:")
    refs = client.table("dictionary_references").select("component_key, reference_role, doc_id").limit(100).execute().data or []
    print(f"  Sample references (first 100): {len(refs)}")
    
    if refs:
        role_counts = {}
        for r in refs:
            role = r.get("reference_role", "NULL")
            role_counts[role] = role_counts.get(role, 0) + 1
        print(f"  Reference roles distribution:")
        for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
            print(f"    {role}: {count}")
        
        # Show unique component keys
        comp_keys = set(r.get("component_key") for r in refs)
        print(f"\n  Unique component keys in sample: {len(comp_keys)}")
        print(f"  Examples: {list(comp_keys)[:5]}")
    else:
        print("  ⚠️  No references found!")
    
    # Check for components without references
    if comps:
        comp_keys_with_refs = set(r.get("component_key") for r in refs)
        comp_keys_all = set(c.get("component_key") for c in comps)
        orphaned = comp_keys_all - comp_keys_with_refs
        if orphaned:
            print(f"\n  ⚠️  Components without references: {len(orphaned)}")
            print(f"  Examples: {list(orphaned)[:5]}")
    
    # Check embeddings
    if comps:
        with_emb = sum(1 for c in comps if c.get("embedding"))
        without_emb = len(comps) - with_emb
        print(f"\n🔢 Embeddings:")
        print(f"  Components with embeddings: {with_emb}/{len(comps)}")
        if without_emb > 0:
            print(f"  ⚠️  Components without embeddings: {without_emb}")
            print(f"  (Embeddings will be computed on first query)")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""
Validate dictionary role fields after migration.

This script checks:
1. All components have component_type set (no NULLs)
2. All references have reference_role set (no NULLs)
3. component_type values are valid (COMPONENT or GLOBAL_UI)
4. reference_role values are valid (CORE, UI, GLOBAL_UI, META)
5. GLOBAL_UI components have appropriate references
6. Reference roles match component types where applicable

Usage:
    python scripts/validate_dictionary_roles.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client

def test_connection_and_tables():
    """Test Supabase connection and try to list tables."""
    client = get_supabase_client()
    print("\n" + "=" * 70)
    print("Connection Diagnostics")
    print("=" * 70)
    
    # Try to query dictionary_components directly
    print("\nTesting dictionary_components table...")
    try:
        res = client.table("dictionary_components").select("component_key").limit(1).execute()
        print(f"✅ dictionary_components table exists and is accessible")
        print(f"   Found {len(res.data or [])} row(s) in sample query")
        components_ok = True
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error accessing dictionary_components: {error_msg}")
        components_ok = False
    
    # Try to query dictionary_references directly
    print("\nTesting dictionary_references table...")
    try:
        res = client.table("dictionary_references").select("id").limit(1).execute()
        print(f"✅ dictionary_references table exists and is accessible")
        print(f"   Found {len(res.data or [])} row(s) in sample query")
        references_ok = True
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error accessing dictionary_references: {error_msg}")
        references_ok = False
    
    return components_ok and references_ok

def check_table_exists(client, table_name):
    """Check if a table exists by trying to query it."""
    try:
        # Try a simple select with limit 0 (doesn't fetch data, just checks table exists)
        # Use a wildcard select which works for any table structure
        res = client.table(table_name).select("*").limit(0).execute()
        return True
    except Exception as e:
        error_msg = str(e).lower()
        # Check for common "table doesn't exist" error patterns
        if any(phrase in error_msg for phrase in [
            "does not exist", 
            "relation", 
            "no such table",
            "table",
            "relation \"public." + table_name.lower() + "\" does not exist"
        ]):
            # Print the actual error for debugging
            print(f"   Debug: Error checking table '{table_name}': {error_msg}")
            return False
        # Other errors might be permissions or other issues, but table might exist
        print(f"   Debug: Unexpected error checking table '{table_name}': {error_msg}")
        return True

def validate_components():
    """Validate dictionary_components table."""
    client = get_supabase_client()
    print("\n" + "=" * 70)
    print("Validating dictionary_components")
    print("=" * 70)
    
    # Try to query the table directly
    try:
        res = client.table("dictionary_components").select("*").execute()
        components = res.data or []
    except Exception as e:
        error_msg = str(e).lower()
        if any(phrase in error_msg for phrase in ["does not exist", "relation", "no such table"]):
            print("❌ Table 'dictionary_components' does not exist")
            print(f"   Error: {e}")
            print("   Run the migration script first: deploy/populate_dictionary_role_fields.sql")
            return False
        else:
            print(f"❌ Error querying dictionary_components: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    if not components:
        print("ℹ️  No components found in database (table is empty)")
        print("   This is OK if you haven't built the dictionary yet.")
        print("   Run dictionary builder to populate: gdd_dictionary/dictionary_builder.py")
        return True  # Empty table is valid, nothing to validate
    
    print(f"✅ Found {len(components)} components")
    
    # Check for NULL component_type
    null_type = [c for c in components if not c.get("component_type")]
    if null_type:
        print(f"❌ Found {len(null_type)} components with NULL component_type:")
        for c in null_type[:5]:  # Show first 5
            print(f"   - {c.get('component_key', 'unknown')}")
        if len(null_type) > 5:
            print(f"   ... and {len(null_type) - 5} more")
        return False
    else:
        print("✅ All components have component_type set")
    
    # Check for invalid component_type values
    valid_types = {"COMPONENT", "GLOBAL_UI"}
    invalid_type = [c for c in components if c.get("component_type") not in valid_types]
    if invalid_type:
        print(f"❌ Found {len(invalid_type)} components with invalid component_type:")
        for c in invalid_type[:5]:
            print(f"   - {c.get('component_key')}: {c.get('component_type')}")
        return False
    else:
        print("✅ All component_type values are valid")
    
    # Show distribution
    type_counts = {}
    for c in components:
        ctype = c.get("component_type", "NULL")
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    print("\n📊 Component type distribution:")
    for ctype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = 100.0 * count / len(components)
        print(f"   {ctype}: {count} ({pct:.1f}%)")
    
    return True

def validate_references():
    """Validate dictionary_references table."""
    client = get_supabase_client()
    print("\n" + "=" * 70)
    print("Validating dictionary_references")
    print("=" * 70)
    
    # Try to query the table directly
    try:
        res = client.table("dictionary_references").select("*").execute()
        references = res.data or []
    except Exception as e:
        error_msg = str(e).lower()
        if any(phrase in error_msg for phrase in ["does not exist", "relation", "no such table"]):
            print("❌ Table 'dictionary_references' does not exist")
            print(f"   Error: {e}")
            print("   Run the migration script first: deploy/populate_dictionary_role_fields.sql")
            return False
        else:
            print(f"❌ Error querying dictionary_references: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    if not references:
        print("ℹ️  No references found in database (table is empty)")
        print("   This is OK if you haven't built the dictionary yet.")
        print("   Run dictionary builder to populate: gdd_dictionary/dictionary_builder.py")
        return True  # Empty table is valid, nothing to validate
    
    print(f"✅ Found {len(references)} references")
    
    # Check for NULL reference_role
    null_role = [r for r in references if not r.get("reference_role")]
    if null_role:
        print(f"❌ Found {len(null_role)} references with NULL reference_role:")
        for r in null_role[:5]:
            print(f"   - component_key: {r.get('component_key')}, doc_id: {r.get('doc_id')}")
        if len(null_role) > 5:
            print(f"   ... and {len(null_role) - 5} more")
        return False
    else:
        print("✅ All references have reference_role set")
    
    # Check for invalid reference_role values
    valid_roles = {"CORE", "UI", "GLOBAL_UI", "META"}
    invalid_role = [r for r in references if r.get("reference_role") not in valid_roles]
    if invalid_role:
        print(f"❌ Found {len(invalid_role)} references with invalid reference_role:")
        for r in invalid_role[:5]:
            print(f"   - component_key: {r.get('component_key')}, role: {r.get('reference_role')}")
        return False
    else:
        print("✅ All reference_role values are valid")
    
    # Show distribution
    role_counts = {}
    for r in references:
        role = r.get("reference_role", "NULL")
        role_counts[role] = role_counts.get(role, 0) + 1
    
    print("\n📊 Reference role distribution:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        pct = 100.0 * count / len(references)
        print(f"   {role}: {count} ({pct:.1f}%)")
    
    return True

def validate_cross_references():
    """Validate relationships between components and references."""
    client = get_supabase_client()
    print("\n" + "=" * 70)
    print("Validating component-reference relationships")
    print("=" * 70)
    
    # Check if tables have data
    try:
        comp_count = client.table("dictionary_components").select("component_key", count="exact").limit(1).execute().count
        ref_count = client.table("dictionary_references").select("id", count="exact").limit(1).execute().count
    except Exception as e:
        print(f"❌ Error checking table counts: {e}")
        return False
    
    if comp_count == 0 or ref_count == 0:
        print("ℹ️  Skipping cross-reference validation (tables are empty)")
        return True
    
    # Get GLOBAL_UI components
    try:
        comp_res = client.table("dictionary_components").select("component_key, component_type").eq("component_type", "GLOBAL_UI").execute()
        global_ui_components = {c["component_key"] for c in (comp_res.data or [])}
    except Exception as e:
        print(f"❌ Error querying GLOBAL_UI components: {e}")
        return False
    
    if global_ui_components:
        print(f"✅ Found {len(global_ui_components)} GLOBAL_UI components")
    
    # Get references for GLOBAL_UI components
    if global_ui_components:
        try:
            ref_res = client.table("dictionary_references").select("component_key, reference_role").in_("component_key", list(global_ui_components)).execute()
            global_ui_refs = ref_res.data or []
            
            # Check if GLOBAL_UI components have GLOBAL_UI references
            wrong_role = [r for r in global_ui_refs if r.get("reference_role") != "GLOBAL_UI"]
            if wrong_role:
                print(f"⚠️  Found {len(wrong_role)} references for GLOBAL_UI components with non-GLOBAL_UI role:")
                for r in wrong_role[:5]:
                    print(f"   - component_key: {r.get('component_key')}, role: {r.get('reference_role')}")
            else:
                if global_ui_refs:
                    print("✅ All references for GLOBAL_UI components have GLOBAL_UI role")
        except Exception as e:
            print(f"⚠️  Error checking GLOBAL_UI component references: {e}")
    
    # Check for GLOBAL_UI references pointing to non-GLOBAL_UI components
    try:
        ref_res = client.table("dictionary_references").select("component_key, reference_role").eq("reference_role", "GLOBAL_UI").execute()
        global_ui_refs = ref_res.data or []
        
        if global_ui_refs:
            ref_component_keys = {r["component_key"] for r in global_ui_refs}
            comp_res = client.table("dictionary_components").select("component_key, component_type").in_("component_key", list(ref_component_keys)).execute()
            components = {c["component_key"]: c.get("component_type") for c in (comp_res.data or [])}
            
            mismatched = [k for k in ref_component_keys if components.get(k) != "GLOBAL_UI"]
            if mismatched:
                print(f"⚠️  Found {len(mismatched)} GLOBAL_UI references pointing to non-GLOBAL_UI components:")
                for k in mismatched[:5]:
                    print(f"   - component_key: {k}, component_type: {components.get(k, 'NOT_FOUND')}")
            else:
                print("✅ All GLOBAL_UI references point to GLOBAL_UI components")
    except Exception as e:
        print(f"⚠️  Error checking GLOBAL_UI reference-component matching: {e}")
    
    return True

def main():
    """Run all validations."""
    print("=" * 70)
    print("Dictionary Role Fields Validation")
    print("=" * 70)
    
    # Run diagnostics first
    test_connection_and_tables()
    
    results = []
    
    try:
        results.append(("Components", validate_components()))
    except Exception as e:
        print(f"❌ Error validating components: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Components", False))
    
    try:
        results.append(("References", validate_references()))
    except Exception as e:
        print(f"❌ Error validating references: {e}")
        results.append(("References", False))
    
    try:
        results.append(("Cross-references", validate_cross_references()))
    except Exception as e:
        print(f"❌ Error validating cross-references: {e}")
        results.append(("Cross-references", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All validations passed!")
        return 0
    else:
        print("\n⚠️  Some validations failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


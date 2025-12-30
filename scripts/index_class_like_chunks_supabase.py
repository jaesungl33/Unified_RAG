"""
Index class-like chunks (class, struct, interface, enum) to Supabase.

This script fully integrates the code_qa logic into Supabase:
1. Scans Assets folder for .cs files
2. Checks if class-like chunks already exist (skips if they do)
3. Parses class/struct/interface/enum using regex (matching code_qa behavior)
4. Extracts full source code for each type
5. Uses the same embedding/indexing infrastructure as method chunks
6. Ensures path normalization matches method chunks

Usage:
    cd unified_rag_app
    python -m scripts.index_class_like_chunks_supabase
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client
from backend.storage.code_supabase_storage import (
    index_code_chunks_to_supabase,
    normalize_path_consistent,
)
from gdd_rag_backbone.llm_providers import QwenProvider
from backend.code_service import _analyze_csharp_file_symbols


# Pattern to find all type declarations (class, struct, interface, enum)
TYPE_DECL_PATTERN = re.compile(
    r'(?:^|\n)\s*'
    r'(?:\[[^\]]+\]\s*)*'                          # Optional attributes
    r'(?:(?:public|private|protected|internal|abstract|sealed|static|partial)\s+)*'  # Optional modifiers
    r'(?P<kind>class|struct|interface|enum)\s+'    # Type kind
    r'(?P<name>\w+)'                                # Type name
    r'(?:[^{;]*)?',                                # Optional inheritance/constraints (up to { or ;)
    re.MULTILINE | re.IGNORECASE
)


def find_type_declarations(code_text: str) -> List[Dict[str, Any]]:
    """
    Find all type declarations (class, struct, interface, enum) in C# code.
    Returns list of dicts with 'kind', 'name', 'start', 'end' positions.
    """
    types = []
    
    for match in TYPE_DECL_PATTERN.finditer(code_text):
        kind = match.group("kind").lower()
        name = match.group("name")
        start_pos = match.start()
        
        # Verify this is actually at the start of a line (not in the middle of code)
        # Check what's before the match
        if start_pos > 0:
            char_before = code_text[start_pos - 1]
            # Should be newline, semicolon, closing brace, or opening brace (for nested types)
            if char_before not in ['\n', ';', '}', '{', ' ', '\t']:
                # Not at a valid position, skip (might be inside a string or method)
                continue
        
        # Find the opening brace (or semicolon for enum without body)
        # Look for '{' after the type name
        search_start = match.end()
        brace_pos = code_text.find("{", search_start)
        semicolon_pos = code_text.find(";", search_start)
        
        # Handle enum without body: enum MyEnum; or enum MyEnum { ... }
        if kind == "enum":
            if semicolon_pos != -1 and (brace_pos == -1 or semicolon_pos < brace_pos):
                # Enum without body
                end_pos = semicolon_pos + 1
                types.append({
                    "kind": kind,
                    "name": name,
                    "start": start_pos,
                    "end": end_pos,
                    "is_partial": "partial" in match.group(0).lower(),
                })
                continue
        
        # For types with body, find matching closing brace
        if brace_pos == -1:
            # No opening brace found, skip this type
            continue
        
        # Find matching closing brace
        brace_count = 1
        pos = brace_pos + 1
        
        while pos < len(code_text) and brace_count > 0:
            char = code_text[pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '"' or char == "'":
                # Skip string literals
                quote_char = char
                pos += 1
                while pos < len(code_text) and code_text[pos] != quote_char:
                    if code_text[pos] == '\\':
                        pos += 1  # Skip escaped character
                    pos += 1
            pos += 1
        
        if brace_count == 0:
            end_pos = pos
            types.append({
                "kind": kind,
                "name": name,
                "start": start_pos,
                "end": end_pos,
                "is_partial": "partial" in match.group(0).lower(),
            })
    
    return types


def extract_methods_in_type(code_text: str, type_start: int, type_end: int, 
                           all_methods: List[Dict[str, Any]]) -> List[str]:
    """
    Extract method declarations that belong to a specific type.
    Methods are considered to belong to a type if they appear within the type's span.
    """
    method_declarations = []
    
    for method in all_methods:
        # Get method position from signature (approximate)
        # We'll search for the method signature in the type's span
        method_sig = method.get("signature", "")
        if not method_sig:
            continue
        
        # Find method signature within type span
        type_section = code_text[type_start:type_end]
        if method_sig.strip() in type_section:
            method_declarations.append(method_sig.strip())
    
    return method_declarations


def has_class_like_chunks(client, file_path: str) -> bool:
    """
    Check if this file already has any class-like chunks in Supabase.
    Returns True if any class/struct/interface/enum chunks exist.
    """
    try:
        result = (
            client.table("code_chunks")
            .select("id")
            .eq("file_path", file_path)
            .in_("chunk_type", ["class", "struct", "interface", "enum"])
            .limit(1)
            .execute()
        )
        return bool(result.data and len(result.data) > 0)
    except Exception as e:
        print(f"   ⚠️  Error checking for existing chunks: {e}")
        return False


def get_files_with_method_chunks(client) -> set:
    """
    Get all file paths that have method chunks in Supabase.
    Returns a set of file paths as stored in the database (typically full Windows paths).
    """
    try:
        # Get all unique file_paths that have method chunks
        result = (
            client.table("code_chunks")
            .select("file_path")
            .eq("chunk_type", "method")
            .execute()
        )
        
        if not result.data:
            return set()
        
        # Extract unique file paths - keep them as-is to match database format
        file_paths = set()
        for row in result.data:
            file_path = row.get("file_path", "")
            if file_path:
                # Keep the path as-is (typically Windows format like c:\users\...)
                file_paths.add(file_path)
        
        print(f"   Sample Supabase paths (first 5):")
        for i, path in enumerate(list(file_paths)[:5], 1):
            print(f"      {i}. {path}")
        
        return file_paths
    except Exception as e:
        print(f"   ⚠️  Error getting files with method chunks: {e}")
        import traceback
        traceback.print_exc()
        return set()


def matches_supabase_path(local_path: str, supabase_paths: set) -> bool:
    """
    Check if a local file path matches any path in the Supabase set.
    Uses case-insensitive matching since paths may differ in format.
    """
    local_path_lower = local_path.lower()
    local_filename = Path(local_path).name.lower()
    
    # Check for direct match (case-insensitive)
    for s_path in supabase_paths:
        if s_path.lower() == local_path_lower:
            return True
    
    # Try matching by filename if direct match fails
    for s_path in supabase_paths:
        s_filename = Path(s_path).name.lower()
        if s_filename == local_filename:
            return True
    
    return False


def build_class_like_chunks(
    code_text: str,
    file_path: str,
    file_name: str
) -> List[Dict[str, Any]]:
    """
    Build chunk dictionaries for all type declarations in the file.
    Matches the structure expected by index_code_chunks_to_supabase.
    """
    # Find all type declarations
    types = find_type_declarations(code_text)
    
    if not types:
        return []
    
    # Analyze file for methods, fields, properties (for metadata)
    methods, fields, properties = _analyze_csharp_file_symbols(code_text)
    
    chunks = []
    
    for type_info in types:
        kind = type_info["kind"]
        name = type_info["name"]
        start = type_info["start"]
        end = type_info["end"]
        is_partial = type_info.get("is_partial", False)
        
        # Extract full source code for this type
        source_code = code_text[start:end]
        
        # Extract method declarations within this type
        method_decls = extract_methods_in_type(code_text, start, end, methods)
        method_declarations_str = "\n-----\n".join(method_decls) if method_decls else ""
        
        # Format source code similar to code_qa style
        # This matches the format used in create_tables.py:
        # "File: {file_path}\n\nClass: {class_name}\n\nSource Code:\n{source_code}\n\n"
        formatted_source = (
            f"File: {file_path}\n\n"
            f"{kind.capitalize()}: {name}\n\n"
            f"Source Code:\n{source_code}\n\n"
        )
        
        # Build chunk dictionary matching Supabase schema
        chunk = {
            "chunk_type": kind,  # "class", "struct", "interface", "enum"
            "class_name": name,
            "method_name": None,  # Always None for class-like chunks
            "source_code": formatted_source,  # Formatted like code_qa
            "code": None,  # Always None for class-like chunks
            "doc_comment": None,  # Could extract if needed
            "constructor_declaration": "",  # Could extract if needed
            "method_declarations": method_declarations_str,
            "references": "",  # Could populate with reference finding logic
            "metadata": {
                "indexed_from": "class_chunk_supabase",
                "kind": kind,
                "is_partial": is_partial,
                "file_name": file_name,
            }
        }
        
        chunks.append(chunk)
    
    return chunks


def walk_cs_files(root: Path) -> List[Path]:
    """Recursively find all .cs files under root directory."""
    cs_files = []
    for path in root.rglob("*.cs"):
        if path.is_file():
            cs_files.append(path)
    return sorted(cs_files)


def main():
    """Main indexing function."""
    print("=" * 80)
    print("🔄 Index Class-Like Chunks to Supabase")
    print("=" * 80)
    print("\nThis script will:")
    print("  1. Scan Assets folder for .cs files")
    print("  2. Skip files that already have class-like chunks")
    print("  3. Parse class/struct/interface/enum declarations")
    print("  4. Extract full source code for each type")
    print("  5. Embed and index to Supabase")
    print()
    
    # Check for command-line argument
    if len(sys.argv) > 1:
        assets_root = Path(sys.argv[1]).resolve()
        if not assets_root.exists():
            print(f"❌ Error: Provided path does not exist: {assets_root}")
            return
    else:
        # Determine Assets folder path automatically
        # Try multiple possible locations
        possible_paths = [
            PROJECT_ROOT / "Assets",  # Relative to unified_rag_app
            Path("Assets"),  # Current directory
            Path("../Assets"),  # Parent directory
            Path("C:/Users/CPU12391/Desktop/GDD_RAG_Gradio/codebase_RAG/tank_online_1-dev/Assets"),  # Absolute path
            Path("C:/Users/CPU12391/Desktop/unified_rag_app/Assets"),  # Alternative absolute path
        ]
        
        assets_root = None
        for path in possible_paths:
            if path.exists() and path.is_dir():
                assets_root = path.resolve()
                break
        
        if not assets_root:
            print("❌ Error: Assets folder not found!")
            print("\nTried the following paths:")
            for path in possible_paths:
                print(f"   - {path}")
            print("\nPlease provide the Assets folder path as an argument:")
            print("   python -m scripts.index_class_like_chunks_supabase <path_to_Assets>")
            return
    
    print(f"📁 Scanning: {assets_root}")
    
    # Find all .cs files
    cs_files = walk_cs_files(assets_root)
    
    if not cs_files:
        print("⚠️  No .cs files found in Assets folder!")
        return
    
    print(f"✅ Found {len(cs_files)} .cs file(s)")
    print(f"\nFirst 10 files:")
    for i, path in enumerate(cs_files[:10], 1):
        print(f"  {i}. {path.relative_to(assets_root)}")
    if len(cs_files) > 10:
        print(f"  ... and {len(cs_files) - 10} more")
    
    # Confirm
    print(f"\n⚠️  This will index class-like chunks for {len(cs_files)} files")
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Indexing cancelled")
        return
    
    # Initialize Supabase client and provider
    try:
        client = get_supabase_client()
        provider = QwenProvider()
    except Exception as e:
        print(f"❌ Error initializing Supabase or provider: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Get all files that have method chunks in Supabase
    print(f"\n📊 Loading list of files with method chunks from Supabase...")
    files_with_methods = get_files_with_method_chunks(client)
    print(f"✅ Found {len(files_with_methods)} files with method chunks in Supabase")
    
    if not files_with_methods:
        print("⚠️  No files with method chunks found in Supabase!")
        print("   Make sure method chunks are indexed first.")
        return
    
    # Process each file
    print(f"\n🔄 Starting indexing...")
    total_indexed = 0
    total_chunks = 0
    skipped = 0
    failed = 0
    
    for idx, cs_file in enumerate(cs_files, 1):
        print(f"\n[{idx}/{len(cs_files)}] 📄 Processing: {cs_file.name}")
        print(f"   Path: {cs_file}")
        
        # Use full local path for matching
        local_path_str = str(cs_file)
        
        # Check if this file has method chunks (using full path matching)
        if not matches_supabase_path(local_path_str, files_with_methods):
            print(f"   ⏭️  Skipped (no method chunks found in Supabase)")
            skipped += 1
            continue
        
        # Use full Windows path to match old indexed chunks format
        # Don't normalize - keep the full path as it matches existing method chunks
        raw_path = str(cs_file)
        # Keep the full Windows path format (e.g., c:\users\...\assets\...)
        # This matches the format used by old indexed chunks from LanceDB migration
        normalized_path = raw_path
        
        # Check if class-like chunks already exist
        if has_class_like_chunks(client, normalized_path):
            print(f"   ✅ Skipped (class-like chunks already exist in Supabase)")
            skipped += 1
            continue
        
        # Read file
        try:
            code_text = cs_file.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"   ❌ Failed to read file: {e}")
            failed += 1
            continue
        
        # Build chunks
        try:
            chunks = build_class_like_chunks(code_text, normalized_path, cs_file.name)
        except Exception as e:
            print(f"   ❌ Error parsing file: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            continue
        
        if not chunks:
            print(f"   ⚠️  No class/struct/interface/enum found, skipping")
            skipped += 1
            continue
        
        # Log what we found
        print(f"   🔍 Found {len(chunks)} type declaration(s):")
        for chunk in chunks:
            kind = chunk["chunk_type"]
            name = chunk["class_name"]
            is_partial = chunk.get("metadata", {}).get("is_partial", False)
            partial_str = " (partial)" if is_partial else ""
            print(f"      - {kind} {name}{partial_str}")
        
        # Index to Supabase
        try:
            success = index_code_chunks_to_supabase(
                file_path=normalized_path,
                file_name=cs_file.name,
                chunks=chunks,
                provider=provider,
            )
            
            if success:
                print(f"   ✅ Indexed {len(chunks)} class-like chunk(s) to Supabase")
                total_indexed += 1
                total_chunks += len(chunks)
            else:
                print(f"   ❌ Indexing failed")
                failed += 1
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Error indexing to Supabase: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            
            # Check if this is an enum constraint error - stop immediately
            if 'enum' in error_msg.lower() and ('constraint' in error_msg.lower() or '23514' in error_msg):
                print("\n" + "=" * 80)
                print("🛑 STOPPING: Enum constraint error detected!")
                print("=" * 80)
                print(f"\nFile: {cs_file}")
                print(f"Error: {error_msg}")
                print("\nThis indicates the database constraint still doesn't allow 'enum' chunks.")
                print("Please verify the constraint was updated correctly in Supabase.")
                sys.exit(1)
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ Indexing Complete!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Files scanned: {len(cs_files)}")
    print(f"   Files indexed: {total_indexed}")
    print(f"   Files skipped: {skipped}")
    print(f"   Files failed: {failed}")
    print(f"   Total chunks indexed: {total_chunks}")
    print(f"\n💡 Next steps:")
    print(f"   1. Run check_supabase_code_files_retrieval.py to verify")
    print(f"   2. Test 'list all variables' queries to ensure global variables work")
    print(f"   3. Test class-focused queries to verify class chunks are retrieved")


if __name__ == "__main__":
    main()


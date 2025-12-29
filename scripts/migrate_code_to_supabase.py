"""
Migration script: Move Code Q&A data from LanceDB to Supabase

This script:
1. Connects to LanceDB database
2. Finds all method and class tables
3. Reads all chunks with embeddings
4. Migrates to Supabase code_chunks and code_files tables
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add parent directory to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PARENT_ROOT) not in sys.path:
    sys.path.insert(0, str(PARENT_ROOT))

# Add code_qa directory for imports
CODE_QA_ROOT = PARENT_ROOT / "codebase_RAG" / "code_qa"
if str(CODE_QA_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_QA_ROOT))

try:
    import lancedb
    from dotenv import load_dotenv
    from backend.storage.supabase_client import (
        get_supabase_client,
        insert_code_file,
        insert_code_chunks,
    )
    from backend.storage.code_supabase_storage import normalize_path_consistent
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("  pip install lancedb python-dotenv supabase")
    sys.exit(1)

load_dotenv()

# Check Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    print("   Please set them in your .env file or environment")
    sys.exit(1)

# LanceDB database path
LANCE_DB_PATH = CODE_QA_ROOT / "database"
if not LANCE_DB_PATH.exists():
    # Try alternative path
    LANCE_DB_PATH = Path("../database")
    if not LANCE_DB_PATH.exists():
        print(f"❌ Error: LanceDB database not found at {CODE_QA_ROOT / 'database'}")
        print("   Please ensure the database directory exists")
        sys.exit(1)


def get_all_lancedb_tables(db):
    """Get all method and class tables from LanceDB"""
    try:
        # Use list_tables() instead of deprecated table_names()
        try:
            tables_response = db.list_tables()
            # Handle response object - it might be a dict with 'tables' key
            if isinstance(tables_response, dict):
                available_tables = tables_response.get('tables', [])
            elif hasattr(tables_response, 'tables'):
                available_tables = tables_response.tables
            elif hasattr(tables_response, '__iter__') and not isinstance(tables_response, str):
                # Try to iterate and get table names
                available_tables = list(tables_response)
            else:
                available_tables = []
        except AttributeError:
            # Fallback for older versions
            available_tables = db.table_names()
        except Exception as e:
            # Try alternative method
            try:
                available_tables = [name for name in dir(db) if not name.startswith('_')]
                # Filter to actual table names
                available_tables = [t for t in available_tables if isinstance(t, str) and ('_method' in t or '_class' in t)]
            except:
                raise e
        
        print(f"  📋 Found {len(available_tables)} tables: {available_tables}")
        
        method_tables = [t for t in available_tables if isinstance(t, str) and t.endswith("_method")]
        class_tables = [t for t in available_tables if isinstance(t, str) and t.endswith("_class")]
        
        print(f"  📋 Method tables: {method_tables}")
        print(f"  📋 Class tables: {class_tables}")
        
        # Match method and class tables by prefix
        table_pairs = {}
        for method_table in method_tables:
            prefix = method_table[:-7]  # Remove "_method"
            class_table = prefix + "_class"
            if class_table in class_tables:
                table_pairs[prefix] = (method_table, class_table)
            else:
                print(f"  ⚠️  Warning: Method table {method_table} has no matching class table {class_table}")
        
        # Also check for class tables without method tables (shouldn't happen, but just in case)
        for class_table in class_tables:
            prefix = class_table[:-6]  # Remove "_class"
            method_table = prefix + "_method"
            if method_table not in method_tables and prefix not in table_pairs:
                print(f"  ⚠️  Warning: Class table {class_table} has no matching method table {method_table}")
        
        return table_pairs
    except Exception as e:
        print(f"❌ Error getting tables: {e}")
        import traceback
        traceback.print_exc()
        return {}


def read_lancedb_table(db, table_name: str) -> List[Dict[str, Any]]:
    """Read all rows from a LanceDB table"""
    try:
        table = db.open_table(table_name)
        df = table.to_pandas()
        
        # Convert DataFrame to list of dicts
        chunks = df.to_dict('records')
        print(f"  ✅ Read {len(chunks)} chunks from {table_name}")
        return chunks
    except Exception as e:
        print(f"  ❌ Error reading {table_name}: {e}")
        return []


def convert_method_chunk(chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert LanceDB method chunk to Supabase format"""
    try:
        file_path = chunk.get('file_path', '')
        if not file_path:
            return None
        
        normalized_path = normalize_path_consistent(file_path)
        
        # Get embedding - could be in different field names
        embedding = None
        if 'method_embeddings' in chunk:
            embedding = chunk['method_embeddings']
        elif 'embedding' in chunk:
            embedding = chunk['embedding']
        
        if embedding is None:
            print(f"  ⚠️  Warning: No embedding found for method {chunk.get('name', 'unknown')} in {file_path}")
            return None
        
        # Convert numpy array to list if needed
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        elif not isinstance(embedding, list):
            embedding = list(embedding)
        
        # Ensure embedding is the right length (1024 for Qwen)
        if len(embedding) != 1024:
            print(f"  ⚠️  Warning: Embedding dimension mismatch: {len(embedding)} != 1024")
            return None
        
        supabase_chunk = {
            "file_path": normalized_path or file_path,
            "chunk_type": "method",
            "class_name": chunk.get('class_name'),
            "method_name": chunk.get('name'),
            "source_code": chunk.get('source_code', ''),
            "code": chunk.get('code', ''),
            "embedding": embedding,
            "doc_comment": chunk.get('doc_comment', ''),
            "constructor_declaration": None,
            "method_declarations": None,
            "references": chunk.get('references', ''),  # Will be mapped to code_references column
            "metadata": {
                "indexed_from": "lancedb_migration",
                "original_table": "method"
            }
        }
        
        return supabase_chunk
    except Exception as e:
        print(f"  ❌ Error converting method chunk: {e}")
        return None


def convert_class_chunk(chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert LanceDB class chunk to Supabase format"""
    try:
        file_path = chunk.get('file_path', '')
        if not file_path:
            return None
        
        normalized_path = normalize_path_consistent(file_path)
        
        # Get embedding
        embedding = None
        if 'class_embeddings' in chunk:
            embedding = chunk['class_embeddings']
        elif 'embedding' in chunk:
            embedding = chunk['embedding']
        
        if embedding is None:
            print(f"  ⚠️  Warning: No embedding found for class {chunk.get('class_name', 'unknown')} in {file_path}")
            return None
        
        # Convert numpy array to list if needed
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        elif not isinstance(embedding, list):
            embedding = list(embedding)
        
        # Ensure embedding is the right length
        if len(embedding) != 1024:
            print(f"  ⚠️  Warning: Embedding dimension mismatch: {len(embedding)} != 1024")
            return None
        
        supabase_chunk = {
            "file_path": normalized_path or file_path,
            "chunk_type": "class",
            "class_name": chunk.get('class_name'),
            "method_name": None,
            "source_code": chunk.get('source_code', ''),
            "code": None,
            "embedding": embedding,
            "doc_comment": None,
            "constructor_declaration": chunk.get('constructor_declaration', ''),
            "method_declarations": chunk.get('method_declarations', ''),
            "references": chunk.get('references', ''),  # Will be mapped to code_references column
            "metadata": {
                "indexed_from": "lancedb_migration",
                "original_table": "class"
            }
        }
        
        return supabase_chunk
    except Exception as e:
        print(f"  ❌ Error converting class chunk: {e}")
        return None


def collect_unique_files(chunks: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Collect unique file paths from chunks"""
    files = {}
    for chunk in chunks:
        file_path = chunk.get('file_path', '')
        if file_path:
            normalized = normalize_path_consistent(file_path)
            if normalized and normalized not in files:
                # Extract filename from path
                file_name = os.path.basename(file_path)
                files[normalized] = {
                    'file_path': normalized,
                    'file_name': file_name,
                    'normalized_path': normalized
                }
    return files


def migrate_table_pair(db, prefix: str, method_table: str, class_table: str):
    """Migrate a pair of method and class tables"""
    print(f"\n📦 Migrating table pair: {prefix}")
    print(f"   Method table: {method_table}")
    print(f"   Class table: {class_table}")
    
    # Read chunks from LanceDB
    method_chunks = read_lancedb_table(db, method_table)
    class_chunks = read_lancedb_table(db, class_table)
    
    if not method_chunks and not class_chunks:
        print(f"  ⚠️  No chunks found in {prefix} tables, skipping")
        return
    
    # Convert chunks to Supabase format
    print(f"  🔄 Converting chunks...")
    supabase_chunks = []
    
    for chunk in method_chunks:
        converted = convert_method_chunk(chunk)
        if converted:
            supabase_chunks.append(converted)
    
    for chunk in class_chunks:
        converted = convert_class_chunk(chunk)
        if converted:
            supabase_chunks.append(converted)
    
    print(f"  ✅ Converted {len(supabase_chunks)} chunks")
    
    if not supabase_chunks:
        print(f"  ⚠️  No valid chunks to migrate for {prefix}")
        return
    
    # Collect unique files
    all_chunks = method_chunks + class_chunks
    unique_files = collect_unique_files(all_chunks)
    
    # Insert files first
    print(f"  📁 Inserting {len(unique_files)} unique files...")
    for file_info in unique_files.values():
        try:
            insert_code_file(
                file_path=file_info['file_path'],
                file_name=file_info['file_name'],
                normalized_path=file_info['normalized_path']
            )
        except Exception as e:
            # File might already exist, that's okay
            if "duplicate" not in str(e).lower() and "unique" not in str(e).lower():
                print(f"    ⚠️  Warning inserting file {file_info['file_name']}: {e}")
    
    # Insert chunks in batches
    print(f"  💾 Inserting {len(supabase_chunks)} chunks to Supabase...")
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(supabase_chunks), batch_size):
        batch = supabase_chunks[i:i + batch_size]
        try:
            inserted = insert_code_chunks(batch)
            total_inserted += inserted
            print(f"    ✅ Inserted batch {i//batch_size + 1} ({inserted} chunks)")
        except Exception as e:
            print(f"    ❌ Error inserting batch {i//batch_size + 1}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"  ✅ Successfully migrated {total_inserted} chunks from {prefix}")


def main():
    """Main migration function"""
    print("=" * 70)
    print("🚀 Code Q&A Migration: LanceDB → Supabase")
    print("=" * 70)
    
    # Connect to LanceDB
    print(f"\n📂 Connecting to LanceDB at: {LANCE_DB_PATH}")
    try:
        db = lancedb.connect(str(LANCE_DB_PATH))
        print("  ✅ Connected to LanceDB")
    except Exception as e:
        print(f"  ❌ Error connecting to LanceDB: {e}")
        sys.exit(1)
    
    # Get all table pairs
    print("\n🔍 Discovering tables...")
    table_pairs = get_all_lancedb_tables(db)
    
    if not table_pairs:
        print("  ❌ No method/class table pairs found")
        sys.exit(1)
    
    print(f"  ✅ Found {len(table_pairs)} table pair(s):")
    for prefix in table_pairs:
        print(f"     - {prefix}")
    
    # Confirm migration
    print(f"\n⚠️  This will migrate all data from LanceDB to Supabase")
    print(f"   Total table pairs: {len(table_pairs)}")
    response = input("   Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("   Migration cancelled")
        sys.exit(0)
    
    # Migrate each table pair
    total_chunks = 0
    for prefix, (method_table, class_table) in table_pairs.items():
        try:
            migrate_table_pair(db, prefix, method_table, class_table)
        except Exception as e:
            print(f"  ❌ Error migrating {prefix}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ Migration completed!")
    print("=" * 70)
    print("\n📝 Next steps:")
    print("   1. Verify data in Supabase dashboard")
    print("   2. Test queries in the unified app")
    print("   3. Once verified, you can archive the LanceDB database")


if __name__ == "__main__":
    main()


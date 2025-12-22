"""
Fix embeddings using raw SQL - this ensures vectors are stored correctly
"""

import os
import sys
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# Add project directories to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Fixing Supabase Embeddings with Raw SQL")
print("=" * 60)

# Get Supabase connection details
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_key:
    print("\n✗ Error: Supabase not configured")
    sys.exit(1)

# Extract database connection from Supabase URL
# Supabase URL format: https://xxxxx.supabase.co
# We need to connect to: xxxxx.supabase.co:5432
import re
match = re.match(r'https://([^.]+)\.supabase\.co', supabase_url)
if not match:
    print("✗ Error: Could not parse Supabase URL")
    sys.exit(1)

project_ref = match.group(1)
db_host = f"{project_ref}.supabase.co"
db_port = 5432

# Get database password from environment or prompt
db_password = os.getenv('SUPABASE_DB_PASSWORD')
if not db_password:
    print("\n⚠ Note: To use raw SQL, you need SUPABASE_DB_PASSWORD in .env")
    print("   Alternatively, you can run SQL directly in Supabase SQL Editor:")
    print("   1. Go to Supabase Dashboard → SQL Editor")
    print("   2. Run the SQL script in scripts/fix_embeddings.sql")
    sys.exit(1)

# Local storage paths
MARKDOWN_WORKING_DIR = PARENT_ROOT / "rag_storage_md_indexed"
VDB_CHUNKS_PATH = MARKDOWN_WORKING_DIR / "vdb_chunks.json"

if not VDB_CHUNKS_PATH.exists():
    print(f"\n✗ Error: Local storage not found at {VDB_CHUNKS_PATH}")
    sys.exit(1)

try:
    # Load embeddings from local storage
    print("\n1. Loading embeddings from local storage...")
    with open(VDB_CHUNKS_PATH, 'r', encoding='utf-8') as f:
        vectors_data = json.load(f)
    
    vector_lookup = {}
    for entry in vectors_data.get("data", []):
        chunk_id = entry.get("__id__") or entry.get("id")
        vector = entry.get("vector") or entry.get("embedding")
        if chunk_id and vector and isinstance(vector, list):
            try:
                vector_lookup[chunk_id] = [float(x) for x in vector]
            except:
                continue
    
    print(f"   ✓ Loaded {len(vector_lookup)} embeddings")
    
    # Connect to database
    print("\n2. Connecting to database...")
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        database='postgres',
        user='postgres',
        password=db_password
    )
    cur = conn.cursor()
    print("   ✓ Connected")
    
    # Update embeddings using raw SQL
    print("\n3. Updating embeddings with raw SQL...")
    updated_count = 0
    
    for chunk_id, embedding in vector_lookup.items():
        # Convert list to PostgreSQL array format
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
        
        try:
            # Use PostgreSQL's array casting
            cur.execute("""
                UPDATE gdd_chunks 
                SET embedding = %s::vector 
                WHERE chunk_id = %s
            """, (embedding_str, chunk_id))
            
            if cur.rowcount > 0:
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"   Updated {updated_count} chunks...")
                    conn.commit()
        except Exception as e:
            print(f"   ⚠ Error updating {chunk_id}: {e}")
            continue
    
    conn.commit()
    print(f"\n✓ Updated {updated_count} chunks")
    
    # Verify
    print("\n4. Verifying...")
    cur.execute("""
        SELECT chunk_id, 
               pg_typeof(embedding) as embedding_type,
               array_length(embedding::float[], 1) as embedding_dim
        FROM gdd_chunks 
        WHERE embedding IS NOT NULL 
        LIMIT 5
    """)
    
    results = cur.fetchall()
    for row in results:
        chunk_id, emb_type, dim = row
        print(f"   ✓ {chunk_id}: Type={emb_type}, Dim={dim}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Fix completed!")
print("=" * 60)

